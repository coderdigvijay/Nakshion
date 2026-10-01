import { AlertTriangle, Sunrise, Sunset } from "lucide-react";
import { Card, CardHeader } from "../ui/Card";
import { ErrorState } from "../ui/EmptyState";
import { Skeleton } from "../ui/Skeleton";
import { usePanchang } from "../../hooks/usePanchang";

// C9 Panchang for today (pages/dashboard.md → timing). Shown only when the server provides it.

function localIsoDate(d = new Date()): string {
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${m}-${day}`;
}

/** "18:10" or "03:20 (+1)". Uses the server's end date when sent, else infers "next day" from sunrise. */
function endText(item: { end_local: string | null; end_local_date?: string | null }, date: string, sunrise: string | null): string | null {
  if (!item.end_local) return null;
  const nextDay = item.end_local_date ? item.end_local_date > date : sunrise !== null && item.end_local < sunrise;
  return nextDay ? `${item.end_local} (+1)` : item.end_local;
}

function Row({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="flex items-baseline justify-between gap-3 py-2">
      <dt className="text-body-sm text-fg-muted">{label}</dt>
      <dd className="min-w-0 text-right text-body-sm text-fg">
        {value}
        {sub && <span className="block text-caption text-fg-muted">{sub}</span>}
      </dd>
    </div>
  );
}

export function PanchangCard({ lat, lon }: { lat: number; lon: number }) {
  const q = usePanchang(localIsoDate(), lat, lon);
  const p = q.data;
  return (
    <Card as="section" aria-labelledby="panchang" className="h-full">
      <CardHeader overline="Panchang" title="Today's sky" titleId="panchang" />
      {q.isLoading ? (
        <div aria-busy="true" className="space-y-3">
          <span role="status" className="sr-only">
            Loading Panchang
          </span>
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-5" />
          ))}
        </div>
      ) : q.isError || !p || !p.tithi || !p.nakshatra ? (
        <ErrorState compact error={q.error} what="the Panchang" onRetry={() => void q.refetch()} retrying={q.isFetching} />
      ) : (
        <>
          <dl className="divide-y divide-border">
            <Row label="Tithi" value={`${p.tithi.paksha} ${p.tithi.name}`} sub={endText(p.tithi, p.date, p.sunrise_local) ? `until ${endText(p.tithi, p.date, p.sunrise_local)}` : undefined} />
            <Row label="Nakshatra" value={`${p.nakshatra.name} · pada ${p.nakshatra.pada}`} sub={endText(p.nakshatra, p.date, p.sunrise_local) ? `until ${endText(p.nakshatra, p.date, p.sunrise_local)}` : undefined} />
            {p.yoga?.name && <Row label="Yoga" value={p.yoga.name} />}
          </dl>
          {p.rahu_kaal?.start_local && p.rahu_kaal.end_local && (
            <p className="mt-3 flex items-center gap-2 rounded-control bg-elevated p-3 text-caption tabular text-warning">
              <AlertTriangle aria-hidden="true" className="size-4 shrink-0" />
              Rahu Kaal {p.rahu_kaal.start_local} – {p.rahu_kaal.end_local}
            </p>
          )}
          {p.sunrise_available && p.sunrise_local && p.sunset_local && (
            <p className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-caption tabular text-fg-secondary">
              <span className="flex items-center gap-1.5">
                <Sunrise aria-hidden="true" className="size-4" /> {p.sunrise_local}
              </span>
              <span className="flex items-center gap-1.5">
                <Sunset aria-hidden="true" className="size-4" /> {p.sunset_local}
              </span>
              <span className="text-fg-muted">{p.timezone}</span>
            </p>
          )}
        </>
      )}
    </Card>
  );
}
