import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "../../lib/utils";
import { findGraha, GRAHA_BG, GRAHA_TEXT } from "../../lib/astro";
import { formatMonthYear, parseCivilDate } from "../../lib/format";
import { DASHA_THEMES } from "../../lib/interpretationCopy";
import type { DashaInfo, DashaPeriod } from "../../types";
import { Badge } from "../ui/Badge";
import { PlanetMark } from "./PlanetMark";

// COMPONENTS.md → DashaTimeline, MASTER §9.3. Uses `dasha.timeline` when the engine sends it
// ([v1-add]); otherwise renders the MVP current Mahadasha/Antardasha pair.

function years(start: string, end: string): number {
  const a = parseCivilDate(start)?.getTime();
  const b = parseCivilDate(end)?.getTime();
  if (!a || !b) return 0;
  return Math.round(((b - a) / (365.25 * 24 * 3600 * 1000)) * 10) / 10;
}

function isCurrent(p: DashaPeriod, now: Date) {
  const s = parseCivilDate(p.start);
  const e = parseCivilDate(p.end);
  return !!s && !!e && s <= now && now < e;
}

function progress(start: string, end: string, now: Date): number {
  const s = parseCivilDate(start)?.getTime();
  const e = parseCivilDate(end)?.getTime();
  if (!s || !e || e <= s) return 0;
  return Math.min(1, Math.max(0, (now.getTime() - s) / (e - s)));
}

function sanskrit(lord: string) {
  return findGraha(lord)?.sanskrit ?? lord;
}

export function DashaSummary({ dasha, className }: { dasha: DashaInfo; className?: string }) {
  const md = dasha.maha_dasha;
  const ad = dasha.antar_dasha;
  const pct = progress(ad.start, ad.end, new Date());
  return (
    <div className={className}>
      <p className="text-body text-fg">
        You're in{" "}
        <span className="font-semibold text-accent-text">
          {sanskrit(md.current)} Mahadasha → {sanskrit(ad.current)} Antardasha
        </span>{" "}
        until {formatMonthYear(ad.end)}.
      </p>
      <div
        role="meter"
        aria-label={`${ad.current} Antardasha progress`}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(pct * 100)}
        aria-valuetext={`${Math.round(pct * 100)} percent through, ends ${formatMonthYear(ad.end)}`}
        className="mt-3 h-2 overflow-hidden rounded-chip bg-elevated"
      >
        <div className="h-full origin-left rounded-chip bg-accent" style={{ transform: `scaleX(${pct})` }} />
      </div>
      {dasha.approximate && <p className="mt-1.5 text-caption text-fg-muted">Approximate: birth time unknown.</p>}
      <p className="mt-1.5 flex justify-between text-caption tabular text-fg-muted">
        <span>{formatMonthYear(ad.start)}</span>
        <span>{formatMonthYear(ad.end)}</span>
      </p>
    </div>
  );
}

export function DashaTimeline({ dasha, now = new Date() }: { dasha: DashaInfo; now?: Date }) {
  const timeline = dasha.timeline;
  const initiallyOpen = timeline?.find((p) => isCurrent(p, now))?.lord ?? null;
  const [open, setOpen] = useState<string | null>(initiallyOpen);

  if (!timeline || timeline.length === 0) {
    const md = dasha.maha_dasha;
    const ad = dasha.antar_dasha;
    return (
      <div className="space-y-4">
        <DashaSummary dasha={dasha} />
        <ol className="space-y-3">
          {[
            { kind: "Mahadasha", lord: md.current, start: md.start, end: md.end },
            { kind: "Antardasha", lord: ad.current, start: ad.start, end: ad.end },
          ].map((row) => {
            const g = findGraha(row.lord);
            return (
              <li key={row.kind} className="flex gap-3 rounded-control border border-border bg-surface p-4 shadow-[inset_3px_0_0_var(--nk-accent)]">
                <PlanetMark abbr={g?.abbr ?? row.lord.slice(0, 2)} grahaKey={g?.key} />
                <div className="min-w-0">
                  <p className="flex flex-wrap items-center gap-2 text-[0.9375rem] font-semibold text-fg">
                    {sanskrit(row.lord)} {row.kind} <Badge tone="accent">Current</Badge>
                  </p>
                  <p className="text-caption tabular text-fg-muted">
                    {formatMonthYear(row.start)} – {formatMonthYear(row.end)} · {years(row.start, row.end)} years
                  </p>
                  {DASHA_THEMES[g?.english ?? row.lord] && (
                    <p className="mt-1 text-body-sm text-fg-secondary">Themes: {DASHA_THEMES[g?.english ?? row.lord]}.</p>
                  )}
                </div>
              </li>
            );
          })}
        </ol>
        <p className="text-caption text-fg-muted">The full 120-year timeline appears here once your chart is recalculated with the latest engine.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <DashaSummary dasha={dasha} />
      <ol className="space-y-2">
        {timeline.map((p) => {
          const g = findGraha(p.lord);
          const current = isCurrent(p, now);
          const past = (parseCivilDate(p.end)?.getTime() ?? 0) <= now.getTime();
          const expanded = open === p.lord;
          const panelId = `dasha-${p.lord}`;
          return (
            <li key={`${p.lord}-${p.start}`} className={cn("rounded-control border border-border bg-surface", current && "shadow-[inset_3px_0_0_var(--nk-accent)]")}>
              <button
                type="button"
                aria-expanded={expanded}
                aria-controls={panelId}
                aria-label={`${g?.english ?? p.lord} Mahadasha, ${formatMonthYear(p.start)} to ${formatMonthYear(p.end)}${current ? ", current" : past ? ", past" : ""}`}
                onClick={() => setOpen(expanded ? null : p.lord)}
                className="focus-ring flex w-full cursor-pointer items-center gap-3 rounded-control p-3 text-left hover:bg-elevated"
              >
                <PlanetMark abbr={g?.abbr ?? p.lord.slice(0, 2)} grahaKey={g?.key} />
                <span className="min-w-0 flex-1">
                  <span className={cn("flex flex-wrap items-center gap-2 text-[0.9375rem] font-semibold", past ? "text-fg-secondary" : "text-fg")}>
                    {sanskrit(p.lord)} Mahadasha {current && <Badge tone="accent">Current</Badge>}
                  </span>
                  <span className="block text-caption tabular text-fg-muted">
                    {formatMonthYear(p.start)} – {formatMonthYear(p.end)} · {years(p.start, p.end)} years
                  </span>
                </span>
                <ChevronDown aria-hidden="true" className={cn("size-5 text-fg-muted transition-transform duration-150", expanded && "rotate-180")} />
              </button>
              {expanded && (
                <div id={panelId} className="border-t border-border px-3 pb-3 pt-2">
                  {DASHA_THEMES[g?.english ?? p.lord] && <p className="mb-2 text-body-sm text-fg-secondary">Themes: {DASHA_THEMES[g?.english ?? p.lord]}.</p>}
                  {p.antar && p.antar.length > 0 && (
                    <ol className="grid gap-1 sm:grid-cols-2">
                      {p.antar.map((a) => {
                        const ag = findGraha(a.lord);
                        const ac = isCurrent(a, now);
                        return (
                          <li key={`${a.lord}-${a.start}`} className={cn("flex items-center gap-2 rounded-[8px] px-2 py-1.5 text-body-sm", ac && "bg-accent-subtle")}>
                            <span aria-hidden="true" className={cn("size-2 rounded-chip", ag ? GRAHA_BG[ag.key] : "bg-fg-muted")} />
                            <span className={cn("font-medium", ag ? GRAHA_TEXT[ag.key] : "text-fg")}>{sanskrit(a.lord)}</span>
                            <span className="tabular text-fg-muted">
                              {formatMonthYear(a.start)} – {formatMonthYear(a.end)}
                            </span>
                            {ac && <span className="sr-only">(current)</span>}
                          </li>
                        );
                      })}
                    </ol>
                  )}
                </div>
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
}
