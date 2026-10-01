import { useEffect, useState } from "react";
import { CloudOff, KeyRound, MoonStar, SearchX, Clock, WifiOff } from "lucide-react";
import { cn } from "../../lib/utils";
import { Button, ButtonLink } from "./Button";
import { isNotFound, quotaMessage, toApiError } from "../../services/errors";

// COMPONENTS.md → EmptyState, plus a status-aware ErrorState (coding_rules_frontend §3).

export interface EmptyStateProps {
  icon: React.ReactNode;
  title: string;
  body?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
  tone?: "ai" | "danger" | "neutral";
  headingLevel?: "h2" | "h3";
}

export function EmptyState({ icon, title, body, action, className, tone = "ai", headingLevel: H = "h2" }: EmptyStateProps) {
  return (
    <div className={cn("mx-auto flex max-w-[400px] flex-col items-center py-12 text-center", className)}>
      <div
        aria-hidden="true"
        className={cn(
          "mb-4 flex size-20 items-center justify-center rounded-chip [&_svg]:size-9",
          tone === "ai" && "bg-ai-subtle text-ai",
          tone === "danger" && "bg-danger-subtle text-danger",
          tone === "neutral" && "bg-elevated text-fg-secondary",
        )}
      >
        {icon}
      </div>
      <H className="font-sans text-title text-fg">{title}</H>
      {body && <p className="mt-2 text-body-sm text-fg-secondary">{body}</p>}
      {action && <div className="mt-6 flex flex-wrap items-center justify-center gap-3">{action}</div>}
    </div>
  );
}

export interface ErrorStateProps {
  error: unknown;
  onRetry?: () => void;
  retrying?: boolean;
  /** What failed, e.g. "your chart". */
  what?: string;
  className?: string;
  compact?: boolean;
  /** Where to send people when the thing no longer exists (404 / NOT_FOUND). Replaces "Try again". */
  notFoundLink?: { to: string; label: string };
  notFoundAction?: { onClick: () => void; label: string };
}

/** Maps HTTP status to plain-language copy: 401 / 404 / 429 / 503 / network / other. */
type Tone = "ai" | "danger" | "neutral";

/** "5:30 AM" local, plus "tomorrow at" when it is not today. */
function localTimeLabel(d: Date): string {
  const time = d.toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit" });
  return d.toDateString() === new Date().toDateString() ? time : `tomorrow at ${time}`;
}

function describeError(error: unknown, what = "this"): { icon: React.ReactNode; title: string; body: string; tone: Tone } {
  const e = toApiError(error);
  if (isNotFound(e)) return { icon: <SearchX />, title: "Not found", body: "We couldn't find that. It may have been deleted.", tone: "neutral" };
  if (e.network) return { icon: <WifiOff />, title: `Couldn't load ${what}`, body: e.detail, tone: "danger" };
  switch (e.status) {
    case 401:
      return { icon: <KeyRound />, title: "Your session has ended", body: "Please sign in again to continue.", tone: "neutral" };
    case 429: {
      // A limit isn't a failure: say when it lifts (local time) instead of offering a retry that can't work.
      if (e.code === "QUOTA_EXCEEDED") return { icon: <Clock />, title: "You've reached today's limit", body: quotaMessage(e), tone: "neutral" };
      const at = e.retryAfter ? new Date(Date.now() + e.retryAfter * 1000) : null;
      return {
        icon: <Clock />,
        title: "Too many requests for now",
        body: at ? `You can try again at ${localTimeLabel(at)}.` : "Please wait a little before trying again.",
        tone: "neutral",
      };
    }
    case 503:
      return { icon: <MoonStar />, title: "Waking up the stars…", body: "Nakshion is starting up. This can take up to 30 seconds after a quiet spell.", tone: "ai" };
    default:
      // Raw server text can be technical; only 4xx messages are written for users (api-contract §1.3).
      return {
        icon: <CloudOff />,
        title: `Couldn't load ${what}`,
        body: e.status && e.status < 500 ? e.detail : "Something went wrong on our side. Please try again.",
        tone: "danger",
      };
  }
}

const MAX_AUTO_RETRIES = 3;

/** DB-cold / dependency 503: count down (Retry-After, default 10 s) and retry on its own a few times. */
export function WakingRetry({ seconds, onRetry, retrying, attemptsKey }: { seconds: number; onRetry: () => void; retrying?: boolean; attemptsKey: unknown }) {
  const [left, setLeft] = useState(seconds);
  const [attempts, setAttempts] = useState(0);
  const [seen, setSeen] = useState(attemptsKey);
  // A new error object means the last retry failed again: restart the countdown (derived state, set during render).
  if (seen !== attemptsKey) {
    setSeen(attemptsKey);
    setLeft(seconds);
    setAttempts((n) => n + 1);
  }
  useEffect(() => {
    if (retrying || attempts > MAX_AUTO_RETRIES) return;
    if (left <= 0) {
      onRetry();
      return;
    }
    const t = setTimeout(() => setLeft((l) => l - 1), 1000);
    return () => clearTimeout(t);
  }, [left, retrying, attempts, onRetry]);
  return (
    <Button size="sm" variant="secondary" onClick={onRetry} loading={retrying}>
      {attempts <= MAX_AUTO_RETRIES && !retrying ? `Trying again in ${Math.max(left, 0)} s` : "Try again"}
    </Button>
  );
}

export function ErrorState({ error, onRetry, retrying, what, className, compact, notFoundLink, notFoundAction }: ErrorStateProps) {
  const d = describeError(error, what);
  const apiErr = toApiError(error);
  const missing = isNotFound(apiErr);
  const back = missing
    ? notFoundLink
      ? <ButtonLink to={notFoundLink.to} variant="secondary" size="sm">{notFoundLink.label}</ButtonLink>
      : notFoundAction
        ? <Button size="sm" variant="secondary" onClick={notFoundAction.onClick}>{notFoundAction.label}</Button>
        : null
    : onRetry && apiErr.status !== 429
      ? apiErr.status === 503 && !apiErr.network
        ? <WakingRetry seconds={Math.min(Math.max(apiErr.retryAfter ?? 10, 3), 60)} onRetry={onRetry} retrying={retrying} attemptsKey={error} />
        : <Button size="sm" variant="secondary" onClick={onRetry} loading={retrying}>Try again</Button>
      : null;
  if (compact) {
    return (
      <div
        role="alert"
        className={cn(
          "flex flex-col gap-3 rounded-control border p-4 sm:flex-row sm:items-center",
          d.tone === "danger" && "border-danger/30 bg-danger-subtle",
          d.tone === "ai" && "border-ai/30 bg-ai-subtle",
          d.tone === "neutral" && "border-border bg-elevated",
          className,
        )}
      >
        <span aria-hidden="true" className={cn("[&_svg]:size-5", d.tone === "danger" ? "text-danger" : d.tone === "ai" ? "text-ai" : "text-fg-secondary")}>
          {d.icon}
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-body-sm font-semibold text-fg">{d.title}</p>
          <p className="text-caption text-fg-secondary">{d.body}</p>
        </div>
        {back}
      </div>
    );
  }
  return (
    <div role="alert" className={className}>
      <EmptyState
        tone={d.tone}
        icon={d.icon}
        title={d.title}
        body={d.body}
        action={back}
      />
    </div>
  );
}
