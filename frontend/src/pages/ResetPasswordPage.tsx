import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { AlertCircle, CheckCircle2 } from "lucide-react";
import { AuthLayout } from "../components/auth/AuthLayout";
import { Button, ButtonLink } from "../components/ui/Button";
import { Input } from "../components/ui/Field";
import { authService } from "../services/auth";
import { toApiError } from "../services/errors";

const schema = z
  .object({
    password: z
      .string()
      .min(8, "Use at least 8 characters.")
      .refine((p) => new TextEncoder().encode(p).length <= 72, "Keep the password under 72 bytes."),
    confirmPassword: z.string(),
  })
  .refine((d) => d.password === d.confirmPassword, { message: "The two passwords don't match.", path: ["confirmPassword"] });
type FormData = z.infer<typeof schema>;

export default function ResetPasswordPage() {
  const [params] = useSearchParams();
  const token = params.get("token");
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema), mode: "onTouched" });

  const onSubmit = handleSubmit(async (d) => {
    if (!token) return;
    setError(null);
    try {
      await authService.resetPassword(token, d.password);
      setDone(true);
    } catch (err) {
      setError(toApiError(err).detail);
    }
  });

  if (!token) {
    return (
      <AuthLayout>
        <div className="text-center">
          <AlertCircle aria-hidden="true" className="mx-auto size-12 text-danger" />
          <h1 className="mt-4 text-h2 text-fg">This link isn't valid</h1>
          <p className="mt-2 text-body-sm text-fg-secondary">The reset link is missing its code or has expired. Request a new one.</p>
          <ButtonLink to="/forgot-password" variant="primary" className="mt-6">
            Request a new link
          </ButtonLink>
        </div>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout>
      {done ? (
        <div className="text-center" role="status">
          <CheckCircle2 aria-hidden="true" className="mx-auto size-12 text-success" />
          <h1 className="mt-4 text-h2 text-fg">Password updated</h1>
          <p className="mt-2 text-body-sm text-fg-secondary">Sign in with your new password.</p>
          <ButtonLink to="/auth" variant="primary" className="mt-6">
            Sign in
          </ButtonLink>
        </div>
      ) : (
        <>
          <h1 className="text-h2 text-fg">Choose a new password</h1>
          <form onSubmit={onSubmit} noValidate className="mt-6 space-y-5">
            <Input label="New password" type="password" autoComplete="new-password" hint="At least 8 characters." error={errors.password?.message} {...register("password")} />
            <Input label="Confirm new password" type="password" autoComplete="new-password" error={errors.confirmPassword?.message} {...register("confirmPassword")} />
            {error && (
              <p role="alert" className="flex items-start gap-2 rounded-control bg-danger-subtle p-3 text-body-sm text-fg">
                <AlertCircle aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-danger" />
                {error}
              </p>
            )}
            <Button type="submit" variant="primary" fullWidth size="lg" loading={isSubmitting} loadingLabel="Saving">
              Save new password
            </Button>
          </form>
        </>
      )}
    </AuthLayout>
  );
}
