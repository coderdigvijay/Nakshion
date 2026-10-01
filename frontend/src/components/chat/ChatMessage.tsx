import { useEffect, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { AlertCircle, AlertTriangle, Bookmark, Check, ChevronRight, Clock, Copy, ThumbsDown, ThumbsUp } from "lucide-react";
import { cn } from "../../lib/utils";
import { formatClock } from "../../lib/format";
import { spring } from "../../lib/motion";
import { AiAvatar } from "../ui/Avatar";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { IconButton } from "../ui/IconButton";
import { Markdown } from "./Markdown";
import { bufferPartial, extractFactMarkers, humaniseFactId, stripFactMarkers } from "../../lib/markdown";

// COMPONENTS.md → ChatMessage. Streaming-ready contract: the same props render
// thinking → streaming → complete | interrupted | error, so SSE (H6) needs no redesign.

export type ChatMessageStatus = "complete" | "sending" | "failed" | "thinking" | "streaming" | "interrupted" | "error";

export interface ChatMessageProps {
  role: "user" | "assistant";
  content: string;
  status?: ChatMessageStatus;
  createdAt?: string;
  /** [v1-add] factor citations; MVP shows one static "Based on your chart" badge. */
  citations?: Array<{ factor_id: string; label: string }>;
  sources?: Array<{ source_id: string; title: string; section?: string | null }>;
  onRetry?: () => void;
  lang?: string;
  errorText?: string;
  /** Persisted assistant messages only (H7/H8). */
  messageId?: string;
  bookmarked?: boolean;
  feedback?: "up" | "down" | null;
  onBookmark?: (bookmarked: boolean) => void;
  onFeedback?: (rating: "up" | "down") => void;
}

const THINKING_STEPS = ["Reading your chart…", "Looking at your dasha and transits…", "Putting it into words…", "Still working, this one needs a little longer…"];

function ThinkingDots() {
  const reduce = useReducedMotion();
  return (
    <span aria-hidden="true" className="inline-flex items-center gap-1">
      {[0, 1, 2].map((i) =>
        reduce ? (
          <span key={i} className="size-1.5 rounded-chip bg-ai" />
        ) : (
          <motion.span
            key={i}
            className="size-1.5 rounded-chip bg-ai"
            animate={{ opacity: [0.3, 1, 0.3] }}
            transition={{ duration: 1.2, repeat: Infinity, delay: i * 0.2 }}
          />
        ),
      )}
    </span>
  );
}

function ThinkingCopy() {
  const [step, setStep] = useState(0);
  useEffect(() => {
    const timers = [setTimeout(() => setStep(1), 3000), setTimeout(() => setStep(2), 7000), setTimeout(() => setStep(3), 15000)];
    return () => timers.forEach(clearTimeout);
  }, []);
  return <span className="text-body-sm text-fg-muted">{THINKING_STEPS[step]}</span>;
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <IconButton
      size="sm"
      aria-label={copied ? "Copied" : "Copy answer"}
      onClick={() => {
        navigator.clipboard
          .writeText(text)
          .then(() => {
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
          })
          .catch(() => setCopied(false));
      }}
    >
      {copied ? <Check aria-hidden="true" /> : <Copy aria-hidden="true" />}
    </IconButton>
  );
}

export function ChatMessage({ role, content, status = "complete", createdAt, citations, sources, onRetry, lang, errorText, messageId, bookmarked, feedback, onBookmark, onFeedback }: ChatMessageProps) {
  const reduce = useReducedMotion();
  const time = createdAt ? formatClock(createdAt) : "";

  if (role === "user") {
    return (
      <motion.article
        aria-label={`You${time ? `, ${time}` : ""}`}
        initial={reduce ? false : { opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={spring.snappy}
        className="flex flex-col items-end"
        lang={lang}
      >
        <div
          className={cn(
            "max-w-[85%] whitespace-pre-wrap break-words [overflow-wrap:anywhere] rounded-bubble rounded-br-[6px] bg-elevated px-4 py-3 text-body text-fg md:max-w-[70%]",
            status === "failed" && "border border-danger",
          )}
        >
          {content}
        </div>
        <p className="mt-1 flex items-center gap-1.5 text-caption text-fg-muted">
          {status === "sending" && <Clock aria-hidden="true" className="size-3.5" />}
          {status === "sending" ? "Sending" : time}
        </p>
        {status === "failed" && (
          <p role="alert" className="mt-1 flex items-center gap-2 text-caption text-danger">
            <AlertCircle aria-hidden="true" className="size-4" />
            {errorText ?? "Not sent."}
            {onRetry && (
              <Button variant="link" size="sm" onClick={onRetry} className="min-h-0 text-caption">
                Retry
              </Button>
            )}
          </p>
        )}
      </motion.article>
    );
  }

  const busy = status === "thinking" || status === "streaming";
  const shown = status === "streaming" ? bufferPartial(content) : stripFactMarkers(content);
  // Prefer server citations; otherwise turn any markers the model wrote into chips at the end.
  const chips = citations && citations.length > 0 ? citations.map((c) => ({ id: c.factor_id, label: c.label })) : extractFactMarkers(content).map((id) => ({ id, label: humaniseFactId(id) }));

  return (
    <motion.article
      aria-label={`Nakshion${time ? `, ${time}` : ""}`}
      aria-busy={busy || undefined}
      initial={reduce ? false : { opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.15 }}
      lang={lang}
    >
      <div className="flex items-center gap-3">
        <AiAvatar streaming={busy} />
        <p className="text-caption font-semibold text-fg-secondary">Nakshion</p>
        <Badge tone="ai">AI</Badge>
        {time && !busy && <p className="text-caption text-fg-muted">{time}</p>}
      </div>
      <div className="mt-2 min-w-0 sm:pl-11">
        {status === "thinking" && (
          <p className="flex items-center gap-3 py-1">
            <ThinkingDots />
            <ThinkingCopy />
          </p>
        )}
        {status === "error" ? (
          <div role="alert" className="flex flex-col gap-3 rounded-control border border-danger/30 bg-danger-subtle p-4 sm:flex-row sm:items-center">
            <AlertCircle aria-hidden="true" className="size-5 shrink-0 text-danger" />
            <p className="flex-1 text-body-sm text-fg">{errorText ?? "Nakshion couldn't answer just now."}</p>
            {onRetry && (
              <Button size="sm" variant="secondary" onClick={onRetry}>
                Try again
              </Button>
            )}
          </div>
        ) : (
          shown && (
            <div className="max-w-[68ch] text-body-lg text-fg">
              <Markdown text={shown} />
              {status === "streaming" && (
                <span aria-hidden="true" className="ml-0.5 inline-block h-[1.1em] w-0.5 translate-y-[0.2em] animate-caret bg-ai" />
              )}
            </div>
          )
        )}
        {status === "interrupted" && (
          <p role="alert" className="mt-3 flex items-center gap-2 rounded-control bg-warning-subtle p-3 text-body-sm text-fg">
            <AlertTriangle aria-hidden="true" className="size-4 text-warning" />
            Response interrupted.
            {onRetry && (
              <Button variant="link" size="sm" className="min-h-0" onClick={onRetry}>
                Retry
              </Button>
            )}
          </p>
        )}
        {status === "complete" && shown && sources && sources.length > 0 && (
          <details className="group mt-2">
            <summary className="focus-ring flex min-h-11 w-fit cursor-pointer list-none items-center gap-1.5 rounded-control text-caption font-medium text-fg-muted hover:text-fg-secondary md:min-h-9">
              <ChevronRight aria-hidden="true" className="size-4 transition-transform group-open:rotate-90" />
              {lang === "hi" ? "स्रोत" : "Sources"} ({new Set(sources.map((s) => `${s.title}|${s.section ?? ""}`)).size})
            </summary>
            <ul className="mt-1 space-y-1 pl-5 text-caption text-fg-secondary">
              {[...new Map(sources.map((s) => [`${s.title}|${s.section ?? ""}`, s])).values()].map((s) => (
                <li key={s.source_id} className="break-words [overflow-wrap:anywhere]">
                  {s.title}
                  {s.section ? <span className="line-clamp-1 text-fg-muted">{s.section}</span> : null}
                </li>
              ))}
            </ul>
          </details>
        )}
        {status === "complete" && shown && (
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <span className="text-caption text-fg-muted">{lang === "hi" ? "आधार" : "Based on"}</span>
            {chips.length > 0 ? (
              chips.slice(0, 4).map((c) => <Badge key={c.id} className="max-w-full whitespace-normal break-words text-left [overflow-wrap:anywhere]">{c.label}</Badge>)
            ) : (
              <Badge>{lang === "hi" ? "आपकी कुंडली" : "Your chart"}</Badge>
            )}
            <span className="ml-auto flex items-center">
              {messageId && onFeedback && (
                <>
                  <IconButton size="sm" aria-label="Helpful" aria-pressed={feedback === "up"} onClick={() => onFeedback("up")} className={feedback === "up" ? "text-success" : undefined}>
                    <ThumbsUp aria-hidden="true" className={feedback === "up" ? "fill-current" : undefined} />
                  </IconButton>
                  <IconButton size="sm" aria-label="Not helpful" aria-pressed={feedback === "down"} onClick={() => onFeedback("down")} className={feedback === "down" ? "text-danger" : undefined}>
                    <ThumbsDown aria-hidden="true" className={feedback === "down" ? "fill-current" : undefined} />
                  </IconButton>
                </>
              )}
              {messageId && onBookmark && (
                <IconButton
                  size="sm"
                  aria-label={bookmarked ? "Remove bookmark" : "Bookmark answer"}
                  aria-pressed={!!bookmarked}
                  onClick={() => onBookmark(!bookmarked)}
                  className={bookmarked ? "text-accent-text" : undefined}
                >
                  <Bookmark aria-hidden="true" className={bookmarked ? "fill-current" : undefined} />
                </IconButton>
              )}
              <CopyButton text={shown} />
            </span>
          </div>
        )}
      </div>
    </motion.article>
  );
}
