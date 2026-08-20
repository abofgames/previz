"""Sample material so the app is usable without writing a screenplay first.

Everything here is original writing — no third-party IP — because the sample
that ships with a demo ends up in the demo video.
"""
from __future__ import annotations

import random

SCRIPT_GEN_PROMPT = """Write an original short screenplay excerpt for a
storyboard test. Requirements:

- 2 or 3 scenes, each with a proper slug line (INT./EXT. - LOCATION - TIME).
- 2 or 3 characters, named in caps on first appearance.
- Genre: {genre}.
- Visually specific. Every beat should be something a camera can see:
  physical action, an object, a change in light. Avoid interior monologue.
- Under 250 words. Real screenplay formatting.
- Completely original. Do not use characters, places or plots from any
  existing film, book, game or show.

Output only the screenplay text. No title page, no commentary.
"""

GENRES = [
    "neo-noir crime",
    "quiet science fiction",
    "psychological thriller",
    "modern western",
    "supernatural mystery",
    "heist",
    "post-industrial drama",
]

SAMPLE_SCRIPTS: list[dict[str, str]] = [
    {
        "title": "Cold Open",
        "script": """INT. DISPATCH OFFICE - NIGHT

A converted shopfront. Route maps pinned three deep. One desk lamp.

MARCUS, 50s, cardigan, reading glasses on a cord, slides a padded
envelope across the desk without looking up.

LENA, 30s, rain shell beaded with water, picks it up. Stops.
The envelope is warm.

                    LENA
          How long has this been sitting here?

                    MARCUS
          Came in twenty minutes ago.

She turns it over. The seal is intact. She pockets it.

EXT. LOADING ALLEY - NIGHT

Wet brick. One sodium lamp at the far end throws Lena's shadow
back toward camera, twenty feet long.

She crouches behind a dumpster and works the seal open with a
thumbnail.

It lifts away clean. No tear. It was opened before.

Lena goes very still. Somewhere behind her, a bike freewheel
ticks and stops.""",
    },
    {
        "title": "The Long Count",
        "script": """EXT. SALT FLAT - DAWN

White ground to the horizon. A single radio mast, guy-wired,
rust bleeding down the white.

VERA, 40s, sun-bleached jacket, walks the last hundred meters
with a spool of cable over one shoulder.

INT. RELAY SHACK - CONTINUOUS

Cramped. Banks of analog meters, most dead. One needle twitches.

Vera drops the spool, strips a cable end with her teeth, and
splices it into the terminal block.

The needle steadies. Then swings hard right.

                    VERA
          That's not us.

She looks up. Through the window, far out on the flat, a second
mast stands where there was nothing an hour ago.

EXT. SALT FLAT - CONTINUOUS

Vera in the doorway, small against the white.

The second mast is closer than it was.""",
    },
    {
        "title": "Housekeeping",
        "script": """INT. HOTEL CORRIDOR - DAY

Patterned carpet, endless. A housekeeping cart, abandoned mid-hall,
one wheel still turning.

ODILE, 20s, uniform, stops beside it. She checks both directions.

The door to 1114 stands open four inches.

INT. ROOM 1114 - CONTINUOUS

Curtains drawn. The bed has not been slept in. On the desk: forty
identical room keys, laid out in a grid, perfectly spaced.

Odile picks one up. It has no room number.

Behind her, the bathroom light clicks on by itself.

                    ODILE
          Housekeeping.

No answer. Steam begins to creep under the bathroom door, across
the carpet, toward her shoes.""",
    },
    {
        "title": "Nine Bar",
        "script": """INT. ESPRESSO BAR - EARLY MORNING

Chrome and steam. Chairs still stacked. TOMASZ, 60s, aproned,
pulls a shot and watches it fall.

The stream stutters. He stops the pump.

                    TOMASZ
          Grinder's warm.

RUTH, 30s, coat still on, sits at the counter with a folder she
has not opened.

                    RUTH
          I need you to look at something.

He wipes his hands. Doesn't move toward her.

                    TOMASZ
          I looked at it in 1994.

EXT. ESPRESSO BAR - CONTINUOUS

Through the window, from the street: the two of them framed by
the machine, neither one moving.

A tram passes between camera and glass, and when it clears, Ruth's
seat is empty and the folder is open on the counter.""",
    },
]

LOOK_PRESETS: list[dict] = [
    {
        "name": "Sodium Night",
        "note": (
            "Night exteriors lit by a single sodium source. Crushed blacks, no fill, "
            "long hard shadows thrown toward camera. Anamorphic wides, subjects small "
            "in frame. Grain visible in the shadows."
        ),
        "palette": ["#f0872b", "#1d2b33", "#0a0c0e", "#6b4a2f", "#c9d6d9"],
    },
    {
        "name": "Overcast Procedural",
        "note": (
            "Flat overcast daylight, no visible sun. Desaturated, cool, almost no "
            "contrast. Locked-off symmetrical frames on long lenses. Everything "
            "readable, nothing dramatic."
        ),
        "palette": ["#9aa7ad", "#c5ccd0", "#5c666c", "#2f3639", "#dfe4e6"],
    },
    {
        "name": "Tungsten Interior",
        "note": (
            "Practical tungsten sources inside frame — lamps, bulbs, screens. Warm "
            "pools of light falling off into deep amber shadow. Shallow focus on 85mm, "
            "faces half-lit."
        ),
        "palette": ["#e8b465", "#8a5a2b", "#2a1c12", "#f5e3c3", "#402a1a"],
    },
    {
        "name": "Bleach Salt",
        "note": (
            "High-key daylight exteriors, blown highlights, near-white ground. "
            "Bleach-bypass contrast, silver blacks, minimal color. Wide 24mm frames "
            "with a very high horizon."
        ),
        "palette": ["#f4f4f0", "#d8d6cc", "#8f9089", "#3d3f3c", "#b7b2a4"],
    },
    {
        "name": "Fluorescent Green",
        "note": (
            "Institutional fluorescent overheads, green cast left uncorrected. Hard "
            "top light, unflattering, eye sockets in shadow. Static wides on 35mm, "
            "ceiling always in frame."
        ),
        "palette": ["#8fae7a", "#c7d6b8", "#3b4636", "#1a1f18", "#e2e8d8"],
    },
    {
        "name": "Rain Neon",
        "note": (
            "Wet streets after rain, mixed neon sources — magenta and cyan — reflected "
            "in standing water. Heavy atmosphere and haze. Long lens compression, "
            "layered foreground silhouettes."
        ),
        "palette": ["#e0489b", "#2ad5d5", "#120a1f", "#5a2a6b", "#f2f2f7"],
    },
]


def random_script() -> dict[str, str]:
    return dict(random.choice(SAMPLE_SCRIPTS))


def random_look() -> dict:
    return dict(random.choice(LOOK_PRESETS))


def random_genre() -> str:
    return random.choice(GENRES)
