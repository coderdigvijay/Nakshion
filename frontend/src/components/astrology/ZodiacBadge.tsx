import { AstroGlyph } from "./glyphs/AstroGlyph";
import { hasGlyph } from "./glyphs/paths";
import { cn } from "../../lib/utils";
import { ELEMENT_LABEL, ELEMENT_TEXT, findSign, SYSTEM_LABEL, type Element, type ZodiacSystem } from "../../lib/astro";
export type { ZodiacSystem } from "../../lib/astro";

// COMPONENTS.md → ZodiacBadge. No Unicode zodiac glyphs (they render as emoji on iOS/Android):
// the circle carries the custom sign glyph (components/astrology/glyphs); the sign is always written out in text.

const ELEMENT_CIRCLE: Record<Element, string> = {
  fire: "bg-fire/12 ring-fire/40",
  earth: "bg-earth/12 ring-earth/40",
  air: "bg-air/12 ring-air/40",
  water: "bg-water/12 ring-water/40",
};

const ICON_PX = { xs: 12, sm: 16, md: 20, lg: 28, xl: 36 } as const;

const SIZE = {
  xs: { circle: "size-5", icon: "size-3", label: "" },
  sm: { circle: "size-6", icon: "size-3.5", label: "text-body-sm" },
  md: { circle: "size-8", icon: "size-4", label: "text-[0.9375rem]" },
  lg: { circle: "size-12", icon: "size-6", label: "text-[1.125rem] font-semibold" },
  xl: { circle: "size-16", icon: "size-8", label: "text-h3 font-display" },
} as const;


export interface ZodiacBadgeProps {
  /** English sign or rashi name. */
  sign: string | undefined;
  system: ZodiacSystem;
  size?: keyof typeof SIZE;
  variant?: "glyph" | "labeled" | "role";
  /** Overline for `role` variant: "Sun", "Moon", "Lagna". */
  role?: string;
  /** Extra line under the sign, e.g. Moon nakshatra. */
  extra?: string;
  accent?: boolean;
  className?: string;
}

export function ZodiacBadge({ sign, system, size = "md", variant = "labeled", role, extra, accent, className }: ZodiacBadgeProps) {
  const info = findSign(sign);
  // In the "role" tile the glyph sits beside its own label, so it is always the small circle.
  const eff = variant === "role" ? "sm" : size;
  const s = SIZE[eff];
  const el = info?.element;
  const glyphName = info ? info.english.toLowerCase() : "";
  const circle = (
    <span
      aria-hidden={variant !== "glyph" || undefined}
      role={variant === "glyph" ? "img" : undefined}
      aria-label={variant === "glyph" ? `${info?.english ?? "Unknown sign"} (${SYSTEM_LABEL[system]})` : undefined}
      className={cn(
        "inline-flex shrink-0 items-center justify-center rounded-chip ring-1",
        el ? ELEMENT_CIRCLE[el] : "bg-elevated ring-border",
        accent && "ring-2 ring-accent",
        s.circle,
      )}
    >
      {hasGlyph(glyphName) ? (
        <AstroGlyph name={glyphName} size={ICON_PX[eff]} className={el ? ELEMENT_TEXT[el] : "text-fg-muted"} />
      ) : (
        <span aria-hidden="true" className="text-caption text-fg-muted">?</span>
      )}
    </span>
  );

  if (variant === "glyph") return <span className={className}>{circle}</span>;

  const name = info ? info.english : "Unknown";
  const secondary = info ? `${info.rashi}${el ? ` · ${ELEMENT_LABEL[el]}` : ""}` : undefined;

  if (variant === "role") {
    const roleColour = role === "Sun" ? "text-sun" : role === "Moon" ? "text-moon" : "text-fg";
    return (
      <div className={cn("flex min-w-0 flex-col gap-0.5 break-words text-left [overflow-wrap:anywhere]", className)}>
        <div className="flex items-center gap-2">
          {circle}
          <p className={cn("text-caption font-medium", accent ? "text-accent-text" : "text-fg-muted")}>{role}</p>
        </div>
        <p className={cn("mt-1 text-[1rem] font-semibold leading-snug", roleColour)}>{info ? (system === "sidereal" ? info.rashi : info.english) : name}</p>
        {(system === "sidereal" || !info) && <p className="text-caption text-fg-secondary">{info ? info.english : "Needs birth time"}</p>}
        {extra && <p className="text-caption text-fg-secondary">{extra}</p>}
        <p className="text-caption text-fg-muted">{system === "sidereal" ? "Vedic · sidereal" : "Western · tropical"}</p>
      </div>
    );
  }

  return (
    <span className={cn("inline-flex items-center gap-2", className)}>
      {circle}
      <span className="min-w-0">
        <span className={cn("block text-fg", s.label)}>{name}</span>
        {size !== "xs" && size !== "sm" && secondary && <span className="block text-caption text-fg-muted">{secondary}</span>}
      </span>
      <span className="sr-only">({SYSTEM_LABEL[system]})</span>
    </span>
  );
}

/** Small "Vedic · sidereal (Lahiri)" marker shown next to sign data (rules §4: always show the system). */
export function SystemTag({ system, className }: { system: ZodiacSystem; className?: string }) {
  return (
    <span className={cn("text-caption text-fg-muted", className)}>
      {system === "sidereal" ? "Vedic · sidereal (Lahiri)" : "Western · tropical"}
    </span>
  );
}
