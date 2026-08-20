"""Targeted research for one character, one location, or the film's look.

Deliberately not an agent. The scene-level research agent in
``agents/research.py`` reasons about what to look up; these passes already know
exactly what they need, so they run a single Parallel search and hand the
excerpts to a Gemini call that was going to happen anyway — the plate prompt,
or the look block.

That costs one cheap search and **zero extra model calls**, which matters:
Parallel is $0.001 a query while the Gemini free tier allows 20 requests a day
per model. Research is the abundant resource here; reasoning is the scarce one.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from ..models import Character, Citation, Location
from ..project import ProjectPaths

log = logging.getLogger("steps.entity_research")

_MAX_CITED = 5


def _cache(paths: ProjectPaths, key: str) -> Path:
    return paths.research_dir / f"entity_{key}.json"


def _load(paths: ProjectPaths, key: str) -> list[Citation] | None:
    p = _cache(paths, key)
    if not p.exists():
        return None
    try:
        return [Citation.model_validate(c) for c in json.loads(p.read_text())]
    except (json.JSONDecodeError, ValueError):
        return None


def _save(paths: ProjectPaths, key: str, cites: list[Citation]) -> None:
    p = _cache(paths, key)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps([c.model_dump() for c in cites], indent=2))


async def _search(
    paths: ProjectPaths, key: str, search_client, objective: str,
    queries: list[str], *, force: bool = False,
) -> list[Citation]:
    if not force:
        cached = _load(paths, key)
        if cached is not None:
            return cached
    try:
        cites = await search_client.search(objective=objective, queries=queries)
    except Exception as exc:  # noqa: BLE001
        # Research is an enhancement, never a gate — a plate still draws
        # without it, just on the model's own assumptions.
        log.warning("entity research failed for %s: %s", key, exc)
        return []
    cites = cites[:_MAX_CITED]
    _save(paths, key, cites)
    log.info("entity research %s: %d sources", key, len(cites))
    return cites


async def research_character(
    paths: ProjectPaths, character: Character, *, search_client,
    period: str = "", force: bool = False,
) -> list[Citation]:
    """What this specific person would actually be wearing.

    Wardrobe is where searching most clearly beats the model's priors — it
    returns outfitters, trade writing and reporting with real garment names,
    rather than a generic "practical jacket".
    """
    era = period or "contemporary"
    role = character.description or character.name
    return await _search(
        paths, ids_key("char", character.id), search_client,
        objective=(
            f"Describe in words what {character.name} would realistically wear and "
            f"look like: {role}. Setting: {era}. Needed for costume design — "
            "specific garments, fabrics, silhouettes, wear and materials."
        ),
        queries=[
            f"{era} {role} clothing description",
            f"what {role} actually wear",
            f"{era} workwear garments fabrics",
        ],
        force=force,
    )


async def research_location(
    paths: ProjectPaths, location: Location, *, search_client,
    period: str = "", force: bool = False,
) -> list[Citation]:
    """What this kind of place actually looks like — materials and fittings."""
    era = period or "contemporary"
    return await _search(
        paths, ids_key("loc", location.id), search_client,
        objective=(
            f"Describe in words the architecture, materials, fittings and light of "
            f"a {location.name}: {location.description}. Setting: {era}. Needed for "
            "production design — surfaces, furniture, fixtures, wear."
        ),
        queries=[
            f"{location.name} interior architecture description",
            f"{era} {location.name} materials fittings",
            f"what a {location.name} looks like inside",
        ],
        force=force,
    )


async def research_influences(
    paths: ProjectPaths, look_note: str, *, search_client, force: bool = False,
) -> list[Citation]:
    """How the named influences actually shoot.

    A look note like "shot like Michael Mann" is a reference the model only
    half-knows. Searching turns it into specifics — sources, ratios, lens
    choices — which is the difference between imitating a name and imitating
    a technique.
    """
    note = (look_note or "").strip()
    if len(note) < 12:
        return []
    return await _search(
        paths, "look_influences", search_client,
        objective=(
            "Explain the concrete cinematography technique behind this look note, "
            "for a DP to reproduce: lighting sources and their placement, contrast "
            "ratio, colour treatment, lens and framing habits. "
            f"Look note: {note}"
        ),
        queries=[
            f"{note[:70]} cinematography technique",
            f"{note[:70]} lighting setup how shot",
            "cinematographer lighting contrast ratio breakdown",
        ],
        force=force,
    )


def cached(paths: ProjectPaths, kind: str, entity_id: str) -> list[Citation]:
    """Sources previously found for this entity, for redisplay without a
    re-search when its plate is already drawn."""
    return _load(paths, ids_key(kind, entity_id)) or []


def as_notes(citations: list[Citation], heading: str) -> str:
    """Fold citations into a prompt-ready block.

    Excerpts are passed through verbatim but always under a heading that marks
    them as raw source material, so the model treats them as evidence to read
    rather than direction to copy.
    """
    if not citations:
        return ""
    lines = [f"{heading} (researched sources — extract the concrete visual facts):"]
    for c in citations:
        text = (c.excerpt or "").strip()
        if text:
            lines.append(f"- {text[:400]}")
    return "\n".join(lines) if len(lines) > 1 else ""


def ids_key(kind: str, entity_id: str) -> str:
    return f"{kind}_{entity_id}"
