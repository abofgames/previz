"""Gemini-backed clients — the only inference path in previz.

Everything the app generates comes from Google models:

- Reasoning / structured extraction → ``gemini-2.5-flash`` with a
  ``response_schema``, so the breakdown and the look block come back as
  validated Pydantic objects rather than parsed prose.
- Images → ``gemini-2.5-flash-image`` (Nano Banana). Reference plates are
  attached as inline image parts, which is what holds character likeness and
  location continuity across every panel: lookboard → plates → panels.
- Video (optional) → Veo via ``generate_videos``, gated behind ENABLE_VEO
  because Veo has no free tier.

Both classes subclass the mocks so any method left unwired degrades to canned
data instead of taking the pipeline down.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from pathlib import Path

from google import genai
from google.genai import types

from ..models import LookBlock, ResearchDossier, ScriptBreakdown
from .mock import MockImageClient, MockTextClient, mime_for
from .prompts import (
    BREAKDOWN_PROMPT,
    LOOK_PROMPT,
    LOOK_REF_CLAUSE,
    NO_TEXT_CLAUSE,
    PANEL_PROMPT_TEMPLATE,
    PLATE_PROMPT_TEMPLATE,
)

log = logging.getLogger("gemini")

# The free tier grants a *per-model* daily quota (20/day on 2.5-flash), so when
# one model is spent the others are untouched. The client walks this chain
# rather than failing the run — all Google models, so the Google-AI-only rule
# still holds. Verified reachable and schema-capable on a free key.
DEFAULT_TEXT_MODEL = "gemini-3.5-flash"
TEXT_MODEL_CHAIN = [
    "gemini-3.5-flash",
    "gemini-3.6-flash",
    "gemini-3-flash-preview",
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash",
    "gemma-4-31b-it",
]
# Verified against the live API: EVERY Gemini image model reports
# `limit: 0` on the free tier — image generation needs a billed key. 2.5 Flash
# Image is still the right target because it is the cheapest once billing is on.
DEFAULT_IMAGE_MODEL = "gemini-2.5-flash-image"
DEFAULT_VIDEO_MODEL = "veo-3.1-generate-preview"

_MAX_REF_IMAGES = 8       # keep the panel call inside a sane request size
_MAX_VISION_IMAGES = 6    # look refs fed to the vision model

# Free-tier RPM is the binding constraint, and image jobs are the expensive
# ones. Serialize them so a fan-out of panels queues here instead of tripping
# 429s at the API.
_IMAGE_SEMAPHORE = asyncio.Semaphore(1)

_MAX_ATTEMPTS = 4
_BACKOFF_BASE_S = 2.0

# The free tier allows 5 requests/minute/model, and it is the binding limit in
# practice — far tighter than the daily cap. Every Gemini call in the process
# is paced through this bucket so a fan-out queues instead of tripping 429s.
FREE_TIER_RPM = int(os.environ.get("GEMINI_RPM", "5"))
_rate_lock = asyncio.Lock()
_recent_calls: list[float] = []


async def pace() -> None:
    """Block until another Gemini request fits inside the RPM budget."""
    while True:
        async with _rate_lock:
            now = time.monotonic()
            _recent_calls[:] = [t for t in _recent_calls if now - t < 60.0]
            if len(_recent_calls) < FREE_TIER_RPM:
                _recent_calls.append(now)
                return
            wait = 60.0 - (now - _recent_calls[0]) + 0.25
        log.info("rate limit: waiting %.1fs for the RPM window", wait)
        await asyncio.sleep(wait)


def _is_daily_quota(msg: str) -> bool:
    """A per-DAY quota is gone until midnight Pacific; a per-MINUTE one clears
    in under a minute. Only the former is worth switching models over."""
    return "PerDay" in msg or "RequestsPerDay" in msg


def _retry_after(msg: str) -> float | None:
    """Pull the server's own retryDelay out of a 429 body, if it gave one."""
    m = re.search(r"retryDelay['\"]?:\s*['\"]?(\d+(?:\.\d+)?)s", msg)
    return float(m.group(1)) if m else None


def _friendly(exc: Exception, what: str) -> RuntimeError:
    """Turn an SDK exception into something readable on a failed node card."""
    msg = str(exc)
    if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
        # `limit: 0` means the free tier never had this quota — waiting for the
        # daily reset will not help, so say so instead of sending the user away
        # to watch a counter that is already zero.
        if "limit: 0" in msg:
            return RuntimeError(
                f"{what}: image generation is not available on the Gemini free "
                "tier (quota limit is 0). It needs a billed API key — enable "
                "billing on the Cloud project behind this key."
            )
        scope = "daily" if _is_daily_quota(msg) else "per-minute"
        quota_id = "PerDay" if _is_daily_quota(msg) else "PerMinute"
        return RuntimeError(
            f"{what}: Gemini {scope} quota exhausted ({quota_id}). Daily quotas "
            "reset at midnight Pacific — check aistudio.google.com/rate-limit."
        )
    if "401" in msg or "403" in msg or "API key" in msg:
        return RuntimeError(f"{what}: Gemini rejected the API key — check GEMINI_API_KEY.")
    if "404" in msg:
        return RuntimeError(f"{what}: model not found — check the model id. ({msg[:160]})")
    return RuntimeError(f"{what} failed: {msg[:300]}")


async def _with_retry(coro_factory, *, what: str):
    """Run an SDK call, paced against the RPM budget and retried on failures
    that can actually recover.

    Two very different things arrive as 429. `limit: 0` means the quota was
    never granted and no amount of waiting helps. A per-minute limit comes with
    the server's own `retryDelay` and clears in under a minute — that one is
    worth waiting out, because the alternative is failing a card the user is
    watching.
    """
    last: Exception | None = None
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        await pace()
        try:
            return await coro_factory()
        except Exception as e:  # noqa: BLE001 - SDK raises a wide range
            msg = str(e)
            last = e
            # A daily-quota 429 also carries a retryDelay, but that delay only
            # refers to the per-minute throttle — the daily budget is gone until
            # midnight. Bail out immediately so the caller can switch models
            # instead of sleeping through three pointless retries.
            if "429" in msg and _is_daily_quota(msg):
                raise _friendly(e, what) from e
            if "429" in msg and "limit: 0" not in msg and attempt < _MAX_ATTEMPTS:
                delay = _retry_after(msg) or (_BACKOFF_BASE_S * 2**attempt)
                log.warning("%s: rate limited, waiting %.0fs (%d/%d)",
                            what, delay, attempt, _MAX_ATTEMPTS)
                await asyncio.sleep(delay + 0.5)
                continue
            transient = any(s in msg for s in ("500", "502", "503", "504", "UNAVAILABLE"))
            if transient and attempt < _MAX_ATTEMPTS:
                log.warning("%s: transient error, retry %d/%d", what, attempt, _MAX_ATTEMPTS)
                await asyncio.sleep(_BACKOFF_BASE_S * attempt)
                continue
            raise _friendly(e, what) from e
    raise _friendly(last or RuntimeError("unknown"), what)


def _summarize(block: dict | None, keys: tuple[str, ...]) -> str:
    """Flatten a dict into short 'key: value' lines for embedding in a prompt."""
    if not block:
        return "(none)"
    lines = []
    for k in keys:
        v = block.get(k)
        if not v:
            continue
        v = ", ".join(str(x) for x in v) if isinstance(v, list) else str(v)
        lines.append(f"{k.replace('_', ' ')}: {v}")
    return "\n".join(lines) or "(none)"


def look_summary(block: dict | None) -> str:
    return _summarize(
        block,
        ("palette", "film_stock", "lighting", "lens_character",
         "composition_notes", "mood", "influences"),
    )


def research_summary(dossier: dict | None) -> str:
    return _summarize(
        dossier,
        ("period_notes", "wardrobe_notes", "location_notes", "cinematography_notes"),
    )


class GeminiText(MockTextClient):
    """Reasoning + structured extraction via the Gemini API."""

    def __init__(self, api_key: str, model: str = DEFAULT_TEXT_MODEL) -> None:
        super().__init__(mock=False)
        self._client = genai.Client(api_key=api_key)
        # Preferred model first, then the rest of the chain as fallbacks.
        self._chain = [model] + [m for m in TEXT_MODEL_CHAIN if m != model]
        self._idx = 0

    @property
    def model(self) -> str:
        """The model currently in use — may have rolled forward from the
        configured one after a daily quota ran out."""
        return self._chain[self._idx]

    def _next_model(self) -> bool:
        """Roll to the next model in the chain. False when none are left."""
        if self._idx + 1 >= len(self._chain):
            return False
        self._idx += 1
        log.warning("daily quota spent — switching to %s", self.model)
        return True

    async def _generate(self, contents, *, schema=None, temperature: float = 0.5) -> str:
        cfg = types.GenerateContentConfig(temperature=temperature)
        if schema is not None:
            cfg.response_mime_type = "application/json"
            cfg.response_schema = schema

        while True:
            model = self.model
            try:
                resp = await _with_retry(
                    lambda: self._client.aio.models.generate_content(
                        model=model, contents=contents, config=cfg
                    ),
                    what=f"Gemini text ({model})",
                )
            except RuntimeError as exc:
                # A spent daily quota on one model says nothing about the next.
                if _is_daily_quota(str(exc)) and self._next_model():
                    continue
                raise
            text = (resp.text or "").strip()
            if not text:
                raise RuntimeError("Gemini returned an empty response")
            return text

    async def write_script(self, genre: str = "") -> str:
        """Write an original scene to storyboard, for when the user has no
        script to hand. Text-only, so this works on the free tier."""
        from ..samples import SCRIPT_GEN_PROMPT, random_genre

        log.info("write_script (%s)", genre or "random genre")
        return await self._generate(
            SCRIPT_GEN_PROMPT.format(genre=genre or random_genre()),
            temperature=1.0,
        )

    async def breakdown(self, script: str = "") -> dict:
        if not script.strip():
            raise ValueError("script is empty — paste a screenplay in the Script card")
        log.info("breakdown (%d chars)", len(script))
        out = await self._generate(
            BREAKDOWN_PROMPT.format(script=script),
            schema=ScriptBreakdown,
            temperature=0.3,
        )
        return ScriptBreakdown.model_validate_json(out).model_dump()

    async def look_block(
        self, image_paths: list[Path] | None = None, look_note: str = ""
    ) -> dict:
        paths = [Path(p) for p in (image_paths or []) if Path(p).exists()]
        if not paths and not look_note.strip():
            raise ValueError(
                "no look input — upload reference frames or write a look note"
            )
        log.info("look_block (%d refs, note %d chars)", len(paths), len(look_note))
        parts: list = [
            types.Part.from_text(
                text=LOOK_PROMPT.format(
                    ref_clause=LOOK_REF_CLAUSE if paths else "",
                    look_note=look_note or "(none given — infer from the references)",
                )
            )
        ]
        for p in paths[:_MAX_VISION_IMAGES]:
            parts.append(types.Part.from_bytes(data=p.read_bytes(), mime_type=mime_for(p)))
        out = await self._generate(
            [types.Content(role="user", parts=parts)],
            schema=LookBlock,
            temperature=0.3,
        )
        return LookBlock.model_validate_json(out).model_dump()

    async def research_synthesis(
        self, prompt: str, search_findings: str, scene_id: str
    ) -> dict:
        """Turn raw Parallel search excerpts into a structured dossier.

        The search itself happens in ``parallel_search.py``; this is only the
        Gemini side that reads the findings and writes usable art direction.
        """
        out = await self._generate(
            f"{prompt}\n\n--- SEARCH FINDINGS ---\n{search_findings}\n\n"
            "Write the dossier from these findings. Cite only sources listed above.",
            schema=ResearchDossier,
            temperature=0.4,
        )
        dossier = ResearchDossier.model_validate_json(out).model_dump()
        dossier["scene_id"] = scene_id
        return dossier

    async def plate_prompt(
        self, kind: str, name: str, description: str,
        look_summary: str = "", research_summary: str = "", extra: str = "",
    ) -> str:
        log.info("plate_prompt (%s %s)", kind, name)
        return await self._generate(
            PLATE_PROMPT_TEMPLATE.format(
                kind=kind, name=name, description=description, extra=extra,
                look=look_summary or "(no look block)",
                research=research_summary or "(no research)",
            ),
            temperature=0.7,
        )

    async def panel_prompt(self, shot: dict, scene: dict, research_summary: str = "") -> str:
        log.info("panel_prompt (%s)", shot.get("id"))
        return await self._generate(
            PANEL_PROMPT_TEMPLATE.format(
                shot_id=shot.get("id", ""),
                size=shot.get("size", "MS"),
                lens=shot.get("lens", "35mm"),
                angle=shot.get("angle", "eye level"),
                movement=shot.get("movement", "static"),
                slug_line=scene.get("slug_line", ""),
                description=shot.get("description", ""),
                beat=shot.get("beat", ""),
                mood=scene.get("mood", ""),
                research=research_summary or "(no research)",
            ),
            temperature=0.7,
        )


class GeminiImage(MockImageClient):
    """Image generation via Gemini, with reference plates attached inline.

    The reference chain is the whole trick: the lookboard fixes rendering, the
    character and location plates fix likeness and place, and a panel that
    receives all three comes back consistent with every other panel.
    """

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_IMAGE_MODEL,
        video_model: str = DEFAULT_VIDEO_MODEL,
    ) -> None:
        super().__init__(mock=False)
        self._client = genai.Client(api_key=api_key)
        self._model = model
        self._video_model = video_model

    async def generate(
        self,
        dest: Path,
        prompt: str,
        size: tuple[int, int] = (1024, 576),
        refs: list[Path] | None = None,
    ) -> None:
        ref_paths = [Path(p) for p in (refs or []) if Path(p).exists()][:_MAX_REF_IMAGES]
        log.info("image → %s (prompt %d chars, %d refs)", dest.name, len(prompt), len(ref_paths))

        parts: list = [types.Part.from_text(text=prompt + NO_TEXT_CLAUSE)]
        for p in ref_paths:
            parts.append(types.Part.from_bytes(data=p.read_bytes(), mime_type=mime_for(p)))

        cfg = types.GenerateContentConfig(response_modalities=["IMAGE", "TEXT"])
        async with _IMAGE_SEMAPHORE:
            resp = await _with_retry(
                lambda: self._client.aio.models.generate_content(
                    model=self._model,
                    contents=[types.Content(role="user", parts=parts)],
                    config=cfg,
                ),
                what="Gemini image",
            )

        data = _first_image_bytes(resp)
        if not data:
            raise RuntimeError(
                f"Gemini returned no image for prompt: {prompt[:120]!r}. "
                "The model may have refused the prompt."
            )
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)

    async def animate(self, src: Path, dest: Path, prompt: str = "") -> None:
        """Turn a finished panel into a short animatic clip with Veo.

        Off by default: Veo has no free tier, so this raises unless the caller
        explicitly enabled it and the key is billed.
        """
        log.info("veo animatic → %s", dest.name)
        image = types.Image(image_bytes=src.read_bytes(), mime_type=mime_for(src))
        op = await _with_retry(
            lambda: self._client.aio.models.generate_videos(
                model=self._video_model,
                prompt=prompt or "Subtle camera move, consistent with the frame.",
                image=image,
            ),
            what="Veo",
        )
        # generate_videos returns a long-running operation; poll it out.
        for _ in range(60):
            if getattr(op, "done", False):
                break
            await asyncio.sleep(10)
            op = self._client.operations.get(op)
        if not getattr(op, "done", False):
            raise RuntimeError("Veo job did not finish in time")

        videos = getattr(op.response, "generated_videos", None) or []
        if not videos:
            raise RuntimeError("Veo returned no video")
        video = videos[0].video
        self._client.files.download(file=video)
        dest.parent.mkdir(parents=True, exist_ok=True)
        video.save(str(dest))


def _first_image_bytes(resp) -> bytes | None:
    for cand in getattr(resp, "candidates", None) or []:
        content = getattr(cand, "content", None)
        for part in getattr(content, "parts", None) or []:
            inline = getattr(part, "inline_data", None)
            if inline is not None and getattr(inline, "data", None):
                return inline.data
    return None


async def _smoke() -> None:
    """python -m backend.clients.gemini --smoke"""
    from dotenv import load_dotenv

    load_dotenv()
    key = os.environ.get("GEMINI_API_KEY", "")
    if key in ("", "replace-me", "your-key-here"):
        print("GEMINI_API_KEY not set — nothing to smoke test.")
        return

    text = GeminiText(key)
    print("→ breakdown…")
    out = await text.breakdown(
        "INT. DINER - NIGHT\n\nMAYA sits alone. The door opens. RAY enters, soaked.\n"
        "\nMAYA\nYou're late.\n"
    )
    print(json.dumps({k: len(v) if isinstance(v, list) else v
                      for k, v in out.items()}, indent=2)[:600])

    img = GeminiImage(key)
    dest = Path("/tmp/previz_smoke.png")
    print("→ image…")
    await img.generate(dest, "Storyboard panel: a wide shot of an empty night diner, "
                             "graphite sketch, single practical light.")
    print(f"wrote {dest} ({dest.stat().st_size} bytes)")


if __name__ == "__main__":
    import sys

    if "--smoke" in sys.argv:
        asyncio.run(_smoke())
