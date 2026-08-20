"""Storyboard panels — the actual deliverable.

Each panel is generated with the full reference chain attached: the director's
look frames, the plate for every character in the shot, and the plate for its
location. The text prompt then only has to describe framing and staging, which
is the part a storyboard is actually for.
"""
from __future__ import annotations

import logging
from pathlib import Path

from .. import ids
from ..clients.gemini import research_summary
from ..models import ResearchDossier, ScriptBreakdown, Shot
from ..project import ProjectPaths
from .look_dev import look_refs

log = logging.getLogger("steps.panels")

PANEL_SIZE = (1024, 576)      # 16:9 — panels are frames, not pages


def panel_refs(paths: ProjectPaths, shot: Shot) -> list[Path]:
    """Reference images for one shot, most-specific last.

    Order matters: the look frames set rendering, then the location fixes the
    space, then the character plates fix who is in it. Plates that haven't been
    generated yet are simply absent — the panel still draws, just with weaker
    continuity, which is better than blocking on them.
    """
    refs = list(look_refs(paths))
    loc = paths.ref_image(ids.loc_ref(shot.location_id)) if shot.location_id else None
    if loc is not None and loc.exists():
        refs.append(loc)
    for cid in shot.character_ids:
        p = paths.ref_image(ids.char_ref(cid))
        if p.exists():
            refs.append(p)
    return refs


async def gen_panel(
    paths: ProjectPaths,
    shot: Shot,
    breakdown: ScriptBreakdown,
    *,
    text_client,
    image_client,
    dossier: ResearchDossier | None = None,
    force: bool = False,
) -> None:
    image_path = paths.shot_image(shot.id)
    prompt_path = paths.shot_prompt(shot.id)
    if image_path.exists() and not force:
        log.info("panel: reusing %s", image_path.name)
        return

    scene = next((s for s in breakdown.scenes if s.id == shot.scene_id), None)
    scene_dict = scene.model_dump() if scene else {}

    if prompt_path.exists() and not force:
        prompt = prompt_path.read_text()
    else:
        prompt = await text_client.panel_prompt(
            shot.model_dump(),
            scene_dict,
            research_summary=research_summary(dossier.model_dump() if dossier else None),
        )
        prompt_path.parent.mkdir(parents=True, exist_ok=True)
        prompt_path.write_text(prompt)

    refs = panel_refs(paths, shot)
    await image_client.generate(image_path, prompt, size=PANEL_SIZE, refs=refs)
    log.info("panel: wrote %s (%d refs)", image_path.name, len(refs))


async def gen_animatic(
    paths: ProjectPaths, shot: Shot, *, image_client, force: bool = False
) -> None:
    """Optional Veo pass: turn a finished panel into a moving shot."""
    dest = paths.animatic_video(shot.id)
    if dest.exists() and not force:
        return
    src = paths.shot_image(shot.id)
    if not src.exists():
        raise RuntimeError(f"generate the panel for {shot.id} before its animatic")
    motion = f"Camera: {shot.movement}. {shot.description}"
    await image_client.animate(src, dest, prompt=motion)
    log.info("animatic: wrote %s", dest.name)
