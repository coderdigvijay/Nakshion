import { Link } from "react-router-dom";
import { cn } from "../../lib/utils";

/** Nakshion wordmark with a small nakshatra mark (SVG, no emoji). */
export function Logo({ to = "/", className }: { to?: string; className?: string }) {
  return (
    <Link to={to} className={cn("focus-ring inline-flex min-h-11 items-center gap-2 rounded-control", className)} aria-label="Nakshion home">
      <svg aria-hidden="true" viewBox="0 0 24 24" className="size-6 text-accent" fill="none" stroke="currentColor" strokeWidth={1.75} strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="9" className="stroke-border-strong" />
        <path d="M12 5.5l1.6 4.9 5 .1-4 3 1.5 4.9L12 15.5l-4.1 2.9 1.5-4.9-4-3 5-.1z" />
      </svg>
      <span className="font-display text-[1.25rem] font-medium tracking-tight text-fg">Nakshion</span>
    </Link>
  );
}

/** Custom kundali glyph for the Chart tab (MASTER §5.3). */
export function KundaliIcon({ className }: { className?: string }) {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth={1.75} strokeLinejoin="round">
      <rect x="3.5" y="3.5" width="17" height="17" rx="1.5" />
      <path d="M12 3.5 20.5 12 12 20.5 3.5 12Z M3.5 3.5l17 17 M20.5 3.5l-17 17" />
    </svg>
  );
}
