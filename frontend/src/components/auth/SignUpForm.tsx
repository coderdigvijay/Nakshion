import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { AlertCircle, Check } from "lucide-react";
import { FieldMessage, Input } from "../ui/Field";
import { Button } from "../ui/Button";
import { useAuthStore } from "../../store/authStore";

const schema = z
  .object({
    name: z.string().trim().min(1, "Enter your name.").max(100, "Keep it under 100 characters."),
    email: z.string().trim().email("Enter a valid email address."),
    password: z
      .string()
      .min(8, "Use at least 8 characters.")
      .refine((p) => new TextEncoder().encode(p).length <= 72, "Keep the password under 72 bytes."),
    confirmPassword: z.string(),
    consent: z.boolean().refine((v) => v === true, "Please agree to the Terms and Privacy Policy to create an account."),
  })
  .refine((d) => d.password === d.confirmPassword, { message: "The two passwords don't match.", path: ["confirmPassword"] });
type FormData = z.infer<typeof schema>;

export function SignUpForm() {
  const navigate = useNavigate();
  const registerUser = useAuthStore((s) => s.register);
  const [error, setError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema), mode: "onTouched", defaultValues: { consent: false } });

  const onSubmit = handleSubmit(async (data) => {
    setError(null);
    try {
      await registerUser(data.email, data.password, data.name.trim());
      navigate("/verify", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign up failed. Please try again.");
    }
  });

  return (
    <form className="space-y-5" onSubmit={onSubmit} noValidate>
      <Input label="Name" autoComplete="name" error={errors.name?.message} {...register("name")} />
      <Input label="Email" type="email" autoComplete="email" inputMode="email" error={errors.email?.message} {...register("email")} />
      <Input label="Password" type="password" autoComplete="new-password" hint="At least 8 characters." error={errors.password?.message} {...register("password")} />
      <Input label="Confirm password" type="password" autoComplete="new-password" error={errors.confirmPassword?.message} {...register("confirmPassword")} />
      <div>
        <label className="flex min-h-11 cursor-pointer items-start gap-3 py-1.5">
          <span className="relative mt-0.5 inline-flex size-5 shrink-0">
            <input
              type="checkbox"
              aria-invalid={errors.consent ? true : undefined}
              aria-describedby={errors.consent ? "consent-msg" : undefined}
              className="peer focus-ring size-5 cursor-pointer appearance-none rounded-[6px] border border-border-strong bg-field checked:border-ai checked:bg-ai-fill aria-[invalid=true]:border-danger"
              {...register("consent")}
            />
            <Check aria-hidden="true" className="pointer-events-none absolute inset-0.5 size-4 text-on-ai opacity-0 peer-checked:opacity-100" />
          </span>
          <span className="text-body-sm text-fg-secondary">
            By creating an account you agree to the{" "}
            <Link to="/terms" target="_blank" rel="noopener" className="focus-ring rounded-[4px] text-accent-text underline underline-offset-4">
              Terms<span className="sr-only"> (opens in a new tab)</span>
            </Link>{" "}
            and{" "}
            <Link to="/privacy" target="_blank" rel="noopener" className="focus-ring rounded-[4px] text-accent-text underline underline-offset-4">
              Privacy Policy<span className="sr-only"> (opens in a new tab)</span>
            </Link>
            , and confirm you are 18 or older.
          </span>
        </label>
        <FieldMessage id="consent-msg" error={errors.consent?.message} />
      </div>
      {error && (
        <p role="alert" className="flex items-start gap-2 rounded-control bg-danger-subtle p-3 text-body-sm text-fg">
          <AlertCircle aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-danger" />
          {error}
        </p>
      )}
      <Button type="submit" variant="primary" fullWidth size="lg" loading={isSubmitting} loadingLabel="Creating your account">
        Create account
      </Button>
    </form>
  );
}
