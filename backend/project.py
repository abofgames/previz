from __future__ import annotations

from pathlib import Path

PROJECTS_ROOT = Path(__file__).resolve().parent.parent / "projects"


class ProjectPaths:
    """Single source of truth for the on-disk layout of a production's
    artifacts.

    The filesystem is the state store: every step writes its artifact through
    one of these properties and checks for existence before recomputing, so a
    restart resumes where it left off and nothing re-burns quota.
    No raw path construction outside this class.
    """

    def __init__(self, name: str, root: Path | None = None) -> None:
        self.name = name
        self.root = (root or PROJECTS_ROOT) / name

    # -- top-level ---------------------------------------------------------
    @property
    def breakdown(self) -> Path:
        return self.root / "breakdown.json"

    @property
    def look_block(self) -> Path:
        return self.root / "look_block.json"

    @property
    def graph(self) -> Path:
        return self.root / "graph.json"

    # -- cache markers -----------------------------------------------------
    # Signature of the inputs each step last ran against, so re-clicking Start
    # with unchanged inputs skips the recompute.
    @property
    def look_inputs_marker(self) -> Path:
        return self.root / ".look_inputs.sha"

    @property
    def script_inputs_marker(self) -> Path:
        return self.root / ".script_inputs.sha"

    # -- inputs ------------------------------------------------------------
    @property
    def script(self) -> Path:
        return self.root / "input" / "script.txt"

    @property
    def look_note(self) -> Path:
        return self.root / "input" / "look_note.txt"

    @property
    def look_refs_dir(self) -> Path:
        return self.root / "input" / "look_refs"

    # -- look development --------------------------------------------------
    @property
    def look_dir(self) -> Path:
        return self.root / "look"

    @property
    def lookboard_image(self) -> Path:
        return self.look_dir / "lookboard.png"

    # -- research ----------------------------------------------------------
    @property
    def research_dir(self) -> Path:
        return self.root / "research"

    def dossier(self, scene_id: str) -> Path:
        return self.research_dir / f"{scene_id}.json"

    # -- reference plates (characters + locations) -------------------------
    @property
    def refs_dir(self) -> Path:
        return self.root / "refs"

    def ref_image(self, ref_id: str) -> Path:
        return self.refs_dir / f"{ref_id}.png"

    def ref_prompt(self, ref_id: str) -> Path:
        return self.refs_dir / f"{ref_id}.prompt.txt"

    # -- storyboard panels -------------------------------------------------
    @property
    def shots_dir(self) -> Path:
        return self.root / "shots"

    def shot_image(self, shot_id: str) -> Path:
        return self.shots_dir / f"{shot_id}.png"

    def shot_prompt(self, shot_id: str) -> Path:
        return self.shots_dir / f"{shot_id}.prompt.txt"

    # -- animatic (optional, Veo) ------------------------------------------
    @property
    def animatic_dir(self) -> Path:
        return self.root / "animatic"

    def animatic_video(self, shot_id: str) -> Path:
        return self.animatic_dir / f"{shot_id}.mp4"

    def ensure_dirs(self) -> None:
        for d in (
            self.root,
            self.look_refs_dir,
            self.look_dir,
            self.research_dir,
            self.refs_dir,
            self.shots_dir,
            self.animatic_dir,
        ):
            d.mkdir(parents=True, exist_ok=True)
