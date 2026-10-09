"""
Memory system — short-term buffer + long-term summarization + session persistence.

Short-term: keeps the last N messages in full.
Long-term: when the buffer exceeds a threshold, older messages are compressed
           into a running summary by the LLM itself.
Persistence: sessions can be saved to / loaded from JSON files.
"""

import json
import os
import logging
from datetime import datetime
from typing import Optional, Callable

logger = logging.getLogger("agent.memory")


class Memory:
    """Manages conversation history with automatic summarization."""

    def __init__(
        self,
        max_messages: int = 20,
        summary_trigger: int = 16,  # compress when we have this many messages
        summary_keep: int = 10,      # keep this many latest messages after compression
    ):
        self.max_messages = max_messages
        self.summary_trigger = summary_trigger
        self.summary_keep = summary_keep

        self.messages: list[dict] = []     # full messages in context window
        self.summary: str = ""             # compressed older history
        self.metadata: dict = {            # session metadata
            "created_at": datetime.now().isoformat(),
            "message_count": 0,
        }

    # ── Add / Retrieve ────────────────────────────────────────────

    def add(self, role: str, content: str) -> None:
        """Add a message to the buffer."""
        self.messages.append({"role": role, "content": content})
        self.metadata["message_count"] += 1
        # Trim if over max (without summarization — hard cutoff)
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]

    def add_tool_result(self, tool_name: str, result: str) -> None:
        """Record a tool call and its result as a system message."""
        msg = f"[Tool: {tool_name}]\n{result}"
        self.messages.append({"role": "system", "content": msg})

    def get_context(self) -> list[dict]:
        """Return the full message list for the LLM context."""
        if self.summary:
            summary_msg = {
                "role": "system",
                "content": f"[Conversation history summary]\n{self.summary}",
            }
            return [summary_msg] + self.messages
        return self.messages

    # ── Summarization ─────────────────────────────────────────────

    def needs_summary(self) -> bool:
        """Check if the buffer should be compressed."""
        return len(self.messages) >= self.summary_trigger

    def compress(self, llm_chat: Callable) -> None:
        """
        Compress older messages into a running summary using the LLM.
        `llm_chat(messages, tools=None)` should return a dict like Ollama's response.
        """
        if len(self.messages) <= self.summary_keep:
            return

        to_summarize = self.messages[: -self.summary_keep]
        self.messages = self.messages[-self.summary_keep:]

        # Build summarization prompt
        existing = f"Previous summary:\n{self.summary}" if self.summary else ""
        dialog = "\n".join(
            f"{m['role']}: {m['content'][:500]}" for m in to_summarize
        )

        prompt = f"""Summarize the following conversation into a concise paragraph (keep key facts, names, decisions, and open questions).

{existing}

New dialogue to summarize:
{dialog}

Updated summary:"""

        try:
            resp = llm_chat([{"role": "user", "content": prompt}])
            self.summary = resp["message"]["content"].strip()
            logger.info("memory compressed: %d messages → summary (%d chars)",
                        len(to_summarize), len(self.summary))
        except Exception as e:
            logger.error("summarization failed: %s", e)
            # fallback: keep raw messages as summary
            self.summary = dialog[:2000]

    # ── Persistence ───────────────────────────────────────────────

    def save(self, filepath: str) -> None:
        """Save full session to a JSON file."""
        data = {
            "metadata": self.metadata,
            "summary": self.summary,
            "messages": self.messages,
        }
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info("session saved to %s", filepath)

    def load(self, filepath: str) -> None:
        """Restore session from a JSON file."""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.metadata = data.get("metadata", {})
        self.summary = data.get("summary", "")
        self.messages = data.get("messages", [])
        logger.info("session loaded from %s (%d messages)", filepath, len(self.messages))

    # ── Reset ─────────────────────────────────────────────────────

    def clear(self) -> None:
        """Reset all memory."""
        self.messages = []
        self.summary = ""
        self.metadata = {"created_at": datetime.now().isoformat(), "message_count": 0}
