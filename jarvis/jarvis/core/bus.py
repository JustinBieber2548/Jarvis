"""Simple in-process event bus for cross-agent signals (reflection, telemetry)."""
from __future__ import annotations

from collections import defaultdict
from typing import Callable


class EventBus:
    def __init__(self):
        self._subs: dict[str, list[Callable]] = defaultdict(list)

    def subscribe(self, topic: str, fn: Callable):
        self._subs[topic].append(fn)

    def publish(self, topic: str, payload: dict):
        for fn in list(self._subs.get(topic, [])):
            try:
                fn(payload)
            except Exception as e:  # pragma: no cover
                print(f"[EventBus] {topic} subscriber failed: {e}")
