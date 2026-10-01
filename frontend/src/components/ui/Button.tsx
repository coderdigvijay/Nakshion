import { forwardRef } from "react";
import { Link, type LinkProps } from "react-router-dom";
import { type VariantProps } from "class-variance-authority";
import { buttonStyles } from "./styles";
import { Loader2 } from "lucide-react";
import { cn } from "../../lib/utils";

// COMPONENTS.md → Button. One gold `primary` per view (P3); `ai` only for Ask/Send (P4).

type StyleProps = VariantProps<typeof buttonStyles>;

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement>, StyleProps {
  loading?: boolean;
  /** Label announced while loading, e.g. "Saving". */
  loadingLabel?: string;
  leadingIcon?: React.ReactNode;
  trailingIcon?: React.ReactNode;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant, size, fullWidth, loading = false, loadingLabel, leadingIcon, trailingIcon, className, children, disabled, type = "button", ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      className={cn(buttonStyles({ variant, size, fullWidth }), className)}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...props}
    >
      {loading ? <Loader2 aria-hidden="true" className="size-4 animate-spin motion-reduce:animate-none" /> : leadingIcon}
      <span>{loading && loadingLabel ? loadingLabel : children}</span>
      {!loading && trailingIcon}
    </button>
  );
});

export interface ButtonLinkProps extends LinkProps, StyleProps {
  leadingIcon?: React.ReactNode;
  trailingIcon?: React.ReactNode;
}

/** A router link styled as a button. Never wrap <Link> around <Button> (AUDIT #2). */
export const ButtonLink = forwardRef<HTMLAnchorElement, ButtonLinkProps>(function ButtonLink(
  { variant, size, fullWidth, leadingIcon, trailingIcon, className, children, ...props },
  ref,
) {
  return (
    <Link ref={ref} className={cn(buttonStyles({ variant, size, fullWidth }), className)} {...props}>
      {leadingIcon}
      <span>{children}</span>
      {trailingIcon}
    </Link>
  );
});
