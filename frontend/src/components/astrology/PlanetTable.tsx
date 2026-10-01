import { cn } from "../../lib/utils";
import { degAriaLabel, formatDeg, ordinal, SIGNS } from "../../lib/astro";
import type { WheelPlanet } from "../../lib/chartModel";
import { PlanetMark, PlanetStateBadges } from "./PlanetMark";
import { ZodiacBadge, type ZodiacSystem } from "./ZodiacBadge";

// COMPONENTS.md → PlanetRow. Semantic <table> at >= 768px, stacked rows below. No card per planet.

export interface PlanetTableProps {
  planets: WheelPlanet[];
  system: ZodiacSystem;
  highlightHouse?: number | null;
  onHoverHouse?: (house: number | null) => void;
  caption: string;
}

export function PlanetTable({ planets, system, highlightHouse, onHoverHouse, caption }: PlanetTableProps) {
  return (
    <>
      {/* Desktop / tablet */}
      <div className="hidden overflow-x-auto md:block">
        <table className="w-full border-collapse text-left">
          <caption className="sr-only">{caption}</caption>
          <thead>
            <tr className="border-b border-border text-caption font-medium text-fg-muted">
              <th scope="col" className="py-3 pl-3 pr-4 font-medium">Graha</th>
              <th scope="col" className="py-3 pr-4 font-medium">Sign</th>
              <th scope="col" className="py-3 pr-4 font-medium">Degree</th>
              <th scope="col" className="py-3 pr-4 font-medium">House</th>
              <th scope="col" className="py-3 pr-4 font-medium">Nakshatra</th>
              <th scope="col" className="py-3 pr-3 font-medium">State</th>
            </tr>
          </thead>
          <tbody>
            {planets.map((p) => {
              const hl = p.house > 0 && highlightHouse === p.house;
              return (
                <tr
                  key={p.english}
                  onMouseEnter={() => p.house > 0 && onHoverHouse?.(p.house)}
                  onMouseLeave={() => onHoverHouse?.(null)}
                  className={cn(
                    "border-b border-border transition-colors duration-150 hover:bg-elevated",
                    hl && "bg-ai-subtle shadow-[inset_3px_0_0_var(--nk-ai)] hover:bg-ai-subtle",
                  )}
                >
                  <th scope="row" className="py-3 pl-3 pr-4 font-normal">
                    <span className="flex items-center gap-3">
                      <PlanetMark abbr={p.abbr} grahaKey={p.key} />
                      <span>
                        <span className="block text-[0.9375rem] font-semibold text-fg">{p.sanskrit}</span>
                        <span className="block text-caption text-fg-muted">{p.english}</span>
                      </span>
                    </span>
                  </th>
                  <td className="py-3 pr-4">
                    <ZodiacBadge sign={SIGNS[p.signIdx]?.english} system={system} size="sm" />
                  </td>
                  <td className="py-3 pr-4 tabular text-fg" aria-label={degAriaLabel(p.degree)}>
                    {formatDeg(p.degree)}
                  </td>
                  <td className="py-3 pr-4 text-fg-secondary">{p.house > 0 ? ordinal(p.house) : "—"}</td>
                  <td className="py-3 pr-4 text-body-sm text-fg-secondary">
                    {p.nakshatra ? `${p.nakshatra}${p.pada ? ` · pada ${p.pada}` : ""}` : "—"}
                  </td>
                  <td className="py-3 pr-3">
                    <PlanetStateBadges dignity={p.dignity} retrograde={p.retrograde} combust={p.combust} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Mobile */}
      <ul className="divide-y divide-border md:hidden" aria-label={caption}>
        {planets.map((p) => {
          const hl = p.house > 0 && highlightHouse === p.house;
          return (
            <li key={p.english} className={cn("py-3 pl-1 pr-1", hl && "bg-ai-subtle shadow-[inset_3px_0_0_var(--nk-ai)] pl-3")}>
              <div className="flex items-center gap-3">
                <PlanetMark abbr={p.abbr} grahaKey={p.key} />
                <p className="min-w-0 flex-1">
                  <span className="text-[0.9375rem] font-semibold text-fg">{p.sanskrit}</span>{" "}
                  <span className="text-caption text-fg-muted">{p.english}</span>
                </p>
                <span className="text-body-sm text-fg-secondary">{p.house > 0 ? `${ordinal(p.house)} house` : ""}</span>
              </div>
              <p className="mt-1 pl-11 text-body-sm text-fg-secondary">
                {SIGNS[p.signIdx]?.rashi} ({SIGNS[p.signIdx]?.english}){" "}
                <span className="tabular text-fg" aria-label={degAriaLabel(p.degree)}>
                  {formatDeg(p.degree)}
                </span>
                {p.nakshatra && ` · ${p.nakshatra}${p.pada ? ` pada ${p.pada}` : ""}`}
              </p>
              <div className="mt-2 pl-11 empty:hidden">
                <PlanetStateBadges dignity={p.dignity} retrograde={p.retrograde} combust={p.combust} />
              </div>
            </li>
          );
        })}
      </ul>
    </>
  );
}
