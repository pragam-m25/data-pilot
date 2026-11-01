import React from "react";

type LogoSize = "sm" | "md" | "lg";

const sizes: Record<LogoSize, { mark: number; text: number; gap: number }> = {
  sm: { mark: 24, text: 14, gap: 8 },
  md: { mark: 32, text: 16, gap: 10 },
  lg: { mark: 44, text: 20, gap: 12 },
};

/**
 * DataPilot geometric mark:
 * Three data-point nodes arranged in a small triangle, connected by lines.
 * The bottom-right node has a small tick to suggest "verified data".
 * Uses only teal (#0F8B83) for the mark.
 */
export function DataPilotLogo({
  size = "md",
  wordmark = true,
}: {
  size?: LogoSize;
  wordmark?: boolean;
}) {
  const { mark, text, gap } = sizes[size];

  // Node positions (as fractions of the mark bounding box, 0–1)
  // Top-left, top-right, bottom-center
  const nodes = [
    { cx: 0.18, cy: 0.22 },   // A — top-left
    { cx: 0.82, cy: 0.22 },   // B — top-right
    { cx: 0.5,  cy: 0.78 },   // C — bottom-center
  ];

  // Scale to mark size
  const scale = (v: number) => v * mark;
  const r = mark * 0.09; // node radius

  // Tick at node C (bottom-center) — small checkmark
  const tickCx = scale(nodes[2].cx);
  const tickCy = scale(nodes[2].cy);
  const tickSize = mark * 0.1;

  return (
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: `${gap}px`,
        lineHeight: 1,
      }}
    >
      {/* SVG mark */}
      <svg
        width={mark}
        height={mark}
        viewBox={`0 0 ${mark} ${mark}`}
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
      >
        {/* Triangle lines connecting the three nodes */}
        <line
          x1={scale(nodes[0].cx)} y1={scale(nodes[0].cy)}
          x2={scale(nodes[1].cx)} y2={scale(nodes[1].cy)}
          stroke="#0F8B83" strokeWidth={mark * 0.055} strokeLinecap="round"
        />
        <line
          x1={scale(nodes[1].cx)} y1={scale(nodes[1].cy)}
          x2={scale(nodes[2].cx)} y2={scale(nodes[2].cy)}
          stroke="#0F8B83" strokeWidth={mark * 0.055} strokeLinecap="round"
        />
        <line
          x1={scale(nodes[0].cx)} y1={scale(nodes[0].cy)}
          x2={scale(nodes[2].cx)} y2={scale(nodes[2].cy)}
          stroke="#0F8B83" strokeWidth={mark * 0.055} strokeLinecap="round"
        />

        {/* Three nodes */}
        {nodes.map((n, i) => (
          <circle
            key={i}
            cx={scale(n.cx)}
            cy={scale(n.cy)}
            r={r}
            fill="#0F8B83"
          />
        ))}

        {/* Verification tick at node C (bottom-center) */}
        <polyline
          points={`${tickCx - tickSize * 0.7},${tickCy + tickSize * 0.05} ${tickCx - tickSize * 0.1},${tickCy + tickSize * 0.65} ${tickCx + tickSize * 0.7},${tickCy - tickSize * 0.55}`}
          stroke="#fff"
          strokeWidth={mark * 0.05}
          strokeLinecap="round"
          strokeLinejoin="round"
          fill="none"
        />
      </svg>

      {/* Wordmark */}
      {wordmark && (
        <span
          style={{
            fontSize: `${text}px`,
            fontWeight: 700,
            letterSpacing: "-0.02em",
            color: "var(--color-text-primary)",
            userSelect: "none",
          }}
        >
          Data<span style={{ color: "var(--color-accent)" }}>Pilot</span>
        </span>
      )}
    </div>
  );
}
