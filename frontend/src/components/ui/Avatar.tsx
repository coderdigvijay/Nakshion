import { useState } from "react";
import { Sparkles } from "lucide-react";
import { cn } from "../../lib/utils";
import { initials } from "../../lib/format";

// COMPONENTS.md → Avatar.
const SIZES = {
  xs: "size-6 text-overline",
  sm: "size-8 text-caption",
  md: "size-10 text-[0.9375rem]",
  lg: "size-14 text-xl",
  xl: "size-24 text-[2rem] font-display",
} as const;

export interface AvatarProps {
  name?: string | null;
  src?: string | null;
  size?: keyof typeof SIZES;
  /** Set when the name is printed next to the avatar. */
  decorative?: boolean;
  className?: string;
}

export function Avatar({ name, src, size = "md", decorative, className }: AvatarProps) {
  const [failed, setFailed] = useState(false);
  const label = decorative ? undefined : name ?? undefined;
  return (
    <span
      role={decorative ? undefined : "img"}
      aria-label={label}
      aria-hidden={decorative || undefined}
      className={cn(
        "inline-flex shrink-0 items-center justify-center overflow-hidden rounded-chip bg-ai-subtle font-semibold text-ai",
        SIZES[size],
        className,
      )}
    >
      {src && !failed ? (
        <img src={src} alt="" className="size-full object-cover" referrerPolicy="no-referrer" onError={() => setFailed(true)} />
      ) : (
        initials(name) || "·"
      )}
    </span>
  );
}

export function AiAvatar({ size = "sm", streaming, className }: { size?: "sm" | "md" | "lg"; streaming?: boolean; className?: string }) {
  return (
    <span
      aria-hidden="true"
      className={cn(
        "inline-flex shrink-0 items-center justify-center rounded-chip bg-ai-fill text-on-ai",
        size === "sm" && "size-8 [&_svg]:size-4",
        size === "md" && "size-10 [&_svg]:size-5",
        size === "lg" && "size-14 [&_svg]:size-7",
        streaming && "shadow-glow-ai",
        className,
      )}
    >
      <Sparkles />
    </span>
  );
}
