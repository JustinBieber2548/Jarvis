"""Coding agent: drafts code. Writes go through approval."""
from __future__ import annotations

from pathlib import Path

from jarvis.core.approval import ActionRequest, ApprovalGate, Risk

SYS = """You are Jarvis's Coding Agent. Produce minimal, correct code.
When asked to modify a file, output a complete replacement, prefixed with the file path
on its own line like: `### FILE: path/to/file.py`
Then the code in a fenced block. No prose unless asked."""


class CodingAgent:
    def __init__(self, llm, approval: ApprovalGate, repo_path: Path):
        self.llm = llm
        self.approval = approval
        self.repo_path = Path(repo_path)

    def handle(self, request: str) -> str:
        draft = self.llm.complete(request, system=SYS, temperature=0.2, max_tokens=2000)
        # Don't auto-apply. Return draft; user can then `/apply` (future) or paste manually.
        return f"Draft (not applied):\n\n{draft}"

    def write_file(self, rel_path: str, content: str) -> str:
        target = (self.repo_path / rel_path).resolve()
        if not str(target).startswith(str(self.repo_path)):
            return "Refused: path escapes repo."
        ok = self.approval.request(ActionRequest(
            action="write_file", target=rel_path, risk=Risk.MEDIUM,
            category="code_change",
            details=f"{len(content)} bytes",
        ))
        if not ok:
            return "Cancelled."
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"Wrote {rel_path}"
