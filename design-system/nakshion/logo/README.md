# Nakshion logo: usage guide

Recommended and built concept: **A, Lunar Dial** (see `concepts.html` for all three, ranked).
A crescent Moon inside an orbit of 27 dots (the 27 nakshatras). One gold dot is the lamp: the nakshatra the Moon is in tonight. The wordmark is Fraunces SemiBold converted to outlines and hand-kerned, so no font is needed to render it.

## Status

Frontend integration is **staged, not applied**. Writes into `frontend/` were denied by the permission system during this session, so everything is in `integration/` ready to copy (see "Applying to the frontend"). Nothing was committed or pushed.

## Colours

| Role | Dark theme | Light theme | Notes |
|---|---|---|---|
| Crescent and wordmark (fg) | #EEF0FA | #1A1830 | token `fg` |
| Orbit dots (ai, moonlit violet) | #A99BFF | #5443CF | token `ai` |
| Lamp (gold, once only) | #F2B544 | #E0A030 | token `accent` |
| Night (tile and share backgrounds) | #0B0D1A | | |

The structure never relies on hue: the lamp is a separate shape, and the mark reads in grayscale, deuteranopia and protanopia (checked in `concepts.html`).

## Versions

- **Full mark**: crescent + 27-dot orbit + lamp. Use at 44 px and larger.
- **Small mark** (optical size): crescent + lamp only. Use at 16 to 43 px. Never scale the full mark below 44 px; the dots become noise.
- **Horizontal / stacked lockups**; `horizontal-compact` uses the small mark for navbars.
- **Mono**: everything in `currentColor`. Use on gold, photos, or one-colour print.

## Clear space and minimum size

- Clear space: half the mark height on every side (32 units of the 64-unit grid). Nothing, including other logos, enters it.
- Minimum: small mark 16 px; full mark 44 px; horizontal lockup 20 px mark height (about 90 px wide); stacked lockup 80 px wide.
- App tile: mark at 70% of the tile, centred; maskable icon at 56% (inside the 80% safe circle).

## Do

- Use the file for the background: `-dark` on night, `-light` on cream or white, `-mono` on gold or imagery.
- Keep exactly one gold element per composition; the lamp is it.
- Use the supplied SVGs; they are clean paths with no fonts or filters.

## Don't

- Don't place the colour logo on gold or on mid-violet; use mono.
- Don't turn the lamp into a star, recolour it, or add a second gold element (it would also drift toward a crescent-and-star flag).
- Don't add the crescent to other graphics as decoration, glow, or gradients; don't rotate, outline or stretch it.
- Don't retype the wordmark in Fraunces; use the outlined paths (kerning is tuned).
- Don't animate it. If a twinkle is ever wanted, the lamp alone, and only under `prefers-reduced-motion: no-preference`.

## Asset index

| File | Use |
|---|---|
| `concept-a-lunar-dial/` (recommended), `concept-b-constellation-n/`, `concept-c-kundali-emblem/` | per concept: `mark-`, `mark-small-`, `horizontal-`, `horizontal-compact-`, `stacked-` in `dark`, `light`, `mono` (15 SVGs each) |
| `concepts.html` | self-contained comparison sheet (open from disk) |
| `favicon.svg` | browser tab icon (night rounded tile, small mark) |
| `assets/favicon-16.png`, `favicon-32.png`, `favicon-48.png` | PNG favicon fallbacks |
| `assets/apple-touch-icon-180.png` | iOS home screen (opaque, full-bleed) |
| `assets/icon-192.png`, `icon-512.png` | PWA icons, purpose "any" |
| `assets/icon-maskable-512.png` | PWA maskable icon |
| `assets/icon-monochrome-512.png` | PWA monochrome icon (black on transparent) |
| `og-image-1200x630.svg` / `.png` | Open Graph and Twitter large card; key content inside the centred 1000x500 area; the same file serves Twitter (2:1 crop is safe) |
| `social/linkedin-logo-400.png`, `linkedin-banner-1584x396.png`, `github-social-1280x640.png`, `avatar-1024.png`, `x-header-1500x500.png` | profile kit |
| `integration/` | files staged for `frontend/` (see below) |
| `build/` | generator scripts (Node: `opentype.js`, `wawoff2`, `@resvg/resvg-js` installed in a scratch dir; Fraunces 600 WOFF2 is OFL) |

## Applying to the frontend (staged in `integration/`)

1. `integration/Logo.tsx` replaces `frontend/src/components/layout/Logo.tsx`. Same `Logo` and `KundaliIcon` exports. New props: `variant` (`mark` | `horizontal` | `stacked`), `size` (mark height px, default 32), `tone` (`color` | `mono`), optional `to` (renders a link with `aria-label="Nakshion home"`; without it the SVG is `role="img"` `aria-label="Nakshion"`). It switches to the small mark under 44 px automatically. The existing call sites (`AppShell`, `MarketingHeader`, `Footer`, `OnboardingPage`; auth, legal and 404 pages all go through `MarketingHeader`) pick it up unchanged. It is theme-aware via `fill-fg`, `fill-ai`, `fill-accent`.
2. Copy `integration/public/*` (including `.well-known/security.txt`, a clearly marked placeholder) into `frontend/public/`, replacing the old `favicon.svg` and deleting `icons.svg` only if nothing references it (grep first).
3. Paste `integration/index-head-snippet.html` into `frontend/index.html` `<head>`. The JSON-LD block is `type="application/ld+json"`: not executable, so the CSP script hash is unaffected. The existing inline theme script and its hash must not change. CSP `img-src` already allows what is needed.
4. Add `integration/useDocumentTitle.ts` to `frontend/src/hooks/` and call it per page (and in `LegalLayout`, replacing its manual effect) for titles like "Privacy Policy — Nakshion".
5. Domain constant: every absolute URL uses `https://nakshion.vercel.app` (OG tags, canonical, `sitemap.xml`, `robots.txt`, JSON-LD). Update them all if a custom domain is added.
6. Verify: `npm run build`, `npm run lint`, axe, light and dark screenshots.

## Rasterising

No `rsvg-convert`, Inkscape, ImageMagick, Pillow, cairosvg or sharp were installed. PNGs were produced with `@resvg/resvg-js` (installed in a scratch directory, not in the project) from the SVGs; all text is outlined, so output is font-independent.
