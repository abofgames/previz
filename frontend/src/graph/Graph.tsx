import { useEffect, useRef } from "react";
import ReactFlow, {
  Background,
  Controls as RFControls,
  MarkerType,
  useEdgesState,
  useNodesState,
  type Edge,
  type Node,
} from "reactflow";
import dagre from "dagre";
import type { Citation, Graph as GraphData, GraphNode, NodeKind } from "../types";
import BriefNode from "./nodes/BriefNode";
import LookDevNode from "./nodes/LookDevNode";
import BreakdownNode from "./nodes/BreakdownNode";
import ResearchNode from "./nodes/ResearchNode";
import ImageNode from "./nodes/ImageNode";
import GroupNode from "./nodes/GroupNode";
import AnimaticNode from "./nodes/AnimaticNode";

const nodeTypes = {
  briefNode: BriefNode,
  lookDevNode: LookDevNode,
  breakdownNode: BreakdownNode,
  researchNode: ResearchNode,
  imageNode: ImageNode,
  groupNode: GroupNode,
  animaticNode: AnimaticNode,
};

type Size = { width: number; height: number; rfType: string };

function sizeFor(kind: NodeKind): Size {
  switch (kind) {
    case "brief":
      return { width: 90, height: 90, rfType: "briefNode" };
    case "look_dev":
      return { width: 300, height: 250, rfType: "lookDevNode" };
    case "breakdown":
      return { width: 360, height: 290, rfType: "breakdownNode" };
    case "research":
      return { width: 320, height: 290, rfType: "researchNode" };
    case "lookboard":
      return { width: 280, height: 250, rfType: "imageNode" };
    case "character":
    case "location":
      return { width: 220, height: 350, rfType: "imageNode" };
    case "shot":
      return { width: 280, height: 300, rfType: "imageNode" };
    case "animatic":
      return { width: 280, height: 230, rfType: "animaticNode" };
    case "group":
    default:
      return { width: 160, height: 40, rfType: "groupNode" };
  }
}

/** Image cards are drawn at their real aspect so a panel reads as a frame. */
function aspectFor(kind: NodeKind): string {
  switch (kind) {
    case "shot":
    case "lookboard":
      return "16 / 9";
    case "character":
    case "location":
      return "3 / 4";
    default:
      return "1 / 1";
  }
}

export type GraphCallbacks = {
  files: File[];
  onFiles: (f: File[]) => void;
  script: string;
  onScript: (s: string) => void;
  lookNote: string;
  onLookNote: (s: string) => void;
  onRetry: (nodeId: string) => void;
  onExpand: (nodeId: string) => void;
};

function str(v: unknown): string | undefined {
  return typeof v === "string" ? v : undefined;
}

function buildData(node: GraphNode, cb: GraphCallbacks) {
  const meta = (node.meta || {}) as Record<string, unknown>;
  const base = { label: node.label, status: node.status, error: str(meta.error) };

  switch (node.kind) {
    case "look_dev":
      return { ...base, files: cb.files, onFiles: cb.onFiles,
               lookNote: cb.lookNote, onLookNote: cb.onLookNote };

    case "breakdown":
      return { ...base, script: cb.script, onScript: cb.onScript,
               counts: meta.counts as Record<string, number> | undefined };

    case "research":
      return {
        ...base,
        citations: (meta.citations as Citation[] | undefined) ?? [],
        scenesResearched: meta.scenes_researched as number | undefined,
        sourceCount: meta.source_count as number | undefined,
        onRetry: () => cb.onRetry(node.id),
      };

    case "animatic":
      return { ...base, videoUrl: str(meta.video_url), onRetry: () => cb.onRetry(node.id) };

    case "lookboard":
    case "character":
    case "location":
    case "shot":
      return {
        ...base,
        kind: node.kind,
        aspect: aspectFor(node.kind),
        imageUrl: str(meta.image_url),
        prompt: str(meta.prompt),
        spec: node.kind === "shot"
          ? {
              size: str(meta.size), lens: str(meta.lens),
              angle: str(meta.angle), movement: str(meta.movement),
              description: str(meta.description),
            }
          : undefined,
        onRetry: () => cb.onRetry(node.id),
        onExpand: () => cb.onExpand(node.id),
      };

    default:
      return base;
  }
}

function layout(graph: GraphData, cb: GraphCallbacks): { nodes: Node[]; edges: Edge[] } {
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: "TB", nodesep: 44, ranksep: 90 });

  const sizes = new Map<string, Size>();
  for (const n of graph.nodes) {
    const s = sizeFor(n.kind);
    sizes.set(n.id, s);
    g.setNode(n.id, { width: s.width, height: s.height });
  }
  for (const e of graph.edges) {
    if (sizes.has(e.source) && sizes.has(e.target)) g.setEdge(e.source, e.target);
  }
  dagre.layout(g);

  const nodes: Node[] = graph.nodes.map((n) => {
    const s = sizes.get(n.id)!;
    const pos = g.node(n.id);
    return {
      id: n.id,
      type: s.rfType,
      position: { x: pos.x - s.width / 2, y: pos.y - s.height / 2 },
      data: buildData(n, cb),
    };
  });

  const edges: Edge[] = graph.edges.map((e, i) => ({
    id: `${e.source}->${e.target}-${i}`,
    source: e.source,
    target: e.target,
    type: "smoothstep",
    animated: e.kind === "fans_out_to",
    markerEnd: { type: MarkerType.ArrowClosed, color: "#52525b" },
    style: { stroke: "#52525b", strokeWidth: 1.5 },
  }));

  return { nodes, edges };
}

/** Identity of the graph's *shape*, ignoring status and meta. */
function structureKey(g: GraphData): string {
  const n = g.nodes.map((x) => x.id).sort().join(",");
  const e = g.edges.map((x) => `${x.source}>${x.target}`).sort().join(",");
  return `${n}|${e}`;
}

export default function Graph({
  graph,
  connected,
  project,
  callbacks,
}: {
  graph: GraphData;
  connected: boolean;
  project: string;
  callbacks: GraphCallbacks;
}) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const sKey = structureKey(graph);
  const lastKey = useRef<string>("");

  // Two effects, deliberately. Re-running the dagre layout on every status or
  // meta update remounts every node and makes the whole graph flicker, so the
  // layout is recomputed only when the set of nodes or edges actually changes.
  useEffect(() => {
    if (lastKey.current === sKey) return;
    lastKey.current = sKey;
    const { nodes: ln, edges: le } = layout(graph, callbacks);
    setNodes(ln);
    setEdges(le);
  }, [sKey, graph, callbacks, setNodes, setEdges]);

  // ...and this one patches data in place on every update, leaving positions
  // (including anything the user has dragged) untouched.
  useEffect(() => {
    setNodes((curr) =>
      curr.map((rn) => {
        const gn = graph.nodes.find((x) => x.id === rn.id);
        return gn ? { ...rn, data: buildData(gn, callbacks) } : rn;
      })
    );
  }, [graph, callbacks, setNodes]);

  return (
    <div style={{ position: "relative", width: "100%", height: "100%" }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        fitView
        minZoom={0.1}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#222831" gap={24} />
        <RFControls />
      </ReactFlow>
      <div
        style={{
          position: "absolute",
          top: 12,
          left: 12,
          color: connected ? "#bbf7d0" : "#fecaca",
          fontFamily: "ui-monospace, monospace",
          fontSize: 12,
          background: "#0f1115cc",
          padding: "4px 10px",
          borderRadius: 6,
          border: `1px solid ${connected ? "#22c55e" : "#ef4444"}`,
        }}
      >
        {connected ? "● live" : "○ disconnected"} · {project}
      </div>
    </div>
  );
}
