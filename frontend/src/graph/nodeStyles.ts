import type { NodeStatus } from "../types";

export const STATUS_COLORS: Record<
  NodeStatus,
  { bg: string; border: string; fg: string }
> = {
  pending:  { bg: "#1f2530", border: "#3a4252", fg: "#aab2c0" },
  running:  { bg: "#1e3a5f", border: "#3b82f6", fg: "#dbeafe" },
  complete: { bg: "#14352a", border: "#22c55e", fg: "#bbf7d0" },
  failed:   { bg: "#3a1818", border: "#ef4444", fg: "#fecaca" },
  stale:    { bg: "#2a2730", border: "#71717a", fg: "#a1a1aa" },
};
