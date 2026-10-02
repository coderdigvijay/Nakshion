import { lazy, Suspense, useEffect } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MotionConfig } from "framer-motion";
import { useAuthStore } from "./store/authStore";
import { ProtectedRoute } from "./components/auth/ProtectedRoute";
import { Toaster } from "./components/ui/Toaster";
import { ConnectionBanner } from "./components/layout/ConnectionBanner";
import { ErrorBoundary } from "./components/layout/ErrorBoundary";
import { toApiError } from "./services/errors";

// Route-level code splitting (rules §6).
const LandingPage = lazy(() => import("./pages/LandingPage"));
const AuthPage = lazy(() => import("./pages/AuthPage"));
const OAuthCallback = lazy(() => import("./pages/OAuthCallback"));
const VerifyPage = lazy(() => import("./pages/VerifyPage"));
const ForgotPasswordPage = lazy(() => import("./pages/ForgotPasswordPage"));
const ResetPasswordPage = lazy(() => import("./pages/ResetPasswordPage"));
const OnboardingPage = lazy(() => import("./pages/OnboardingPage"));
const DashboardPage = lazy(() => import("./pages/DashboardPage"));
const ChatPage = lazy(() => import("./pages/ChatPage"));
const CompatibilityPage = lazy(() => import("./pages/CompatibilityPage"));
const ProfilePage = lazy(() => import("./pages/ProfilePage"));
const ChartPage = lazy(() => import("./pages/ChartPage"));
const PrivacyPage = lazy(() => import("./pages/PrivacyPage"));
const TermsPage = lazy(() => import("./pages/TermsPage"));
const NotFoundPage = lazy(() => import("./pages/NotFoundPage"));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,
      // Retry network blips and 5xx once; never retry 4xx (they won't change).
      retry: (count, err) => {
        const e = toApiError(err);
        if (e.status && e.status < 500) return false;
        return count < 1;
      },
      refetchOnWindowFocus: false,
    },
  },
});

function RouteFallback() {
  // Blank, same background — pages render their own shaped skeletons once loaded.
  return <div className="min-h-svh" aria-busy="true" />;
}

function AppRoutes() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const user = useAuthStore((s) => s.user);
  const fetchUser = useAuthStore((s) => s.fetchUser);

  useEffect(() => {
    if (isAuthenticated && !user) void fetchUser();
  }, [isAuthenticated, user, fetchUser]);

  const guard = (el: React.ReactNode) => <ProtectedRoute>{el}</ProtectedRoute>;

  return (
    <Suspense fallback={<RouteFallback />}>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/auth" element={<AuthPage />} />
        <Route path="/auth/callback" element={<OAuthCallback />} />
        <Route path="/verify" element={<VerifyPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />
        <Route path="/onboarding" element={guard(<OnboardingPage />)} />
        <Route path="/dashboard" element={guard(<DashboardPage />)} />
        <Route path="/chat" element={guard(<ChatPage />)} />
        <Route path="/compatibility" element={guard(<CompatibilityPage />)} />
        <Route path="/chart" element={guard(<ChartPage />)} />
        <Route path="/profile" element={guard(<ProfilePage />)} />
        <Route path="/privacy" element={<PrivacyPage />} />
        <Route path="/terms" element={<TermsPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </Suspense>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      {/* MASTER §8.2: honour the OS reduced-motion setting in every Framer animation. */}
      <MotionConfig reducedMotion="user">
        <BrowserRouter>
          <ConnectionBanner />
          <ErrorBoundary>
            <AppRoutes />
          </ErrorBoundary>
          <Toaster />
        </BrowserRouter>
      </MotionConfig>
    </QueryClientProvider>
  );
}
