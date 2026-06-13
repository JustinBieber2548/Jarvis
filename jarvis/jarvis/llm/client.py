"""Unified LLM client. Auto-detects Ollama; falls back to OpenAI-compatible HTTP."""
from __future__ import annotations

import json
from typing import Iterable

import httpx


class LLMError(RuntimeError):
    pass


class LLMClient:
    def __init__(self, cfg):
        self.cfg = cfg
        self._backend: str | None = None  # "ollama" | "openai" | "echo"
        self._model: str | None = None

    # ---- backend detection ----
    def detect_backend(self) -> tuple[str, str]:
        # Try Ollama
        try:
            r = httpx.get(f"{self.cfg.ollama_host}/api/tags", timeout=1.5)
            if r.status_code == 200:
                models = [m["name"] for m in r.json().get("models", [])]
                model = self.cfg.ollama_model
                if not any(m.startswith(model) for m in models) and models:
                    model = models[0]
                self._backend, self._model = "ollama", model
                return "ollama", f"host={self.cfg.ollama_host} model={model}"
        except Exception:
            pass

        if self.cfg.openai_api_base and self.cfg.openai_api_key:
            self._backend = "openai"
            self._model = self.cfg.openai_model
            return "openai", f"base={self.cfg.openai_api_base} model={self._model}"

        self._backend, self._model = "echo", "echo"
        return "echo", "No LLM configured — using echo mode. Install Ollama or set OPENAI_API_KEY."

    def _ensure(self):
        if self._backend is None:
            self.detect_backend()

    # ---- core API ----
    def chat(self, messages: list[dict], temperature: float = 0.4, max_tokens: int = 1024) -> str:
        self._ensure()
        if self._backend == "ollama":
            return self._ollama_chat(messages, temperature, max_tokens)
        if self._backend == "openai":
            return self._openai_chat(messages, temperature, max_tokens)
        # echo
        last = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        return f"[echo:no-llm] {last[:400]}"

    def complete(self, prompt: str, system: str | None = None, **kw) -> str:
        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.append({"role": "user", "content": prompt})
        return self.chat(msgs, **kw)

    # ---- backends ----
    def _ollama_chat(self, messages, temperature, max_tokens):
        body = {
            "model": self._model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        r = httpx.post(f"{self.cfg.ollama_host}/api/chat", json=body, timeout=120)
        r.raise_for_status()
        data = r.json()
        return data.get("message", {}).get("content", "").strip()

    def _openai_chat(self, messages, temperature, max_tokens):
        url = self.cfg.openai_api_base.rstrip("/") + "/chat/completions"
        body = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {"Authorization": f"Bearer {self.cfg.openai_api_key}"}
        r = httpx.post(url, json=body, headers=headers, timeout=120)
        if r.status_code >= 400:
            raise LLMError(f"{r.status_code}: {r.text[:300]}")
        return r.json()["choices"][0]["message"]["content"].strip()
