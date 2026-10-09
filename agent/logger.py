"""
Work logger — produces AI-readable structured logs in Markdown and JSONL formats.

Each session produces:
  - logs/sessions/{session_id}.md     (human & AI readable narrative)
  - logs/sessions/{session_id}.jsonl  (machine-parseable structured log)
"""

import json
import os
import time
from datetime import datetime
from typing import Optional


class WorkLogger:
    """Records every step of an agent session for debugging, auditing, and improvement."""

    def __init__(self, log_dir: str = "logs/sessions"):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)

        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.start_time = time.time()

        self.steps: list[dict] = []           # structured step records
        self.llm_calls: list[dict] = []       # LLM call details
        self.tool_calls: list[dict] = []      # Tool call details
        self.errors: list[dict] = []          # Errors encountered

        self._md_lines: list[str] = []        # accumulating markdown

    # ── Recording methods ─────────────────────────────────────────

    def start(self, model: str) -> None:
        header = f"""# Agent Session: {self.session_id}
**Started**: {datetime.now().isoformat()}
**Model**: {model}
**Log directory**: {self.log_dir}

---
"""
        self._md_lines.append(header)

    def user_input(self, text: str) -> None:
        self._md_lines.append(f"### 👤 User\n{text}\n")
        self.steps.append({"type": "user", "text": text, "ts": time.time()})

    def agent_think(self, thought: str) -> None:
        self._md_lines.append(f"### 🧠 Think\n{thought}\n")
        self.steps.append({"type": "think", "text": thought, "ts": time.time()})

    def agent_response(self, text: str) -> None:
        self._md_lines.append(f"### 🤖 Assistant\n{text}\n")
        self.steps.append({"type": "assistant", "text": text, "ts": time.time()})

    def tool_call(self, name: str, args: dict, result: str, duration: float) -> None:
        entry = (
            f"### 🔧 Tool: `{name}`\n"
            f"**Args**: `{json.dumps(args, ensure_ascii=False)}`\n"
            f"**Duration**: {duration:.2f}s\n\n"
            f"**Result**:\n{result}\n"
        )
        self._md_lines.append(entry)
        self.tool_calls.append({
            "name": name,
            "args": args,
            "result": result[:500],
            "duration": round(duration, 3),
            "ts": time.time(),
        })
        self.steps.append({
            "type": "tool",
            "name": name,
            "args": args,
            "result_preview": result[:300],
            "duration": round(duration, 3),
            "ts": time.time(),
        })

    def llm_call(self, messages_count: int, response: dict, duration: float) -> None:
        content = response.get("message", {}).get("content", "")
        tool_calls = response.get("message", {}).get("tool_calls") or []
        self.llm_calls.append({
            "messages_count": messages_count,
            "content_preview": content[:300] if content else "",
            "tool_calls": [tc.get("function", {}).get("name", "?") for tc in tool_calls],
            "duration": round(duration, 3),
            "ts": time.time(),
        })

    def error(self, context: str, err: Exception) -> None:
        self._md_lines.append(f"### ❌ Error ({context})\n```\n{err}\n```\n")
        self.errors.append({"context": context, "error": str(err), "ts": time.time()})

    def finish(self, model: str) -> tuple[str, str]:
        """Finalize and write logs to disk. Returns (md_path, jsonl_path)."""
        duration = time.time() - self.start_time

        # Summary section
        total_tool_calls = len(self.tool_calls)
        total_llm_calls = len(self.llm_calls)
        summary = f"""---
## 📊 Session Summary
| Metric | Value |
|--------|-------|
| Duration | {duration:.1f}s |
| LLM calls | {total_llm_calls} |
| Tool calls | {total_tool_calls} |
| Errors | {len(self.errors)} |
| Steps | {len(self.steps)} |
| Model | {model} |
"""
        self._md_lines.append(summary)

        # Write Markdown log
        md_path = os.path.join(self.log_dir, f"{self.session_id}.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(self._md_lines))

        # Write JSONL log
        jsonl_path = os.path.join(self.log_dir, f"{self.session_id}.jsonl")
        with open(jsonl_path, "w", encoding="utf-8") as f:
            for step in self.steps:
                f.write(json.dumps(step, ensure_ascii=False) + "\n")
            # Also append llm_calls and tool_calls as structured data
            f.write(json.dumps({"type": "meta", "llm_calls": self.llm_calls, "tool_calls": self.tool_calls, "errors": self.errors, "duration_s": round(duration, 1)}, ensure_ascii=False) + "\n")

        return md_path, jsonl_path
