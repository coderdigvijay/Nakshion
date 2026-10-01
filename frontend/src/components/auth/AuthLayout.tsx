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
    </div>
  );
}
