import { forwardRef } from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "../../lib/utils";

// COMPONENTS.md → IconButton. `aria-label` is required by the type.
const iconButtonStyles = cva(
  [
    "focus-ring relative inline-flex shrink-0 items-center justify-center cursor-pointer",
    "transition-[background-color,color,box-shadow,transform] duration-150 ease-standard active:scale-[0.96]",
    "disabled:cursor-not-allowed disabled:text-fg-disabled disabled:active:scale-100",
    "aria-disabled:cursor-not-allowed",
  ],
  {
    variants: {
      variant: {
        ghost: "text-fg-secondary hover:bg-elevated hover:text-fg",
        secondary: "bg-surface text-fg border border-border-strong hover:bg-elevated",
        primary: "bg-accent text-on-accent hover:bg-accent-hover hover:shadow-glow-accent",
        ai: "bg-ai-fill text-on-ai hover:brightness-110 hover:shadow-glow-ai aria-disabled:bg-elevated aria-disabled:text-fg-disabled aria-disabled:shadow-none aria-disabled:brightness-100",
      },
      size: {
        sm: "size-11 md:size-9 md:before:absolute md:before:-inset-1 md:before:content-[''] [&_svg]:size-4",
        md: "size-11 [&_svg]:size-5",
        lg: "size-13 [&_svg]:size-6",
      },
      round: { true: "rounded-chip", false: "rounded-control" },
    },
    defaultVariants: { variant: "ghost", size: "md", round: false },
  },
);

export interface IconButtonProps
  extends Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, "aria-label">,
    VariantProps<typeof iconButtonStyles> {
  "aria-label": string;
}

export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(function IconButton(
  { variant, size, round, className, type = "button", title, ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      title={title ?? props["aria-label"]}
      className={cn(iconButtonStyles({ variant, size, round }), className)}
      {...props}
    />
  );
});
