import type { ReactNode } from "react";
import type { NodeKind, NodeStatus } from "../../types";
import { STATUS_COLORS } from "../nodeStyles";
import { KIND_THEMES } from "../kindThemes";

export function StatusPill({ status }: { status: NodeStatus }) {
  const c = STATUS_COLORS[status];
  return (
    <span
      style={{
        display: "inline-block",
        padding: "1px 8px",
        borderRadius: 999,
        fontSize: 10,
        fontWeight: 600,
        textTransform: "uppercase",
        letterSpacing: 0.4,
        background: c.bg,
        color: c.fg,
        border: `1px solid ${c.border}`,
      }}
    >
      {status}
    </span>
  );
}

export function CardShell({
  status,
  kind,
  children,
  width,
}: {
  status: NodeStatus;
  kind: NodeKind;
  children: ReactNode;
  width: number;
}) {
  const c = STATUS_COLORS[status];
  const theme = KIND_THEMES[kind];
  return (
    <div
      style={{
        width,
        background: "#13161d",
        color: "#e4e4e7",
        border: `1.5px solid ${c.border}`,
        borderLeft: `5px solid ${theme.accent}`,
        borderRadius: 10,
        boxShadow: status === "running" ? `0 0 0 3px ${c.border}33` : "none",
        fontFamily: "ui-sans-serif, system-ui, sans-serif",
        fontSize: 12,
        overflow: "hidden",
      }}
    >
      {children}
    </div>
  );
}

export function CardHeader({
  label,
  kind,
  status,
  onRetry,
}: {
  label: string;
  kind: NodeKind;
  status: NodeStatus;
  onRetry?: () => void;
}) {
  const theme = KIND_THEMES[kind];
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        padding: "8px 10px",
        borderBottom: "1px solid #232936",
        background: theme.band,
      }}
    >
      <div style={{ flex: 1, minWidth: 0 }}>
        <div
          style={{
            fontSize: 9,
            letterSpacing: 0.5,
            textTransform: "uppercase",
            color: theme.accent,
            fontWeight: 700,
          }}
        >
          {theme.label}
        </div>
        <div
          style={{
            fontSize: 12,
            color: "#e4e4e7",
            fontWeight: 600,
            whiteSpace: "normal",
            lineHeight: 1.3,
            wordBreak: "break-word",
          }}
        >
          {label}
        </div>
      </div>
      <StatusPill status={status} />
      {onRetry && (
        <button
          onClick={onRetry}
          title="Regenerate"
          className="nodrag"
          style={{
            background: "transparent",
            color: "#a1a1aa",
            border: "1px solid #3a4252",
            borderRadius: 6,
            fontSize: 11,
            padding: "1px 8px",
            cursor: "pointer",
          }}
        >
          ↻
        </button>
      )}
    </div>
  );
}

export function ErrorText({ error }: { error?: string }) {
  if (!error) return null;
  return (
    <div style={{ color: "#fca5a5", fontSize: 10, lineHeight: 1.4, padding: "6px 10px" }}>
      {error}
    </div>
  );
}
