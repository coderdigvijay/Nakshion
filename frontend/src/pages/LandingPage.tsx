import { CalendarDays, Languages, Lock, MessageCircle, ScrollText, ShieldCheck, Sparkles, Telescope, Trash2 } from "lucide-react";
import { MarketingHeader } from "../components/layout/MarketingHeader";
import { Footer } from "../components/layout/Footer";
import { Starfield } from "../components/layout/AppShell";
import { ButtonLink } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { ChartWheel } from "../components/astrology/ChartWheel";
import { ChatMessage } from "../components/chat/ChatMessage";
import { ZodiacCards } from "../components/landing/ZodiacCards";
import { useAuthStore } from "../store/authStore";
import type { WheelData } from "../lib/chartModel";

// pages/landing.md. One gold CTA above the fold; hero text is the LCP element.

/** Static sample chart for the "live sample" section (clearly captioned as an example). */
const SAMPLE: WheelData = {
  lagnaIdx: 4,
  approximate: false,
  planets: [
    { english: "Sun", sanskrit: "Surya", abbr: "Su", key: "sun", signIdx: 1, house: 10, degree: 14.3, retrograde: false, combust: false, dignity: "neutral" },
    { english: "Moon", sanskrit: "Chandra", abbr: "Mo", key: "moon", signIdx: 1, house: 10, degree: 3.2, retrograde: false, combust: false, dignity: "exalted" },
    { english: "Mars", sanskrit: "Mangala", abbr: "Ma", key: "mars", signIdx: 7, house: 4, degree: 22.1, retrograde: false, combust: false, dignity: "own" },
    { english: "Mercury", sanskrit: "Budha", abbr: "Me", key: "mercury", signIdx: 0, house: 9, degree: 28.4, retrograde: true, combust: false, dignity: "neutral" },
    { english: "Jupiter", sanskrit: "Guru", abbr: "Ju", key: "jupiter", signIdx: 8, house: 5, degree: 9.9, retrograde: false, combust: false, dignity: "own" },
    { english: "Venus", sanskrit: "Shukra", abbr: "Ve", key: "venus", signIdx: 2, house: 11, degree: 1.5, retrograde: false, combust: false, dignity: "neutral" },
    { english: "Saturn", sanskrit: "Shani", abbr: "Sa", key: "saturn", signIdx: 10, house: 7, degree: 17.8, retrograde: true, combust: false, dignity: "own" },
    { english: "Rahu", sanskrit: "Rahu", abbr: "Ra", key: "rahu", signIdx: 5, house: 2, degree: 6.6, retrograde: true, combust: false, dignity: "neutral" },
    { english: "Ketu", sanskrit: "Ketu", abbr: "Ke", key: "ketu", signIdx: 11, house: 8, degree: 6.6, retrograde: true, combust: false, dignity: "neutral" },
  ],
};

const SAMPLE_ANSWER =
  "With your **Moon exalted in Vrishabha in the 10th house**, steady, visible work tends to feel emotionally right for you. Saturn in the 7th asks for patience in partnerships: commitments grow slowly but last.\n\n- A good window for career moves opens when Jupiter supports your 10th.\n- Let decisions settle for a day before you act.";

export default function LandingPage() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const cta = isAuthenticated
    ? { to: "/dashboard", label: "Open Nakshion" }
    : { to: "/auth?mode=signup&next=/onboarding", label: "Get your free chart" };

  return (
    <div className="relative">
      <Starfield twinkle />
      <MarketingHeader />
      <main id="main">
        {/* 1 · Hero */}
        <section className="relative overflow-hidden">
          <div className="mx-auto grid min-h-[min(88svh,820px)] max-w-app items-center gap-10 px-4 pb-16 pt-24 md:grid-cols-12 md:px-6 lg:px-8">
            <div className="md:col-span-7 lg:col-span-6">
              <p className="text-overline uppercase text-fg-muted">Vedic astrology · Swiss Ephemeris precision</p>
              <h1 className="mt-4 text-display text-fg">
                Your sky, read with{" "}
                <span className="bg-gradient-to-r from-accent to-moon bg-clip-text text-transparent">care.</span>
              </h1>
              <p className="mt-5 max-w-xl text-body-lg text-fg-secondary">
                Accurate Vedic charts and answers grounded in your own placements — in English, हिंदी or Hinglish. No generic sun-sign text.
              </p>
              <div className="mt-8 flex flex-col items-start gap-3">
                <ButtonLink to={cta.to} variant="primary" size="lg" className="w-full sm:w-auto">
                  {cta.label}
                </ButtonLink>
                <p className="text-caption text-fg-muted">Free · No card · About 60 seconds</p>
              </div>
            </div>
            <div className="relative md:col-span-5 lg:col-span-6">
              <div aria-hidden="true" className="absolute left-1/2 top-1/2 hidden size-[420px] -translate-x-1/2 -translate-y-1/2 rounded-chip border border-border-strong/40 motion-safe:animate-spin-slow lg:block" />
              <picture>
                <source srcSet="/images/zodiac/opt/leo-480.avif" type="image/avif" />
                <img
                  src="/images/zodiac/opt/leo-480.jpg"
                  alt="Leo — a lion crowned in sunlight"
                  width={480}
                  height={643}
                  fetchPriority="high"
                  decoding="async"
                  className="relative mx-auto aspect-[3/4] max-h-[360px] w-auto rounded-card border border-border object-cover shadow-e3 md:max-h-[480px]"
                />
              </picture>
            </div>
          </div>
        </section>

        {/* 2 · Proof strip */}
        <section aria-label="What makes Nakshion different" className="border-y border-border bg-surface/60">
          <ul className="mx-auto grid max-w-app gap-6 px-4 py-8 md:grid-cols-3 md:px-6 lg:px-8">
            {[
              { icon: <Telescope aria-hidden="true" />, title: "Sidereal (Lahiri) charts", body: "Computed with the Swiss Ephemeris, to the arc-minute." },
              { icon: <Languages aria-hidden="true" />, title: "English · हिंदी · Hinglish", body: "Ask in the language you think in." },
              { icon: <ScrollText aria-hidden="true" />, title: "Grounded in classical texts", body: "Answers cite the placements they rely on." },
            ].map((p) => (
              <li key={p.title} className="flex gap-3">
                <span className="text-accent-text [&_svg]:size-6">{p.icon}</span>
                <span>
                  <span className="block text-title text-fg">{p.title}</span>
                  <span className="block text-caption text-fg-secondary">{p.body}</span>
                </span>
              </li>
            ))}
          </ul>
        </section>

        {/* 3 · How it works */}
        <section id="how-it-works" aria-labelledby="how-h" className="scroll-mt-20 py-16 md:py-24">
          <div className="mx-auto max-w-app px-4 md:px-6 lg:px-8">
            <h2 id="how-h" className="text-h2 text-fg">
              How it works
            </h2>
            <ol className="mt-8 grid gap-6 md:grid-cols-3">
              {[
                { icon: <CalendarDays aria-hidden="true" />, title: "Add your birth details", body: "Date, time and place. We find the exact sky and time zone." },
                { icon: <Sparkles aria-hidden="true" />, title: "We compute the facts", body: "Planets, houses, nakshatras and dasha periods, precisely." },
                { icon: <MessageCircle aria-hidden="true" />, title: "Ask anything", body: "Nakshion explains what your chart suggests, in plain words." },
              ].map((s, i) => (
                <li key={s.title}>
                  <span className="flex size-8 items-center justify-center rounded-chip bg-accent-subtle text-body-sm font-semibold text-accent-text tabular">{i + 1}</span>
                  <h3 className="mt-3 font-sans text-title text-fg">{s.title}</h3>
                  <p className="mt-1 text-body-sm text-fg-secondary">{s.body}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        {/* 4 · Live sample */}
        <section aria-labelledby="sample-h" className="py-8 md:py-16">
          <div className="mx-auto max-w-app px-4 md:px-6 lg:px-8">
            <h2 id="sample-h" className="text-h2 text-fg">
              See the difference
            </h2>
            <p className="mt-2 text-body text-fg-secondary">Every answer starts from the chart, and says which placements it used.</p>
            <div className="mt-8 grid items-start gap-6 md:grid-cols-[240px_1fr] lg:grid-cols-[300px_1fr]">
              <ChartWheel data={SAMPLE} format="north" variant="full" title="Sample D1 chart" className="mx-auto w-full max-w-[320px]" />
              <Card>
                <ChatMessage
                  role="assistant"
                  content={SAMPLE_ANSWER}
                  citations={[
                    { factor_id: "s1", label: "Moon in Rohini" },
                    { factor_id: "s2", label: "Saturn in the 7th" },
                    { factor_id: "s3", label: "Shani Mahadasha" },
                  ]}
                />
              </Card>
            </div>
            <p className="mt-3 text-caption text-fg-muted">Example for a sample chart, not a real person.</p>
          </div>
        </section>

        {/* 5 · Signs */}
        <ZodiacCards />

        {/* 6 · Trust */}
        <section aria-labelledby="trust-h" className="py-16 md:py-24">
          <div className="mx-auto max-w-app px-4 md:px-6 lg:px-8">
            <h2 id="trust-h" className="text-h2 text-fg">
              Your data, your call
            </h2>
            <ul className="mt-8 grid gap-6 md:grid-cols-3">
              {[
                { icon: <Lock aria-hidden="true" />, title: "Your birth data stays yours", body: "AI providers see computed chart facts, not your birth details." },
                { icon: <Trash2 aria-hidden="true" />, title: "Delete anytime", body: "Remove your account and everything in it from your profile." },
                { icon: <ShieldCheck aria-hidden="true" />, title: "Guidance, not certainty", body: "Not a substitute for medical, legal or financial advice." },
              ].map((t) => (
                <li key={t.title} className="flex gap-3">
                  <span className="text-ai [&_svg]:size-6">{t.icon}</span>
                  <span>
                    <span className="block text-title text-fg">{t.title}</span>
                    <span className="block text-body-sm text-fg-secondary">{t.body}</span>
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </section>

        {/* 7 · Final CTA */}
        <section className="px-4 pb-16 md:px-6 md:pb-24 lg:px-8">
          <Card variant="feature" className="mx-auto max-w-app text-center md:p-12">
            <h2 className="text-h2 text-fg">Ready to see your chart?</h2>
            <p className="mx-auto mt-2 max-w-md text-body text-fg-secondary">It takes about a minute, and it's free.</p>
            <ButtonLink to={cta.to} variant="primary" size="lg" className="mt-6">
              {cta.label}
            </ButtonLink>
          </Card>
        </section>
      </main>
      <Footer />
    </div>
  );
}
