"""Desktop control via PyAutoGUI. Every action requires approval."""
from __future__ import annotations

from jarvis.core.approval import ActionRequest, ApprovalGate, Risk


class Desktop:
    def __init__(self, approval: ApprovalGate):
        self.approval = approval
        try:
            import pyautogui
            self.pg = pyautogui
            self.pg.FAILSAFE = True
        except ImportError:
            self.pg = None

    def _gate(self, action: str, target: str, risk: Risk = Risk.HIGH) -> bool:
        return self.approval.request(ActionRequest(
            action=action, target=target, risk=risk, category="desktop",
        ))

    def type_text(self, text: str) -> str:
        if not self.pg: return "pyautogui not installed"
        if not self._gate("type_text", text[:60]): return "cancelled"
        self.pg.typewrite(text, interval=0.02)
        return "typed"

    def click(self, x: int, y: int) -> str:
        if not self.pg: return "pyautogui not installed"
        if not self._gate("click", f"({x},{y})"): return "cancelled"
        self.pg.click(x, y); return "clicked"

    def hotkey(self, *keys: str) -> str:
        if not self.pg: return "pyautogui not installed"
        if not self._gate("hotkey", "+".join(keys)): return "cancelled"
        self.pg.hotkey(*keys); return "ok"

    def screenshot(self, path: str) -> str:
        if not self.pg: return "pyautogui not installed"
        # screenshot is read-only → low risk
        if not self._gate("screenshot", path, risk=Risk.LOW): return "cancelled"
        self.pg.screenshot(path); return path
