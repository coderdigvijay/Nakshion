import { useEffect, useState } from "react";
import { cn } from "../../lib/utils";

// COMPONENTS.md → Skeleton. Blocks are aria-hidden; the container announces the loading state.

export function Skeleton({ className }: { className?: string }) {
  return <div aria-hidden="true" className={cn("skeleton rounded-[4px]", className)} />;
}

export function SkeletonText({ lines = 3, className }: { lines?: number; className?: string }) {
  return (
    <div aria-hidden="true" className={cn("space-y-2.5", className)}>
      {Array.from({ length: lines }, (_, i) => (
        <div key={i} className={cn("skeleton h-3 rounded-[4px]", i === lines - 1 ? "w-3/5" : "w-full")} />
      ))}
    </div>
  );
}

/**
 * Loading region: aria-busy + sr-only label; after 8 s adds the honest "still working" caption.
 */
export function LoadingRegion({
  label,
  children,
  className,
}: {
  label: string;
  children: React.ReactNode;
  className?: string;
}) {
  const [slow, setSlow] = useState(false);
  useEffect(() => {
    const t = setTimeout(() => setSlow(true), 8000);
    return () => clearTimeout(t);
  }, []);
  return (
    <div aria-busy="true" className={className}>
      <span role="status" className="sr-only">
        {label}
      </span>
      {children}
      {slow && <p className="mt-4 text-center text-caption text-fg-muted">Still working — the stars take a moment.</p>}
    </div>
  );
}
