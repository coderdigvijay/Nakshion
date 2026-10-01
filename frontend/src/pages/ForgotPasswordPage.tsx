import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { ArrowLeft, CheckCircle2 } from "lucide-react";
import { AuthLayout } from "../components/auth/AuthLayout";
import { Button, ButtonLink } from "../components/ui/Button";
import { Input } from "../components/ui/Field";
import { authService } from "../services/auth";
import { toApiError } from "../services/errors";

const schema = z.object({ email: z.string().trim().email("Enter a valid email address.") });
type FormData = z.infer<typeof schema>;

export default function ForgotPasswordPage() {
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema), mode: "onTouched" });

  const onSubmit = handleSubmit(async (d) => {
    setError(null);
    try {
      await authService.forgotPassword(d.email);
      setSent(true);
    } catch (err) {
      setError(toApiError(err).detail);
    }
  });

  return (
    <AuthLayout>
      {sent ? (
        <div className="text-center" role="status">
          <CheckCircle2 aria-hidden="true" className="mx-auto size-12 text-success" />
          <h1 className="mt-4 text-h2 text-fg">Check your email</h1>
          <p className="mt-2 text-body-sm text-fg-secondary">If an account exists for that email, a reset link is on its way. It works for one hour.</p>
          <ButtonLink to="/auth" variant="secondary" className="mt-6" leadingIcon={<ArrowLeft aria-hidden="true" className="size-4" />}>
            Back to sign in
          </ButtonLink>
        </div>
      ) : (
        <>
          <h1 className="text-h2 text-fg">Reset your password</h1>
          <p className="mt-2 text-body-sm text-fg-secondary">Enter your email and we'll send you a reset link.</p>
          <form onSubmit={onSubmit} noValidate className="mt-6 space-y-5">
            <Input label="Email" type="email" autoComplete="email" error={errors.email?.message ?? error ?? undefined} {...register("email")} />
            <Button type="submit" variant="primary" fullWidth size="lg" loading={isSubmitting} loadingLabel="Sending">
              Send reset link
            </Button>
          </form>
          <ButtonLink to="/auth" variant="ghost" size="sm" className="mt-4" leadingIcon={<ArrowLeft aria-hidden="true" className="size-4" />}>
            Back to sign in
          </ButtonLink>
        </>
      )}
    </AuthLayout>
  );
}
