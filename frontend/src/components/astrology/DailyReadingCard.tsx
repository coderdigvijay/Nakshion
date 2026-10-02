import { useEffect, useId, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion, useReducedMotion } from "framer-motion";
import { AlertTriangle, Briefcase, Clock, Coins, Heart, Leaf, MoonStar, Sparkles } from "lucide-react";
import type { DailyHoroscope, PersonalReading } from "../../types";
import { findSign } from "../../lib/astro";
import { formatCivilDate, formatClock, formatDateRangesInText } from "../../lib/format";
import { Card } from "../ui/Card";
import { Button } from "../ui/Button";
import { Skeleton, SkeletonText, LoadingRegion } from "../ui/Skeleton";
import { WakingRetry } from "../ui/EmptyState";
import { ErrorState } from "../ui/EmptyState";
import { Badge } from "../ui/Badge";

// COMPONENTS.md → DailyReadingCard (feature card, dashboard hero).
// MVP data is the R1 sun-sign reading (gap G-08). Focus meters and timing strip need R3 scores
// and Panchang; they are omitted rather than faked.

function moonSignFromTransit(t: Record<string, unknown> | undefined): string | undefined {
  const moon = t?.moon;
  if (typeof moon === "object" && moon !== null && typeof (moon as { sign?: unknown }).sign === "string") {
    return (moon as { sign: string }).sign;
  }
  return undefined;
}

function FocusMeter({ label, icon, score }: { label: string; icon: React.ReactNode; score: number }) {
  const v = Math.max(0, Math.min(5, Math.round(score)));
  return (
    <div role="meter" aria-label={label} aria-valuemin={0} aria-valuemax={5} aria-valuenow={v} aria-valuetext={`${v} out of 5`}>
      <p className="flex items-center gap-1.5 text-body-sm text-fg-secondary [&_svg]:size-4">
        {icon}
        {label}
      </p>
      <div className="mt-1.5 flex items-center gap-2">
        <span aria-hidden="true" className="flex gap-1">
          {Array.from({ length: 5 }, (_, i) => (
            <span key={i} className={i < v ? "h-1.5 w-4 rounded-chip bg-accent" : "h-1.5 w-4 rounded-chip bg-elevated"} />
          ))}
        </span>
        <span className="text-caption tabular text-fg-muted">{v}/5</span>
      </div>
    </div>
  );
}

function windowText(w: { start: string; end: string }): string {
  const a = formatClock(w.start);
  const b = formatClock(w.end);
  return a && b ? `${a} – ${b}` : `${w.start} – ${w.end}`;
}

function PersonalBody({ r }: { r: PersonalReading }) {
  const [expanded, setExpanded] = useState(false);
  const id = useId();
  const areas = [
    { label: "Love", icon: <Heart aria-hidden="true" />, a: r.areas.love },
    { label: "Career", icon: <Briefcase aria-hidden="true" />, a: r.areas.career },
    { label: "Wellbeing", icon: <Leaf aria-hidden="true" />, a: r.areas.wellness },
    { label: "Money", icon: <Coins aria-hidden="true" />, a: r.areas.money },
  ];
  return (
    <>
      <h2 className="mt-3 text-h3 text-fg">{r.headline || "Your day"}</h2>
      <div id={id} className="mt-3">
        <p className={expanded ? "text-body-lg text-fg" : "line-clamp-3 text-body-lg text-fg"}>{r.overview}</p>
        {expanded && (
          <dl className="mt-4 space-y-3">
            {areas.filter((x) => x.a.text).map((x) => (
              <div key={x.label}>
                <dt className="text-body-sm font-semibold text-fg">{x.label}</dt>
                <dd className="mt-1 text-body text-fg-secondary">{x.a.text}</dd>
              </div>
            ))}
            {r.affirmation && <p className="text-body text-fg-secondary">{r.affirmation}</p>}
          </dl>
        )}
        <Button variant="link" size="sm" className="mt-1" aria-expanded={expanded} aria-controls={id} onClick={() => setExpanded((v) => !v)}>
          {expanded ? "Show less" : "Read full reading"}
        </Button>
      </div>
      <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
        {areas.map((x) => (
          <FocusMeter key={x.label} label={x.label} icon={x.icon} score={x.a.score} />
        ))}
      </div>
      {(r.timing.best_window || r.timing.rahu_kaal) && (
        <div className="mt-4 space-y-1.5 rounded-control bg-elevated p-3 text-caption tabular">
          {r.timing.best_window && (
            <p className="flex items-center gap-2 text-success">
              <Clock aria-hidden="true" className="size-4 shrink-0" />
              <span>Good window {windowText(r.timing.best_window)}</span>
            </p>
          )}
          {r.timing.rahu_kaal && (
            <p className="flex items-center gap-2 text-warning">
              <AlertTriangle aria-hidden="true" className="size-4 shrink-0" />
              <span>Rahu Kaal {windowText(r.timing.rahu_kaal)}</span>
            </p>
          )}
        </div>
      )}
      {r.key_factors.length > 0 && (
        <p className="mt-3 flex min-w-0 max-w-full flex-wrap items-center gap-2">
          <span className="text-caption text-fg-muted">Based on</span>
          {r.key_factors.slice(0, 4).map((f) => (
            <Badge key={f.factor_id} className="max-w-full whitespace-normal break-words text-left [overflow-wrap:anywhere]">{formatDateRangesInText(f.label)}</Badge>
          ))}
        </p>
      )}
      {(r.lucky.color || r.lucky.number) && (
        <p className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-body-sm text-fg-secondary">
          {r.lucky.color && <span>Lucky colour: <span className="font-medium text-fg">{r.lucky.color}</span></span>}
          {r.lucky.number && <span>Lucky number: <span className="font-medium tabular text-fg">{r.lucky.number}</span></span>}
          <span className="text-caption text-fg-muted">(just for fun)</span>
        </p>
      )}
    </>
  );
}

const READING_STAGES = ["Reading your sky…", "Placing the planets against your chart…", "Writing your reading…"];

/** Staged copy for the long first load of a personal reading, so the wait reads as intentional. */
function ReadingProgress() {
  const [stage, setStage] = useState(0);
  useEffect(() => {
    const a = setTimeout(() => setStage(1), 3500);
    const b = setTimeout(() => setStage(2), 8000);
    return () => {
      clearTimeout(a);
      clearTimeout(b);
    };
  }, []);
  return (
    <p className="mb-4 flex items-center gap-2 text-body-sm text-fg-secondary" aria-live="polite">
      <MoonStar aria-hidden="true" className="size-4 text-ai" />
      {READING_STAGES[stage]}
    </p>
  );
}

export interface DailyReadingCardProps {
  /** Set when the personal reading failed with a 5xx/network error: show a calm "being prepared" retry. */
  preparing?: { error: unknown; retryAfter?: number };
  /** R3 personal reading; preferred when present. */
  personal?: PersonalReading;
  reading: DailyHoroscope | undefined;
  isLoading: boolean;
  error: unknown;
  onRetry: () => void;
  retrying?: boolean;
  /** Tropical sun sign the reading was requested for. */
  sign: string | undefined;
}

export function DailyReadingCard({ preparing, personal, reading, isLoading, error, onRetry, retrying, sign }: DailyReadingCardProps) {
  const navigate = useNavigate();
  const reduceMotion = useReducedMotion();
  const [expanded, setExpanded] = useState(false);
  const bodyId = useId();
  const signInfo = findSign(sign);

  if (preparing && !isLoading) {
    return (
      <Card variant="feature" as="section" aria-labelledby={`${bodyId}-prep`}>
        <div className="flex flex-col items-center py-6 text-center">
          <span aria-hidden="true" className="mb-4 flex size-16 items-center justify-center rounded-chip bg-ai-subtle text-ai [&_svg]:size-7">
            <MoonStar />
          </span>
          <h2 id={`${bodyId}-prep`} className="font-sans text-title text-fg">
            Your reading is being prepared…
          </h2>
          <p className="mt-2 max-w-sm text-body-sm text-fg-secondary">It can take a moment the first time each day. Everything else on this page is ready.</p>
          <div className="mt-5">
            <WakingRetry seconds={Math.min(Math.max(preparing.retryAfter ?? 10, 3), 60)} onRetry={onRetry} retrying={retrying} attemptsKey={preparing.error} />
          </div>
        </div>
      </Card>
    );
  }

  if (personal && !isLoading) {
    return (
      <Card variant="feature" as="section" aria-labelledby={`${bodyId}-p`}>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p id={`${bodyId}-p`} className="flex items-center gap-2 text-caption font-medium text-fg-muted">
            <MoonStar aria-hidden="true" className="size-4" />
            Today · {formatCivilDate(personal.date, { weekday: true })}
          </p>
          <Badge tone="ai">{personal.generated_by === "template" ? "Simplified reading" : "Your personal reading"}</Badge>
        </div>
        {personal.generated_by && (
          <p role="status" className="mt-3 min-h-5 text-caption text-fg-muted">
            {personal.generated_by === "template" ? "Your full reading is being written…" : ""}
          </p>
        )}
        <motion.div key={personal.generated_by} initial={reduceMotion || personal.generated_by === "template" ? false : { opacity: 0.3 }} animate={{ opacity: 1 }} transition={{ duration: 0.4 }}>
          <PersonalBody r={personal} />
        </motion.div>
        <div className="mt-5">
          <Button
            variant="ai"
            leadingIcon={<Sparkles aria-hidden="true" className="size-4" />}
            onClick={() => navigate("/chat", { state: { draft: "What does today hold for me, based on my chart?" } })}
          >
            Ask about today
          </Button>
        </div>
      </Card>
    );
  }

  if (isLoading) {
    return (
      <Card variant="feature" as="section" aria-label="Today's reading">
        <LoadingRegion label="Loading today's reading">
          <ReadingProgress />
          <Skeleton className="h-3 w-40" />
          <Skeleton className="mt-4 h-6 w-3/4" />
          <SkeletonText lines={3} className="mt-5" />
          <div className="mt-6 grid grid-cols-[repeat(3,minmax(0,1fr))] gap-3">
            <Skeleton className="h-10 rounded-control" />
            <Skeleton className="h-10 rounded-control" />
            <Skeleton className="h-10 rounded-control" />
          </div>
          <Skeleton className="mt-6 h-11 w-44 rounded-control" />
        </LoadingRegion>
      </Card>
    );
  }

  if (error || !reading) {
    return (
      <Card variant="feature" as="section" aria-labelledby={`${bodyId}-t`}>
        <h2 id={`${bodyId}-t`} className="mb-3 font-sans text-title text-fg">
          Today's reading
        </h2>
        <ErrorState compact error={error ?? new Error("Today's reading didn't load.")} what="today's reading" onRetry={onRetry} retrying={retrying} />
      </Card>
    );
  }

  const moonSign = moonSignFromTransit(reading.transit_data);
  const headline = moonSign ? `The Moon moves through ${moonSign} today` : `Your day as a ${signInfo?.english ?? "sun sign"}`;
  const areas = [
    { key: "love", label: "Love", icon: <Heart aria-hidden="true" />, text: reading.love_reading },
    { key: "career", label: "Career", icon: <Briefcase aria-hidden="true" />, text: reading.career_reading },
    { key: "wellness", label: "Wellbeing", icon: <Leaf aria-hidden="true" />, text: reading.wellness_reading },
  ].filter((a) => !!a.text);
  const today = new Date().toISOString().slice(0, 10);
  const stale = reading.date < today;

  return (
    <Card variant="feature" as="section" aria-labelledby={`${bodyId}-h`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="flex items-center gap-2 text-caption font-medium text-fg-muted">
          <MoonStar aria-hidden="true" className="size-4" />
          Today · {formatCivilDate(reading.date, { weekday: true })}
        </p>
        {stale ? <Badge>From yesterday</Badge> : <Badge tone="ai">General reading</Badge>}
      </div>
      <h2 id={`${bodyId}-h`} className="mt-3 text-h3 text-fg">
        {headline}
      </h2>
      <p className="mt-1 text-caption text-fg-muted">
        For {signInfo?.english ?? "your"} sun sign (Western, tropical). Your personal Vedic reading arrives in a later update.
      </p>
      <div id={bodyId} className="mt-4">
        <p className={expanded ? "text-body-lg text-fg" : "line-clamp-3 text-body-lg text-fg"}>{reading.general_reading}</p>
        {expanded && areas.length > 0 && (
          <dl className="mt-4 space-y-3">
            {areas.map((a) => (
              <div key={a.key}>
                <dt className="flex items-center gap-2 text-body-sm font-semibold text-fg [&_svg]:size-4 [&_svg]:text-fg-muted">
                  {a.icon}
                  {a.label}
                </dt>
                <dd className="mt-1 text-body text-fg-secondary">{a.text}</dd>
              </div>
            ))}
          </dl>
        )}
        <Button variant="link" size="sm" className="mt-1" aria-expanded={expanded} aria-controls={bodyId} onClick={() => setExpanded((v) => !v)}>
          {expanded ? "Show less" : "Read full reading"}
        </Button>
      </div>

      <p className="mt-3 flex min-w-0 max-w-full flex-wrap items-center gap-2">
        <span className="text-caption text-fg-muted">Based on</span>
        {signInfo && <Badge className="max-w-full whitespace-normal break-words text-left [overflow-wrap:anywhere]">{signInfo.english} sun sign</Badge>}
        {moonSign && <Badge className="max-w-full whitespace-normal break-words text-left [overflow-wrap:anywhere]">Moon in {moonSign}</Badge>}
        <Badge>Today's sky</Badge>
      </p>

      {(reading.lucky_color || reading.lucky_number) && (
        <p className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-body-sm text-fg-secondary">
          {reading.lucky_color && (
            <span>
              Lucky colour: <span className="font-medium text-fg">{reading.lucky_color}</span>
            </span>
          )}
          {reading.lucky_number && (
            <span>
              Lucky number: <span className="font-medium tabular text-fg">{reading.lucky_number}</span>
            </span>
          )}
          <span className="text-caption text-fg-muted">(just for fun)</span>
        </p>
      )}

      <div className="mt-5">
        <Button
          variant="ai"
          leadingIcon={<Sparkles aria-hidden="true" className="size-4" />}
          onClick={() => navigate("/chat", { state: { draft: "What does today hold for me, based on my chart?" } })}
        >
          Ask about today
        </Button>
      </div>
    </Card>
  );
}
