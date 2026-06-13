"""Memory agent: chat with context + explicit remember/recall."""
from __future__ import annotations


CHAT_SYSTEM = """You are Jarvis, a calm, capable AI companion.
You are local-first, persistent, and honest. If you don't know, say so.
Use the provided context if relevant; otherwise answer directly. Be concise."""


class MemoryAgent:
    def __init__(self, store, llm):
        self.store = store
        self.llm = llm

    def chat(self, user_text: str) -> str:
        history = self.store.recent(8)
        msgs = [{"role": "system", "content": CHAT_SYSTEM}]
        # Inject long-term facts as context
        facts = self.store.recall(kind="fact", limit=10) + self.store.recall(kind="preference", limit=10)
        if facts:
            ctx = "\n".join(f"- {f['value']}" for f in facts)
            msgs.append({"role": "system", "content": f"Known about the user:\n{ctx}"})
        for h in history[:-1]:  # exclude the just-added user message duplicate
            role = "user" if h["role"] == "user" else "assistant"
            msgs.append({"role": role, "content": h["content"]})
        msgs.append({"role": "user", "content": user_text})
        return self.llm.chat(msgs)

    def remember_from_text(self, text: str) -> str:
        # Strip leading verbs
        cleaned = text
        for prefix in ("remember that ", "remember ", "note that ", "save: "):
            if cleaned.lower().startswith(prefix):
                cleaned = cleaned[len(prefix):]
                break
        kind = "preference" if any(w in cleaned.lower() for w in ["i like", "i prefer", "i hate", "my favorite"]) else "fact"
        self.store.remember(kind, cleaned.strip())
        return f"Stored ({kind}): {cleaned.strip()}"

    def recall_for(self, query: str) -> str:
        hits = self.store.semantic_search(query, n=5) if False else []
        items = self.store.recall(limit=20)
        if not items:
            return "I don't have anything stored yet."
        lines = [f"- [{i['kind']}] {i['value']}" for i in items[:10]]
        return "Here's what I remember:\n" + "\n".join(lines)
