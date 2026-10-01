import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowRight, HeartHandshake, Sparkles } from "lucide-react";
import { AppShell } from "../components/layout/AppShell";
import { Card, CardHeader, CardLink } from "../components/ui/Card";
import { ButtonLink } from "../components/ui/Button";
import { Badge, Chip } from "../components/ui/Badge";
import { EmptyState, ErrorState } from "../components/ui/EmptyState";
import { LoadingRegion, Skeleton, SkeletonText } from "../components/ui/Skeleton";
import { ZodiacBadge } from "../components/astrology/ZodiacBadge";
import { DailyReadingCard } from "../components/astrology/DailyReadingCard";
import { DashaSummary } from "../components/astrology/DashaTimeline";
import { ChartWheel } from "../components/astrology/ChartWheel";
import { PanchangCard } from "../components/astrology/PanchangCard";
import { bandFor } from "../lib/compatBands";
import { useCharts, pickPrimaryChart } from "../hooks/useCharts";
import { useDailyHoroscope, usePersonalReading } from "../hooks/useHoroscope";
import { useCompatibilityReports } from "../hooks/useCompatibility";
import { useAuthStore } from "../store/authStore";
import { toApiError } from "../services/errors";
import { usePrefsStore } from "../store/prefsStore";
import { bigThree, chartWheelData, housesAvailable, isApproximate, wheelSummary } from "../lib/chartModel";
import { firstName, timeOfDayGreeting } from "../lib/format";
import { fadeUp, stagger } from "../lib/motion";
import { cn } from "../lib/utils";

const SUGGESTIONS = ["What does my current dasha mean for me?", "Is this a good month for a job change?", "What should I keep in mind in love right now?"];

function Greeting() {
  const user = useAuthStore((s) => s.user);
  const name = firstName(user?.name);
  const today = new Date().toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "long" });
  return (
    <div>
      <h1 className="text-h1 text-fg">
        {timeOfDayGreeting()}
        {name ? `, ${name}` : ""}
      </h1>
      <p className="mt-1 text-body text-fg-secondary">{today}</p>
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <LoadingRegion label="Loading your dashboard" className="mt-8 grid gap-3 md:gap-4 lg:grid-cols-12 lg:gap-6">
      <div className="grid grid-cols-[repeat(3,minmax(0,1fr))] gap-2 md:gap-4 lg:col-span-8">
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} className="h-[168px] rounded-card" />
        ))}
      </div>
      <div className="lg:col-span-8 lg:row-span-2">
        <div className="rounded-card border border-border bg-surface p-5 md:p-6">
          <Skeleton className="h-3 w-40" />
          <Skeleton className="mt-4 h-6 w-3/4" />
          <SkeletonText lines={3} className="mt-5" />
          <Skeleton className="mt-6 h-11 w-44 rounded-control" />
        </div>
      </div>
      <Skeleton className="h-44 rounded-card lg:col-span-4" />
      <Skeleton className="h-44 rounded-card lg:col-span-4" />
    </LoadingRegion>
  );
}

export default function DashboardPage() {
  const navigate = useNavigate();
  const chartFormat = usePrefsStore((s) => s.chartFormat);
  const charts = useCharts();
  const chart = pickPrimaryChart(charts.data);
  const system = useAuthStore((s) => s.user?.astrology_system) ?? "vedic";
  const sunSign = chart?.chart_data?.sun_sign?.sign;
  // R3 personal reading first; fall back to the R1 sun-sign reading when R3 isn't available (gap G-08).
  const personal = usePersonalReading(!!chart);
  // 403/409 (verify email, no chart) fall back to the general reading. A 5xx / network failure means the
  // personal reading is still being prepared: show a calm retry state instead of a generic card.
  const personalErr = personal.isError ? toApiError(personal.error) : null;
  const preparing = !!personalErr && (personalErr.network || (personalErr.status !== undefined && personalErr.status >= 500));
  const fallbackToGeneral = personal.isError && !preparing;
  const horoscope = useDailyHoroscope(chart && fallbackToGeneral ? sunSign : undefined);
  const reports = useCompatibilityReports();

  return (
    <AppShell>
      <div className="mx-auto max-w-app px-4 pt-6 md:px-6 md:pt-10 lg:px-8">
        <Greeting />

        {charts.isLoading ? (
          <DashboardSkeleton />
        ) : charts.isError ? (
          // Never show "no chart" when the request failed — that reads as lost data (pages/dashboard.md).
          <Card className="mt-8">
            <ErrorState error={charts.error} what="your chart" onRetry={() => void charts.refetch()} retrying={charts.isFetching} />
          </Card>
        ) : !chart ? (
          <Card variant="feature" className="mt-8">
            <EmptyState
              icon={<Sparkles />}
              title={(charts.data?.length ?? 0) > 0 ? "Create your own chart" : "Your chart isn't cast yet"}
              body={
                (charts.data?.length ?? 0) > 0
                  ? "You've saved other people's charts, but readings are about you. Add your own birth details to unlock them."
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
          <motion.div variants={stagger} initial="hidden" animate="show" className="mt-6 grid gap-3 md:mt-8 md:grid-cols-2 md:gap-4 lg:grid-cols-12 lg:items-start lg:gap-6 [&_*]:min-w-0">
            <div className="contents lg:col-span-8 lg:flex lg:flex-col lg:gap-6">
            {/* 2 · Big Three */}
            <motion.section variants={fadeUp} aria-labelledby="big3" className="lg:order-none order-1 md:col-span-2">
              <h2 id="big3" className="sr-only">
                Your Big Three
              </h2>
              <ul className="grid grid-cols-[repeat(3,minmax(0,1fr))] gap-2 md:gap-4">
                {bigThree(chart, system).map((b) => (
                  <li key={b.role} className="min-w-0">
                    <Link
                      to={b.role === "Lagna" && !housesAvailable(chart) ? "/profile#charts" : `/chart?tab=${b.role === "Lagna" ? "houses" : "planets"}`}
                      className={cn("focus-ring flex h-full min-w-0 flex-col rounded-card border p-3 transition-colors md:p-4", b.role === "Lagna" ? "border-accent bg-accent-subtle" : "border-border bg-surface hover:border-border-strong")}
                    >
                      <ZodiacBadge
                        variant="role"
                        role={b.role === "Lagna" ? "Lagna" : b.role}
                        sign={b.sign}
                        system={b.system}
                        extra={b.role === "Lagna" && !housesAvailable(chart) ? undefined : b.extra}
                        accent={b.role === "Lagna"}
                        size="md"
                      />
                      {b.role === "Lagna" && !housesAvailable(chart) ? (
                        <Badge tone="warning" className="mt-2">
                          Add birth time
                        </Badge>
                      ) : (
                        b.role === "Lagna" &&
                        isApproximate(chart) && (
                          <Badge tone="warning" className="mt-2">
                            Approximate
                          </Badge>
                        )
                      )}
                    </Link>
                  </li>
                ))}
              </ul>
            </motion.section>

            {/* 3 · Today's reading (hero) */}
            <motion.div variants={fadeUp} className="lg:order-none order-2 md:col-span-2">
              <DailyReadingCard
                personal={personal.data}
                reading={horoscope.data}
                preparing={preparing ? { error: personal.error, retryAfter: personalErr?.retryAfter } : undefined}
                isLoading={personal.isLoading || (fallbackToGeneral && !!sunSign && horoscope.isPending)}
                error={fallbackToGeneral ? horoscope.error : undefined}
                onRetry={() => void (fallbackToGeneral ? horoscope.refetch() : personal.refetch())}
                retrying={personal.isFetching || horoscope.isFetching}
                sign={sunSign}
              />
            </motion.div>

              <div className="contents lg:grid lg:grid-cols-2 lg:gap-6">
            {/* 6 · Your chart */}
            <motion.div variants={fadeUp} className="lg:order-none order-6">
              <CardLink to="/chart" aria-label="Open your full chart" className="flex h-full gap-4">
                {housesAvailable(chart) && (
                  <div className="w-[120px] shrink-0 sm:w-[160px]">
                    <ChartWheel data={chartWheelData(chart)} format={chartFormat} variant="thumbnail" title={`${chart.name}'s chart (thumbnail)`} />
                  </div>
                )}
                <div className="min-w-0">
                  <p className="text-caption font-medium text-fg-muted">Your chart</p>
                  <p className="mt-1 text-title text-fg">{chart.name}</p>
                  <p className="mt-1 line-clamp-3 text-body-sm text-fg-secondary">{wheelSummary(chartWheelData(chart))}</p>
                  <p className="mt-2 flex items-center gap-1 text-body-sm font-semibold text-ai">
                    Open full chart <ArrowRight aria-hidden="true" className="size-4" />
                  </p>
                </div>
              </CardLink>
            </motion.div>

            {/* 7 · Compatibility */}
            <motion.div variants={fadeUp} className="lg:order-none order-7">
              <Card as="section" aria-labelledby="compat" className="h-full">
                <CardHeader overline="Match" title="Compatibility" titleId="compat" />
                {reports.isLoading ? (
                  <div aria-busy="true" className="space-y-2">
                    <Skeleton className="h-12 rounded-control" />
                    <Skeleton className="h-12 rounded-control" />
                  </div>
                ) : reports.isError ? (
                  <ErrorState compact error={reports.error} what="your reports" onRetry={() => void reports.refetch()} />
                ) : reports.data && reports.data.length > 0 ? (
                  <ul className="divide-y divide-border">
                    {reports.data.slice(0, 2).map((r) => {
                      const band = bandFor(r.overall_score);
                      return (
                        <li key={r.id} className="flex items-center justify-between gap-3 py-3">
                          <span className="min-w-0">
                            <span className="block truncate text-body-sm font-semibold text-fg">You & {r.partner_name ?? "partner"}</span>
                            <span className="block text-caption capitalize text-fg-muted">{r.relationship_type}</span>
                          </span>
                          <span className={`flex shrink-0 items-center gap-1.5 text-body-sm tabular [&_svg]:size-4 ${band.text}`}>
                            {band.icon}
                            {Number(r.overall_score).toFixed(1)} · {band.label}
                          </span>
                        </li>
                      );
                    })}
                  </ul>
                ) : (
                  <p className="flex items-start gap-2 text-body-sm text-fg-secondary">
                    <HeartHandshake aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-ai" />
                    See how your chart meets a partner's, friend's or family member's.
                  </p>
                )}
                <ButtonLink to="/compatibility" variant="link" size="sm" className="mt-2" trailingIcon={<ArrowRight aria-hidden="true" className="size-4" />}>
                  Check compatibility
                </ButtonLink>
              </Card>
            </motion.div>
              </div>
            </div>
            <div className="contents lg:col-span-4 lg:flex lg:flex-col lg:gap-6">
            {/* 4 · Current period */}
            {system === "vedic" && chart.chart_data.vedic?.dasha?.maha_dasha?.current && (
              <motion.div variants={fadeUp} className="lg:order-none order-3">
                <Card as="section" aria-labelledby="period" className="h-full">
                  <CardHeader overline="Vimshottari dasha" title="Current period" titleId="period" />
                  <DashaSummary dasha={chart.chart_data.vedic.dasha} />
                  <ButtonLink to="/chart?tab=dasha" variant="link" size="sm" trailingIcon={<ArrowRight aria-hidden="true" className="size-4" />}>
                    View timeline
                  </ButtonLink>
                </Card>
              </motion.div>
            )}

            {/* Panchang (C9) */}
            {system === "vedic" && (
              <motion.div variants={fadeUp} className="lg:order-none order-4">
                <PanchangCard lat={chart.latitude} lon={chart.longitude} />
              </motion.div>
            )}

            {/* 5 · Ask */}
            <motion.div variants={fadeUp} className="lg:order-none order-5 md:col-span-2 lg:col-span-1">
              <Card as="section" aria-labelledby="ask" className="h-full">
                <CardHeader overline="Ask Nakshion" title="Questions about your chart" titleId="ask" />
                <ul className="scroll-fade-x -mx-5 flex gap-2 px-5 md:mx-0 md:flex-col md:overflow-visible md:px-0 md:[mask-image:none]">
                  {SUGGESTIONS.map((s) => (
                    <li key={s} className="w-[260px] shrink-0 md:w-auto">
                      <Chip kind="suggestion" className="w-full justify-start py-2" onClick={() => navigate("/chat", { state: { send: s } })}>
                        {s}
                      </Chip>
                    </li>
                  ))}
                </ul>
                <ButtonLink to="/chat" variant="link" size="sm" className="mt-2" trailingIcon={<ArrowRight aria-hidden="true" className="size-4" />}>
                  Open chat
                </ButtonLink>
              </Card>
            </motion.div>

            </div>
          </motion.div>
        )}
      </div>
    </AppShell>
  );
}
