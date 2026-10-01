import { useId, useRef } from "react";
import { AlertCircle } from "lucide-react";
import { cn } from "../../lib/utils";
import { controlStyles } from "../ui/styles";
import { dateFromParts, MONTHS, type BirthDateValue } from "../../lib/birthForm";

// COMPONENTS.md → BirthDateField: Day · Month · Year (en-IN order), live read-back line.

export interface BirthDateFieldProps {
  legend?: string;
  value: BirthDateValue;
  onChange: (v: BirthDateValue) => void;
  onBlur?: () => void;
  error?: string;
  hint?: string;
}

export function BirthDateField({ legend = "Date of birth", value, onChange, onBlur, error, hint }: BirthDateFieldProps) {
  const id = useId();
  const monthRef = useRef<HTMLSelectElement>(null);
  const yearRef = useRef<HTMLInputElement>(null);
  const dayRef = useRef<HTMLInputElement>(null);
  const date = dateFromParts(value);
  const readBack = date
    ? date.toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "long", year: "numeric" })
    : "";
  const msgId = `${id}-msg`;
  const describedBy = [error || hint ? msgId : null, `${id}-readback`].filter(Boolean).join(" ");

  return (
    <fieldset
      className="min-w-0"
      onBlur={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget as Node | null)) onBlur?.();
      }}
    >
      <legend className="mb-2 text-body-sm font-medium text-fg-secondary">{legend}</legend>
      <div className="flex gap-2">
        <div className="w-[72px] shrink-0">
          <label htmlFor={`${id}-d`} className="sr-only">
            Day
          </label>
          <input
            ref={dayRef}
            id={`${id}-d`}
            inputMode="numeric"
            autoComplete="bday-day"
            maxLength={2}
            placeholder="DD"
            value={value.day}
            aria-invalid={error ? true : undefined}
            aria-describedby={describedBy}
            onChange={(e) => {
              const day = e.target.value.replace(/\D/g, "").slice(0, 2);
              onChange({ ...value, day });
              if (day.length === 2) monthRef.current?.focus();
            }}
            className={cn(controlStyles, "h-12 px-3 text-center tabular", error ? "border-danger" : "border-border-strong")}
          />
        </div>
        <div className="relative min-w-0 flex-1">
          <label htmlFor={`${id}-m`} className="sr-only">
            Month
          </label>
          <select
            ref={monthRef}
            id={`${id}-m`}
            autoComplete="bday-month"
            value={value.month}
            aria-invalid={error ? true : undefined}
            aria-describedby={describedBy}
            onChange={(e) => {
              onChange({ ...value, month: e.target.value });
              if (e.target.value) yearRef.current?.focus();
            }}
            className={cn(controlStyles, "h-12 cursor-pointer appearance-none px-3", error ? "border-danger" : "border-border-strong", !value.month && "text-fg-muted")}
          >
            <option value="" disabled>
              Month
            </option>
            {MONTHS.map((m, i) => (
              <option key={m} value={String(i + 1)}>
                {m}
              </option>
            ))}
          </select>
        </div>
        <div className="w-[96px] shrink-0">
          <label htmlFor={`${id}-y`} className="sr-only">
            Year
          </label>
          <input
            ref={yearRef}
            id={`${id}-y`}
            inputMode="numeric"
            autoComplete="bday-year"
            maxLength={4}
            placeholder="YYYY"
            value={value.year}
            aria-invalid={error ? true : undefined}
            aria-describedby={describedBy}
            onKeyDown={(e) => {
              if (e.key === "Backspace" && !value.year) monthRef.current?.focus();
            }}
            onChange={(e) => onChange({ ...value, year: e.target.value.replace(/\D/g, "").slice(0, 4) })}
            className={cn(controlStyles, "h-12 px-3 text-center tabular", error ? "border-danger" : "border-border-strong")}
          />
        </div>
      </div>
      <p id={`${id}-readback`} aria-live="polite" className="mt-2 min-h-[1.4em] text-body-sm text-fg-secondary">
        {readBack}
      </p>
      {error ? (
        <p id={msgId} className="flex items-start gap-1.5 text-caption text-danger">
          <AlertCircle aria-hidden="true" className="mt-px size-4 shrink-0" />
          {error}
        </p>
      ) : (
        hint && (
          <p id={msgId} className="text-caption text-fg-muted">
            {hint}
          </p>
        )
      )}
    </fieldset>
  );
}
