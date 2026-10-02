import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { AlertTriangle, Check, CheckCircle2 } from "lucide-react";
import { AuthLayout } from "../components/auth/AuthLayout";
import { GoogleButton, OrDivider } from "../components/auth/SocialLogin";
import { LoginForm } from "../components/auth/LoginForm";
import { SignUpForm } from "../components/auth/SignUpForm";
import { TabPanel, Tabs } from "../components/ui/Tabs";

type Mode = "login" | "signup";

export default function AuthPage() {
  const [params, setParams] = useSearchParams();
  const [googleConsent, setGoogleConsent] = useState(false);
  const mode: Mode = params.get("mode") === "signup" ? "signup" : "login";
  const next = params.get("next") ?? undefined;
  const deleted = params.get("deleted") === "1";
  const expired = params.get("expired") === "1";

  return (
    <AuthLayout>
      {expired && (
        <p role="status" className="mb-5 flex items-start gap-2 rounded-control bg-warning-subtle p-3 text-body-sm text-fg">
          <AlertTriangle aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-warning" />
          Your session expired. Please sign in again.
        </p>
      )}
      {deleted && (
        <p role="status" className="mb-5 flex items-start gap-2 rounded-control bg-success-subtle p-3 text-body-sm text-fg">
          <CheckCircle2 aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-success" />
          Your account was deleted. Everything linked to it has been removed.
        </p>
      )}
      <h1 className="text-h2 text-fg">{mode === "login" ? "Welcome back" : "Create your account"}</h1>
      <p className="mt-2 text-body-sm text-fg-secondary">
        {mode === "login" ? "Sign in to see today's reading and ask about your chart." : "Free. Your chart in about a minute."}
      </p>
      <Tabs<Mode>
        className="mt-6"
        idBase="auth"
        label="Sign in or sign up"
        value={mode}
        onChange={(m) => {
          const p = new URLSearchParams(params);
          p.set("mode", m);
          setParams(p, { replace: true });
        }}
        items={[
          { value: "login", label: "Sign in" },
          { value: "signup", label: "Sign up" },
        ]}
      />
      <TabPanel idBase="auth" value={mode} className="pt-6">
        <GoogleButton termsAccepted={mode === "signup" && googleConsent} disabled={mode === "signup" && !googleConsent} />
        {mode === "signup" && (
          <label className="mt-3 flex min-h-11 cursor-pointer items-start gap-3 py-1.5">
            <span className="relative mt-0.5 inline-flex size-5 shrink-0">
              <input
                type="checkbox"
                checked={googleConsent}
                onChange={(e) => setGoogleConsent(e.target.checked)}
                className="peer focus-ring size-5 cursor-pointer appearance-none rounded-[6px] border border-border-strong bg-field checked:border-ai checked:bg-ai-fill"
              />
              <Check aria-hidden="true" className="pointer-events-none absolute inset-0.5 size-4 text-on-ai opacity-0 peer-checked:opacity-100" />
            </span>
            <span className="text-body-sm text-fg-secondary">
              To sign up with Google, tick to agree to the{" "}
              <Link to="/terms" target="_blank" rel="noopener" className="focus-ring rounded-[4px] text-accent-text underline underline-offset-4">Terms<span className="sr-only"> (opens in a new tab)</span></Link>{" "}
              and{" "}
              <Link to="/privacy" target="_blank" rel="noopener" className="focus-ring rounded-[4px] text-accent-text underline underline-offset-4">Privacy Policy<span className="sr-only"> (opens in a new tab)</span></Link>
              , and confirm you are 18 or older.
            </span>
          </label>
        )}
        <OrDivider />
        {mode === "login" ? <LoginForm next={next} /> : <SignUpForm />}
      </TabPanel>
    </AuthLayout>
  );
}
