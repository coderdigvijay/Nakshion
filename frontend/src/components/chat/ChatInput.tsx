import { useEffect, useId, useRef, useState } from "react";
import { ArrowUp, Check, Languages, Square } from "lucide-react";
import { cn } from "../../lib/utils";
import { IconButton } from "../ui/IconButton";
import type { ChatLanguage } from "../../types";

// COMPONENTS.md → ChatInput. Controlled draft (the page keeps it on failure), Send/Stop,
// accessible language menu, counter from 80% of the 2,000-character limit.

const LANGUAGES: Array<{ value: ChatLanguage; label: string; short: string; lang?: string }> = [
  { value: "english", label: "English", short: "EN" },
  { value: "hindi", label: "हिंदी", short: "हिंदी", lang: "hi" },
  { value: "hinglish", label: "Hinglish", short: "Hinglish" },
];

const LIMIT = 2000;

export interface ChatInputProps {
  value: string;
  onChange: (v: string) => void;
  onSend: () => void;
  onStop: () => void;
  busy: boolean;
  language: ChatLanguage;
  onLanguageChange: (l: ChatLanguage) => void;
  /** Disables the composer and explains why (quota, no chart, unverified). */
  disabledReason?: string;
  inputRef?: React.RefObject<HTMLTextAreaElement | null>;
}

function LanguageMenu({ value, onChange }: { value: ChatLanguage; onChange: (l: ChatLanguage) => void }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  const btnRef = useRef<HTMLButtonElement>(null);
  const itemRefs = useRef<Array<HTMLButtonElement | null>>([]);
  const current = LANGUAGES.find((l) => l.value === value) ?? LANGUAGES[0];

  useEffect(() => {
    if (open) itemRefs.current[LANGUAGES.findIndex((l) => l.value === value)]?.focus();
  }, [open, value]);

  const close = (refocus = true) => {
    setOpen(false);
    if (refocus) btnRef.current?.focus();
  };

  return (
    <div
      className="relative"
      onBlur={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget as Node | null)) setOpen(false);
      }}
    >
      <button
        ref={btnRef}
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={`${id}-menu`}
        aria-label={`Answer language: ${current.label}`}
        onClick={() => setOpen((v) => !v)}
        className="focus-ring flex min-h-11 cursor-pointer md:min-h-9 items-center gap-1.5 rounded-control px-2.5 text-body-sm font-medium text-fg-secondary hover:bg-elevated hover:text-fg"
      >
        <Languages aria-hidden="true" className="size-4" />
        <span lang={current.lang}>{current.short}</span>
      </button>
      {open && (
        <div
          id={`${id}-menu`}
          role="menu"
          aria-label="Answer language"
          onKeyDown={(e) => {
            const idx = itemRefs.current.findIndex((el) => el === document.activeElement);
            if (e.key === "Escape") {
              e.preventDefault();
              close();
            } else if (e.key === "ArrowDown") {
              e.preventDefault();
              itemRefs.current[(idx + 1) % LANGUAGES.length]?.focus();
            } else if (e.key === "ArrowUp") {
              e.preventDefault();
              itemRefs.current[(idx - 1 + LANGUAGES.length) % LANGUAGES.length]?.focus();
            }
          }}
          className="absolute bottom-full left-0 z-40 mb-2 w-44 rounded-card border border-border bg-overlay p-1 shadow-e2"
        >
          {LANGUAGES.map((l, i) => (
            <button
              key={l.value}
              ref={(el) => {
                itemRefs.current[i] = el;
              }}
              type="button"
              role="menuitemradio"
              aria-checked={l.value === value}
              tabIndex={-1}
              lang={l.lang}
              onClick={() => {
                onChange(l.value);
                close();
              }}
              className={cn(
                "focus-ring flex min-h-11 w-full cursor-pointer items-center justify-between rounded-control px-3 text-left text-body-sm",
                l.value === value ? "bg-ai-subtle text-fg" : "text-fg-secondary hover:bg-elevated hover:text-fg",
              )}
            >
              {l.label}
              {l.value === value && <Check aria-hidden="true" className="size-4" />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export function ChatInput({ value, onChange, onSend, onStop, busy, language, onLanguageChange, disabledReason, inputRef }: ChatInputProps) {
  const id = useId();
  const localRef = useRef<HTMLTextAreaElement>(null);
  const ref = inputRef ?? localRef;
  const disabled = !!disabledReason;
  const empty = value.trim().length === 0;
  const over = value.length > LIMIT;

  // Auto-grow 1→6 lines (max 200px), then scroll.
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }, [value, ref]);

  const trySend = () => {
    if (busy || disabled || empty || over) return;
    onSend();
  };

  return (
    <div>
      <div
        className={cn(
          "flex items-end gap-1 rounded-sheet border bg-field p-2 transition-[border-color,box-shadow] duration-150",
          disabled ? "border-border" : "border-border-strong focus-within:border-ai focus-within:shadow-glow-ai",
        )}
      >
        <LanguageMenu value={language} onChange={onLanguageChange} />
        <label htmlFor={`${id}-ta`} className="sr-only">
          Message Nakshion
        </label>
        <textarea
          ref={ref}
          id={`${id}-ta`}
          rows={1}
          value={value}
          disabled={disabled}
          aria-describedby={`${id}-cap${disabledReason ? ` ${id}-reason` : ""}`}
          aria-invalid={over || undefined}
          placeholder="Ask about your chart…"
          lang={language === "hindi" ? "hi" : undefined}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={(e) => {
            const coarse = window.matchMedia?.("(pointer: coarse)").matches;
            if (e.key === "Enter" && !e.shiftKey && !coarse && !e.nativeEvent.isComposing) {
              e.preventDefault();
              trySend();
            } else if (e.key === "Escape" && busy) {
              e.preventDefault();
              onStop();
            }
          }}
          className="max-h-[200px] min-h-10 flex-1 resize-none bg-transparent px-2 py-2 text-body text-fg outline-none placeholder:text-fg-muted disabled:cursor-not-allowed disabled:text-fg-disabled"
        />
        {busy ? (
          <IconButton aria-label="Stop generating" variant="secondary" round onClick={onStop}>
            <Square aria-hidden="true" className="fill-current" />
          </IconButton>
        ) : (
          <IconButton
            aria-label="Send"
            variant="ai"
            round
            aria-disabled={empty || disabled || over || undefined}
            onClick={trySend}
          >
            <ArrowUp aria-hidden="true" />
          </IconButton>
        )}
      </div>
      <div className="mt-2 flex items-start justify-between gap-3 px-2">
        <p id={`${id}-cap`} className="text-caption text-fg-muted">
          Nakshion reads your chart with AI. Treat it as guidance, not certainty.
        </p>
        {value.length >= LIMIT * 0.8 && (
          <p className={cn("shrink-0 text-caption tabular", value.length >= LIMIT * 0.95 ? "text-warning" : "text-fg-muted")} aria-live="polite">
            {value.length.toLocaleString("en-IN")} / {LIMIT.toLocaleString("en-IN")}
          </p>
        )}
      </div>
      {disabledReason && (
        <p id={`${id}-reason`} className="sr-only">
          {disabledReason}
        </p>
      )}
    </div>
  );
}
