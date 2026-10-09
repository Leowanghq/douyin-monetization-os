"""
File read/write tools — safely access the local filesystem.
"""

import os

from agent.tools import BaseTool


class ReadFileTool(BaseTool):
    name = "read_file"
    description = "Read the contents of a local file. Returns the file text."
    parameters = {
        "filepath": {
            "type": "string",
            "description": "Absolute or relative path to the file to read.",
        },
    }

    def execute(self, filepath: str) -> str:
        if not os.path.exists(filepath):
            return f"Error: file not found: {filepath}"
        if not os.path.isfile(filepath):
            return f"Error: not a file: {filepath}"
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            if len(content) > 10000:
                content = content[:10000] + "\n... [file truncated at 10000 chars]"
            return content
        except Exception as e:
            return f"Error reading {filepath}: {e}"


class WriteFileTool(BaseTool):
    name = "write_file"
    description = "Write text content to a local file. Creates or overwrites the file."
    parameters = {
        "filepath": {
            "type": "string",
            "description": "Absolute or relative path to write to.",
        },
        "content": {
            "type": "string",
            "description": "The text content to write to the file.",
        },
    }

    def execute(self, filepath: str, content: str) -> str:
        try:
            os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Successfully wrote {len(content)} characters to {filepath}"
        except Exception as e:
            return f"Error writing {filepath}: {e}"
