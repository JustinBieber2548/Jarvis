"""Memory: SQLite for structured/episodic, ChromaDB for semantic (lazy)."""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any


SCHEMA = """
CREATE TABLE IF NOT EXISTS short_term (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS long_term (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    kind TEXT NOT NULL,        -- preference | fact | reflection | project | goal
    key TEXT,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS episodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    summary TEXT NOT NULL,
    success INTEGER NOT NULL DEFAULT 1,
    payload TEXT
);
"""


class MemoryStore:
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data_dir / "jarvis.sqlite"
        self.con = sqlite3.connect(self.db_path, check_same_thread=False)
        self.con.executescript(SCHEMA)
        self.con.commit()
        self._chroma = None

    # ---- short-term (conversation buffer) ----
    def add_short(self, role: str, content: str):
        self.con.execute(
            "INSERT INTO short_term (ts, role, content) VALUES (?, ?, ?)",
            (time.time(), role, content),
        )
        self.con.commit()

    def recent(self, n: int = 20) -> list[dict]:
        cur = self.con.execute(
            "SELECT role, content, ts FROM short_term ORDER BY id DESC LIMIT ?", (n,)
        )
        return [{"role": r, "content": c, "ts": t} for r, c, t in reversed(cur.fetchall())]

    # ---- long-term ----
    def remember(self, kind: str, value: str, key: str | None = None):
        self.con.execute(
            "INSERT INTO long_term (ts, kind, key, value) VALUES (?, ?, ?, ?)",
            (time.time(), kind, key, value),
        )
        self.con.commit()

    def recall(self, kind: str | None = None, limit: int = 50) -> list[dict]:
        if kind:
            cur = self.con.execute(
                "SELECT kind, key, value, ts FROM long_term WHERE kind=? ORDER BY id DESC LIMIT ?",
                (kind, limit),
            )
        else:
            cur = self.con.execute(
                "SELECT kind, key, value, ts FROM long_term ORDER BY id DESC LIMIT ?", (limit,)
            )
        return [{"kind": k, "key": kk, "value": v, "ts": t} for k, kk, v, t in cur.fetchall()]

    # ---- episodic ----
    def episode(self, summary: str, success: bool = True, payload: Any = None):
        self.con.execute(
            "INSERT INTO episodes (ts, summary, success, payload) VALUES (?, ?, ?, ?)",
            (time.time(), summary, int(success), json.dumps(payload) if payload else None),
        )
        self.con.commit()

    # ---- semantic (lazy chroma) ----
    def _chroma_collection(self):
        if self._chroma is None:
            try:
                import chromadb
                client = chromadb.PersistentClient(path=str(self.data_dir / "chroma"))
                self._chroma = client.get_or_create_collection("jarvis_semantic")
            except Exception as e:
                print(f"[memory] chroma unavailable: {e}")
                self._chroma = False
        return self._chroma if self._chroma else None

    def semantic_add(self, doc_id: str, text: str, meta: dict | None = None):
        col = self._chroma_collection()
        if not col:
            return
        col.upsert(ids=[doc_id], documents=[text], metadatas=[meta or {}])

    def semantic_search(self, query: str, n: int = 5) -> list[dict]:
        col = self._chroma_collection()
        if not col:
            return []
        res = col.query(query_texts=[query], n_results=n)
        out = []
        for i, doc in enumerate(res.get("documents", [[]])[0]):
            out.append({
                "id": res["ids"][0][i],
                "text": doc,
                "meta": res["metadatas"][0][i] if res.get("metadatas") else {},
            })
        return out
