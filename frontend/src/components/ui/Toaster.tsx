import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { AlertCircle, AlertTriangle, CheckCircle2, Info, X } from "lucide-react";
import { useToastStore, type ToastItem, type ToastTone } from "../../store/toastStore";
import { IconButton } from "./IconButton";
import { dur, ease } from "../../lib/motion";
import { cn } from "../../lib/utils";

// COMPONENTS.md → Toast. Errors never auto-dismiss; timers pause on hover/focus.

const TIMING: Record<ToastTone, number | null> = { success: 4000, info: 5000, warning: 7000, error: null };
const ICON: Record<ToastTone, React.ReactNode> = {
  success: <CheckCircle2 className="text-success" />,
  info: <Info className="text-info" />,
  warning: <AlertTriangle className="text-warning" />,
  error: <AlertCircle className="text-danger" />,
};

function ToastCard({ t }: { t: ToastItem }) {
  const dismiss = useToastStore((s) => s.dismiss);
  const [paused, setPaused] = useState(false);
  const remaining = useRef(TIMING[t.tone]);

  useEffect(() => {
    if (remaining.current === null || paused) return;
    const started = Date.now();
    const timer = setTimeout(() => dismiss(t.id), remaining.current);
    return () => {
      clearTimeout(timer);
      if (remaining.current !== null) remaining.current -= Date.now() - started;
    };
  }, [paused, dismiss, t.id]);

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0, transition: { duration: dur.base, ease: ease.enter } }}
      exit={{ opacity: 0, transition: { duration: dur.fast, ease: ease.exit } }}
      role={t.tone === "error" ? "alert" : "status"}
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      onFocus={() => setPaused(true)}
      onBlur={() => setPaused(false)}
      className="pointer-events-auto flex w-[min(360px,calc(100vw-32px))] items-start gap-3 rounded-card border border-border bg-overlay p-4 shadow-e2"
    >
      <span aria-hidden="true" className="mt-0.5 [&_svg]:size-5">
        {ICON[t.tone]}
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-[0.9375rem] font-semibold text-fg">{t.title}</p>
        {t.body && <p className="mt-0.5 text-body-sm text-fg-secondary">{t.body}</p>}
      </div>
      <IconButton aria-label="Dismiss notification" size="sm" onClick={() => dismiss(t.id)} className="-mr-1 -mt-1">
        <X aria-hidden="true" />
      </IconButton>
    </motion.div>
  );
}

export function Toaster() {
  const toasts = useToastStore((s) => s.toasts);
  return (
    <section
      aria-label="Notifications"
      className={cn(
        "pointer-events-none fixed z-[70] flex flex-col gap-2",
        "left-1/2 top-[calc(4.5rem+env(safe-area-inset-top))] -translate-x-1/2 items-center",
        "md:left-auto md:right-6 md:top-auto md:bottom-6 md:translate-x-0 md:items-end",
      )}
    >
      <AnimatePresence initial={false}>
        {toasts.map((t) => (
          <ToastCard key={t.id} t={t} />
        ))}
      </AnimatePresence>
    </section>
  );
}
