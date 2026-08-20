import { Handle, Position, type NodeProps } from "reactflow";
import { STATUS_COLORS } from "../nodeStyles";
import { KIND_THEMES } from "../kindThemes";
import type { NodeStatus } from "../../types";

export type BriefNodeData = { label: string; status: NodeStatus };

export default function BriefNode({ data }: NodeProps<BriefNodeData>) {
  const c = STATUS_COLORS[data.status];
  const theme = KIND_THEMES.brief;
  return (
    <div
      style={{
        width: 90,
        height: 90,
        borderRadius: "50%",
        background: "#13161d",
        border: `2px solid ${c.border}`,
        boxShadow: `inset 0 0 0 3px ${theme.accent}22`,
        color: theme.accent,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        textAlign: "center",
        fontSize: 10,
        fontWeight: 700,
        letterSpacing: 0.5,
        textTransform: "uppercase",
        fontFamily: "ui-sans-serif, system-ui, sans-serif",
        padding: 8,
      }}
    >
      {data.label}
      <Handle type="source" position={Position.Bottom} style={{ background: "#52525b" }} />
    </div>
  );
}
