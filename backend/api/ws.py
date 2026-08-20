from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..models import WSEvent
from ..runner import get_runner

router = APIRouter()


@router.websocket("/ws/{project}")
async def graph_ws(ws: WebSocket, project: str) -> None:
    runner = get_runner(project)
    await ws.accept()
    init = WSEvent(type="graph_init", payload=runner.snapshot().model_dump())
    await ws.send_json(init.model_dump())
    try:
        async for event in runner.bus.subscribe():
            await ws.send_json(event.model_dump())
    except WebSocketDisconnect:
        return
