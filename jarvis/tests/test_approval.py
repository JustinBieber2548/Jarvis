"""Tests for approval gate."""
from jarvis.core.approval import ApprovalGate, ActionRequest, Risk


def test_safe_auto_approved():
    gate = ApprovalGate(auto_approve_safe=True)
    ok = gate.request(ActionRequest("read", "x", Risk.SAFE))
    assert ok is True


def test_self_modify_always_prompts(monkeypatch):
    gate = ApprovalGate(full_control=True)
    monkeypatch.setattr("builtins.input", lambda *a, **k: "n")
    ok = gate.request(ActionRequest("modify", "core.py", Risk.HIGH, category="self_modify"))
    assert ok is False


def test_full_control_first_time_prompts_then_auto(monkeypatch):
    gate = ApprovalGate(full_control=True)
    monkeypatch.setattr("builtins.input", lambda *a, **k: "y")
    assert gate.request(ActionRequest("write", "a.py", Risk.MEDIUM, category="code_change")) is True
    # Now full_control_confirmed → second request auto-approved without prompt
    def fail(*a, **k): raise AssertionError("should not prompt")
    monkeypatch.setattr("builtins.input", fail)
    assert gate.request(ActionRequest("write", "b.py", Risk.MEDIUM, category="code_change")) is True
