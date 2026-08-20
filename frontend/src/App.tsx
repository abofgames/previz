import { useCallback, useMemo, useState } from "react";
import { API, PROJECT } from "./config";
import { useGraphSocket } from "./graph/useGraphSocket";
import Graph, { type GraphCallbacks } from "./graph/Graph";
import Controls from "./graph/Controls";
import Lightbox, { type LightboxData } from "./graph/Lightbox";
import type { Citation } from "./types";

export default function App() {
  const { graph, connected, log } = useGraphSocket(PROJECT);
  const [script, setScript] = useState("");
  const [lookNote, setLookNote] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [lightbox, setLightbox] = useState<LightboxData | null>(null);

  const onRetry = useCallback((nodeId: string) => {
    fetch(`${API}/api/projects/${PROJECT}/retry`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ node_id: nodeId }),
    });
  }, []);

  const onExpand = useCallback(
    (nodeId: string) => {
      const node = graph.nodes.find((n) => n.id === nodeId);
      if (!node) return;
      const meta = (node.meta || {}) as Record<string, unknown>;
      const url = typeof meta.image_url === "string" ? meta.image_url : "";
      if (!url) return;

      // Panels show the sources that shaped their scene, so the reasoning
      // behind a frame is one click away from the frame itself.
      const sceneId = typeof meta.scene_id === "string" ? meta.scene_id : undefined;
      const research = graph.nodes.find((n) => n.kind === "research");
      const citations =
        sceneId && research
          ? ((research.meta?.citations as Citation[] | undefined) ?? [])
          : undefined;

      setLightbox({
        imageUrl: API + url,
        label: node.label,
        prompt: typeof meta.prompt === "string" ? meta.prompt : undefined,
        citations,
        onRetry: () => onRetry(nodeId),
      });
    },
    [graph.nodes, onRetry]
  );

  const callbacks = useMemo<GraphCallbacks>(
    () => ({
      files, onFiles: setFiles,
      script, onScript: setScript,
      lookNote, onLookNote: setLookNote,
      onRetry, onExpand,
    }),
    [files, script, lookNote, onRetry, onExpand]
  );

  return (
    <div
      style={{
        width: "100vw",
        height: "100vh",
        background: "#0f1115",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <Controls
        graph={graph}
        project={PROJECT}
        script={script}
        lookNote={lookNote}
        files={files}
        log={log}
      />
      <div style={{ flex: 1, position: "relative" }}>
        <Graph graph={graph} connected={connected} project={PROJECT} callbacks={callbacks} />
      </div>
      <Lightbox data={lightbox} onClose={() => setLightbox(null)} />
    </div>
  );
}
