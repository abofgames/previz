"""Look development — the film's visual language, plus a lookboard to show it.

The lookboard is assembled with Pillow rather than generated: it is a contact
sheet of the director's own reference frames beside the extracted palette. That
costs no image quota, and it is more honest than a synthesized "vibe" image —
what the user uploaded is what conditions every panel downstream.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from PIL import Image, ImageDraw

from ..models import LookBlock
from ..project import ProjectPaths
from . import entity_research

log = logging.getLogger("steps.look_dev")

_SHEET = (1024, 576)
_SWATCH_H = 96
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


def look_refs(paths: ProjectPaths) -> list[Path]:
    """The director's uploaded reference frames — attached to every image call
    so the rendering style stays locked across plates and panels."""
    d = paths.look_refs_dir
    if not d.exists():
        return []
    return sorted(p for p in d.iterdir() if p.suffix.lower() in IMAGE_SUFFIXES)


async def run(
    paths: ProjectPaths, text_client, look_note: str = "", *,
    search_client=None, force: bool = False,
) -> LookBlock:
    dest = paths.look_block
    if dest.exists() and paths.lookboard_image.exists() and not force:
        log.info("look_dev: reusing %s", dest)
        return LookBlock.model_validate_json(dest.read_text())

    paths.look_note.parent.mkdir(parents=True, exist_ok=True)
    paths.look_note.write_text(look_note)

    refs = look_refs(paths)

    # A look note names references the model only half-knows ("like Michael
    # Mann"). Searching turns the name into technique — source placement,
    # contrast ratio, lens habits — before the look block is written.
    note = look_note
    if search_client is not None:
        cites = await entity_research.research_influences(
            paths, look_note, search_client=search_client
        )
        sourced = entity_research.as_notes(cites, "Cinematography research")
        if sourced:
            note = f"{look_note}\n\n{sourced}"

    data = await text_client.look_block(refs, note)
    block = LookBlock.model_validate(data)

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(block.model_dump(), indent=2))
    _build_lookboard(paths.lookboard_image, refs, block)
    log.info("look_dev: %d refs, %d palette entries", len(refs), len(block.palette))
    return block


def _build_lookboard(dest: Path, refs: list[Path], block: LookBlock) -> None:
    """Contact sheet: reference frames on top, palette swatches beneath."""
    sheet = Image.new("RGB", _SHEET, (14, 14, 18))
    frame_h = _SHEET[1] - _SWATCH_H

    usable = refs[:4]
    if usable:
        cell_w = _SHEET[0] // len(usable)
        for i, p in enumerate(usable):
            try:
                thumb = Image.open(p).convert("RGB")
            except OSError:
                log.warning("lookboard: cannot open %s", p)
                continue
            thumb = _cover(thumb, (cell_w - 8, frame_h - 8))
            sheet.paste(thumb, (i * cell_w + 4, 4))
    else:
        draw = ImageDraw.Draw(sheet)
        draw.text(
            (24, 24),
            "No reference frames uploaded.\nLook derived from the director's note:\n"
            f"{block.mood}\n{block.lighting}",
            fill=(200, 200, 210),
        )

    swatches = block.palette[:6] or ["#202028"]
    sw_w = _SHEET[0] // len(swatches)
    draw = ImageDraw.Draw(sheet)
    for i, name in enumerate(swatches):
        x0 = i * sw_w
        draw.rectangle(
            [(x0, frame_h), (x0 + sw_w - 2, _SHEET[1])],
            fill=_as_rgb(name),
        )

    dest.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(dest, "PNG")


def _cover(img: Image.Image, box: tuple[int, int]) -> Image.Image:
    """Scale-and-crop to fill `box` without distorting the frame."""
    bw, bh = max(box[0], 1), max(box[1], 1)
    scale = max(bw / img.width, bh / img.height)
    resized = img.resize((max(int(img.width * scale), bw), max(int(img.height * scale), bh)))
    left = (resized.width - bw) // 2
    top = (resized.height - bh) // 2
    return resized.crop((left, top, left + bw, top + bh))


def _as_rgb(name: str) -> tuple[int, int, int]:
    """Palette entries come back as hex or as prose ("sodium orange"). Hex is
    used directly; prose is hashed to a stable colour so the board still reads
    as a palette rather than failing."""
    s = name.strip()
    if s.startswith("#") and len(s) in (4, 7):
        try:
            if len(s) == 4:
                return tuple(int(c * 2, 16) for c in s[1:])  # type: ignore[return-value]
            return (int(s[1:3], 16), int(s[3:5], 16), int(s[5:7], 16))
        except ValueError:
            pass
    import hashlib

    h = hashlib.md5(s.encode()).digest()
    return (30 + h[0] % 180, 30 + h[1] % 180, 30 + h[2] % 180)
