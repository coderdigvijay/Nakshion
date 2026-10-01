import { useSearchParams } from "react-router-dom";
import { AlertTriangle, CheckCircle2 } from "lucide-react";
import { AuthLayout } from "../components/auth/AuthLayout";
import { GoogleButton, OrDivider } from "../components/auth/SocialLogin";
import { LoginForm } from "../components/auth/LoginForm";
import { SignUpForm } from "../components/auth/SignUpForm";
import { TabPanel, Tabs } from "../components/ui/Tabs";

type Mode = "login" | "signup";

export default function AuthPage() {
  const [params, setParams] = useSearchParams();
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
        <GoogleButton />
        <OrDivider />
        {mode === "login" ? <LoginForm next={next} /> : <SignUpForm />}
      </TabPanel>
    </AuthLayout>
  );
}
