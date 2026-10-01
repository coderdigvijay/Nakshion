import { useMemo, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { AlertTriangle, CheckCircle2, Info, Share2, Sparkles } from "lucide-react";
import { AppShell } from "../components/layout/AppShell";
import { Card } from "../components/ui/Card";
import { Button, ButtonLink } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import { Select } from "../components/ui/Select";
import { Segmented, TabPanel, Tabs } from "../components/ui/Tabs";
import { EmptyState, ErrorState } from "../components/ui/EmptyState";
import { LoadingRegion, Skeleton } from "../components/ui/Skeleton";
import { Dialog } from "../components/ui/Dialog";
import { ChartWheel, ChartWheelLegend } from "../components/astrology/ChartWheel";
import { PlanetTable } from "../components/astrology/PlanetTable";
import { PlanetMark } from "../components/astrology/PlanetMark";
import { DashaTimeline } from "../components/astrology/DashaTimeline";
import { SystemTag, ZodiacBadge } from "../components/astrology/ZodiacBadge";
import { useCharts, useDasha, useTransits, isSavedPerson, pickPrimaryChart } from "../hooks/useCharts";
import { ChartShareDialog } from "../components/astrology/ChartShareDialog";
import { IconButton } from "../components/ui/IconButton";
import { wheelSummary } from "../lib/chartModel";
import { usePrefsStore, type ChartFormat } from "../store/prefsStore";
import { chartWheelData, divisionalWheel, housesAvailable, isApproximate, type WheelData } from "../lib/chartModel";
import { coreSignature } from "../lib/interpretationCopy";
import { findGraha, formatCoords, formatDeg, HOUSE_THEMES, ordinal, SIGNS } from "../lib/astro";
import { formatCivilDate, formatTime24 } from "../lib/format";
import type { BirthChart, DashaInfo, TransitsResponse, VedicData } from "../types";

type TabKey = "planets" | "houses" | "aspects" | "dasha" | "yogas" | "transits";
type Varga = "d1" | "d9" | "d10";
const TAB_KEYS: TabKey[] = ["planets", "houses", "aspects", "dasha", "yogas", "transits"];

function useIsDesktop() {
  return typeof window !== "undefined" && window.matchMedia?.("(min-width: 1024px)").matches;
}

function HouseDetail({ data, house, vedic }: { data: WheelData; house: number; vedic?: VedicData }) {
  const sign = SIGNS[(data.lagnaIdx + house - 1) % 12];
  const ps = data.planets.filter((p) => p.house === house);
  const lord = vedic?.house_lords?.find((h) => h.house === house);
  return (
    <div className="space-y-3">
      <ZodiacBadge sign={sign?.english} system="sidereal" size="md" />
      <p className="text-body-sm text-fg-secondary">
        {ordinal(house)} house · {HOUSE_THEMES[house]}
      </p>
      {lord && (
        <p className="text-body-sm text-fg-secondary">
          Lord: <span className="font-medium text-fg">{lord.lord}</span>, placed in the {ordinal(lord.lord_in_house)} house
        </p>
      )}
      {ps.length === 0 ? (
        <p className="text-body-sm text-fg-muted">No planets in this house.</p>
      ) : (
        <ul className="space-y-2">
          {ps.map((p) => (
            <li key={p.english} className="flex items-center gap-3">
              <PlanetMark abbr={p.abbr} grahaKey={p.key} size="sm" />
              <span className="text-body-sm text-fg">
                {p.sanskrit} ({p.english}) <span className="tabular text-fg-secondary">{formatDeg(p.degree)}</span>
                {p.retrograde && <span className="text-fg-muted"> · retrograde</span>}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function ChartFacts({ chart, hasHouses }: { chart: BirthChart; hasHouses: boolean }) {
  const v = chart.chart_data.vedic;
  if (!v) return null;
  const moon = v.planets.find((p) => findGraha(p.english)?.key === "moon");
  const rows: Array<[string, string]> = [];
  if (hasHouses && v.lagna) rows.push(["Lagna (Ascendant)", `${v.lagna.rashi} (${v.lagna.rashi_english}) · ${v.lagna.nakshatra}${v.lagna.pada ? ` pada ${v.lagna.pada}` : ""}`]);
  if (moon) rows.push(["Moon sign", `${moon.rashi} (${moon.rashi_english})`]);
  if (v.moon_nakshatra?.name) rows.push(["Moon nakshatra", `${v.moon_nakshatra.name}${v.moon_nakshatra.pada ? ` · pada ${v.moon_nakshatra.pada}` : ""}${v.moon_nakshatra.lord ? ` · lord ${v.moon_nakshatra.lord}` : ""}`]);
  if (v.dasha?.maha_dasha?.current) rows.push(["Current dasha", `${v.dasha.maha_dasha.current} → ${v.dasha.antar_dasha?.current ?? ""}`]);
  if (v.sade_sati) rows.push(["Sade Sati", v.sade_sati.active ? `Active (${v.sade_sati.phase})` : "Not active"]);
  if (rows.length === 0) return null;
  return (
    <Card as="section" aria-labelledby="facts">
      <h2 id="facts" className="mb-2 font-sans text-title text-fg">
        At a glance
      </h2>
      <dl className="divide-y divide-border">
        {rows.map(([k, val]) => (
          <div key={k} className="flex items-baseline justify-between gap-4 py-2.5">
            <dt className="text-body-sm text-fg-muted">{k}</dt>
            <dd className="min-w-0 text-right text-body-sm text-fg">{val}</dd>
          </div>
        ))}
      </dl>
    </Card>
  );
}

function DashaApproxNote({ approximate, dasha }: { approximate: boolean; dasha: DashaInfo }) {
  if (!approximate) return null;
  const c = dasha.candidates ?? [];
  return (
    <div className="mb-4 flex gap-2 rounded-control bg-info-subtle p-3 text-caption text-fg-secondary">
      <Info aria-hidden="true" className="mt-px size-4 shrink-0 text-info" />
      <div className="space-y-1.5">
        <p className="font-semibold text-fg">Approximate dasha dates</p>
        <p>
          {dasha.approximate_note ??
            "Without an exact birth time the Moon's position, and so the dasha balance at birth, can shift. Treat these dates as a guide, not a fixed schedule."}
        </p>
        {c.length > 0 && (
          <ul className="space-y-0.5">
            {c.map((x, i) => (
              <li key={i}>
                {i === 0 ? "If born just after midnight" : "If born just before midnight"}: {x.maha_dasha} → {x.antar_dasha}
                {x.balance_at_birth_years !== undefined && <span className="tabular"> (balance at birth {x.balance_at_birth_years.toFixed(1)} years)</span>}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

function NeedsBirthTime({ compact }: { compact?: boolean }) {
  return (
    <Card variant="raised" className={compact ? "" : "text-center"}>
      <Info aria-hidden="true" className={compact ? "mb-2 size-5 text-info" : "mx-auto mb-3 size-7 text-info"} />
      <h3 className="font-sans text-title text-fg">Add your birth time to unlock houses and ascendant</h3>
      <p className="mt-2 text-body-sm text-fg-secondary">
        Houses and your Lagna (Ascendant) depend on the exact time you were born. Planet signs, nakshatras and approximate dasha periods stay available. The D9 and D10 charts also need your birth time.
      </p>
      <ButtonLink to="/profile#charts" variant="secondary" size="sm" className="mt-4">
        Add birth time
      </ButtonLink>
    </Card>
  );
}

function ChartSkeleton() {
  return (
    <LoadingRegion label="Loading your chart" className="mt-6">
      <Skeleton className="h-3 w-72 max-w-full" />
      <div className="mt-6 grid gap-6 lg:grid-cols-12">
        <Skeleton className="mx-auto aspect-square w-full max-w-[520px] rounded-card lg:col-span-7" />
        <Skeleton className="h-48 rounded-card lg:col-span-5" />
      </div>
      <div className="mt-8 space-y-2">
        {Array.from({ length: 6 }, (_, i) => (
          <Skeleton key={i} className="h-14 rounded-control" />
        ))}
      </div>
    </LoadingRegion>
  );
}

function BirthLine({ chart }: { chart: BirthChart }) {
  const v = chart.chart_data.vedic;
  const approx = isApproximate(chart);
  return (
    <p className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-caption tabular text-fg-muted">
      <span>{formatCivilDate(chart.date_of_birth)}</span>
      <span aria-hidden="true">·</span>
      <span>{chart.time_of_birth ? formatTime24(chart.time_of_birth) : "Time unknown"}</span>
      <span aria-hidden="true">·</span>
      <span>
        {chart.birth_place_name} ({formatCoords(chart.latitude, chart.longitude)})
      </span>
      {chart.timezone && (
        <>
          <span aria-hidden="true">·</span>
          <span>{chart.timezone}</span>
        </>
      )}
      {v && (
        <>
          <span aria-hidden="true">·</span>
          <span>Lahiri ayanamsa {formatDeg(v.ayanamsa_value)}</span>
        </>
      )}
      <Badge tone={approx ? "warning" : "success"} className="ml-1">
        {!chart.has_exact_time && !chart.time_of_birth ? "Time unknown" : approx ? "Approximate" : "Exact time"}
      </Badge>
    </p>
  );
}

function TransitsPanel({ data, hasLagna }: { data: TransitsResponse; hasLagna: boolean }) {
  const v = data.vedic;
  const aspects = data.western.slice(0, 8);
  return (
    <div className="space-y-6">
      {v.moon_transit_rashi && (
        <p className="text-body text-fg">
          The Moon is in <span className="font-semibold">{v.moon_transit_rashi}</span>
          {v.moon_transit_house ? `, your ${ordinal(v.moon_transit_house)} house from the natal Moon` : ""}.
          {v.sade_sati?.active && <span className="text-fg-secondary"> Sade Sati is active ({v.sade_sati.phase}).</span>}
        </p>
      )}
      {v.gochara && v.gochara.length > 0 && (
        <section aria-labelledby="gochara">
          <h3 id="gochara" className="mb-2 font-sans text-title text-fg">
            Gochara (slow planets)
          </h3>
          <p className="mb-2 text-caption text-fg-muted">Vedic, sidereal. Houses are counted from your Moon{hasLagna ? " and from your Lagna" : ""}; without a birth time there is no Lagna.</p>
          <ul className="divide-y divide-border">
            {v.gochara.map((g) => {
              const gr = findGraha(g.planet);
              return (
                <li key={g.planet} className="flex items-center gap-3 py-3">
                  <PlanetMark abbr={gr?.abbr ?? g.planet.slice(0, 2)} grahaKey={gr?.key} size="sm" />
                  <p className="min-w-0 flex-1 text-body-sm text-fg">
                    {g.planet} in {g.rashi}
                  </p>
                  <p className="text-caption tabular text-fg-secondary">
                    {[
                      g.house_from_moon ? `${ordinal(g.house_from_moon)} from Moon` : null,
                      g.house_from_lagna ? `${ordinal(g.house_from_lagna)} from Lagna` : null,
                    ]
                      .filter(Boolean)
                      .join(" · ")}
                  </p>
                </li>
              );
            })}
          </ul>
        </section>
      )}
      {aspects.length > 0 && (
        <section aria-labelledby="tr-asp">
          <h3 id="tr-asp" className="mb-2 font-sans text-title text-fg">
            Closest aspects to your natal planets
          </h3>
          <p className="mb-2 text-caption text-fg-muted">Western, tropical, tightest orb first.</p>
          <ul className="divide-y divide-border">
            {aspects.map((a) => (
              <li key={`${a.transiting}-${a.type}-${a.natal}`} className="flex flex-wrap items-center justify-between gap-2 py-3 text-body-sm">
                <span className="text-fg">
                  Transiting {a.transiting} <span className="text-fg-secondary">{a.type}</span> natal {a.natal}
                </span>
                <span className="tabular text-caption text-fg-muted">
                  orb {a.orb.toFixed(1)}° · {a.applying ? "applying" : "separating"}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

export default function ChartPage() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const charts = useCharts();
  const primary = pickPrimaryChart(charts.data);
  const chartId = params.get("chart");
  const chart = (chartId && charts.data?.find((c) => c.id === chartId)) || primary;

  const tabParam = params.get("tab") as TabKey | null;
  const tab: TabKey = tabParam && TAB_KEYS.includes(tabParam) ? tabParam : "planets";
  const format = usePrefsStore((s) => s.chartFormat);
  const setFormat = usePrefsStore((s) => s.setChartFormat);
  const [varga, setVarga] = useState<Varga>("d1");
  const [selectedHouse, setSelectedHouse] = useState<number | null>(null);
  const [sheetOpen, setSheetOpen] = useState(false);
  const [showLegend, setShowLegend] = useState(false);
  const [showAllSig, setShowAllSig] = useState(false);
  const [shareOpen, setShareOpen] = useState(false);
  // The wheel animates in once; later switches (D1/D9, North/South) swap instantly.
  const [wheelSettled, setWheelSettled] = useState(false);
  const wheelBox = useRef<HTMLDivElement>(null);
  const isDesktop = useIsDesktop();

  const setParam = (k: string, v: string | null) => {
    const next = new URLSearchParams(params);
    if (v) next.set(k, v);
    else next.delete(k);
    setParams(next, { replace: true });
  };

  const vedic = chart?.chart_data.vedic;
  const approx = chart ? isApproximate(chart) : false;
  const hasHouses = chart ? housesAvailable(chart) : true;
  const wheel = useMemo<WheelData | null>(() => {
    if (!chart) return null;
    if (varga === "d9" && vedic?.navamsa_d9) return divisionalWheel(vedic.navamsa_d9, approx);
    if (varga === "d10" && vedic?.dashamsa_d10) return divisionalWheel(vedic.dashamsa_d10, approx);
    return chartWheelData(chart);
  }, [chart, varga, vedic, approx]);
  const d1 = useMemo(() => (chart ? chartWheelData(chart) : null), [chart]);
  const signature = useMemo(() => (vedic ? coreSignature(vedic) : []), [vedic]);
  const aspects = vedic?.aspects ?? [];
  // C8 / C7 load only when their tab is open.
  const dashaQ = useDasha(chart?.id, tab === "dasha" && !!vedic);
  const transitsQ = useTransits(chart?.id, tab === "transits");

  const vargaTitle = varga === "d9" ? "D9 Navamsa" : varga === "d10" ? "D10 Dashamsa" : "D1 Rashi";

  const onSelectHouse = (h: number) => {
    setSelectedHouse((cur) => (cur === h && isDesktop ? null : h));
    if (!isDesktop) setSheetOpen(true);
  };

  return (
    <AppShell>
      <div className="mx-auto max-w-app px-4 pt-6 md:px-6 md:pt-10 lg:px-8">
        {charts.isLoading ? (
          <>
            <Skeleton className="h-10 w-64" />
            <ChartSkeleton />
          </>
        ) : charts.isError ? (
          <Card>
            <ErrorState error={charts.error} what="your chart" onRetry={() => void charts.refetch()} retrying={charts.isFetching} />
          </Card>
        ) : !chart || !wheel || !d1 ? (
          <Card variant="feature">
            <EmptyState
              icon={<Sparkles />}
              title={(charts.data?.length ?? 0) > 0 ? "Create your own chart" : "Your chart isn't cast yet"}
              body={
                (charts.data?.length ?? 0) > 0
                  ? "You have saved charts for other people, but not one of your own. Add your birth details to see yours."
                  : "Add your birth date, time and place. It takes a minute and unlocks every reading."
              }
              action={
                <ButtonLink to="/onboarding" variant="primary" size="lg">
                  Create my chart
                </ButtonLink>
              }
            />
          </Card>
        ) : (
          <>
            {/* 1 · Title row */}
            <div className="flex flex-wrap items-end justify-between gap-4">
              <div className="min-w-0">
                <h1 className="text-h1 text-fg">{chart.is_primary ? "Your chart" : `${chart.name}'s chart`}</h1>
                <BirthLine chart={chart} />
              </div>
              <div className="flex flex-wrap items-end gap-3">
                {(charts.data?.length ?? 0) > 1 && (
                  <Select
                    label="Chart"
                    hideLabel
                    value={chart.id}
                    onChange={(e) => setParam("chart", e.target.value)}
                    options={(charts.data ?? []).map((c) => ({ value: c.id, label: isSavedPerson(c) ? `${c.name} (${c.relationship_label})` : c.name }))}
                    containerClassName="w-56 max-w-full sm:w-72"
                  />
                )}
                <IconButton aria-label="Share or download chart" onClick={() => setShareOpen(true)} disabled={!hasHouses}>
                  <Share2 aria-hidden="true" />
                </IconButton>
                <Button
                  variant="ghost"
                  leadingIcon={<Sparkles aria-hidden="true" className="size-4 text-ai" />}
                  onClick={() => navigate("/chat", { state: { draft: "Explain the most important features of my chart." } })}
                >
                  Ask about this
                </Button>
              </div>
            </div>

            {/* 2 · Wheel + signature */}
            <div className="mt-6 grid gap-6 lg:grid-cols-12">
              <section aria-labelledby="wheel-title" className="lg:col-span-7">
                <h2 id="wheel-title" className="sr-only">
                  Birth chart drawing
                </h2>
{hasHouses ? (
<>
                <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
                  <Segmented<Varga>
                    label="Divisional chart"
                    value={varga}
                    onChange={(v) => {
                      setWheelSettled(true);
                      setVarga(v);
                    }}
                    options={[
                      { value: "d1", label: "D1 Rashi" },
                      ...(vedic?.navamsa_d9 ? [{ value: "d9" as const, label: "D9 Navamsa" }] : []),
                      ...(vedic?.dashamsa_d10 ? [{ value: "d10" as const, label: "D10 Dashamsa" }] : []),
                    ]}
                  />
                  <Segmented<ChartFormat>
                    label="Chart style"
                    value={format}
                    onChange={(f) => {
                      setWheelSettled(true);
                      setFormat(f);
                    }}
                    options={[
                      { value: "north", label: "North" },
                      { value: "south", label: "South" },
                    ]}
                  />
                </div>
                <div ref={wheelBox} className="mx-auto w-full max-w-[343px] md:max-w-[440px] lg:max-w-[520px]">
                  <ChartWheel
                    data={wheel}
                    format={format}
                    title={`${vargaTitle} chart`}
                    selectedHouse={selectedHouse}
                    onSelectHouse={onSelectHouse}
                    animate={!wheelSettled}
                  />
                </div>
                <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
                  <SystemTag system={vedic ? "sidereal" : "tropical"} />
                  {approx && hasHouses && (
                    <Badge tone="warning" icon={<AlertTriangle aria-hidden="true" />}>
                      Lagna approximate
                    </Badge>
                  )}
                  <Button variant="link" size="sm" aria-expanded={showLegend} onClick={() => setShowLegend((v) => !v)}>
                    {showLegend ? "Hide legend" : "Show legend"}
                  </Button>
                </div>
                {showLegend && <ChartWheelLegend className="mt-3 rounded-control bg-surface p-4" />}
                <p className="mt-2 text-caption text-fg-muted">Select a house to see what's in it. Arrow keys move between houses.</p>
</>
) : (
<NeedsBirthTime />
)}
              </section>

              <div className="space-y-4 lg:col-span-5">
                {selectedHouse && isDesktop && (
                  <Card as="section" aria-labelledby="house-detail">
                    <h2 id="house-detail" className="mb-3 font-sans text-title text-fg">
                      {ordinal(selectedHouse)} house{selectedHouse === 1 ? " · Lagna (Ascendant)" : ""}
                    </h2>
                    <HouseDetail data={wheel} house={selectedHouse} vedic={vedic} />
                  </Card>
                )}
                <ChartFacts chart={chart} hasHouses={hasHouses} />
                {signature.length > 0 && (
                  <Card variant="feature" as="section" aria-labelledby="signature">
                    <h2 id="signature" className="flex items-center gap-2 font-sans text-title text-fg">
                      <Sparkles aria-hidden="true" className="size-5 text-accent-text" />
                      Core signature
                    </h2>
                    <ul className="mt-3 space-y-3 text-body-lg text-fg">
                      {(showAllSig ? signature : signature.slice(0, 2)).map((s) => (
                        <li key={s} className="flex gap-3">
                          <span aria-hidden="true" className="mt-3 size-1.5 shrink-0 rounded-chip bg-accent" />
                          {s}
                        </li>
                      ))}
                    </ul>
                    {signature.length > 2 && (
                      <Button variant="link" size="sm" aria-expanded={showAllSig} onClick={() => setShowAllSig((v) => !v)}>
                        {showAllSig ? "Less" : "More"}
                      </Button>
                    )}
                  </Card>
                )}
              </div>
            </div>

            {/* 3 · Tabs */}
            <div className="sticky top-0 z-20 -mx-4 mt-10 bg-bg px-4 md:top-[var(--nk-header-h)] md:-mx-6 md:px-6 lg:-mx-8 lg:px-8">
              <Tabs<TabKey>
                idBase="chart"
                label="Chart details"
                value={tab}
                onChange={(t) => setParam("tab", t)}
                items={[
                  { value: "planets", label: "Planets" },
                  { value: "houses", label: "Houses" },
                  { value: "aspects", label: "Aspects", disabled: !vedic, disabledReason: "Not available for this chart" },
                  { value: "dasha", label: "Dasha", disabled: !vedic, disabledReason: "Not available for this chart" },
                  { value: "yogas", label: "Yogas", disabled: !vedic, disabledReason: "Not available for this chart" },
                  { value: "transits", label: "Transits" },
                ]}
              />
            </div>

            <div className="pt-6">
              {tab === "planets" && (
                <TabPanel idBase="chart" value="planets">
                  <h2 className="mb-1 text-h3 text-fg">Graha sthiti (planetary positions)</h2>
                  <SystemTag system={vedic ? "sidereal" : "tropical"} />
                  <div className="mt-4">
                    <PlanetTable planets={d1.planets} system={vedic ? "sidereal" : "tropical"} highlightHouse={selectedHouse} caption="Planetary positions" />
                  </div>
                </TabPanel>
              )}

              {tab === "houses" && (
                <TabPanel idBase="chart" value="houses">
                  <h2 className="mb-3 text-h3 text-fg">Bhavas (houses)</h2>
                  {!hasHouses ? (
                    <NeedsBirthTime compact />
                  ) : (
                    <>
                  {approx && (
                    <p className="mb-4 flex gap-2 rounded-control bg-info-subtle p-3 text-caption text-fg-secondary">
                      <Info aria-hidden="true" className="mt-px size-4 shrink-0 text-info" />
                      Without an exact birth time, house positions may be off. Planet signs stay accurate.
                    </p>
                  )}
                  <ul className="divide-y divide-border">
                    {Array.from({ length: 12 }, (_, i) => {
                      const h = i + 1;
                      const sign = SIGNS[(d1.lagnaIdx + i) % 12];
                      const ps = d1.planets.filter((p) => p.house === h);
                      const lord = vedic?.house_lords?.find((x) => x.house === h);
                      return (
                        <li key={h} className={`grid gap-2 py-3 sm:grid-cols-[64px_200px_1fr] sm:items-center ${selectedHouse === h ? "bg-ai-subtle" : ""}`}>
                          <p className="text-title tabular text-fg">{ordinal(h)}</p>
                          <ZodiacBadge sign={sign?.english} system={vedic ? "sidereal" : "tropical"} size="sm" />
                          <div className="min-w-0">
                            <p className="text-body-sm text-fg-secondary">{HOUSE_THEMES[h]}</p>
                            <p className="text-caption text-fg-muted">
                              {lord ? `Lord ${lord.lord} in the ${ordinal(lord.lord_in_house)}` : ""}
                              {lord && ps.length ? " · " : ""}
                              {ps.length ? `Occupied by ${ps.map((p) => p.english).join(", ")}` : lord ? "" : "Empty"}
                            </p>
                          </div>
                        </li>
                      );
                    })}
                  </ul>
                    </>
                  )}
                </TabPanel>
              )}

              {tab === "aspects" && vedic && (
                <TabPanel idBase="chart" value="aspects">
                  <h2 className="mb-1 text-h3 text-fg">Graha drishti (planetary aspects)</h2>
                  <p className="mb-4 text-body-sm text-fg-secondary">
                    Every planet aspects the 7th house from itself. Mars also aspects the 4th and 8th, Jupiter the 5th and 9th, Saturn the 3rd and 10th.
                  </p>
                  {aspects.filter((a) => a.to_house).length === 0 && (
                    <p className="text-body-sm text-fg-muted">
                      {hasHouses ? "Aspects aren't available for this chart yet. Editing and saving it recalculates it with the latest engine." : "Aspects are counted by house, so they need your birth time."}
                    </p>
                  )}
                  <ul className="divide-y divide-border">
                    {aspects
                      .filter((a) => a.to_house)
                      .slice()
                      .sort((a, b) => b.to_planets.length - a.to_planets.length)
                      .map((a) => {
                        const g = findGraha(a.from);
                        return (
                          <li key={`${a.from}-${a.to_house}`} className="flex items-start gap-3 py-3">
                            <PlanetMark abbr={g?.abbr ?? a.from.slice(0, 2)} grahaKey={g?.key} size="sm" />
                            <p className="text-body-sm text-fg">
                              {a.from} aspects the {ordinal(a.to_house ?? 0)} house
                              {a.to_planets.length > 0 ? (
                                <span className="text-fg-secondary">, falling on {a.to_planets.join(", ")}</span>
                              ) : (
                                <span className="text-fg-muted"> (no planets there)</span>
                              )}
                            </p>
                          </li>
                        );
                      })}
                  </ul>
                </TabPanel>
              )}

              {tab === "dasha" && vedic && (
                <TabPanel idBase="chart" value="dasha">
                  <h2 className="mb-3 text-h3 text-fg">Vimshottari dasha</h2>
                  {dashaQ.isLoading ? (
                    <LoadingRegion label="Loading the dasha timeline">
                      <Skeleton className="h-12 rounded-control" />
                      <div className="mt-3 space-y-2">
                        {Array.from({ length: 5 }, (_, i) => (
                          <Skeleton key={i} className="h-14 rounded-control" />
                        ))}
                      </div>
                    </LoadingRegion>
                  ) : dashaQ.isError ? (
                    <>
                      <ErrorState compact error={dashaQ.error} what="the full timeline" onRetry={() => void dashaQ.refetch()} retrying={dashaQ.isFetching} />
                      <div className="mt-4">
                        <DashaApproxNote approximate={!!vedic.dasha.approximate} dasha={vedic.dasha} />
                        <DashaTimeline dasha={vedic.dasha} />
                      </div>
                    </>
                  ) : dashaQ.data ? (
                    <>
                      <DashaApproxNote approximate={dashaQ.data.approximate || dashaQ.data.timeline.some((t) => t.approximate) || !!vedic.dasha.approximate} dasha={vedic.dasha} />
                      <DashaTimeline
                        dasha={{
                          maha_dasha: dashaQ.data.current.maha_dasha ?? vedic.dasha.maha_dasha,
                          antar_dasha: dashaQ.data.current.antar_dasha ?? vedic.dasha.antar_dasha,
                          timeline: dashaQ.data.timeline,
                        }}
                      />
                    </>
                  ) : null}
                </TabPanel>
              )}

              {tab === "yogas" && vedic && (
                <TabPanel idBase="chart" value="yogas">
                  <h2 className="mb-3 text-h3 text-fg">Yogas and doshas</h2>
                  {(vedic.yogas ?? []).filter((y) => y.present).length === 0 ? (
                    <p className="text-body-sm text-fg-secondary">No classical yogas from our list are formed in this chart.</p>
                  ) : (
                    <ul className="grid gap-3 md:grid-cols-2">
                      {(vedic.yogas ?? [])
                        .filter((y) => y.present)
                        .map((y) => {
                          const dosha = /dosha/i.test(y.name);
                          return (
                            <li key={y.name}>
                              <Card padding="sm" className="h-full">
                                <p className="flex flex-wrap items-center gap-2">
                                  {dosha ? <AlertTriangle aria-hidden="true" className="size-4 text-warning" /> : <CheckCircle2 aria-hidden="true" className="size-4 text-success" />}
                                  <span className="text-[0.9375rem] font-semibold text-fg">{y.name}</span>
                                  <Badge tone={dosha ? "warning" : "success"} className="capitalize">
                                    {y.strength}
                                  </Badge>
                                  {y.approximate && <Badge>Approximate</Badge>}
                                </p>
                                {y.description && <p className="mt-2 text-body-sm text-fg-secondary">{y.description}</p>}
                                {dosha && <p className="mt-2 text-caption text-fg-muted">What it asks of you: patience and awareness in this area. Traditional remedies exist, and many astrologers weigh it against the rest of the chart.</p>}
                              </Card>
                            </li>
                          );
                        })}
                    </ul>
                  )}
                </TabPanel>
              )}

              {tab === "transits" && (
                <TabPanel idBase="chart" value="transits">
                  <h2 className="mb-1 text-h3 text-fg">Transits today</h2>
                  <p className="mb-4 text-body-sm text-fg-secondary">Where the planets are now, measured against your chart.</p>
                  {transitsQ.isLoading ? (
                    <LoadingRegion label="Loading transits">
                      {Array.from({ length: 6 }, (_, i) => (
                        <Skeleton key={i} className="mb-2 h-12 rounded-control" />
                      ))}
                    </LoadingRegion>
                  ) : transitsQ.isError || !transitsQ.data ? (
                    <ErrorState compact error={transitsQ.error} what="transits" onRetry={() => void transitsQ.refetch()} retrying={transitsQ.isFetching} />
                  ) : (
                    <TransitsPanel data={transitsQ.data} hasLagna={hasHouses} />
                  )}
                </TabPanel>
              )}
            </div>

            <ChartShareDialog
              open={shareOpen}
              onClose={() => setShareOpen(false)}
              getSvg={() => wheelBox.current?.querySelector("svg") ?? null}
              title={`${vargaTitle} · ${chart.name}`}
              birthLine={`${formatCivilDate(chart.date_of_birth)} · ${chart.time_of_birth ? formatTime24(chart.time_of_birth) : "time unknown"} · ${chart.birth_place_name}`}
              summary={wheelSummary(wheel)}
            />

            {!isDesktop && selectedHouse && (
              <Dialog open={sheetOpen} onClose={() => setSheetOpen(false)} title={`${ordinal(selectedHouse)} house${selectedHouse === 1 ? " · Lagna" : ""}`} presentation="sheet">
                <HouseDetail data={wheel} house={selectedHouse} vedic={vedic} />
              </Dialog>
            )}
          </>
        )}
      </div>
    </AppShell>
  );
}
