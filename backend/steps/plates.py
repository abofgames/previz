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
from . import entity_research
from .look_dev import look_refs

log = logging.getLogger("steps.plates")

PLATE_SIZE = (768, 1024)      # portrait — a standing figure or a room elevation


async def gen_character(
    paths: ProjectPaths,
    character: Character,
    *,
    text_client,
    image_client,
    search_client=None,
    look: LookBlock | None = None,
    dossier: ResearchDossier | None = None,
    period: str = "",
    force: bool = False,
) -> list:
    """Draw this character's reference plate. Returns the sources used."""
    ref_id = ids.char_ref(character.id)
    if paths.ref_image(ref_id).exists() and not force:
        log.info("plate: reusing %s", ref_id)
        return entity_research.cached(paths, "char", character.id)

    cites = (
        await entity_research.research_character(
            paths, character, search_client=search_client, period=period
        )
        if search_client is not None
        else []
    )

    extra = ""
    if character.wardrobe:
        extra += f"Wardrobe: {character.wardrobe}\n"
    if character.visual_traits:
        extra += f"Must show: {', '.join(character.visual_traits)}\n"
    if character.continuity_anchors:
        extra += f"Continuity anchors (never omit): {', '.join(character.continuity_anchors)}\n"

    await _gen_plate(
        paths, ref_id, "character",
        name=character.name, description=character.description, extra=extra,
        text_client=text_client, image_client=image_client,
        look=look, dossier=dossier, force=force,
        sourced=entity_research.as_notes(cites, "Wardrobe research"),
    )
    return cites


async def gen_location(
    paths: ProjectPaths,
    location: Location,
    *,
    text_client,
    image_client,
    search_client=None,
    look: LookBlock | None = None,
    dossier: ResearchDossier | None = None,
    period: str = "",
    force: bool = False,
) -> list:
    """Draw this location's reference plate. Returns the sources used."""
    ref_id = ids.loc_ref(location.id)
    if paths.ref_image(ref_id).exists() and not force:
        log.info("plate: reusing %s", ref_id)
        return entity_research.cached(paths, "loc", location.id)

    cites = (
        await entity_research.research_location(
            paths, location, search_client=search_client, period=period
        )
        if search_client is not None
        else []
    )

    extra = ""
    if location.key_features:
        extra += f"Must show: {', '.join(location.key_features)}\n"
    if location.time_of_day:
        extra += f"Time of day: {location.time_of_day}\n"
    if location.lighting:
        extra += f"Lighting: {location.lighting}\n"

    await _gen_plate(
        paths, ref_id, "location",
        name=location.name, description=location.description, extra=extra,
        text_client=text_client, image_client=image_client,
        look=look, dossier=dossier, force=force,
        sourced=entity_research.as_notes(cites, "Location research"),
    )
    return cites


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
    sourced: str = "",
) -> None:
    image_path = paths.ref_image(ref_id)
    prompt_path = paths.ref_prompt(ref_id)
    if prompt_path.exists() and not force:
        prompt = prompt_path.read_text()
    else:
        research = research_summary(dossier.model_dump() if dossier else None)
        if sourced:
            # Entity-specific sources sit alongside the scene dossier — they
            # are far more targeted, so they go last where they carry most
            # weight in the prompt.
            research = f"{research}\n\n{sourced}" if research != "(none)" else sourced
        prompt = await text_client.plate_prompt(
            kind=kind, name=name, description=description, extra=extra,
            look_summary=look_summary(look.model_dump() if look else None),
            research_summary=research,
        )
        prompt_path.parent.mkdir(parents=True, exist_ok=True)
        prompt_path.write_text(prompt)

    await image_client.generate(
        image_path, prompt, size=PLATE_SIZE, refs=look_refs(paths)
    )
    log.info("plate: wrote %s", image_path.name)
