"""Planner agent: break a goal into numbered tasks."""
from __future__ import annotations

SYS = """You are Jarvis's Planner. Break the user's goal into 3-8 concrete, ordered steps.
Format strictly as:
1. ...
2. ...
No preamble."""


class PlannerAgent:
    def __init__(self, llm):
        self.llm = llm

    def plan(self, goal: str) -> str:
        return self.llm.complete(goal, system=SYS, temperature=0.2, max_tokens=600)
