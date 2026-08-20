"""Mock clients — the default when no API key is configured.

These exist so the whole app is demoable with zero credentials, and so a
drained daily quota never blocks development. The real clients subclass these
and override only the methods they actually implement, which means any method
not yet wired degrades to canned data instead of crashing the pipeline.
"""
from __future__ import annotations

import asyncio
import hashlib
import random
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw


def mime_for(path: Path) -> str:
    ext = path.suffix.lower().lstrip(".")
    if ext in ("jpg", "jpeg"):
        return "image/jpeg"
    if ext == "png":
        return "image/png"
    if ext == "webp":
        return "image/webp"
    return "image/jpeg"


_CANNED_BREAKDOWN = {
    "title": "COLD OPEN",
    "logline": "A courier discovers the package she is carrying is already open.",
    "characters": [
        {
            "id": "lena",
            "name": "LENA",
            "description": "Bike courier, early thirties. Watchful, economical with movement.",
            "wardrobe": "Faded red rain shell, cross-body courier bag, fingerless gloves",
            "visual_traits": ["short dark hair", "steel watch on left wrist"],
            "continuity_anchors": ["small scar above left eyebrow"],
        },
        {
            "id": "marcus",
            "name": "MARCUS",
            "description": "Dispatcher, fifties. Never leaves the desk.",
            "wardrobe": "Cardigan over a work shirt, reading glasses on a cord",
            "visual_traits": ["heavy build", "grey stubble"],
            "continuity_anchors": ["missing tip of right index finger"],
        },
    ],
    "locations": [
        {
            "id": "dispatch",
            "name": "Dispatch Office",
            "slug_line": "INT. DISPATCH OFFICE - NIGHT",
            "description": "A converted shopfront. Radio static, pinned route maps, one desk lamp.",
            "key_features": ["wall of route maps", "steel security shutter", "desk lamp"],
            "time_of_day": "NIGHT",
            "lighting": "single practical, deep falloff",
        },
        {
            "id": "alley",
            "name": "Loading Alley",
            "slug_line": "EXT. LOADING ALLEY - NIGHT",
            "description": "Wet brick, a dumpster, one sodium lamp at the far end.",
            "key_features": ["sodium lamp", "standing water", "fire escape"],
            "time_of_day": "NIGHT",
            "lighting": "sodium orange, hard, from behind",
        },
    ],
    "scenes": [
        {
            "id": "scene_001",
            "index": 1,
            "slug_line": "INT. DISPATCH OFFICE - NIGHT",
            "summary": "Marcus hands Lena a package that is warm to the touch.",
            "location_id": "dispatch",
            "character_ids": ["lena", "marcus"],
            "time_of_day": "NIGHT",
            "mood": "quiet dread",
        },
        {
            "id": "scene_002",
            "index": 2,
            "slug_line": "EXT. LOADING ALLEY - NIGHT",
            "summary": "Alone, Lena opens the package and finds the seal already broken.",
            "location_id": "alley",
            "character_ids": ["lena"],
            "time_of_day": "NIGHT",
            "mood": "cold, exposed",
        },
    ],
    "shots": [
        {
            "id": "shot_001", "scene_id": "scene_001", "index": 1,
            "size": "MLS", "lens": "35mm", "movement": "static", "angle": "eye level",
            "description": "Lena enters frame right, shutter half-open behind her. Marcus at the desk, foreground left, back to camera.",
            "character_ids": ["lena", "marcus"], "location_id": "dispatch",
            "beat": "arrival",
        },
        {
            "id": "shot_002", "scene_id": "scene_001", "index": 2,
            "size": "OTS", "lens": "50mm", "movement": "slow push in", "angle": "eye level",
            "description": "Over Marcus's shoulder onto the package as he slides it across the desk.",
            "character_ids": ["lena", "marcus"], "location_id": "dispatch",
            "beat": "the handoff",
        },
        {
            "id": "shot_003", "scene_id": "scene_001", "index": 3,
            "size": "CU", "lens": "85mm", "movement": "static", "angle": "low angle",
            "description": "Lena's hands closing over the package. She registers the warmth and stops.",
            "character_ids": ["lena"], "location_id": "dispatch",
            "beat": "she notices",
        },
        {
            "id": "shot_004", "scene_id": "scene_002", "index": 4,
            "size": "LS", "lens": "24mm", "movement": "static", "angle": "high angle",
            "description": "Lena small in the alley, sodium lamp behind her throwing a long shadow toward camera.",
            "character_ids": ["lena"], "location_id": "alley",
            "beat": "isolation",
        },
        {
            "id": "shot_005", "scene_id": "scene_002", "index": 5,
            "size": "ECU", "lens": "85mm", "movement": "static", "angle": "overhead",
            "description": "The broken seal, lifted away clean. No tear.",
            "character_ids": ["lena"], "location_id": "alley",
            "beat": "the reveal",
        },
    ],
}


class MockTextClient:
    """Mocked reasoning model. Returns canned shapes after a plausible delay."""

    def __init__(self, mock: bool = True) -> None:
        self.mock = mock

    async def write_script(self, genre: str = "") -> str:
        """Mock screenwriter: hand back one of the curated samples."""
        from ..samples import random_script

        await asyncio.sleep(0.8 + random.random() * 0.4)
        return random_script()["script"]

    async def breakdown(self, script: str = "") -> dict:
        await asyncio.sleep(2.0 + random.random() * 0.6)
        return dict(_CANNED_BREAKDOWN)

    async def look_block(
        self, image_paths: list[Path] | None = None, look_note: str = ""
    ) -> dict:
        await asyncio.sleep(1.4 + random.random() * 0.6)
        return {
            "palette": ["sodium orange", "desaturated teal shadow", "near-black"],
            "film_stock": "pushed 500T, visible grain in the shadows",
            "lighting": "single-source practicals, deep unlit falloff",
            "lens_character": "slight barrel on the wides, creamy 85mm falloff",
            "composition_notes": "subjects pushed to frame edge, heavy negative space",
            "mood": "watchful, nocturnal",
            "influences": ["Michael Mann", "Roger Deakins night exteriors"],
        }

    async def research(self, scene: dict, look_note: str = "") -> dict:
        await asyncio.sleep(1.8 + random.random() * 0.8)
        return {
            "scene_id": scene.get("id", "scene_001"),
            "objective": f"Visual research for {scene.get('slug_line', 'scene')}",
            "period_notes": "[mock] Contemporary; no period constraint detected.",
            "wardrobe_notes": "[mock] High-vis-free courier kit; layered technical shell over merino.",
            "location_notes": "[mock] Converted shopfront dispatch rooms keep the original shutter and tile.",
            "cinematography_notes": "[mock] Night exteriors lit by a single practical, letting the shadows go fully black.",
            "citations": [
                {
                    "title": "[mock citation] configure PARALLEL_API_KEY for real sources",
                    "url": "https://platform.parallel.ai",
                    "excerpt": "This dossier is mock data. Set PARALLEL_API_KEY to run live research.",
                    "publish_date": None,
                }
            ],
        }

    async def plate_prompt(
        self, kind: str, name: str, description: str,
        look_summary: str = "", research_summary: str = "", extra: str = "",
    ) -> str:
        await asyncio.sleep(0.8 + random.random() * 0.4)
        return (
            f"[mock plate prompt] Reference plate of the {kind} {name}. {description} "
            f"{extra} Rendered per the film's look: {look_summary[:180]}"
        )

    async def panel_prompt(self, shot: dict, scene: dict, research_summary: str = "") -> str:
        await asyncio.sleep(0.8 + random.random() * 0.4)
        return (
            f"[mock panel prompt] {shot.get('size')} on {shot.get('lens')}, "
            f"{shot.get('angle')}, {shot.get('movement')}. "
            f"{shot.get('description')} — {scene.get('slug_line', '')}"
        )


class MockImageClient:
    """Mocked image generator. Writes a deterministic placeholder PNG so every
    card shows *something*, with its prompt legible on the image."""

    def __init__(self, mock: bool = True) -> None:
        self.mock = mock

    async def generate(
        self,
        dest: Path,
        prompt: str,
        size: tuple[int, int] = (1024, 576),
        refs: list[Path] | None = None,
    ) -> None:
        await asyncio.sleep(1.6 + random.random() * 0.7)
        seed = prompt + "|" + "|".join(p.name for p in (refs or []))
        img = Image.new("RGB", size, self._color_from(seed))
        draw = ImageDraw.Draw(img)
        caption = prompt[:300]
        if refs:
            caption = f"[refs: {len(refs)}] " + caption
        draw.text((20, 20), textwrap.fill(caption, width=52), fill=(255, 255, 255))
        dest.parent.mkdir(parents=True, exist_ok=True)
        img.save(dest, "PNG")

    async def animate(self, src: Path, dest: Path, prompt: str = "") -> None:
        raise RuntimeError(
            "Animatic generation needs Veo, which has no free tier. "
            "Set ENABLE_VEO=1 with a billed GEMINI_API_KEY."
        )

    @staticmethod
    def _color_from(seed: str) -> tuple[int, int, int]:
        h = hashlib.md5(seed.encode()).digest()
        return (20 + h[0] % 90, 20 + h[1] % 90, 30 + h[2] % 90)
