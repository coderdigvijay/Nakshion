import { Navigate, useLocation } from "react-router-dom";
import { useAuthStore } from "../../store/authStore";

/** UX gate only — the backend enforces auth (coding_rules_frontend §5). */
export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const expired = useAuthStore((s) => s.sessionExpired);
  const location = useLocation();
  if (!isAuthenticated) {
    return <Navigate to={`/auth?${expired ? "expired=1&" : ""}next=${encodeURIComponent(location.pathname + location.search)}`} replace />;
  }
  return <>{children}</>;
}
