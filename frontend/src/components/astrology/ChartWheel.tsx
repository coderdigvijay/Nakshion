import { useId, useMemo, useRef, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { cn } from "../../lib/utils";
import { formatDeg, GRAHA_FILL, HOUSE_THEMES, ordinal, SIGNS } from "../../lib/astro";
import type { WheelData, WheelPlanet } from "../../lib/chartModel";
import { wheelSummary } from "../../lib/chartModel";
import { GlyphInSvg } from "./glyphs/AstroGlyph";
import { hasGlyph } from "./glyphs/paths";

// COMPONENTS.md → ChartWheel, MASTER §9.1. viewBox 0 0 400 400. Planet labels 16 units
// (>= 12.8px at the 320px minimum render size). Two-letter abbreviations, never Unicode glyphs.

export type ChartFormat = "north" | "south";

export interface ChartWheelProps {
  data: WheelData;
  format?: ChartFormat;
  variant?: "full" | "thumbnail";
  selectedHouse?: number | null;
  onSelectHouse?: (house: number) => void;
  /** Visible/accessible title, e.g. "D1 Rashi chart". */
  title: string;
  className?: string;
  /** Show degrees under abbreviations (only legible at >= 440px render size). */
  showDegrees?: boolean;
  /** Entrance animation (lines draw, planets fade in). Turn off after the first view so switching D1/D9/style is instant. */
  animate?: boolean;
}

// ── North Indian geometry: houses run anticlockwise from the top diamond ──────────────
const N_POLY: Record<number, string> = {
  1: "200,0 300,100 200,200 100,100",
  2: "0,0 200,0 100,100",
  3: "0,0 100,100 0,200",
  4: "0,200 100,100 200,200 100,300",
  5: "0,200 100,300 0,400",
  6: "0,400 100,300 200,400",
  7: "200,400 100,300 200,200 300,300",
  8: "200,400 300,300 400,400",
  9: "400,400 300,300 400,200",
  10: "400,200 300,300 200,200 300,100",
  11: "400,200 300,100 400,0",
  12: "400,0 300,100 200,0",
};
/** Where planet labels go and how they stack: grid (2x2) or column (1x4). */
const N_SLOT: Record<number, { x: number; y: number; layout: "grid" | "col" }> = {
  1: { x: 200, y: 100, layout: "grid" },
  2: { x: 100, y: 32, layout: "grid" },
  3: { x: 34, y: 100, layout: "col" },
  4: { x: 100, y: 200, layout: "grid" },
  5: { x: 34, y: 300, layout: "col" },
  6: { x: 100, y: 368, layout: "grid" },
  7: { x: 200, y: 300, layout: "grid" },
  8: { x: 300, y: 368, layout: "grid" },
  9: { x: 366, y: 300, layout: "col" },
  10: { x: 300, y: 200, layout: "grid" },
  11: { x: 366, y: 100, layout: "col" },
  12: { x: 300, y: 32, layout: "grid" },
};
/** Sign number near each house's inner vertex. */
const N_NUM: Record<number, { x: number; y: number }> = {
  1: { x: 200, y: 182 }, 2: { x: 100, y: 84 }, 3: { x: 84, y: 104 }, 4: { x: 182, y: 204 },
  5: { x: 84, y: 304 }, 6: { x: 100, y: 326 }, 7: { x: 200, y: 230 }, 8: { x: 300, y: 326 },
  9: { x: 316, y: 304 }, 10: { x: 218, y: 204 }, 11: { x: 316, y: 104 }, 12: { x: 300, y: 84 },
};

// ── South Indian geometry: fixed sign cells (Pisces top-left, clockwise) ────────────
const S_CELL: Record<number, { col: number; row: number }> = {
  11: { col: 0, row: 0 }, 0: { col: 1, row: 0 }, 1: { col: 2, row: 0 }, 2: { col: 3, row: 0 },
  3: { col: 3, row: 1 }, 4: { col: 3, row: 2 }, 5: { col: 3, row: 3 }, 6: { col: 2, row: 3 },
  7: { col: 1, row: 3 }, 8: { col: 0, row: 3 }, 9: { col: 0, row: 2 }, 10: { col: 0, row: 1 },
};

function slotOffsets(count: number, layout: "grid" | "col"): Array<{ dx: number; dy: number }> {
  if (layout === "col") {
    const gap = 19;
    const start = -((count - 1) * gap) / 2;
    return Array.from({ length: count }, (_, i) => ({ dx: 0, dy: start + i * gap }));
  }
  if (count === 1) return [{ dx: 0, dy: 0 }];
  if (count === 2) return [{ dx: -22, dy: 0 }, { dx: 22, dy: 0 }];
  return [
    { dx: -22, dy: -10 },
    { dx: 22, dy: -10 },
    { dx: -22, dy: 12 },
    { dx: 22, dy: 12 },
  ].slice(0, count);
}

function PlanetLabel({ p, x, y, showDegree }: { p: WheelPlanet; x: number; y: number; showDegree: boolean }) {
  const fill = p.key ? GRAHA_FILL[p.key] : "fill-fg-muted";
  return (
    <g>
      <text x={x} y={y} textAnchor="middle" dominantBaseline="middle" className={cn(fill, "font-sans")} style={{ fontSize: 16, fontWeight: 600 }}>
        {p.abbr}
        {p.retrograde && (
          <tspan dy={-6} style={{ fontSize: 14 }}>
            R
          </tspan>
        )}
        {p.combust && (
          <tspan dy={p.retrograde ? 0 : -6} style={{ fontSize: 14 }}>
            c
          </tspan>
        )}
      </text>
      {p.dignity === "exalted" && <path d={`M ${x + 15} ${y + 7} l 4 -7 l 4 7 z`} className={fill} />}
      {p.dignity === "debilitated" && <path d={`M ${x + 15} ${y - 6} l 4 7 l 4 -7 z`} className={fill} />}
      {showDegree && (
        <text x={x} y={y + 13} textAnchor="middle" className="fill-fg-muted font-sans tabular" style={{ fontSize: 11 }}>
          {formatDeg(p.degree)}
        </text>
      )}
    </g>
  );
}

function housePlanets(planets: WheelPlanet[], house: number) {
  return planets.filter((p) => p.house === house);
}

function houseLabel(data: WheelData, house: number): string {
  const signIdx = (data.lagnaIdx + house - 1) % 12;
  const sign = SIGNS[signIdx];
  const ps = housePlanets(data.planets, house);
  const who = ps.length ? ps.map((p) => `${p.english}${p.retrograde ? " retrograde" : ""} ${formatDeg(p.degree)}`).join(", ") : "no planets";
  return `${ordinal(house)} house${house === 1 ? ", Lagna" : ""}, ${sign?.rashi ?? ""} (${sign?.english ?? ""}): ${who}. ${HOUSE_THEMES[house] ?? ""}`;
}

export function ChartWheel({ data, format = "north", variant = "full", selectedHouse = null, onSelectHouse, title, className, showDegrees = false, animate = true }: ChartWheelProps) {
  const uid = useId().replace(/:/g, "");
  const reduce = useReducedMotion();
  const thumb = variant === "thumbnail";
  const interactive = !thumb && !!onSelectHouse;
  const [focusHouse, setFocusHouse] = useState<number>(selectedHouse ?? 1);
  const houseRefs = useRef<Record<number, SVGGElement | null>>({});
  const summary = useMemo(() => wheelSummary(data), [data]);
  const titleId = `${uid}-title`;
  const descId = `${uid}-desc`;
  const hasLagna = data.lagnaIdx >= 0;

  const moveFocus = (h: number) => {
    setFocusHouse(h);
    houseRefs.current[h]?.focus();
  };
  const onHouseKey = (e: React.KeyboardEvent, house: number) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      onSelectHouse?.(house);
    } else if (e.key === "ArrowRight" || e.key === "ArrowDown") {
      e.preventDefault();
      moveFocus((house % 12) + 1);
    } else if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
      e.preventDefault();
      moveFocus(((house + 10) % 12) + 1);
    } else if (e.key === "Home") {
      e.preventDefault();
      moveFocus(1);
    } else if (e.key === "End") {
      e.preventDefault();
      moveFocus(12);
    }
  };

  const lineDraw = reduce || thumb || !animate ? {} : { initial: { pathLength: 0, opacity: 0 }, animate: { pathLength: 1, opacity: 1 }, transition: { duration: 0.6, ease: [0.16, 1, 0.3, 1] as const } };
  const planetFade = (i: number) =>
    reduce || thumb || !animate ? {} : { initial: { opacity: 0 }, animate: { opacity: 1 }, transition: { delay: 0.45 + i * 0.03, duration: 0.25 } };

  const houseProps = (house: number) =>
    interactive
      ? {
          role: "button",
          tabIndex: focusHouse === house ? 0 : -1,
          "aria-label": houseLabel(data, house),
          "aria-pressed": selectedHouse === house,
          onClick: () => {
            setFocusHouse(house);
            onSelectHouse?.(house);
          },
          onKeyDown: (e: React.KeyboardEvent) => onHouseKey(e, house),
          ref: (el: SVGGElement | null) => {
            houseRefs.current[house] = el;
          },
          className: "group cursor-pointer outline-none",
        }
      : {};

  const houseFill = (house: number) =>
    cn(
      "transition-colors duration-150",
      selectedHouse === house
        ? "fill-ai-subtle stroke-ai"
        : house === 1 && hasLagna
          ? "fill-accent-subtle stroke-transparent"
          : "fill-transparent stroke-transparent",
      interactive && selectedHouse !== house && "group-hover:fill-ai-subtle group-focus-visible:fill-ai-subtle",
      interactive && "group-focus-visible:stroke-focus",
    );

  let planetIdx = 0;

  const north = (
    <>
      {Object.entries(N_POLY).map(([h, pts]) => {
        const house = Number(h);
        const ps = housePlanets(data.planets, house);
        const slot = N_SLOT[house];
        const shown = ps.length > 4 ? ps.slice(0, 3) : ps;
        const offs = slotOffsets(ps.length > 4 ? 4 : shown.length, slot.layout);
        const signIdx = (data.lagnaIdx + house - 1) % 12;
        return (
          <g key={house} {...houseProps(house)}>
            <polygon points={pts} className={houseFill(house)} strokeWidth={2} />
            {house === 1 && hasLagna && data.approximate && <polygon points={pts} fill={`url(#${uid}-hatch)`} />}
            {!thumb && hasLagna && (
              <text x={N_NUM[house].x} y={N_NUM[house].y} textAnchor="middle" dominantBaseline="middle" className="fill-fg-muted font-sans tabular" style={{ fontSize: 15 }}>
                {signIdx + 1}
              </text>
            )}
            {!thumb &&
              shown.map((p, i) => (
                <motion.g key={p.english} {...planetFade(planetIdx++)}>
                  <PlanetLabel p={p} x={slot.x + offs[i].dx} y={slot.y + offs[i].dy} showDegree={showDegrees && shown.length <= 2} />
                </motion.g>
              ))}
            {!thumb && ps.length > 4 && (
              <text x={slot.x + offs[3].dx} y={slot.y + offs[3].dy} textAnchor="middle" dominantBaseline="middle" className="fill-fg-secondary font-sans" style={{ fontSize: 14, fontWeight: 600 }}>
                +{ps.length - 3}
              </text>
            )}
          </g>
        );
      })}
      <g className="pointer-events-none stroke-border-strong" fill="none">
        <motion.rect x={1} y={1} width={398} height={398} strokeWidth={1.5} {...lineDraw} />
        <motion.path d="M0 0 L400 400 M400 0 L0 400" strokeWidth={1} strokeOpacity={0.6} {...lineDraw} />
        <motion.path d="M200 0 L400 200 L200 400 L0 200 Z" strokeWidth={1} strokeOpacity={0.6} {...lineDraw} />
      </g>
      {hasLagna && (
        <text x={200} y={thumb ? 70 : 40} textAnchor="middle" dominantBaseline="middle" className="pointer-events-none fill-accent-text font-sans" style={{ fontSize: thumb ? 34 : 15, fontWeight: 600 }}>
          La
        </text>
      )}
      {thumb && (() => {
        const moon = data.planets.find((p) => p.key === "moon");
        if (!moon) return null;
        const slot = N_SLOT[moon.house];
        return (
          <text x={slot.x} y={moon.house === 1 ? 130 : slot.y} textAnchor="middle" dominantBaseline="middle" className="fill-moon font-sans" style={{ fontSize: 34, fontWeight: 600 }}>
            Mo
          </text>
        );
      })()}
    </>
  );

  const south = (
    <>
      {Array.from({ length: 12 }, (_, signIdx) => {
        const cell = S_CELL[signIdx];
        const x = cell.col * 100;
        const y = cell.row * 100;
        const house = hasLagna ? ((signIdx - data.lagnaIdx + 12) % 12) + 1 : signIdx + 1;
        const ps = housePlanets(data.planets, house);
        const shown = ps.length > 4 ? ps.slice(0, 3) : ps;
        const offs = slotOffsets(ps.length > 4 ? 4 : shown.length, "grid");
        const isLagna = hasLagna && signIdx === data.lagnaIdx;
        return (
          <g key={signIdx} {...houseProps(house)}>
            <rect x={x} y={y} width={100} height={100} className={houseFill(house)} strokeWidth={2} />
            {isLagna && data.approximate && <rect x={x} y={y} width={100} height={100} fill={`url(#${uid}-hatch)`} />}
            {isLagna && <line x1={x} y1={y + 26} x2={x + 26} y2={y} className="stroke-accent" strokeWidth={2} />}
            {!thumb && (
              (() => {
                const g = SIGNS[signIdx].english.toLowerCase();
                return hasGlyph(g) ? <GlyphInSvg name={g} x={x + 76} y={y + 4} size={18} className="stroke-fg-muted" /> : null;
              })()
            )}
            {isLagna && (
              <text x={x + 50} y={thumb ? y + 60 : y + 88} textAnchor="middle" className="fill-accent-text font-sans" style={{ fontSize: thumb ? 34 : 15, fontWeight: 600 }}>
                La
              </text>
            )}
            {!thumb &&
              shown.map((p, i) => (
                <motion.g key={p.english} {...planetFade(planetIdx++)}>
                  <PlanetLabel p={p} x={x + 50 + offs[i].dx} y={y + 50 + offs[i].dy} showDegree={false} />
                </motion.g>
              ))}
            {!thumb && ps.length > 4 && (
              <text x={x + 50 + offs[3].dx} y={y + 50 + offs[3].dy} textAnchor="middle" dominantBaseline="middle" className="fill-fg-secondary font-sans" style={{ fontSize: 14, fontWeight: 600 }}>
                +{ps.length - 3}
              </text>
            )}
          </g>
        );
      })}
      <g className="pointer-events-none stroke-border-strong" fill="none">
        <motion.rect x={1} y={1} width={398} height={398} strokeWidth={1.5} {...lineDraw} />
        <motion.path
          d="M100 0 V400 M300 0 V400 M0 100 H400 M0 300 H400 M200 0 V100 M200 300 V400 M0 200 H100 M300 200 H400"
          strokeWidth={1}
          strokeOpacity={0.6}
          {...lineDraw}
        />
      </g>
      {!thumb && (
        <text x={200} y={200} textAnchor="middle" dominantBaseline="middle" className="pointer-events-none fill-fg-muted font-display" style={{ fontSize: 18 }}>
          {title}
        </text>
      )}
    </>
  );

  return (
    <figure className={cn("m-0", className)}>
      <div className={cn("aspect-square w-full rounded-card border border-border bg-bg-sunken", thumb ? "p-1.5" : "p-2 sm:p-3")}>
        <svg
          viewBox="0 0 400 400"
          role={interactive ? "group" : "img"}
          aria-labelledby={titleId}
          aria-describedby={descId}
          className="block size-full select-none overflow-visible"
        >
          <title id={titleId}>{title}</title>
          <desc id={descId}>{summary}</desc>
          <defs>
            <pattern id={`${uid}-hatch`} width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
              <line x1="0" y1="0" x2="0" y2="8" className="stroke-border-strong" strokeWidth="1" strokeOpacity="0.4" />
            </pattern>
          </defs>
          {format === "north" ? north : south}
        </svg>
      </div>
      {!thumb && (
        // Screen-reader / keyboard alternative to the drawing (rules §6: no visual-only chart).
        <ul className="sr-only" aria-label={`${title}: placements by house`}>
          {Array.from({ length: 12 }, (_, i) => (
            <li key={i}>{houseLabel(data, i + 1)}</li>
          ))}
        </ul>
      )}
    </figure>
  );
}

export function ChartWheelLegend({ className }: { className?: string }) {
  return (
    <dl className={cn("grid grid-cols-2 gap-x-6 gap-y-1.5 text-caption text-fg-secondary sm:grid-cols-3", className)}>
      {[
        ["Su Mo Ma Me", "Sun, Moon, Mars, Mercury"],
        ["Ju Ve Sa Ra Ke", "Jupiter, Venus, Saturn, Rahu, Ketu"],
        ["La", "Lagna (Ascendant)"],
        ["R", "Retrograde"],
        ["c", "Combust"],
        ["Up / down mark", "Exalted / debilitated"],
        ["1–12", "Sign number (North Indian)"],
      ].map(([k, v]) => (
        <div key={k} className="flex gap-2">
          <dt className="font-semibold text-fg">{k}</dt>
          <dd>{v}</dd>
        </div>
      ))}
    </dl>
  );
}
