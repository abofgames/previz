"""Provider-neutral prompt templates.

Kept apart from any client so the Gemini client and the mock client share one
set of instructions, and so prompt work is reviewable without reading transport
code.
"""
from __future__ import annotations

# Appended to every real image-gen call. Storyboards are drawings, not comps:
# shot numbers, slug lines and dialogue are overlaid by the UI/print layout,
# never burned into the pixels where they can't be edited or translated.
NO_TEXT_CLAUSE = (
    "\n\n--- HARD CONSTRAINT ---\n"
    "Output illustration ONLY. The image must contain NO rendered text or "
    "typography of any kind. Specifically forbidden: speech bubbles, dialogue, "
    "captions, subtitles, slug lines, shot numbers, arrows with labels, "
    "timecode, signs with readable text, watermarks, signatures. "
    "Pure visual illustration — all text is overlaid later."
)

BREAKDOWN_PROMPT = """You are a first assistant director doing a script
breakdown, working with the storyboard artist.

From the screenplay below, extract:

- characters: every distinct speaking or visually present person.
- locations: every distinct place, keyed to its slug line where there is one.
- scenes: ordered, one per slug line / location-and-time change.
- shots: an actual shot list. Cover each scene in the number of shots a
  competent director would use — usually 2 to 6. Do not emit one shot per
  scene; break the scene into coverage.

Rules:
- snake_case ids. Scenes are "scene_001", "scene_002", ... in script order.
  Shots are "shot_001", "shot_002", ... continuous across the whole script.
- Every shot's scene_id, character_ids and location_id must reference ids you
  already emitted. Never invent an id in one list that is absent from another.
- size must be one of: ELS, LS, MLS, MS, MCU, CU, ECU, OTS, POV, TWO-SHOT,
  INSERT.
- lens is a focal length ("24mm", "50mm", "85mm"). movement is real grip
  language ("static", "slow push in", "handheld follow", "crane down",
  "pan left to right"). angle is "eye level", "low angle", "high angle",
  "dutch", "overhead".
- shot.description is what the audience SEES in that frame — staging, blocking
  and framing. Not dialogue, not internal state.
- character wardrobe and visual_traits should capture what must stay consistent
  from panel to panel.

Screenplay:
{script}
"""

LOOK_PROMPT = """You are a director of photography establishing the visual
language of a film.

{ref_clause}Look note from the director: {look_note}

Describe the look this implies — palette, film stock or digital character,
lighting approach, lens character, composition habits, mood, and any clearly
evoked influences. This is a guide for how the storyboard panels should be
rendered. Never reproduce a source frame; describe the grammar, not the image.
"""

LOOK_REF_CLAUSE = (
    "Reference frames are attached. Read the shared visual language across "
    "them — not the content of any single one.\n\n"
)

RESEARCH_PROMPT = """You are the art department researcher on a film. You have
the Parallel Search tool for live web search, and you must use it.

Scene: {slug_line}
Summary: {summary}
Time of day: {time_of_day}
Characters present: {characters}
Location: {location}
Director's look note: {look_note}

Run searches to ground this scene in reality, then write the dossier. Look for:
- period and setting accuracy: what this place and era actually looked like
- wardrobe: what these people would actually wear, in this period and role
- location: real-world references for this kind of space, its architecture
  and materials
- cinematography: if the look note names a film, director or DP, find how
  they actually shoot this kind of scene

Call the search tool at least twice with different angles before answering.
Write each notes field as concrete, visual, usable direction — things a
storyboard artist can draw. Not prose about themes. Cite every source you
used in citations; do not cite a source you did not read.
"""

PLATE_PROMPT_TEMPLATE = """Write a single image-generation prompt for ONE
clean reference plate of this {kind}, rendered in the film's look.

Name: {name}
Description: {description}
{extra}

The film's look (apply to rendering — palette, lighting, lens character):
{look}

Grounded research (use these concrete details — they are researched fact,
prefer them over your own assumptions):
{research}

The image-gen call will ALSO receive the director's reference frames. Those
are for LOOK ONLY — never copy their subject or content; render *this*
{kind}, not whatever appears in the references.

The plate must show ONLY the {kind}: plain neutral background, no labels, no
turnaround or model-sheet layout, no callouts. A single view — full-figure
neutral standing pose for a character, neutral establishing wide for a
location — in even, readable lighting. This plate is what locks continuity for
every panel that follows, so embed every distinguishing visual detail.

Output only the image-gen prompt text. No preamble, no quotes.
"""

PANEL_PROMPT_TEMPLATE = """Write a single image-generation prompt for this
storyboard panel. Output only the prompt text, no preamble.

Shot {shot_id} — {size}, {lens}, {angle}, {movement}
Scene: {slug_line}
What happens in frame: {description}
Beat: {beat}
Mood: {mood}

Grounded research for this scene:
{research}

The image-gen call receives reference plates for every character and the
location in this shot, plus the film's lookboard. Those plates lock likeness,
wardrobe, location and rendering style automatically. Your prompt should:

- Describe framing, staging, blocking, camera height and what the lens does
  at this focal length — that is the whole point of a storyboard panel
- Reference characters by name and name the location, so the model maps each
  attached plate to the right subject
- NOT re-describe character or location appearance — the plates do that
- NOT prescribe an art style — the lookboard does that

Translate the shot spec into visual terms: an ECU on 85mm is a different
frame from a LS on 24mm, and the panel must read as that shot.

Output only the prompt text.
"""
