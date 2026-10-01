# Profile — You (`/profile`)

**User goal:** manage my charts, my preferences, my account — find things fast, break nothing by accident.
**Primary action:** none gold at page level. Each section has its own save (secondary until dirty → becomes gold only inside the section being edited).

## Structure
Settings-style page with grouped sections. ≥1024: left section nav (sticky, 240px, `<nav aria-label="Profile sections">`, anchors) + content `max-w-reading`. <1024: single column, section headings as anchors.

| # | Section | Content |
|---|---|---|
| 1 | **Identity header** | Avatar xl (lg on mobile) with sun-sign overlay · name `text-h2` · email `fg-muted` · Big Three ZodiacBadges sm row · plan Badge (Free / Premium `accent`) |
| 2 | **My charts** | List rows (64px): chart name + "Primary" accent Badge · birth line `text-caption tabular` · precision Badge · overflow menu (Edit, Set as primary, Delete). `Add a chart` secondary button. Edit opens Dialog/Sheet using the onboarding field components. |
| 3 | **Preferences** | Language (Segmented EN · हिंदी · Hinglish) · Theme (Segmented System · Dark · Light → sets/removes `data-theme`) · Chart style (Segmented North · South) · Ayanamsa (Select: Lahiri default; Raman, KP) · Daily reading notification (switch + time) |
| 4 | **Account** | Name (inline edit: value + `Edit` ghost → Input + Save/Cancel) · Email (read-only + "Change" → verification flow) · Password (collapsed "Change password" → current / new / confirm, each with show toggle; strength meter text, not colour only) · Connected Google account |
| 5 | **Plan** | Current plan, usage ("6 of 10 questions today", 8px bar), `See Premium` secondary |
| 6 | **Privacy & data** | `Download my data` secondary · explanation of what's stored |
| 7 | **Danger zone** | Separate card with 1px `danger/30` border; heading in `fg` with `AlertTriangle danger` icon (not red uppercase text); `Delete account` secondary button with `text-danger` → confirm Dialog requiring typing the email; button `danger` "Delete my account" |
| 8 | Sign out | ghost button, bottom |

Section headings: `text-h3` Fraunces, sentence case (today: `text-sm uppercase tracking-widest text-primary/80` — illegible and shouting).

## Layout

| | 375px | ≥768 | ≥1024 |
|---|---|---|---|
| Header | centred stack | left-aligned row | row, in content column |
| Sections | cards stacked, gap 12 | gap 16 | gap 24, left nav |
| Rows | label above value | label left 200px / value right | same |

## States & feedback
- Save success: toast "Saved" (4 s). Field errors inline.
- Chart delete: confirm Dialog "Delete 'Mom's chart'? Readings and compatibility reports that use it will be removed." Cannot delete the only primary chart without choosing another (button disabled with reason).
- Theme switch applies instantly (no reload), persisted to account + `localStorage` fallback.
