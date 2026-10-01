import { motion, useReducedMotion } from "framer-motion";
import { cn } from "../../lib/utils";
import { bandFor } from "../../lib/compatBands";

// COMPONENTS.md → CompatibilityMeter, MASTER §9.4a. 240° arc; band colour carries meaning,
// always paired with an icon and a band word.


const R = 80;
const CX = 100;
const CY = 100;
const START = 150; // degrees, SVG coords (0 = 3 o'clock, clockwise)
const SWEEP = 240;

function polar(deg: number) {
  const rad = (deg * Math.PI) / 180;
  return { x: CX + R * Math.cos(rad), y: CY + R * Math.sin(rad) };
}
const a0 = polar(START);
const a1 = polar(START + SWEEP);
const ARC = `M ${a0.x} ${a0.y} A ${R} ${R} 0 1 1 ${a1.x} ${a1.y}`;

export function CompatibilityMeter({ score, max = 10, className }: { score: number; max?: 10 | 36; className?: string }) {
  const reduce = useReducedMotion();
  const clamped = Math.max(0, Math.min(max, Number.isFinite(score) ? score : 0));
  const frac = clamped / max;
  const band = bandFor(clamped, max);
  return (
    <div className={cn("flex flex-col items-center", className)}>
      <div
        role="meter"
        aria-valuemin={0}
        aria-valuemax={max}
        aria-valuenow={clamped}
        aria-valuetext={`${clamped.toFixed(1)} out of ${max}, ${band.label}`}
        aria-label="Overall compatibility"
        className="relative size-[168px] md:size-[200px]"
      >
        <svg viewBox="0 0 200 200" className={cn("size-full", band.glow && "drop-shadow-[0_8px_20px_rgb(242_181_68/0.35)]")} aria-hidden="true">
          <path d={ARC} fill="none" className="stroke-border" strokeWidth={12} strokeLinecap="round" />
          <motion.path
            d={ARC}
            fill="none"
            className={band.stroke}
            strokeWidth={12}
            strokeLinecap="round"
            initial={reduce ? false : { pathLength: 0 }}
            animate={{ pathLength: frac }}
            transition={{ duration: 0.9, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="font-display text-stat tabular text-fg">{clamped.toFixed(1)}</span>
          <span className="text-caption text-fg-muted">out of {max}</span>
        </div>
      </div>
      <p className={cn("mt-1 flex items-center gap-2 text-title [&_svg]:size-5", band.text)}>
        {band.icon}
        {band.label}
      </p>
    </div>
  );
}

export function CategoryBar({ label, score, summary }: { label: string; score: number; summary?: string }) {
  const band = bandFor(score);
  const v = Math.max(0, Math.min(10, score));
  return (
    <div>
      <div className="flex items-baseline justify-between gap-3">
        <span className="text-body-sm font-medium text-fg">{label}</span>
        <span className="flex items-center gap-1.5 text-body-sm tabular text-fg">
          <span className="sr-only">{band.label},</span>
          {v.toFixed(1)}
        </span>
      </div>
      <div
        role="meter"
        aria-label={label}
        aria-valuemin={0}
        aria-valuemax={10}
        aria-valuenow={v}
        aria-valuetext={`${v.toFixed(1)} out of 10, ${band.label}`}
        className="mt-2 h-2 overflow-hidden rounded-chip bg-elevated"
      >
        <div className={cn("h-full origin-left rounded-chip", band.bg)} style={{ transform: `scaleX(${v / 10})` }} />
      </div>
      {summary && <p className="mt-2 text-body-sm text-fg-secondary">{summary}</p>}
    </div>
  );
}
