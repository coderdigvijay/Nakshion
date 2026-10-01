import { useEffect, useState } from "react";
import { cn } from "../../lib/utils";
import { useAuthStore } from "../../store/authStore";
import { ButtonLink } from "../ui/Button";
import { Logo } from "./Logo";

// MASTER §5.3: landing/auth get a marketing header (logo + Sign in ghost + one primary).
export function MarketingHeader({ minimal = false }: { minimal?: boolean }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header className={cn("fixed inset-x-0 top-0 z-30 h-16 transition-colors duration-150", scrolled ? "surface-glass border-x-0 border-t-0" : "border-b border-transparent")}>
      <div className="mx-auto flex h-full max-w-app items-center justify-between gap-3 px-4 md:px-6 lg:px-8">
        <Logo />
        {!minimal && (
          <div className="flex items-center gap-2">
            {isAuthenticated ? (
              <ButtonLink to="/dashboard" variant="secondary" size="sm">
                Open Nakshion
              </ButtonLink>
            ) : (
              <>
                <ButtonLink to="/auth" variant="ghost" size="sm">
                  Sign in
                </ButtonLink>
                <ButtonLink to="/auth?mode=signup" variant="secondary" size="sm" className="hidden sm:inline-flex">
                  Get your chart
                </ButtonLink>
              </>
            )}
          </div>
        )}
      </div>
    </header>
  );
}
