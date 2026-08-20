import { useRef } from "react";
import { Handle, Position, type NodeProps } from "reactflow";
import { CardShell, CardHeader, ErrorText } from "./shared";
import { KIND_THEMES } from "../kindThemes";
import { API } from "../../config";
import type { NodeStatus } from "../../types";

export type LookDevNodeData = {
  label: string;
  status: NodeStatus;
  files: File[];
  onFiles: (f: File[]) => void;
  lookNote: string;
  onLookNote: (s: string) => void;
  refUrls?: string[];
  lookName?: string;
  onRandomLook: () => void;
  busy?: boolean;
  error?: string;
};

export default function LookDevNode({ data }: NodeProps<LookDevNodeData>) {
  const inputRef = useRef<HTMLInputElement>(null);
  const theme = KIND_THEMES.look_dev;
  const hasLook =
    (data.refUrls?.length ?? 0) > 0 ||
    data.files.length > 0 ||
    data.lookNote.trim().length > 0;

  return (
    <CardShell status={data.status} kind="look_dev" width={300}>
      <Handle type="target" position={Position.Top} style={{ background: "#52525b" }} />
      <CardHeader
        label={data.label}
        kind="look_dev"
        status={data.status}
        ready={hasLook && data.status === "pending"}
        pill={
          data.status === "pending"
            ? hasLook
              ? "ready"
              : "optional"
            : undefined
        }
      />

      <div style={{ padding: 10, display: "flex", flexDirection: "column", gap: 8 }}>
        <button
          onClick={data.onRandomLook}
          disabled={data.busy}
          className="nodrag"
          style={{
            background: data.busy ? "#1f2530" : `${theme.accent}22`,
            color: data.busy ? "#71717a" : theme.accent,
            border: `1px solid ${theme.accent}66`,
            borderRadius: 8,
            padding: "7px 10px",
            fontSize: 11,
            fontWeight: 700,
            cursor: data.busy ? "default" : "pointer",
          }}
        >
          {data.busy ? "generating…" : "🎲 Generate a look"}
        </button>

        {data.refUrls && data.refUrls.length > 0 && (
          <div>
            {data.lookName && (
              <div style={{ fontSize: 10, color: theme.accent, fontWeight: 700, marginBottom: 4 }}>
                {data.lookName}
              </div>
            )}
            <div style={{ display: "flex", gap: 4 }}>
              {data.refUrls.map((u) => (
                <img
                  key={u}
                  src={API + u}
                  alt="look reference"
                  style={{
                    flex: 1,
                    minWidth: 0,
                    height: 46,
                    objectFit: "cover",
                    borderRadius: 4,
                    display: "block",
                  }}
                />
              ))}
            </div>
          </div>
        )}

        <label
          className="nodrag"
          onClick={() => inputRef.current?.click()}
          style={{
            border: `1.5px dashed ${theme.accent}66`,
            borderRadius: 8,
            padding: "10px 8px",
            textAlign: "center",
            color: theme.accent,
            fontSize: 11,
            cursor: "pointer",
          }}
        >
          {data.files.length
            ? `${data.files.length} uploaded frame${data.files.length > 1 ? "s" : ""}`
            : "or upload your own frames"}
          <input
            ref={inputRef}
            type="file"
            multiple
            accept="image/*"
            style={{ display: "none" }}
            onChange={(e) => data.onFiles(Array.from(e.target.files ?? []))}
          />
        </label>

        {data.files.length > 0 && (
          <div style={{ color: "#71717a", fontSize: 10, lineHeight: 1.5 }}>
            {data.files.slice(0, 4).map((f) => (
              <div key={f.name} style={{ overflow: "hidden", textOverflow: "ellipsis" }}>
                {f.name}
              </div>
            ))}
            {data.files.length > 4 && <div>+{data.files.length - 4} more</div>}
          </div>
        )}

        <textarea
          className="nodrag nowheel"
          value={data.lookNote}
          onChange={(e) => data.onLookNote(e.target.value)}
          placeholder='Director&apos;s look note — e.g. "night exteriors like Michael Mann, single sodium source, let the shadows go black"'
          style={{
            width: "100%",
            height: 76,
            resize: "none",
            boxSizing: "border-box",
            background: "#0f1115",
            color: "#e4e4e7",
            border: "1px solid #232936",
            borderRadius: 8,
            padding: 8,
            fontSize: 11,
            fontFamily: "ui-sans-serif, system-ui, sans-serif",
            lineHeight: 1.4,
          }}
        />
      </div>

      <ErrorText error={data.error} />
      <Handle type="source" position={Position.Bottom} style={{ background: "#52525b" }} />
    </CardShell>
  );
}
