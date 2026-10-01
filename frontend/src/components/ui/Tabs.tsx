import { useId, useRef } from "react";
import { motion } from "framer-motion";
import { cn } from "../../lib/utils";
import { spring } from "../../lib/motion";

// COMPONENTS.md → Tabs & Segmented. Roving tabindex, arrow keys, Home/End.

function useRovingKeys<T extends string>(values: T[], current: T, onChange: (v: T) => void, isDisabled?: (v: T) => boolean) {
  const refs = useRef<Array<HTMLButtonElement | null>>([]);
  const onKeyDown = (e: React.KeyboardEvent) => {
    const enabled = values.filter((v) => !isDisabled?.(v));
    const idx = enabled.indexOf(current);
    let next: T | undefined;
    if (e.key === "ArrowRight" || e.key === "ArrowDown") next = enabled[(idx + 1) % enabled.length];
    else if (e.key === "ArrowLeft" || e.key === "ArrowUp") next = enabled[(idx - 1 + enabled.length) % enabled.length];
    else if (e.key === "Home") next = enabled[0];
    else if (e.key === "End") next = enabled[enabled.length - 1];
    if (next !== undefined) {
      e.preventDefault();
      onChange(next);
      refs.current[values.indexOf(next)]?.focus();
    }
  };
  return { refs, onKeyDown };
}

export interface TabItem<T extends string> {
  value: T;
  label: string;
  disabled?: boolean;
  disabledReason?: string;
}

export interface TabsProps<T extends string> {
  items: TabItem<T>[];
  value: T;
  onChange: (v: T) => void;
  label: string;
  /** Prefix for tab/panel ids; panels use `${idBase}-panel-${value}`. */
  idBase: string;
  className?: string;
}

export function Tabs<T extends string>({ items, value, onChange, label, idBase, className }: TabsProps<T>) {
  const values = items.map((i) => i.value);
  const { refs, onKeyDown } = useRovingKeys(values, value, onChange, (v) => !!items.find((i) => i.value === v)?.disabled);
  return (
    <div className={cn("border-b border-border", className)}>
      <div role="tablist" aria-label={label} className="scroll-fade-x flex gap-1 px-1" onKeyDown={onKeyDown}>
        {items.map((item, i) => {
          const active = item.value === value;
          return (
            <button
              key={item.value}
              ref={(el) => {
                refs.current[i] = el;
              }}
              id={`${idBase}-tab-${item.value}`}
              role="tab"
              type="button"
              aria-selected={active}
              aria-controls={`${idBase}-panel-${item.value}`}
              aria-disabled={item.disabled || undefined}
              title={item.disabled ? item.disabledReason : undefined}
              tabIndex={active ? 0 : -1}
              onClick={() => !item.disabled && onChange(item.value)}
              className={cn(
                "focus-ring relative min-h-11 shrink-0 cursor-pointer whitespace-nowrap px-4 text-[0.9375rem] font-medium transition-colors duration-150",
                active ? "text-fg" : "text-fg-muted hover:text-fg-secondary",
                item.disabled && "cursor-not-allowed text-fg-disabled hover:text-fg-disabled",
              )}
            >
              {item.label}
              {active && (
                <motion.span
                  layoutId={`${idBase}-indicator`}
                  transition={spring.snappy}
                  aria-hidden="true"
                  className="absolute inset-x-2 -bottom-px h-0.5 rounded-chip bg-accent"
                />
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}

export function TabPanel({ idBase, value, children, className }: { idBase: string; value: string; children: React.ReactNode; className?: string }) {
  return (
    <div
      role="tabpanel"
      id={`${idBase}-panel-${value}`}
      aria-labelledby={`${idBase}-tab-${value}`}
      tabIndex={0}
      className={cn("focus-ring rounded-control", className)}
    >
      {children}
    </div>
  );
}

export interface SegmentedProps<T extends string> {
  options: Array<{ value: T; label: string; lang?: string }>;
  value: T;
  onChange: (v: T) => void;
  label: string;
  /** Visually show the label above the control. */
  showLabel?: boolean;
  className?: string;
  size?: "sm" | "md";
}

export function Segmented<T extends string>({ options, value, onChange, label, showLabel, className, size = "md" }: SegmentedProps<T>) {
  const id = useId();
  const values = options.map((o) => o.value);
  const { refs, onKeyDown } = useRovingKeys(values, value, onChange);
  return (
    <div className={className}>
      {showLabel && (
        <p id={`${id}-label`} className="mb-2 text-body-sm font-medium text-fg-secondary">
          {label}
        </p>
      )}
      <div
        role="radiogroup"
        aria-label={showLabel ? undefined : label}
        aria-labelledby={showLabel ? `${id}-label` : undefined}
        onKeyDown={onKeyDown}
        className="inline-flex rounded-control border border-border bg-field p-1"
      >
        {options.map((o, i) => {
          const active = o.value === value;
          return (
            <button
              key={o.value}
              ref={(el) => {
                refs.current[i] = el;
              }}
              type="button"
              role="radio"
              aria-checked={active}
              tabIndex={active ? 0 : -1}
              lang={o.lang}
              onClick={() => onChange(o.value)}
              className={cn(
                "focus-ring relative cursor-pointer whitespace-nowrap rounded-[8px] px-3 font-medium transition-colors duration-150",
                size === "md" ? "min-h-11 text-body-sm md:min-h-9" : "min-h-10 text-caption md:min-h-8",
                active ? "text-fg" : "text-fg-muted hover:text-fg-secondary",
              )}
            >
              {active && (
                <motion.span
                  layoutId={`${id}-thumb`}
                  transition={spring.snappy}
                  aria-hidden="true"
                  className="absolute inset-0 rounded-[8px] bg-elevated shadow-e1"
                />
              )}
              <span className="relative">{o.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
