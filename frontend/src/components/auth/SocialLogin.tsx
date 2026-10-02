import { authService } from "../../services/auth";

/** Google first (PRD §7.2). Google's mark keeps its brand colours (MASTER §11 exception). */
export function GoogleButton({ termsAccepted = false, disabled = false }: { termsAccepted?: boolean; disabled?: boolean }) {
  return (
    <button
      type="button"
      onClick={() => {
        window.location.href = authService.googleOAuthUrl(termsAccepted);
      }}
      disabled={disabled}
      className="focus-ring flex min-h-12 w-full cursor-pointer items-center justify-center gap-3 rounded-control border border-border-strong bg-surface text-[0.9375rem] font-semibold text-fg transition-colors hover:bg-elevated disabled:cursor-not-allowed disabled:opacity-60"
    >
      <svg aria-hidden="true" className="size-5" viewBox="0 0 24 24">
        <path d="M12 5.04c1.9 0 3.61.65 4.95 1.93l3.71-3.71C18.41 1.3 15.42 0 12 0 7.33 0 3.28 2.67 1.25 6.57l4.13 3.21c1-2.97 3.76-5.14 6.62-5.14z" fill="#EA4335" />
        <path d="M22.75 12.27c0-.85-.08-1.68-.21-2.48H12v4.69h6.03c-.26 1.4-1.06 2.59-2.25 3.39l4.13 3.21c2.41-2.23 3.84-5.51 3.84-8.81z" fill="#4285F4" />
        <path d="M5.38 14.78c-.24-.72-.38-1.49-.38-2.28s.14-1.56.38-2.28L1.25 7c-.8 1.6-1.25 3.4-1.25 5.3s.45 3.7 1.25 5.3l4.13-3.22z" fill="#FBBC05" />
        <path d="M12 24c3.24 0 5.96-1.07 7.95-2.9l-4.13-3.21c-1.09.73-2.49 1.16-3.82 1.16-2.86 0-5.32-1.92-6.19-4.51l-4.13 3.21C3.28 21.33 7.33 24 12 24z" fill="#34A853" />
      </svg>
      Continue with Google
    </button>
  );
}

export function OrDivider() {
  return (
    <div className="my-6 flex items-center gap-3" role="separator" aria-label="or">
      <span className="h-px flex-1 bg-border" />
      <span className="text-caption text-fg-muted">or with email</span>
      <span className="h-px flex-1 bg-border" />
    </div>
  );
}
