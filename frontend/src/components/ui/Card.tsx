import { Link, type LinkProps } from "react-router-dom";
import { type VariantProps } from "class-variance-authority";
import { cardStyles } from "./styles";
import { cn } from "../../lib/utils";

// COMPONENTS.md → Card. Opaque, hairline-bordered; glass only over imagery (MASTER §2).

export interface CardProps extends React.HTMLAttributes<HTMLElement>, VariantProps<typeof cardStyles> {
  as?: "div" | "section" | "article" | "li";
}

export function Card({ as: Tag = "div", variant, padding, className, ...props }: CardProps) {
  return <Tag className={cn(cardStyles({ variant, padding }), className)} {...props} />;
}

/** Whole card is one link (one link per card). */
export function CardLink({ className, padding, ...props }: LinkProps & { padding?: "none" | "md" | "sm" }) {
  return <Link className={cn(cardStyles({ variant: "interactive", padding }), className)} {...props} />;
}

export function CardHeader({
  overline,
  title,
  titleAs: TitleTag = "h2",
  actions,
  className,
  titleId,
}: {
  overline?: React.ReactNode;
  title: React.ReactNode;
  titleAs?: "h2" | "h3";
  actions?: React.ReactNode;
  className?: string;
  titleId?: string;
}) {
  return (
    <div className={cn("mb-4 flex items-start justify-between gap-3", className)}>
      <div className="min-w-0">
        {overline && <p className="mb-1 text-caption font-medium text-fg-muted">{overline}</p>}
        <TitleTag id={titleId} className="font-sans text-title text-fg">
          {title}
        </TitleTag>
      </div>
      {actions && <div className="flex shrink-0 items-center gap-1">{actions}</div>}
    </div>
  );
}
