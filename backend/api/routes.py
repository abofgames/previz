from __future__ import annotations

from fastapi import APIRouter, File, Form, UploadFile
from pydantic import BaseModel

from ..runner import get_runner

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return {"ok": True}


@router.post("/projects/{project}/start")
async def start_production(
    project: str,
    script: str = Form(""),
    look_note: str = Form(""),
    look_refs: list[UploadFile] = File(default=[]),
) -> dict:
    """Kick off breakdown + look development.

    Multipart because the look references are image uploads. Panel generation
    is NOT started here — panels are click-to-generate so a run drains no image
    quota until the user asks for a specific plate or shot.
    """
    runner = get_runner(project)
    refs_dir = runner.paths.look_refs_dir
    refs_dir.mkdir(parents=True, exist_ok=True)

    # Wipe prior uploads so look_dev sees only what was submitted now.
    for old in refs_dir.iterdir():
        if old.is_file():
            old.unlink()

    saved = 0
    for f in look_refs:
        if not f.filename:
            continue
        (refs_dir / f.filename).write_bytes(await f.read())
        saved += 1

    await runner.start(script, look_note)
    return {"started": True, "look_refs_saved": saved}


class RetryBody(BaseModel):
    node_id: str


@router.post("/projects/{project}/retry")
async def retry_node(project: str, body: RetryBody) -> dict:
    """Generate or regenerate a single card (plate, panel, or animatic)."""
    runner = get_runner(project)
    await runner.retry(body.node_id)
    return {"retried": body.node_id}


@router.get("/projects/{project}/graph")
async def graph(project: str) -> dict:
    return get_runner(project).snapshot().model_dump()
