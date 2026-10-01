# Frontend Coding Rules - React / TypeScript

Stack (verify against `frontend/package.json`; on 2026-10-01 it matched): React 19, TypeScript
5.9, Vite 8, Tailwind CSS 4 (`@tailwindcss/vite`), Framer Motion 12, Swiper 12, Lucide React,
React Hook Form 7 + Zod 4, Axios, TanStack Query 5, Zustand 5, react-router-dom 7, clsx +
tailwind-merge + class-variance-authority. **Not installed:** shadcn/ui, Radix, GSAP, Lenis,
Three.js, Recharts, date-fns, Vitest, Playwright. Propose before adding any of them.

Design source of truth: `design-system/cosmic-intelligence/MASTER.md` (plus `pages/`
overrides). Read it before building UI.

## 1. Layering

| Folder | Role | Rule |
|---|---|---|
| `services/` | `api.ts` (the one axios instance) + one module per domain (`auth.ts`, `charts.ts`, `chat.ts`, ...) | the **only** place axios is imported; typed request/response |
| `hooks/` | TanStack Query wrappers and business logic (`useCharts`, `useChat`) | components never call services directly for server data |
| `components/` | render only | no axios, no business branches in JSX |
| `pages/` | route composition | lazy-loaded per route |
| `store/` | Zustand for slow-changing client globals (auth session, active chart id) | never server data |

## 2. State: pick the tool by kind

| State | Tool |
|---|---|
| Server data | TanStack Query. Never `useEffect` + axios + `useState`. |
| URL state (tab, filter, page, selected chart) | router search params |
| Forms | React Hook Form + Zod resolver. Share the Zod schema with the service's TS type. |
| Local UI | `useState` in the owning component |
| Cross-cutting client globals | Zustand, using selectors (`useAuth(s => s.user)`) to avoid re-render storms |

- Every mutation invalidates the query keys it affects (chart create/edit/delete invalidates `["charts"]`,
  `["chart", id]`, and anything derived from that chart). This mirrors the backend cache contract.
- Query keys are built by one factory per domain (`chartKeys.all`, `chartKeys.detail(id)`), not by
  ad-hoc arrays.

## 3. Errors and the four states

Every data view designs **loading** (fixed-size skeleton, no layout shift), **empty** (teaches
and offers the primary action), **error** (plain language plus retry), and **overflow** (long
names, 0 or 100 charts, long AI answers).

```typescript
const status = axios.isAxiosError(err) ? err.response?.status : undefined
// 401 -> session expired flow; 404 -> not found; 429 -> "daily limit reached" with reset time;
// 503 -> "the guide is resting, try again shortly"; else generic + retry
```

- Branch on the real HTTP status. `isError` alone is not proof the resource is gone. A
  network blip must not delete local pointers (for example the remembered conversation id).

## 4. AI chat surface

- Stream responses (SSE / fetch reader through a service function). Show a typing affordance
  immediately. Keep the container stable as text grows (no CLS).
- Buffer incomplete markdown before rendering. Render model output as text or sanitised markdown.
  `dangerouslySetInnerHTML` with model or user content is forbidden.
- Label AI content as AI-generated. Show the disclaimer on AI surfaces.
- Disable send while a response streams. Allow stop. Preserve the typed draft on error.
- Show which zodiac system a sign belongs to wherever signs appear.

## 5. Auth token

- Current state (verified): the JWT is stored in `localStorage` (`services/api.ts`,
  `store/authStore.ts`) and the 401 interceptor hard-redirects to `/auth`. This is a known
  XSS-exposure risk, tracked in PITFALLS. Do not extend it: never store PII or birth data in
  localStorage. The target is an httpOnly refresh cookie plus an in-memory access token.
- Frontend gates (hiding premium features, route guards) are UX only. The backend denies.
- No secrets in `VITE_*` variables. Vite inlines them into the public bundle.

## 6. Performance and accessibility bar

- Core Web Vitals (p75): INP <= 200 ms, LCP <= 2.5 s, CLS <= 0.1. `React.lazy` per route;
  check the bundle when adding a dependency; images have width/height.
- Framer Motion for gestures, layout, and enter/exit; Tailwind transitions for simple hover/color.
  Animate transform and opacity only. Honour `prefers-reduced-motion` (`useReducedMotion()` plus the
  global CSS block in `CLAUDE.md`). Motion never carries meaning alone.
- WCAG 2.2 AA: semantic elements (a `<button>`, never a clickable `<div>`), targets >= 24x24 px,
  visible focus >= 3:1, text contrast >= 4.5:1 (check text over cosmic/gradient backgrounds),
  labels on every input, `alt` on images, `aria-label` on icon-only buttons, no drag-only
  interactions (the chart wheel needs a keyboard/list alternative).
- Lucide icons only. No emoji as icons.

## 7. TypeScript

- Explicit interfaces for props and every API response (`types/`). No `any`. Use `unknown` plus a guard.
- `npm run build` (runs `tsc -b`) and `npm run lint` must be clean.

## Done checklist (frontend)

- [ ] No axios outside `services/`; server data through TanStack Query; mutations invalidate keys
- [ ] Loading / empty / error / overflow all implemented
- [ ] Forms use RHF + Zod
- [ ] No `any`; build and lint clean
- [ ] Checked in the running app at 375px and 1440px (Playwright script, no console errors)
- [ ] a11y basics (focus, labels, contrast, reduced motion)
- [ ] Matches `design-system/` MASTER tokens; no one-off colors or spacing
