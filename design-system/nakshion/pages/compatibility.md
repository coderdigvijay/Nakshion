# Compatibility — Match (`/compatibility`, `/compatibility/:reportId`)

**User goal:** "How do we fit — and what should we be careful about?"
**Primary action:** form step → `See our compatibility` (gold). Report step → `Ask about us` (ai) — no gold on the report.

## Flow
1. **Setup** (form) → 2. **Calculating** → 3. **Report**. Previously saved reports listed above the form (≥1 report) as compact rows.

### 1 · Setup
Two-sided form that makes the pairing visible:

| | 375px | ≥768 | ≥1024 |
|---|---|---|---|
| Layout | stacked: "You" card (Select of user's charts, defaults to primary; shows Big-Three mini) → `HeartHandshake` divider → "Them" card | same, `max-w-form` | two columns side by side (You · Them) with the divider icon centred between, `max-w-chat` |
| Relationship type | choice Chips: Romantic · Marriage · Friendship · Family · Work (single-select, required) above both cards | | |
| Them fields | Name · BirthDateField · BirthTimeField (unknown-time path) · LocationAutocomplete — **same components as onboarding** (today the partner form duplicates onboarding's markup with native date/time inputs) | | |
| Action | sticky bottom primary full-width | inline | inline, centred under columns |

Optional "Save as a person" checkbox → saved partners appear as choice Chips next time.

### 2 · Calculating
In-place card: two Avatars sliding toward each other (x ±24→0, spring gentle) with the meter track drawing; copy "Comparing Moon nakshatras…" → "Checking Mars and Venus…" (2 s steps). Reduced motion: static + text.

### 3 · Report

| Order | Block | Notes |
|---|---|---|
| 1 | Header: two Avatars + names + relationship type Badge | |
| 2 | **CompatibilityMeter** (0–10, or 36 for Ashtakoot) + band label + 2-sentence verdict | `feature` card |
| 3 | Category bars (Emotional, Communication, Physical, Values, Growth — whatever the API returns, in API priority order) | each row expandable to a paragraph |
| 4 | Strengths · Challenges | two lists side by side ≥768. Icons: `CheckCircle2 success` / `AlertTriangle warning`. Headings in `fg` (not coloured text as today's `text-emerald-400` / `text-amber-400` headings) |
| 5 | Ashtakoot table (if available) | per MASTER §9.4b |
| 6 | `Ask about us` ai button (pre-fills chat with the report context) + `Share` ghost | |

Layout ≥1024: meter column (4 cols, sticky) + content (8 cols).

## Copy & tone
- Lead with what works, then what needs care. Never "incompatible", "doomed", "bad match". Lowest band label is "Challenging", with "Every pairing has work; here is where yours lies."
- Doshas (Nadi, Bhakoot, Manglik): `warning` Badge + plain explanation + "Traditional remedies exist; many astrologers consider…" — never a red alarm.

## States
- Report loading (revisit): skeleton circle + 5 bars.
- Partner has no birth time: Badge "Their Lagna approximate" in header; affected categories marked.
- Error: inline card, form data preserved.
