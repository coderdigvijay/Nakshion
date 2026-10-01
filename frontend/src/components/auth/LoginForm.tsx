import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { AlertCircle } from "lucide-react";
import { Input } from "../ui/Field";
import { Button } from "../ui/Button";
import { useAuthStore } from "../../store/authStore";

const schema = z.object({
  email: z.string().trim().email("Enter a valid email address."),
  password: z.string().min(1, "Enter your password."),
});
type FormData = z.infer<typeof schema>;

export function LoginForm({ next }: { next?: string }) {
  const navigate = useNavigate();
  const login = useAuthStore((s) => s.login);
  const [error, setError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema), mode: "onTouched" });

  const onSubmit = handleSubmit(async (data) => {
    setError(null);
    try {
      const user = await login(data.email, data.password);
      // Gap G-03: unverified users go to /verify first.
      if (user && !user.email_verified) navigate("/verify", { replace: true });
      else navigate(next && next.startsWith("/") ? next : "/dashboard", { replace: true });
    } catch (err) {
      // Errors persist inline (PRD §7.2); entered values are kept.
      setError(err instanceof Error ? err.message : "Sign in failed. Please try again.");
    }
  });

  return (
    <form className="space-y-5" onSubmit={onSubmit} noValidate>
      <Input label="Email" type="email" autoComplete="email" inputMode="email" error={errors.email?.message} {...register("email")} />
      <Input
        label="Password"
        type="password"
        autoComplete="current-password"
        labelRight={
          <Link to="/forgot-password" className="focus-ring inline-flex min-h-11 items-center rounded-[4px] text-body-sm font-medium text-ai underline-offset-4 hover:underline md:min-h-0">
            Forgot password?
          </Link>
        }
        error={errors.password?.message}
        {...register("password")}
      />
      {error && (
        <p role="alert" className="flex items-start gap-2 rounded-control bg-danger-subtle p-3 text-body-sm text-fg">
          <AlertCircle aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-danger" />
          {error}
        </p>
      )}
      <Button type="submit" variant="primary" fullWidth size="lg" loading={isSubmitting} loadingLabel="Signing in">
        Sign in
      </Button>
    </form>
  );
}
