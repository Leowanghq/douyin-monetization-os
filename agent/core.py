"""
Agent core loop — the ReAct (Reasoning + Acting) engine.

Flow:
  User Input → [System Prompt + Memory + Tools] → LLM
    → Tool Call? → Execute tool → Feed result back → LLM
    → Final answer? → Display to user → Log → Wait for next input
"""

import json
import logging
import time
from typing import Optional

from agent.llm import LLMInterface
from agent.tools import ToolRegistry
from agent.memory import Memory
from agent.logger import WorkLogger

logger = logging.getLogger("agent.core")

SYSTEM_PROMPT = """You are a helpful AI assistant running locally via Ollama. You have access to tools that let you search the web, read and write files, calculate math, check the date/time, run safe shell commands, and search a local knowledge base.

**Guidelines:**
1. Use tools when you need real-time information, calculations, or file access. Don't guess — look it up.
2. If a tool returns an error, try a different approach or explain the issue to the user.
3. Be concise but thorough. Answer in the same language the user uses.
4. When using web_search, be specific with your query terms.
5. For math, always use the calculator tool — don't do it in your head.
6. You can read and write files. The working directory is where the agent was launched.

You are powered by a local Ollama model — no data leaves this computer."""


class Agent:
    """The main Agent that runs the ReAct loop."""

    def __init__(
        self,
        llm: LLMInterface,
        tools: ToolRegistry,
        memory: Memory,
        logger_inst: WorkLogger,
        max_tool_rounds: int = 10,
    ):
        self.llm = llm
        self.tools = tools
        self.memory = memory
        self.log = logger_inst
        self.max_tool_rounds = max_tool_rounds
        self.extra_system_prompt = ""  # optional expert persona (e.g. Douyin OS)

    # ── Public API ────────────────────────────────────────────────

    def run(self, user_input: str) -> str:
        """
        Process one user input through the ReAct loop.
        Returns the agent's final text response.
        """
        # Handle slash commands
        if user_input.startswith("/"):
            return self._handle_command(user_input)

        self.log.user_input(user_input)
        self.memory.add("user", user_input)

        # Main ReAct loop
        response = self._react_loop()

        # Record and return
        self.memory.add("assistant", response)
        self.log.agent_response(response)
        return response

    # ── ReAct Loop ────────────────────────────────────────────────

    def _react_loop(self) -> str:
        """Core ReAct loop: LLM ↔ Tool execution."""
        all_messages = self._build_messages()
        tool_schemas = self.tools.get_all_schemas()

        for round_num in range(self.max_tool_rounds):
            t0 = time.time()

            # 1. Call LLM with tools
            try:
                resp = self.llm.chat(all_messages, tools=tool_schemas)
            except Exception as e:
                self.log.error("LLM call", e)
                return f"Sorry, I encountered an error calling the LLM: {e}"

            duration = time.time() - t0
            self.log.llm_call(len(all_messages), resp, duration)

            msg = resp.get("message", {})

            # 2. Check for tool calls
            tool_calls = msg.get("tool_calls", [])
            if tool_calls:
                for tc in tool_calls:
                    fn = tc.get("function", {})
                    tool_name = fn.get("name", "")
                    tool_args = fn.get("arguments", {})

                    # Handle when arguments come as a JSON string
                    if isinstance(tool_args, str):
                        try:
                            tool_args = json.loads(tool_args)
                        except json.JSONDecodeError:
                            tool_args = {}

                    # Add assistant's tool call to context
                    all_messages.append({
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [tc],
                    })

                    # Execute tool
                    t0_tool = time.time()
                    result = self._execute_tool_sync(tool_name, tool_args)
                    tool_duration = time.time() - t0_tool

                    self.log.tool_call(tool_name, tool_args, result, tool_duration)

                    # Add tool result to context
                    all_messages.append({
                        "role": "tool",
                        "content": result,
                    })
                    self.memory.add_tool_result(tool_name, result)

                # Continue loop → LLM processes tool results
                continue

            # 3. No tool calls → it's a final response
            content = msg.get("content", "")
            if not content and round_num > 0:
                # Sometimes the model returns empty after tool calls; prompt it
                all_messages.append({"role": "user", "content": "Please provide your final answer based on the tool results above."})
                continue

            return content or "(I couldn't generate a response. Please try rephrasing.)"

        # Max rounds reached
        return "(I've reached the maximum number of tool-calling rounds. Let me summarize what I have so far.)"

    # ── Helpers ───────────────────────────────────────────────────

    def _build_messages(self) -> list[dict]:
        """Construct the message list: system prompt + persona + memory context."""
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        if self.extra_system_prompt:
            messages.append({"role": "system", "content": self.extra_system_prompt})
        messages.extend(self.memory.get_context())
        return messages

    def _execute_tool_sync(self, tool_name: str, tool_args: dict) -> str:
        """Execute a tool synchronously."""
        return self.tools.execute(tool_name, tool_args)

    # ── Persona / 专家模式 ──────────────────────────────────────

    def set_persona(self, prompt: str) -> None:
        """Activate an expert persona (injected as a secondary system prompt)."""
        self.extra_system_prompt = prompt

    def clear_persona(self) -> None:
        """Deactivate any active expert persona."""
        self.extra_system_prompt = ""

    def _handle_command(self, user_input: str) -> str:
        """Handle slash commands like /exit, /clear, /save, /load."""
        parts = user_input.strip().split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        if cmd == "/exit" or cmd == "/quit":
            return "__EXIT__"
        elif cmd == "/clear":
            self.memory.clear()
            return "🧹 Memory cleared. Starting fresh."
        elif cmd == "/save":
            filepath = arg or f"logs/sessions/{self.log.session_id}_save.json"
            self.memory.save(filepath)
            return f"💾 Session saved to {filepath}"
        elif cmd == "/load":
            if not arg:
                return "Usage: /load <filepath>"
            try:
                self.memory.load(arg)
                return f"📂 Session loaded from {arg} ({len(self.memory.messages)} messages)"
            except Exception as e:
                return f"❌ Failed to load: {e}"
        elif cmd == "/stats":
            stats = self.llm.stats
            return (
                f"📊 **Session Stats**\n"
                f"  Model: {stats['model']}\n"
                f"  LLM calls: {stats['total_calls']}\n"
                f"  Total tokens: {stats['total_tokens']}\n"
                f"  Total latency: {stats['total_latency_s']}s\n"
                f"  Avg latency: {stats['avg_latency_s']}s\n"
                f"  Memory messages: {len(self.memory.messages)}"
            )
        elif cmd == "/tools":
            names = self.tools.get_tool_names()
            return "🔧 **Available tools**: " + ", ".join(names)
        elif cmd == "/douyin" or cmd == "/d":
            return self._handle_douyin(arg)
        elif len(cmd) == 3 and cmd.startswith("/d") and cmd[2] in "12345678":
            return self._handle_douyin(cmd[2])
        elif cmd == "/help":
            return (
                "**Commands:**\n"
                "  /exit — Quit the agent\n"
                "  /clear — Clear conversation memory\n"
                "  /save [path] — Save session to file\n"
                "  /load <path> — Load session from file\n"
                "  /stats — Show LLM usage statistics\n"
                "  /tools — List available tools\n"
                "  /douyin — 抖音变现操作系统（/d1../d8 快速激活模块）\n"
                "  /help — Show this message"
            )
        else:
            return f"Unknown command: {cmd}. Type /help for available commands."

    def _handle_douyin(self, arg: str) -> str:
        """Handle /douyin commands by delegating to the DouyinOS module."""
        try:
            from douyin.engine import get_os
        except Exception as e:
            return f"❌ 抖音模块加载失败: {e}"

        os_ = get_os()
        parts = arg.strip().split()
        sub = parts[0].lower() if parts else ""

        if not sub or sub in ("help", "menu", "?"):
            return os_.menu()
        if sub in ("status", "state"):
            return os_.status()
        if sub in ("off", "clear", "exit"):
            self.clear_persona()
            return os_.deactivate()
        if sub == "run":
            return os_.run_all(self)
        if sub == "set" and len(parts) >= 2:
            return os_.set_state(" ".join(parts[1:]))

        persona, reply = os_.activate(sub)
        if persona:
            self.set_persona(persona)
        return reply
