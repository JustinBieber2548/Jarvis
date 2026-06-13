"""Tests for memory store."""
from pathlib import Path
import tempfile

from jarvis.memory.store import MemoryStore


def test_short_term_roundtrip():
    with tempfile.TemporaryDirectory() as d:
        m = MemoryStore(Path(d))
        m.add_short("user", "hello")
        m.add_short("jarvis", "hi")
        recent = m.recent(10)
        assert len(recent) == 2
        assert recent[0]["role"] == "user"
        assert recent[1]["content"] == "hi"


def test_long_term_kinds():
    with tempfile.TemporaryDirectory() as d:
        m = MemoryStore(Path(d))
        m.remember("fact", "the user lives in NYC")
        m.remember("preference", "prefers dark mode")
        facts = m.recall(kind="fact")
        prefs = m.recall(kind="preference")
        assert len(facts) == 1 and len(prefs) == 1
        assert "NYC" in facts[0]["value"]


def test_episode():
    with tempfile.TemporaryDirectory() as d:
        m = MemoryStore(Path(d))
        m.episode("did a thing", success=True, payload={"x": 1})
