"""Reference plates — the continuity anchors every panel is drawn against.

One clean plate per character and per location, generated once and then
attached to every panel that features them. This is what stops the same
character arriving at shot 12 with a different face and coat than she had at
shot 3.
"""
from __future__ import annotations

import logging

from .. import ids
from ..clients.gemini import look_summary, research_summary
from ..models import Character, Location, LookBlock, ResearchDossier
from ..project import ProjectPaths
from .look_dev import look_refs

log = logging.getLogger("steps.plates")

PLATE_SIZE = (768, 1024)      # portrait — a standing figure or a room elevation


async def gen_character(
    paths: ProjectPaths,
    character: Character,
    *,
    text_client,
    image_client,
    look: LookBlock | None = None,
    dossier: ResearchDossier | None = None,
    force: bool = False,
) -> None:
    extra = ""
    if character.wardrobe:
        extra += f"Wardrobe: {character.wardrobe}\n"
    if character.visual_traits:
        extra += f"Must show: {', '.join(character.visual_traits)}\n"
    if character.continuity_anchors:
        extra += f"Continuity anchors (never omit): {', '.join(character.continuity_anchors)}\n"

    await _gen_plate(
        paths, ids.char_ref(character.id), "character",
        name=character.name, description=character.description, extra=extra,
        text_client=text_client, image_client=image_client,
        look=look, dossier=dossier, force=force,
    )


async def gen_location(
    paths: ProjectPaths,
    location: Location,
    *,
    text_client,
    image_client,
    look: LookBlock | None = None,
    dossier: ResearchDossier | None = None,
    force: bool = False,
) -> None:
    extra = ""
    if location.key_features:
        extra += f"Must show: {', '.join(location.key_features)}\n"
    if location.time_of_day:
        extra += f"Time of day: {location.time_of_day}\n"
    if location.lighting:
        extra += f"Lighting: {location.lighting}\n"

    await _gen_plate(
        paths, ids.loc_ref(location.id), "location",
        name=location.name, description=location.description, extra=extra,
        text_client=text_client, image_client=image_client,
        look=look, dossier=dossier, force=force,
    )


async def _gen_plate(
    paths: ProjectPaths,
    ref_id: str,
    kind: str,
    *,
    name: str,
    description: str,
    extra: str,
    text_client,
    image_client,
    look: LookBlock | None,
    dossier: ResearchDossier | None,
    force: bool,
) -> None:
    image_path = paths.ref_image(ref_id)
    prompt_path = paths.ref_prompt(ref_id)
    if image_path.exists() and not force:
        log.info("plate: reusing %s", image_path.name)
        return

    if prompt_path.exists() and not force:
        prompt = prompt_path.read_text()
    else:
        prompt = await text_client.plate_prompt(
            kind=kind, name=name, description=description, extra=extra,
            look_summary=look_summary(look.model_dump() if look else None),
            research_summary=research_summary(dossier.model_dump() if dossier else None),
        )
        prompt_path.parent.mkdir(parents=True, exist_ok=True)
        prompt_path.write_text(prompt)

    await image_client.generate(
        image_path, prompt, size=PLATE_SIZE, refs=look_refs(paths)
    )
    log.info("plate: wrote %s", image_path.name)
