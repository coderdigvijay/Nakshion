# Nakshion Design System — MASTER

> **Version 1.0 · 2026-10-01 · Owner: ui-ux-elite**
> Supersedes `design-system/cosmic-intelligence/MASTER.md` (that file described a light lavender "spa" theme that was never shipped; the live app drifted to a neon-violet Stitch theme. This file reconciles both into one system.)
>
> **Resolution order:** `pages/<screen>.md` overrides → this file → `COMPONENTS.md` for component anatomy.
> **Implementation:** `tokens.css` is the single source of truth for values. If this doc and `tokens.css` disagree, `tokens.css` wins and this doc gets a bug.

| File | What it is |
|---|---|
| `MASTER.md` | Principles, foundations, tokens, data-viz rules (this file) |
| `COMPONENTS.md` | 23 component specs: anatomy, variants, states, a11y |
| `tokens.css` | Tailwind v4 `@theme` drop-in (dark default + light) — compile-tested against the repo's `tailwindcss@4` |
| `pages/*.md` | Screen layouts: landing, onboarding, dashboard, chart, chat, compatibility, profile |
| `AUDIT.md` | Current UI vs this system, ranked, with file references |

---

## 1. Brand: "The Quiet Observatory"

Nakshion (from *nakshatra*, the lunar mansion) is a Vedic astrologer that thinks in precise sky maths and speaks like a warm, patient elder. The UI should feel like **stepping onto a rooftop at night with someone who knows the sky** — not a neon casino, not a pastel spa.

**Personality:** wise · warm · precise · unhurried · bilingual.
**Not:** mystical kitsch, fortune-cookie, gamer neon, shouting caps, emoji.

### Six principles (every review cites these by number)

| # | Principle | What it means in practice |
|---|---|---|
| P1 | **Sky first, chrome last** | The chart and the reading are the hero. Cards are quiet, opaque, hairline-bordered. Decoration never competes with data. |
| P2 | **Show the maths** | Trust comes from precision: degrees `14°22′`, timezone `UTC+05:30`, coordinates, "Based on: Moon in Rohini" chips under AI answers. Never hide the inputs behind vibes. |
| P3 | **One lamp per room** | Gold (`accent`) is the lamp: exactly **one** gold primary action per view. Gold also marks Lagna, the current dasha, auspicious windows. Overuse kills its meaning. |
| P4 | **Violet is Nakshion's voice** | `ai` violet means "the AI is speaking / thinking / grounded this". It is never a generic brand decoration and never a primary CTA fill (except Send/Ask). |
| P5 | **Bilingual by default** | Every component must survive Hindi (Devanagari) strings that are ~30% longer and ~20% taller. No uppercase, no letter-spacing on Devanagari, no fixed-height text boxes. |
| P6 | **Calm motion** | Feedback is fast (150 ms); arrivals are gentle (250–400 ms); ambience is slow (2.4 s+) and lives only on the landing page. Nothing loops inside a reading area. |

### Voice (microcopy)

- Sentence case everywhere. `Generate my chart`, not `GENERATE MY CHART`.
- Speak to "you"; Nakshion speaks in first person in chat only.
- Hedge honestly: "suggests", "tends to", "a good window for". Never "will", never fear ("danger", "doom", "bad luck"). Malefic ≠ bad: say "demanding", "testing", "asks for patience".
- Errors say what happened + what to do: "We couldn't find that place. Try the nearest larger city."
- Use the Sanskrit term with the English gloss on first use per screen: "Lagna (Ascendant)".

---

## 2. Visual direction: "Soft Night Editorial"

| Decision | Choice | Why (vs current + alternatives) |
|---|---|---|
| Base | Opaque tonal layers on deep indigo-black `#0B0D1A` | Current neon glass (`backdrop-blur` on every card) costs frame time on mid-range Android (the core Indian market) and makes text contrast unpredictable over moving backgrounds. ui-ux-pro-max flags Liquid/Glassmorphism as "Accessibility: text contrast ⚠, Performance: moderate-poor". |
| Glass | **Only** on layers floating over imagery or the starfield (landing hero cards, mobile bottom nav, sticky headers over content). `surface-glass` utility. | Keeps the signature "lens into the sky" moment without taxing every card. |
| Accent | Warm "diya" gold `#F2B544` | Gold = sun, auspiciousness, the lamp at puja. Warm against cool indigo gives the best figure/ground for the one action that matters. ui-ux-pro-max: "Premium dark + gold accent" (CTA `#CA8A04` family). The old `#CA8A04` fails on dark (4.0:1 vs bg); brightened to `#F2B544` (10.55:1). |
| AI colour | Moonlit violet `#A99BFF` (text) / `#6A5AE0` (fill) | Continuity with today's `#ca98ff` brand recognition, but desaturated toward blue so it reads "moonlight", not "neon". |
| Headlines | Serif display (Fraunces), editorial weight 500 | Today everything is extrabold uppercase Plus Jakarta Sans — it shouts. A soft old-style serif reads "almanac / manuscript / panchang", premium and calm. |
| Edges | 1px hairlines + tonal steps; no thick borders, no rainbow gradient borders except one `feature` card per page | P1. |
| Imagery | The 12 zodiac portraits in `Zodiac signs/` are the only illustrative imagery. Used large on landing + sign detail; never as card backgrounds behind text. | They are strong art; competing with text halves the value of both. |

---

## 3. Colour

### 3.1 Semantic tokens

Utility = Tailwind class generated by `tokens.css` (e.g. `bg-surface`, `text-fg-muted`, `border-border-strong`). Opacity modifiers work: `bg-accent/20`.

| Role | Token / utility | Dark (default) | Light | Use |
|---|---|---|---|---|
| Canvas | `bg` | `#0B0D1A` | `#FAF7F0` | Page background (use `bg-night` utility for the nebula wash) |
| Sunken | `bg-sunken` | `#070812` | `#EFE9DC` | Chart backdrop, code, wells |
| Surface | `surface` | `#12152A` | `#FFFFFF` | Cards |
| Elevated | `elevated` | `#1A1E38` | `#F3EEE3` | Nested blocks, hover rows, menus, skeletons |
| Overlay | `overlay` | `#232847` | `#FFFFFF` | Dialogs, sheets, toasts, popovers |
| Field | `field` | `#0E1124` | `#FFFFFF` | Input wells |
| Scrim | `scrim` | `rgb(5 6 14 / .72)` | `rgb(26 24 48 / .40)` | Behind modals |
| Border | `border` | `#262B4A` | `#E6DECD` | Decorative hairlines, dividers |
| Border strong | `border-strong` | `#6B73A8` | `#8A7D60` | **Control boundaries** (inputs, secondary buttons, chart lines) — ≥3:1 |
| Text primary | `fg` | `#EEF0FA` | `#1A1830` | Headings, body |
| Text secondary | `fg-secondary` | `#B4B9D6` | `#46435F` | Supporting copy, labels |
| Text muted | `fg-muted` | `#8F95B8` | `#625F7C` | Captions, meta, placeholders |
| Text disabled | `fg-disabled` | `#5C6188` | `#A9A4B8` | Disabled only (WCAG-exempt) |
| Accent | `accent` / `-hover` / `-pressed` | `#F2B544` / `#F7C66A` / `#E0A030` | `#E3A63A` / `#EBB552` / `#D0922A` | Primary action fill, Lagna, current period |
| Accent as text | `accent-text` | `#F2B544` | `#8A5A00` | Gold words/icons on surfaces |
| On accent | `on-accent` | `#1A1204` | `#1A1204` | Text on gold fill |
| Accent subtle | `accent-subtle` | gold @ 12% | gold @ 16% | Lagna house fill, selected-auspicious |
| AI | `ai` | `#A99BFF` | `#5443CF` | AI text/icons, links in chat |
| AI fill / on | `ai-fill` / `on-ai` | `#6A5AE0` / `#FFFFFF` | `#5443CF` / `#FFFFFF` | Send button, AI avatar |
| AI subtle | `ai-subtle` | violet @ 12% | violet @ 10% | Selected chips, grounding chips, selection |
| Success | `success` (+`-subtle`) | `#4FD1A5` | `#0B7354` | Saved, exalted, harmonious |
| Warning | `warning` (+`-subtle`) | `#FB923C` | `#A8410A` | Approximate data, combust, caution windows |
| Danger | `danger` (+`-fill`, `on-danger`, `-subtle`) | `#FF6B81` / on `#1A0508` | `#C0263F` / on `#FFFFFF` | Errors, destructive, debilitated |
| Info | `info` (+`-subtle`) | `#7CC4FF` | `#1D66AA` | Neutral notices, retrograde marker |
| Focus | `focus` | `#C9BFFF` | `#5443CF` | Focus ring (2px, offset 2px) |

**Why warning is orange, not amber:** amber would collide with the gold accent. Warning `#FB923C` is visibly redder than gold `#F2B544`, and every warning carries an icon (`AlertTriangle`) so hue is never the only cue.

### 3.2 Element (tattva) colours — categorical, always paired with glyph or label

| Element | Signs | Dark | Light |
|---|---|---|---|
| Fire `fire` | Aries, Leo, Sagittarius | `#FF8A65` | `#B23A0A` |
| Earth `earth` | Taurus, Virgo, Capricorn | `#B5C97A` | `#52701A` |
| Air `air` | Gemini, Libra, Aquarius | `#7FD3E8` | `#0E6C86` |
| Water `water` | Cancer, Scorpio, Pisces | `#8FB0FF` | `#2952C7` |

### 3.3 Graha (planet) colours — rooted in Jyotish associations

| Graha | Utility | Dark | Light | Association |
|---|---|---|---|---|
| Surya / Sun | `sun` | `#FF9E57` | `#9C4706` | copper |
| Chandra / Moon | `moon` | `#DCE3F2` | `#55607A` | pearl |
| Mangal / Mars | `mars` | `#FF6B6B` | `#C81E1E` | coral red |
| Budha / Mercury | `mercury` | `#6FD39B` | `#167A47` | emerald |
| Guru / Jupiter | `jupiter` | `#FFD166` | `#7A5A00` | yellow sapphire |
| Shukra / Venus | `venus` | `#F3A6D8` | `#B0307F` | diamond-rose |
| Shani / Saturn | `saturn` | `#8EA2FF` | `#3F51C7` | blue sapphire |
| Rahu | `rahu` | `#A8AEC8` | `#5A5F78` | smoke |
| Ketu | `ketu` | `#D0A884` | `#8A5B30` | ochre |

Uranus/Neptune/Pluto (if ever shown in Western mode) use `fg-muted` — they are not grahas and must not look equal to them.

**Rule:** planet colour is *identity*, never *judgement*. Never colour a planet red because it is "malefic".

### 3.4 Contrast verification (WCAG 2.2 AA)

Computed with the WCAG relative-luminance formula. Text needs ≥4.5:1; UI boundaries need ≥3:1. Every foreground token is checked on every surface it can sit on. **All pass.**

#### Dark

| Token | Hex | on bg `#0B0D1A` | on surface `#12152A` | on elevated `#1A1E38` | on overlay `#232847` | Min | Verdict |
|---|---|---|---|---|---|---|---|
| text-primary | `#EEF0FA` | 17.01 | 15.84 | 14.36 | 12.61 | 12.61 | AA |
| text-secondary | `#B4B9D6` | 9.99 | 9.30 | 8.43 | 7.40 | 7.40 | AA |
| text-muted | `#8F95B8` | 6.59 | 6.14 | 5.56 | 4.88 | 4.88 | AA |
| accent (gold) | `#F2B544` | 10.55 | 9.83 | 8.91 | 7.82 | 7.82 | AA |
| ai (violet) | `#A99BFF` | 8.12 | 7.56 | 6.85 | 6.02 | 6.02 | AA |
| success | `#4FD1A5` | 10.12 | 9.43 | 8.55 | 7.50 | 7.50 | AA |
| warning | `#FB923C` | 8.54 | 7.95 | 7.21 | 6.33 | 6.33 | AA |
| danger | `#FF6B81` | 7.06 | 6.58 | 5.96 | 5.23 | 5.23 | AA |
| info | `#7CC4FF` | 10.30 | 9.60 | 8.70 | 7.64 | 7.64 | AA |
| focus ring | `#C9BFFF` | 11.39 | 10.61 | 9.62 | 8.44 | 8.44 | AA |
| border-strong | `#6B73A8` | 4.27 | 3.98 | 3.61 | 3.17 | 3.17 | AA (UI 3:1) |
| fire | `#FF8A65` | 8.35 | 7.78 | 7.05 | 6.19 | 6.19 | AA |
| earth | `#B5C97A` | 10.67 | 9.95 | 9.02 | 7.91 | 7.91 | AA |
| air | `#7FD3E8` | 11.40 | 10.62 | 9.63 | 8.45 | 8.45 | AA |
| water | `#8FB0FF` | 9.04 | 8.42 | 7.63 | 6.70 | 6.70 | AA |
| sun | `#FF9E57` | 9.46 | 8.81 | 7.99 | 7.01 | 7.01 | AA |
| moon | `#DCE3F2` | 15.01 | 13.99 | 12.68 | 11.13 | 11.13 | AA |
| mars | `#FF6B6B` | 6.96 | 6.49 | 5.88 | 5.16 | 5.16 | AA |
| mercury | `#6FD39B` | 10.55 | 9.83 | 8.91 | 7.82 | 7.82 | AA |
| jupiter | `#FFD166` | 13.40 | 12.49 | 11.32 | 9.93 | 9.93 | AA |
| venus | `#F3A6D8` | 10.36 | 9.65 | 8.75 | 7.68 | 7.68 | AA |
| saturn | `#8EA2FF` | 8.06 | 7.51 | 6.81 | 5.98 | 5.98 | AA |
| rahu | `#A8AEC8` | 8.79 | 8.19 | 7.42 | 6.52 | 6.52 | AA |
| ketu | `#D0A884` | 8.85 | 8.24 | 7.47 | 6.56 | 6.56 | AA |

#### Light

| Token | Hex | on bg `#FAF7F0` | on surface `#FFFFFF` | on elevated `#F3EEE3` | on overlay `#FFFFFF` | Min | Verdict |
|---|---|---|---|---|---|---|---|
| text-primary | `#1A1830` | 16.12 | 17.25 | 14.91 | 17.25 | 14.91 | AA |
| text-secondary | `#46435F` | 8.81 | 9.42 | 8.14 | 9.42 | 8.14 | AA |
| text-muted | `#625F7C` | 5.69 | 6.09 | 5.27 | 6.09 | 5.27 | AA |
| accent (gold text) | `#8A5A00` | 5.54 | 5.93 | 5.12 | 5.93 | 5.12 | AA |
| ai (violet) | `#5443CF` | 6.37 | 6.82 | 5.89 | 6.82 | 5.89 | AA |
| success | `#0B7354` | 5.46 | 5.84 | 5.05 | 5.84 | 5.05 | AA |
| warning | `#A8410A` | 5.73 | 6.13 | 5.30 | 6.13 | 5.30 | AA |
| danger | `#C0263F` | 5.47 | 5.85 | 5.06 | 5.85 | 5.06 | AA |
| info | `#1D66AA` | 5.56 | 5.94 | 5.14 | 5.94 | 5.14 | AA |
| focus ring | `#5443CF` | 6.37 | 6.82 | 5.89 | 6.82 | 5.89 | AA |
| border-strong | `#8A7D60` | 3.79 | 4.05 | 3.50 | 4.05 | 3.50 | AA (UI 3:1) |
| fire | `#B23A0A` | 5.60 | 6.00 | 5.18 | 6.00 | 5.18 | AA |
| earth | `#52701A` | 5.32 | 5.69 | 4.92 | 5.69 | 4.92 | AA |
| air | `#0E6C86` | 5.60 | 5.99 | 5.17 | 5.99 | 5.17 | AA |
| water | `#2952C7` | 6.28 | 6.72 | 5.81 | 6.72 | 5.81 | AA |
| sun | `#9C4706` | 5.92 | 6.33 | 5.47 | 6.33 | 5.47 | AA |
| moon | `#55607A` | 5.88 | 6.29 | 5.43 | 6.29 | 5.43 | AA |
| mars | `#C81E1E` | 5.36 | 5.74 | 4.96 | 5.74 | 4.96 | AA |
| mercury | `#167A47` | 5.02 | 5.37 | 4.64 | 5.37 | 4.64 | AA |
| jupiter | `#7A5A00` | 5.97 | 6.38 | 5.52 | 6.38 | 5.52 | AA |
| venus | `#B0307F` | 5.49 | 5.87 | 5.08 | 5.87 | 5.08 | AA |
| saturn | `#3F51C7` | 6.11 | 6.54 | 5.65 | 6.54 | 5.65 | AA |
| rahu | `#5A5F78` | 5.87 | 6.28 | 5.43 | 6.28 | 5.43 | AA |
| ketu | `#8A5B30` | 5.42 | 5.80 | 5.01 | 5.80 | 5.01 | AA |

#### Filled controls

| Pairing | Colours | Ratio |
|---|---|---|
| Primary button text on gold (dark) | `#1A1204` on `#F2B544` | 10.13 |
| Primary button text on gold hover (dark) | `#1A1204` on `#F7C66A` | 11.69 |
| Primary button text on gold (light) | `#1A1204` on `#E3A63A` | 8.64 |
| White on AI violet fill (dark) | `#FFFFFF` on `#6A5AE0` | 5.06 |
| White on AI violet fill (light) | `#FFFFFF` on `#5443CF` | 6.82 |
| Danger button text (dark) | `#1A0508` on `#FF6B81` | 7.18 |
| Danger button text (light) | `#FFFFFF` on `#C0263F` | 5.85 |
| Focus ring vs bg (dark) | `#C9BFFF` on `#0B0D1A` | 11.39 |
| Focus ring vs bg (light) | `#5443CF` on `#FAF7F0` | 6.37 |

Light-theme gold fill `#E3A63A` vs the `#FAF7F0` canvas is 2.0:1. That is compliant (WCAG 1.4.11 does not require a button's fill to contrast with the page when its text label identifies it), but primary buttons in light theme also get `shadow-e1` so the shape reads clearly.

### 3.5 Colour rules

1. **Opacity is not a colour.** Never `text-fg/60`, `text-on-surface-variant/50`, `opacity-50` on text. Use `fg-secondary` / `fg-muted`, which are contrast-verified. (Today: ~29 such usages; see AUDIT #1.)
2. **No raw Tailwind palette** (`text-red-400`, `bg-emerald-500`, `text-amber-400`) in feature code. Status → `success/warning/danger/info`. Planets/elements → their tokens.
3. **No gradient text** on anything below 40px or on body copy. A single gold-to-cream word in the landing display headline is the only allowed use, and its lowest stop must stay ≥4.5:1.
4. **Gradient `--nk-gradient-aurora`** is reserved for: 1px hairline on a `feature` card, the compatibility ring track glow, onboarding progress. Max one per viewport.
5. **Colour is never the only cue** — every coloured state also has an icon, a label, or a shape (retrograde = "R", exalted = up-chevron, danger = AlertCircle).

---

## 4. Typography

### 4.1 Families

| Role | Family | Fallback chain | Why |
|---|---|---|---|
| Display (h1–h3, stat numerals, reading titles) | **Fraunces** (variable: `opsz` 9–144, `wght` 400–600, `SOFT` 50) | `Tiro Devanagari Hindi` → `Noto Serif Devanagari` → Georgia → serif | Old-style soft serif with optical sizing — reads like a beautifully set almanac at 64px and stays crisp at 20px. Lora (previous MASTER) is a *text* serif and goes bland at display sizes; Playfair (ui-ux-pro-max suggestion) is high-contrast fashion, too cold and too thin on dark backgrounds. Tiro Devanagari Hindi was designed as a calligraphic book face and pairs with Fraunces' warmth. |
| UI + body (everything else) | **Inter** (400–700, variable) | `Noto Sans Devanagari` → system-ui | Already loaded today (zero migration cost), excellent small-size legibility, true tabular figures for degrees (`14°22′`). Noto Sans Devanagari has matched x-height/weight so mixed Hinglish lines don't jump. |
| Mono | system mono | — | Only for debug/coords if ever needed. Degrees use Inter `tabular-nums`, not mono. |

**Dropped:** Plus Jakarta Sans (current headline font; extrabold uppercase is the "shouting" problem) and Raleway (thin weights fail on dark, poor numerals).

**Loading** (replace the `<link>` in `frontend/index.html`):
```html
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght,SOFT@9..144,400..600,0..100&family=Inter:wght@400..700&family=Noto+Sans+Devanagari:wght@400..600&family=Tiro+Devanagari+Hindi&display=swap" rel="stylesheet" />
```
Google Fonts serves Devanagari through `unicode-range` subsets, so English-only sessions download zero Devanagari bytes. Budget: ≤ 110 KB woff2 for Latin (Fraunces + Inter).

### 4.2 Scale

Mobile-first; display sizes use `clamp()` so there are no breakpoint jumps. All sizes in rem (respect user zoom).

| Utility | Size (mobile → desktop) | Line height | Tracking | Family / weight | Use |
|---|---|---|---|---|---|
| `text-display` | 40 → 64 px | 1.05 | −0.02em | Fraunces 500 | Landing hero only |
| `text-h1` | 32 → 44 px | 1.12 | −0.015em | Fraunces 500 | Page title (one per page) |
| `text-h2` | 24 → 32 px | 1.2 | −0.01em | Fraunces 500 | Section title |
| `text-h3` | 20 → 24 px | 1.3 | 0 | Fraunces 500 | Card hero title, reading headline |
| `text-title` | 18 px | 1.4 | 0 | Inter 600 | Card titles, dialog titles |
| `text-body-lg` | 17 px | 1.7 | 0 | Inter 400 | Readings, AI replies (long-form) |
| `text-body` | 16 px | 1.6 | 0 | Inter 400/500 | Default UI; **all inputs** (prevents iOS zoom) |
| `text-body-sm` | 14 px | 1.55 | 0 | Inter 400/500 | Secondary UI, table cells, buttons-sm |
| `text-caption` | 13 px | 1.45 | 0 | Inter 400/500 | Meta, helper text. **Floor for any sentence.** |
| `text-overline` | 12 px | 1.3 | +0.08em | Inter 600, uppercase | Badges, Latin-only section kickers. **Absolute floor.** |
| `text-stat` | 40 → 56 px | 1.0 | 0 | Fraunces 500 + `tabular` | Scores, big numbers |

**Rules**
- **Nothing below 12px.** `text-[10px]`, `text-[11px]`, `text-[9px]` are banned (19 usages today).
- Max line length 68ch for reading (`max-w-reading` = 672px).
- Headings `text-wrap: balance`; paragraphs `text-wrap: pretty` (set in base layer).
- Weights: 400, 500, 600 only. No 800/extrabold, no 300/light on dark.
- Uppercase only via `text-overline`, only for Latin, max 3 words. Buttons, headings, tabs are sentence case.
- Numbers that update or align (degrees, scores, dates in tables) use `tabular`.
- Degrees format: `14°22′` (U+2032 prime), not `14.37°` and not `14°22'`.

### 4.3 Devanagari / i18n

- `:lang(hi)` resets letter-spacing to 0 and text-transform to none (tracking breaks conjuncts; Devanagari has no case), raises line-height to 1.75 (matras above/below). Set `lang="hi"` on the element, not only the `<html>`, when mixing (chat messages in Hindi, rashi names in Devanagari).
- Design all boxes to grow: no fixed heights on text containers, buttons use `min-h` not `h`, and allow 2-line button labels on mobile (`text-balance`).
- Test strings: `"अपनी जन्म कुंडली बनाएं"` (Generate your birth chart), `"शनि महादशा"`, a 40-character Hinglish line.
- Numerals: keep Western digits (0–9) in both locales for degrees and dates; Devanagari digits optional for prose only.

---

## 5. Layout, spacing, radius

### 5.1 Spacing
Tailwind's 4px base (`--spacing: 0.25rem`). Use only these steps: **4, 8, 12, 16, 20, 24, 32, 40, 48, 64, 96**.

| Context | Mobile | ≥768 | ≥1024 |
|---|---|---|---|
| Page side gutter | 16 (`px-4`) | 24 | 32 |
| Card padding | 20 (`p-5`) | 24 | 24 |
| Gap between cards | 12 | 16 | 24 |
| Section gap (vertical) | 40 | 56 | 64 |
| Form field gap | 20 | 20 | 24 |
| Inline icon–label gap | 8 | 8 | 8 |
| Landing section rhythm | 64 | 96 | 128 |

### 5.2 Grid & breakpoints
Tailwind defaults: `sm 640` · `md 768` · `lg 1024` · `xl 1280`. Design at **360 and 375** first.
- App container `max-w-app` (1200px). Reading `max-w-reading` (672). Forms `max-w-form` (480). Chat column `max-w-chat` (768).
- 4-col grid on mobile, 8 on tablet, 12 on desktop, gutters = card gap row above.

### 5.3 App shell & navigation
- **Mobile (<768): bottom tab bar** (64px + `env(safe-area-inset-bottom)`, `surface-glass`, top hairline `border`). Five tabs: **Today** (Sun) · **Chart** (custom kundali glyph) · **Ask** (Sparkles, centre, `ai` tint) · **Match** (HeartHandshake) · **You** (avatar). Labels always visible, 12px, active = `fg` + 2px top indicator in `accent`; inactive `fg-muted`. Hide on scroll-down only in Chat (keyboard).
- **Desktop (≥768): top bar** 64px, sticky, `bg/80` + blur 12px, hairline bottom. Logo left, the same 5 destinations centre as text links (active: `fg` + 2px `accent` underline offset 20px), avatar menu right.
- Landing/auth use a marketing header (logo + "Sign in" ghost + "Get your chart" primary), not the app nav.
- Content must clear fixed bars: `pt-[var(--nk-header-h)]` desktop, `pb-[calc(var(--nk-bottom-nav-h)+env(safe-area-inset-bottom))]` mobile.

### 5.4 Radius (semantic — Tailwind's own `rounded-*` scale is untouched)

| Utility | Value | Used by |
|---|---|---|
| `rounded-control` | 12px | Button, IconButton (square), Input, Select, segmented control, tabs container |
| `rounded-card` | 16px | Card, menu, popover, toast, listbox |
| `rounded-sheet` | 24px | Dialog, bottom sheet (top corners), ChatInput |
| `rounded-bubble` | 20px | User chat bubble (with 6px "tail" corner) |
| `rounded-chip` | full | Chip, Badge, Avatar, round IconButton, ZodiacBadge |

Nested radius rule: inner radius = outer radius − padding (min 8px). Never mix `rounded-xl`/`rounded-2xl`/`rounded-3xl` ad hoc (today: 6 different radii on cards).

---

## 6. Elevation & glow

Dark mode depth = **tone first, shadow second**. Each step up the surface ladder is a lighter tone; shadows only separate things that physically float.

| Level | Surface | Shadow | Border | Use |
|---|---|---|---|---|
| 0 | `bg` | none | — | Page |
| 1 | `surface` | none (`shadow-highlight` optional) | `border` | Cards |
| 2 | `elevated` | `shadow-e1` | `border` | Nested, menus, hover rows |
| 3 | `overlay` | `shadow-e2` | `border` | Popovers, toasts, sticky bars |
| 4 | `overlay` | `shadow-e3` | `border` | Dialogs, sheets |

| Glow | Value (dark) | Use — and nowhere else |
|---|---|---|
| `shadow-glow-accent` | `0 8px 28px -6px rgb(242 181 68 / .45)` | Primary button hover; current-dasha segment; compatibility score ≥8.5 |
| `shadow-glow-ai` | `0 8px 32px -8px rgb(124 108 240 / .55)` | ChatInput focus-within; AI avatar while streaming |

No coloured glows on cards, icons, or text. No `blur-[80px]` decorative blobs inside cards (today: Onboarding, Dashboard).

### Atmosphere
- `bg-night` on `<body>`/app root: two radial washes (violet top-left 14%, gold bottom-right 6%) — static.
- `starfield` on one `fixed inset-0 pointer-events-none aria-hidden` layer: 20-star SVG tile, opacity .55 dark / 0 light. `animate-twinkle` **landing only**.
- Light theme: no stars, washes at 6–10% for warmth.

---

## 7. Iconography

### 7.1 UI icons — Lucide (`lucide-react@0.575`)
- Default `size={20}` `strokeWidth={1.75}`; 16 in dense rows/badges; 24 in nav/empty states (48 inside an 80px circle for EmptyState).
- Icon colour inherits text colour (`currentColor`). Never colour an icon a hue that the adjacent label doesn't justify.
- Icon-only controls require `aria-label`; decorative icons get `aria-hidden="true"` (Lucide sets this by default — keep it).
- Canonical mapping (one meaning per icon across the app):

| Meaning | Icon |
|---|---|
| AI / Nakshion | `Sparkles` |
| Today / daily reading | `Sun` |
| Moon phase / night | `Moon`, `MoonStar` |
| Compatibility | `HeartHandshake` |
| Birth date / time / place | `CalendarDays`, `Clock`, `MapPin` |
| Retrograde | `RotateCcw` (+ "R") |
| Info / approximation | `Info` |
| Warning | `AlertTriangle` |
| Error | `AlertCircle` |
| Success | `CheckCircle2` |
| Send / Stop | `ArrowUp` / `Square` |
| Language | `Languages` |

### 7.2 Astrological glyphs — custom SVG set (no emoji, no raw Unicode)
Today zodiac/planet glyphs are Unicode characters (`♈`, `☉`, `♄` in `ZodiacCards.tsx`, `KundaliChart.tsx`, `ChartPage.tsx`). On iOS and many Android builds U+2648–2653 render as **colour emoji**, which violates the no-emoji rule and breaks the palette.

**Spec: `<AstroGlyph name="leo" | "saturn" | ... />`** (proposed home `frontend/src/components/astrology/glyphs/`)
- 24×24 viewBox, 2px safe padding, **stroke 1.75, round caps/joins, `fill="none"`, `stroke="currentColor"`** — identical construction to Lucide so glyphs sit beside UI icons without looking foreign.
- Set (26): 12 rashis, 9 grahas (Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, Rahu ☊, Ketu ☋), Uranus, Neptune, Pluto, Ascendant/Lagna mark, Retrograde ℞.
- Source: draw in-house, or trace outlines from **Noto Sans Symbols** (SIL OFL 1.1 — attribution in `THIRD_PARTY.md`). Ship as a typed TS map of path strings (tree-shakeable, ~4 KB total), not a sprite request.
- Props: `name`, `size` (16/20/24/32/48), `title?` → when given, renders `<svg role="img"><title>…</title>`; otherwise `aria-hidden`.
- **Interim fallback** until the SVG set exists: `{"♌︎"}` (append U+FE0E VARIATION SELECTOR-15 to force text presentation) inside `font-family: "Noto Sans Symbols 2", var(--font-sans)`.
- In charts, planets render as **two-letter abbreviations** (`Su Mo Ma Me Ju Ve Sa Ra Ke`, localised: `सू चं मं बु गु शु श रा के`) — more legible at 12px than glyphs and familiar to Jyotish users. Glyphs are for badges, lists, headers.

### 7.3 Zodiac imagery
The 12 portraits (`Zodiac signs/*.jpeg`, ~900 KB each; 11 MB in `frontend/public/images/zodiac/`) must ship as AVIF + WebP at 480w and 960w (target ≤ 90 KB @960w), `loading="lazy"`, `decoding="async"`, explicit `width/height` (aspect 4:5), meaningful `alt` ("Leo — a lion crowned in sunlight").

---

## 8. Motion

### 8.1 Tokens
CSS: `--nk-dur-*` and `ease-*` utilities. Framer Motion: mirror in `frontend/src/lib/motion.ts`:

```ts
export const dur = { instant: 0.1, fast: 0.15, base: 0.25, slow: 0.4, slower: 0.6, ambient: 2.4 } as const;
export const ease = {
  standard:   [0.2, 0, 0, 1],
  enter:      [0.16, 1, 0.3, 1],   // decelerate — things arriving
  exit:       [0.4, 0, 1, 1],      // accelerate — things leaving
  emphasized: [0.3, 0, 0, 1.2],
} as const;
export const spring = {
  snappy: { type: "spring", stiffness: 400, damping: 30 },  // buttons, chips, tab indicator
  smooth: { type: "spring", stiffness: 300, damping: 32 },  // layout, sheets
  gentle: { type: "spring", stiffness: 180, damping: 24 },  // chart reveal, meters
} as const;
export const fadeUp = {
  hidden: { opacity: 0, y: 8 },
  show:   { opacity: 1, y: 0, transition: { duration: dur.base, ease: ease.enter } },
};
```

| Interaction | Duration | Easing | Property |
|---|---|---|---|
| Hover colour / border | 150 ms | standard | colour, border-colour, bg |
| Press | 100 ms | standard | `scale(0.98)` |
| Focus ring | 0 ms | — | appears instantly |
| Tooltip | 150 ms after 500 ms delay | enter | opacity, y 4→0 |
| Menu / popover in / out | 150 / 100 ms | enter / exit | opacity, scale .97→1, y −4→0 |
| Card / list entrance | 250 ms, stagger 40 ms, max 6 items staggered | enter | opacity, y 8→0 |
| Dialog in / out | 250 / 150 ms | enter / exit | opacity, scale .96→1 |
| Sheet in / out | spring smooth / 200 ms | — / exit | y 100%→0 |
| Toast | 250 in / 150 out | enter / exit | opacity, y 16→0 |
| Tab indicator | spring snappy | — | `layoutId` |
| Page transition | 250 ms | enter | opacity only (no slide — avoids nav disorientation) |
| Chart draw-in | 600 ms lines + 30 ms stagger per planet | enter | `pathLength`, opacity |
| Score meter fill | 900 ms, 200 ms delay | enter | `pathLength` |
| Ambient (stars, nebula) | 2.4–7 s | ease-in-out | opacity only — landing only |

**Rules:** animate only `transform` and `opacity` (plus SVG `pathLength`). Never animate `height` (today: Onboarding birth-time field animates `height: auto` → use `layout` or a grid-rows 0fr→1fr transition). Total entrance choreography on any screen ≤ 500 ms. No infinite animation inside a content area except the streaming caret and loading indicators.

### 8.2 Reduced motion
`prefers-reduced-motion: reduce` →
- Global CSS kill-switch in `tokens.css` (durations → 0.01 ms).
- **Also** in Framer: wrap the app in `<MotionConfig reducedMotion="user">` so transforms are dropped and only opacity animates.
- Replace: draw-in → instant; meter fill → instant with number shown; stagger → none; sheet slide → 150 ms fade; twinkle/rotating orbit loaders → static icon + text; skeleton shimmer → static `elevated` block.
- Typing/streaming text still appears (it is content, not motion) but the caret stops blinking.

---

## 9. Data visualisation

Shared rules: every chart has (a) a text title, (b) a one-sentence `aria-describedby` summary, (c) an equivalent accessible list/table, (d) labels in text — colour is secondary. Minimum rendered label size 12px. All figures `tabular`.

### 9.1 Kundali / ChartWheel
Nakshion is Vedic-first. **Default format: North Indian diamond**; toggle to **South Indian grid** (segmented control, persisted per user). A Western circular wheel is optional later and follows the same tokens.

| Element | Spec (viewBox 0 0 400 400) |
|---|---|
| Rendered size | min 320px (mobile = full width minus 16px gutters, cap 343); desktop 440–520px. Never below 320 (labels would fall under 12px). Dashboard thumbnail 160px is **non-interactive, labels hidden**, shows only Lagna + Moon markers. |
| Backdrop | `bg-sunken` square, `rounded-card`, 1px `border` |
| Frame | outer square stroke `border-strong` 1.5; diagonals + inner diamond `border-strong` 1 at 60% opacity |
| Lagna (house 1) | fill `accent-subtle`; label "La" / "Asc" in `accent-text`, 13 units, weight 600; 2px `accent` inner stroke |
| Sign numbers (North) | 1–12 in `fg-muted`, 13 units (≈10.4px at 320 — supplementary; same data is in the table) |
| Planets | 2-letter abbr in **planet colour**, 16 units (≥12.8px at 320), weight 600; up to 4 per house in a 2×2 stack, then "+2" overflow chip |
| Modifiers | Retrograde: superscript `R` (same colour, 11 units); Combust: `c`; Exalted: ▲ chevron path, Debilitated: ▼ chevron — SVG paths, not Unicode |
| Degrees | shown only ≥ 440px render size, `fg-muted` 11 units below abbr |
| Hover (pointer) | house fill `ai-subtle`, tooltip with planet list + degrees |
| Selected | house stroke `ai` 2px, fill `ai-subtle`; linked PlanetRows highlight |
| Keyboard | each house is `role="button" tabindex` (roving), arrows move in zodiac order, Enter opens detail (Sheet <768, side panel ≥1024) |
| a11y | `<svg role="group" aria-labelledby="chart-title" aria-describedby="chart-summary">`; summary e.g. "Lagna Simha (Leo). Sun and Mercury in the 10th house. Saturn retrograde in the 7th." |
| Motion | lines draw (600 ms), then planets fade in (30 ms stagger). Reduced motion: static. |

### 9.2 Aspect grid (graha drishti)
Lower-triangular planet × planet matrix (9 grahas → 36 cells).
- Cell 36px desktop / 32px mobile (9×32 + 40px label column = 328px — fits 343). Row/column headers: AstroGlyph 16 + abbr.
- **Shape encodes type, colour encodes the aspecting planet** (consistent with 3.3):
  - Conjunction (same house): ring ○ 12px stroke 1.75
  - Full 7th-house drishti: filled dot ● 10px
  - Special drishti (Mars 4/8, Jupiter 5/9, Saturn 3/10): diamond ◆ 10px
  - Mutual aspect: dot with outer ring
- Empty cells: 1px `border` hairline grid only. Hover/focus cell: `elevated` + tooltip "Saturn aspects Moon (10th-house special drishti)".
- Legend always visible above the grid (shapes + words), never hidden behind a tooltip.
- Accessible equivalent: `<table>` with `<th scope>` — the grid itself *is* the table, cells contain visually-hidden text.

### 9.3 Vimshottari dasha timeline
- **≥768:** horizontal track 48px tall, segments proportional to years across the native's lifetime (birth → +100y), `rounded-control` ends.
  - Segment fill: planet colour @ 18%, 3px top bar in solid planet colour, label inside if width ≥ 56px ("Sa · 19y"), otherwise label on hover/focus.
  - **Past:** 45% opacity. **Current:** full opacity, 2px `accent` outline, `shadow-glow-accent`. **Future:** 80%.
  - "Now" marker: 2px `accent` vertical line spanning track + caption "Now · 2026" above.
  - Year axis below: decade ticks, `text-caption fg-muted tabular`.
  - Selecting a mahadasha expands a second 32px track of its 9 antardashas (same encoding) with 250 ms `layout` animation.
- **<768:** vertical stepper list — each row: AstroGlyph 20 in planet colour, "Shani Mahadasha" + "2019 – 2038 · 19 years", current row gets `accent` left bar 3px + "Current" badge (accent), expandable to antardashas.
- Each segment is a button: `aria-label="Saturn Mahadasha, March 2019 to March 2038, current"`, `aria-expanded` when it opens antardashas.

### 9.4 Compatibility score
Backend returns `overall_score` 0–10 + category scores 0–10 (`CompatibilityPage.tsx`). If Ashtakoot (36 guna) is added, use 9.4b.

**9.4a CompatibilityMeter (0–10)** — 240° arc gauge (gap at bottom), 200px desktop / 168px mobile, stroke 12 / 10, round caps.
- Track: `border` colour. Fill: **solid band colour** (not a decorative gradient — the colour carries meaning):

| Score | Band label | Colour | Icon |
|---|---|---|---|
| 0.0 – 3.9 | Challenging | `danger` | `AlertCircle` |
| 4.0 – 6.4 | Workable | `warning` | `Scale` |
| 6.5 – 8.4 | Harmonious | `success` | `CheckCircle2` |
| 8.5 – 10 | Exceptional | `accent` + `shadow-glow-accent` | `Sparkles` |

- Centre: `text-stat` numeral (one decimal) + "/10" in `fg-muted`; below the gauge: band label with icon in band colour (`text-title`).
- Category bars: label (Inter 500 14px) · 8px track `elevated` with band-coloured fill · value "7.5" right-aligned `tabular`. Order by importance, not by score.
- `role="meter" aria-valuemin=0 aria-valuemax=10 aria-valuenow=7.4 aria-valuetext="7.4 out of 10, Harmonious"`.

**9.4b Ashtakoot (36 guna)**: same meter with max 36 and bands <18 Not recommended (`danger`) · 18–24 Average (`warning`) · 25–32 Good (`success`) · 33–36 Excellent (`accent`); plus an 8-row koota table (Varna 1, Vashya 2, Tara 3, Yoni 4, Graha Maitri 5, Gana 6, Bhakoot 7, Nadi 8) with "x / max" and dosha badges (Nadi/Bhakoot dosha → `warning` badge with explanation, never alarmist copy).

### 9.5 Small multiples & ratings
- Daily focus ratings (Love/Career/Health/Mood): 5 segments 16×6px, filled = `accent`, empty = `elevated`, plus "4/5" text. Not stars, not hearts.
- No pie charts. No 3D. No dual axes.

---

## 10. Accessibility contract (blocking)

1. Contrast per §3.4. New colours must be added to the table before use.
2. Every interactive element: visible `:focus-visible` ring (2px `focus`, offset 2px). Never `outline-none` without a replacement.
3. Touch targets ≥ 44×44px (sm buttons get an invisible hit-area extension via `before:absolute before:-inset-1`).
4. **Never nest interactive elements.** `<Link><Button/></Link>` (7 occurrences today) → `Button asChild`-style pattern: Button accepts `as={Link}` / renders `<a>` with button styles.
5. Forms: visible `<label>` for every field (placeholder is not a label), errors linked with `aria-describedby`, `aria-invalid`, focus moves to first invalid field on submit.
6. Dialogs: native `<dialog>` + `showModal()` (free focus trap, `inert` background, Esc). Restore focus to the trigger on close.
7. Live regions: chat log `role="log"`; toasts `role="status"` (success/info) or `role="alert"` (error); async results announce once, never per token.
8. Charts: §9 summary + table equivalents.
9. `lang` attributes on Hindi content; `dir` stays ltr.
10. Reduced motion per §8.2. Test with OS setting on.
11. Zoom to 200% and 320px width without horizontal scroll (WCAG 1.4.10).

---

## 11. Anti-patterns (instant review rejection)

- Emoji or raw Unicode zodiac/planet characters as icons.
- `text-[10px]`/`text-[11px]`; uppercase + `tracking-widest` labels on form fields.
- Opacity-faded text (`/50`, `/60`, `opacity-50` on copy).
- Raw Tailwind palette colours for meaning (`text-red-400`).
- `backdrop-blur` on cards that sit on a flat background.
- Decorative blur blobs inside cards.
- Full-screen spinner for content that has a known shape (use Skeleton).
- More than one gold primary action per view.
- `<Link>` wrapping `<button>`.
- Animating `height`, `width`, `top`, `left`.
- Hard-coded hex in `.tsx` (except third-party brand marks like the Google logo).

---

## 12. Implementation checklist for `frontend-elite`

1. Copy `tokens.css` → `frontend/src/styles/tokens.css`; replace `@theme` in `index.css` with the import (legacy aliases keep pages working).
2. Swap the fonts `<link>` in `index.html`; set `<html data-theme="dark">` (remove `class="dark"`).
3. Add `src/lib/motion.ts` (§8.1) and `<MotionConfig reducedMotion="user">` in `main.tsx`.
4. Rebuild `components/ui/` per `COMPONENTS.md`: Button (with `as`), IconButton, Input, Field, Select, Card, Badge, Chip, Tabs, Dialog/Sheet, Toast, Skeleton, EmptyState, Avatar. Use `class-variance-authority` (already installed) for variants.
5. Build `components/astrology/`: AstroGlyph, ZodiacBadge, PlanetRow, ChartWheel (refactor `KundaliChart.tsx`), DashaTimeline, AspectGrid, CompatibilityMeter, DailyReadingCard.
6. Migrate pages in this order (highest traffic × worst gaps): Onboarding → Dashboard → Chat → Chart → Compatibility → Profile → Landing.
7. Delete legacy aliases (tokens.css §6) once `grep -rE "surface-container|on-surface|outline-variant|font-headline|font-label" frontend/src` is empty.
