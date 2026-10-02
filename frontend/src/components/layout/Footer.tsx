import { Link } from "react-router-dom";
import { Logo } from "./Logo";

// Landing footer. Only real destinations (the old footer had a dozen href="#" links).
export function Footer() {
  return (
    <footer className="border-t border-border">
      <div className="mx-auto grid max-w-app gap-8 px-4 py-12 md:grid-cols-4 md:px-6 lg:px-8">
        <div className="md:col-span-2">
          <Logo />
          <p className="mt-3 max-w-sm text-body-sm text-fg-secondary">
            Vedic astrology with Swiss Ephemeris precision, explained in plain words. Guidance, not certainty.
          </p>
        </div>
        <nav aria-label="Product">
          <h2 className="font-sans text-body-sm font-semibold text-fg">Product</h2>
          <ul className="mt-2 text-body-sm text-fg-secondary">
            {[
              ["/auth?mode=signup", "Get your free chart"],
              ["/auth", "Sign in"],
              ["/#how-it-works", "How it works"],
            ].map(([to, label]) => (
              <li key={to}>
                <Link to={to} className="focus-ring inline-flex min-h-11 items-center rounded-[4px] hover:text-fg">
                  {label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
        <div>
          <h2 className="font-sans text-body-sm font-semibold text-fg">Good to know</h2>
          <ul className="mt-2 text-body-sm text-fg-secondary">
            {[
              ["/privacy", "Privacy Policy"],
              ["/terms", "Terms of Use"],
              ["/terms#astrology-and-ai", "Astrology and AI"],
            ].map(([to, label]) => (
              <li key={to}>
                <Link to={to} className="focus-ring inline-flex min-h-11 items-center rounded-[4px] hover:text-fg">
                  {label}
                </Link>
              </li>
            ))}
          </ul>
          <p className="mt-1 text-caption text-fg-muted">
            Nakshion is not a substitute for medical, legal or financial advice. You can delete your account and data at any time from your profile.
          </p>
        </div>
      </div>
      <p className="border-t border-border px-4 py-6 text-center text-caption text-fg-muted">© {new Date().getFullYear()} Nakshion</p>
    </footer>
  );
}
