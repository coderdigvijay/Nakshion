# Dashboard / Today (`/dashboard`)

**User goal:** "What does today hold for me, and what should I ask?"
**Primary action:** read today's reading → `Ask about today` (ai button inside the reading card). There is **no gold button** on this screen when a chart exists — the reading is the hero (P1, P3). Gold appears only as accent marks (Lagna in Big Three, current dasha).

## Section order

1. **Greeting** — `text-h1` Fraunces: "Good evening, Asha" (time-aware; Hindi: "शुभ संध्या, आशा"). Sub: today's date + tithi, `fg-secondary`. No gradient-text name.
2. **Big Three** — Sun · Moon · Lagna as `ZodiacBadge role` variant in a 3-up row. Each tappable → chart section. Moon additionally shows nakshatra ("Rohini"). Lagna gets the `accent` ring; "approximate" Badge if no birth time.
3. **DailyReadingCard (full, `feature`)** — the hero.
4. **Current period** — compact DashaTimeline summary: "Shani Mahadasha → Budha Antardasha · until Aug 2027" + mini progress bar of the antardasha (accent) + `View timeline` link.
5. **Ask Nakshion** — 3 suggestion Chips generated from the chart + "Open chat" link. (Replaces today's generic "AI Oracle" card copy.)
6. **Your chart** — ChartWheel `thumbnail` 160px + 3-line summary + `Open full chart` link (interactive Card).
7. **Compatibility** — if reports exist: last 2 as compact rows (avatars + score + band); else EmptyState-lite row with `Check compatibility` link.

## Layout

| | 375px | ≥768 | ≥1024 (12-col, `max-w-app`) |
|---|---|---|---|
| Greeting | full | full | cols 1–12 |
| Big Three | 3-up, 104px tall each, gap 8 | 3-up gap 16 | cols 1–8 (beside greeting on xl) |
| Reading | full | full | cols 1–8, rows span 2 |
| Current period | full | half | cols 9–12 |
| Ask | full, chips scroll horizontally | half | cols 9–12 |
| Chart | full | half | cols 1–4 |
| Compatibility | full | half | cols 5–8 |

Mobile bottom nav visible; content padding-bottom clears it.

## States
- **Loading:** skeleton mirroring the exact grid (greeting line, 3 badges, reading card with 3 text lines + 4 meters, 2 side cards). No full-screen spinner (today: skeleton + extra spinner + "Loading your dashboard…" — drop the spinner).
- **No chart:** greeting + a single `feature` EmptyState card "Your chart isn't cast yet" with gold `Create my chart` (gold is allowed here because it is the only action). Hide sections 2–7.
- **Reading failed, chart OK:** reading card shows its inline error with Retry; other sections render normally. Today's code silently swallows both errors (`catch {}`) — must surface.
- **Charts request failed:** inline error card with Retry at the top; do **not** show the "no chart" empty state (that tells a returning user their data is gone).

## Motion
Entrance: sections stagger 40 ms (max 6), 250 ms `fadeUp`; Big Three badges scale .96→1 spring gentle. Total ≤ 500 ms. No hover-scale on cards.
