import { Handle, Position, type NodeProps } from "reactflow";
import { CardShell, CardHeader } from "./shared";
import { KIND_THEMES } from "../kindThemes";
import { API } from "../../config";
import type { NodeKind, NodeStatus } from "../../types";

export type ShotSpec = {
  size?: string;
  lens?: string;
  angle?: string;
  movement?: string;
  description?: string;
};

export type ImageNodeData = {
  label: string;
  status: NodeStatus;
  kind: NodeKind;
  imageUrl?: string;
  prompt?: string;
  error?: string;
  spec?: ShotSpec;
  sourceCount?: number;
  aspect: string;
  onRetry: () => void;
  onExpand: () => void;
};

/**
 * One generated image: a character plate, a location plate, the lookboard, or
 * a storyboard panel. Three states — empty with a Generate button, generating,
 * or the image itself. Nothing generates until the user asks, which is what
 * keeps a run's image quota at zero while they iterate on the breakdown.
 */
export default function ImageNode({ data }: NodeProps<ImageNodeData>) {
  const src = data.imageUrl ? API + data.imageUrl : undefined;
  const theme = KIND_THEMES[data.kind];
  const running = data.status === "running";
  const failed = data.status === "failed";
  const hasImage = Boolean(src);
  const width = data.kind === "shot" || data.kind === "lookboard" ? 280 : 220;

  return (
    <CardShell status={data.status} kind={data.kind} width={width}>
      <Handle type="target" position={Position.Top} style={{ background: "#52525b" }} />
      <CardHeader
        label={data.label}
        kind={data.kind}
        status={data.status}
        onRetry={hasImage ? data.onRetry : undefined}
      />

      {data.spec && (
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: 4,
            padding: "6px 8px",
            borderBottom: "1px solid #232936",
          }}
        >
          {[data.spec.size, data.spec.lens, data.spec.angle, data.spec.movement]
            .filter(Boolean)
            .map((v) => (
              <span
                key={v}
                style={{
                  fontSize: 9,
                  fontFamily: "ui-monospace, monospace",
                  color: theme.accent,
                  border: `1px solid ${theme.accent}44`,
                  borderRadius: 4,
                  padding: "1px 5px",
                }}
              >
                {v}
              </span>
            ))}
        </div>
      )}

      <div
        onClick={hasImage ? data.onExpand : undefined}
        className={hasImage ? "nodrag" : undefined}
        style={{
          width: "100%",
          aspectRatio: data.aspect,
          background: "#0f1115",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          overflow: "hidden",
          color: "#52525b",
          fontSize: 11,
          cursor: hasImage ? "zoom-in" : "default",
        }}
      >
        {src ? (
          <img
            src={src}
            alt={data.label}
            style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
          />
        ) : running ? (
          <span style={{ color: theme.accent }}>drawing…</span>
        ) : (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: 8,
              padding: 12,
              textAlign: "center",
            }}
          >
            {failed && data.error && (
              <span style={{ color: "#fca5a5", fontSize: 10, lineHeight: 1.4 }}>
                {data.error}
              </span>
            )}
            <button
              onClick={data.onRetry}
              className="nodrag"
              style={{
                background: failed ? "#ef4444" : theme.accent,
                color: "#0f1115",
                border: "none",
                borderRadius: 8,
                padding: "10px 16px",
                fontSize: 12,
                fontWeight: 700,
                cursor: "pointer",
                letterSpacing: 0.3,
              }}
            >
              {failed ? "Retry" : "Draw"}
            </button>
          </div>
        )}
      </div>

      {!!data.sourceCount && (
        <div
          style={{
            padding: "4px 9px",
            borderTop: "1px solid #232936",
            fontSize: 9.5,
            color: "#f97316",
            fontWeight: 700,
            letterSpacing: 0.3,
          }}
        >
          ◆ grounded in {data.sourceCount} researched source
          {data.sourceCount === 1 ? "" : "s"}
        </div>
      )}

      {data.spec?.description && (
        <div
          style={{
            padding: "6px 9px",
            fontSize: 10,
            color: "#a1a1aa",
            lineHeight: 1.4,
            borderTop: "1px solid #232936",
            maxHeight: 46,
            overflow: "hidden",
          }}
        >
          {data.spec.description}
        </div>
      )}

      <Handle type="source" position={Position.Bottom} style={{ background: "#52525b" }} />
    </CardShell>
  );
}
