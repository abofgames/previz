"""Node/artifact id conventions, in one place.

The graph node id and the on-disk artifact name are deliberately the same
string, so a node can always find its own file and rehydration after a restart
is a directory listing rather than a lookup table.
"""
from __future__ import annotations

CHAR_PREFIX = "char_"
LOC_PREFIX = "loc_"
ANIMATIC_PREFIX = "animatic_"
RESEARCH_PREFIX = "research_"

GROUP_CHARACTERS = "characters"
GROUP_LOCATIONS = "locations"
GROUP_SHOTS = "shots"

NODE_BRIEF = "brief"
NODE_LOOK_DEV = "look_dev"
NODE_BREAKDOWN = "breakdown"
NODE_RESEARCH = "research"
NODE_LOOKBOARD = "lookboard"


def char_ref(char_id: str) -> str:
    return f"{CHAR_PREFIX}{char_id}"


def loc_ref(loc_id: str) -> str:
    return f"{LOC_PREFIX}{loc_id}"


def animatic(shot_id: str) -> str:
    return f"{ANIMATIC_PREFIX}{shot_id}"


def strip_char(node_id: str) -> str:
    return node_id[len(CHAR_PREFIX):]


def strip_loc(node_id: str) -> str:
    return node_id[len(LOC_PREFIX):]


def strip_animatic(node_id: str) -> str:
    return node_id[len(ANIMATIC_PREFIX):]
