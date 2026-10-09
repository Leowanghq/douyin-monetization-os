"""
Shell command execution tool — runs shell commands with a safety whitelist.
"""

import subprocess

from agent.tools import BaseTool

# Only allow these safe commands (prevent arbitrary code execution)
_SAFE_COMMANDS = ["dir", "ls", "cat", "echo", "type", "pwd", "date", "whoami", "hostname", "ping", "nslookup"]


class ShellTool(BaseTool):
    name = "run_shell"
    description = (
        "Run a safe shell command. Allowed commands: " + ", ".join(_SAFE_COMMANDS) + "."
    )
    parameters = {
        "command": {
            "type": "string",
            "description": "The shell command to run. Only safe commands are allowed.",
        },
    }

    def execute(self, command: str) -> str:
        cmd_name = command.strip().split()[0] if command.strip() else ""
        if cmd_name.lower() not in _SAFE_COMMANDS:
            return (
                f"Error: command '{cmd_name}' is not in the safe list. "
                f"Allowed: {', '.join(_SAFE_COMMANDS)}"
            )

        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True,
                timeout=30, cwd=".",
            )
            out = result.stdout.strip() or "(no output)"
            if len(out) > 3000:
                out = out[:3000] + "\n... [truncated]"
            if result.stderr:
                out += f"\n[stderr]\n{result.stderr.strip()[:500]}"
            return out
        except subprocess.TimeoutExpired:
            return f"Error: command timed out after 30s"
        except Exception as e:
            return f"Error running command: {e}"
