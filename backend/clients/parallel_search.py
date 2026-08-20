"""Parallel Search API client — the partner integration, used at runtime.

This is what separates previz from a prompt wrapper. Before any panel is drawn,
the research agent searches the live web for what the scene's world actually
looked like — the period, the wardrobe, the architecture, how a named director
really shoots this kind of scene — and every claim it feeds downstream carries
a source URL the user can click.

Results are cached to disk per (scene, objective) so re-running a production
does not re-bill the same searches, and so a demo is reproducible offline.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
from pathlib import Path

from ..models import Citation

log = logging.getLogger("parallel")

# "fast" is the right tier here: art-department research wants breadth across
# many sources, not one deep multi-hop answer.
DEFAULT_MODE = "fast"
DEFAULT_MAX_CHARS = 6000
_MAX_RESULTS_KEPT = 8


class ParallelSearch:
    """Thin async wrapper over the Parallel SDK returning normalized Citations."""

    def __init__(self, api_key: str, cache_dir: Path | None = None) -> None:
        from parallel import Parallel

        self._client = Parallel(api_key=api_key)
        self._cache_dir = cache_dir
        self.mock = False

    async def search(
        self,
        objective: str,
        queries: list[str],
        *,
        mode: str = DEFAULT_MODE,
        max_chars: int = DEFAULT_MAX_CHARS,
    ) -> list[Citation]:
        cached = self._read_cache(objective, queries)
        if cached is not None:
            log.info("parallel search (cached): %s", objective[:60])
            return cached

        log.info("parallel search: %s | %s", objective[:60], queries)
        # The SDK is synchronous; keep the event loop free.
        resp = await asyncio.to_thread(
            lambda: self._client.search(
                objective=objective,
                search_queries=queries,
                mode=mode,
                max_chars_total=max_chars,
            )
        )

        citations: list[Citation] = []
        for r in (getattr(resp, "results", None) or [])[:_MAX_RESULTS_KEPT]:
            excerpts = getattr(r, "excerpts", None) or []
            citations.append(
                Citation(
                    title=getattr(r, "title", "") or getattr(r, "url", ""),
                    url=getattr(r, "url", ""),
                    excerpt=" ".join(str(e) for e in excerpts)[:1200],
                    publish_date=getattr(r, "publish_date", None),
                )
            )
        self._write_cache(objective, queries, citations)
        return citations

    # -- cache -------------------------------------------------------------
    def _cache_path(self, objective: str, queries: list[str]) -> Path | None:
        if self._cache_dir is None:
            return None
        key = hashlib.sha256(
            (objective + "||" + "|".join(queries)).encode()
        ).hexdigest()[:16]
        return self._cache_dir / f"search_{key}.json"

    def _read_cache(self, objective: str, queries: list[str]) -> list[Citation] | None:
        p = self._cache_path(objective, queries)
        if p is None or not p.exists():
            return None
        try:
            return [Citation.model_validate(c) for c in json.loads(p.read_text())]
        except (json.JSONDecodeError, ValueError):
            return None

    def _write_cache(self, objective: str, queries: list[str], cites: list[Citation]) -> None:
        p = self._cache_path(objective, queries)
        if p is None:
            return
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps([c.model_dump() for c in cites], indent=2))


class MockParallelSearch:
    """Fallback when PARALLEL_API_KEY is unset, so the app still runs."""

    def __init__(self) -> None:
        self.mock = True

    async def search(self, objective: str, queries: list[str], **_) -> list[Citation]:
        await asyncio.sleep(0.6)
        return [
            Citation(
                title="[mock] set PARALLEL_API_KEY for live research",
                url="https://platform.parallel.ai",
                excerpt=f"Mock result for objective {objective!r} "
                        f"(queries: {', '.join(queries)}).",
            )
        ]


def format_findings(citations: list[Citation]) -> str:
    """Render citations into the block the reasoning model reads."""
    if not citations:
        return "(no search results)"
    out = []
    for i, c in enumerate(citations, 1):
        out.append(f"[{i}] {c.title}\n    {c.url}\n    {c.excerpt[:700]}")
    return "\n\n".join(out)


async def _smoke() -> None:
    """python -m backend.clients.parallel_search --smoke"""
    from dotenv import load_dotenv

    load_dotenv()
    key = os.environ.get("PARALLEL_API_KEY", "")
    if key in ("", "replace-me", "your-key-here"):
        print("PARALLEL_API_KEY not set — nothing to smoke test.")
        return
    client = ParallelSearch(key)
    cites = await client.search(
        objective="Find how 1970s New York bike couriers actually dressed, for costume design.",
        queries=["1970s NYC bike messenger clothing", "vintage courier bag photos 1970s"],
    )
    for c in cites:
        print(f"- {c.title}\n  {c.url}\n  {c.excerpt[:160]}\n")


if __name__ == "__main__":
    import sys

    if "--smoke" in sys.argv:
        asyncio.run(_smoke())
