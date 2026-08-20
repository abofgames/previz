"""Per-scene visual research, persisted as a citable dossier."""
from __future__ import annotations

import asyncio
import json
import logging

from ..agents.research import ensure_adk_credentials, research_scene
from ..models import ResearchDossier, ScriptBreakdown
from ..project import ProjectPaths

log = logging.getLogger("steps.research")

# One scene at a time. The free tier allows 5 Gemini requests/minute and a
# single research agent spends 3-4 of them on its own turns, so two concurrent
# agents cannot both finish — measured, not guessed.
_SCENE_CONCURRENCY = 1


async def run_all(
    paths: ProjectPaths,
    breakdown: ScriptBreakdown,
    *,
    text_client,
    search_client,
    look_note: str = "",
    force: bool = False,
) -> dict[str, ResearchDossier]:
    """Research every scene. Returns {scene_id: dossier}."""
    ensure_adk_credentials()
    paths.research_dir.mkdir(parents=True, exist_ok=True)
    sem = asyncio.Semaphore(_SCENE_CONCURRENCY)

    async def one(scene) -> tuple[str, ResearchDossier]:
        async with sem:
            return scene.id, await run_scene(
                paths, scene, breakdown,
                text_client=text_client, search_client=search_client,
                look_note=look_note, force=force,
            )

    results = await asyncio.gather(
        *(one(s) for s in breakdown.scenes), return_exceptions=True
    )

    dossiers: dict[str, ResearchDossier] = {}
    for scene, outcome in zip(breakdown.scenes, results):
        if isinstance(outcome, BaseException):
            # One scene's research failing must not sink the whole production —
            # panels still generate, just without grounded direction.
            log.warning("research failed for %s: %s", scene.id, outcome)
            dossiers[scene.id] = ResearchDossier(scene_id=scene.id)
            continue
        scene_id, dossier = outcome
        dossiers[scene_id] = dossier
    return dossiers


async def run_scene(
    paths: ProjectPaths,
    scene,
    breakdown: ScriptBreakdown,
    *,
    text_client,
    search_client,
    look_note: str = "",
    force: bool = False,
) -> ResearchDossier:
    dest = paths.dossier(scene.id)
    if dest.exists() and not force:
        log.info("research: reusing %s", dest.name)
        return ResearchDossier.model_validate_json(dest.read_text())

    scene_dict = scene.model_dump()

    if getattr(text_client, "mock", False):
        # No Gemini key: fall back to the canned dossier so the graph still
        # completes and the UI stays demoable.
        dossier = ResearchDossier.model_validate(
            await text_client.research(scene_dict, look_note)
        )
    else:
        dossier = await research_scene(
            scene_dict,
            search_client=search_client,
            look_note=look_note,
            characters=_names(breakdown.characters, scene.character_ids),
            location=_location(breakdown, scene.location_id),
        )

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(dossier.model_dump(), indent=2))
    return dossier


def load(paths: ProjectPaths, scene_id: str) -> ResearchDossier | None:
    p = paths.dossier(scene_id)
    if not p.exists():
        return None
    try:
        return ResearchDossier.model_validate_json(p.read_text())
    except ValueError:
        return None


def _names(characters, ids: list[str]) -> str:
    by_id = {c.id: c for c in characters}
    return ", ".join(
        f"{by_id[i].name} ({by_id[i].description})" for i in ids if i in by_id
    )


def _location(breakdown: ScriptBreakdown, loc_id: str) -> str:
    loc = next((l for l in breakdown.locations if l.id == loc_id), None)
    return f"{loc.name} — {loc.description}" if loc else ""
