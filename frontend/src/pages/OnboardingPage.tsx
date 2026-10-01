import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Controller, useForm, useWatch, type FieldPath } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { ArrowLeft, Pencil } from "lucide-react";
import { Logo } from "../components/layout/Logo";
import { Starfield } from "../components/layout/AppShell";
import { Button, ButtonLink } from "../components/ui/Button";
import { Input } from "../components/ui/Field";
import { ErrorState } from "../components/ui/EmptyState";
import { BirthDateField } from "../components/forms/BirthDateField";
import { BirthTimeField } from "../components/forms/BirthTimeField";
import { LocationAutocomplete } from "../components/forms/LocationAutocomplete";
import { useCreateChart } from "../hooks/useCharts";
import { useAuthStore } from "../store/authStore";
import { toast } from "../store/toastStore";
import { cn } from "../lib/utils";
import { dur, ease } from "../lib/motion";
import { formatCoords, formatUtcOffset } from "../lib/astro";
import {
  APPROX_LABEL,
  birthDetailsSchema,
  dateFromParts,
  emptyDate,
  emptyTime,
  hasExactTime,
  timezoneHint,
  toIsoDate,
  toTime24,
  type BirthDetails,
} from "../lib/birthForm";
import { formatTime24 } from "../lib/format";

type Step = 0 | 1 | 2 | 3; // 0 You · 1 When · 2 Where · 3 Review
const STEP_FIELDS: Record<Exclude<Step, 3>, FieldPath<BirthDetails>[]> = { 0: ["name"], 1: ["date", "time"], 2: ["place"] };
const STEP_TITLE = ["What should we call this chart?", "When were you born?", "Where were you born?", "Check your details"];
const STEP_HELP = [
  "This is how we'll label your chart.",
  "Birth time sets your Lagna (Ascendant). Check a birth certificate if you can.",
  "We use the place to find the exact sky and time zone.",
  "Every reading depends on these. Take a second look.",
];

function CastingState({ place }: { place: string }) {
  const reduce = useReducedMotion();
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setElapsed((e) => e + 1), 1000);
    return () => clearInterval(t);
  }, []);
  const city = place.split(",")[0];
  const copy = elapsed < 2 ? `Finding the sky over ${city}…` : elapsed < 4 ? "Placing nine grahas…" : "Calculating your dasha periods…";
  return (
    <div className="flex flex-col items-center py-8 text-center" aria-busy="true">
      <svg viewBox="0 0 200 200" className="size-48 text-border-strong" aria-hidden="true" fill="none" stroke="currentColor">
        <motion.path
          d="M2 2 H198 V198 H2 Z M2 2 L198 198 M198 2 L2 198 M100 2 L198 100 L100 198 L2 100 Z"
          strokeWidth={1.25}
          initial={reduce ? false : { pathLength: 0 }}
          animate={reduce ? undefined : { pathLength: [0, 1, 1] }}
          transition={{ duration: 2.4, ease: "easeInOut", repeat: Infinity }}
        />
      </svg>
      <p className="mt-6 text-title text-fg" aria-live="polite">
        {copy}
      </p>
      {elapsed >= 10 && <p className="mt-2 text-caption text-fg-muted">Still calculating — this can take up to 30 seconds on first use.</p>}
    </div>
  );
}

export default function OnboardingPage() {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const createChart = useCreateChart();
  const reduce = useReducedMotion();
  const [step, setStep] = useState<Step>(0);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const firstRender = useRef(true);

  const form = useForm<BirthDetails>({
    resolver: zodResolver(birthDetailsSchema),
    mode: "onTouched",
    defaultValues: { name: user?.name ?? "", date: emptyDate, time: emptyTime, place: null },
  });
  const { control, register, formState, trigger, getValues, setFocus, clearErrors } = form;
  const watchedDate = useWatch({ control, name: "date" });
  const birthDate = dateFromParts(watchedDate);

  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false;
      return;
    }
    headingRef.current?.focus();
  }, [step]);

  const next = async () => {
    if (step === 3) return;
    const fields = STEP_FIELDS[step];
    const ok = await trigger(fields, { shouldFocus: true });
    if (ok) setStep((s) => (s + 1) as Step);
    else if (fields[0] === "name") setFocus("name");
  };

  const submit = form.handleSubmit((data) => {
    if (!data.place) return;
    createChart.mutate(
      {
        name: data.name.trim(),
        date_of_birth: toIsoDate(data.date),
        time_of_birth: toTime24(data.time),
        has_exact_time: hasExactTime(data.time),
        birth_place_name: data.place.name,
        latitude: data.place.lat,
        longitude: data.place.lon,
        timezone: timezoneHint(data.place),
        is_primary: true,
      },
      {
        onSuccess: () => {
          toast.success("Your chart is ready");
          navigate("/dashboard", { replace: true });
        },
      },
    );
  });

  const casting = createChart.isPending;
  const v = getValues();
  const timeText = v.time.unknown
    ? `Time unknown${v.time.approx && v.time.approx !== "unknown" ? ` · ${APPROX_LABEL[v.time.approx].toLowerCase()}` : ""}`
    : formatTime24(toTime24(v.time));

  return (
    <div className="relative flex min-h-svh flex-col">
      <Starfield />
      <header className="mx-auto flex h-16 w-full max-w-app items-center justify-between gap-3 px-4 md:px-6">
        <Logo to="/dashboard" />
        <div className="flex items-center gap-3">
          <p className="text-body-sm text-fg-secondary" aria-live="polite">
            {step < 3 ? `Step ${step + 1} of 3` : "Review"}
          </p>
          <ButtonLink to="/dashboard" variant="ghost" size="sm">
            Exit
          </ButtonLink>
        </div>
      </header>
      <div className="mx-auto w-full max-w-app px-4 md:px-6" aria-hidden="true">
        <div className="mx-auto grid max-w-form grid-cols-3 gap-1.5">
          {[0, 1, 2].map((i) => (
            <span key={i} className={cn("h-1 rounded-chip", i <= step ? "bg-accent" : "bg-elevated")} />
          ))}
        </div>
      </div>

      <main id="main" className="flex flex-1 items-start justify-center px-4 pb-32 pt-6 sm:pb-10 md:pt-10">
        <div className="w-full max-w-form rounded-sheet border border-border bg-surface p-5 shadow-e2 md:p-8">
          {casting ? (
            <CastingState place={v.place?.name ?? ""} />
          ) : (
            <form
              noValidate
              onSubmit={(e) => {
                e.preventDefault();
                if (step === 3) void submit();
                else void next();
              }}
            >
              <h1 ref={headingRef} tabIndex={-1} className="text-h2 text-fg outline-none">
                {STEP_TITLE[step]}
              </h1>
              <p className="mt-2 text-body-sm text-fg-secondary">{STEP_HELP[step]}</p>

              <AnimatePresence mode="wait" initial={false}>
                <motion.div
                  key={step}
                  initial={reduce ? { opacity: 0 } : { opacity: 0, x: 16 }}
                  animate={{ opacity: 1, x: 0, transition: { duration: dur.base, ease: ease.enter } }}
                  exit={{ opacity: 0, transition: { duration: dur.fast } }}
                  className="mt-6 space-y-6"
                >
                  {step === 0 && <Input label="Name" autoComplete="name" error={formState.errors.name?.message} {...register("name")} />}
                  {step === 1 && (
                    <>
                      <Controller
                        control={control}
                        name="date"
                        render={({ field, fieldState }) => (
                          <BirthDateField value={field.value} onChange={field.onChange} onBlur={field.onBlur} error={fieldState.error?.message} />
                        )}
                      />
                      <Controller
                        control={control}
                        name="time"
                        render={({ field, fieldState }) => (
                          <BirthTimeField value={field.value} onChange={(v) => { if (v.unknown !== field.value.unknown) clearErrors("time"); field.onChange(v); }} onBlur={field.onBlur} error={fieldState.error?.message} />
                        )}
                      />
                    </>
                  )}
                  {step === 2 && (
                    <Controller
                      control={control}
                      name="place"
                      render={({ field, fieldState }) => (
                        <LocationAutocomplete value={field.value} onChange={field.onChange} onBlur={field.onBlur} error={fieldState.error?.message} onDate={birthDate} />
                      )}
                    />
                  )}
                  {step === 3 && (
                    <>
                      <dl className="divide-y divide-border rounded-card border border-border">
                        {[
                          { label: "Name", value: v.name, to: 0 as Step },
                          { label: "Date", value: birthDate?.toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short", year: "numeric" }) ?? "", to: 1 as Step },
                          { label: "Time", value: timeText, to: 1 as Step },
                          {
                            label: "Place",
                            value: v.place
                              ? `${v.place.name}${v.place.timezone ? ` (${formatUtcOffset(v.place.timezone, birthDate ?? new Date())})` : ""} · ${formatCoords(v.place.lat, v.place.lon)}`
                              : "",
                            to: 2 as Step,
                          },
                        ].map((row) => (
                          <div key={row.label} className="flex items-start gap-3 p-4">
                            <dt className="w-14 shrink-0 text-body-sm text-fg-muted">{row.label}</dt>
                            <dd className="min-w-0 flex-1 text-body text-fg tabular">{row.value}</dd>
                            <Button
                              variant="ghost"
                              size="sm"
                              leadingIcon={<Pencil aria-hidden="true" className="size-4" />}
                              aria-label={`Edit ${row.label.toLowerCase()}`}
                              onClick={() => setStep(row.to)}
                            >
                              Edit
                            </Button>
                          </div>
                        ))}
                      </dl>
                      {createChart.isError && (
                        <ErrorState compact error={createChart.error} what="your chart" onRetry={() => void submit()} />
                      )}
                    </>
                  )}
                </motion.div>
              </AnimatePresence>

              <div className="fixed inset-x-0 bottom-0 z-20 flex gap-3 border-t border-border bg-surface px-4 pb-[calc(1rem+env(safe-area-inset-bottom))] pt-3 sm:static sm:mt-8 sm:justify-end sm:border-0 sm:p-0">
                {step > 0 && (
                  <Button variant="ghost" leadingIcon={<ArrowLeft aria-hidden="true" className="size-4" />} onClick={() => setStep((s) => (s - 1) as Step)}>
                    Back
                  </Button>
                )}
                <Button type="submit" variant="primary" className="flex-1 sm:flex-none">
                  {step === 3 ? "Cast my chart" : "Next"}
                </Button>
              </div>
            </form>
          )}
        </div>
      </main>
    </div>
  );
}
