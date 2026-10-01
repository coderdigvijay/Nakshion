# Onboarding — birth details (`/onboarding`)

**User goal:** enter birth details correctly, once, without anxiety.
**Primary action:** `Cast my chart` (gold, full-width on mobile).
**Why it matters:** wrong data = every reading wrong. This screen optimises for **accuracy and confidence**, not speed alone.

## Flow: one card, three short steps (progressive disclosure)

The current single long form (name, date, time, checkbox, place) is fine in length, but users make D/M and AM/PM errors and don't know why time matters. Split into steps inside one card; each step validates before Next.

| Step | Fields | Helper copy |
|---|---|---|
| 1 · You | Name (for the chart label, "Optional" if account name exists) · Gender is **not** asked unless a feature needs it | "This is how we'll label your chart." |
| 2 · When | BirthDateField · BirthTimeField (+ "I don't know my exact time" → time-of-day chips + info note) | "Birth time sets your Lagna (Ascendant). Check a birth certificate if you can." |
| 3 · Where | LocationAutocomplete (+ resolved timezone & coordinates caption) | "We use the place to find the exact sky and time zone." |
| Review | Summary card: "Asha · Tue 14 Mar 1995 · 6:42 AM · Varanasi, India (UTC+05:30)" each row with `Edit` link → step | Primary `Cast my chart` |

## Layout

| | 375px | ≥768 | ≥1024 |
|---|---|---|---|
| Shell | No app nav; minimal header: logo + "Step 2 of 3" + `Exit` ghost | same | same |
| Card | full-bleed `surface` card, `rounded-sheet` top only, p-5 | centred `max-w-form`, `rounded-sheet`, p-8 | + left illustrative column (zodiac art / slow-drawing kundali), 5/7 split |
| Progress | 3 segments 4px tall, `accent` filled, `elevated` empty, under the header | same | same |
| Actions | sticky bottom bar: `Back` ghost + `Next` primary (full-width, safe-area padding) | inline at card bottom, right-aligned | same |

Step transitions: content x 16→0 + opacity, 250 ms enter; reduced motion: crossfade.
Keyboard: Enter = Next when valid; focus moves to the step heading on step change (`tabindex=-1` heading, announced).

## Casting state (after submit)
Full-card state, not a separate route:
- ChartWheel lines drawing in (600 ms) using real data as soon as API returns; *before* it returns, an empty North-Indian frame draws slowly (2.4 s ease-in-out, loop allowed here — this is a loading indicator).
- Progress copy (one line, `text-title`, `aria-live="polite"`): "Finding the sky over Varanasi…" → "Placing nine grahas…" → "Calculating your dasha periods…" — tied to elapsed time (0 / 2 / 4 s), last one holds.
- > 10 s: caption "Still calculating — this can take up to 30 seconds on first use." (free-tier cold starts are real; say so).
- Success → `/dashboard` with a one-time toast "Your chart is ready" and the dashboard's Big Three animating in.
- Failure: stay on Review step, inline error card with the server message mapped to human copy + `Try again`. Never lose entered data.
- Reduced motion: static frame + text progression.

## Validation copy
- Date: "Enter a real date between 1900 and today."
- Time: "Hour 1–12 and minute 0–59" (or 0–23 in 24h).
- Place not selected: "Choose a place from the list so we can find its exact coordinates."

## Acceptance
- Works with keyboard only; screen reader announces step changes and errors.
- No `type="date"` / `type="time"` native inputs.
- Time-unknown path produces a chart with the "Lagna approximate" badge downstream.
