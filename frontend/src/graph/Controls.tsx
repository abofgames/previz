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
  const hasScript = script.trim().length > 0;
  // The graph only grows past its three input cards once a breakdown has run,
  // so node count is a reliable read on whether this production has started.
  const hasRun = graph.nodes.length > 3;

  const drawable = graph.nodes.filter(
    (n) => n.kind === "shot" || n.kind === "character" || n.kind === "location"
  );
  const drawn = drawable.filter((n) => n.status === "complete").length;

  const onStart = () => {
    const fd = new FormData();
    fd.append("script", script);
    fd.append("look_note", lookNote);
    // No Content-Type header — the browser sets the multipart boundary itself.
    for (const f of files) fd.append("look_refs", f, f.name);
    fetch(`${API}/api/projects/${project}/start`, { method: "POST", body: fd });
  };

  // One line saying what to do next, so a "pending" card is never a puzzle.
  const hint = anyRunning
    ? "Agents are working — the graph updates live"
    : !hasScript
    ? "Start with 🎲 Write me a scene, or paste your own screenplay"
    : !hasRun
    ? "Script ready — press Break down script"
    : drawn < drawable.length
    ? `Press Draw on any card — ${drawn}/${drawable.length} drawn`
    : "Every card drawn";

  const disabled = anyRunning || !hasScript;
  const urgent = hasScript && !hasRun && !anyRunning;

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

      <div
        style={{
          flex: 1,
          minWidth: 0,
          display: "flex",
          alignItems: "center",
          gap: 10,
        }}
      >
        <span
          style={{
            color: urgent ? "#34d399" : "#71717a",
            fontSize: 11.5,
            fontWeight: urgent ? 700 : 400,
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
          }}
        >
          {hint}
        </span>
        {log.length > 0 && (
          <span
            style={{
              color: "#3f3f46",
              fontSize: 10.5,
              fontFamily: "ui-monospace, monospace",
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
            }}
          >
            {log[log.length - 1]}
          </span>
        )}
      </div>

      <button onClick={onStart} disabled={disabled} style={btn(disabled, urgent)}>
        {anyRunning ? "Working…" : hasRun ? "Re-run breakdown" : "▶ Break down script"}
      </button>
    </div>
  );
}

function btn(disabled: boolean, urgent: boolean): CSSProperties {
  return {
    background: disabled ? "#1f2530" : urgent ? "#34d399" : "#3b82f6",
    color: disabled ? "#71717a" : "#0f1115",
    border: "none",
    borderRadius: 6,
    padding: "7px 16px",
    fontSize: 13,
    fontWeight: 700,
    cursor: disabled ? "default" : "pointer",
    whiteSpace: "nowrap",
    boxShadow: urgent ? "0 0 0 3px #34d39933" : "none",
  };
}
