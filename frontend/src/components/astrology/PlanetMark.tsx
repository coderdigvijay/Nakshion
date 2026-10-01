import { ChevronDown, ChevronUp, Flame, RotateCcw } from "lucide-react";
import { cn } from "../../lib/utils";
import { AstroGlyph } from "./glyphs/AstroGlyph";
import { GRAHA_TEXT, type GrahaKey } from "../../lib/astro";
import type { Dignity } from "../../lib/chartModel";
import { Badge } from "../ui/Badge";

/** Planet identity mark: two-letter abbreviation in the graha colour (MASTER §7.2). */
export function PlanetMark({ abbr, grahaKey, size = "md", className }: { abbr: string; grahaKey: GrahaKey | undefined; size?: "sm" | "md"; className?: string }) {
  return (
    <span
      aria-hidden="true"
      className={cn(
        "inline-flex shrink-0 items-center justify-center rounded-chip bg-elevated font-semibold ring-1 ring-border",
        size === "md" ? "size-8 text-body-sm" : "size-6 text-overline",
        grahaKey ? GRAHA_TEXT[grahaKey] : "text-fg-muted",
        className,
      )}
    >
      {grahaKey ? <AstroGlyph name={grahaKey} size={size === "md" ? 18 : 14} /> : abbr}
    </span>
  );
}

const DIGNITY_BADGE: Partial<Record<Dignity, { label: string; tone: "success" | "accent" | "danger"; icon?: React.ReactNode }>> = {
  exalted: { label: "Exalted", tone: "success", icon: <ChevronUp aria-hidden="true" /> },
  own: { label: "Own sign", tone: "accent" },
  mooltrikona: { label: "Mooltrikona", tone: "accent" },
  debilitated: { label: "Debilitated", tone: "danger", icon: <ChevronDown aria-hidden="true" /> },
};

/** Canonical state badges (COMPONENTS.md → Badge): colour is never the only cue. */
export function PlanetStateBadges({ dignity, retrograde, combust }: { dignity: Dignity; retrograde: boolean; combust: boolean }) {
  const d = DIGNITY_BADGE[dignity];
  if (!d && !retrograde && !combust) return null;
  return (
    <span className="flex flex-wrap gap-1.5">
      {d && (
        <Badge tone={d.tone} icon={d.icon}>
          {d.label}
        </Badge>
      )}
      {retrograde && (
        <Badge tone="info" icon={<RotateCcw aria-hidden="true" />}>
          Retrograde
        </Badge>
      )}
      {combust && (
        <Badge tone="warning" icon={<Flame aria-hidden="true" />}>
          Combust
        </Badge>
      )}
    </span>
  );
}
