import { Handle, Position, type NodeProps } from "reactflow";
import { STATUS_COLORS } from "../nodeStyles";
import type { NodeStatus } from "../../types";

export type GroupNodeData = { label: string; status: NodeStatus };

export default function GroupNode({ data }: NodeProps<GroupNodeData>) {
  const c = STATUS_COLORS[data.status];
  return (
    <div
      style={{
        padding: "8px 16px",
        borderRadius: 999,
        border: `1.5px dashed ${c.border}`,
        background: "#13161d",
        color: c.fg,
        fontSize: 11,
        fontWeight: 700,
        letterSpacing: 0.8,
        textTransform: "uppercase",
        textAlign: "center",
        fontFamily: "ui-sans-serif, system-ui, sans-serif",
      }}
    >
      <Handle type="target" position={Position.Top} style={{ background: "#52525b" }} />
      {data.label}
      <Handle type="source" position={Position.Bottom} style={{ background: "#52525b" }} />
    </div>
  );
}
