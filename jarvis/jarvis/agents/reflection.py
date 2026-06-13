"""Reflection agent: after each interaction, evaluate and store lessons."""
from __future__ import annotations

SYS = """You are Jarvis's Reflection Agent. In ONE sentence, note what was learned or what to improve.
If nothing notable, reply exactly: SKIP"""


class ReflectionAgent:
    def __init__(self, llm, memory, bus):
        self.llm = llm
        self.memory = memory
        self.bus = bus

    def observe(self, user_text: str, reply: str):
        prompt = f"User said: {user_text}\nJarvis replied: {reply}"
        try:
            note = self.llm.complete(prompt, system=SYS, temperature=0.3, max_tokens=80)
        except Exception:
            return
        note = note.strip()
        if note and note.upper() != "SKIP":
            self.memory.remember("reflection", note)
            self.bus.publish("reflection.new", {"note": note})
