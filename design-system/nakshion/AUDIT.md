# Nakshion UI Audit vs Design System v1.0

> 2026-10-01 · ui-ux-elite · Scope: `frontend/src` (React 19, Tailwind 4), static code review. No runtime screenshots were taken.
> Ranked by **severity × reach**. "Blocker" means it fails WCAG AA or can produce a wrong chart. All paths are relative to `frontend/src/`.

## Scorecard (6 pillars, 1–4)

| Pillar | Score | One-line reason |
|---|---|---|
| Clarity | 2 | Chart page stacks 10 sections; several CTAs compete or go nowhere |
| Feedback | 2 | 12 silent `catch {}` blocks; full-screen spinners; chat doesn't stream |
| Consistency | 1 | 3 conflicting design sources, ~80 raw palette classes, 6 card radii |
| Accessibility | 1 | No `focus-visible` styles anywhere; 19 sub-12px texts; nested interactive elements |
| Responsiveness | 3 | Generally mobile-aware; mobile nav is fake; 140px chart thumbnail unreadable |
| Perceived performance | 2 | 13.4 MB of images, `backdrop-blur` in 11 files, height animations |

---

## Top problems (ranked)

### 1. Text that many users can't read — BLOCKER (a11y, i18n)
- **19 usages of `text-[9px]`, `text-[10px]` or `text-[11px]`**, e.g. `pages/DashboardPage.tsx:164,191,203,208`, `components/chat/ChatInput.tsx:50,106`, `components/chat/MobileNav.tsx:28`, `components/landing/ZodiacCards.tsx:110,132,135,138,214`, `pages/ProfilePage.tsx:181`.
- **~29 opacity-faded text colours** (`text-on-surface-variant/50`, `text-outline/50`, `opacity-50` on copy). Contrast becomes unverifiable and often < 4.5:1 — e.g. `components/ui/Input.tsx:35` (placeholder `text-outline/50` ≈ 2.4:1), `components/chat/ChatInput.tsx:106` (AI disclaimer at 11px *and* 50% opacity), `pages/ChartPage.tsx:661,673`, `pages/CompatibilityPage.tsx:431`.
- **`uppercase tracking-widest` on ~45 labels and headings** (18 in `pages/ChartPage.tsx` alone, every form label via `components/ui/Input.tsx:22`). Hard to read in English and actively broken in Devanagari (tracking splits conjuncts) — while `components/chat/ChatInput.tsx:9` already offers हिंदी.
- **Fix:** MASTER §4.2 scale (12px floor, 13px for sentences), `fg-secondary`/`fg-muted` tokens instead of opacity, sentence-case labels, `:lang(hi)` rules in `tokens.css`.

### 2. Keyboard and screen-reader users get lost — BLOCKER (a11y)
- **Zero `focus-visible` styles** in the codebase; **7 `outline-none`** remove the browser ring with only a faint ring replacement or none: `components/ui/Input.tsx:36`, `components/chat/ChatInput.tsx:87`, `pages/ProfilePage.tsx:206`, `pages/CompatibilityPage.tsx:437,526`, `pages/OnboardingPage.tsx:272`, `pages/VerifyPage.tsx:204`.
- **`<Link>` wrapping `<Button>` (invalid nested interactive content, double tab stop)** in 7 places: `components/landing/Hero.tsx:38`, `components/layout/Navbar.tsx:142`, `pages/DashboardPage.tsx:235,317`, `pages/ForgotPasswordPage.tsx:90`, `pages/ResetPasswordPage.tsx:89,141`.
- Custom popups without ARIA patterns: location dropdown (`pages/OnboardingPage.tsx:262-306`, no combobox/listbox roles, no arrow-key support), language menu (`components/chat/ChatInput.tsx:45-82`, no `role="menu"`, no Esc), user menu (`components/layout/Navbar.tsx:93-140`) and mobile menu (`:160`).
- Password show/hide toggle is unreachable by keyboard (`components/ui/Input.tsx:48`, `tabIndex={-1}`).
- Chat has no `role="log"` / live region — AI replies are never announced (`pages/ChatPage.tsx`, `components/chat/ChatMessage.tsx`).
- **Fix:** `focus-ring` utility + base `:focus-visible` (in `tokens.css`); Button `as` prop; COMPONENTS.md → LocationAutocomplete, Select, ChatMessage a11y specs.

### 3. Birth-data entry invites wrong charts — BLOCKER (correctness)
- Native `type="date"` / `type="time"` for birth data: `pages/OnboardingPage.tsx:222,240`, `pages/CompatibilityPage.tsx:475,494`. On mobile this means scrolling back decades; locale order is inconsistent (D/M swaps go unnoticed); no AM/PM confirmation.
- No read-back of what was entered (no "Tuesday, 14 March 1995"), no display of the resolved timezone or coordinates after picking a place — the user can't catch a wrong "Hyderabad" (India vs Pakistan).
- The "must pick from dropdown" rule is shown as an amber hint while typing (`pages/OnboardingPage.tsx:308`, `text-amber-400`) rather than a validation error.
- "I don't know my birth time" gives no explanation of the consequence (Lagna/houses unreliable) and no approximate-time option.
- The partner form in `pages/CompatibilityPage.tsx` re-implements the onboarding form markup instead of sharing components.
- **Fix:** COMPONENTS.md → BirthDate/BirthTime pattern + LocationAutocomplete; `pages/onboarding.md` 3-step flow with review step.

### 4. Astrological glyphs render as emoji; chart labels too small — HIGH (brand, a11y)
- Zodiac and planet symbols are raw Unicode: `components/landing/ZodiacCards.tsx:7-73` (`♈…♓`), `components/astrology/KundaliChart.tsx:94-98` (`☉ ☽ ♂ ☿ ♃ ♀ ♄ ☊ ☋`), rendered at `pages/ChartPage.tsx:619,686`. On iOS and many Android builds U+2648–2653 display as **colour emoji tiles**, breaking the no-emoji rule and the palette.
- `KundaliChart.tsx` uses 9–11 viewBox units for labels (`:370,381,400,425,512,520`) and the dashboard renders it at `size={140}` (`pages/DashboardPage.tsx:259`), so planet labels come out at about **3.5px**.
- Retrograde/combust markers use raw `text-red-400` / `text-amber-400` with single letters (`pages/ChartPage.tsx:626,632,692`), so colour does all the work and "retrograde" reads as an error.
- **Fix:** MASTER §7.2 `AstroGlyph` SVG set (interim: append U+FE0E); §9.1 label minimums, a thumbnail variant with no labels; canonical Badges.

### 5. Failures are silent and loading is generic — HIGH (feedback, trust)
- **12 empty `catch {}` blocks**: `pages/DashboardPage.tsx:53,57`, `pages/ChatPage.tsx:36,56,76,94,114,145`, `pages/ChartPage.tsx:369,421`, `pages/ProfilePage.tsx:154`, `pages/VerifyPage.tsx:104`. Worst case: if the charts request fails, the dashboard tells a returning user "Your Stars Await — Create your birth chart", which reads as though their data is gone.
- Full-screen centred spinners for content with a known shape: `pages/ChartPage.tsx:451`, `pages/ChatPage.tsx:232`. Dashboard shows a skeleton *and* a spinner *and* "Loading…" text (`pages/DashboardPage.tsx:66-96`).
- Chat waits for the whole answer behind a typing indicator, with no progress copy, stop button or interrupted state.
- Hard-coded demo content (`AiComplexMessage`, "The Duality of Saturn and Jupiter") ships in a production component (`components/chat/ChatMessage.tsx:77-126`).
- **Fix:** each page spec's States section; Skeleton rules; ChatMessage state table (thinking → streaming → complete / interrupted / error).

### 6. Three conflicting design systems, and no light theme — HIGH (consistency)
- `design-system/cosmic-intelligence/MASTER.md` specifies light lavender `#FAF5FF`, Lora + Raleway and gold CTAs. `stitch_astroai_landing_page/celestial_nebula/DESIGN.md` specifies neon `#ca98ff`, Plus Jakarta + Manrope and "no 1px borders". The shipped `index.css` follows Stitch but loads Inter instead of Manrope. Nobody can tell which one is right.
- **~80 raw Tailwind palette classes** used for meaning (`text-red-400` ×29, `text-emerald-400` ×8, `text-amber-400` ×8, `bg-red-500` ×7…), plus hard-coded hex in the score gauge (`pages/CompatibilityPage.tsx:93-94`) and inline `rgba(202,152,255,…)` gradients on each page.
- 6 different radii on equivalent cards (`rounded-lg/xl/2xl/3xl`, plus `rounded-t-[2rem]` on the mobile nav).
- No light theme, and no theme preference anywhere. `index.html` hard-codes `class="dark"`.
- Neither of the shipped fonts has Devanagari, so Hindi falls back to the system font and mismatches in mixed Hinglish lines.
- **Fix:** `design-system/nakshion/` replaces both older sources; `tokens.css` legacy aliases let pages migrate one at a time.

### 7. Visual noise that costs performance — MEDIUM (perf, P1)
- `backdrop-blur` in 11 files, including every `GlassCard` (`components/ui/GlassCard.tsx:13`), mostly over a flat background where it has nothing to blur but still costs GPU on mid-range Android.
- 13 decorative `blur-[80px]` blobs, e.g. inside the onboarding card (`pages/OnboardingPage.tsx:189-190`) and the auth page (`pages/AuthPage.tsx:35-36`).
- **13.4 MB of images**: `public/images/zodiac/*.jpeg` total 11 MB (~900 KB each) and `public/images/hero-bg.png` is 2.4 MB, used as a full-bleed image *behind* the hero text (`components/landing/Hero.tsx:11`).
- Animating `height` (layout thrash): `pages/OnboardingPage.tsx:234-236`, `pages/CompatibilityPage.tsx:488-490`. These also lack `AnimatePresence`, so the exit animation never runs.
- Hero headline is extrabold, all-caps and 4 lines at 72px (`components/landing/Hero.tsx:24`). It shouts, which works against the trust a guidance product needs.
- **Fix:** MASTER §2 (glass only over imagery), §6 (no blobs), §7.3 (AVIF/WebP ≤ 90 KB), §8 (transform/opacity only).

### 8. Information architecture and dead ends — MEDIUM (clarity)
- `pages/ChartPage.tsx` (1,014 lines) stacks 10 sections vertically, about 9 screens on mobile before the dasha. → `pages/chart.md` tabbed structure.
- The dashboard's "Daily Reading" card says "Deep dive into today's planetary transits" but its "Read More" goes to `/chat` (`pages/DashboardPage.tsx:289`).
- The hero's second CTA "EXPLORE BIRTH CHART" has no handler (`components/landing/Hero.tsx:45-47`). There are two equal-weight CTAs, and one of them does nothing.
- The mobile bottom nav in chat is fake: `href="#"` items with a hard-coded active state (`components/chat/MobileNav.tsx:5-8,17-19`). Elsewhere the app has only a hamburger menu, with no persistent mobile navigation. → MASTER §5.3 five-tab bottom bar.

### 9. Smaller polish items — LOW
- Interpretation text is in italics (`pages/ChartPage.tsx:587`). Long italic text is tiring to read, and Devanagari has no italic.
- `hover:scale-105` on CTAs (`components/landing/Hero.tsx:41`, `components/chat/ChatInput.tsx:99`) causes jitter.
- The dashboard greeting falls back to "User" (`pages/DashboardPage.tsx:127`). Use a neutral greeting instead.
- The 11px AI disclaimer is the most important trust copy in chat, and it is the least legible text on the page.

---

## Migration order (suggested)
1. Install `tokens.css` + fonts + `MotionConfig` (no visual regressions thanks to the legacy aliases).
2. Rebuild `components/ui/` primitives (Button with `as`, Field/Input, Select, Card, Badge, Chip, Skeleton, EmptyState, Dialog, Toast). This fixes issues 1–2 across every page at once.
3. Onboarding (issue 3) → Dashboard (5) → Chat (2, 5) → Chart (4, 8) → Compatibility → Profile → Landing (7).
4. `AstroGlyph` set + ChartWheel refactor.
5. Image optimisation pass (can run in parallel at any point).
6. Delete legacy aliases and `GlassCard`.
