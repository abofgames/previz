"""Script breakdown — screenplay in, structured production data out."""
from __future__ import annotations

import json
import logging

from ..models import ScriptBreakdown
from ..project import ProjectPaths

log = logging.getLogger("steps.breakdown")


async def run(
    paths: ProjectPaths, text_client, script: str, *, force: bool = False
) -> ScriptBreakdown:
    """Write ``breakdown.json``. Skips the model call when the artifact already
    exists and the caller hasn't forced a re-run."""
    dest = paths.breakdown
    if dest.exists() and not force:
        log.info("breakdown: reusing %s", dest)
        return ScriptBreakdown.model_validate_json(dest.read_text())

    paths.script.parent.mkdir(parents=True, exist_ok=True)
    paths.script.write_text(script)

    data = await text_client.breakdown(script)
    breakdown = _repair(ScriptBreakdown.model_validate(data))

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(breakdown.model_dump(), indent=2))
    log.info(
        "breakdown: %d characters, %d locations, %d scenes, %d shots",
        len(breakdown.characters), len(breakdown.locations),
        len(breakdown.scenes), len(breakdown.shots),
    )
    return breakdown


def _repair(b: ScriptBreakdown) -> ScriptBreakdown:
    """Drop dangling references before they reach the graph.

    A model occasionally emits a shot pointing at a character or location id it
    never defined. Building a graph edge to a node that doesn't exist orphans
    the card in the UI, so the references are pruned here rather than defended
    against in five downstream places.
    """
    char_ids = {c.id for c in b.characters}
    loc_ids = {l.id for l in b.locations}
    scene_ids = {s.id for s in b.scenes}

    for scene in b.scenes:
        dropped = [c for c in scene.character_ids if c not in char_ids]
        if dropped:
            log.warning("scene %s: dropping unknown character ids %s", scene.id, dropped)
        scene.character_ids = [c for c in scene.character_ids if c in char_ids]
        if scene.location_id and scene.location_id not in loc_ids:
            log.warning("scene %s: unknown location %r", scene.id, scene.location_id)
            scene.location_id = ""

    kept = []
    for shot in b.shots:
        if shot.scene_id not in scene_ids:
            log.warning("shot %s: unknown scene %r, dropping", shot.id, shot.scene_id)
            continue
        shot.character_ids = [c for c in shot.character_ids if c in char_ids]
        if shot.location_id not in loc_ids:
            # Fall back to the parent scene's location rather than dropping the shot.
            parent = next((s for s in b.scenes if s.id == shot.scene_id), None)
            shot.location_id = parent.location_id if parent else ""
        kept.append(shot)
    b.shots = kept
    return b
