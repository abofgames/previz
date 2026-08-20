import { Handle, Position, type NodeProps } from "reactflow";
import { CardShell, CardHeader, ErrorText } from "./shared";
import { KIND_THEMES } from "../kindThemes";
import type { Citation, NodeStatus } from "../../types";

export type ResearchNodeData = {
  label: string;
  status: NodeStatus;
  citations?: Citation[];
  scenesResearched?: number;
  sourceCount?: number;
  error?: string;
  onRetry: () => void;
};

/**
 * The research card is where the agent's work is auditable: every source it
 * actually read is listed and clickable, so a panel's art direction can be
 * traced back to a real page rather than taken on trust.
 */
export default function ResearchNode({ data }: NodeProps<ResearchNodeData>) {
  const theme = KIND_THEMES.research;
  const citations = data.citations ?? [];
  const running = data.status === "running";

  return (
    <CardShell status={data.status} kind="research" width={320}>
      <Handle type="target" position={Position.Top} style={{ background: "#52525b" }} />
      <CardHeader
        label={data.label}
        kind="research"
        status={data.status}
        onRetry={citations.length ? data.onRetry : undefined}
      />

      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 6,
          padding: "6px 10px",
          borderBottom: "1px solid #232936",
          fontSize: 10,
          color: "#71717a",
          fontFamily: "ui-monospace, monospace",
        }}
      >
        <span style={{ color: theme.accent, fontWeight: 700 }}>Parallel Search</span>
        <span>·</span>
        <span>{data.scenesResearched ?? 0} scenes</span>
        <span>·</span>
        <span>{data.sourceCount ?? citations.length} sources</span>
      </div>

      <div className="nowheel" style={{ maxHeight: 190, overflowY: "auto", padding: "6px 0" }}>
        {running && (
          <div style={{ padding: "10px 10px", color: theme.accent, fontSize: 11 }}>
            searching the web…
          </div>
        )}
        {!running && citations.length === 0 && (
          <div style={{ padding: "10px", color: "#52525b", fontSize: 11 }}>
            No sources yet.
          </div>
        )}
        {citations.map((c, i) => (
          <a
            key={c.url + i}
            href={c.url}
            target="_blank"
            rel="noreferrer"
            className="nodrag"
            style={{
              display: "block",
              padding: "6px 10px",
              color: "#d4d4d8",
              textDecoration: "none",
              borderLeft: `2px solid ${theme.accent}55`,
              margin: "2px 8px",
              fontSize: 10.5,
              lineHeight: 1.35,
            }}
          >
            <div style={{ fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis" }}>
              {c.title || c.url}
            </div>
            <div style={{ color: "#52525b", fontSize: 9.5, overflow: "hidden", textOverflow: "ellipsis" }}>
              {hostOf(c.url)}
            </div>
          </a>
        ))}
      </div>

      <ErrorText error={data.error} />
      <Handle type="source" position={Position.Bottom} style={{ background: "#52525b" }} />
    </CardShell>
  );
}

function hostOf(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}
