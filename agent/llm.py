"""
Ollama LLM interface — handles chat completions and embeddings.
All calls go to a local Ollama server. No API keys needed.
"""

import time
import logging
from typing import Optional

import ollama

logger = logging.getLogger("agent.llm")


class LLMInterface:
    """Wraps Ollama chat & embedding APIs with retry, timeout, and telemetry."""

    def __init__(
        self,
        chat_model: str = "qwen2.5:7b",
        embed_model: str = "bge-m3",
        host: str = "http://127.0.0.1:11434",
        timeout: float = 120.0,
        max_retries: int = 2,
    ):
        self.chat_model = chat_model
        self.embed_model = embed_model
        self.timeout = timeout
        self.max_retries = max_retries
        self._client = ollama.Client(host=host, timeout=timeout)

        # Telemetry counters (reset per session)
        self.total_tokens = 0
        self.total_calls = 0
        self.total_latency = 0.0

    # ── Chat ──────────────────────────────────────────────────────

    def chat(
        self,
        messages: list[dict],
        tools: Optional[list[dict]] = None,
        stream: bool = False,
    ) -> dict:
        """
        Send a chat request. Returns the Ollama response dict.
        When `tools` is provided, the model may return a tool_call instead of content.

        Response shape (no tools):
          {"message": {"role": "assistant", "content": "..."}, ...}
        Response shape (with tool_call):
          {"message": {"role": "assistant", "content": "", "tool_calls": [...]}, ...}
        """
        last_error = None
        for attempt in range(self.max_retries + 1):
            t0 = time.time()
            try:
                kwargs = {
                    "model": self.chat_model,
                    "messages": messages,
                    "stream": stream,
                }
                if tools:
                    kwargs["tools"] = tools

                resp = self._client.chat(**kwargs)

                elapsed = time.time() - t0
                self.total_calls += 1
                self.total_latency += elapsed

                # Count tokens when available
                if "eval_count" in resp:
                    self.total_tokens += resp.get("eval_count", 0)
                if "prompt_eval_count" in resp:
                    self.total_tokens += resp.get("prompt_eval_count", 0)

                logger.debug(
                    "chat call #%d OK (%.1fs, attempt %d)",
                    self.total_calls, elapsed, attempt + 1,
                )
                return resp

            except Exception as e:
                last_error = e
                logger.warning("chat attempt %d failed: %s", attempt + 1, e)
                if attempt < self.max_retries:
                    time.sleep(1.0 * (attempt + 1))  # linear backoff

        raise RuntimeError(
            f"Ollama chat failed after {self.max_retries + 1} attempts: {last_error}"
        )

    def chat_stream(self, messages: list[dict], tools: Optional[list[dict]] = None):
        """Generator that yields content chunks from a streaming chat."""
        kwargs = {
            "model": self.chat_model,
            "messages": messages,
            "stream": True,
        }
        if tools:
            kwargs["tools"] = tools

        t0 = time.time()
        for chunk in self._client.chat(**kwargs):
            yield chunk

        elapsed = time.time() - t0
        self.total_calls += 1
        self.total_latency += elapsed

    # ── Embedding ─────────────────────────────────────────────────

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts. Returns list of vectors."""
        last_error = None
        for attempt in range(self.max_retries + 1):
            t0 = time.time()
            try:
                resp = self._client.embed(model=self.embed_model, input=texts)

                elapsed = time.time() - t0
                self.total_calls += 1
                self.total_latency += elapsed
                self.total_tokens += resp.get("total_tokens", 0)

                return resp["embeddings"]
            except Exception as e:
                last_error = e
                logger.warning("embed attempt %d failed: %s", attempt + 1, e)
                if attempt < self.max_retries:
                    time.sleep(1.0 * (attempt + 1))

        raise RuntimeError(
            f"Ollama embed failed after {self.max_retries + 1} attempts: {last_error}"
        )

    # ── Telemetry ─────────────────────────────────────────────────

    @property
    def stats(self) -> dict:
        return {
            "model": self.chat_model,
            "total_calls": self.total_calls,
            "total_tokens": self.total_tokens,
            "total_latency_s": round(self.total_latency, 2),
            "avg_latency_s": round(self.total_latency / max(1, self.total_calls), 2),
        }
