"""Self-Improvement Agent: proposes patches to Jarvis's own codebase, then asks for approval."""
from __future__ import annotations

import json
import re
from pathlib import Path

from jarvis.core.approval import ActionRequest, ApprovalGate, Risk

PROPOSE_SYS = """You are Jarvis's Self-Improvement Agent. You read your own source
code and propose ONE small, safe, testable improvement.

Output strict JSON, no prose:
{
  "title": "short title",
  "rationale": "why",
  "changes": [
    {"path": "relative/path.py", "new_content": "full new file content"}
  ],
  "tests_added": ["tests/test_x.py"]   // optional
}

Rules:
- Only modify files under jarvis/jarvis/ or jarvis/tests/.
- Never modify jarvis/jarvis/core/approval.py or jarvis/jarvis/selfimprove/.
- Keep diffs small. Prefer adding tests, docstrings, type hints, or fixing obvious bugs.
- If nothing is worth changing, return {"title":"noop","rationale":"...","changes":[]}.
"""


PROTECTED = {
    "jarvis/jarvis/core/approval.py",
    "jarvis/jarvis/selfimprove/loop.py",
    "jarvis/jarvis/selfimprove/git_apply.py",
    "jarvis/jarvis/selfimprove/sandbox.py",
    "jarvis/jarvis/agents/self_improvement.py",
}


class SelfImprovementAgent:
    def __init__(self, llm, approval: ApprovalGate, repo_path: Path, bus):
        self.llm = llm
        self.approval = approval
        self.repo_path = Path(repo_path)
        self.bus = bus

    def propose_summary(self, hint: str) -> str:
        proposal = self.propose(hint)
        return f"Proposal: {proposal.get('title')}\n\n{proposal.get('rationale','')}\n\n" \
               f"Files: {[c['path'] for c in proposal.get('changes', [])]}"

    def propose(self, hint: str | None = None) -> dict:
        # Gather a snapshot of source for context (capped)
        snippets = []
        root = self.repo_path
        for p in sorted((root / "jarvis").rglob("*.py")):
            try:
                rel = p.relative_to(root)
                text = p.read_text(encoding="utf-8")
                if len(text) > 4000:
                    text = text[:4000] + "\n# ...truncated..."
                snippets.append(f"### FILE: {rel}\n{text}")
            except Exception:
                continue
            if sum(len(s) for s in snippets) > 30000:
                break
        context = "\n\n".join(snippets)

        user = f"Hint from operator: {hint or '(none)'}\n\nCurrent source:\n{context}"
        raw = self.llm.complete(user, system=PROPOSE_SYS, temperature=0.2, max_tokens=3000)
        return _extract_json(raw)

    def validate(self, proposal: dict) -> tuple[bool, str]:
        for ch in proposal.get("changes", []):
            path = ch.get("path", "")
            if not path.startswith("jarvis/"):
                return False, f"path outside repo: {path}"
            if path in PROTECTED:
                return False, f"protected path: {path}"
            if ".." in Path(path).parts:
                return False, f"path traversal: {path}"
            if "new_content" not in ch:
                return False, f"missing new_content for {path}"
        return True, "ok"


def _extract_json(text: str) -> dict:
    # Try direct
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Find first {...} blob
        m = re.search(r"\{.*\}", text, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
    return {"title": "parse_error", "rationale": text[:300], "changes": []}
