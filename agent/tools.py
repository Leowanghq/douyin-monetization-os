"""
Tool system — base class, registry, and schema helpers.

Adding a new tool is as simple as:
  1. Subclass BaseTool
  2. Implement `execute(**kwargs) -> str`
  3. Register it with ToolRegistry.register(MyTool())
"""

import json
import logging
from typing import Any

logger = logging.getLogger("agent.tools")


class BaseTool:
    """Every tool must subclass this and define name, description, parameters, execute."""

    name: str = ""
    description: str = ""
    parameters: dict = {}  # JSON Schema for the tool's inputs

    def execute(self, **kwargs) -> str:
        """Run the tool with the given keyword arguments. Return a string result."""
        raise NotImplementedError

    def to_ollama_schema(self) -> dict:
        """Convert to Ollama-compatible tool schema dict."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": self.parameters,
                    "required": list(self.parameters.keys()),
                },
            },
        }


class ToolRegistry:
    """Holds all registered tools and dispatches calls by name."""

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool
        logger.info("registered tool: %s", tool.name)

    def get_all_schemas(self) -> list[dict]:
        return [t.to_ollama_schema() for t in self._tools.values()]

    def get_tool_names(self) -> list[str]:
        return list(self._tools.keys())

    def execute(self, name: str, arguments: dict) -> str:
        """
        Execute a tool by name with given arguments.
        Returns the tool's string output or an error message.
        """
        tool = self._tools.get(name)
        if tool is None:
            return f"Error: unknown tool '{name}'. Available: {self.get_tool_names()}"

        try:
            logger.info("executing tool: %s(%s)", name, json.dumps(arguments, ensure_ascii=False))
            result = tool.execute(**arguments)
            # Truncate overly long results to keep context manageable
            if len(result) > 8000:
                result = result[:8000] + "\n... [truncated]"
            logger.debug("tool %s returned %d chars", name, len(result))
            return result
        except Exception as e:
            logger.error("tool %s failed: %s", name, e)
            return f"Error executing {name}: {e}"
