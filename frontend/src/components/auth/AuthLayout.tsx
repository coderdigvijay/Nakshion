import { Link } from "react-router-dom";
import { MarketingHeader } from "../layout/MarketingHeader";
import { Starfield } from "../layout/AppShell";

/** Shared shell for /auth, /verify, /forgot-password, /reset-password, /auth/callback. */
export function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative flex min-h-svh flex-col">
      <Starfield />
      <MarketingHeader minimal />
      <main id="main" className="flex flex-1 items-start justify-center px-4 pb-12 pt-24 md:items-center md:pt-20">
        <div className="w-full max-w-form rounded-sheet border border-border bg-surface p-5 shadow-e2 md:p-8">{children}</div>
      </main>
      <footer className="px-4 pb-6 text-center text-caption text-fg-muted">
        <nav aria-label="Legal" className="flex justify-center gap-x-2">
          <Link to="/privacy" className="focus-ring inline-flex min-h-11 items-center rounded-[4px] px-2 underline-offset-4 hover:text-fg hover:underline">Privacy Policy</Link>
          <Link to="/terms" className="focus-ring inline-flex min-h-11 items-center rounded-[4px] px-2 underline-offset-4 hover:text-fg hover:underline">Terms of Use</Link>
        </nav>
      </footer>
    </div>
  );
}
