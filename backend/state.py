from __future__ import annotations

import asyncio
from pathlib import Path
from typing import AsyncIterator

from .models import Graph, WSEvent


class EventBus:
    """In-process pub/sub. Producers publish WSEvents; subscribers receive them
    via an async iterator backed by an asyncio.Queue. Keeps the runner from
    knowing anything about WebSockets."""

    def __init__(self) -> None:
        self._subscribers: list[asyncio.Queue[WSEvent]] = []

    async def publish(self, event: WSEvent) -> None:
        for q in list(self._subscribers):
            await q.put(event)

    async def subscribe(self) -> AsyncIterator[WSEvent]:
        q: asyncio.Queue[WSEvent] = asyncio.Queue()
        self._subscribers.append(q)
        try:
            while True:
                yield await q.get()
        finally:
            self._subscribers.remove(q)


def load_graph(path: Path) -> Graph | None:
    if not path.exists():
        return None
    return Graph.model_validate_json(path.read_text())


def save_graph(path: Path, graph: Graph) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(graph.model_dump_json(indent=2))
