import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Controller, useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { motion, useReducedMotion } from "framer-motion";
import { AlertTriangle, ArrowLeft, Trash2, CheckCircle2, ChevronRight, HeartHandshake, Sparkles } from "lucide-react";
import { AppShell } from "../components/layout/AppShell";
import { Card } from "../components/ui/Card";
import { Button, ButtonLink } from "../components/ui/Button";
import { Badge, Chip } from "../components/ui/Badge";
import { Input } from "../components/ui/Field";
import { Select } from "../components/ui/Select";
import { Avatar } from "../components/ui/Avatar";
import { EmptyState, ErrorState } from "../components/ui/EmptyState";
import { LoadingRegion, Skeleton } from "../components/ui/Skeleton";
import { BirthDateField } from "../components/forms/BirthDateField";
import { BirthTimeField } from "../components/forms/BirthTimeField";
import { LocationAutocomplete } from "../components/forms/LocationAutocomplete";
import { CategoryBar, CompatibilityMeter } from "../components/astrology/CompatibilityMeter";
import { AshtakootaCard, ScoreBreakdownCard } from "../components/astrology/CompatibilityDetails";
import { bandFor } from "../lib/compatBands";
import { ZodiacBadge } from "../components/astrology/ZodiacBadge";
import { useCharts, ownCharts, pickPrimaryChart } from "../hooks/useCharts";
import { useCalculateCompatibility, useCompatibilityReport, useCompatibilityReports, useDeleteReport } from "../hooks/useCompatibility";
import { Dialog } from "../components/ui/Dialog";
import { toast } from "../store/toastStore";
import { toApiError } from "../services/errors";
import { useAuthStore } from "../store/authStore";
import { bigThree } from "../lib/chartModel";
import { formatRelativeTime } from "../lib/format";
import {
  dateFromParts,
  dateSchema,
  emptyDate,
  emptyTime,
  hasExactTime,
  nameSchema,
  placeSchema,
  timeSchema,
  timezoneHint,
  toIsoDate,
  toTime24,
} from "../lib/birthForm";
import type { CompatibilityReport, RelationshipType } from "../types";

const RELATIONSHIPS: Array<{ value: RelationshipType; label: string }> = [
  { value: "romantic", label: "Romantic" },
  { value: "friend", label: "Friendship" },
  { value: "family", label: "Family" },
  { value: "coworker", label: "Work" },
];

const CATEGORY_ORDER: Array<{ key: string; label: string }> = [
  { key: "emotional", label: "Emotional" },
  { key: "communication", label: "Communication" },
  { key: "romance", label: "Romance and warmth" },
  { key: "passion", label: "Passion and drive" },
  { key: "long-term", label: "Long-term" },
];

const schema = z.object({
  chartId: z.string().min(1, "Choose your chart."),
  relationship: z.enum(["romantic", "friend", "family", "coworker"]),
  name: nameSchema,
  date: dateSchema,
  time: timeSchema,
  place: placeSchema,
});
type FormValues = z.infer<typeof schema>;

function verdict(score: number): string {
  const b = bandFor(score).label;
  if (b === "Exceptional") return "Your charts support each other unusually well. Keep tending what already works.";
  if (b === "Harmonious") return "There is a lot of natural ease here, with a few areas that ask for care.";
  if (b === "Workable") return "Real strengths sit beside real differences. Understanding them is half the work.";
  return "Every pairing has work; here is where yours lies, and what tends to help.";
}

function Calculating({ you, them }: { you: string; them: string }) {
  const reduce = useReducedMotion();
  const [i, setI] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setI((x) => Math.min(x + 1, 2)), 2000);
    return () => clearInterval(t);
  }, []);
  const copy = ["Comparing Moon signs…", "Checking Mars and Venus…", "Weighing long-term ties…"][i];
  return (
    <Card className="flex flex-col items-center py-12 text-center" aria-busy="true">
      <div className="flex items-center gap-4">
        <motion.span initial={reduce ? false : { x: -24 }} animate={{ x: 0 }} transition={{ type: "spring", stiffness: 180, damping: 24 }}>
          <Avatar name={you} size="lg" />
        </motion.span>
        <HeartHandshake aria-hidden="true" className="size-6 text-ai" />
        <motion.span initial={reduce ? false : { x: 24 }} animate={{ x: 0 }} transition={{ type: "spring", stiffness: 180, damping: 24 }}>
          <Avatar name={them} size="lg" />
        </motion.span>
      </div>
      <p className="mt-6 text-title text-fg" aria-live="polite">
        {copy}
      </p>
      <p className="mt-1 text-caption text-fg-muted">Step {i + 1} of 3</p>
      <div role="progressbar" aria-label="Comparing charts" aria-valuemin={0} aria-valuemax={3} aria-valuenow={i + 1} className="mt-4 flex w-48 gap-1.5">
        {[0, 1, 2].map((n) => (
          <span key={n} className={n <= i ? "h-1 flex-1 rounded-chip bg-accent" : "h-1 flex-1 rounded-chip bg-elevated"} />
        ))}
      </div>
    </Card>
  );
}

function Report({ report, youName, onBack }: { report: CompatibilityReport; youName: string; onBack: () => void }) {
  const navigate = useNavigate();
  const data = report.compatibility_data;
  const cats = data.categories ?? {};
  const ordered = [
    ...CATEGORY_ORDER.filter((c) => cats[c.key]),
    ...Object.keys(cats)
      .filter((k) => !CATEGORY_ORDER.some((c) => c.key === k))
      .map((k) => ({ key: k, label: k.replace(/-/g, " ").replace(/^./, (c) => c.toUpperCase()) })),
  ];
  const partner = report.partner_name ?? "Partner";
  const del = useDeleteReport();
  const [confirming, setConfirming] = useState(false);
  const [allAspects, setAllAspects] = useState(false);
  const rel = RELATIONSHIPS.find((r) => r.value === report.relationship_type)?.label ?? report.relationship_type;

  return (
    <div className="space-y-6">
      <Button variant="ghost" size="sm" leadingIcon={<ArrowLeft aria-hidden="true" className="size-4" />} onClick={onBack}>
        New comparison
      </Button>
      <header className="flex flex-wrap items-center gap-3">
        <Avatar name={youName} size="md" decorative />
        <HeartHandshake aria-hidden="true" className="size-6 text-ai" />
        <Avatar name={partner} size="md" decorative />
        <h1 className="text-h2 text-fg">
          You & {partner}
        </h1>
        <Badge tone="ai">{rel}</Badge>
        {data.approximate && <Badge tone="warning">Birth time approximate</Badge>}
      </header>

      <div className="grid gap-6 lg:grid-cols-12">
        <div className="lg:col-span-4">
          <Card variant="feature" className="flex flex-col items-center text-center lg:sticky lg:top-24">
            <CompatibilityMeter score={report.overall_score} />
            {data.score_breakdown?.overall_range && (
              <p className="mt-2 text-caption tabular text-fg-secondary">
                Range {data.score_breakdown.overall_range[0].toFixed(1)}–{data.score_breakdown.overall_range[1].toFixed(1)} until a birth time is added
              </p>
            )}
            <p className="mt-3 text-body text-fg-secondary">{data.summary ?? verdict(report.overall_score)}</p>
          </Card>
        </div>
        <div className="space-y-6 lg:col-span-8">
          <Card as="section" aria-labelledby="cats">
            <h2 id="cats" className="mb-4 font-sans text-title text-fg">
              Where you meet
            </h2>
            <ul className="space-y-5">
              {ordered.map((c) => (
                <li key={c.key}>
                  <CategoryBar label={c.label} score={cats[c.key].score} summary={cats[c.key].summary} />
                </li>
              ))}
            </ul>
          </Card>

          <ScoreBreakdownCard breakdown={data.score_breakdown} />
          <AshtakootaCard data={data.ashtakoota} />

          <div className="grid gap-4 md:grid-cols-2">
            <Card as="section" aria-labelledby="str">
              <h2 id="str" className="mb-3 flex items-center gap-2 font-sans text-title text-fg">
                <CheckCircle2 aria-hidden="true" className="size-5 text-success" /> Strengths
              </h2>
              <ul className="space-y-2 text-body-sm text-fg-secondary">
                {(data.strengths ?? []).map((s) => (
                  <li key={s}>{s}</li>
                ))}
              </ul>
            </Card>
            <Card as="section" aria-labelledby="chal">
              <h2 id="chal" className="mb-3 flex items-center gap-2 font-sans text-title text-fg">
                <AlertTriangle aria-hidden="true" className="size-5 text-warning" /> Needs care
              </h2>
              <ul className="space-y-2 text-body-sm text-fg-secondary">
                {(data.challenges ?? []).map((s) => (
                  <li key={s}>{s}</li>
                ))}
              </ul>
            </Card>
          </div>

          {data.synastry_aspects?.length > 0 && (
            <Card as="section" aria-labelledby="asp">
              <h2 id="asp" className="mb-1 font-sans text-title text-fg">
                Key connections
              </h2>
              <p className="mb-3 text-caption text-fg-muted">Western synastry (tropical zodiac): how your planets meet theirs. The three strongest first.</p>
              <ul className="divide-y divide-border">
                {(allAspects ? data.synastry_aspects : data.synastry_aspects.slice(0, 3)).map((a) => (
                  <li key={`${a.planet1}-${a.aspect}-${a.planet2}`}>
                    <details className="group py-3">
                      <summary className="focus-ring flex min-h-11 cursor-pointer list-none items-center justify-between gap-3 rounded-[4px]">
                        <span className="text-body-sm text-fg">
                          Your {a.planet1} <span className="text-fg-secondary">{a.aspect}</span> their {a.planet2}
                          <span className="ml-2 text-caption tabular text-fg-muted">orb {a.orb.toFixed(1)}°</span>
                        </span>
                        <ChevronRight aria-hidden="true" className="size-4 text-fg-muted transition-transform group-open:rotate-90" />
                      </summary>
                      <p className="pt-1 text-body-sm text-fg-secondary">{a.interpretation}</p>
                    </details>
                  </li>
                ))}
              </ul>
              {data.synastry_aspects.length > 3 && (
                <Button variant="link" size="sm" aria-expanded={allAspects} onClick={() => setAllAspects((v) => !v)}>
                  {allAspects ? "Show fewer" : `Show all ${data.synastry_aspects.length}`}
                </Button>
              )}
            </Card>
          )}

          <div className="flex flex-wrap gap-3">
            <Button
              variant="ai"
              leadingIcon={<Sparkles aria-hidden="true" className="size-4" />}
              onClick={() =>
                navigate("/chat", {
                  state: { draft: `Tell me more about my ${report.relationship_type} compatibility with ${partner}. Our overall score is ${report.overall_score}/10.` },
                })
              }
            >
              Ask about us
            </Button>
          </div>
          <p className="text-caption text-fg-muted">Compatibility describes tendencies, not a verdict on whether a relationship will work.</p>
          <Button variant="ghost" size="sm" className="text-danger" leadingIcon={<Trash2 aria-hidden="true" className="size-4" />} onClick={() => setConfirming(true)}>
            Delete this report
          </Button>
          <Dialog
            open={confirming}
            onClose={() => setConfirming(false)}
            title="Delete this report?"
            description={`Your comparison with ${partner} will be removed. ${partner}'s chart stays in your list.`}
            presentation="dialog"
            footer={
              <>
                <Button variant="secondary" onClick={() => setConfirming(false)} autoFocus>
                  Cancel
                </Button>
                <Button
                  variant="danger"
                  loading={del.isPending}
                  onClick={() =>
                    del.mutate(report.id, {
                      onSuccess: () => {
                        setConfirming(false);
                        toast.success("Report deleted");
                        onBack();
                      },
                      onError: (err) => toast.error("Couldn't delete the report", toApiError(err).detail),
                    })
                  }
                >
                  Delete report
                </Button>
              </>
            }
          />
        </div>
      </div>
    </div>
  );
}

export default function CompatibilityPage() {
  const user = useAuthStore((s) => s.user);
  const [params, setParams] = useSearchParams();
  const reportId = params.get("report");
  const charts = useCharts();
  const mine = ownCharts(charts.data);
  const primary = pickPrimaryChart(charts.data);
  const reports = useCompatibilityReports();
  const opened = useCompatibilityReport(reportId);
  const calc = useCalculateCompatibility();

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    mode: "onTouched",
    defaultValues: { chartId: "", relationship: "romantic", name: "", date: emptyDate, time: emptyTime, place: null },
  });
  const { control, register, handleSubmit, formState, setValue, getValues, clearErrors } = form;
  const chartId = useWatch({ control, name: "chartId" });
  const relationship = useWatch({ control, name: "relationship" });
  const birthDate = dateFromParts(useWatch({ control, name: "date" }));

  useEffect(() => {
    if (!getValues("chartId") && primary) setValue("chartId", primary.id);
  }, [primary, getValues, setValue]);

  const selectedChart = mine.find((c) => c.id === chartId) ?? primary;

  const onSubmit = handleSubmit((v) => {
    if (!v.place) return;
    calc.mutate(
      {
        chart1_id: v.chartId,
        partner_name: v.name.trim(),
        partner_date_of_birth: toIsoDate(v.date),
        partner_time_of_birth: toTime24(v.time),
        partner_has_exact_time: hasExactTime(v.time),
        partner_birth_place_name: v.place.name,
        partner_latitude: v.place.lat,
        partner_longitude: v.place.lon,
        partner_timezone: timezoneHint(v.place),
        relationship_type: v.relationship,
      },
      { onSuccess: (r) => setParams({ report: r.id }) },
    );
  });

  const youName = selectedChart?.name ?? user?.name ?? "You";
  const report = reportId ? opened.data : undefined;

  return (
    <AppShell>
      <div className="mx-auto max-w-app px-4 pt-6 md:px-6 md:pt-10 lg:px-8">
        {reportId ? (
          opened.isLoading ? (
            <LoadingRegion label="Loading the report" className="grid gap-6 lg:grid-cols-12">
              <Skeleton className="mx-auto size-[200px] rounded-chip lg:col-span-4" />
              <div className="space-y-4 lg:col-span-8">
                {Array.from({ length: 5 }, (_, i) => (
                  <Skeleton key={i} className="h-10 rounded-control" />
                ))}
              </div>
            </LoadingRegion>
          ) : opened.isError || !report ? (
            <Card>
              <ErrorState error={opened.error} what="this report" onRetry={() => void opened.refetch()} notFoundAction={{ label: "Back to compatibility", onClick: () => setParams({}) }} />
              <div className="flex justify-center pb-6">
                <Button variant="ghost" onClick={() => setParams({})}>
                  Back to compatibility
                </Button>
              </div>
            </Card>
          ) : (
            <Report report={report} youName={youName} onBack={() => setParams({})} />
          )
        ) : calc.isPending ? (
          <div className="mx-auto max-w-chat">
            <Calculating you={youName} them={getValues("name")} />
          </div>
        ) : (
          <>
            <h1 className="text-h1 text-fg">Compatibility</h1>
            <p className="mt-1 text-body text-fg-secondary">How do your charts meet, and what deserves care?</p>

            {reports.data && reports.data.length > 0 && (
              <section aria-labelledby="saved" className="mt-6">
                <h2 id="saved" className="mb-2 font-sans text-body-sm font-semibold text-fg-secondary">
                  Saved reports
                </h2>
                <ul className="divide-y divide-border rounded-card border border-border bg-surface">
                  {reports.data.slice(0, 5).map((r) => {
                    const b = bandFor(r.overall_score);
                    return (
                      <li key={r.id}>
                        <button
                          type="button"
                          onClick={() => setParams({ report: r.id })}
                          className="focus-ring flex min-h-14 w-full cursor-pointer items-center gap-3 rounded-card px-4 py-2 text-left hover:bg-elevated"
                        >
                          <Avatar name={r.partner_name} size="sm" decorative />
                          <span className="min-w-0 flex-1">
                            <span className="block truncate text-body-sm font-semibold text-fg">You & {r.partner_name ?? "partner"}</span>
                            <span className="block text-caption text-fg-muted">
                              <span className="capitalize">{r.relationship_type}</span> · {formatRelativeTime(r.created_at)}
                            </span>
                          </span>
                          <span className={`flex items-center gap-1 text-body-sm tabular [&_svg]:size-4 ${b.text}`}>
                            {b.icon}
                            {Number(r.overall_score).toFixed(1)}
                          </span>
                          <ChevronRight aria-hidden="true" className="size-4 text-fg-muted" />
                        </button>
                      </li>
                    );
                  })}
                </ul>
              </section>
            )}
            {reports.isError && (
              <ErrorState compact className="mt-6" error={reports.error} what="your saved reports" onRetry={() => void reports.refetch()} />
            )}

            {charts.isLoading ? (
              <LoadingRegion label="Loading your charts" className="mt-8 grid gap-4 lg:grid-cols-2">
                <Skeleton className="h-48 rounded-card" />
                <Skeleton className="h-96 rounded-card" />
              </LoadingRegion>
            ) : charts.isError ? (
              <Card className="mt-8">
                <ErrorState error={charts.error} what="your charts" onRetry={() => void charts.refetch()} />
              </Card>
            ) : !primary ? (
              <Card className="mt-8">
                <EmptyState
                  icon={<HeartHandshake />}
                  title="Cast your own chart first"
                  body="Compatibility compares two charts, so we need yours before adding someone else's."
                  action={
                    <ButtonLink to="/onboarding" variant="primary">
                      Create my chart
                    </ButtonLink>
                  }
                />
              </Card>
            ) : (
              <form noValidate onSubmit={onSubmit} className="mt-8 space-y-6">
                <fieldset className="min-w-0">
                  <legend className="mb-2 text-body-sm font-medium text-fg-secondary">Relationship</legend>
                  <div role="radiogroup" aria-label="Relationship" className="scroll-fade-x -mx-1 flex gap-2 px-1 py-1">
                    {RELATIONSHIPS.map((r) => (
                      <Chip key={r.value} selected={relationship === r.value} onClick={() => setValue("relationship", r.value)}>
                        {r.label}
                      </Chip>
                    ))}
                  </div>
                </fieldset>

                <div className="grid items-start gap-4 lg:grid-cols-[1fr_auto_1fr]">
                  <Card as="section" aria-labelledby="you-h">
                    <h2 id="you-h" className="mb-4 font-sans text-title text-fg">
                      You
                    </h2>
                    {mine.length > 1 && (
                      <Select label="Your chart" options={mine.map((c) => ({ value: c.id, label: c.name }))} {...register("chartId")} containerClassName="mb-4" />
                    )}
                    {selectedChart && (
                      <ul className="grid grid-cols-[repeat(3,minmax(0,1fr))] gap-2">
                        {bigThree(selectedChart, user?.astrology_system ?? "vedic").map((b) => (
                          <li key={b.role} className="min-w-0">
                            <ZodiacBadge variant="role" role={b.role} sign={b.sign} system={b.system} size="sm" accent={b.role === "Lagna"} />
                          </li>
                        ))}
                      </ul>
                    )}
                  </Card>
                  <div aria-hidden="true" className="flex justify-center lg:pt-16">
                    <span className="flex size-12 items-center justify-center rounded-chip bg-ai-subtle text-ai">
                      <HeartHandshake className="size-6" />
                    </span>
                  </div>
                  <Card as="section" aria-labelledby="them-h" className="space-y-6">
                    <h2 id="them-h" className="font-sans text-title text-fg">
                      Them
                    </h2>
                    <Input label="Their name" autoComplete="off" error={formState.errors.name?.message} {...register("name")} />
                    <Controller
                      control={control}
                      name="date"
                      render={({ field, fieldState }) => (
                        <BirthDateField legend="Their date of birth" value={field.value} onChange={field.onChange} onBlur={field.onBlur} error={fieldState.error?.message} />
                      )}
                    />
                    <Controller
                      control={control}
                      name="time"
                      render={({ field, fieldState }) => (
                        <BirthTimeField legend="Their time of birth" whose="their" value={field.value} onChange={(v) => { if (v.unknown !== field.value.unknown) clearErrors("time"); field.onChange(v); }} onBlur={field.onBlur} error={fieldState.error?.message} />
                      )}
                    />
                    <Controller
                      control={control}
                      name="place"
                      render={({ field, fieldState }) => (
                        <LocationAutocomplete label="Their place of birth" value={field.value} onChange={field.onChange} onBlur={field.onBlur} error={fieldState.error?.message} onDate={birthDate} />
                      )}
                    />
                  </Card>
                </div>

                {calc.isError && <ErrorState compact error={calc.error} what="the comparison" onRetry={() => void onSubmit()} />}

                <div className="flex justify-center">
                  <Button type="submit" variant="primary" size="lg" className="w-full sm:w-auto">
                    See our compatibility
                  </Button>
                </div>
              </form>
            )}
          </>
        )}
      </div>
    </AppShell>
  );
}
