"""Test that the self-improvement agent validates and rejects bad proposals."""
from pathlib import Path
import tempfile

from jarvis.agents.self_improvement import SelfImprovementAgent, _extract_json
from jarvis.core.approval import ApprovalGate


class _Bus:
    def publish(self, *a, **k): pass


class _LLM:
    def complete(self, *a, **k): return '{"title":"x","rationale":"y","changes":[]}'


def test_protected_paths_rejected():
    agent = SelfImprovementAgent(_LLM(), ApprovalGate(), Path("."), _Bus())
    ok, why = agent.validate({"changes": [{"path": "jarvis/jarvis/core/approval.py", "new_content": "x"}]})
    assert not ok
    assert "protected" in why


def test_paths_outside_repo_rejected():
    agent = SelfImprovementAgent(_LLM(), ApprovalGate(), Path("."), _Bus())
    ok, why = agent.validate({"changes": [{"path": "../etc/passwd", "new_content": "x"}]})
    assert not ok


def test_extract_json_handles_fenced():
    out = _extract_json('```json\n{"a":1}\n```')
    assert out == {"a": 1}


def test_extract_json_handles_prose():
    out = _extract_json('here you go: {"a":2} done')
    assert out == {"a": 2}
