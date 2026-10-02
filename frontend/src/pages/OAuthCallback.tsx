import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AlertCircle } from "lucide-react";
import { AuthLayout } from "../components/auth/AuthLayout";
import { Button, ButtonLink } from "../components/ui/Button";
import { Skeleton } from "../components/ui/Skeleton";
import { authService } from "../services/auth";
import { toApiError } from "../services/errors";
import { useAuthStore } from "../store/authStore";

// v1.1: the Google redirect carries a single-use `code` (60 s), never the JWT. We strip it from the
// URL at once, keep it in memory, and exchange it for the access token.
export default function OAuthCallback() {
  const navigate = useNavigate();
  const setToken = useAuthStore((s) => s.setToken);
  const fetchUser = useAuthStore((s) => s.fetchUser);
  const [initial] = useState(() => {
    const params = new URLSearchParams(window.location.search);
    return { code: params.get("code"), failed: params.get("error") };
  });
  const termsRequired = initial.failed === "terms_required";
  const [problem, setProblem] = useState<{ message: string; canRetry: boolean } | null>(
    termsRequired
      ? { message: "New here? Create your account on the Sign up tab so you can agree to the Terms and Privacy Policy first.", canRetry: false }
      : !initial.code || initial.failed
        ? { message: "Google sign-in didn't complete.", canRetry: false }
        : null,
  );
  const [busy, setBusy] = useState(!!initial.code && !initial.failed);
  const started = useRef(false);

  const exchange = useCallback(async () => {
    if (!initial.code) return;
    setBusy(true);
    setProblem(null);
    try {
      const res = await authService.oauthExchange(initial.code);
      setToken(res.data.access_token);
      const user = await fetchUser();
      if (!user) {
        setProblem({ message: "You're signed in, but we couldn't load your profile.", canRetry: true });
        return;
      }
      navigate(user.email_verified ? "/dashboard" : "/verify", { replace: true });
    } catch (err) {
      const e = toApiError(err);
      // A network failure may not have consumed the code, so retrying is worth offering;
      // 400 INVALID_OR_EXPIRED_CODE means it's gone and the user must start over.
      setProblem({
        // 4xx here (expired, reused, malformed) all mean the one-time link is unusable; never echo server text.
        message: e.status && e.status < 500 ? "That sign-in link expired. Try again." : e.detail,
        canRetry: e.network || (e.status !== undefined && e.status >= 500),
      });
    } finally {
      setBusy(false);
    }
  }, [initial.code, setToken, fetchUser, navigate]);

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    // Gap G-04: remove the code from the address bar and history immediately.
    window.history.replaceState(null, "", "/auth/callback");
    if (initial.code && !initial.failed) void exchange();
  }, [initial, exchange]);

  return (
    <AuthLayout>
      {problem ? (
        <div className="text-center" role="alert">
          <AlertCircle aria-hidden="true" className="mx-auto size-12 text-danger" />
          <h1 className="mt-4 text-h2 text-fg">{termsRequired ? "One more step" : "Sign-in didn't finish"}</h1>
          <p className="mt-2 text-body-sm text-fg-secondary">{problem.message}</p>
          <div className="mt-6 flex flex-col items-center justify-center gap-3 sm:flex-row">
            {problem.canRetry && (
              <Button variant="secondary" onClick={() => void exchange()} loading={busy}>
                Try again
              </Button>
            )}
            <ButtonLink to={termsRequired ? "/auth?mode=signup" : "/auth"} variant="primary">
              {termsRequired ? "Create your account" : "Back to sign in"}
            </ButtonLink>
          </div>
        </div>
      ) : (
        <div aria-busy="true" className="py-4">
          <p role="status" className="text-title text-fg">
            Signing you in…
          </p>
          <Skeleton className="mt-4 h-3 w-2/3" />
        </div>
      )}
    </AuthLayout>
  );
}
