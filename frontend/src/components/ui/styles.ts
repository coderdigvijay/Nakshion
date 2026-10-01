// Shared class recipes for the hand-built primitives (kept apart from components for fast refresh).
import { cva } from "class-variance-authority";
import { cn } from "../../lib/utils";

// COMPONENTS.md → Button. One gold `primary` per view (P3); `ai` only for Ask/Send (P4).
export const buttonStyles = cva(
  [
    "focus-ring relative inline-flex items-center justify-center gap-2 rounded-control font-sans font-semibold",
    "text-balance text-center select-none cursor-pointer",
    "transition-[background-color,border-color,color,box-shadow,transform] duration-150 ease-standard",
    "active:scale-[0.98] disabled:cursor-not-allowed disabled:active:scale-100",
    "aria-disabled:cursor-not-allowed aria-disabled:active:scale-100",
  ],
  {
    variants: {
      variant: {
        primary:
          "bg-accent text-on-accent shadow-highlight hover:bg-accent-hover hover:shadow-glow-accent active:bg-accent-pressed disabled:bg-elevated disabled:text-fg-disabled disabled:shadow-none",
        secondary:
          "bg-surface text-fg border border-border-strong hover:bg-elevated disabled:bg-elevated disabled:text-fg-disabled disabled:border-border",
        ghost: "text-fg-secondary hover:bg-elevated hover:text-fg disabled:text-fg-disabled disabled:bg-transparent",
        ai: "bg-ai-fill text-on-ai hover:brightness-110 hover:shadow-glow-ai active:brightness-95 disabled:bg-elevated disabled:text-fg-disabled disabled:shadow-none",
        danger: "bg-danger-fill text-on-danger hover:brightness-110 active:brightness-95 disabled:bg-elevated disabled:text-fg-disabled",
        link: "text-ai underline-offset-4 hover:underline px-0 min-h-11 md:min-h-9",
      },
      size: {
        sm: "min-h-11 px-3 text-body-sm md:min-h-9 md:before:absolute md:before:-inset-1 md:before:content-['']",
        md: "min-h-11 px-5 text-[0.9375rem]",
        lg: "min-h-13 px-7 text-body",
      },
      fullWidth: { true: "w-full", false: "" },
    },
    compoundVariants: [{ variant: "link", class: "px-0" }],
    defaultVariants: { variant: "secondary", size: "md", fullWidth: false },
  },
);

// COMPONENTS.md → Card. Opaque, hairline-bordered; glass only over imagery (MASTER §2).
export const cardStyles = cva("rounded-card", {
  variants: {
    variant: {
      default: "bg-surface border border-border",
      raised: "bg-elevated border border-border shadow-e1",
      feature: "card-feature",
      glass: "surface-glass",
      interactive:
        "focus-ring block bg-surface border border-border transition-[border-color,box-shadow] duration-150 ease-standard hover:border-border-strong hover:shadow-e2",
    },
    padding: {
      none: "",
      md: "p-5 md:p-6",
      sm: "p-4",
    },
  },
  defaultVariants: { variant: "default", padding: "md" },
});

// COMPONENTS.md → Input / Field. 16px text, visible focus, >=3:1 boundary.
export const controlStyles = cn(
  "w-full rounded-control border bg-field text-body text-fg placeholder:text-fg-muted",
  "transition-[border-color,box-shadow] duration-150 ease-standard",
  "outline-none focus:border-ai focus:ring-4 focus:ring-ai/25",
  "disabled:bg-elevated disabled:text-fg-disabled disabled:border-border disabled:cursor-not-allowed",
  "[&:is(input):read-only]:border-dashed",
);
