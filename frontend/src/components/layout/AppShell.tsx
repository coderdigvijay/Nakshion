import { NavLink, useLocation } from "react-router-dom";
import { HeartHandshake, Sparkles, Sun } from "lucide-react";
import { cn } from "../../lib/utils";
import { useAuthStore } from "../../store/authStore";
import { Avatar } from "../ui/Avatar";
import { KundaliIcon, Logo } from "./Logo";

// MASTER §5.3: mobile bottom tab bar (Today · Chart · Ask · Match · You) + desktop top bar.

const TABS = [
  { to: "/dashboard", label: "Today", icon: <Sun aria-hidden="true" /> },
  { to: "/chart", label: "Chart", icon: <KundaliIcon /> },
  { to: "/chat", label: "Ask", icon: <Sparkles aria-hidden="true" />, ai: true },
  { to: "/compatibility", label: "Match", icon: <HeartHandshake aria-hidden="true" /> },
] as const;

function TopBar() {
  const user = useAuthStore((s) => s.user);
  return (
    <header className="fixed inset-x-0 top-0 z-30 hidden h-[var(--nk-header-h)] border-b border-border bg-bg/80 backdrop-blur-md md:block">
      <div className="mx-auto flex h-full max-w-app items-center justify-between gap-6 px-6 lg:px-8">
        <Logo to="/dashboard" />
        <nav aria-label="Main" className="flex h-full items-center gap-1">
          {TABS.map((t) => (
            <NavLink
              key={t.to}
              to={t.to}
              className={({ isActive }) =>
                cn(
                  "focus-ring relative flex h-11 items-center rounded-control px-4 text-[0.9375rem] font-medium transition-colors",
                  isActive
                    ? "text-fg after:absolute after:inset-x-4 after:-bottom-[10px] after:h-0.5 after:rounded-chip after:bg-accent"
                    : "text-fg-muted hover:text-fg-secondary",
                )
              }
            >
              {t.label}
            </NavLink>
          ))}
        </nav>
        <NavLink
          to="/profile"
          aria-label="You — profile and settings"
          className={({ isActive }) => cn("focus-ring flex items-center gap-2 rounded-chip p-0.5", isActive && "ring-2 ring-accent")}
        >
          <Avatar name={user?.name} src={user?.avatar_url} size="md" decorative />
        </NavLink>
      </div>
    </header>
  );
}

function BottomTabBar() {
  const user = useAuthStore((s) => s.user);
  const items = [
    ...TABS,
    { to: "/profile", label: "You", icon: <Avatar name={user?.name} src={user?.avatar_url} size="xs" decorative />, ai: false },
  ];
  return (
    <nav
      aria-label="Main"
      className="surface-glass fixed inset-x-0 bottom-0 z-30 border-x-0 border-b-0 pb-[env(safe-area-inset-bottom)] md:hidden"
    >
      <ul className="grid h-[var(--nk-bottom-nav-h)] grid-cols-5">
        {items.map((t) => (
          <li key={t.to}>
            <NavLink
              to={t.to}
              className={({ isActive }) =>
                cn(
                  "focus-ring relative flex h-full flex-col items-center justify-center gap-1 text-overline font-medium normal-case tracking-normal [&_svg]:size-6",
                  isActive ? "text-fg before:absolute before:inset-x-5 before:top-0 before:h-0.5 before:rounded-chip before:bg-accent" : "text-fg-muted",
                  "ai" in t && t.ai && !isActive && "[&_svg]:text-ai",
                )
              }
            >
              {t.icon}
              <span>{t.label}</span>
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}

export function Starfield({ twinkle = false }: { twinkle?: boolean }) {
  return <div aria-hidden="true" className={cn("starfield pointer-events-none fixed inset-0 -z-10", twinkle && "animate-twinkle")} />;
}

/**
 * Authenticated app chrome. `hideBottomNav` is used by chat (the composer owns the bottom edge).
 */
export function AppShell({ children, hideBottomNav = false, fullHeight = false }: { children: React.ReactNode; hideBottomNav?: boolean; fullHeight?: boolean }) {
  const { pathname } = useLocation();
  return (
    <div className={cn("relative min-h-svh", fullHeight && "h-svh overflow-hidden")}>
      <a href="#main" className="sr-only-focusable focus-ring fixed left-4 top-2 z-50 rounded-control bg-overlay px-4 py-2 text-body-sm text-fg">
        Skip to content
      </a>
      {pathname !== "/chat" && <Starfield />}
      <TopBar />
      <main
        id="main"
        className={cn(
          "motion-safe:animate-[nk-page-in_300ms_cubic-bezier(0.16,1,0.3,1)_both] md:pt-[var(--nk-header-h)]",
          !hideBottomNav && "pb-[calc(var(--nk-bottom-nav-h)+env(safe-area-inset-bottom)+24px)] md:pb-16",
          fullHeight && "h-full pb-0 md:pb-0",
        )}
      >
        {children}
      </main>
      {!hideBottomNav && <BottomTabBar />}
    </div>
  );
}
