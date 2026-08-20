from __future__ import annotations

import logging
import os
from pathlib import Path

from .gemini import (
    DEFAULT_IMAGE_MODEL,
    DEFAULT_TEXT_MODEL,
    DEFAULT_VIDEO_MODEL,
    GeminiImage,
    GeminiText,
)
from .mock import MockImageClient, MockTextClient
from .parallel_search import MockParallelSearch, ParallelSearch

log = logging.getLogger("clients")

PLACEHOLDER_VALUES = {"", "replace-me", "your-key-here"}


def _key(name: str) -> str | None:
    v = (os.environ.get(name) or "").strip()
    return None if v in PLACEHOLDER_VALUES else v


def _model(name: str, default: str) -> str:
    return (os.environ.get(name) or default).strip()


def make_text_client() -> MockTextClient:
    key = _key("GEMINI_API_KEY")
    if key:
        model = _model("GEMINI_TEXT_MODEL", DEFAULT_TEXT_MODEL)
        log.info("text client: GeminiText (%s)", model)
        return GeminiText(api_key=key, model=model)
    log.info("text client: MockTextClient (GEMINI_API_KEY not set)")
    return MockTextClient()


def make_image_client() -> MockImageClient:
    key = _key("GEMINI_API_KEY")
    if key:
        model = _model("GEMINI_IMAGE_MODEL", DEFAULT_IMAGE_MODEL)
        log.info("image client: GeminiImage (%s)", model)
        return GeminiImage(
            api_key=key,
            model=model,
            video_model=_model("VEO_MODEL", DEFAULT_VIDEO_MODEL),
        )
    log.info("image client: MockImageClient (GEMINI_API_KEY not set)")
    return MockImageClient()


def make_search_client(cache_dir: Path | None = None):
    key = _key("PARALLEL_API_KEY")
    if key:
        log.info("search client: ParallelSearch")
        return ParallelSearch(api_key=key, cache_dir=cache_dir)
    log.info("search client: MockParallelSearch (PARALLEL_API_KEY not set)")
    return MockParallelSearch()


def veo_enabled() -> bool:
    """Veo has no free tier, so the animatic pass is opt-in."""
    return (os.environ.get("ENABLE_VEO") or "0").strip().lower() in ("1", "true", "yes")
