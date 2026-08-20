import { Handle, Position, type NodeProps } from "reactflow";
import { CardShell, CardHeader, ErrorText } from "./shared";
import type { NodeStatus } from "../../types";

export type BreakdownCounts = {
  characters: number;
  locations: number;
  scenes: number;
  shots: number;
};

export type BreakdownNodeData = {
  label: string;
  status: NodeStatus;
  script: string;
  onScript: (s: string) => void;
  counts?: BreakdownCounts;
  error?: string;
};

const PLACEHOLDER = `INT. DISPATCH OFFICE - NIGHT

MARCUS slides a package across the desk. LENA picks it up.
It is warm.

                    LENA
          How long has this been here?`;

export default function BreakdownNode({ data }: NodeProps<BreakdownNodeData>) {
  return (
    <CardShell status={data.status} kind="breakdown" width={360}>
      <Handle type="target" position={Position.Top} style={{ background: "#52525b" }} />
      <CardHeader label={data.label} kind="breakdown" status={data.status} />

      <div style={{ padding: 10 }}>
        <textarea
          className="nodrag nowheel"
          value={data.script}
          onChange={(e) => data.onScript(e.target.value)}
          placeholder={PLACEHOLDER}
          style={{
            width: "100%",
            height: 150,
            resize: "none",
            boxSizing: "border-box",
            background: "#0f1115",
            color: "#e4e4e7",
            border: "1px solid #232936",
            borderRadius: 8,
            padding: 8,
            fontSize: 11,
            fontFamily: "ui-monospace, SFMono-Regular, monospace",
            lineHeight: 1.45,
          }}
        />
      </div>

      {data.counts && (
        <div
          style={{
            display: "flex",
            borderTop: "1px solid #232936",
            fontFamily: "ui-monospace, monospace",
          }}
        >
          {(
            [
              ["chars", data.counts.characters],
              ["locs", data.counts.locations],
              ["scenes", data.counts.scenes],
              ["shots", data.counts.shots],
            ] as const
          ).map(([label, n]) => (
            <div
              key={label}
              style={{
                flex: 1,
                padding: "6px 4px",
                textAlign: "center",
                borderRight: "1px solid #232936",
              }}
            >
              <div style={{ fontSize: 15, fontWeight: 700, color: "#2dd4bf" }}>{n}</div>
              <div style={{ fontSize: 9, color: "#71717a", letterSpacing: 0.4 }}>{label}</div>
            </div>
          ))}
        </div>
      )}

      <ErrorText error={data.error} />
      <Handle type="source" position={Position.Bottom} style={{ background: "#52525b" }} />
    </CardShell>
  );
}
