#!/usr/bin/env python3
"""
Basic Agent CLI — a local AI agent powered by Ollama.

Usage:
    python main.py                # Interactive mode
    python main.py --model qwen2.5:7b  # Specify model
    python main.py --single "Your question"  # Single-shot mode
"""

import argparse
import logging
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent.llm import LLMInterface
from agent.tools import ToolRegistry
from agent.memory import Memory
from agent.logger import WorkLogger
from agent.core import Agent

from tools import (
    WebSearchTool,
    ReadFileTool,
    WriteFileTool,
    CalculatorTool,
    DateTimeTool,
    ShellTool,
    RAGSearchTool,
)

# Optional: rich for pretty output
try:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.prompt import Prompt
    HAS_RICH = True
except ImportError:
    HAS_RICH = False


def setup_logging(level: str = "INFO") -> None:
    """Configure Python logging for the agent internals."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def build_agent(model: str = "qwen2.5:7b", embed_model: str = "bge-m3") -> Agent:
    """Wire up all components and return a ready-to-use Agent."""
    # LLM interface
    llm = LLMInterface(chat_model=model, embed_model=embed_model)

    # Tools
    registry = ToolRegistry()
    registry.register(WebSearchTool())
    registry.register(ReadFileTool())
    registry.register(WriteFileTool())
    registry.register(CalculatorTool())
    registry.register(DateTimeTool())
    registry.register(ShellTool())

    # RAG tool (needs special init for ChromaDB)
    knowledge_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "knowledge")
    try:
        from tools.rag_search import init_rag
        init_rag(knowledge_dir, llm.embed)
        registry.register(RAGSearchTool())
    except Exception as e:
        logging.getLogger("main").warning("RAG init skipped: %s", e)

    # Memory
    memory = Memory()

    # Logger
    work_logger = WorkLogger()

    # Agent
    agent = Agent(llm=llm, tools=registry, memory=memory, logger_inst=work_logger)
    return agent


def interactive_loop(agent: Agent, model: str) -> None:
    """Run the agent in interactive CLI mode."""
    agent.log.start(model)

    # Welcome banner
    welcome = f"""
╔══════════════════════════════════════════════╗
║         🤖 Basic Agent - Local AI            ║
║         Powered by Ollama ({model})          ║
║                                              ║
║  Type /help for commands, /exit to quit      ║
║  Your data stays on this computer            ║
╚══════════════════════════════════════════════╝
"""
    if HAS_RICH:
        console = Console()
        console.print(Panel(welcome.strip(), border_style="cyan"))
    else:
        print(welcome)

    while True:
        try:
            if HAS_RICH:
                user_input = Prompt.ask("\n[bold green]You[/]").strip()
            else:
                user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        # Run agent
        try:
            response = agent.run(user_input)
        except Exception as e:
            logging.getLogger("main").error("Agent error: %s", e)
            print(f"\n❌ Error: {e}")
            continue

        # Check for exit command
        if response == "__EXIT__":
            print("Goodbye!")
            break

        # Display response
        if HAS_RICH:
            console.print("\n[bold blue]Agent[/]", end=" ")
            try:
                console.print(Markdown(response))
            except Exception:
                console.print(response)
        else:
            print(f"\nAgent: {response}")

    # Cleanup
    md_path, jsonl_path = agent.log.finish(model)
    print(f"\n📝 Session log: {md_path}")
    print(f"📊 JSONL log:   {jsonl_path}")


def single_shot(agent: Agent, model: str, question: str) -> None:
    """Run a single question and exit."""
    agent.log.start(model)
    response = agent.run(question)
    print(response)
    agent.log.finish(model)


def main():
    parser = argparse.ArgumentParser(description="Basic Agent - Local AI powered by Ollama")
    parser.add_argument(
        "--model", "-m", default="qwen2.5:7b",
        help="Ollama chat model name (default: qwen2.5:7b)"
    )
    parser.add_argument(
        "--embed-model", default="bge-m3",
        help="Ollama embedding model name (default: bge-m3)"
    )
    parser.add_argument(
        "--single", "-s", default=None,
        help="Single-shot mode: ask one question and exit"
    )
    parser.add_argument(
        "--log-level", default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity (default: INFO)"
    )
    args = parser.parse_args()

    setup_logging(args.log_level)

    agent = build_agent(model=args.model, embed_model=args.embed_model)

    if args.single:
        single_shot(agent, args.model, args.single)
    else:
        interactive_loop(agent, args.model)


if __name__ == "__main__":
    main()
