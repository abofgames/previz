import type { CSSProperties } from "react";
import { API } from "../config";
import type { Graph } from "../types";

export default function Controls({
  graph,
  project,
  script,
  lookNote,
  files,
  log,
}: {
  graph: Graph;
  project: string;
  script: string;
  lookNote: string;
  files: File[];
  log: string[];
}) {
  const anyRunning = graph.nodes.some((n) => n.status === "running");
  const drawn = graph.nodes.filter(
    (n) => (n.kind === "shot" || n.kind === "character" || n.kind === "location") &&
      n.status === "complete"
  ).length;
  const drawable = graph.nodes.filter(
    (n) => n.kind === "shot" || n.kind === "character" || n.kind === "location"
  ).length;

  const onStart = () => {
    const fd = new FormData();
    fd.append("script", script);
    fd.append("look_note", lookNote);
    // No Content-Type header — the browser sets the multipart boundary itself.
    for (const f of files) fd.append("look_refs", f, f.name);
    fetch(`${API}/api/projects/${project}/start`, { method: "POST", body: fd });
  };

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 12,
        padding: "10px 16px",
        background: "#13161d",
        borderBottom: "1px solid #232936",
        color: "#e4e4e7",
        fontFamily: "ui-sans-serif, system-ui, sans-serif",
        fontSize: 13,
      }}
    >
      <strong style={{ letterSpacing: 1, fontWeight: 800 }}>previz</strong>
      <span style={{ color: "#52525b", fontSize: 11 }}>agentic pre-production</span>
      <span style={{ color: "#52525b" }}>·</span>
      <span style={{ color: "#a1a1aa" }}>{project}</span>

      {drawable > 0 && (
        <span style={{ color: "#71717a", fontSize: 11, fontFamily: "ui-monospace, monospace" }}>
          {drawn}/{drawable} drawn
        </span>
      )}

      <div style={{ flex: 1, minWidth: 0 }}>
        {log.length > 0 && (
          <span
            style={{
              color: "#52525b",
              fontSize: 11,
              fontFamily: "ui-monospace, monospace",
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
              display: "block",
            }}
          >
            {log[log.length - 1]}
          </span>
        )}
      </div>

      <button onClick={onStart} disabled={anyRunning} style={btn("#3b82f6", anyRunning)}>
        {anyRunning ? "Working…" : "Break down script"}
      </button>
    </div>
  );
}

function btn(color: string, disabled: boolean): CSSProperties {
  return {
    background: disabled ? "#1f2530" : color,
    color: disabled ? "#71717a" : "#0f1115",
    border: "none",
    borderRadius: 6,
    padding: "6px 14px",
    fontSize: 13,
    fontWeight: 700,
    cursor: disabled ? "default" : "pointer",
    whiteSpace: "nowrap",
  };
}
