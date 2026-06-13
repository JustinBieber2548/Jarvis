"""Configuration loaded from environment + .env."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def _bool(v: str | None, default: bool = False) -> bool:
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class Config:
    # LLM
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"
    openai_api_base: str | None = None
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"

    # Self-improve
    full_control: bool = False
    repo_path: Path = field(default_factory=lambda: Path.cwd())

    # Voice
    voice: bool = False
    wakeword: str = "hey_jarvis"
    piper_voice: str = "en_US-amy-medium"

    # Data
    data_dir: Path = field(default_factory=lambda: Path("./data"))

    @classmethod
    def load(cls) -> "Config":
        c = cls(
            ollama_host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
            ollama_model=os.getenv("OLLAMA_MODEL", "llama3.1"),
            openai_api_base=os.getenv("OPENAI_API_BASE"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            full_control=_bool(os.getenv("JARVIS_FULL_CONTROL"), False),
            repo_path=Path(os.getenv("JARVIS_REPO_PATH", ".")).resolve(),
            voice=_bool(os.getenv("JARVIS_VOICE"), False),
            wakeword=os.getenv("JARVIS_WAKEWORD", "hey_jarvis"),
            piper_voice=os.getenv("JARVIS_PIPER_VOICE", "en_US-amy-medium"),
            data_dir=Path(os.getenv("JARVIS_DATA_DIR", "./data")).resolve(),
        )
        c.data_dir.mkdir(parents=True, exist_ok=True)
        return c
