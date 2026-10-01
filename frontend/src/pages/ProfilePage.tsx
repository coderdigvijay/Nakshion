import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { AlertTriangle, CheckCircle2, Crown, LogOut } from "lucide-react";
import { AppShell } from "../components/layout/AppShell";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import { Input } from "../components/ui/Field";
import { Avatar } from "../components/ui/Avatar";
import { Segmented } from "../components/ui/Tabs";
import { Dialog } from "../components/ui/Dialog";
import { Skeleton } from "../components/ui/Skeleton";
import { ErrorState } from "../components/ui/EmptyState";
import { ZodiacBadge } from "../components/astrology/ZodiacBadge";
import { useCharts, ownCharts, savedPeople, pickPrimaryChart, useDeleteChart, useSetPrimaryChart } from "../hooks/useCharts";
import { ChartEditDialog } from "../components/forms/ChartEditDialog";
import { useChangePassword, useDeleteAccount, useRequestDeletionCode, useSetPassword, useUpdateName, useUpdateTimezone } from "../hooks/useUser";
import { useAuthStore } from "../store/authStore";
import { usePrefsStore, type ChartFormat, type ThemePref } from "../store/prefsStore";
import { toast } from "../store/toastStore";
import { toApiError } from "../services/errors";
import { bigThree, isApproximate } from "../lib/chartModel";
import { formatCivilDate, formatTime24 } from "../lib/format";
import { canonicalTimeZone } from "../lib/astro";
import type { BirthChart, ChatLanguage } from "../types";

const SECTIONS = [
  { id: "charts", label: "Your charts" },
  { id: "preferences", label: "Preferences" },
  { id: "account", label: "Account" },
  { id: "plan", label: "Plan" },
  { id: "privacy", label: "Privacy and data" },
  { id: "danger", label: "Delete account" },
];

const nameSchema = z.object({ name: z.string().trim().min(1, "Enter your name.").max(100, "Keep it under 100 characters.") });
const pwSchema = z
  .object({
    current: z.string(),
    next: z.string().min(8, "Use at least 8 characters."),
    confirm: z.string(),
  })
  .refine((d) => d.next === d.confirm, { message: "The two passwords don't match.", path: ["confirm"] });

function SectionTitle({ id, children, icon }: { id: string; children: React.ReactNode; icon?: React.ReactNode }) {
  return (
    <h2 id={`${id}-h`} className="mb-4 flex items-center gap-2 text-h3 text-fg">
      {icon}
      {children}
    </h2>
  );
}

function NameRow() {
  const user = useAuthStore((s) => s.user);
  const [editing, setEditing] = useState(false);
  const update = useUpdateName();
  const form = useForm<z.infer<typeof nameSchema>>({ resolver: zodResolver(nameSchema), values: { name: user?.name ?? "" } });
  const onSubmit = form.handleSubmit((v) =>
    update.mutate(v.name.trim(), {
      onSuccess: () => {
        setEditing(false);
        toast.success("Saved");
      },
      onError: (err) => form.setError("name", { message: toApiError(err).detail }),
    }),
  );
  if (!editing) {
    return (
      <div className="flex flex-col gap-1 py-3 md:flex-row md:items-center">
        <p className="text-body-sm text-fg-muted md:w-[200px]">Name</p>
        <p className="flex-1 text-body text-fg">{user?.name || "—"}</p>
        <Button variant="ghost" size="sm" className="self-start" onClick={() => setEditing(true)}>
          Edit
        </Button>
      </div>
    );
  }
  return (
    <form onSubmit={onSubmit} className="space-y-3 py-3" noValidate>
      <Input label="Name" autoFocus error={form.formState.errors.name?.message} {...form.register("name")} />
      <div className="flex gap-2">
        <Button type="submit" variant="primary" size="sm" loading={update.isPending}>
          Save
        </Button>
        <Button variant="ghost" size="sm" onClick={() => setEditing(false)}>
          Cancel
        </Button>
      </div>
    </form>
  );
}

function PasswordRow() {
  const user = useAuthStore((s) => s.user);
  // [v1-add] has_password tells us which flow to show; MVP backends omit it, so default to "change".
  const [mode, setMode] = useState<"change" | "set">(user?.has_password === false ? "set" : "change");
  const [open, setOpen] = useState(false);
  const change = useChangePassword();
  const setPw = useSetPassword();
  const form = useForm<z.infer<typeof pwSchema>>({ resolver: zodResolver(pwSchema), defaultValues: { current: "", next: "", confirm: "" } });
  const pending = change.isPending || setPw.isPending;

  const onSubmit = form.handleSubmit((v) => {
    if (mode === "change" && !v.current) {
      form.setError("current", { message: "Enter your current password." });
      return;
    }
    const done = {
      onSuccess: () => {
        form.reset();
        setOpen(false);
        toast.success(mode === "change" ? "Password changed" : "Password set");
      },
      onError: (err: unknown) => {
        const e = toApiError(err);
        if (e.code === "NO_PASSWORD_SET") {
          setMode("set");
          form.setError("root", { message: "Your account uses Google sign-in. Set a password instead." });
        } else if (e.code === "INVALID_CURRENT_PASSWORD") {
          form.setError("current", { message: e.detail });
        } else {
          form.setError("root", { message: e.detail });
        }
      },
    };
    if (mode === "change") change.mutate({ current: v.current, next: v.next }, done);
    else setPw.mutate(v.next, done);
  });

  if (!open) {
    return (
      <div className="flex flex-col gap-1 py-3 md:flex-row md:items-center">
        <p className="text-body-sm text-fg-muted md:w-[200px]">Password</p>
        <p className="flex-1 text-body text-fg-secondary">{mode === "set" ? "Not set (Google sign-in)" : "••••••••"}</p>
        <Button variant="ghost" size="sm" className="self-start" onClick={() => setOpen(true)}>
          {mode === "set" ? "Set a password" : "Change password"}
        </Button>
      </div>
    );
  }
  return (
    <form onSubmit={onSubmit} className="space-y-4 py-3" noValidate>
      {mode === "change" && (
        <Input label="Current password" type="password" autoComplete="current-password" error={form.formState.errors.current?.message} {...form.register("current")} />
      )}
      <Input label="New password" type="password" autoComplete="new-password" hint="At least 8 characters." error={form.formState.errors.next?.message} {...form.register("next")} />
      <Input label="Confirm new password" type="password" autoComplete="new-password" error={form.formState.errors.confirm?.message} {...form.register("confirm")} />
      {form.formState.errors.root && (
        <p role="alert" className="text-caption text-danger">
          {form.formState.errors.root.message}
        </p>
      )}
      <div className="flex flex-wrap gap-2">
        <Button type="submit" variant="primary" size="sm" loading={pending}>
          {mode === "change" ? "Change password" : "Set password"}
        </Button>
        <Button variant="ghost" size="sm" onClick={() => setOpen(false)}>
          Cancel
        </Button>
        {mode === "change" && user?.has_password === undefined && (
          <Button variant="link" size="sm" onClick={() => setMode("set")}>
            Signed in with Google? Set a password instead
          </Button>
        )}
      </div>
    </form>
  );
}

/** U3 v1.1: typed DELETE + re-auth. Password accounts send the password; OAuth-only accounts get an emailed code. */
function DeleteAccountDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const user = useAuthStore((s) => s.user);
  const del = useDeleteAccount();
  const requestCode = useRequestDeletionCode();
  const usesPassword = user?.has_password !== false;
  const [typed, setTyped] = useState("");
  const [secret, setSecret] = useState("");
  const [codeSent, setCodeSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reset = () => {
    setTyped("");
    setSecret("");
    setCodeSent(false);
    setError(null);
    del.reset();
  };
  const close = () => {
    reset();
    onClose();
  };

  const sendCode = () => {
    setError(null);
    requestCode.mutate(undefined, {
      onSuccess: () => {
        setCodeSent(true);
        toast.success("Code sent", "Check your inbox for the 6-digit code.");
      },
      onError: (err) => setError(toApiError(err).detail),
    });
  };

  const ready = typed === "DELETE" && secret.length > 0 && (usesPassword || codeSent);
  const submit = () => {
    setError(null);
    del.mutate(usesPassword ? { password: secret } : { code: secret.trim() }, {
      onError: (err) => {
        const e = toApiError(err);
        setError(
          e.code === "REAUTH_REQUIRED"
            ? "Confirm it's you to continue."
            : e.code === "CODE_EXPIRED"
              ? "That code expired. Send a new one."
              : e.detail,
        );
      },
    });
  };

  return (
    <Dialog
      open={open}
      onClose={close}
      title="Delete your account?"
      description="Your account, every chart, conversation and compatibility report will be removed permanently."
      presentation="dialog"
      footer={
        <>
          <Button variant="secondary" onClick={close} autoFocus>
            Cancel
          </Button>
          <Button variant="danger" disabled={!ready} loading={del.isPending} onClick={submit}>
            Delete my account
          </Button>
        </>
      }
    >
      <form
        className="space-y-5"
        noValidate
        onSubmit={(e) => {
          e.preventDefault();
          if (ready) submit();
        }}
      >
        <Input label="Type DELETE to confirm" autoComplete="off" value={typed} onChange={(e) => setTyped(e.target.value)} />
        {usesPassword ? (
          <Input label="Your password" type="password" autoComplete="current-password" value={secret} onChange={(e) => setSecret(e.target.value)} />
        ) : (
          <div className="space-y-3">
            <p className="text-body-sm text-fg-secondary">Your account uses Google sign-in. We'll email a code to confirm it's you.</p>
            <Button variant="secondary" size="sm" onClick={sendCode} loading={requestCode.isPending}>
              {codeSent ? "Send a new code" : "Email me a code"}
            </Button>
            {codeSent && (
              <Input label="6-digit code" inputMode="numeric" autoComplete="one-time-code" maxLength={6} value={secret} onChange={(e) => setSecret(e.target.value.replace(/\D/g, ""))} />
            )}
          </div>
        )}
        {error && (
          <p role="alert" className="text-caption text-danger">
            {error}
          </p>
        )}
      </form>
    </Dialog>
  );
}

function TimezoneRow() {
  const user = useAuthStore((s) => s.user);
  const update = useUpdateTimezone();
  const device = canonicalTimeZone(Intl.DateTimeFormat().resolvedOptions().timeZone);
  const differs = !!user && device !== canonicalTimeZone(user.timezone);
  const [message, setMessage] = useState<string | null>(null);
  // Once changed (or refused), stay visible but locked with the reason: the zone is changeable once per 24 h.
  const [lockedReason, setLockedReason] = useState<string | null>(null);
  return (
    <div className="flex flex-col gap-1 py-3 md:flex-row md:items-start">
      <p className="text-body-sm text-fg-muted md:w-[200px]">Time zone</p>
      <div className="flex-1">
        <p className="text-body text-fg">{user?.timezone ?? "—"}</p>
        <p className="text-caption text-fg-muted">Sets when "today" starts and when your daily questions reset. Changeable once every 24 hours.</p>
        {message && (
          <p role="alert" className="mt-1 text-caption text-danger">
            {message}
          </p>
        )}
        {lockedReason && !message && <p className="mt-1 text-caption text-fg-secondary">{lockedReason}</p>}
      </div>
      {(differs || lockedReason) && (
        <Button
          variant="ghost"
          size="sm"
          className="self-start"
          loading={update.isPending}
          aria-disabled={!!lockedReason || undefined}
          title={lockedReason ?? undefined}
          onClick={() => {
            if (lockedReason) return;
            setMessage(null);
            update.mutate(device, {
              onSuccess: () => {
                toast.success("Time zone updated", device);
                setLockedReason("Updated just now. You can change it again in 24 hours.");
              },
              onError: (err) => {
                const e = toApiError(err);
                if (e.status === 429) {
                  setMessage("You can change your time zone once every 24 hours. Try again tomorrow.");
                  setLockedReason("Locked until 24 hours after your last change.");
                } else setMessage(e.detail);
              },
            });
          }}
        >
          Use {device}
        </Button>
      )}
    </div>
  );
}

export default function ProfilePage() {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const userError = useAuthStore((s) => s.userError);
  const fetchUser = useAuthStore((s) => s.fetchUser);
  const logout = useAuthStore((s) => s.logout);
  const charts = useCharts();
  const primary = pickPrimaryChart(charts.data);
  const prefs = usePrefsStore();
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [editing, setEditing] = useState<BirthChart | null>(null);
  const [chartToDelete, setChartToDelete] = useState<BirthChart | null>(null);
  const delChart = useDeleteChart();
  const setPrimary = useSetPrimaryChart();

  const own = ownCharts(charts.data);
  const people = savedPeople(charts.data);
  const onlyChart = own.length <= 1;
  const signOut = () => {
    logout();
    navigate("/", { replace: true });
  };

  const chartList = (list: BirthChart[], allowPrimary: boolean) => (
    <ul className="divide-y divide-border">
      {list.map((c) => (
                  <li key={c.id} className="flex flex-wrap items-center gap-x-3 gap-y-1 py-3">
                    <span className="min-w-0 flex-1">
                      <span className="flex flex-wrap items-center gap-2 text-[0.9375rem] font-semibold text-fg">
                        {c.name}
                        {c.is_primary && <Badge tone="accent">Primary</Badge>}
                        {!c.is_primary && c.relationship_label && c.relationship_label !== "self" && <Badge className="capitalize">{c.relationship_label}</Badge>}
                      </span>
                      <span className="block text-caption tabular text-fg-muted">
                        {formatCivilDate(c.date_of_birth)} · {c.time_of_birth ? formatTime24(c.time_of_birth) : "time unknown"} · {c.birth_place_name}
                      </span>
                    </span>
                    <Badge tone={isApproximate(c) ? "warning" : "success"}>{isApproximate(c) ? "Approximate" : "Exact time"}</Badge>
                    <span className="flex w-full flex-wrap gap-1 sm:w-auto">
                      <Button variant="ghost" size="sm" onClick={() => setEditing(c)} aria-label={`Edit ${c.name}'s chart`}>
                        Edit
                      </Button>
                      {!c.is_primary && allowPrimary && (
                        <Button
                          variant="ghost"
                          size="sm"
                          loading={setPrimary.isPending && setPrimary.variables === c.id}
                          onClick={() =>
                            setPrimary.mutate(c.id, {
                              onSuccess: () => toast.success("Primary chart changed", `${c.name} now drives your readings.`),
                              onError: (err) => {
                              const e = toApiError(err);
                              toast.error("Couldn't change the primary chart", e.code === "PRIMARY_MUST_BE_SELF" ? "Only your own chart can be primary." : e.detail);
                            },
                            })
                          }
                          aria-label={`Set ${c.name}'s chart as primary`}
                        >
                          Set as primary
                        </Button>
                      )}
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-danger"
                        disabled={c.is_primary && onlyChart}
                        title={c.is_primary && onlyChart ? "Add another chart before deleting your only one" : undefined}
                        onClick={() => setChartToDelete(c)}
                        aria-label={`Delete ${c.name}'s chart`}
                      >
                        Delete
                      </Button>
                    </span>
                  </li>
      ))}
    </ul>
  );


  return (
    <AppShell>
      <div className="mx-auto max-w-app px-4 pt-6 md:px-6 md:pt-10 lg:grid lg:grid-cols-[240px_1fr] lg:gap-12 lg:px-8">
        <nav aria-label="Profile sections" className="hidden lg:block">
          <ul className="sticky top-24 space-y-1">
            {SECTIONS.map((s) => (
              <li key={s.id}>
                <a href={`#${s.id}`} className="focus-ring flex min-h-11 items-center rounded-control px-3 text-body-sm text-fg-secondary hover:bg-elevated hover:text-fg">
                  {s.label}
                </a>
              </li>
            ))}
          </ul>
        </nav>

        <div className="max-w-reading space-y-3 md:space-y-4 lg:space-y-6">
          {/* 1 · Identity */}
          <header className="flex flex-col items-center gap-4 pb-4 text-center md:flex-row md:items-center md:text-left">
            <Avatar name={user?.name} src={user?.avatar_url} size="xl" className="hidden md:inline-flex" decorative />
            <Avatar name={user?.name} src={user?.avatar_url} size="lg" className="md:hidden" decorative />
            <div className="min-w-0">
              {user ? (
                <>
                  <h1 className="text-h2 text-fg">{user.name || "Your profile"}</h1>
                  <p className="text-body-sm text-fg-muted">{user.email}</p>
                </>
              ) : userError ? (
                <ErrorState compact error={new Error(userError)} what="your profile" onRetry={() => void fetchUser()} />
              ) : (
                <div aria-busy="true">
                  <Skeleton className="h-8 w-48" />
                  <Skeleton className="mt-2 h-3 w-40" />
                </div>
              )}
              <div className="mt-2 flex flex-wrap justify-center gap-2 md:justify-start">
                {user?.subscription_tier === "premium" ? (
                  <Badge tone="accent" icon={<Crown aria-hidden="true" />}>
                    Premium
                  </Badge>
                ) : (
                  <Badge>Free plan</Badge>
                )}
                {user?.email_verified ? (
                  <Badge tone="success" icon={<CheckCircle2 aria-hidden="true" />}>
                    Email verified
                  </Badge>
                ) : (
                  user && <Badge tone="warning">Email not verified</Badge>
                )}
              </div>
            </div>
          </header>

          {/* 2 · My charts */}
          <Card as="section" id="charts" aria-labelledby="charts-h" className="scroll-mt-24">
            <SectionTitle id="charts">Your charts</SectionTitle>
            {charts.isLoading ? (
              <div aria-busy="true" className="space-y-2">
                <Skeleton className="h-16 rounded-control" />
                <Skeleton className="h-16 rounded-control" />
              </div>
            ) : charts.isError ? (
              <ErrorState compact error={charts.error} what="your charts" onRetry={() => void charts.refetch()} />
            ) : !charts.data || charts.data.length === 0 ? (
              <p className="text-body-sm text-fg-secondary">No charts yet.</p>
            ) : (
              <>
                {chartList(own, true)}
                {people.length > 0 && (
                  <div className="mt-6">
                    <h3 className="mb-1 font-sans text-title text-fg">People you've saved</h3>
                    <p className="mb-2 text-caption text-fg-muted">Added through compatibility. They don't drive your readings.</p>
                    {chartList(people, false)}
                  </div>
                )}
              </>
            )}
            {primary && (
              <ul className="mt-4 grid grid-cols-[repeat(3,minmax(0,1fr))] gap-2 border-t border-border pt-4">
                {bigThree(primary, user?.astrology_system ?? "vedic").map((b) => (
                  <li key={b.role} className="min-w-0">
                    <ZodiacBadge variant="role" role={b.role} sign={b.sign} system={b.system} size="sm" accent={b.role === "Lagna"} />
                  </li>
                ))}
              </ul>
            )}
          </Card>

          {/* 3 · Preferences */}
          <Card as="section" id="preferences" aria-labelledby="preferences-h" className="scroll-mt-24 space-y-5">
            <SectionTitle id="preferences">Preferences</SectionTitle>
            <Segmented<ChatLanguage>
              label="Answer language"
              showLabel
              value={prefs.language}
              onChange={prefs.setLanguage}
              options={[
                { value: "english", label: "English" },
                { value: "hindi", label: "हिंदी", lang: "hi" },
                { value: "hinglish", label: "Hinglish" },
              ]}
            />
            <Segmented<ThemePref>
              label="Theme"
              showLabel
              value={prefs.theme}
              onChange={prefs.setTheme}
              options={[
                { value: "system", label: "System" },
                { value: "dark", label: "Dark" },
                { value: "light", label: "Light" },
              ]}
            />
            <Segmented<ChartFormat>
              label="Chart style"
              showLabel
              value={prefs.chartFormat}
              onChange={prefs.setChartFormat}
              options={[
                { value: "north", label: "North Indian" },
                { value: "south", label: "South Indian" },
              ]}
            />
            <p className="text-caption text-fg-muted">Saved on this device.</p>
          </Card>

          {/* 4 · Account */}
          <Card as="section" id="account" aria-labelledby="account-h" className="scroll-mt-24">
            <SectionTitle id="account">Account</SectionTitle>
            <div className="divide-y divide-border">
              <NameRow />
              <div className="flex flex-col gap-1 py-3 md:flex-row md:items-center">
                <p className="text-body-sm text-fg-muted md:w-[200px]">Email</p>
                <p className="flex-1 break-all text-body text-fg">{user?.email}</p>
              </div>
              <TimezoneRow />
              <PasswordRow />
            </div>
          </Card>

          {/* 5 · Plan */}
          <Card as="section" id="plan" aria-labelledby="plan-h" className="scroll-mt-24">
            <SectionTitle id="plan">Plan</SectionTitle>
            <p className="text-body text-fg">{user?.subscription_tier === "premium" ? "Premium" : "Free"}</p>
            {user?.quota ? (
              <div className="mt-3">
                <p className="text-body-sm text-fg-secondary">
                  {user.quota.chat_daily_limit - user.quota.chat_remaining_today} of {user.quota.chat_daily_limit} questions used today
                </p>
                <div className="mt-2 h-2 overflow-hidden rounded-chip bg-elevated">
                  <div
                    className="h-full origin-left rounded-chip bg-ai-fill"
                    style={{ transform: `scaleX(${(user.quota.chat_daily_limit - user.quota.chat_remaining_today) / Math.max(1, user.quota.chat_daily_limit)})` }}
                  />
                </div>
              </div>
            ) : (
              <p className="mt-1 text-body-sm text-fg-secondary">The free plan includes a few questions to Nakshion each day.</p>
            )}
          </Card>

          {/* 6 · Privacy */}
          <Card as="section" id="privacy" aria-labelledby="privacy-h" className="scroll-mt-24">
            <SectionTitle id="privacy">Privacy and data</SectionTitle>
            <p className="text-body-sm text-fg-secondary">
              We store your account, the birth details you enter, the charts computed from them, your conversations and compatibility reports. AI providers receive computed chart facts, not your birth details.
            </p>
          </Card>

          {/* 7 · Danger zone */}
          <Card as="section" id="danger" aria-labelledby="danger-h" className="scroll-mt-24 border-danger/30">
            <SectionTitle id="danger" icon={<AlertTriangle aria-hidden="true" className="size-5 text-danger" />}>
              Delete account
            </SectionTitle>
            <p className="text-body-sm text-fg-secondary">Permanently delete your account, charts, conversations and reports. This can't be undone.</p>
            <Button variant="secondary" className="mt-4 text-danger" onClick={() => setDeleteOpen(true)}>
              Delete account
            </Button>
          </Card>

          <div className="pt-2">
            <Button variant="ghost" leadingIcon={<LogOut aria-hidden="true" className="size-4" />} onClick={signOut}>
              Sign out
            </Button>
          </div>
        </div>
      </div>

      <ChartEditDialog chart={editing} onClose={() => setEditing(null)} />

      <Dialog
        open={!!chartToDelete}
        onClose={() => setChartToDelete(null)}
        title={`Delete ${chartToDelete?.name ?? "this"}'s chart?`}
        description="Compatibility reports that use this chart will be removed. Conversations keep their messages."
        presentation="dialog"
        footer={
          <>
            <Button variant="secondary" onClick={() => setChartToDelete(null)} autoFocus>
              Cancel
            </Button>
            <Button
              variant="danger"
              loading={delChart.isPending}
              onClick={() => {
                if (!chartToDelete) return;
                delChart.mutate(chartToDelete.id, {
                  onSuccess: () => {
                    setChartToDelete(null);
                    toast.success("Chart deleted");
                  },
                  onError: (err) => toast.error("Couldn't delete the chart", toApiError(err).detail),
                });
              }}
            >
              Delete chart
            </Button>
          </>
        }
      />

      <DeleteAccountDialog open={deleteOpen} onClose={() => setDeleteOpen(false)} />
    </AppShell>
  );
}
