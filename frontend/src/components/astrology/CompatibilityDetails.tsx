import { ChevronRight, Info } from "lucide-react";
import type { AshtakootaResult, ScoreBreakdown } from "../../types";
import { Badge } from "../ui/Badge";
import { Card } from "../ui/Card";

// Engine 2.0 compatibility extras. Every field is optional/nullable on purpose: older reports
// and non-romantic types simply omit them.

const CATEGORY_LABEL: Record<string, string> = {
  emotional: "Emotional",
  communication: "Communication",
  romance: "Romance and warmth",
  passion: "Passion and drive",
  "long-term": "Long-term",
};

const pct = (n: number) => `${Math.round(n * 100)}%`;

export function ScoreBreakdownCard({ breakdown }: { breakdown: ScoreBreakdown | null | undefined }) {
  if (!breakdown) return null;
  const weights = breakdown.category_weights ?? {};
  const keys = Object.keys(weights);
  const asht = breakdown.ashtakoota;
  return (
    <Card as="section" aria-labelledby="how-built" padding="sm">
      <details className="group">
        <summary className="focus-ring flex min-h-11 cursor-pointer list-none items-center justify-between gap-3 rounded-control">
          <h2 id="how-built" className="font-sans text-title text-fg">
            How this score is built
          </h2>
          <ChevronRight aria-hidden="true" className="size-5 text-fg-muted transition-transform group-open:rotate-90" />
        </summary>
        <div className="space-y-4 pt-3">
          {breakdown.explanation && <p className="text-body-sm text-fg-secondary">{breakdown.explanation}</p>}
          {keys.length > 0 && (
            <table className="w-full text-left text-body-sm">
              <caption className="sr-only">Category weights and contributions to the overall score</caption>
              <thead>
                <tr className="border-b border-border text-caption text-fg-muted">
                  <th scope="col" className="py-2 pr-3 font-medium">Category</th>
                  <th scope="col" className="py-2 pr-3 text-right font-medium">Score</th>
                  <th scope="col" className="py-2 pr-3 text-right font-medium">Weight</th>
                  <th scope="col" className="py-2 text-right font-medium">Adds</th>
                </tr>
              </thead>
              <tbody>
                {keys.map((k) => (
                  <tr key={k} className="border-b border-border">
                    <th scope="row" className="py-2 pr-3 font-normal text-fg">{CATEGORY_LABEL[k] ?? k}</th>
                    <td className="py-2 pr-3 text-right tabular text-fg-secondary">{breakdown.category_scores?.[k]?.toFixed(1) ?? "—"}</td>
                    <td className="py-2 pr-3 text-right tabular text-fg-secondary">{pct(weights[k])}</td>
                    <td className="py-2 text-right tabular text-fg">{breakdown.weighted_contributions?.[k]?.toFixed(2) ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {breakdown.formula && <p className="rounded-control bg-elevated p-3 text-caption tabular text-fg-secondary">{breakdown.formula}</p>}
          {asht && (
            <p className="text-caption text-fg-muted">
              {asht.included
                ? `Ashtakoota counts for half of this score${asht.total !== undefined ? ` (${asht.total} of 36` : ""}${asht.scaled_0_10 !== undefined ? `, scaled to ${asht.scaled_0_10.toFixed(1)} of 10` : ""}${asht.total !== undefined ? ")" : ""}. Details are in the table above.`
                : "Ashtakoota isn't part of this score for this kind of relationship."}
            </p>
          )}
          {breakdown.overall_range && (
            <p className="text-caption text-fg-muted">
              Because a birth time is missing, the overall score could fall anywhere from {breakdown.overall_range[0].toFixed(1)} to {breakdown.overall_range[1].toFixed(1)}.
            </p>
          )}
        </div>
      </details>
    </Card>
  );
}

export function AshtakootaCard({ data }: { data: AshtakootaResult | null | undefined }) {
  if (!data) return null;
  const max = data.max ?? 36;
  const doshas: Array<[boolean | undefined, string]> = [
    [data.nadi_dosha, "Nadi dosha"],
    [data.bhakoot_dosha, "Bhakoot dosha"],
    [data.gana_dosha, "Gana dosha"],
  ];
  return (
    <Card as="section" aria-labelledby="ashtakoota">
      <h2 id="ashtakoota" className="font-sans text-title text-fg">
        Ashtakoota (guna milan)
      </h2>
      <p className="mt-1 text-body text-fg">
        <span className="font-display text-h3 tabular">{data.total}</span> <span className="text-fg-muted">out of {max}</span>
        {data.moon_ambiguous && data.total_range && data.total_range[0] !== data.total_range[1] && <span className="ml-2 text-caption text-fg-secondary tabular">(range {data.total_range[0]}–{data.total_range[1]} without a birth time)</span>}
        {data.verdict && <span className="ml-2 capitalize text-fg-secondary">· {data.verdict.replace(/_/g, " ")}</span>}
      </p>
      {data.kootas && data.kootas.length > 0 && (
        <table className="mt-3 w-full text-left text-body-sm">
          <caption className="sr-only">Eight kootas with score out of maximum</caption>
          <thead>
            <tr className="border-b border-border text-caption text-fg-muted">
              <th scope="col" className="py-2 pr-3 font-medium">Koota</th>
              <th scope="col" className="py-2 pr-3 text-right font-medium">Score</th>
              <th scope="col" className="py-2 font-medium">Note</th>
            </tr>
          </thead>
          <tbody>
            {data.kootas.map((k) => (
              <tr key={k.name} className="border-b border-border align-top">
                <th scope="row" className="py-2 pr-3 font-normal text-fg">{k.name}</th>
                <td className="py-2 pr-3">
                  <span className="flex items-center justify-end gap-2">
                    <span
                      role="meter"
                      aria-label={`${k.name} score`}
                      aria-valuemin={0}
                      aria-valuemax={k.max}
                      aria-valuenow={k.score}
                      className="block h-1.5 w-16 shrink-0 overflow-hidden rounded-chip bg-border"
                    >
                      <span className={`block h-full origin-left rounded-chip ${k.score >= k.max ? "bg-success" : k.score === 0 ? "bg-transparent" : "bg-accent"}`} style={{ transform: `scaleX(${k.max ? k.score / k.max : 0})` }} />
                    </span>
                    <span className="w-12 shrink-0 text-right tabular text-fg">
                      {k.score} / {k.max}
                    </span>
                  </span>
                </td>
                <td className="py-2 text-fg-secondary">{k.note}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {doshas.some(([on]) => on) && (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {doshas.filter(([on]) => on).map(([, label]) => (
            <Badge key={label} tone="warning">{label}</Badge>
          ))}
          <p className="text-caption text-fg-muted">Traditional remedies exist, and many astrologers weigh these against the whole chart.</p>
        </div>
      )}
      {(data.moon_ambiguous || data.note) && (
        <p className="mt-3 flex gap-2 rounded-control bg-info-subtle p-3 text-caption text-fg-secondary">
          <Info aria-hidden="true" className="mt-px size-4 shrink-0 text-info" />
          {data.note ?? "Without an exact birth time the Moon sign can differ, so these points may change."}
        </p>
      )}
      {data.alternate_total !== undefined && data.alternate_total !== null && (
        <p className="mt-2 text-caption text-fg-muted">Traditional matching assigns bride and groom roles. The other order scores {data.alternate_total}; we show the lower.</p>
      )}
      {data.tables_fixture_verified === false && (
        <p className="mt-2 text-caption text-fg-muted">{data.tables_note ?? "Vashya, Gana and Yoni tables are pending verification against reference charts."}</p>
      )}
    </Card>
  );
}
