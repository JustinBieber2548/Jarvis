"""Router agent: picks which downstream agent (or direct LLM) handles a request."""
from __future__ import annotations

import re

SYSTEM = """You are Jarvis's Router. Given a user request, reply with EXACTLY ONE label:
- chat         (general talk / questions)
- plan         (multi-step goal that needs breaking down)
- code         (write/modify code)
- selfimprove  (improve Jarvis itself)
- remember     (store a fact/preference)
- recall       (look up something from memory)
No explanation. Just the label."""


class RouterAgent:
    def __init__(self, llm, agents: dict):
        self.llm = llm
        self.agents = agents

    def route(self, user_text: str) -> str:
        label = self._classify(user_text)
        if label == "plan":
            return self.agents["planner"].plan(user_text)
        if label == "code":
            return self.agents["coding"].handle(user_text)
        if label == "selfimprove":
            return self.agents["selfimprove"].propose_summary(user_text)
        if label == "remember":
            return self.agents["memory"].remember_from_text(user_text)
        if label == "recall":
            return self.agents["memory"].recall_for(user_text)
        # default: chat with memory context
        return self.agents["memory"].chat(user_text)

    def _classify(self, text: str) -> str:
        # Quick heuristics first (cheap, no LLM round trip for obvious cases)
        t = text.lower().strip()
        if t.startswith(("remember ", "note that ", "save:")):
            return "remember"
        if t.startswith(("recall ", "what did i ", "do you remember")):
            return "recall"
        if any(k in t for k in ["improve yourself", "self-improve", "rewrite yourself", "self improve"]):
            return "selfimprove"
        if re.search(r"\b(write|create|fix|refactor|debug)\b.*\b(code|function|file|module|class)\b", t):
            return "code"

        try:
            out = self.llm.complete(text, system=SYSTEM, temperature=0.0, max_tokens=8)
            label = out.strip().split()[0].lower().strip(".,:")
            if label in {"chat", "plan", "code", "selfimprove", "remember", "recall"}:
                return label
        except Exception:
            pass
        return "chat"
