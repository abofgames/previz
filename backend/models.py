from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class NodeStatus(str, Enum):
    pending = "pending"
    running = "running"
    complete = "complete"
    failed = "failed"
    stale = "stale"


# --------------------------------------------------------------------------
# Domain — what an agent extracts from a screenplay
# --------------------------------------------------------------------------


class Character(BaseModel):
    id: str
    name: str
    description: str
    wardrobe: str = ""
    visual_traits: list[str] = Field(default_factory=list)
    continuity_anchors: list[str] = Field(default_factory=list)


class Location(BaseModel):
    id: str
    name: str
    slug_line: str = ""
    description: str
    key_features: list[str] = Field(default_factory=list)
    time_of_day: str = ""
    lighting: str = ""


ShotSize = Literal[
    "ELS", "LS", "MLS", "MS", "MCU", "CU", "ECU", "OTS", "POV", "TWO-SHOT", "INSERT"
]


class Shot(BaseModel):
    """One storyboard panel. The spec fields are what a 1st AD or DP would
    actually read off a shot list — they drive the panel prompt directly."""

    id: str
    scene_id: str
    index: int
    size: ShotSize = "MS"
    lens: str = "35mm"
    movement: str = "static"
    angle: str = "eye level"
    description: str
    character_ids: list[str] = Field(default_factory=list)
    location_id: str = ""
    beat: str = ""


class Scene(BaseModel):
    id: str
    index: int
    slug_line: str
    summary: str
    location_id: str = ""
    character_ids: list[str] = Field(default_factory=list)
    time_of_day: str = ""
    mood: str = ""


class ScriptBreakdown(BaseModel):
    """Output of the breakdown agent — the whole script, structured."""

    title: str = ""
    logline: str = ""
    characters: list[Character] = Field(default_factory=list)
    locations: list[Location] = Field(default_factory=list)
    scenes: list[Scene] = Field(default_factory=list)
    shots: list[Shot] = Field(default_factory=list)


# --------------------------------------------------------------------------
# Research — grounded in real sources via the Parallel Search API
# --------------------------------------------------------------------------


class Citation(BaseModel):
    title: str
    url: str
    excerpt: str = ""
    publish_date: str | None = None


class ResearchDossier(BaseModel):
    """Per-scene visual research. `notes` are what the art-direction and panel
    prompts consume; `citations` are what the UI shows so the output is
    traceable back to real sources rather than model invention."""

    scene_id: str
    objective: str = ""
    period_notes: str = ""
    wardrobe_notes: str = ""
    location_notes: str = ""
    cinematography_notes: str = ""
    citations: list[Citation] = Field(default_factory=list)


class LookBlock(BaseModel):
    """Descriptive look guide derived from the user's reference images and
    look note. Tells a downstream model how to render — never reproduces a
    source frame."""

    palette: list[str] = Field(default_factory=list)
    film_stock: str = ""
    lighting: str = ""
    lens_character: str = ""
    composition_notes: str = ""
    mood: str = ""
    influences: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------
# Graph — what the frontend renders and animates
# --------------------------------------------------------------------------


NodeKind = Literal[
    "brief",
    "look_dev",
    "breakdown",
    "research",
    "lookboard",
    "group",
    "character",
    "location",
    "shot",
    "animatic",
]


class GraphNode(BaseModel):
    id: str
    kind: NodeKind
    label: str
    status: NodeStatus = NodeStatus.pending
    meta: dict = Field(default_factory=dict)


class GraphEdge(BaseModel):
    source: str
    target: str
    kind: Literal["depends_on", "fans_out_to"] = "depends_on"


class Graph(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class WSEvent(BaseModel):
    type: Literal["graph_init", "graph_replace", "node_update", "log"]
    payload: dict
