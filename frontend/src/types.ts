export type NodeStatus = "pending" | "running" | "complete" | "failed" | "stale";

export type NodeKind =
  | "brief"
  | "look_dev"
  | "breakdown"
  | "research"
  | "lookboard"
  | "group"
  | "character"
  | "location"
  | "shot"
  | "animatic";

export interface Citation {
  title: string;
  url: string;
}

export interface GraphNode {
  id: string;
  kind: NodeKind;
  label: string;
  status: NodeStatus;
  meta?: Record<string, unknown>;
}

export interface GraphEdge {
  source: string;
  target: string;
  kind: "depends_on" | "fans_out_to";
}

export interface Graph {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export type WSEvent =
  | { type: "graph_init"; payload: Graph }
  | { type: "graph_replace"; payload: Graph }
  | {
      type: "node_update";
      payload: { id: string; status: NodeStatus; meta?: Record<string, unknown> };
    }
  | { type: "log"; payload: { message: string } };
