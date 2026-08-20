"""Generated look references, for when you don't have stills to upload.

Two paths, and the fallback is not a placeholder — it is the point:

- With a billed key, Gemini draws real reference frames in the chosen look.
- Otherwise (and on the free tier, where image quota is zero) the frames are
  composed procedurally from the preset's palette. That is not a stand-in
  image: a lighting study carrying the right palette, contrast ratio and
  falloff is genuinely most of what "look conditioning" transmits downstream,
  and it costs nothing.

Either way the files land in ``look_refs_dir`` and the rest of the pipeline
cannot tell the difference.
"""
from __future__ import annotations

import logging
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from ..project import ProjectPaths

log = logging.getLogger("steps.refgen")

FRAME_SIZE = (1024, 576)      # 16:9, same as a panel
DEFAULT_COUNT = 3

REF_PROMPT = """A single cinematic reference frame establishing a film's visual
language. No characters, no story, no recognisable location — this is a
lighting and colour study, the kind a DP shows a director.

The look: {note}

Dominant palette: {palette}

Show the light doing what that description says: the source, its direction,
its falloff, the depth of the shadows, the atmosphere in the air. An empty
space is fine — a corridor, a street, a room, a horizon. Photographic, shot on
a real lens, not an illustration.
"""


async def generate_look_refs(
    paths: ProjectPaths,
    preset: dict,
    *,
    image_client,
    count: int = DEFAULT_COUNT,
) -> list[Path]:
    """Fill ``look_refs_dir`` with ``count`` reference frames for this preset."""
    d = paths.look_refs_dir
    d.mkdir(parents=True, exist_ok=True)
    for old in d.glob("look_ref_*.png"):
        old.unlink()

    palette = [_as_rgb(c) for c in preset.get("palette", [])] or [(40, 44, 52)]
    note = preset.get("note", "")
    written: list[Path] = []

    for i in range(count):
        dest = d / f"look_ref_{i + 1}.png"
        try:
            await image_client.generate(
                dest,
                REF_PROMPT.format(note=note, palette=", ".join(preset.get("palette", []))),
                size=FRAME_SIZE,
            )
            log.info("look ref %d: generated", i + 1)
        except Exception as exc:  # noqa: BLE001
            # Quota, no key, refusal — any of them, the demo keeps working.
            log.info("look ref %d: falling back to composed frame (%s)", i + 1, exc)
            _compose(dest, palette, seed=f"{preset.get('name','')}-{i}")
        written.append(dest)

    return written


def _compose(dest: Path, palette: list[tuple[int, int, int]], *, seed: str) -> None:
    """Build a lighting study from a palette: a source, its falloff, some
    structure to read depth against, then vignette and grain."""
    rng = random.Random(seed)
    w, h = FRAME_SIZE
    shadow = min(palette, key=_luma)
    key = max(palette, key=_luma)
    mid = sorted(palette, key=_luma)[len(palette) // 2]

    img = Image.new("RGB", (w, h), shadow)
    px = img.load()
    assert px is not None

    # A single source, placed off-centre, falling off with distance.
    sx, sy = rng.uniform(0.15, 0.85) * w, rng.uniform(0.15, 0.6) * h
    reach = rng.uniform(0.45, 0.85) * w
    for y in range(0, h, 2):
        for x in range(0, w, 2):
            t = max(0.0, 1.0 - math.hypot(x - sx, y - sy) / reach) ** 2.2
            c = _mix(shadow, key, t)
            px[x, y] = c
            if x + 1 < w:
                px[x + 1, y] = c
            if y + 1 < h:
                px[x, y + 1] = c
                if x + 1 < w:
                    px[x + 1, y + 1] = c

    draw = ImageDraw.Draw(img, "RGBA")

    # Vertical structure — edges for the light to fall across, so depth reads.
    for _ in range(rng.randint(2, 5)):
        bx = rng.uniform(0, w)
        bw = rng.uniform(w * 0.03, w * 0.14)
        draw.rectangle([(bx, 0), (bx + bw, h)], fill=(*shadow, rng.randint(40, 110)))

    img = img.filter(ImageFilter.GaussianBlur(radius=rng.uniform(8, 16)))

    # Seat the frame on a reflective floor: mirror the lit half, dim it, and
    # fade it out with depth. A flat band reads as a rectangle; a falling-off
    # reflection reads as wet ground, which is what these looks describe.
    hy = int(rng.uniform(0.58, 0.78) * h)
    floor_h = h - hy
    if floor_h > 8:
        mirror = img.crop((0, max(0, hy - floor_h), w, hy)).transpose(
            Image.FLIP_TOP_BOTTOM
        )
        mirror = Image.blend(mirror, Image.new("RGB", mirror.size, shadow), 0.55)
        fade = Image.linear_gradient("L").resize((w, floor_h))
        img.paste(mirror, (0, hy), fade.point(lambda v: 255 - v))
        # A soft tint line where floor meets wall, not a hard step.
        glow = Image.new("RGB", (w, h), mid)
        band = Image.new("L", (w, h), 0)
        ImageDraw.Draw(band).rectangle([(0, hy - 3), (w, hy + 3)], fill=90)
        img = Image.composite(glow, img, band.filter(ImageFilter.GaussianBlur(12)))

    vig = Image.new("L", (w, h), 0)
    ImageDraw.Draw(vig).ellipse([(-w * 0.2, -h * 0.3), (w * 1.2, h * 1.3)], fill=255)
    img = Image.composite(
        img, Image.new("RGB", (w, h), shadow),
        vig.filter(ImageFilter.GaussianBlur(radius=w * 0.10)),
    )

    px = img.load()
    assert px is not None
    for y in range(h):
        for x in range(0, w, 3):
            n = rng.randint(-9, 9)
            r, g, b = px[x, y]
            px[x, y] = (_clamp(r + n), _clamp(g + n), _clamp(b + n))

    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, "PNG")


def _luma(c: tuple[int, int, int]) -> float:
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def _mix(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(_clamp(int(a[i] + (b[i] - a[i]) * t)) for i in range(3))  # type: ignore[return-value]


def _clamp(v: int) -> int:
    return 0 if v < 0 else 255 if v > 255 else v


def _as_rgb(name: str) -> tuple[int, int, int]:
    s = name.strip()
    if s.startswith("#") and len(s) == 7:
        try:
            return (int(s[1:3], 16), int(s[3:5], 16), int(s[5:7], 16))
        except ValueError:
            pass
    import hashlib

    d = hashlib.md5(s.encode()).digest()
    return (30 + d[0] % 180, 30 + d[1] % 180, 30 + d[2] % 180)
