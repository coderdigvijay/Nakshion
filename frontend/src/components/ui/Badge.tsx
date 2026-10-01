import { forwardRef } from "react";
import { Check, Sparkles } from "lucide-react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "../../lib/utils";

// COMPONENTS.md → Badge (static) & Chip (interactive).

const badgeStyles = cva(
  "inline-flex min-h-6 items-center gap-1 rounded-chip border px-2 text-overline normal-case tracking-normal font-semibold whitespace-nowrap [&_svg]:size-3.5 [&_svg]:shrink-0",
  {
    variants: {
      tone: {
        neutral: "bg-elevated text-fg-secondary border-border",
        accent: "bg-accent-subtle text-accent-text border-accent/30",
        ai: "bg-ai-subtle text-ai border-ai/30",
        success: "bg-success-subtle text-success border-success/30",
        warning: "bg-warning-subtle text-warning border-warning/30",
        danger: "bg-danger-subtle text-danger border-danger/30",
        info: "bg-info-subtle text-info border-info/30",
      },
    },
    defaultVariants: { tone: "neutral" },
  },
);

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement>, VariantProps<typeof badgeStyles> {
  icon?: React.ReactNode;
}

export function Badge({ tone, icon, className, children, ...props }: BadgeProps) {
  return (
    <span className={cn(badgeStyles({ tone }), className)} {...props}>
      {icon}
      {children}
    </span>
  );
}

export interface ChipProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  selected?: boolean;
  /** "suggestion" chips get a leading Sparkles and send on tap. */
  kind?: "choice" | "filter" | "suggestion";
  icon?: React.ReactNode;
}

export const Chip = forwardRef<HTMLButtonElement, ChipProps>(function Chip(
  { selected = false, kind = "choice", icon, className, children, type = "button", ...props },
  ref,
) {
  const roleProps =
    kind === "choice" ? { role: "radio", "aria-checked": selected } : kind === "filter" ? { "aria-pressed": selected } : {};
  return (
    <button
      ref={ref}
      type={type}
      className={cn(
        "focus-ring relative inline-flex min-h-11 shrink-0 md:min-h-9 cursor-pointer items-center gap-1.5 rounded-chip border px-3.5 text-body-sm font-medium",
        "before:absolute before:-inset-1 before:content-['']",
        "transition-colors duration-150 ease-standard [&_svg]:size-4 [&_svg]:shrink-0",
        selected
          ? "border-ai bg-ai-subtle text-fg"
          : "border-border-strong bg-surface text-fg-secondary hover:bg-elevated hover:text-fg",
        "disabled:cursor-not-allowed disabled:text-fg-disabled",
        className,
      )}
      {...roleProps}
      {...props}
    >
      {kind === "suggestion" ? <Sparkles aria-hidden="true" className="text-ai" /> : selected ? <Check aria-hidden="true" /> : icon}
      <span className="text-left">{children}</span>
    </button>
  );
});
