import { Handle, Position, type NodeProps } from "reactflow";
import { CardShell, CardHeader, ErrorText } from "./shared";
import { KIND_THEMES } from "../kindThemes";
import { API } from "../../config";
import type { NodeStatus } from "../../types";

export type AnimaticNodeData = {
  label: string;
  status: NodeStatus;
  videoUrl?: string;
  error?: string;
  onRetry: () => void;
};

/** Optional Veo pass: a finished panel turned into a moving shot. */
export default function AnimaticNode({ data }: NodeProps<AnimaticNodeData>) {
  const theme = KIND_THEMES.animatic;
  const src = data.videoUrl ? API + data.videoUrl : undefined;
  const running = data.status === "running";

  return (
    <CardShell status={data.status} kind="animatic" width={280}>
      <Handle type="target" position={Position.Top} style={{ background: "#52525b" }} />
      <CardHeader
        label={data.label}
        kind="animatic"
        status={data.status}
        onRetry={src ? data.onRetry : undefined}
      />
      <div
        style={{
          width: "100%",
          aspectRatio: "16 / 9",
          background: "#0f1115",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        {src ? (
          <video
            src={src}
            controls
            loop
            className="nodrag"
            style={{ width: "100%", height: "100%", objectFit: "cover" }}
          />
        ) : running ? (
          <span style={{ color: theme.accent, fontSize: 11 }}>rendering…</span>
        ) : (
          <button
            onClick={data.onRetry}
            className="nodrag"
            style={{
              background: theme.accent,
              color: "#0f1115",
              border: "none",
              borderRadius: 8,
              padding: "10px 16px",
              fontSize: 12,
              fontWeight: 700,
              cursor: "pointer",
            }}
          >
            Animate
          </button>
        )}
      </div>
      <ErrorText error={data.error} />
    </CardShell>
  );
}
