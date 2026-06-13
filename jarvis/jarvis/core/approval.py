"""Human-in-the-loop approval gate. Every restricted action passes through here."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable

from rich.console import Console
from rich.panel import Panel

console = Console()


class Risk(str, Enum):
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ActionRequest:
    action: str
    target: str
    risk: Risk
    details: str = ""
    category: str = "generic"  # code_change | file_delete | deploy | browser | desktop | self_modify


class ApprovalGate:
    """CLI-driven approval. Override `prompt` for GUI/voice approvals later."""

    def __init__(self, auto_approve_safe: bool = True, full_control: bool = False):
        self.auto_approve_safe = auto_approve_safe
        self.full_control = full_control
        # Once-per-session unlock for full_control mode
        self._full_control_confirmed = False
        self._audit: list[tuple[ActionRequest, bool]] = []

    def request(self, req: ActionRequest) -> bool:
        if req.risk == Risk.SAFE and self.auto_approve_safe:
            self._audit.append((req, True))
            return True

        if self.full_control and req.category != "self_modify":
            if not self._full_control_confirmed:
                ok = self._prompt(req, prefix="[FULL CONTROL MODE — confirm once]")
                self._full_control_confirmed = ok
                self._audit.append((req, ok))
                return ok
            self._audit.append((req, True))
            return True

        ok = self._prompt(req)
        self._audit.append((req, ok))
        return ok

    def _prompt(self, req: ActionRequest, prefix: str = "") -> bool:
        body = (
            f"[bold]Action:[/bold]   {req.action}\n"
            f"[bold]Target:[/bold]   {req.target}\n"
            f"[bold]Risk:[/bold]     {req.risk.value}\n"
            f"[bold]Category:[/bold] {req.category}\n"
        )
        if req.details:
            body += f"\n{req.details}"
        title = "Jarvis would like to perform the following action"
        if prefix:
            title = f"{prefix} {title}"
        console.print(Panel(body, title=title, border_style="yellow"))
        try:
            answer = input("Approve? [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return False
        return answer in {"y", "yes"}

    def audit(self) -> list[tuple[ActionRequest, bool]]:
        return list(self._audit)
