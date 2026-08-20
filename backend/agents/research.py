"""The research agent — a real ADK agent, not a single templated call.

This is the one place in previz where the work is genuinely agentic: the model
decides what to search for, runs several searches from different angles, reads
what comes back, and decides whether it has enough to write the dossier. It
runs on Gemini via the Agent Development Kit, and its one tool is the Parallel
Search API.

Everything else in the pipeline is a deterministic DAG and is orchestrated
directly, because wrapping a known sequence of calls in an agent loop buys
nothing but latency.
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import FunctionTool
from google.genai import types

from ..clients.gemini import DEFAULT_TEXT_MODEL
from ..clients.parallel_search import format_findings
from ..clients.prompts import RESEARCH_PROMPT
from ..models import Citation, ResearchDossier

log = logging.getLogger("agents.research")

APP_NAME = "previz"
_MAX_SEARCHES = 5

AGENT_INSTRUCTION = """You are the art department researcher on a film in
pre-production. Your job is to ground a scene in verifiable reality so the
storyboard artist draws what the world actually looked like.

You have one tool: `search_visual_references`. Use it. Call it at least twice
with genuinely different angles before you answer — one pass on the setting
and period, one on wardrobe and props, and a third on cinematography if the
director's note names a film, director or DP.

Write concrete, drawable direction: materials, silhouettes, light sources,
architecture, specific garments. Never write thematic prose. If the searches
did not support a claim, leave that field brief rather than inventing detail.

Return ONLY a JSON object matching the required schema. Every entry in
`citations` must be a source the tool actually returned — never fabricate a
URL, and never cite a source you did not use.
"""


class _SearchToolState:
    """Per-invocation scratchpad.

    The agent's tool calls happen deep inside the ADK loop, so the citations it
    collects are captured here and read back out after the run. That also lets
    the UI show the real sources instead of trusting the model to echo them.
    """

    def __init__(self) -> None:
        self.citations: list[Citation] = []
        self.searches = 0

    def record(self, cites: list[Citation]) -> None:
        seen = {c.url for c in self.citations}
        self.citations.extend(c for c in cites if c.url and c.url not in seen)


def _build_tool(search_client, state: _SearchToolState):
    async def search_visual_references(objective: str, queries: list[str]) -> dict:
        """Search the live web for visual references to ground a film scene.

        Args:
            objective: What you are trying to establish, in one sentence.
                e.g. "Determine what a 1970s NYC bike courier actually wore."
            queries: Two or three short keyword queries, each a different
                angle on the objective.

        Returns:
            A dict with `findings`, a numbered list of sources and excerpts.
        """
        if state.searches >= _MAX_SEARCHES:
            return {"findings": "Search budget exhausted. Write the dossier now."}
        state.searches += 1
        cites = await search_client.search(objective=objective, queries=queries[:3])
        state.record(cites)
        log.info("search %d: %s → %d results", state.searches, objective[:50], len(cites))
        return {"findings": format_findings(cites)}

    return FunctionTool(search_visual_references)


async def research_scene(
    scene: dict[str, Any],
    *,
    search_client,
    look_note: str = "",
    characters: str = "",
    location: str = "",
    model: str = DEFAULT_TEXT_MODEL,
) -> ResearchDossier:
    """Run the agent over one scene and return its dossier."""
    scene_id = scene.get("id", "scene_001")
    state = _SearchToolState()

    agent = LlmAgent(
        name="art_department_researcher",
        model=model,
        description="Researches a film scene's visual world against live sources.",
        instruction=AGENT_INSTRUCTION,
        tools=[_build_tool(search_client, state)],
        output_schema=ResearchDossier,
        output_key="dossier",
    )

    session_service = InMemorySessionService()
    session = await session_service.create_session(app_name=APP_NAME, user_id="previz")
    runner = Runner(app_name=APP_NAME, agent=agent, session_service=session_service)

    prompt = RESEARCH_PROMPT.format(
        slug_line=scene.get("slug_line", ""),
        summary=scene.get("summary", ""),
        time_of_day=scene.get("time_of_day", ""),
        characters=characters or "(none listed)",
        location=location or "(none listed)",
        look_note=look_note or "(none given)",
    )

    final_text = ""
    async for event in runner.run_async(
        user_id="previz",
        session_id=session.id,
        new_message=types.Content(role="user", parts=[types.Part.from_text(text=prompt)]),
    ):
        if event.is_final_response() and event.content and event.content.parts:
            final_text = "".join(p.text or "" for p in event.content.parts).strip()

    dossier = _parse(final_text, scene_id)

    # The tool's own record of what came back is authoritative — it cannot be
    # hallucinated. Anything the model cited that the tool never returned is
    # dropped; anything the tool returned that the model omitted is added back.
    if state.citations:
        dossier.citations = state.citations
    log.info(
        "dossier %s: %d searches, %d citations", scene_id, state.searches,
        len(dossier.citations),
    )
    return dossier


def _parse(text: str, scene_id: str) -> ResearchDossier:
    try:
        dossier = ResearchDossier.model_validate_json(_strip_fences(text))
    except ValueError as e:
        log.warning("dossier %s: unparseable agent output (%s)", scene_id, e)
        dossier = ResearchDossier(scene_id=scene_id, location_notes=text[:1500])
    dossier.scene_id = scene_id
    return dossier


def _strip_fences(text: str) -> str:
    t = (text or "").strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[-1]
        t = t.rsplit("```", 1)[0]
    start, end = t.find("{"), t.rfind("}")
    return t[start : end + 1] if start != -1 and end > start else t


def ensure_adk_credentials() -> None:
    """ADK reads GOOGLE_API_KEY; previz configures a single GEMINI_API_KEY.

    Mirror one onto the other so users only ever set one variable, and pin the
    SDK to the AI Studio backend rather than Vertex.
    """
    key = (os.environ.get("GEMINI_API_KEY") or "").strip()
    if key and key not in ("replace-me", "your-key-here"):
        os.environ.setdefault("GOOGLE_API_KEY", key)
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "FALSE")


__all__ = ["research_scene", "ensure_adk_credentials", "APP_NAME"]
