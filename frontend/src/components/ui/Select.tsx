import { forwardRef, useId } from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "../../lib/utils";
import { FieldLabel, FieldMessage } from "./Field";
import { controlStyles } from "./styles";

// COMPONENTS.md → Select. Native <select> by default: best mobile pickers and free a11y.

export interface SelectOption {
  value: string;
  label: string;
}

export interface SelectProps extends Omit<React.SelectHTMLAttributes<HTMLSelectElement>, "children"> {
  label: string;
  options: SelectOption[];
  hint?: React.ReactNode;
  error?: string;
  hideLabel?: boolean;
  placeholder?: string;
  containerClassName?: string;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { label, options, hint, error, hideLabel, placeholder, id, className, containerClassName, ...props },
  ref,
) {
  const autoId = useId();
  const sid = id ?? autoId;
  const msgId = `${sid}-msg`;
  return (
    <div className={containerClassName}>
      {hideLabel ? (
        <label htmlFor={sid} className="sr-only">
          {label}
        </label>
      ) : (
        <FieldLabel htmlFor={sid}>{label}</FieldLabel>
      )}
      <div className="relative">
        <select
          ref={ref}
          id={sid}
          aria-invalid={error ? true : undefined}
          aria-describedby={error || hint ? msgId : undefined}
          className={cn(
            controlStyles,
            "h-12 cursor-pointer appearance-none pl-4 pr-11",
            error ? "border-danger" : "border-border-strong",
            className,
          )}
          {...props}
        >
          {placeholder && (
            <option value="" disabled>
              {placeholder}
            </option>
          )}
          {options.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <ChevronDown aria-hidden="true" className="pointer-events-none absolute right-3.5 top-1/2 size-5 -translate-y-1/2 text-fg-muted" />
      </div>
      <FieldMessage id={msgId} error={error} hint={hint} />
    </div>
  );
});
