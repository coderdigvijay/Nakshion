# Landing (`/`) — overrides MASTER where stated

**User goal:** "Is this real astrology or a gimmick — and how fast can I see *my* chart?"
**Primary action (gold, one):** `Get your free chart` → `/auth?next=/onboarding`.
**Secondary:** `Sign in` (ghost, header).
**Overrides:** ambient motion allowed here only (twinkle, slow orbit); `text-display` allowed; `surface-glass` cards allowed over the hero art.

## Structure (mobile-first)

| # | Section | 375px | ≥768 | ≥1024 |
|---|---|---|---|---|
| 0 | Marketing header (64px, `surface-glass` once scrolled > 8px) | logo + `Sign in` ghost sm | + primary sm | same, `max-w-app` |
| 1 | **Hero** | Overline "Vedic astrology · Swiss Ephemeris precision" → `text-display` "Your sky, read with care." (gold-to-cream gradient allowed on "care." only) → `text-body-lg fg-secondary` 2 lines → primary lg full-width → caption "Free · No card · 60 seconds" → hero art (zodiac portrait or kundali) below, 4:5, max-h 360 | 2-col 7/5 | 6/6, min-h `min(88svh, 820px)` |
| 2 | **Proof strip** | 3 stats in a row, `text-title tabular` + 13px caption: "Sidereal (Lahiri) charts", "Answers in English · हिंदी · Hinglish", "Grounded in classical texts" | — | — |
| 3 | **How it works** (3 steps) | vertical: number in 32px `accent-subtle` circle → title → 1 line | 3-col | 3-col |
| 4 | **Live sample** — the differentiator | A static, real-looking ChartWheel (`thumbnail` 240px) beside a sample AI answer (ChatMessage AI layout with grounding badges). Caption "Example for a sample chart". | 2-col | 2-col |
| 5 | **Explore the signs** (ZodiacCards) | Swiper carousel, cards 240×300, portrait art (AVIF), sign name `text-title`, element Badge, Sanskrit name; `slidesPerView: 1.3`, free mode, keyboard + a11y module on | 2.5 per view | 4 per view, arrows as IconButtons |
| 6 | **Trust & privacy** | 3 short rows with icons: "Your birth data stays yours", "Delete anytime", "Not a substitute for medical/financial advice" | 3-col | 3-col |
| 7 | **Final CTA** | `feature` card: h2 + primary | — | — |
| 8 | Footer | stacked groups, 44px links | 4-col | 4-col |

Section rhythm: 64 / 96 / 128px.

## Rules specific to landing
- Hero copy is **sentence case** (today: all-caps "DECODE YOUR FUTURE WITH AI-POWERED ASTROLOGY" in extrabold — remove).
- Exactly one gold button above the fold. The current second hero button "EXPLORE BIRTH CHART" has no action — delete or make it a ghost link to section 4.
- Hero background: today a 2.4 MB PNG full-bleed behind text. Replace with: `bg-night` + `starfield` (`animate-twinkle` with 3 layers at 5s/7s/9s offsets) + one optimised art image (AVIF ≤ 120 KB, `fetchpriority="high"`, explicit dimensions) placed *beside* the copy, not under it.
- Optional ambient: a 1px `border-strong` orbit ring (420px) behind the art, `animate-spin-slow` (24 s). Disabled in reduced motion.
- No auto-playing carousel.
- LCP target ≤ 2.5 s on Moto G-class 4G; hero text is the LCP element, not the image.

## States
- Logged-in visitor: header CTA becomes `Open Nakshion` → `/dashboard`; hero CTA same.

## Acceptance
- 375px: headline ≤ 4 lines, CTA visible without scroll on 667px-tall screens.
- Lighthouse a11y ≥ 95; no `<Link><Button>` nesting.
