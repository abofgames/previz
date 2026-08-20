import type { NodeKind } from "../types";

export type KindTheme = { accent: string; band: string; label: string };

export const KIND_THEMES: Record<NodeKind, KindTheme> = {
  brief:     { accent: "#a78bfa", band: "#2a2240", label: "brief" },
  look_dev:  { accent: "#60a5fa", band: "#172741", label: "look development" },
  breakdown: { accent: "#2dd4bf", band: "#0f2c2a", label: "script breakdown" },
  research:  { accent: "#f97316", band: "#331d0f", label: "visual research" },
  lookboard: { accent: "#22d3ee", band: "#0f2b33", label: "lookboard" },
  group:     { accent: "#71717a", band: "#1a1c22", label: "group" },
  character: { accent: "#34d399", band: "#0f2a23", label: "character plate" },
  location:  { accent: "#fbbf24", band: "#33250f", label: "location plate" },
  shot:      { accent: "#f472b6", band: "#321a28", label: "storyboard panel" },
  animatic:  { accent: "#c084fc", band: "#2b1a3a", label: "animatic" },
};
