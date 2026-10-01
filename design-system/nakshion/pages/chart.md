# Chart (`/chart`, `/chart/:id`)

**User goal:** understand *my* chart — first the shape, then the detail I care about.
**Primary action:** none gold. The chart is the hero; secondary actions: `Ask about this` (ai ghost, contextual), `Share` / `Download` (ghost IconButtons).

## Information architecture — tabs, not a 10-section scroll

Today `ChartPage.tsx` (1,014 lines) stacks ten sections: format toggle, chart, ayanamsa, "core life signature", planet cards, drishti, D9+D10, dasha, yogas, bhava lords. A first-time user scrolls ~9 screens on mobile. Restructure:

**Persistent top (above tabs):**
1. Title row: `text-h1` "Asha's chart" + chart switcher (Select, if multiple charts) + actions.
2. Birth data line `text-caption fg-muted tabular`: "14 Mar 1995 · 6:42 AM · Varanasi (25.32° N, 82.97° E) · Lahiri ayanamsa 23°47′" + precision Badge (P2).
3. **ChartWheel** (full) + format Segmented (North/South) + varga Tabs `D1 Rashi · D9 Navamsa · D10 Dashamsa` directly above the wheel (switches the wheel — divisional charts are not separate stacked charts).
4. **Core signature** — 3 bullet insights max, `text-body-lg`, `feature` card on ≥1024 beside the wheel, below it on mobile. Collapsed to 3 lines with "More".

**Tabs (sticky under the header on scroll, URL-synced `?tab=`):**

| Tab | Content |
|---|---|
| Planets (default) | PlanetRow table/list (9 grahas; outer planets behind a "Show Uranus, Neptune, Pluto" toggle in Western mode only) |
| Houses | 12 rows: house number + ZodiacBadge + lord + occupants + one-line meaning ("10th · career, public life"); replaces "Bhava Lords" |
| Aspects | AspectGrid + plain-language list of the 5 most significant drishtis |
| Dasha | DashaTimeline (full) with theme descriptions per period |
| Yogas | Cards per yoga/dosha: name, formed by (glyph chips), strength Badge, 2-line meaning; doshas framed constructively with "What it asks of you" |

## Layout

| | 375px | ≥768 | ≥1024 |
|---|---|---|---|
| Wheel | full width (max 343), centred | 440px centred | 7-col left (480–520px), sticky top while the right column scrolls *only within the top block* |
| Signature | below wheel | below wheel | 5-col right of wheel |
| Tabs | horizontal scroll, edge fades | full row | full row under the top block |
| Tab content | single column | single column, PlanetRow as table | table, `max-w-app` |

## Linking (the "aha" interaction)
Selecting a house on the wheel highlights the matching PlanetRows (and vice versa: hovering/focusing a PlanetRow outlines its house). On mobile, tapping a house opens a Sheet with the house detail; on desktop it filters/scrolls the Planets tab to those rows with `ai-subtle` highlight.

## States
- Loading: skeleton square (wheel) + caption line + 6 PlanetRow skeletons. Today: a bare centred spinner.
- No chart: EmptyState "Your chart isn't cast yet" + gold `Create my chart`.
- No birth time: hatched Lagna + Badge "Lagna approximate"; Houses tab shows a top info note explaining reduced accuracy.
- Varga unavailable (no D9/D10 data): disable that tab with tooltip "Not available for this chart".

## Content rules
- Sanskrit + English: "Graha sthiti (planetary positions)" on first use; tab labels in the user's language only.
- Degrees always `DD°MM′`. Italic is not used for interpretation text (today's "Core Life Signature" is italic — hard to read in long form, and italic Devanagari doesn't exist).
- Replace raw `text-red-400`/`text-amber-400` retrograde/combust markers with the canonical Badges.
