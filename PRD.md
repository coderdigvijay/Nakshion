# Nakshion: Product Requirements Document

| | |
|---|---|
| **Product** | Nakshion: AI astrology with accurate Vedic and Western charts, personal daily guidance, compatibility, and a chart-grounded AI astrologer |
| **Internal codename** | Cosmic Intelligence (dev docs and `.claude/` only; never user-facing) |
| **Version** | 2.0, a full rewrite superseding v1.0 (2026-03-26) |
| **Date** | 2026-10-01 |
| **Owner** | Solo founder-developer |
| **Status** | Approved for build. The backend (`backend/app/`) is being rebuilt from this PRD |

**Companion specifications.** Each is normative: when it's more specific than this PRD, it wins.

| Doc | Scope |
|---|---|
| [`docs/api-contract.md`](docs/api-contract.md) | Every endpoint, request/response shape and error code the frontend relies on, the gaps found in the frontend, and the v2 changes |
| [`docs/astrology-engine.md`](docs/astrology-engine.md) | Calculation core, reference tables, Vedic and Western rules, compatibility scoring, `chart_data` schema, golden tests |
| [`docs/llm-integration.md`](docs/llm-integration.md) | Provider choice, prediction pipeline, RAG, prompts, hallucination guards, safety, evals, cost |
| [`docs/architecture.md`](docs/architecture.md) | System layout, data model and migrations, caching, rate limits, deployment, observability |
| `design-system/cosmic-intelligence/MASTER.md` | Visual language (owned by the design-system agent; this PRD specifies behaviour only) |

---

## Table of contents

1. Summary
2. Problem, vision, goals
3. Audience and personas
4. Product principles
5. Scope and release plan
6. Feature requirements (with acceptance criteria)
7. Screen-by-screen UX requirements
8. Prediction quality: what "most accurate" means here
9. Architecture summary
10. Non-functional requirements
11. Privacy, safety and compliance
12. Testing and release gates
13. Metrics
14. Cost model and budget
15. Decision log
16. Risks
17. Open questions
- Appendix A: Glossary
- Appendix B: Sources (verified Oct 2026)
- Appendix C: What changed from PRD v1.0

---

## 1. Summary

Nakshion computes a user's birth chart with professional-grade precision: Swiss Ephemeris, with sidereal Lahiri **and** tropical systems. It turns the chart into:

1. a personal **daily reading** driven by real transits, dasha periods and Panchang;
2. a **compatibility** report combining Western synastry with Vedic Ashtakoota (Guna Milan);
3. an **AI astrologer chat** that answers in English, Hindi or Hinglish and cites the chart factors behind every answer.

The core design idea: **the deterministic engine computes the facts, and the LLM only writes the narrative.** A rules layer ranks which facts matter for the question, retrieval adds classical interpretation from a curated knowledge base, and the LLM writes the answer under validators that reject any position, date or dasha it didn't get from the engine. This is what makes the readings accurate and personal rather than generic, and it keeps cost per user to cents.

It's built for a solo developer on free-tier infrastructure (Render, Neon, Upstash). The target is hundreds to low thousands of users, with an Indian-leaning audience.

## 2. Problem, vision, goals

### 2.1 Problem

- Most apps give **generic sun-sign content**. The rest compute charts but leave interpretation to dense tables, or to LLM chatbots that **invent planetary positions**.
- Indian users need **Vedic specifics**: rashi, nakshatra, dasha, Kundli matching, Panchang, doshas. They also want them in **Hindi or Hinglish**, without fear-mongering or paid-remedy upsells.
- Users can't ask follow-up questions about *their* chart and timing.

### 2.2 Vision

The most trustworthy astrology companion: correct calculations, transparent reasoning ("this is based on your Saturn–Moon transit and your Jupiter–Saturn dasha"), and warm, practical guidance in the user's language.

### 2.3 Goals for the first 6 months after launch

| # | Goal | Measure |
|---|---|---|
| G1 | Calculation accuracy beyond reproach | 100 % of the golden tests pass (`astrology-engine.md` §11); zero confirmed calculation bugs open for more than 7 days |
| G2 | Grounded, personal AI | 0 % chart-contradicting statements shipped (after validators); ≥ 80 % thumbs-up on rated answers |
| G3 | A daily habit | D30 retention ≥ 15 %; ≥ 35 % of weekly actives open the daily reading 3 or more times a week |
| G4 | Sustainable cost | ≤ $0.25 LLM cost per free MAU per month (typical); infrastructure on free tiers until 1,000 MAU |
| G5 | Reach | 1,000 registered users, 60 % of them with a chart created |
| G6 (v1) | Revenue covers costs | ≥ 3 % premium conversion among MAU |

### 2.4 Non-goals (for now)

Native iOS/Android apps (a PWA instead), community and forums, human-astrologer marketplace, live consultations, Chinese astrology features, mundane astrology, KP sub-lord system, Tarot or numerology, advertising.

## 3. Audience and personas

The primary audience is urban Indians aged 20–40 and the Indian diaspora: mobile-first, comfortable with English, many preferring Hindi or Hinglish for personal topics. The secondary audience is global Western-astrology enthusiasts.

| Persona | Who | Needs | What wins them |
|---|---|---|---|
| **Priya, the everyday believer** | 27, Pune, marketing executive. Checks her rashi horoscope daily; family consults a pandit for big decisions | Hindi/Hinglish, rashi and nakshatra, "is this a good time for a job change?", dasha understanding | A daily reading tied to *her* Moon sign and dasha, explained simply; Panchang and Rahu Kaal |
| **Arjun, the curious skeptic** | 31, Bengaluru, engineer | Wants to know *why*; distrusts vague text | Citations to computed factors; visible calculation settings (ayanamsa, house system); "how this was calculated" |
| **Meera, the enthusiast** | 24, Delhi or London, studies both systems | Depth: D9, yogas, dashas, transits, Western aspects | Accurate data, both systems side by side, a timing calendar |
| **Rohan & Anjali, pre-marriage** | 28 & 26, families discussing marriage | Kundli matching (36 gunas), Mangal dosha, explained calmly | Guna Milan with a clear breakdown, explicit "doshas aren't verdicts" framing, a synastry view |
| **Sam, the Western user** | 33, Austin | Sun, Moon and Rising; transits; synastry | Tropical/Placidus mode as the default view |

## 4. Product principles

These are tie-breakers when requirements conflict.

1. **Accuracy is the brand.** Calculations are deterministic, versioned and golden-tested. The AI never computes and never guesses.
2. **Show your work.** Every reading names the factors behind it. Users can always see the settings (zodiac, ayanamsa, house system, birth-time certainty).
3. **Guidance, not fate.** Language is calibrated, never fatalistic. No death, child-sex or medical predictions. No fear about doshas. No paid-remedy upsells.
4. **Personal over generic.** If we can't personalise (no chart, unknown time), we say so and degrade honestly.
5. **Privacy by default.** Birth data is sensitive. The LLM receives computed facts and a first name, never the email, date, time or place.
6. **Works without the AI.** Charts, scores, Panchang and dashas need no LLM. Readings fall back to templates.
7. **One design language.** Every screen is composed from the shared primitives and tokens in the design system, so new features reuse rather than restyle (§7.0).

## 5. Scope and release plan

### 5.1 Release tiers

| Area | **MVP** (rebuild; frontend works unchanged) | **v1** (+6–10 weeks) | **v2** (later) |
|---|---|---|---|
| Accounts | Email/password + OTP verification, Google OAuth, reset, change/set password, delete account | Data export, consent controls, log out everywhere | Refresh-token sessions, one-time OAuth code |
| Charts | Western (tropical, Placidus) + Vedic (Lahiri, whole sign) natal, nakshatra, Vimshottari MD/AD, D9, D10, yogas and doshas, Sade Sati, historical timezones, unknown-time handling | Edit/delete chart, full dasha timeline (3 levels), graha drishti, yogakaraka, Chiron, choice of house system | Alternate ayanamsas (KP, Raman), more vargas, Ashtakavarga, Shadbala, progressions, solar return |
| Daily | Generic daily horoscope by sign (cached) | **Personal daily reading** (transits + dasha + Panchang), Panchang screen, Rahu Kaal | Monthly and yearly forecast (premium) |
| Compatibility | Western synastry scores (5 categories) + narrative | **Ashtakoota 36-guna**, Mangal dosha both charts, report delete | Composite chart, Dashakoota (South Indian) |
| Chat | Chart-grounded chat (non-streaming), 3 languages, quotas, safety | Streaming, bookmarks, feedback, suggestions, compatibility-linked chat | Voice input, conversation memory summaries |
| Engagement | — | Web Push daily reading, transit alerts, shareable cards, installable PWA | Weekly email digest (paid email tier), referrals |
| Monetisation | `subscription_tier` field, quotas enforced | **Premium** via Razorpay (UPI autopay), premium deep reports | International payments, gift subscriptions |
| i18n | AI responses in EN/HI/Hinglish | UI strings in Hindi | More Indian languages (Marathi, Tamil, Bengali) |

### 5.2 Premium (v1) gating

| Capability | Free | Premium (₹199/mo or ₹1,499/yr; intl $4.99/$39.99, OQ-2) |
|---|---|---|
| Natal chart (both systems), D9/D10, yogas, dashas | ✓ | ✓ |
| Personal daily reading, Panchang | ✓ | ✓ |
| AI chat replies | 5 / day | 60 / day |
| Compatibility reports | 3 / month | 50 / month |
| Ashtakoota detail and Mangal dosha | ✓ | ✓ |
| Transit calendar | next 30 days | next 12 months |
| Deep reports (yearly forecast, career, relationships), written by the premium model | — | 4 / month |
| Saved charts | 10 | 100 |
| Alternate calculation settings (v2) | — | ✓ |

**Never gated:** calculation accuracy, safety behaviour, data export or deletion.

## 6. Feature requirements

Each feature lists user stories, requirements and **acceptance criteria (AC)**. Endpoint IDs (A1, C1…) refer to `docs/api-contract.md`.

### 6.1 Accounts and authentication (MVP)

**Stories**

- As a visitor, I sign up with email or Google in under a minute.
- As a user, I verify my email with a 6-digit code.
- As a user, I reset a forgotten password.
- As a Google user, I can add a password later.
- As a user, I can delete my account and all data.

**Requirements**

- Registration needs name, email, a password of 8 characters to 72 bytes, a terms + privacy acceptance checkbox, and an **18+ confirmation** checkbox.
- A 6-digit OTP is emailed via Brevo. It's valid for 10 minutes, allows 5 attempts, and can be resent after 60 s (max 5 per day).
- Unverified users can create a chart and see the dashboard. AI features require verification.
- Google OAuth uses state + PKCE. It links to an existing account only when Google reports a verified email.
- JWT session of 7 days. Password reset revokes all sessions.

**AC**

1. Registering with an existing email returns `EMAIL_EXISTS` with a login hint. Registering with a common password returns `PASSWORD_TOO_COMMON`.
2. A wrong password shows "Incorrect email or password" **on the login page without logging out or reloading** (400, not 401; G-01).
3. Six wrong OTP attempts invalidate the code. Resend within 60 s is refused, with the remaining seconds shown.
4. The reset link works once and expires after 1 h. After a reset, previously issued tokens return 401.
5. Google sign-in for a new user lands on `/onboarding`; for an existing user with a chart, on `/dashboard`.
6. Account deletion removes every row tied to the user in one transaction, purges caches, sends a confirmation email, and returns to `/` logged out.
7. All auth endpoints are rate-limited as in `architecture.md` §7.

### 6.2 Onboarding and birth data capture (MVP)

**Stories**

- As a new user, I enter my birth details once, accurately, even if I'm unsure of the time.
- I can find my birthplace even if it's a small town.

**Requirements**

- **Fields:**
  - name
  - date of birth (1800-01-01 to today)
  - time of birth, with an "I don't know my exact time" toggle and an "approximate" option (morning, afternoon, evening, night maps to an approximate time, with the flag set; v1)
  - birthplace (autocomplete, ≥ 3 characters, 400 ms debounce)
- **Timezone is resolved by the server from coordinates**, using historical rules for that date. The UI shows it before submit, e.g. "Time zone on 21 Jul 1994: IST (UTC+5:30)". (G-05: remove the browser-timezone fallback.)
- DST edge cases:
  - A non-existent local time is rejected with a plain-language message.
  - An ambiguous time defaults to the first occurrence, with a "which one?" choice (v1).
- Pre-1970 or low-confidence timezone data shows a hint and lets the user enter the official UTC offset (v1).
- Unknown time: the chart is still created, with honest labelling (see §6.3).
- **Consent step** (one screen, before the first chart is saved): a plain-language explanation that birth details are used to compute the chart, and that computed chart facts (not the birth details themselves) are sent to AI providers to write readings. Shows the list of providers and links to the privacy notice. Checkbox: "I agree to AI processing" (required to use AI features; the chart works without it).

**AC**

1. A user who selects "Pune, Maharashtra, India" while their browser is set to America/New_York gets a chart computed in Asia/Kolkata. The UI displays that zone.
2. 02:30 on a US spring-forward date returns the `BIRTH_TIME_NONEXISTENT` message.
3. With an unknown time, onboarding completes. The dashboard shows "Rising: Unknown", with a link explaining why and how to add the time later (v1, chart edit).
4. Geocoding p95 is under 800 ms when the result is cached and under 2 s when it isn't. If both providers fail, the UI shows "Location search is having trouble" and keeps the form state.
5. Chart creation p95 is under 1.5 s end to end on the free tier (warm instance).
6. The LocationIQ (or Geoapify) attribution link is visible beside the place field.

### 6.3 Chart generation and accuracy (MVP; engine spec is normative)

**Requirements**

- Both systems are always computed and stored in one `chart_data` (schema: `astrology-engine.md` §9).
- **Western:** tropical, Placidus (Porphyry above 66° latitude), 10 planets + nodes, ASC/MC, 5 major aspects with stated orbs.
- **Vedic:** Lahiri ayanamsa, whole-sign houses from the sidereal lagna, mean node, 9 grahas (+ outer planets for completeness), nakshatra and pada, dignity, combustion, house lords, functional benefics/malefics, Vimshottari MD/AD, D9, D10, the MVP yoga set, Mangal dosha, Kaal Sarp, Sade Sati.
- **Unknown time:** Western rising is "Unknown" and houses are solar whole-sign. Vedic uses Chandra Lagna (Moon as the 1st house). The Moon sign and nakshatra are flagged if they change during the birth day, and the dasha is flagged approximate.
- Every chart stores provenance: engine version, ephemeris, ayanamsa, node type, UTC instant, offset, timezone source and confidence.
- Time-dependent values (current dasha, Sade Sati) are recomputed on read.

**AC**

1. All golden suites pass within their tolerances (`astrology-engine.md` §11). This is a CI gate.
2. Ketu is always present. Rashi and dignity strings match the contract spelling exactly (G-13).
3. A chart created under engine 1.x and read after a 2.0 release is recomputed lazily and returns the new `engine_version`.
4. The UI can show a "How this was calculated" panel from `metadata` alone.
5. The production ephemeris check fails readiness if the Swiss Ephemeris files are missing (no silent fallback to Moshier).

### 6.4 Dashboard and daily reading

**MVP**

- The dashboard shows Sun / Moon / Rising and the generic daily horoscope for the user's sun sign (R1), cached daily.

**v1: Personal daily reading (R3)**

It's generated from today's top factors:

- the Moon's transit house from the natal Moon
- slow-planet transits
- the current MD/AD
- Panchang tithi and nakshatra at the user's location
- the Rahu Kaal window

Content: a headline, a 90–150-word overview, four areas (love, career, wellness, money), each with an **engine-computed** score from 1 to 5 and 30–60 words, the key factors with plain-English labels, the best time window, an affirmation, and lucky number and colour (labelled "for fun").

- Generated **lazily** on the first open of the day (no cron cost for absent users) and cached until local midnight + 2 h.
- If the LLM fails, a template reading from the same factors, labelled "Simplified reading".

**AC**

1. Two loads on the same local day return identical content.
2. Changing the primary chart regenerates the reading.
3. Every reading lists ≥ 2 key factors. Each factor label matches a computed factor (validator).
4. With the LLM down, the dashboard still renders a reading within 1 s (template).
5. Users whose `astrology_system` is Vedic see moon-sign (rashi) based content first. Western users see sun-sign based content first (G-08).

### 6.5 Chart view (MVP data, v1 cleanup)

**Requirements**

- North/South Indian kundli chart toggle (already in the frontend).
- Planet table (rashi, degree, nakshatra-pada, house, dignity, retro, combust).
- Western wheel and aspect list.
- D9/D10 charts, yogas with strength and plain-language description, the dasha card, house lords with functional nature, and a settings strip ("Lahiri · Whole Sign · Sidereal").
- v1: **all derivations come from the API.** The frontend's client-side yoga, aspect and "core signature" logic is deleted (G-09).
- Each planet row and yoga has "Ask about this", which opens chat with a prefilled question and that factor as context.

**AC**

1. Every value displayed is traceable to `chart_data`. No astrology math remains in the frontend (v1, verified by grep in review).
2. Unknown-time charts visibly mark houses and lagna as Moon-based.
3. The chart renders correctly at 320 px width, and is keyboard- and screen-reader-navigable (each planet has a text equivalent).

### 6.6 Compatibility

**MVP**

The user picks one of their charts and enters partner details (same capture rules as onboarding) and a relationship type (romantic, friend, family, coworker).

- Deterministic **synastry scores**: overall 0–10, plus five categories (emotional, communication, romance, passion, long-term) with fixed keys.
- The top 10 inter-aspects, 3 strengths and 3 challenges, and a narrative written by the LLM *from* the scored factors.
- The partner chart is saved (deduplicated).
- Free: 3 per month.

**v1: Kundli matching**

- Ashtakoota 36-point breakdown (8 kootas with notes), Nadi/Bhakoot/Gana dosha flags, and Mangal dosha for both people.
- For romantic relationships the overall score blends Western and Vedic results 50/50.
- Orientation (bride/groom) is optional. Without it, the conservative score is shown and both are disclosed (OQ-4).

**Framing requirements**

- No score is ever described as whether a relationship "will work".
- Doshas are always presented with "traditional cancellations exist" and "many happy couples have this".
- The Varna koota is labelled "temperament (Varna)" and never framed in caste terms.

**AC**

1. The same two people with the same type always produce identical scores (determinism test).
2. A repeat request within 30 days returns the existing report without a new LLM call.
3. If either birth time is unknown, the report says so, and house- or ASC-based contributions are excluded.
4. Koota scores match the Prokerala-generated golden pairs exactly.
5. If the LLM fails, the report still returns, with scores and templated summaries.

### 6.7 AI astrologer chat

**MVP**

- Conversations list, new conversation, delete. Messages are persisted.
- Language selector: English, Hindi (Devanagari), Hinglish.
- Each answer is grounded via the pipeline in `llm-integration.md` §3:
  1. rule-based topic and timeframe
  2. ranked chart factors
  3. factor-keyed hybrid retrieval
  4. structured LLM output with citations
  5. validators (schema, citation subset, claim checker, unknown-time guard, safety, language)
  6. repair once, then fall back to another provider
- Answers are 120–300 words, end with an optional follow-up, and never state a position, date or dasha not in the facts.
- **Quotas:** free 5 replies a day (user-local midnight reset), premium 60. Requires a verified email and a chart.
- **Failure:** 503 with nothing persisted and no quota consumed. The UI shows its retry bubble.

**v1**

Streaming, bookmarks, thumbs up/down with reason, 3 suggested questions derived from top factors (no LLM cost), a "why this answer" expander listing the cited factors, and compatibility-linked conversations.

**AC**

1. For the 40 adversarial eval cases (injection, death prediction, child-sex prediction, a false user premise, demands for gemstones): 100 % handled per policy.
2. **Grounding:** 0 claim-checker violations in persisted answers across the eval set. In production, the repair rate stays under 5 % (alert at 2 % sustained).
3. When the user writes "my Moon is in Leo" but the chart says Taurus, the answer gently corrects it, citing the chart.
4. For an unknown-time chart, answers never cite the rising sign, house numbers or exact dasha dates.
5. The response is exactly `[userMessage, assistantMessage]`. `message_count` increments by 2 atomically. Two concurrent sends to one conversation give one 409.
6. Chat p95 is under 12 s non-streaming. With streaming (v1), the first token arrives in under 2.5 s.
7. A Hindi request yields ≥ 70 % Devanagari script. A Hinglish request yields Roman script.

### 6.8 Profile and privacy controls

**MVP**

Edit name, change or set password, list of saved charts, delete account.

**v1**

- **Export my data** (JSON).
- Consent toggles: AI processing, which can be withdrawn and disables AI features with an explanation; marketing email.
- Preferred language and default system (Vedic or Western).
- Notification preferences.
- "Log out of all devices".
- Edit or delete each chart.

**AC**

1. Withdrawing AI consent immediately blocks LLM calls for that user (403 `AI_CONSENT_REQUIRED`). Charts keep working.
2. The export contains every row the user owns and is produced within 10 s.
3. The Profile page shows "Set password" vs "Change password" correctly (`has_password`, G-17).

### 6.9 Panchang and timing (v1)

**Requirements**

- A daily Panchang for the user's current location (default: the primary chart's birthplace until they set a location): tithi, paksha, nakshatra, yoga, karana, vara, sunrise/sunset, Rahu Kaal.
- A **transit calendar**: upcoming ingresses, stations and exact transits to the user's natal points, plus dasha and antardasha changes. Free sees 30 days, premium 12 months.

**AC**

1. Panchang values match the golden fixtures (sunrise and Rahu Kaal within ±2 min).
2. Calendar events carry `window_start` / `exact_at` / `window_end`. Tapping one opens chat about that event.

### 6.10 Notifications (v1)

- **Web Push** (VAPID, no third-party service). It's opt-in, offered after the user has opened the daily reading on 2 separate days. Never on first visit.
- Types:
  - the daily reading teaser at the user's chosen local hour (default 07:00)
  - transit alerts: a slow-planet transit to a natal key point starts its window, or a dasha/antardasha change in the next 7 days; at most 2 per week
  - Sade Sati phase changes
- Email is used only for transactional messages on the free plan. A weekly digest is added only once a paid email tier is justified (`architecture.md` §11).
- Every notification has a one-tap "turn off this type".

**AC**

1. No push without explicit opt-in.
2. Delivery happens within ±15 min of the chosen hour.
3. A dead subscription (HTTP 404/410) is deleted.
4. No more than 1 daily push and 2 alerts per week per user.

### 6.11 Sharing (v1)

- Shareable cards (rendered client-side as SVG → PNG, with no new dependency):
  - "Big Three" (Sun, Moon, Rising)
  - Rashi + Nakshatra
  - the compatibility score
  - a daily-reading headline
- Cards contain **no birth date, time or place** unless the user explicitly toggles them on.
- The Web Share API is used where available; otherwise download.

**AC**

The default card reveals no birth details. Sharing doesn't create a public URL to any user data.

### 6.12 Premium and payments (v1)

- Razorpay Subscriptions (UPI autopay, cards) for INR. International payments are OQ-11.
- The webhook is idempotent (`payment_events.provider_event_id` is unique) and is the only writer of `subscription_tier`.
- Grace period: 3 days after a failed renewal.
- Cancel from Profile, effective at the end of the period.
- **Before the premium launch:** buy the Swiss Ephemeris Professional License, or confirm continued AGPL compliance (D-02, OQ-1).

**AC**

1. A replayed webhook doesn't double-apply.
2. A downgrade restores free quotas at the next period boundary.
3. Premium status appears within 10 s of payment success.

### 6.13 Internationalisation

- **MVP:** AI output in English, Hindi and Hinglish. Astrology terms follow a fixed glossary per language: Surya, Chandra, rashi names, nakshatra names, "dasha".
- **v1:** UI strings extracted into message catalogs (`en`, `hi`). Dates use the locale format. Devanagari typography is supported by the design system's font stack (design-system agent).
- Content tone is reviewed by a native Hindi speaker before the v1 launch.

## 7. Screen-by-screen UX requirements

These are behavioural only. Visual styling, tokens and motion values come from `design-system/cosmic-intelligence/MASTER.md`.

### 7.0 Reusable design language (applies to all screens)

- Every screen is composed only from shared primitives in `frontend/src/components/ui/`: Button, Input, Select, Toggle, Card/GlassCard, Dialog, Toast, Tabs, Skeleton, EmptyState, ErrorState, Badge, Tooltip, Sheet. Domain components (`components/astrology/`, `components/chat/`) build on those primitives.
- A new screen may not introduce one-off colours, spacing or font sizes. It extends the design tokens instead. This is what makes the design language reusable across features and future products.
- **Standard states:** every data-backed component implements **loading (skeleton), empty, error (with retry), degraded (e.g. "Simplified reading") and success**. Each has a single shared implementation.
- **Accessibility:** WCAG 2.2 AA (contrast, focus visible, 44 px targets, labels, `prefers-reduced-motion`). Lucide icons only, with no emoji as icons. Every chart has a text alternative.
- Copy uses the brand name **Nakshion** only.

### 7.1 Landing (`/`)

- **Value proposition in one line:** accurate Vedic + Western charts, AI explanations grounded in your chart.
- One primary CTA ("Get my free chart") and one secondary ("How it works": computed facts → classical meaning → your reading).
- A sample reading with visible factor citations, to demonstrate the differentiator.
- A trust row: "Swiss Ephemeris precision · Your birth data never leaves our servers for AI · Delete anytime".
- No fake testimonials or fabricated user counts.
- **AC:** LCP < 2.5 s on 4G mid-range Android; CTA visible above the fold at 360×640; no layout shift > 0.1.

### 7.2 Auth (`/auth`, `/verify`, `/forgot-password`, `/reset-password`, `/auth/callback`)

- Tabs for login and signup. Google button first.
- Errors appear inline and persist (G-01).
- The OTP input is one field with `inputmode="numeric"`, `autocomplete="one-time-code"` and paste support. It shows the resend countdown.
- After login, if `email_verified=false`, route to `/verify` (G-03).
- The OAuth callback strips the token from the URL immediately (`history.replaceState`).

### 7.3 Onboarding (`/onboarding`)

- Three short steps: **(1) name + date, (2) time (or unknown / approximate), (3) place → consent → generate.**
- The step indicator shows progress. Back navigation keeps the entered values. The draft is saved locally until submit.
- The resolved timezone is shown under the place field. Invalid DST times get an inline explanation.
- During generation (≤ 1.5 s typically), a short purposeful animation runs. Under reduced motion, it's a static progress message.
- On success, land on the dashboard with a one-time "Here's your chart in 3 lines" card (Big Three + rashi/nakshatra + current dasha).

### 7.4 Dashboard (`/dashboard`)

- **Order:**
  1. Today's reading (personal in v1, else by sign)
  2. Big Three + rashi/nakshatra chip
  3. Current dasha card
  4. Today's Panchang / Rahu Kaal (v1)
  5. Quick actions: Ask, Compatibility, Full chart
- No chart yet: an empty state with a single "Add birth details" CTA.
- Remaining free questions are visible on the Ask card (v1 `quota`).
- Pull-to-refresh doesn't regenerate the reading (it's stable for the day).

### 7.5 Chart (`/chart`)

- Defaults to the user's preferred system. A tab switches Vedic / Western.
- A North/South toggle is persisted per user (local preference).
- Tapping a planet shows a bottom sheet with its placement facts, a 2-line meaning (from the KB, no LLM) and "Ask about this".
- A collapsible "How this was calculated" section.

### 7.6 Chat (`/chat`)

- A conversation list (sidebar on desktop, sheet on mobile). Each item shows its title and relative time.
- **Composer:**
  - A language selector that remembers the last choice.
  - The character limit (2,000) is shown from 1,600 characters.
  - Enter sends; Shift+Enter adds a newline.
  - Send is disabled while a reply is in flight.
- An empty conversation shows 3–4 suggested questions personalised from top factors (v1), plus static suggestions in MVP.
- Answers render light Markdown. A "Based on:" chip row lists the cited factors (v1). Thumbs up/down (v1).
- **Error states:**
  - quota reached: shows the reset time and an upgrade CTA (v1)
  - email not verified: "Verify now" CTA
  - no chart: "Add birth details" CTA
  - AI unavailable: inline retry, with the user's text preserved
- A safety reply (crisis) renders as a distinct, calm card with helpline links. It has no astrology styling.

### 7.7 Compatibility (`/compatibility`)

- Form: select "your chart" (defaults to primary), then partner details using the same place, time and timezone behaviour as onboarding, then the relationship type.
- **Results:**
  - Overall score with a one-line summary.
  - Five category bars with summaries.
  - Ashtakoota table (v1): 8 rows with score/max and notes, total /36, dosha notes with the framing copy.
  - Strengths and challenges.
  - Top aspects (expandable).
  - "Ask about this match" opens a linked chat (v1).
- Past reports list (v1), with delete.

### 7.8 Profile (`/profile`)

- Sections: Account, Charts, Preferences, Notifications (v1), Privacy & data (export, consents, delete), Subscription (v1).
- Delete account needs a confirmation dialog in which the user types "DELETE". The dialog explains what's removed and that it can't be undone.

## 8. Prediction quality: what "most accurate" means here

Astrology's predictive validity isn't something we can claim or measure. What we **can** guarantee and measure:

| Dimension | Definition | How we ensure it | Measure |
|---|---|---|---|
| **Calculation accuracy** | Positions, houses, ayanamsa, nakshatra, dasha, vargas and kootas exactly match reference tools | Swiss Ephemeris + golden tests + versioned engine | Golden pass rate (100 %) |
| **Faithfulness** | Readings never contradict the computed chart | Facts-only prompting, citations, claim checker, repair | Violations after repair = 0; repair rate < 5 % |
| **Classical fidelity** | Interpretations agree with the classical meanings of the cited factors | Factor-keyed RAG over the curated KB; LLM-judge "coherence" criterion; astrologer spot review | Judge ≥ 4.0/5 |
| **Personal specificity** | The answer uses *this* user's factors and timing windows, not sun-sign filler | Ranked factor selection; judge "personalisation" and "specificity" | ≥ 4.0/5; ≥ 2 cited factors per answer |
| **Timing precision** | Dates come from computed windows (exact transit dates, dasha boundaries) | Event finder + "dates only from factor windows" rule | 100 % of dates traceable |
| **User-perceived quality** | Users find it accurate and helpful | Thumbs-up rate, D30 retention | ≥ 80 % up; D30 ≥ 15 % |

The full pipeline and its guards are in `docs/llm-integration.md`.

## 9. Architecture summary

- **Frontend:** React 19 + TypeScript + Vite + Tailwind 4 (existing). API access only through `src/services/`.
- **Backend:** FastAPI (rebuilt), routers → services → engine/DB, async SQLAlchemy + asyncpg, Alembic, a single uvicorn worker on Render free, ephemeris on a single-thread executor.
- **Data:** Neon Postgres (+ pgvector for RAG), Upstash Redis (TTL state and caches only), quotas in Postgres.
- **AI:**
  - Gemini (paid tier): `gemini-3.8-flash` for chat, `gemini-3.5-flash-lite` for daily, horoscope and compatibility text.
  - Claude Haiku 4.5 as the cross-vendor fallback; Claude Sonnet 5.5 for premium deep reports and the eval judge.
  - All behind a provider-abstraction router with timeouts, circuit breaker, budget guard and templates.
- **RAG:** the curated KB (`backend/knowledge_base/*.md`), chunked and embedded **locally** (fastembed bge-small, ONNX), stored in **pgvector**. Hybrid vector + FTS retrieval keyed by computed chart factors.
- **Integrations:** LocationIQ (geocoding, with Geoapify fallback), Brevo (email), Google OAuth, cron-job.org (keep-awake + jobs), Razorpay (v1).

Full detail is in `docs/architecture.md`. The frozen HTTP contract is in `docs/api-contract.md`.

## 10. Non-functional requirements

### 10.1 Performance (warm instance, Render free)

| Operation | p95 target |
|---|---|
| Cached GET endpoints (charts list, horoscope, conversations) | < 300 ms |
| Chart create (full compute + insert) | < 1.5 s |
| Geocoding (cached / uncached) | < 300 ms / < 2 s |
| Chat (non-streaming) | < 12 s; hard deadline 25 s |
| Chat first token (v1 streaming) | < 2.5 s |
| Personal daily reading (cold / cached) | < 6 s / < 300 ms |
| Frontend LCP (4G, mid-range Android) | < 2.5 s; JS bundle for the landing route < 200 KB gzip |

Cold start after a spin-down is about 1 minute on Render free. The keep-awake ping avoids it, and the UI shows a friendly "waking up" state if the API takes more than 5 s.

### 10.2 Reliability

- Target 99.5 % monthly availability, which is realistic on free tiers.
- No single external dependency except Postgres can take down charts or dashboards. LLM, geocoder, Redis and email failures degrade gracefully (`architecture.md` §8).
- All multi-step writes are transactional. Counters and the primary-flag flip are atomic at the DB level.
- Backups: Neon restore window + a weekly encrypted dump, with a quarterly restore drill.

### 10.3 Security

- JWT (HS256, at least 32-byte secret, `token_version` revocation). bcrypt cost 12. OTPs and reset tokens are stored hashed.
- Ownership checks on every resource. Cross-user access gives 404 (IDOR test suite).
- Rate limits on every LLM-, geocoding- and email-triggering endpoint, plus auth brute-force protection (`architecture.md` §7).
- **Prompt-injection defence:** user text is delimited, KB text is labelled non-authoritative, the system rules can't be overridden, and output is filtered. No tools or actions are exposed to the LLM, so injection can at worst produce bad text, which the validators catch.
- Security headers. Strict CORS allow-list. No secrets in the repo. `pip-audit` / `npm audit` / gitleaks run in CI.
- v2: a short-lived access token plus an httpOnly refresh cookie; a one-time OAuth code (G-04).

### 10.4 Observability

- JSON logs with request IDs and a PII scrubber. An `llm_usage` row for every LLM call.
- Owner alerts: 5xx bursts, LLM budget at 80 %, repair rate above 2 %, Redis or Neon quota at 70 %.
- Weekly owner digest email.

### 10.5 Accessibility

WCAG 2.2 AA, as in §7.0. Charts have tabular and text equivalents. The full app is keyboard-operable. Screen-reader labels are provided for chart glyphs.

## 11. Privacy, safety and compliance

### 11.1 Data classification

| Data | Class | Handling |
|---|---|---|
| Birth date, time, place, coordinates | **Sensitive personal data** (can identify people and reveal family information) | Stored in Postgres with Neon encryption at rest, TLS in transit. **Never sent to LLM providers** (they receive computed factors only). Never logged |
| Chat content | Personal; may include health, relationship or finance matters | Stored for the user's history. Sent to the LLM for the current turn only. Never logged. Never used for training. Eval sets use synthetic charts |
| Email, name | Personal | The name may be passed to the LLM as a first name only. The email is never passed |
| Usage and cost logs | Pseudonymous | `user_id` hashed in logs; `llm_usage.user_id` set to NULL on account deletion |

### 11.2 Regulatory posture

- **India DPDP Act 2023 + Rules 2025.** Full obligations apply from **13 May 2027**. We comply at launch:
  - notice in plain English, and in Hindi from v1 (the Act allows any 8th Schedule language on request)
  - free, specific, informed consent with easy withdrawal (§6.8)
  - purpose limitation
  - erasure on request (account and per-item deletion)
  - grievance contact published in the privacy notice, with a response within 7 days
  - breach notification to the Data Protection Board and affected users without delay
  - reasonable security safeguards (§10.3)
  - no processing of children's data: 18+ only, with a confirmation checkbox
- **GDPR (EU users).** Lawful basis is consent for AI processing and contract for the core service. Users have rights of access and portability (export), erasure and rectification (chart edit). We keep a record of processors. Breach notification within 72 h. Data is processed outside the EU (Singapore/US), with the processors' standard contractual clauses.
- **Sub-processors** (listed in the privacy notice): Render, Neon, Upstash, Google (Gemini API, paid tier; OAuth), Anthropic, Brevo, LocationIQ, Geoapify, and Razorpay (v1).
- **Regions:** deploy Render and Neon in **Singapore** (closest supported region to India) unless the owner chooses otherwise (OQ-14).
- **Retention:**
  - Account data: until deletion.
  - Inactive accounts: after 24 months, a reminder email, then deletion after 30 more days (v1).
  - Logs: Render's retention (days).
  - `personal_readings`: 90 days.
  - Password-reset rows: 24 h after expiry.
- **Gemini free tier is prohibited for production traffic** (unpaid-service data may be used for product improvement and human review; D-06).

### 11.3 Content safety

The policy is specified in `docs/llm-integration.md` §8 and summarised here:

- No predictions of death, lifespan or child sex.
- No medical, legal or investment directives.
- No fatalistic dosha framing. No paid-remedy promotion.
- Crisis detection with helplines (Tele-MANAS 14416).
- No caste framing.
- A permanent footer disclaimer: "For self-reflection and entertainment. Not a substitute for professional advice."

## 12. Testing and release gates

The detail is in `architecture.md` §10.2. **A release is blocked unless** all of these hold:

- golden and property engine tests pass
- API tests cover every contract endpoint, including its documented errors
- the contract shape tests pass against `frontend/src/types/index.ts`
- the IDOR suite passes
- the migration round-trip passes
- the AI eval gates pass for any changed prompt, model or retrieval setting
- the Playwright happy path passes
- there are no high or critical dependency vulnerabilities

## 13. Metrics

| Funnel stage | Metric | Target (6 mo) |
|---|---|---|
| Acquisition | Registered users | 1,000 |
| Activation | Chart created within 24 h of signup | ≥ 75 % |
| Engagement | Weekly actives opening the daily reading ≥ 3 times/week | ≥ 35 % |
| AI value | Users sending ≥ 1 chat in their first week | ≥ 50 %; thumbs-up ≥ 80 % |
| Retention | D7 / D30 | ≥ 25 % / ≥ 15 % |
| Monetisation (v1) | Premium conversion of MAU | ≥ 3 % |
| Quality | Golden pass rate; grounding violations after repair; repair rate | 100 %; 0; < 5 % |
| Cost | LLM $ per free MAU (typical) | ≤ $0.25 |
| Reliability | Monthly availability; chat 503 rate | ≥ 99.5 %; < 1 % |

Measurement uses the first-party events table (v1). There are no third-party trackers.

## 14. Cost model and budget

| Item | Monthly cost at ~300 MAU | At ~1,000 MAU |
|---|---|---|
| Render (backend + static frontend) | $0 | $0, or $7 if cold starts hurt |
| Neon Postgres | $0 | $0, or $19 once over 350 MB |
| Upstash Redis | $0 | $0 |
| LocationIQ / Geoapify | $0 (attribution) | $0 |
| Brevo | $0 (≤ 300/day) | $0–9 |
| Gemini + Claude (LLM) | ≈ $40–65 | ≈ $130–210, capped by the budget guard (OQ-3) |
| Domain | ≈ $1 | ≈ $1 |
| Swiss Ephemeris Professional License | CHF 750 one-off before premium (OQ-1) | — |

LLM unit economics are in `docs/llm-integration.md` §10. A free user costs about $0.13–0.21 a month typically, with a worst case around $1.35 under the 5/day cap. A premium user costs about $1.1–1.9 against a ₹199 (~$2.25) price.

The cost risk on the Gemini 3.8 Flash promo price ending 2026-12-31 is covered by OQ-12: re-run the bake-off in December, and Flash-Lite is the fallback.

## 15. Decision log

| ID | Decision | Rationale | Alternatives rejected |
|---|---|---|---|
| D-01 | **Build the calculation engine on pyswisseph + Swiss Ephemeris files**; no runtime astrology API | Professional accuracy, zero marginal cost, no vendor outage; every API wraps the same library | Prokerala / AstrologyAPI / FreeAstrologyAPI / VedicAstroAPI (cost, rate limits, latency); Kerykeion and flatlib as dependencies |
| D-02 | **AGPL compliance (publish the backend source) until premium; buy the CHF 750 Professional License before charging** | The licence is legally required for a closed network service; a one-off cost | Ignoring the licence; Skyfield-based rewrite (months of work and risk) |
| D-03 | **Compute both systems always; Vedic (Lahiri, whole sign, mean node) is the default view, with a per-user preference** | Indian-leaning audience; enthusiasts want both; the frontend is already Vedic-first | Western-only (v1 PRD) |
| D-04 | **Timezone resolved server-side from coordinates with historical zoneinfo + pinned tzdata** | The browser-tz fallback is a severe accuracy bug | Trusting the client tz |
| D-05 | **Unknown time:** Chandra Lagna (Vedic), solar houses (Western), flags everywhere, the LLM barred from house/angle claims | Honest and traditional; prevents confident wrong readings | Silent noon chart (v1 PRD) |
| D-06 | **LLM: Gemini paid tier as primary (3.8 Flash chat, 3.5 Flash-Lite bulk), Claude Haiku 4.5 as fallback, Claude Sonnet 5.5 for premium and judging; the free Gemini tier only for synthetic evals** | Best quality per dollar; cross-vendor resilience; free-tier data terms are unsuitable for sensitive data | GPT-4-class primary (cost); free tier in production (privacy) |
| D-07 | **Migrate to the `google-genai` SDK** | `google-generativeai` reached end of support on 2025-11-30 | Staying on the deprecated SDK |
| D-08 | **pgvector on Neon replaces chromadb** | Render's ephemeral disk; RAM; one store; hybrid FTS; trivial size | chromadb on disk; a hosted vector DB |
| D-09 | **Local embeddings (fastembed bge-small, ONNX); corpus embedded offline; retrieval keyed by computed factors** | Owner preference for local; fits 512 MB; language-agnostic because the factor keys are English | sentence-transformers/torch (RAM); API embeddings |
| D-10 | **One LLM call per user action; rule-based topic and timeframe classification** | Cost and RPM; latency | LLM classifier + LLM rewrite + answer |
| D-11 | **All scores are deterministic; the LLM only explains them** | Reproducibility, trust, testability | LLM-assigned scores |
| D-12 | **Geocoding: LocationIQ primary, Geoapify fallback, 30-day cache** | Free quota, OSM coverage, caching allowed | Google Places (cost, caching restrictions); public Nominatim (policy) |
| D-13 | **Quotas in Postgres (`usage_counters`); Redis for TTL state and caches only; in-process general rate limiting** | Upstash 500k-command budget; atomicity | All counters in Redis |
| D-14 | **Keep the 7-day JWT in localStorage for MVP**; refresh cookie in v2 | Frontend compatibility; sessions revocable via `token_version` | Breaking auth during the rebuild |
| D-15 | **Login and change-password failures return 400, not 401** | The frontend's 401 interceptor would log the user out | Conventional 401 |
| D-16 | **Google OAuth only; Facebook dropped** | Low value for the audience; app-review overhead | Facebook Login |
| D-17 | **Account deletion is an immediate hard delete** | Simplest compliant erasure; no deleted-PII backlog | 30-day soft delete |
| D-18 | **PWA + Web Push (VAPID); no native apps yet** | Zero cost; one codebase | React Native, OneSignal/FCM |
| D-19 | **Razorpay for v1 payments (INR, UPI autopay)** | Audience fit | Stripe-only (weak on UPI). International payments open (OQ-11) |
| D-20 | **Anonymous horoscope "today" = Asia/Kolkata; authenticated = the user's timezone** | Primary audience | UTC (wrong day boundary for India) |
| D-21 | **No third-party analytics in MVP**; a first-party events table | Privacy positioning; DPDP | GA / Mixpanel |
| D-22 | **Ashtakoota without roles shows the conservative orientation plus the alternate** | Avoids forced gender capture; honest | Mandatory gender field |
| D-23 | **Hindi and Hinglish are first-class from MVP in AI output; UI translation in v1** | Biggest differentiator for the persona at the lowest cost | English-only MVP |

## 16. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| LLM states a wrong position or date | Medium | High (trust) | Facts-only prompts, claim checker, repair, eval gates, production alert |
| AGPL non-compliance discovered | Low | High | D-02; footer source link before launch |
| Free-tier quota exhaustion (Neon CU-hours, Upstash commands, Brevo 300/day) | Medium | Medium | No-DB health ping, L1 cache, Postgres quotas, monitoring at 70 %, scale triggers (`architecture.md` §11) |
| LLM cost overrun (promo price ends; heavy users) | Medium | Medium | Daily and monthly budget guard, quotas, Flash-Lite fallback, December re-bake-off |
| Render 512 MB OOM with local embeddings | Medium | Medium | Lazy load, `EMBEDDINGS_RUNTIME=off` switch (factor keys pre-embedded) |
| Historical timezone errors (pre-1970, India War Time) | Medium | High for those users | tzdata, confidence flag, user offset override, golden tz fixtures |
| Ashtakoota table disagreements between schools | Medium | Medium | One cited reference + Prokerala golden pairs; document the convention |
| Harmful-advice incident (health, finance, dosha fear) | Low | High | Safety policy, filters, adversarial evals, crisis path |
| Knowledge-base copyright concern | Low | Medium | KB contains synthesised summaries only; review before launch (OQ-7) |
| Solo-dev bus factor | High | High | These docs; tests as specification; boring stack |

## 17. Open questions

| ID | Question | Proposed default | Owner decision needed by |
|---|---|---|---|
| OQ-1 | Publish the backend source under AGPL, or buy the Swiss Ephemeris Professional License (CHF 750) now? | AGPL through beta; buy before premium | Before public launch |
| OQ-2 | Premium price points (₹199/mo, ₹1,499/yr; $4.99/$39.99 intl)? | As listed | Before v1 |
| OQ-3 | Monthly LLM budget cap (default $40) and free chat quota (default 5/day)? | $40 and 5/day for beta; review after 4 weeks of data | Before launch |
| OQ-4 | Ashtakoota roles: offer an optional "traditional roles" selector, or keep the conservative orientation only? | Optional selector in v1 | v1 |
| OQ-5 | Default system for users born outside South Asia: Western view first? | Ask at onboarding with a smart default from birthplace country | MVP frontend |
| OQ-6 | Can a practising Vedic astrologer review the functional-nature table, yoga rules and 20 eval answers per release? | Paid one-off review (~10 h) | Before launch |
| OQ-7 | Confirm the KB files are original syntheses (no verbatim copyrighted text) | Owner review | Before launch |
| OQ-8 | Mean or true node for Vedic default? | Mean (configurable) | Before golden fixtures are generated |
| OQ-9 | Separate partner charts from "my charts" in the UI list? | Yes, via a v1 filter (`relationship`) | v1 |
| OQ-10 | Allow exporting chat history to PDF (premium)? | No in v1 (JSON export only) | v1 |
| OQ-11 | International payments: Razorpay international, or add Stripe? | Razorpay international cards first | v1 |
| OQ-12 | Re-run the model bake-off when Gemini 3.8 Flash promo pricing ends (2026-12-31)? | Yes, scheduled for mid-December 2026 | Dec 2026 |
| OQ-13 | Approve adding `sentry-sdk` (error tracking, free tier)? | Yes, with PII scrubbing | MVP |
| OQ-14 | Hosting region for Render and Neon (Singapore proposed)? | Singapore | Before provisioning |

---

## Appendix A: Glossary

| Term | Meaning |
|---|---|
| Tropical / sidereal zodiac | The zodiac measured from the equinox (Western) or from the fixed stars (Vedic). They differ by the **ayanamsa**, about 24° in 2026 (Lahiri) |
| Lagna / Ascendant / Rising | The sign rising on the eastern horizon at birth; needs an accurate birth time |
| Rashi | Sign (Vedic). The Moon's rashi is the basis of Indian horoscopes |
| Nakshatra / pada | One of the 27 lunar mansions (13°20′ each) / one of its four quarters (3°20′) |
| Vimshottari dasha | A 120-year planetary period system that starts from the Moon's nakshatra. MD = mahadasha, AD = antardasha |
| D9 Navamsa, D10 Dashamsa | Divisional charts used for marriage/inner strength and career respectively |
| Graha drishti | Vedic planetary aspects (all planets aspect the 7th; Mars, Jupiter and Saturn have special aspects) |
| Yoga / dosha | A named planetary combination (beneficial / challenging) |
| Sade Sati | Saturn's roughly 7.5-year transit over the 12th, 1st and 2nd signs from the natal Moon |
| Ashtakoota / Guna Milan | An 8-factor, 36-point Vedic compatibility method using both Moons |
| Panchang | The Vedic almanac: tithi, vara, nakshatra, yoga, karana |
| Rahu Kaal | A daily inauspicious period, 1/8 of daylight, varying by weekday |
| Synastry | Comparison of two charts via inter-aspects (Western) |
| Factor | A computed, ID'd astrological fact the AI must cite (`astrology-engine.md` §6.4) |

## Appendix B: Sources (retrieved 2026-09-30 to 2026-10-01)

**Calculation and licensing**

- Swiss Ephemeris price list and licence: https://www.astro.com/swisseph/swephprice_e.htm ; https://www.astro.com/swisseph/swisseph.htm
- Swiss Ephemeris AGPL in SaaS (analysis): https://vedika.io/blog/swiss-ephemeris-agpl-license-astrology-saas ; https://roxyapi.com/blogs/swiss-ephemeris-explained-developers
- Kerykeion (AGPL-3.0, sidereal modes): https://github.com/g-battaglia/kerykeion ; https://pypi.org/project/kerykeion/

**Astrology APIs (build vs buy)**

- Prokerala pricing and credits: https://api.prokerala.com/pricing ; https://api.prokerala.com/api-credits
- AstrologyAPI.com pricing overview: https://astrologyapi.com/blog/best-astrology-api ; https://vedika.io/blog/astrology-api-pricing-real-costs-2026
- FreeAstrologyAPI / FreeAstroAPI free tiers: https://freeastrologyapi.com/pricing ; https://www.freeastroapi.com/guide/best-free-astrology-api-2026
- VedicAstroAPI pricing: https://vedicastroapi.com/pricing/

**LLM providers**

- Gemini pricing: https://ai.google.dev/gemini-api/docs/pricing
- Gemini models (IDs, stable vs preview): https://ai.google.dev/gemini-api/docs/models
- Gemini rate limits (viewed in AI Studio): https://ai.google.dev/gemini-api/docs/rate-limits ; free-tier summaries: https://pecollective.com/tools/gemini-free-tier-guide/
- Gemini API terms (unpaid-services data use): https://ai.google.dev/gemini-api/terms ; https://ai.google.dev/gemini-api/docs/logs-policy
- `google-generativeai` deprecation: https://github.com/google-gemini/deprecated-generative-ai-python ; https://ai.google.dev/gemini-api/docs/libraries
- Claude pricing: https://platform.claude.com/docs/en/about-claude/pricing
- OpenAI pricing (third-party summaries; the official page blocked automated fetch): https://www.cloudzero.com/blog/openai-pricing/ ; https://www.morphllm.com/openai-api-pricing

**Embeddings and vector store**

- FastEmbed: https://qdrant.tech/articles/fastembed/ ; bge-small-en-v1.5 sizes: https://huggingface.co/BAAI/bge-small-en-v1.5/discussions/10
- pgvector on Neon (all plans, HNSW): https://neon.com/docs/extensions/pgvector

**Infrastructure**

- Render free-tier limits (0.1 CPU / 512 MB, 15-min spin-down, ephemeral FS, 750 h): https://agentdeals.dev/vendor/render ; https://www.srvrlss.io/provider/render/
- Neon free-plan limits: https://neon.com/faqs/free-plan-limits-and-quotas
- Upstash Redis pricing: https://upstash.com/pricing/redis
- LocationIQ pricing (5k/day, 2 rps, attribution): https://locationiq.com/pricing
- Geoapify pricing and caching terms: https://www.geoapify.com/pricing/ ; https://www.geoapify.com/address-autocomplete/
- Brevo free plan (300 emails/day, shared marketing + transactional): https://www.brevo.com/bulk-email-service/ ; https://mailflowauthority.com/esp-reviews/brevo-transactional-review

**Privacy law**

- DPDP Rules 2025 timeline (notified 13 Nov 2025; full compliance 13 May 2027): https://www.seclore.com/fundamentals/dpdp-rules-2025-compliance-guide/ ; https://techobserver.in/news/egov/dpdp-compliance-deadline-may-2027-india-data-protection-328129/

> Prices and quotas change. Re-verify before any pricing or capacity decision; model IDs and limits are configuration, not code.

## Appendix C: What changed from PRD v1.0

| Area | v1.0 (Mar 2026) | v2.0 (this) |
|---|---|---|
| Stack | Node/Express, Prisma, D3, Socket.io, Google Places, SendGrid, OneSignal, Stripe | FastAPI + SQLAlchemy (actual stack), custom SVG charts, LocationIQ, Brevo, Web Push, Razorpay |
| Astrology | Western-only, Placidus, noon default for unknown time | Vedic + Western; Lahiri, whole sign, nakshatra, dasha, D9/D10, yogas, doshas, Ashtakoota, Panchang; honest unknown-time handling; historical tz |
| AI | GPT-4 Turbo / Gemini 1.5 / Claude 3, prompt-only | Current models with a provider router; facts → rules → RAG → LLM with validators; evals; safety policy |
| RAG | none | Curated KB, local embeddings, pgvector |
| Targets | 10k users in 3 months, $50K MRR, 99.9 % uptime, $75–155K budget | Solo, free-tier, 1k users in 6 months, cost per user in cents |
| API | `/api/...` ad hoc, with a success envelope | Frozen `/api/v1` contract matching the existing frontend, plus gap list and v2 plan |
| Removed | Facebook login, community, native apps, SSR, admin panel | Deferred or non-goals |
