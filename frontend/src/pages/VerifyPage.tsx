import { useEffect, useRef, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { CheckCircle2, MailOpen } from "lucide-react";
import { AuthLayout } from "../components/auth/AuthLayout";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Field";
import { authService } from "../services/auth";
import { toApiError } from "../services/errors";
import { useAuthStore } from "../store/authStore";
import { toast } from "../store/toastStore";

// PRD §7.2: one OTP field, inputmode numeric, one-time-code autocomplete, paste support, countdown.
export default function VerifyPage() {
  const navigate = useNavigate();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const user = useAuthStore((s) => s.user);
  const fetchUser = useAuthStore((s) => s.fetchUser);
  const [code, setCode] = useState("");
  const [verifying, setVerifying] = useState(false);
  const [resending, setResending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const lastTried = useRef("");

  useEffect(() => {
    if (cooldown <= 0) return;
    const t = setTimeout(() => setCooldown((c) => c - 1), 1000);
    return () => clearTimeout(t);
  }, [cooldown]);

  const verify = async (value: string) => {
    if (value.length !== 6 || verifying) return;
    lastTried.current = value;
    setVerifying(true);
    setError(null);
    try {
      await authService.verifyEmail(value);
      setSuccess(true);
      void fetchUser();
      setTimeout(() => navigate("/onboarding", { replace: true }), 1200);
    } catch (err) {
      setError(toApiError(err).detail);
    } finally {
      setVerifying(false);
    }
  };

  const resend = async () => {
    setResending(true);
    setError(null);
    try {
      await authService.resendOtp();
      setCooldown(60);
      toast.success("Code sent", "Check your inbox and spam folder.");
    } catch (err) {
      const e = toApiError(err);
      if (e.status === 429 && e.retryAfter) setCooldown(e.retryAfter);
      setError(e.detail);
    } finally {
      setResending(false);
    }
  };

  if (!isAuthenticated) return <Navigate to="/auth" replace />;

  return (
    <AuthLayout>
      {success ? (
        <div className="py-6 text-center" role="status">
          <CheckCircle2 aria-hidden="true" className="mx-auto size-12 text-success" />
          <h1 className="mt-4 text-h2 text-fg">Email verified</h1>
          <p className="mt-2 text-body-sm text-fg-secondary">Next, your birth details.</p>
        </div>
      ) : (
        <>
          <MailOpen aria-hidden="true" className="size-10 text-ai" />
          <h1 className="mt-4 text-h2 text-fg">Check your email</h1>
          <p className="mt-2 text-body-sm text-fg-secondary">
            We sent a 6-digit code{user?.email ? ` to ${user.email}` : ""}. It expires in 10 minutes.
          </p>
          <form
            className="mt-6 space-y-5"
            noValidate
            onSubmit={(e) => {
              e.preventDefault();
              if (code.length !== 6) setError("Enter all 6 digits of the code.");
              else void verify(code);
            }}
          >
            <Input
              label="Verification code"
              inputMode="numeric"
              autoComplete="one-time-code"
              maxLength={6}
              value={code}
              error={error ?? undefined}
              className="text-center text-[1.5rem] tracking-[0.5em] tabular"
              onChange={(e) => {
                const v = e.target.value.replace(/\D/g, "").slice(0, 6);
                setCode(v);
                setError(null);
                if (v.length === 6 && v !== lastTried.current) void verify(v);
              }}
            />
            <Button type="submit" variant="primary" fullWidth size="lg" loading={verifying} loadingLabel="Verifying">
              Verify email
            </Button>
          </form>
          <div className="mt-6 flex flex-wrap items-center justify-between gap-2">
            <p className="text-body-sm text-fg-secondary">Didn't get it?</p>
            <Button variant="ghost" size="sm" onClick={() => void resend()} disabled={cooldown > 0} loading={resending}>
              {cooldown > 0 ? (
                <span className="tabular">
                  Resend in {Math.floor(cooldown / 60)}:{String(cooldown % 60).padStart(2, "0")}
                </span>
              ) : (
                "Resend code"
              )}
            </Button>
          </div>
        </>
      )}
    </AuthLayout>
  );
}
