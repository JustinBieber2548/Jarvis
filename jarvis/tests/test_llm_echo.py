"""Test echo backend works without any LLM installed."""
from jarvis.llm.client import LLMClient


class _Cfg:
    ollama_host = "http://127.0.0.1:1"  # guaranteed-bad port
    ollama_model = "none"
    openai_api_base = None
    openai_api_key = None
    openai_model = "none"


def test_echo_fallback():
    c = LLMClient(_Cfg())
    backend, _ = c.detect_backend()
    assert backend == "echo"
    out = c.complete("hello world")
    assert "hello world" in out
