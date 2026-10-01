import { forwardRef, useId, useState } from "react";
import { AlertCircle, Eye, EyeOff } from "lucide-react";
import { cn } from "../../lib/utils";
import { controlStyles } from "./styles";

// COMPONENTS.md → Input / Field. Sentence-case labels, 16px input text, visible focus.


export function FieldLabel({
  htmlFor,
  children,
  optional,
  right,
  id,
}: {
  htmlFor?: string;
  children: React.ReactNode;
  optional?: boolean;
  right?: React.ReactNode;
  id?: string;
}) {
  return (
    <div className="mb-2 flex items-center justify-between gap-3">
      <label id={id} htmlFor={htmlFor} className="text-body-sm font-medium text-fg-secondary">
        {children}
        {optional && <span className="ml-1.5 font-normal text-fg-muted">Optional</span>}
      </label>
      {right}
    </div>
  );
}

export function FieldMessage({ id, error, hint }: { id: string; error?: string; hint?: React.ReactNode }) {
  if (error) {
    return (
      <p id={id} className="mt-1.5 flex items-start gap-1.5 text-caption text-danger">
        <AlertCircle aria-hidden="true" className="mt-px size-4 shrink-0" />
        <span>{error}</span>
      </p>
    );
  }
  if (hint) {
    return (
      <p id={id} className="mt-1.5 text-caption text-fg-muted">
        {hint}
      </p>
    );
  }
  return null;
}

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label: string;
  hint?: React.ReactNode;
  error?: string;
  optional?: boolean;
  labelRight?: React.ReactNode;
  prefixIcon?: React.ReactNode;
  suffix?: React.ReactNode;
  /** Visually hide the label (still read by screen readers). */
  hideLabel?: boolean;
  containerClassName?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { label, hint, error, optional, labelRight, prefixIcon, suffix, hideLabel, id, type = "text", className, containerClassName, ...props },
  ref,
) {
  const autoId = useId();
  const inputId = id ?? autoId;
  const msgId = `${inputId}-msg`;
  const [show, setShow] = useState(false);
  const isPassword = type === "password";
  const hasSuffix = isPassword || !!suffix;

  return (
    <div className={containerClassName}>
      {hideLabel ? (
        <label htmlFor={inputId} className="sr-only">
          {label}
        </label>
      ) : (
        <FieldLabel htmlFor={inputId} optional={optional} right={labelRight}>
          {label}
        </FieldLabel>
      )}
      <div className="relative">
        {prefixIcon && (
          <span aria-hidden="true" className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-fg-muted [&_svg]:size-5">
            {prefixIcon}
          </span>
        )}
        <input
          ref={ref}
          id={inputId}
          type={isPassword && show ? "text" : type}
          aria-invalid={error ? true : undefined}
          aria-describedby={error || hint ? msgId : undefined}
          aria-required={optional ? undefined : props.required}
          className={cn(
            controlStyles,
            "h-12 px-4",
            prefixIcon && "pl-11",
            hasSuffix && "pr-12",
            error ? "border-danger focus:border-danger focus:ring-danger/25" : "border-border-strong",
            className,
          )}
          {...props}
        />
        {isPassword ? (
          <button
            type="button"
            onClick={() => setShow((v) => !v)}
            aria-pressed={show}
            aria-controls={inputId}
            aria-label={show ? "Hide password" : "Show password"}
            className="focus-ring absolute right-1 top-1/2 inline-flex size-10 -translate-y-1/2 cursor-pointer items-center justify-center rounded-control text-fg-muted hover:bg-elevated hover:text-fg"
          >
            {show ? <EyeOff aria-hidden="true" className="size-5" /> : <Eye aria-hidden="true" className="size-5" />}
          </button>
        ) : (
          suffix && <span className="absolute right-3.5 top-1/2 flex -translate-y-1/2 items-center text-fg-muted">{suffix}</span>
        )}
      </div>
      <FieldMessage id={msgId} error={error} hint={hint} />
    </div>
  );
});

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label: string;
  hint?: React.ReactNode;
  error?: string;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(function Textarea(
  { label, hint, error, id, className, ...props },
  ref,
) {
  const autoId = useId();
  const tid = id ?? autoId;
  const msgId = `${tid}-msg`;
  return (
    <div>
      <FieldLabel htmlFor={tid}>{label}</FieldLabel>
      <textarea
        ref={ref}
        id={tid}
        aria-invalid={error ? true : undefined}
        aria-describedby={error || hint ? msgId : undefined}
        className={cn(controlStyles, "min-h-24 px-4 py-3", error ? "border-danger" : "border-border-strong", className)}
        {...props}
      />
      <FieldMessage id={msgId} error={error} hint={hint} />
    </div>
  );
});
