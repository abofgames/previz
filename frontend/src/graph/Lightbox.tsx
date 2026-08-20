import { useEffect } from "react";
import type { Citation } from "../types";

export type LightboxData = {
  imageUrl: string;
  label: string;
  prompt?: string;
  citations?: Citation[];
  onRetry: () => void;
};

/**
 * Full view of one generated image beside the exact prompt that produced it
 * and the sources that informed it. Being able to read the prompt is what
 * makes the pipeline debuggable — a bad panel is almost always a bad prompt.
 */
export default function Lightbox({
  data,
  onClose,
}: {
  data: LightboxData | null;
  onClose: () => void;
}) {
  useEffect(() => {
    if (!data) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [data, onClose]);

  if (!data) return null;

  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        background: "#000000cc",
        zIndex: 1000,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 40,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: "#13161d",
          border: "1px solid #232936",
          borderRadius: 12,
          maxWidth: "min(1200px, 95vw)",
          maxHeight: "92vh",
          width: "100%",
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
          fontFamily: "ui-sans-serif, system-ui, sans-serif",
          color: "#e4e4e7",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 12,
            padding: "12px 18px",
            borderBottom: "1px solid #232936",
            background: "#171a22",
          }}
        >
          <strong style={{ flex: 1, fontSize: 14 }}>{data.label}</strong>
          <button
            onClick={() => {
              data.onRetry();
              onClose();
            }}
            style={{
              background: "#f59e0b",
              color: "#0f1115",
              border: "none",
              borderRadius: 6,
              padding: "6px 14px",
              fontSize: 12,
              fontWeight: 700,
              cursor: "pointer",
            }}
          >
            Redraw
          </button>
          <button
            onClick={onClose}
            style={{
              background: "transparent",
              color: "#a1a1aa",
              border: "1px solid #3a4252",
              borderRadius: 6,
              padding: "6px 12px",
              fontSize: 12,
              cursor: "pointer",
            }}
          >
            Close
          </button>
        </div>

        <div style={{ display: "flex", flex: 1, minHeight: 0, background: "#0f1115" }}>
          <div
            style={{
              flex: 2,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              padding: 20,
              minHeight: 0,
            }}
          >
            <img
              src={data.imageUrl}
              alt={data.label}
              style={{ maxWidth: "100%", maxHeight: "75vh", objectFit: "contain", borderRadius: 6 }}
            />
          </div>

          <div
            style={{
              flex: 1,
              padding: 20,
              borderLeft: "1px solid #232936",
              overflowY: "auto",
              maxHeight: "82vh",
            }}
          >
            <SectionLabel>Prompt sent to Gemini</SectionLabel>
            <pre
              style={{
                margin: "0 0 20px",
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
                fontSize: 12,
                color: "#d4d4d8",
                fontFamily: "ui-monospace, monospace",
                lineHeight: 1.5,
              }}
            >
              {data.prompt || "(no prompt recorded)"}
            </pre>

            {data.citations && data.citations.length > 0 && (
              <>
                <SectionLabel>Researched sources</SectionLabel>
                {data.citations.map((c, i) => (
                  <a
                    key={c.url + i}
                    href={c.url}
                    target="_blank"
                    rel="noreferrer"
                    style={{
                      display: "block",
                      color: "#93c5fd",
                      fontSize: 11.5,
                      lineHeight: 1.4,
                      marginBottom: 8,
                      textDecoration: "none",
                    }}
                  >
                    {c.title || c.url}
                  </a>
                ))}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        fontSize: 10,
        letterSpacing: 0.5,
        textTransform: "uppercase",
        color: "#71717a",
        fontWeight: 700,
        marginBottom: 8,
      }}
    >
      {children}
    </div>
  );
}
