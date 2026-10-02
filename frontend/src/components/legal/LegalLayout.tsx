import { useEffect } from "react";
import { Link } from "react-router-dom";
import { AlertTriangle, Info } from "lucide-react";
import { MarketingHeader } from "../layout/MarketingHeader";
import { Starfield } from "../layout/AppShell";
import { CONTACT_EMAIL } from "../../lib/contact";

export const LEGAL_UPDATED = "2 October 2026";

export interface LegalSection {
  id: string;
  title: string;
}

/** Shared reading shell for /privacy and /terms: draft banner, summary box, table of contents, footer links. */
export function LegalLayout({
  title,
  summary,
  sections,
  children,
}: {
  title: string;
  summary: React.ReactNode;
  sections: LegalSection[];
  children: React.ReactNode;
}) {
  useEffect(() => {
    const prev = document.title;
    document.title = `${title} · Nakshion`;
    return () => {
      document.title = prev;
    };
  }, [title]);

  return (
    <div className="relative">
      <Starfield />
      <MarketingHeader minimal />
      <main id="main" className="px-4 pb-16 pt-24 md:px-6 lg:px-8">
        <article className="mx-auto max-w-reading">
          <p
            role="note"
            className="flex items-start gap-2 rounded-control border border-warning/30 bg-warning-subtle p-3 text-body-sm font-medium text-fg"
          >
            <AlertTriangle aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-warning" />
            Draft policy — have it reviewed by a qualified lawyer before launching publicly.
          </p>
          <h1 className="mt-6 text-h1 text-fg [overflow-wrap:anywhere]">{title}</h1>
          <p className="mt-2 text-body-sm text-fg-muted">Last updated: {LEGAL_UPDATED}</p>

          <section aria-labelledby="summary-h" className="mt-6 rounded-card border border-border bg-surface p-4 md:p-5">
            <h2 id="summary-h" className="flex items-center gap-2 font-sans text-title text-fg">
              <Info aria-hidden="true" className="size-5 text-accent-text" />
              In plain words
            </h2>
            <div className="mt-2 space-y-2 text-body text-fg-secondary">{summary}</div>
          </section>

          <nav aria-label="On this page" className="mt-6">
            <h2 className="font-sans text-body-sm font-semibold text-fg">On this page</h2>
            <ol className="mt-1 columns-1 gap-8 text-body-sm sm:columns-2">
              {sections.map((s) => (
                <li key={s.id} className="break-inside-avoid">
                  <a href={`#${s.id}`} className="focus-ring inline-flex min-h-11 items-center rounded-[4px] text-accent-text underline-offset-4 hover:underline md:min-h-8">
                    {s.title}
                  </a>
                </li>
              ))}
            </ol>
          </nav>

          <div className="mt-6 space-y-10">{children}</div>

          <nav aria-label="Legal pages" className="mt-12 flex flex-wrap gap-x-6 border-t border-border pt-4 text-body-sm">
            <Link to="/privacy" className="focus-ring inline-flex min-h-11 items-center rounded-[4px] text-fg-secondary hover:text-fg">Privacy Policy</Link>
            <Link to="/terms" className="focus-ring inline-flex min-h-11 items-center rounded-[4px] text-fg-secondary hover:text-fg">Terms of Use</Link>
            <Link to="/" className="focus-ring inline-flex min-h-11 items-center rounded-[4px] text-fg-secondary hover:text-fg">Home</Link>
          </nav>
        </article>
      </main>
    </div>
  );
}

export function LegalSectionBlock({ id, title, children }: { id: string; title: string; children: React.ReactNode }) {
  return (
    <section id={id} aria-labelledby={`${id}-h`} className="scroll-mt-24">
      <h2 id={`${id}-h`} className="text-h3 text-fg [overflow-wrap:anywhere]">
        {title}
      </h2>
      <div className="mt-3 space-y-3 text-body text-fg-secondary [overflow-wrap:anywhere] [&_a]:text-accent-text [&_a]:underline [&_a]:underline-offset-4 [&_li]:pl-1 [&_ul]:list-disc [&_ul]:space-y-1.5 [&_ul]:pl-5 [&_strong]:font-semibold [&_strong]:text-fg">
        {children}
      </div>
    </section>
  );
}

/** Contact line that never hardcodes an address: falls back to a sentence if VITE_CONTACT_EMAIL is unset. */
export function ContactLine({ purpose }: { purpose: string }) {
  return CONTACT_EMAIL ? (
    <p>
      {purpose} Email <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>.
    </p>
  ) : (
    <p>
      {purpose} The operator's contact details will be published on this page before launch. Until then, use the Delete account option in your Profile for erasure requests.
    </p>
  );
}

export function Placeholder({ children }: { children: React.ReactNode }) {
  return <mark className="rounded-[4px] bg-warning-subtle px-1 font-medium text-fg">{children}</mark>;
}
