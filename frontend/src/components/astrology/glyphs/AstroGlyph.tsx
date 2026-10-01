import { cn } from "../../../lib/utils";
import { GRAHA_GLYPHS, LAGNA_GLYPH, SIGN_GLYPHS, type GlyphName } from "./paths";

export type { GlyphName } from "./paths";

const ALL: Record<string, readonly string[]> = { ...SIGN_GLYPHS, ...GRAHA_GLYPHS, lagna: LAGNA_GLYPH };

export interface AstroGlyphProps {
  name: GlyphName;
  size?: number;
  /** When given the glyph is an image with this accessible name; otherwise it is decorative. */
  title?: string;
  className?: string;
}

/** Stroke glyph set (MASTER §7.2): 24x24, 1.75 stroke, currentColor. */
export function AstroGlyph({ name, size = 20, title, className }: AstroGlyphProps) {
  const paths = ALL[name] ?? [];
  return (
    <svg
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      role={title ? "img" : undefined}
      aria-label={title}
      aria-hidden={title ? undefined : true}
      className={cn("shrink-0", className)}
    >
      {paths.map((d, i) => (
        <path key={i} d={d} />
      ))}
    </svg>
  );
}

/** Same glyph as raw <path>s for use inside another <svg> (ChartWheel). Positioned by `x`,`y` = top-left. */
export function GlyphInSvg({ name, x, y, size, className }: { name: GlyphName; x: number; y: number; size: number; className?: string }) {
  const paths = ALL[name] ?? [];
  const s = size / 24;
  return (
    <g transform={`translate(${x} ${y}) scale(${s})`} fill="none" strokeWidth={1.75 / 1} strokeLinecap="round" strokeLinejoin="round" className={className} aria-hidden="true">
      {paths.map((d, i) => (
        <path key={i} d={d} />
      ))}
    </g>
  );
}
