import { useEffect, useId, useRef } from "react";
import { X } from "lucide-react";
import { cn } from "../../lib/utils";
import { IconButton } from "./IconButton";

// COMPONENTS.md → Dialog & Sheet. Native <dialog> + showModal(): free focus trap, inert background,
// Esc to close. Focus returns to the trigger on close (browser behaviour for showModal).

export interface DialogProps {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: React.ReactNode;
  children?: React.ReactNode;
  footer?: React.ReactNode;
  /** "auto" = sheet below 640px, dialog above. */
  presentation?: "auto" | "dialog" | "sheet";
  size?: "form" | "content";
  /** Return false to keep the dialog open (e.g. unsaved changes). */
  onRequestClose?: () => boolean;
  className?: string;
}

export function Dialog({
  open,
  onClose,
  title,
  description,
  children,
  footer,
  presentation = "auto",
  size = "form",
  onRequestClose,
  className,
}: DialogProps) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  const descId = useId();

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (open && !el.open) el.showModal();
    if (!open && el.open) el.close();
  }, [open]);

  const requestClose = () => {
    if (onRequestClose && !onRequestClose()) return;
    onClose();
  };

  return (
    <dialog
      ref={ref}
      aria-labelledby={titleId}
      aria-describedby={description ? descId : undefined}
      onCancel={(e) => {
        e.preventDefault();
        requestClose();
      }}
      onClick={(e) => {
        // Click on the backdrop (the dialog element itself, outside the panel).
        if (e.target === e.currentTarget) requestClose();
      }}
      className={cn(
        "m-0 max-h-none max-w-none bg-transparent p-0 text-fg backdrop:bg-scrim",
        "open:flex fixed inset-0 h-full w-full items-end justify-center",
        presentation === "dialog" && "items-center p-4",
        presentation === "auto" && "sm:items-center sm:p-4",
      )}
    >
      <div
        className={cn(
          "flex max-h-[90dvh] w-full flex-col border border-border bg-overlay shadow-e3",
          presentation === "sheet"
            ? "motion-safe:animate-[nk-sheet-in_320ms_cubic-bezier(0.3,0,0,1.15)]"
            : presentation === "auto"
              ? "motion-safe:animate-[nk-sheet-in_320ms_cubic-bezier(0.3,0,0,1.15)] sm:motion-safe:animate-[nk-dialog-in_250ms_cubic-bezier(0.16,1,0.3,1)]"
              : "motion-safe:animate-[nk-dialog-in_250ms_cubic-bezier(0.16,1,0.3,1)]",
          presentation === "sheet" && "rounded-t-sheet",
          presentation === "dialog" && "rounded-sheet",
          presentation === "auto" && "rounded-t-sheet sm:rounded-sheet",
          presentation !== "sheet" && (size === "form" ? "sm:max-w-[560px]" : "sm:max-w-[720px]"),
          className,
        )}
      >
        {presentation !== "dialog" && (
          <div aria-hidden="true" className={cn("mx-auto mt-2 h-1 w-9 rounded-chip bg-border-strong", presentation === "auto" && "sm:hidden")} />
        )}
        <div className="flex items-start justify-between gap-3 px-5 pt-4 sm:px-6 sm:pt-6">
          <div className="min-w-0">
            <h2 id={titleId} className="font-sans text-title text-fg">
              {title}
            </h2>
            {description && (
              <div id={descId} className="mt-1 text-body-sm text-fg-secondary">
                {description}
              </div>
            )}
          </div>
          <IconButton aria-label="Close" size="sm" onClick={requestClose} className="-mr-2 -mt-1">
            <X aria-hidden="true" />
          </IconButton>
        </div>
        {children && <div className="min-h-0 flex-1 overflow-y-auto px-5 pt-4 sm:px-6">{children}</div>}
        {footer && (
          <div className="flex flex-col-reverse gap-3 px-5 pb-[calc(1.25rem+env(safe-area-inset-bottom))] pt-6 sm:flex-row sm:justify-end sm:px-6 sm:pb-6">
            {footer}
          </div>
        )}
        {!footer && <div className="pb-[calc(1.25rem+env(safe-area-inset-bottom))] sm:pb-6" />}
      </div>
    </dialog>
  );
}
