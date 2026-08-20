import { useEffect, useReducer } from "react";
import { WS } from "../config";
import type { Graph, NodeStatus, WSEvent } from "../types";

type State = { graph: Graph; connected: boolean; log: string[] };

type Action =
  | { kind: "init"; graph: Graph }
  | { kind: "replace"; graph: Graph }
  | { kind: "status"; id: string; status: NodeStatus; meta?: Record<string, unknown> }
  | { kind: "log"; message: string }
  | { kind: "connected"; value: boolean };

function reducer(state: State, action: Action): State {
  switch (action.kind) {
    case "init":
    case "replace":
      return { ...state, graph: action.graph };
    case "status":
      return {
        ...state,
        graph: {
          ...state.graph,
          nodes: state.graph.nodes.map((n) =>
            n.id === action.id
              ? {
                  ...n,
                  status: action.status,
                  // Merge rather than replace: a status event may carry only
                  // the newly-changed keys, and dropping the rest would blank
                  // out an image that is already on screen.
                  meta: action.meta ? { ...n.meta, ...action.meta } : n.meta,
                }
              : n
          ),
        },
      };
    case "log":
      return { ...state, log: [...state.log.slice(-40), action.message] };
    case "connected":
      return { ...state, connected: action.value };
  }
}

const EMPTY: Graph = { nodes: [], edges: [] };

export function useGraphSocket(project: string) {
  const [state, dispatch] = useReducer(reducer, {
    graph: EMPTY,
    connected: false,
    log: [],
  });

  useEffect(() => {
    const ws = new WebSocket(`${WS}/ws/${project}`);
    ws.onopen = () => dispatch({ kind: "connected", value: true });
    ws.onclose = () => dispatch({ kind: "connected", value: false });
    ws.onmessage = (e) => {
      const ev = JSON.parse(e.data) as WSEvent;
      switch (ev.type) {
        case "graph_init":
        case "graph_replace":
          dispatch({ kind: ev.type === "graph_init" ? "init" : "replace", graph: ev.payload });
          break;
        case "node_update":
          dispatch({
            kind: "status",
            id: ev.payload.id,
            status: ev.payload.status,
            meta: ev.payload.meta,
          });
          break;
        case "log":
          dispatch({ kind: "log", message: ev.payload.message });
          break;
      }
    };
    return () => ws.close();
  }, [project]);

  return state;
}
