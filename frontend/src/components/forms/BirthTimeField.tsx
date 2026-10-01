import { useId, useRef } from "react";
import { AlertCircle, Check, Info } from "lucide-react";
import { cn } from "../../lib/utils";
import { controlStyles } from "../ui/styles";
import { Segmented } from "../ui/Tabs";
import { Chip } from "../ui/Badge";
import { APPROX_LABEL, type ApproxWindow, type BirthTimeValue } from "../../lib/birthForm";

// COMPONENTS.md → BirthTimeField: hour : minute + AM/PM, "I don't know" path with honest note.

export interface BirthTimeFieldProps {
  legend?: string;
  value: BirthTimeValue;
  onChange: (v: BirthTimeValue) => void;
  onBlur?: () => void;
  error?: string;
  /** "their" for compatibility partner copy. */
  whose?: "my" | "their";
}

const WINDOWS: ApproxWindow[] = ["morning", "afternoon", "evening", "night", "unknown"];

export function BirthTimeField({ legend = "Time of birth", value, onChange, onBlur, error, whose = "my" }: BirthTimeFieldProps) {
  const id = useId();
  const minuteRef = useRef<HTMLInputElement>(null);
  const msgId = `${id}-msg`;

  return (
    <fieldset
      className="min-w-0"
      onBlur={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget as Node | null)) onBlur?.();
      }}
    >
      <legend className="mb-2 text-body-sm font-medium text-fg-secondary">{legend}</legend>

      {/* Collapses with grid-rows 1fr→0fr (never animate height; MASTER §8.1). */}
      <div className={cn("grid transition-[grid-template-rows] duration-250 ease-standard", value.unknown ? "grid-rows-[0fr]" : "grid-rows-[1fr]")}>
        <div className="overflow-hidden" inert={value.unknown || undefined}>
          <div className="flex flex-wrap items-center gap-2 pb-1">
            <label htmlFor={`${id}-h`} className="sr-only">
              Hour
            </label>
            <input
              id={`${id}-h`}
              inputMode="numeric"
              maxLength={2}
              placeholder="HH"
              value={value.hour}
              aria-invalid={error && !value.unknown ? true : undefined}
              aria-describedby={error ? msgId : undefined}
              onChange={(e) => {
                const hour = e.target.value.replace(/\D/g, "").slice(0, 2);
                onChange({ ...value, hour });
                if (hour.length === 2 || (hour.length === 1 && Number(hour) > 1)) minuteRef.current?.focus();
              }}
              className={cn(controlStyles, "h-12 w-16 px-2 text-center tabular", error && !value.unknown ? "border-danger" : "border-border-strong")}
            />
            <span aria-hidden="true" className="text-title text-fg-muted">
              :
            </span>
            <label htmlFor={`${id}-min`} className="sr-only">
              Minute
            </label>
            <input
              ref={minuteRef}
              id={`${id}-min`}
              inputMode="numeric"
              maxLength={2}
              placeholder="MM"
              value={value.minute}
              aria-invalid={error && !value.unknown ? true : undefined}
              aria-describedby={error ? msgId : undefined}
              onChange={(e) => onChange({ ...value, minute: e.target.value.replace(/\D/g, "").slice(0, 2) })}
              className={cn(controlStyles, "h-12 w-16 px-2 text-center tabular", error && !value.unknown ? "border-danger" : "border-border-strong")}
            />
            <Segmented
              label="AM or PM"
              options={[
                { value: "AM", label: "AM" },
                { value: "PM", label: "PM" },
              ]}
              value={value.period}
              onChange={(period) => onChange({ ...value, period })}
              className="ml-1"
            />
          </div>
        </div>
      </div>

      <label className="mt-2 flex min-h-11 cursor-pointer items-center gap-3">
        <span className="relative inline-flex size-5 shrink-0">
          <input
            type="checkbox"
            checked={value.unknown}
            onChange={(e) => onChange({ ...value, unknown: e.target.checked, approx: e.target.checked ? value.approx : "" })}
            className="peer focus-ring size-5 cursor-pointer appearance-none rounded-[6px] border border-border-strong bg-field checked:border-ai checked:bg-ai-fill"
          />
          <Check aria-hidden="true" className="pointer-events-none absolute inset-0.5 size-4 text-on-ai opacity-0 peer-checked:opacity-100" />
        </span>
        <span className="text-body text-fg">I don't know {whose} exact birth time</span>
      </label>

      {value.unknown && (
        <div className="mt-2 space-y-3">
          <div role="radiogroup" aria-label="Roughly when?" className="flex flex-wrap gap-2">
            <p className="w-full text-body-sm font-medium text-fg-secondary">Roughly when?</p>
            {WINDOWS.map((w) => (
              <Chip key={w} selected={value.approx === w} onClick={() => onChange({ ...value, approx: w })}>
                {APPROX_LABEL[w]}
              </Chip>
            ))}
          </div>
          <p className="flex gap-2 rounded-control bg-info-subtle p-3 text-caption text-fg-secondary">
            <Info aria-hidden="true" className="mt-px size-4 shrink-0 text-info" />
            <span>
              Without a birth time, {whose === "my" ? "your" : "their"} Moon sign, nakshatra and dasha periods can be off (the Moon moves about 13° a day). Houses and the ascendant aren't shown.
            </span>
          </p>
        </div>
      )}

      {error && (
        <p id={msgId} className="mt-2 flex items-start gap-1.5 text-caption text-danger">
          <AlertCircle aria-hidden="true" className="mt-px size-4 shrink-0" />
          {error}
        </p>
      )}
    </fieldset>
  );
}
