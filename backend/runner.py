from __future__ import annotations

import asyncio
import hashlib
import logging
import time

from . import ids
from .clients.factory import (
    make_image_client,
    make_search_client,
    make_text_client,
    veo_enabled,
)
from .models import (
    Graph,
    GraphEdge,
    GraphNode,
    LookBlock,
    NodeStatus,
    ResearchDossier,
    ScriptBreakdown,
    WSEvent,
)
from .project import ProjectPaths
from .state import EventBus, save_graph
from .steps import breakdown as breakdown_step
from .steps import look_dev, panels, plates, refgen
from .steps import research as research_step

log = logging.getLogger("runner")


def initial_graph() -> Graph:
    """Pre-Start graph: the brief plus the two things it feeds. Everything
    downstream appears once the script has been broken down."""
    return Graph(
        nodes=[
            GraphNode(id=ids.NODE_BRIEF, kind="brief", label="Production Brief"),
            GraphNode(id=ids.NODE_LOOK_DEV, kind="look_dev", label="Look Development"),
            GraphNode(id=ids.NODE_BREAKDOWN, kind="breakdown", label="Script Breakdown"),
        ],
        edges=[
            GraphEdge(source=ids.NODE_BRIEF, target=ids.NODE_LOOK_DEV),
            GraphEdge(source=ids.NODE_BRIEF, target=ids.NODE_BREAKDOWN),
        ],
    )


def build_exploded_graph(b: ScriptBreakdown, *, with_animatics: bool = False) -> Graph:
    """The full canonical post-breakdown graph.

    Pure — no I/O, no publishing — so the live runner and restart-rehydration
    share one definition of the topology and can never disagree about it. All
    nodes come back ``pending``; callers overlay live or on-disk status.
    """
    nodes: list[GraphNode] = [
        GraphNode(id=ids.NODE_BRIEF, kind="brief", label="Production Brief"),
        GraphNode(id=ids.NODE_LOOK_DEV, kind="look_dev", label="Look Development"),
        GraphNode(id=ids.NODE_BREAKDOWN, kind="breakdown", label="Script Breakdown"),
        GraphNode(id=ids.NODE_LOOKBOARD, kind="lookboard", label="Lookboard"),
        GraphNode(id=ids.NODE_RESEARCH, kind="research", label="Visual Research"),
        GraphNode(id=ids.GROUP_CHARACTERS, kind="group", label="Characters"),
        GraphNode(id=ids.GROUP_LOCATIONS, kind="group", label="Locations"),
        GraphNode(id=ids.GROUP_SHOTS, kind="group", label="Shot List"),
    ]
    edges: list[GraphEdge] = [
        GraphEdge(source=ids.NODE_BRIEF, target=ids.NODE_LOOK_DEV),
        GraphEdge(source=ids.NODE_BRIEF, target=ids.NODE_BREAKDOWN),
        GraphEdge(source=ids.NODE_LOOK_DEV, target=ids.NODE_LOOKBOARD),
        GraphEdge(source=ids.NODE_BREAKDOWN, target=ids.NODE_RESEARCH),
        GraphEdge(source=ids.NODE_RESEARCH, target=ids.GROUP_CHARACTERS),
        GraphEdge(source=ids.NODE_RESEARCH, target=ids.GROUP_LOCATIONS),
        GraphEdge(source=ids.NODE_RESEARCH, target=ids.GROUP_SHOTS),
        # The look conditions every generated image, so it feeds each group
        # rather than being wired to all N children individually.
        GraphEdge(source=ids.NODE_LOOKBOARD, target=ids.GROUP_CHARACTERS),
        GraphEdge(source=ids.NODE_LOOKBOARD, target=ids.GROUP_LOCATIONS),
        GraphEdge(source=ids.NODE_LOOKBOARD, target=ids.GROUP_SHOTS),
    ]

    for char in b.characters:
        nid = ids.char_ref(char.id)
        nodes.append(GraphNode(id=nid, kind="character", label=char.name,
                               meta={"character_id": char.id}))
        edges.append(GraphEdge(source=ids.GROUP_CHARACTERS, target=nid, kind="fans_out_to"))

    for loc in b.locations:
        nid = ids.loc_ref(loc.id)
        nodes.append(GraphNode(id=nid, kind="location", label=loc.name,
                               meta={"location_id": loc.id}))
        edges.append(GraphEdge(source=ids.GROUP_LOCATIONS, target=nid, kind="fans_out_to"))

    char_ids = {c.id for c in b.characters}
    loc_ids = {l.id for l in b.locations}

    for shot in b.shots:
        nodes.append(GraphNode(
            id=shot.id, kind="shot",
            label=f"{shot.size} · {shot.lens}",
            meta={
                "shot_id": shot.id, "scene_id": shot.scene_id,
                "size": shot.size, "lens": shot.lens,
                "movement": shot.movement, "angle": shot.angle,
                "description": shot.description,
            },
        ))
        edges.append(GraphEdge(source=ids.GROUP_SHOTS, target=shot.id, kind="fans_out_to"))
        # Plates the panel is conditioned on. Guarded because a dangling id
        # would render as an edge to a node that does not exist.
        if shot.location_id in loc_ids:
            edges.append(GraphEdge(source=ids.loc_ref(shot.location_id), target=shot.id))
        for cid in shot.character_ids:
            if cid in char_ids:
                edges.append(GraphEdge(source=ids.char_ref(cid), target=shot.id))

        if with_animatics:
            aid = ids.animatic(shot.id)
            nodes.append(GraphNode(id=aid, kind="animatic",
                                   label=f"Animatic {shot.id}",
                                   meta={"shot_id": shot.id}))
            edges.append(GraphEdge(source=shot.id, target=aid))

    return Graph(nodes=nodes, edges=edges)


class ProjectRunner:
    """Owns one production's pipeline state.

    Holds the last submitted inputs so a single card can be regenerated without
    resubmitting the whole brief.
    """

    def __init__(self, paths: ProjectPaths, bus: EventBus) -> None:
        self.paths = paths
        self.bus = bus
        self.graph = initial_graph()
        self.text_client = make_text_client()
        self.image_client = make_image_client()
        self.search_client = make_search_client(cache_dir=paths.research_dir)

        self.script = paths.script.read_text() if paths.script.exists() else ""
        self.look_note = paths.look_note.read_text() if paths.look_note.exists() else ""
        self._run_task: asyncio.Task | None = None
        self._rehydrate()

    # -- public ------------------------------------------------------------

    def snapshot(self) -> Graph:
        return self.graph

    async def start(self, script: str, look_note: str = "") -> None:
        if self._run_task and not self._run_task.done():
            return
        self.script = script
        self.look_note = look_note
        self._run_task = asyncio.create_task(self._execute())

    async def retry(self, node_id: str) -> None:
        node = self._find(node_id)
        if node is not None:
            asyncio.create_task(self._retry_node(node))

    async def write_random_script(self, genre: str = "") -> dict:
        """Produce a screenplay to storyboard when the user hasn't got one.

        Gemini writes an original scene — text-only, so this works on the free
        tier — and a curated sample stands in if that call fails.
        """
        from .samples import random_script

        try:
            script = (await self.text_client.write_script(genre)).strip()
            if script:
                return {"script": script, "source": "gemini"}
        except Exception as exc:  # noqa: BLE001
            log.warning("write_script failed, using a curated sample: %s", exc)
        sample = random_script()
        return {"script": sample["script"], "title": sample["title"], "source": "sample"}

    async def generate_random_look(self) -> dict:
        """Pick a look preset and produce reference frames for it, so the user
        doesn't have to go find film stills before they can start."""
        from .samples import random_look

        preset = random_look()
        await self._begin(ids.NODE_LOOK_DEV)
        try:
            written = await refgen.generate_look_refs(
                self.paths, preset, image_client=self.image_client
            )
        except Exception as exc:  # noqa: BLE001
            await self._fail(ids.NODE_LOOK_DEV, "look reference generation", exc)
            raise

        self.look_note = preset["note"]
        urls = [self._url_for(p) for p in written]
        await self._set_meta(ids.NODE_LOOK_DEV, {
            "ref_urls": urls,
            "look_name": preset["name"],
            "look_note": preset["note"],
        })
        await self._set_status(ids.NODE_LOOK_DEV, NodeStatus.pending)
        return {"name": preset["name"], "note": preset["note"], "ref_urls": urls}

    # -- execution ---------------------------------------------------------

    async def _execute(self) -> None:
        """Breakdown and look development are independent, so they run
        concurrently and each surfaces its own failure onto its own node.

        Image generation is deliberately NOT started here. Plates and panels
        are click-to-generate, which keeps a run's image quota at zero until
        the user asks for a specific frame.
        """
        await self._set_status(ids.NODE_BRIEF, NodeStatus.complete)
        results = await asyncio.gather(
            self._look_branch(), self._script_branch(), return_exceptions=True
        )
        failures = [r for r in results if isinstance(r, BaseException)]
        await self._publish_log(
            f"pre-production finished with {len(failures)} failure(s)"
            if failures else "pre-production ready — pick a card to draw"
        )

    async def _look_branch(self) -> None:
        await self._begin(ids.NODE_LOOK_DEV)
        sig = self._look_sig()
        force = _read_marker(self.paths.look_inputs_marker) != sig
        try:
            await look_dev.run(self.paths, self.text_client, self.look_note, force=force)
        except Exception as exc:
            await self._fail(ids.NODE_LOOK_DEV, "look development", exc)
            raise
        _write_marker(self.paths.look_inputs_marker, sig)
        await self._set_status(ids.NODE_LOOK_DEV, NodeStatus.complete)

        if self._find(ids.NODE_LOOKBOARD) is None:
            self.graph.nodes.append(
                GraphNode(id=ids.NODE_LOOKBOARD, kind="lookboard", label="Lookboard")
            )
            self.graph.edges.append(
                GraphEdge(source=ids.NODE_LOOK_DEV, target=ids.NODE_LOOKBOARD)
            )
            await self._publish_graph_replace()
        await self._set_meta(ids.NODE_LOOKBOARD, {
            "image_url": self._url_for(self.paths.lookboard_image),
            "look": self._look_block_dict(),
        })
        await self._set_status(ids.NODE_LOOKBOARD, NodeStatus.complete)

    async def _script_branch(self) -> None:
        await self._begin(ids.NODE_BREAKDOWN)
        sig = self._script_sig()
        force = _read_marker(self.paths.script_inputs_marker) != sig
        try:
            b = await breakdown_step.run(
                self.paths, self.text_client, self.script, force=force
            )
        except Exception as exc:
            await self._fail(ids.NODE_BREAKDOWN, "script breakdown", exc)
            raise
        _write_marker(self.paths.script_inputs_marker, sig)
        await self._set_meta(ids.NODE_BREAKDOWN, {
            "counts": {
                "characters": len(b.characters), "locations": len(b.locations),
                "scenes": len(b.scenes), "shots": len(b.shots),
            },
        })
        await self._set_status(ids.NODE_BREAKDOWN, NodeStatus.complete)

        await self._explode_fanout(b)

        await self._begin(ids.NODE_RESEARCH)
        try:
            dossiers = await research_step.run_all(
                self.paths, b,
                text_client=self.text_client, search_client=self.search_client,
                look_note=self.look_note, force=force,
            )
        except Exception as exc:
            await self._fail(ids.NODE_RESEARCH, "visual research", exc)
            raise
        await self._set_meta(ids.NODE_RESEARCH, self._research_meta(dossiers))
        await self._set_status(ids.NODE_RESEARCH, NodeStatus.complete)

        # The groups are labels over click-to-generate children; marking them
        # complete is what signals "ready for you to drive".
        for gid in (ids.GROUP_CHARACTERS, ids.GROUP_LOCATIONS, ids.GROUP_SHOTS):
            await self._set_status(gid, NodeStatus.complete)

    # -- graph mutation ----------------------------------------------------

    async def _explode_fanout(self, b: ScriptBreakdown) -> None:
        """Rebuild the downstream graph, carrying over the live status and meta
        of nodes that already exist so the fan-out never resets progress the
        look branch has already made."""
        prior = {n.id: n for n in self.graph.nodes}
        canonical = build_exploded_graph(b, with_animatics=veo_enabled())
        for n in canonical.nodes:
            old = prior.get(n.id)
            if old is not None:
                n.status = old.status
                n.meta = {**n.meta, **old.meta}
        self.graph = canonical
        await self._publish_graph_replace()

    # -- per-card generation ----------------------------------------------

    async def _retry_node(self, node: GraphNode) -> None:
        try:
            if node.kind == "lookboard":
                await self._begin(node.id)
                await look_dev.run(self.paths, self.text_client, self.look_note, force=True)
                await self._set_meta(node.id, {
                    "image_url": self._url_for(self.paths.lookboard_image),
                    "look": self._look_block_dict(),
                })
                await self._set_status(node.id, NodeStatus.complete)
                return

            b = self._load_breakdown()
            if b is None:
                raise RuntimeError("run the script breakdown first")

            if node.kind == "research":
                await self._begin(node.id)
                dossiers = await research_step.run_all(
                    self.paths, b,
                    text_client=self.text_client, search_client=self.search_client,
                    look_note=self.look_note, force=True,
                )
                await self._set_meta(node.id, self._research_meta(dossiers))
                await self._set_status(node.id, NodeStatus.complete)
                return

            if node.kind == "character":
                cid = node.meta.get("character_id")
                char = next(c for c in b.characters if c.id == cid)
                await self._begin(node.id)
                await plates.gen_character(
                    self.paths, char,
                    text_client=self.text_client, image_client=self.image_client,
                    look=self._load_look(), dossier=self._dossier_for_character(b, cid),
                    force=True,
                )
                await self._publish_artifact(node.id, ids.char_ref(char.id), kind="ref")
                return

            if node.kind == "location":
                lid = node.meta.get("location_id")
                loc = next(l for l in b.locations if l.id == lid)
                await self._begin(node.id)
                await plates.gen_location(
                    self.paths, loc,
                    text_client=self.text_client, image_client=self.image_client,
                    look=self._load_look(), dossier=self._dossier_for_location(b, lid),
                    force=True,
                )
                await self._publish_artifact(node.id, ids.loc_ref(loc.id), kind="ref")
                return

            if node.kind == "shot":
                shot = next(s for s in b.shots if s.id == node.meta.get("shot_id"))
                await self._begin(node.id)
                await panels.gen_panel(
                    self.paths, shot, b,
                    text_client=self.text_client, image_client=self.image_client,
                    dossier=research_step.load(self.paths, shot.scene_id),
                    force=True,
                )
                await self._publish_artifact(node.id, shot.id, kind="shot")
                return

            if node.kind == "animatic":
                shot = next(s for s in b.shots if s.id == node.meta.get("shot_id"))
                await self._begin(node.id)
                await panels.gen_animatic(
                    self.paths, shot, image_client=self.image_client, force=True
                )
                await self._set_meta(node.id, {
                    "video_url": self._url_for(self.paths.animatic_video(shot.id)),
                })
                await self._set_status(node.id, NodeStatus.complete)
                return

        except Exception as exc:  # noqa: BLE001 — every failure belongs on the card
            log.exception("generate failed for %s", node.id)
            await self._fail(node.id, node.id, exc)

    async def _publish_artifact(self, node_id: str, artifact_id: str, *, kind: str) -> None:
        image = (
            self.paths.ref_image(artifact_id) if kind == "ref"
            else self.paths.shot_image(artifact_id)
        )
        prompt = (
            self.paths.ref_prompt(artifact_id) if kind == "ref"
            else self.paths.shot_prompt(artifact_id)
        )
        meta = {"image_url": self._url_for(image)}
        if prompt.exists():
            meta["prompt"] = prompt.read_text()
        await self._set_meta(node_id, meta)
        await self._set_status(node_id, NodeStatus.complete)

    # -- rehydration (restart persistence) ---------------------------------

    def _rehydrate(self) -> None:
        """Rebuild the graph from on-disk artifacts at construction, so a
        backend restart resumes the production instead of dropping the user
        back to three empty nodes. The filesystem is the source of truth."""
        b = self._load_breakdown()
        if b is None:
            return

        graph = build_exploded_graph(b, with_animatics=veo_enabled())
        by_id = {n.id: n for n in graph.nodes}

        def done(node_id: str, image=None, prompt=None, extra: dict | None = None) -> None:
            node = by_id.get(node_id)
            if node is None:
                return
            node.status = NodeStatus.complete
            meta = dict(extra or {})
            if image is not None:
                meta["image_url"] = self._url_for(image)
            if prompt is not None and prompt.exists():
                meta["prompt"] = prompt.read_text()
            node.meta = {**node.meta, **meta}

        done(ids.NODE_BRIEF)
        done(ids.NODE_BREAKDOWN, extra={"counts": {
            "characters": len(b.characters), "locations": len(b.locations),
            "scenes": len(b.scenes), "shots": len(b.shots),
        }})
        for gid in (ids.GROUP_CHARACTERS, ids.GROUP_LOCATIONS, ids.GROUP_SHOTS):
            done(gid)

        if self.paths.look_block.exists():
            done(ids.NODE_LOOK_DEV)
        if self.paths.lookboard_image.exists():
            done(ids.NODE_LOOKBOARD, image=self.paths.lookboard_image,
                 extra={"look": self._look_block_dict()})

        dossiers = {
            s.id: d for s in b.scenes
            if (d := research_step.load(self.paths, s.id)) is not None
        }
        if dossiers:
            done(ids.NODE_RESEARCH, extra=self._research_meta(dossiers))

        for char in b.characters:
            rid = ids.char_ref(char.id)
            if self.paths.ref_image(rid).exists():
                done(rid, self.paths.ref_image(rid), self.paths.ref_prompt(rid))
        for loc in b.locations:
            rid = ids.loc_ref(loc.id)
            if self.paths.ref_image(rid).exists():
                done(rid, self.paths.ref_image(rid), self.paths.ref_prompt(rid))
        for shot in b.shots:
            if self.paths.shot_image(shot.id).exists():
                done(shot.id, self.paths.shot_image(shot.id),
                     self.paths.shot_prompt(shot.id))
            vid = self.paths.animatic_video(shot.id)
            if vid.exists():
                done(ids.animatic(shot.id), extra={"video_url": self._url_for(vid)})

        self.graph = graph
        log.info("rehydrated %s (%d nodes) from disk", self.paths.name, len(graph.nodes))

    # -- loading helpers ---------------------------------------------------

    def _load_breakdown(self) -> ScriptBreakdown | None:
        if not self.paths.breakdown.exists():
            return None
        try:
            return ScriptBreakdown.model_validate_json(self.paths.breakdown.read_text())
        except ValueError as exc:
            log.warning("cannot read breakdown: %s", exc)
            return None

    def _load_look(self) -> LookBlock | None:
        if not self.paths.look_block.exists():
            return None
        try:
            return LookBlock.model_validate_json(self.paths.look_block.read_text())
        except ValueError:
            return None

    def _look_block_dict(self) -> dict:
        look = self._load_look()
        return look.model_dump() if look else {}

    def _research_meta(self, dossiers: dict[str, ResearchDossier]) -> dict:
        """Flatten every scene's citations into one deduped list for the card.

        The citation list is the visible proof that the panels are grounded in
        real sources rather than invented, so it goes in the UI, not just a file.
        """
        seen: set[str] = set()
        citations = []
        for dossier in dossiers.values():
            for c in dossier.citations:
                if c.url in seen:
                    continue
                seen.add(c.url)
                citations.append({"title": c.title, "url": c.url})
        return {
            "citations": citations,
            "scenes_researched": len(dossiers),
            "source_count": len(citations),
        }

    def _dossier_for_character(self, b: ScriptBreakdown, cid: str) -> ResearchDossier | None:
        """A character's plate uses the first scene they appear in — that is
        where their wardrobe and period were actually researched."""
        for scene in b.scenes:
            if cid in scene.character_ids:
                return research_step.load(self.paths, scene.id)
        return None

    def _dossier_for_location(self, b: ScriptBreakdown, lid: str) -> ResearchDossier | None:
        for scene in b.scenes:
            if scene.location_id == lid:
                return research_step.load(self.paths, scene.id)
        return None

    # -- input signatures (idempotent Start) -------------------------------

    def _look_sig(self) -> str:
        files = sorted(
            p for p in self.paths.look_refs_dir.glob("*")
            if p.is_file() and not p.name.startswith(".")
        )
        parts = [f"{p.name}:{p.stat().st_size}" for p in files] + [self.look_note]
        return hashlib.sha256("|".join(parts).encode()).hexdigest()

    def _script_sig(self) -> str:
        return hashlib.sha256(self.script.encode()).hexdigest()

    # -- graph/event helpers -----------------------------------------------

    def _find(self, node_id: str) -> GraphNode | None:
        return next((n for n in self.graph.nodes if n.id == node_id), None)

    def _url_for(self, path) -> str:
        """Local artifact path → /projects/... URL, with a cache-busting query
        so a regenerated image replaces the old one in the browser immediately."""
        rel = path.relative_to(self.paths.root.parent)
        return f"/projects/{rel.as_posix()}?v={int(time.time() * 1000)}"

    async def _set_status(self, node_id: str, status: NodeStatus) -> None:
        node = self._find(node_id)
        if node is None:
            return
        node.status = status
        await self.bus.publish(WSEvent(
            type="node_update", payload={"id": node_id, "status": status.value}
        ))

    async def _set_meta(self, node_id: str, meta: dict) -> None:
        node = self._find(node_id)
        if node is None:
            return
        node.meta = {**node.meta, **meta}
        await self.bus.publish(WSEvent(
            type="node_update",
            payload={"id": node_id, "status": node.status.value, "meta": node.meta},
        ))

    async def _begin(self, node_id: str) -> None:
        """Move a node to running, clearing any error left from a prior run."""
        node = self._find(node_id)
        if node is not None and node.meta.get("error"):
            await self._set_meta(node_id, {"error": None})
        await self._set_status(node_id, NodeStatus.running)

    async def _fail(self, node_id: str, what: str, exc: Exception) -> None:
        msg = str(exc).strip() or exc.__class__.__name__
        await self._set_meta(node_id, {"error": msg})
        await self._set_status(node_id, NodeStatus.failed)
        await self._publish_log(f"{what} failed: {msg}")

    async def _publish_graph_replace(self) -> None:
        save_graph(self.paths.graph, self.graph)
        await self.bus.publish(WSEvent(type="graph_replace", payload=self.graph.model_dump()))

    async def _publish_log(self, message: str) -> None:
        await self.bus.publish(WSEvent(type="log", payload={"message": message}))


def _read_marker(path) -> str:
    try:
        return path.read_text().strip()
    except OSError:
        return ""


def _write_marker(path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value)


_BUS = EventBus()
_RUNNERS: dict[str, ProjectRunner] = {}


def get_runner(project: str) -> ProjectRunner:
    if project not in _RUNNERS:
        paths = ProjectPaths(project)
        paths.ensure_dirs()
        _RUNNERS[project] = ProjectRunner(paths, _BUS)
    return _RUNNERS[project]
