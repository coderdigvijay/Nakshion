# Nakshion API Contract

**Status:** Authoritative contract for the backend rebuild · **Version:** 1.0 · **Date:** 2026-10-01
**Derived from:** `frontend/src/services/*.ts`, `frontend/src/types/index.ts`, the pages that call them,
`backend/alembic/versions/001_*.py` + `002_*.py`, and `backend/README.md`.

This document has three layers. Keep them apart when implementing:

| Marker | Meaning |
|---|---|
| **[MVP]** | Required for the current frontend to work unchanged. Shapes are frozen. |
| **[v1-add]** | Additive: new optional response fields or new endpoints. The current frontend ignores them, so they ship any time without breaking it. |
| **[v2-change]** | Changes that need a coordinated frontend change. Each one lists the migration path. Do not ship until the frontend is updated. |

Section 11 lists every gap and inconsistency found in the frontend services.

---

## 1. Conventions

### 1.1 Base URL and transport

- Base URL: `${VITE_API_URL}`, default `http://localhost:8000/api/v1`. Every path below is relative to it.
- JSON in and out, `Content-Type: application/json`, UTF-8.
- Auth: `Authorization: Bearer <access_token>` (the axios interceptor in `api.ts` adds it whenever `localStorage.token` exists).
- **Trailing slashes.** The frontend calls `/charts/` and `/compatibility/` *with* a trailing slash and `/chat/conversations` *without* one. Register the routes with exactly the spelling below **and** make the other spelling work too, without a redirect. FastAPI's default `redirect_slashes` 307 drops CORS context on some browsers. Set `redirect_slashes=False` and declare both paths, or add a path-normalising middleware.
- CORS: allow the origins in `CORS_ORIGINS`, allow the `Authorization` and `Content-Type` headers, and allow methods `GET, POST, PUT, DELETE, OPTIONS`. Credentials are not needed (the token is a header, not a cookie).

### 1.2 Data formats

| Kind | Format | Example |
|---|---|---|
| IDs | UUID v4 string, lowercase | `"3f0c…"` |
| Timestamps (`created_at`, `updated_at`) | ISO 8601 in UTC with `Z` | `"2026-10-01T06:30:00Z"` |
| Dates | `YYYY-MM-DD` | `"1994-07-21"` |
| Times of day | `HH:MM` (24h). Input also accepts `HH:MM:SS`; output is always `HH:MM` | `"14:05"` |
| Decimals (`overall_score`, coordinates, degrees) | JSON **number**, never string. Postgres `NUMERIC` must be cast to float in the schema layer | `7.4` |
| Zodiac sign names (Western) | English, Title Case | `"Sagittarius"` |
| Rashi names (Vedic) | Fixed transliteration list (see `astrology-engine.md` §2) | `"Vrishchika"` |

### 1.3 Error envelope

The frontend reads only `error.response.data.detail` and expects a **string** (see `extractError` in `authStore.ts`, and every page's `catch`). So every error response, including validation errors, must be:

```json
{
  "detail": "Human-readable message safe to show the user",
  "code": "MACHINE_READABLE_CODE",
  "errors": [{ "field": "date_of_birth", "message": "Birth date cannot be in the future" }]
}
```

- `detail`: always a string. **Override FastAPI's default 422 handler**, whose `detail` is an array. That array makes the frontend fall back to "Something went wrong". Put the first field error's message in `detail` and the full list in `errors`.
- `code`: always present. The canonical list is in §10.
- `errors`: present only for validation failures.
- Never include stack traces, SQL errors, or provider SDK messages.

### 1.3a Limits added in v1.1

- Request bodies over **64 KB** get 413 `PAYLOAD_TOO_LARGE` (checked on `Content-Length` and while streaming).
- `PUT /users/me` can change `timezone` **once per 24 h** (429 `RATE_LIMITED` with `Retry-After`; re-sending the current value is free). Quotas reset at the user's local midnight, so this stops flip-flopping for extra quota.
- Chat quota is **reserved before** the LLM call and released if the call fails, so parallel sends can't exceed the limit.

### 1.4 Status codes, and a hard constraint from the frontend

`api.ts` has a global response interceptor. **Any 401 clears the token and hard-navigates to `/auth`.** So:

- Return 401 **only** when the bearer token is missing, malformed, expired, or revoked.
- A wrong password at login, or a wrong `current_password` on change-password, returns **400** (`INVALID_CREDENTIALS` / `INVALID_CURRENT_PASSWORD`). A 401 there would log the user out and wipe the error message. (Gap G-01.)
- For a resource that doesn't exist **or isn't owned by the caller**, return 404. Never return 403 for someone else's resource, because that leaks its existence.
- 403 is reserved for an authenticated user who isn't allowed the action (`EMAIL_NOT_VERIFIED`, `PREMIUM_REQUIRED`).
- 429 always carries a `Retry-After` header (seconds) and `code` = `RATE_LIMITED` or `QUOTA_EXCEEDED`.

### 1.5 JWT

- HS256, signed with `JWT_SECRET_KEY` (at least 32 random bytes in production; refuse to boot with the example value when `APP_ENV=production`).
- Claims: `sub` (user id), `iat`, `exp`, `ver` (the user's `token_version`, used for revocation; see `architecture.md` §5), `typ: "access"`.
- Lifetime: `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`, default 10080 (7 days). This matches the frontend, which has no refresh flow. [v2-change] Section 12 covers the short-lived access token plus refresh cookie.
- The token is rejected (401) when `ver` ≠ the user's current `token_version`. Password reset, password change and "log out everywhere" increment it.

---

## 2. Shared response objects [MVP]

### 2.1 `User`

```ts
{
  id: string;
  email: string;
  name: string;                // never null; if DB name is null return "" 
  email_verified: boolean;
  avatar_url: string | null;   // Google picture for OAuth users
  subscription_tier: "free" | "premium";
  timezone: string;            // IANA "current residence" zone, default "UTC". Used for quota resets and "today". Set via PUT /users/me (v1); frontend should send the browser zone once after login
  created_at: string;
  // [v1-add] optional fields, ignored by current frontend:
  has_password: boolean;       // lets Profile page choose "change" vs "set" password
  preferred_language: "english" | "hindi" | "hinglish";
  astrology_system: "vedic" | "western";   // which view the dashboard leads with
  quota: { chat_remaining_today: number; chat_daily_limit: number; resets_at: string };
}
```

### 2.2 `BirthChart`

```ts
{
  id: string;
  user_id: string;
  name: string;
  relationship_label: string;  // from DB column `relationship` (gap G-06)
  date_of_birth: string;       // YYYY-MM-DD (local civil date at birthplace)
  time_of_birth: string | null;// HH:MM local civil time, null if unknown
  has_exact_time: boolean;
  birth_place_name: string;
  latitude: number;
  longitude: number;
  timezone: string;            // IANA zone resolved SERVER-SIDE from lat/lon (gap G-05)
  chart_data: ChartData;       // exact schema in astrology-engine.md §9
  is_primary: boolean;
  created_at: string;
  updated_at: string;
}
```

`relationship_label` values: `"self" | "partner" | "friend" | "family" | "coworker" | "other"`.


### 2.2a `chart_data` when the birth time is unknown (engine 2.0, additive/nullable)

When `time_of_birth` is null, `chart_data.metadata.houses_available = false` and the chart carries **no** time-dependent output. Render nulls and omissions as "needs birth time", never as zero.

| Where | Value |
|---|---|
| Western | `houses: []`, every `planets[].house = null`, no `house` on `sun_sign`/`moon_sign`, no `mc`, `rising_sign = {sign:"Unknown", degree:0, approximate:true}`, `metadata.house_system = "none"`, `metadata.lagna_basis = "none"` |
| Vedic | `vedic.lagna = null`, `vedic.houses_available = false`, `vedic.planets[].house = null`, `house_lords: []`, `functional_benefics/malefics: []`, `yogakaraka: null`, graha drishti `to_house = null`, `navamsa_d9` and `dashamsa_d10` **omitted**, `vedic.suppressed = {reason, items[]}` (what is withheld) |
| Yogas | the nine lagna-based yogas are not computed; the rest carry `approximate: true`; `manglik.from_lagna = null` (Moon-only) |
| Dasha | every period and antardasha has `approximate: true`; new `dasha.approximate_note` and `dasha.candidates` (running MD/AD if born 00:00 or 23:59). The balance can be off by up to the starting lord's full period (7-20 years) |

Charts stored by engine 1.x are recomputed on read (`GET /charts`, `GET /charts/{id}`), so old unknown-time charts take the new shape automatically.

### 2.3 `Conversation`, `Message`, `ConversationDetail`

```ts
Conversation {
  id: string; user_id: string; chart_id: string | null;
  title: string | null;        // null until first message; then first 60 chars of first user message (trimmed at word boundary)
  category: string | null;     // "general"|"love"|"career"|"health"|"timing"|"spiritual"|"compatibility"; set by classifier on first message
  status: "active" | "archived";
  message_count: number;       // count of persisted messages (user + assistant)
  created_at: string; updated_at: string;  // updated_at bumps on every message
}

Message {
  id: string;
  conversation_id: string;
  role: "user" | "assistant";
  content: string;             // assistant: plain text with light Markdown (**bold**, lists). No HTML.
  bookmarked: boolean;
  tokens_used: number | null;  // assistant only: input+output tokens of the final provider call; null for user
  created_at: string;
  // [v1-add]
  citations?: Array<{ factor_id: string; label: string }>;  // computed chart factors the answer relied on
  // [v1.1] reference notes the answer drew on (citation chips). Assistant messages only: an array (possibly empty)
  // when the answer was generated by this version, null/absent on older messages and on user messages.
  // De-duplicated, at most 8. `source_id` is an opaque hash (never a file name); `title` is a display title, an author
  // only for public-domain classics; `tier` 1 (primary/classic) .. 3 (modern paraphrase), null if unknown.
  // Reference text itself is never returned. Present on the H5 response, the H6 `done` event and on reload (H3).
  sources?: Array<{ source_id: string; title: string; section: string; tier: number | null }> | null;
  feedback?: "up" | "down" | null;
}

ConversationDetail { conversation: Conversation; messages: Message[] }  // messages oldest → newest
```

### 2.4 `CompatibilityReport`

```ts
{
  id: string;
  chart1_id: string;           // the user's chart
  chart2_id: string;           // the partner chart (created by this call)
  relationship_type: "romantic" | "friend" | "family" | "coworker";
  overall_score: number;       // 0.0–10.0, one decimal
  compatibility_data: {
    categories: {              // EXACTLY these five keys (CompatibilityPage CATEGORY_META)
      emotional:     { score: number; summary: string };
      communication: { score: number; summary: string };
      romance:       { score: number; summary: string };
      passion:       { score: number; summary: string };
      "long-term":   { score: number; summary: string };
    };
    synastry_aspects: Array<{ planet1: string; planet2: string; aspect: string; orb: number; interpretation: string }>; // ≤ 10, strongest first; planet1 = chart1's planet
    strengths: string[];       // exactly 3
    challenges: string[];      // exactly 3
    // [v1-add]
    summary?: string;                      // 2–3 sentence overview
    ashtakoota?: AshtakootaResult | null;  // romantic only, see astrology-engine.md §7.2
    manglik?: { person1: ManglikResult; person2: ManglikResult } | null;
    method_version?: string;               // e.g. "compat-1.0"
    score_breakdown?: {                    // engine 2.0: how overall_score was built
      category_weights: Record<string, number>; category_scores: Record<string, number>;
      weighted_contributions: Record<string, number>; blend: string; formula: string; explanation: string;
      ashtakoota: { included: boolean; total?: number; scaled_0_10?: number; tables_fixture_verified: false; tables_note?: string };
      overall_range?: [number, number];    // present when the Moon sign is ambiguous (unknown time)
    } | null;
    // ashtakoota also gains: tables_fixture_verified (false until reference pairs exist), tables_note, and with an
    // unknown birth time: total_range, moon_ambiguous, note. It stays romantic-only (null for other types).
    approximate?: boolean;                 // true if either birth time unknown
  };
  partner_name: string;        // = chart2.name (not a DB column; join)
  created_at: string;
}
```

Keep category keys stable for every relationship type. For `friend`, `family` and `coworker`, the `romance` and `passion` summaries are written in a non-romantic register ("warmth and affection", "drive and friction"). The keys don't change, because the frontend iterates over `Object.entries`.

### 2.5 `DailyHoroscope`

```ts
{
  id: string;
  zodiac_sign: string;         // lowercase english sign as requested, e.g. "leo"
  date: string;                // YYYY-MM-DD
  general_reading: string;     // 80–140 words
  love_reading: string | null; // 40–80 words
  career_reading: string | null;
  wellness_reading: string | null;
  lucky_number: number | null; // 1–9, deterministic (see astrology-engine.md §8.3)
  lucky_color: string | null;  // deterministic from day ruler
  transit_data: Record<string, unknown>;  // see §7.1
  created_at: string;
}
```

### 2.6 `GeocodingResult`

```ts
{ name: string; lat: number; lon: number; timezone?: string }
// name = "City, State/Region, Country" (display_place + address parts); timezone = IANA from timezonefinder — always populated by this backend
```

---

## 3. Auth endpoints

| # | Method | Path | Auth | Tier |
|---|---|---|---|---|
| A1 | POST | `/auth/register` | — | MVP |
| A2 | POST | `/auth/login` | — | MVP |
| A3 | POST | `/auth/verify-email` | Bearer | MVP |
| A4 | POST | `/auth/resend-otp` | Bearer | MVP |
| A5 | POST | `/auth/forgot-password` | — | MVP |
| A6 | POST | `/auth/reset-password` | — | MVP |
| A7 | GET | `/auth/me` | Bearer | MVP |
| A8 | GET | `/auth/oauth/google` | — (browser navigation) | MVP |
| A9 | GET | `/auth/oauth/google/callback` | — (Google redirect) | MVP |
| A10 | POST | `/auth/change-password` | Bearer | MVP |
| A11 | POST | `/auth/set-password` | Bearer | MVP |
| A12 | POST | `/auth/logout-all` | Bearer | v1-add |

### A1 `POST /auth/register`

Request `{ "email": string, "password": string, "name": string }`

| Field | Rule |
|---|---|
| email | RFC-valid, trimmed, lower-cased, ≤ 255 |
| password | 8 chars to **72 UTF-8 bytes** (bcrypt limit; over → 422 `PASSWORD_TOO_LONG`, never silently truncated). Reject if it's in the bundled top-10k breached list (`PASSWORD_TOO_COMMON`). No composition rules (NIST 800-63B style). Same rule for every `new_password` field |
| name | trimmed, 1–100 chars, no control characters |

- **201** `{ "access_token": string, "token_type": "bearer" }`. The user is created with `email_verified=false` and a 6-digit OTP is emailed (Brevo). The frontend (`SignUpForm`) navigates to `/verify` next.
- **409** `EMAIL_EXISTS`: "An account with this email already exists. Try logging in." This is a deliberate usability trade-off (account enumeration), mitigated by the rate limit below.
- **429** `RATE_LIMITED`: 5 registrations / hour / IP.
- If sending the email fails, the user is still created; the OTP can be resent (A4). Log `email_send_failed`.

### A2 `POST /auth/login`

Request `{ "email": string, "password": string }`

- **200** `{ "access_token", "token_type": "bearer" }`. Sets `last_login_at`.
- **400** `INVALID_CREDENTIALS`: "Incorrect email or password." This covers unknown email, wrong password, and an OAuth-only account with no password. Run bcrypt against a dummy hash for unknown emails so the timing is constant.
- **429** `RATE_LIMITED`: 10 failures / 15 min per (IP, email), and 50 / 15 min per IP.
- Unverified users **can** log in. The frontend currently doesn't route them to `/verify` (gap G-03); the LLM endpoints enforce verification instead.

### A3 `POST /auth/verify-email`

Request `{ "code": string }` (6 digits)

- **200** `{ "message": "Email verified" }`. Idempotent: an already-verified user also gets 200.
- **400** `INVALID_CODE` or `CODE_EXPIRED`.
- **429** `RATE_LIMITED` after 5 wrong attempts on the same code. The code is then invalidated and the user must resend.
- Storage: `otp:{user_id}` in Redis, holding `{hash: sha256(code+pepper), attempts, exp}`, TTL 10 min.

### A4 `POST /auth/resend-otp`

- **200** `{ "message": "Verification code sent" }`.
- **429** if less than 60 s since the last send, or more than 5 sends in 24 h.
- **200** with "Email already verified" if already verified (no email sent).

### A5 `POST /auth/forgot-password`

Request `{ "email": string }`

- **200** always: `{ "message": "If an account exists for that email, a reset link is on its way." }`
- If the user exists, create a `password_resets` row with `token = sha256(raw_token)`, `expires_at = now + 1h`. Email the link `${FRONTEND_URL}/reset-password?token=${raw_token}` (`ResetPasswordPage` reads `?token=`). `raw_token` is 32 bytes from `secrets.token_urlsafe`.
- Rate limit: 3 / hour / email, 10 / hour / IP. Over the limit, still return 200 and send nothing.

### A6 `POST /auth/reset-password`

Request `{ "token": string, "new_password": string }`

- **200** `{ "message": "Password updated. Please log in." }`. In one transaction: mark the row `used`, invalidate any other unused reset rows for the user, set `password_hash`, and increment `token_version` (this logs out all sessions). Set `email_verified=true`, because proving control of the inbox is verification.
- **400** `INVALID_OR_EXPIRED_TOKEN`.

### A7 `GET /auth/me` → `User`

### A8 `GET /auth/oauth/google`

- **302** to Google's authorization endpoint with `scope=openid email profile`, `state` (random, stored at `oauth_state:{state}` in Redis, TTL 10 min) and PKCE (`code_challenge`, S256).
- The redirect URI is `${API_PUBLIC_URL}/api/v1/auth/oauth/google/callback`. `API_PUBLIC_URL` is a new env var (see `architecture.md` §9).

### A9 `GET /auth/oauth/google/callback?code=…&state=…`

1. Validate and consume `state` (single use). Exchange the code with PKCE. Verify the ID token (`iss`, `aud`, `exp`, `email_verified == true`).
2. Find the user by `(oauth_provider='google', oauth_id=sub)`. Otherwise find by email: **link** only when Google says `email_verified=true`, then set `email_verified=true` on our side. Otherwise create a user with `password_hash=null`, `name` from the profile, and `avatar_url` from `picture`.
3. **302** to `${FRONTEND_URL}/auth/callback?token=<jwt>` [MVP; `OAuthCallback.tsx` reads `searchParams.get("token")`].
4. On any failure: **302** to `${FRONTEND_URL}/auth/callback?error=oauth_failed`. The page then shows "No token received".

> [v2-change] A JWT in a query string ends up in browser history, and in Render/proxy access logs if the frontend host logs URLs. Section 12 covers moving to a one-time code exchange.

> **[v1.1 change, 2026-10-01] One-time code instead of the JWT in the URL.** The callback now redirects to
> `${FRONTEND_URL}/auth/callback?code=<opaque, single use, 60 s>` (error: `?error=oauth_failed`, unchanged).
> The SPA then calls **`POST /auth/oauth/exchange`** with `{ "code": string }` and receives
> `{ "access_token": string, "token_type": "bearer" }` (400 `INVALID_OR_EXPIRED_CODE` if used, expired or unknown;
> 20 / 10 min / IP). This supersedes the `?token=` redirect above (gap G-04 is closed server-side); the frontend must read
> `code` and strip it with `history.replaceState`.

### A10 `POST /auth/change-password`

Request `{ "current_password": string, "new_password": string }`

- **200** `{ "message": "Password changed" }`. **Decision:** in MVP, change-password does **not** bump `token_version`. The frontend keeps using its current token and has no way to receive a new one, so bumping would log the user out mid-session. [v2-change] Section 12 has it bump the version and return a fresh `access_token`.
- **400** `INVALID_CURRENT_PASSWORD` (not 401; see §1.4).
- **400** `NO_PASSWORD_SET`: "Your account uses Google sign-in. Set a password instead."

### A11 `POST /auth/set-password`

Request `{ "new_password": string }`

- **200** `{ "message": "Password set" }`.
- **409** `PASSWORD_ALREADY_SET`.

---

## 4. User endpoints

### U1 `GET /users/me` → `User` [MVP]. Same as A7.

### U2 `PUT /users/me` [MVP]

Request `{ "name": string }`. [v1-add] also optional `timezone` (IANA, validated against `zoneinfo.available_timezones()`), `preferred_language`, `astrology_system`.

- **200** → `User`.

### U3 `DELETE /users/me` [MVP, **v1.1: re-authentication required**]

> **[v1.1 change]** The request now needs a JSON body proving the caller still controls the account:
> password accounts send `{ "password": "<current password>" }`; OAuth-only accounts first call
> `POST /users/me/deletion-code` (emails a 6-digit code, 1/min, 5/day) and send `{ "code": "123456" }`.
> Missing proof: 400 `REAUTH_REQUIRED`; wrong password: 400 `INVALID_CURRENT_PASSWORD`; wrong or expired code:
> 400 `INVALID_CODE` / `CODE_EXPIRED`; 5 attempts / 15 min. axios: `api.delete("/users/me", { data: { password } })`.

- **204**. Hard delete: a single `DELETE FROM users WHERE id=…`, and the FKs cascade to charts, conversations, messages, compatibility reports and resets. After commit, purge the Redis keys `*:{user_id}*` (see `architecture.md` §6) and send a confirmation email. The frontend navigates to `/` and must clear `localStorage.token` itself (gap G-12).
- [v1-add] Before delete, record `{user_id_hash, deleted_at}` in `deletion_log` for DPDP/GDPR accountability. Store no PII.

### U4 [v1-add] `GET /users/me/export`

- **200** JSON bundle: user, charts (inputs plus chart_data), conversations with messages, and reports. Rate limit 3 / day.

### U5 [v1-add] `PUT /users/me/consents`

Request `{ "ai_processing": boolean, "marketing_email": boolean }`. See the PRD privacy section.

---

## 5. Chart endpoints

### C1 `POST /charts/` [MVP]

Request (`CreateChartPayload`):

```json
{
  "name": "Asha",
  "date_of_birth": "1994-07-21",
  "time_of_birth": "14:05",
  "has_exact_time": true,
  "birth_place_name": "Pune, Maharashtra, India",
  "latitude": 18.5204,
  "longitude": 73.8567,
  "timezone": "Asia/Kolkata",
  "is_primary": true
}
```

Validation and normalisation, in order:

1. `name`: 1–100 chars, trimmed.
2. `date_of_birth`: valid date, `1800-01-01 ≤ d ≤ today` (today in the birthplace zone). Out of range gives 422 `DATE_OUT_OF_RANGE`.
3. `time_of_birth`: `HH:MM[:SS]` or null.
   - `null` → `has_exact_time` is forced to `false`.
   - non-null and `has_exact_time=false` → treat it as an *approximate* time. Compute with it but flag `approximate`.
4. `latitude` ∈ [-90, 90], `longitude` ∈ [-180, 180]. Reject (0, 0) with `INVALID_LOCATION`.
5. **`timezone` is resolved server-side** with `timezonefinder.timezone_at(lng, lat)` (falling back to `certain_timezone_at` and then the nearest zone). If the client value differs, the server value wins and is the one returned. Log `tz_mismatch`. (Gap G-05: the frontend falls back to the *browser's* zone.)
6. Local → UTC conversion uses `zoneinfo` with historical rules:
   - **Non-existent local time** (a DST gap) → 422 `BIRTH_TIME_NONEXISTENT`: "That time didn't exist in {zone} on that date (clocks moved forward). Please check the birth time."
   - **Ambiguous time** (fold) → use `fold=0` (the first occurrence) and set `chart_data.metadata.ambiguous_time=true`. [v1-add] Accept an optional `dst_fold: 0|1` field.
   - [v1-add] Optional `utc_offset_override` (minutes, −720…+840) for records where the user knows the official clock offset (e.g. India 1942–45 War Time). When present it replaces the zoneinfo offset, and `metadata.tz_source="user_override"`.
7. **[v1.1] Primary rule.** The primary chart is always the user's **own** chart (`relationship_label = "self"`). `is_primary: true` without a `relationship` makes the new chart `self`; `is_primary: true` together with a non-self relationship, or a first chart explicitly created for someone else, never becomes primary (the former is 422 `PRIMARY_MUST_BE_SELF`, "Only your own chart can be your primary chart."). Enforced by the API and by a database CHECK. `is_primary`: if true, then in the same transaction run `UPDATE birth_charts SET is_primary=false WHERE user_id=:u AND is_primary` before inserting. A partial unique index enforces one primary per user (migration 003). A user's **first** chart is always primary, whatever the payload says. `relationship` = `"self"` when the new chart is primary and the user has no other `self` chart, otherwise `"other"`.
8. Limits: free 10 charts / user, premium 100. Over the limit → 403 `CHART_LIMIT_REACHED`. Creation is rate-limited to 20 / hour / user.

Responses:

- **201** → `BirthChart`, with `chart_data` computed synchronously by the engine (target p95 < 800 ms on Render free; the frontend shows rotating loading messages).
- **422** for the validation codes above.
- **500** `CHART_CALCULATION_FAILED`. The engine raised; nothing is persisted.

### C2 `GET /charts/` [MVP] → `BirthChart[]`

- **Ordering is part of the contract:** `ORDER BY is_primary DESC, created_at ASC`. `DashboardPage`, `ChartPage` and `ProfilePage` all use `charts[0]` as "my chart" (gap G-07).
- Includes partner charts created through compatibility (their `relationship_label` is `partner`/`friend`/`family`/`coworker`).
- No pagination in MVP (the 100-chart cap bounds it). [v1-add] `?relationship=self` filter.

### C3 `GET /charts/{id}` [MVP] → `BirthChart`, or 404 `NOT_FOUND`.

**Lazy upgrade:** if `chart_data.metadata.engine_version` has an older **major** than the running engine, recompute from the stored inputs, persist, and return the new data (see `astrology-engine.md` §10). C2 does the same per row, bounded to 5 recomputes per request. Anything beyond that is upgraded by a background task.

### C4 [v1-add] `PUT /charts/{id}`

Same body as C1, all fields required. Recomputes `chart_data`. **200** → `BirthChart`. Invalidates `chart_summary:{id}`, `factors:{id}:*` and `daily_personal:{user}:*` if the chart is primary, and marks open conversations on that chart so the next prompt uses the new data.

### C5 [v1-add] `DELETE /charts/{id}`

**204**. If the chart is primary, promote the oldest remaining **`self`** chart. **[v1.1]** If none exists the user simply has **no primary chart** (a saved person is never promoted); `GET /charts` may then contain no `is_primary: true` entry and R3/chat answer 409 `CHART_REQUIRED`. Conversations keep `chart_id` → `NULL` (the FK must become `ON DELETE SET NULL`; migration 003). Compatibility reports cascade.

### C6 [v1-add] `POST /charts/{id}/primary` → **200** `BirthChart`, with an atomic flip. **[v1.1]** 422 `PRIMARY_MUST_BE_SELF` if the chart's `relationship_label` is not `self`.

### C7 [v1-add] `GET /charts/{id}/transits?from=YYYY-MM-DD&days=1..90`

Returns the personal transit factors and timing windows (`astrology-engine.md` §6). Pure computation, cached per chart and month.

### C8 [v1-add] `GET /charts/{id}/dasha?levels=2|3`

Returns the full Vimshottari timeline (all 9 mahadashas with antardashas). This is static, so it's computed on demand and cached for 30 days.

### C9 [v1-add] `GET /panchang?date=YYYY-MM-DD&lat=..&lon=..`

Returns tithi, nakshatra, yoga, karana, vara, sunrise/sunset, Rahu Kaal. Public. Cached per (date, lat/lon rounded to 0.1°).

---

## 6. Chat endpoints

### H1 `POST /chat/conversations` [MVP]

Request `{}`. [v1-add] optional `{ "chart_id"?: string, "category"?: string }`.

- `chart_id` defaults to the user's primary chart, or `null` if they have none.
- **201** → `Conversation` (title `null`, `message_count` 0).
- Rate limit: 30 creations / hour / user.

### H2 `GET /chat/conversations` [MVP] → `Conversation[]`

`ORDER BY updated_at DESC`, `status='active'`, `LIMIT 50`. [v1-add] `?limit=&before=<updated_at cursor>`.

### H3 `GET /chat/conversations/{id}` [MVP] → `ConversationDetail`

Returns the last 200 messages, oldest first. 404 if the conversation isn't owned by the caller.

### H4 `DELETE /chat/conversations/{id}` [MVP] → **204**. Hard delete; messages cascade.

### H5 `POST /chat/conversations/{id}/messages` [MVP]

Request:

```json
{ "content": "Will this year be good for a job change?", "language": "english" }
```

| Field | Rule |
|---|---|
| content | trimmed, 1–2000 chars (the frontend has no counter; over the limit → 422 `MESSAGE_TOO_LONG`, "Please keep questions under 2000 characters.") |
| language | `"english" \| "hindi" \| "hinglish"`, default `"english"`. Any other value → 422 |

Pre-checks, in order:

1. Conversation owned → else 404.
2. `email_verified` → else 403 `EMAIL_NOT_VERIFIED`: "Please verify your email to chat with Nakshion."
3. The conversation's chart (or the primary chart, attached now if `chart_id` is null) exists → else 409 `CHART_REQUIRED`: "Add your birth details first so answers are about *your* chart."
4. AI consent not withdrawn → else 403 `AI_CONSENT_REQUIRED` [v1].
5. Daily quota (`architecture.md` §7): free 5 assistant replies / user-local day, premium 60. Over the limit → 429 `QUOTA_EXCEEDED`, detail "You've used today's 5 free questions. They reset daily." The 429 body also carries `resets_at` (ISO UTC) and `limit`, so the client renders the reset time in the viewer's own zone (v1.1; additive)., with `Retry-After`.
6. Per-user concurrency lock: `chat_lock:{conversation_id}` (Redis `SET NX EX 60`). A second concurrent send → 409 `MESSAGE_IN_FLIGHT`.

Processing: the pipeline in `llm-integration.md` §3, with a hard deadline of 25 s.

Persistence: the user message and the assistant message are inserted **in one transaction**, *after* the LLM succeeds. Then, atomically: `UPDATE conversations SET message_count = message_count + 2, updated_at = now(), title = COALESCE(title, :title) WHERE id = :id`. The quota counter is incremented only on success.

- **200** → `Message[]` of **exactly two** elements, `[savedUserMessage, assistantMessage]` (`ChatPage` destructures `const [savedUserMsg, aiMsg] = res.data`).
- **503** `AI_UNAVAILABLE` when all providers failed or the deadline passed. Nothing is persisted and no quota is consumed. The frontend shows its own "stars are obscured" bubble.
- **422** `INPUT_REJECTED` when the safety pre-filter blocks the input (`llm-integration.md` §8). The detail is a gentle redirect message.

### H6 [v1-add] `POST /chat/conversations/{id}/messages/stream`

Same body as H5. The response is `text/event-stream` with these events:

- `event: meta` `{user_message: Message}`
- `event: delta` `{text}` (repeated)
- `event: done` `{assistant_message: Message}`
- `event: error` `{code, detail}`

The final validated text is what gets persisted. The hallucination guard runs on the full text before `done`. If it fails, an `event: replace` `{text}` carries the corrected answer. The frontend must use `fetch` + `ReadableStream` (axios doesn't stream in browsers).

### H7 [v1-add] `PUT /chat/messages/{id}/bookmark` `{ "bookmarked": boolean }` → `Message`.

### H8 [v1-add] `POST /chat/messages/{id}/feedback` `{ "rating": "up" | "down", "reason"?: "inaccurate"|"generic"|"harmful"|"other", "comment"?: string ≤ 500 }` → 204. This feeds the eval set (`llm-integration.md` §9).

### H9 [v1-add] `GET /chat/suggestions?conversation_id=` → `{ suggestions: string[] }` (3–4). Template-driven from the user's top chart factors, so there's no LLM cost.

### H10 [v1-add] `PATCH /chat/conversations/{id}` `{ "title"?: string, "status"?: "active"|"archived" }`.

---

## 7. Horoscope endpoints

### R1 `GET /horoscopes/daily?sign=<sign>` [MVP]

- `sign`: an English sign name, case-insensitive (the frontend sends `chart_data.sun_sign.sign.toLowerCase()`). Invalid → 400 `INVALID_SIGN`.
- Auth: optional. The frontend sends the token if it has one.
- **Date resolution:** if `date` is given (v1-add, `YYYY-MM-DD`, within today ±1), use it. Otherwise use "today" in the authenticated user's `timezone`, or in `Asia/Kolkata` for anonymous callers (the primary audience; this is a decision, see PRD §15).
- **200** → `DailyHoroscope`. Served from Redis `horoscope:{sign}:{date}` (TTL until 06:00 UTC the next day, roughly 30 h) → Postgres `daily_horoscopes` → generated on miss under a Redis lock `lock:horoscope:{sign}:{date}` (`SET NX EX 30`). Concurrent requests wait up to 10 s polling the cache, then return 503 `AI_UNAVAILABLE`.
- If the LLM is down and nothing is cached: return the **deterministic template reading** built from `transit_data` (`llm-integration.md` §7.3), with `created_at` = now. Never return 5xx for a reading if templating is possible. Don't persist the template to Postgres, so a later LLM generation replaces it.
- The cron job pre-generates all 12 signs for today and tomorrow at 18:00 UTC (= 23:30 IST): 24 LLM calls/day, batched where the provider allows.

#### 7.1 `transit_data` shape (also used by v1 personal readings)

```json
{
  "computed_for": "2026-10-01T00:00:00Z",
  "zodiac": "tropical",
  "moon": { "sign": "Taurus", "phase": "waxing_gibbous", "illumination": 0.78, "void_of_course": false },
  "positions": [{ "planet": "Mars", "sign": "Scorpio", "degree": 12.4, "retrograde": false }],
  "aspects_today": [{ "planet1": "Venus", "planet2": "Saturn", "type": "trine", "orb": 0.6, "applying": true }],
  "ingresses_today": [{ "planet": "Mercury", "from": "Libra", "to": "Scorpio", "at": "2026-10-01T14:12:00Z" }],
  "solar_house_focus": { "moon_house": 3, "highlighted_houses": [3, 7] }
}
```

### R2 `GET /horoscopes/daily/{date}?sign=` [MVP per README; unused by frontend]

Same as R1 with the date in the path. **v1.1: allowed range is today −1 to today +1** (a public endpoint that can trigger LLM generation; out of range gives 422 `DATE_OUT_OF_RANGE`).

### R3 [v1-add] `GET /horoscopes/personal/today`

Auth required; uses the primary chart. Returns a `PersonalReading`:

```ts
{
  date: string; chart_id: string; system: "vedic" | "western";
  headline: string;                 // ≤ 90 chars
  overview: string;                 // 90–150 words
  areas: { love: AreaReading; career: AreaReading; wellness: AreaReading; money: AreaReading };
  // AreaReading = { score: 1..5; text: string /* 30–60 words */ }
  key_factors: Array<{ factor_id: string; label: string; weight: number }>;  // ≤ 5
  timing: { best_window?: { start: string; end: string; reason: string }; rahu_kaal?: { start: string; end: string } };
  dasha_context?: { maha: string; antar: string; note: string };
  affirmation: string;
  lucky: { number: number; color: string };
  generated_by: "llm" | "template";
}
```

Cached at `daily_personal:{user_id}:{date}` until local midnight + 2 h, and persisted to `personal_readings` (migration 004) for history.

**[v1.1] Freshness and failure rules.** A stored reading is served only if it was generated from the *current* primary chart (`chart_id`), in the user's *current* `system`, by the *current* engine version (`engine_version` is part of the object), and after the chart's last edit; editing or deleting a chart deletes its stored readings. If the engine cannot produce the facts the endpoint answers **503 `PERSONAL_READING_UNAVAILABLE`** with `Retry-After: 30`: the client shows a retry state and must **not** substitute a generic or other-system horoscope (R1 is Western/tropical by default; never present it as the user's own reading). If only the LLM is down the reading is a template **in the same system** (`generated_by: "template"`). `system` is always `"vedic"` or `"western"` and labels every figure in the reading.

---

## 8. Compatibility endpoints

### K1 `POST /compatibility/` [MVP]

Request (`CalculateCompatibilityPayload`): `chart1_id`, `partner_name` (1–100), `partner_date_of_birth`, `partner_time_of_birth|null`, `partner_has_exact_time`, `partner_birth_place_name`, `partner_latitude`, `partner_longitude`, `partner_timezone` (a hint, resolved server-side as in C1 step 5), and `relationship_type` ∈ {romantic, friend, family, coworker}.

[v1-add] optional `partner_ashtakoota_role: "bride" | "groom"` and `self_ashtakoota_role` (see `astrology-engine.md` §7.2).

Steps:

1. `chart1_id` must be owned → else 404.
2. Find or create the partner `birth_charts` row. Dedupe key: `(user_id, lower(name), date_of_birth, time_of_birth, round(lat,3), round(lon,3))`. `relationship` = `partner` for romantic, otherwise the type itself.
3. Deterministic scoring (`astrology-engine.md` §7). It never depends on the LLM.
4. Narrative: one structured LLM call that produces the five category `summary`s, the 3 strengths, the 3 challenges, the per-aspect `interpretation` (≤ 30 words each) and `summary`. On failure, use templated text from the knowledge-base snippets (§7.3 of `llm-integration.md`). The report is always returned.
5. Persist `compatibility_reports` (`overall_score` NUMERIC(3,1)).

- **201** → `CompatibilityReport`.
- Quota: free 3 reports / calendar month, premium 50 → 429 `QUOTA_EXCEEDED`. Requires `email_verified` (403).
- An identical request (same chart pair and relationship_type) within 30 days returns the existing report (**200**) instead of recomputing.

### K2 `GET /compatibility/` [MVP] → `CompatibilityReport[]`, newest first, `LIMIT 50`.

### K3 `GET /compatibility/{id}` [MVP] → `CompatibilityReport`, or 404.

### K4 [v1-add] `DELETE /compatibility/{id}` → 204. Doesn't delete the partner chart.

---

## 9. Geocoding and misc

### G1 `GET /geocoding/search?q=<text>` [MVP]

- `q`: 3–100 chars after trim. The frontend debounces at 400 ms and only calls when length ≥ 3.
- Auth: **required** (it calls a metered third party). The hook only runs inside protected routes.
- Normalise `q` (NFKC, lower-case, collapse whitespace), then read the Redis cache `geo:q:{sha1(q)}`, TTL 30 days.
- On miss: LocationIQ `/v1/autocomplete?q=&limit=5&tag=place:city,place:town,place:village,place:hamlet&dedupe=1&normalizecity=1`, 3 s timeout. On error or 429, fall back to the secondary provider (`architecture.md` §8) once.
- Each result: `name` = `display_place` + `", "` + the `display_address` parts; `lat`/`lon` as numbers; `timezone` = `timezonefinder` on lat/lon.
- **200** `{ "results": GeocodingResult[] }` (≤ 5; the frontend also tolerates a bare array, but always send the object).
- Both providers failing → **200** `{ "results": [] }` plus a log line (the UI shows "no matches"). [v1-add] the response carries `"degraded": true` so the UI can say "Location search is having trouble. Try again in a minute."
- Rate limit: 30 / min / user, plus a global token bucket of 2 req/s toward LocationIQ (their free-tier limit). Requests over the bucket wait up to 1 s, then go to the fallback.
- Attribution: the free LocationIQ plan requires a visible "Search by LocationIQ.com" link next to the place search box. That's a frontend item.

### G2 `GET /health/live` (also at `/health`, outside the `/api/v1` prefix)

Returns `{ "status": "ok", "version": "<git sha>" }`. It **must not touch Postgres or Redis**. The cron-job.org keep-awake ping hits this every 14 min; touching Neon would keep its compute awake 24/7 and burn the free CU-hours (`architecture.md` §8).

### G3 `GET /health/ready`

Checks the DB (`SELECT 1`), Redis `PING` and the engine self-test. Returns 200 or 503. Used by Render's health check, not by the pinger.

---

## 10. Error codes

| HTTP | code | When |
|---|---|---|
| 400 | `INVALID_CREDENTIALS` | login failure |
| 400 | `INVALID_CURRENT_PASSWORD` | change-password |
| 400 | `NO_PASSWORD_SET` | change-password on an OAuth-only account |
| 400 | `INVALID_CODE` / `CODE_EXPIRED` | verify-email |
| 400 | `INVALID_OR_EXPIRED_TOKEN` | reset-password |
| 400 | `INVALID_SIGN` | horoscopes |
| 401 | `UNAUTHENTICATED` | missing, invalid, expired or revoked token (triggers the frontend logout) |
| 403 | `EMAIL_NOT_VERIFIED` | LLM-backed endpoints |
| 403 | `CHART_LIMIT_REACHED`, `PREMIUM_REQUIRED`, `AI_CONSENT_REQUIRED` | |
| 404 | `NOT_FOUND` | missing or not owned |
| 409 | `EMAIL_EXISTS`, `PASSWORD_ALREADY_SET`, `CHART_REQUIRED`, `MESSAGE_IN_FLIGHT` | |
| 422 | `PRIMARY_MUST_BE_SELF`, `VALIDATION_ERROR` (generic), `DATE_OUT_OF_RANGE`, `BIRTH_TIME_NONEXISTENT`, `INVALID_LOCATION`, `MESSAGE_TOO_LONG`, `PASSWORD_TOO_COMMON`, `PASSWORD_TOO_LONG`, `INPUT_REJECTED` | |
| 429 | `RATE_LIMITED`, `QUOTA_EXCEEDED` | with `Retry-After` |
| 500 | `INTERNAL_ERROR`, `CHART_CALCULATION_FAILED` | |
| 503 | `AI_UNAVAILABLE`, `DEPENDENCY_UNAVAILABLE`, `PERSONAL_READING_UNAVAILABLE` | **every 503 carries `Retry-After`** (seconds: 5 database waking up, 10 default, 30 personal reading) |

---

## 11. Gaps and inconsistencies found in the frontend services

Severity: **H** = will break or corrupt something, **M** = degrades UX or safety, **L** = cosmetic or debt.

| ID | Sev | Finding | Contract resolution | Frontend follow-up |
|---|---|---|---|---|
| G-01 | H | The global 401 interceptor (`api.ts`) wipes the token and hard-redirects. A 401 from **login** or **change-password** would erase the error and log the user out. | Those return 400 (§1.4). | v2: skip the interceptor for `/auth/login` and `/auth/register` anyway. |
| G-02 | H | FastAPI's default 422 `detail` is an array, but every page expects a string, so users see "Something went wrong" on any validation error. | Custom 422 handler (§1.3). | none |
| G-03 | M | Unverified users are never routed to `/verify` after login; `LoginForm` goes straight to `/dashboard`. | LLM endpoints return 403 `EMAIL_NOT_VERIFIED`. | Read `user.email_verified` after `fetchUser()` and route to `/verify`; handle that 403 code in chat/compat with a CTA. |
| G-04 | H | The OAuth callback passes the JWT in the **query string** (`?token=`). It leaks to history, logs and Referer. | MVP keeps it. Backend sets `Referrer-Policy: no-referrer` on the redirect, and the frontend should `history.replaceState` to strip it. | v2: one-time code exchange (§12.1). |
| G-05 | H | Onboarding and Compatibility fall back to the **browser's** timezone when the geocoder returns none. A user in Delhi entering a New York birthplace would get a chart off by 9.5 h. | The server always resolves tz from lat/lon and ignores the client value (C1 step 5). | Remove the fallback; show the resolved zone ("Time zone: Asia/Kolkata (IST, UTC+5:30 on that date)") before submit. |
| G-06 | M | The `BirthChart` type has `relationship_label`; the DB column is `relationship`; the create payload has no relationship field. | Serialize `relationship` as `relationship_label`; derive it on create (C1 step 7). | v1: add an optional `relationship` to the create payload. |
| G-07 | H | Dashboard, Chart and Profile all use `charts[0]` as "my chart", but nothing defines list ordering. Once compatibility creates partner charts, the user could see their partner's chart as their own. | `ORDER BY is_primary DESC, created_at ASC` is contractual (C2). | v1: select `charts.find(c => c.is_primary)`. |
| G-08 | M | The daily horoscope is fetched by **tropical sun sign** only (generic content), while the chart page is Vedic-first (sidereal, Lahiri). For many Indian users the tropical sun sign differs from the sidereal sun sign and from their Moon sign (rashi), which is what Indian horoscopes use. | Keep R1 as is; add R3 (personal reading); [v1-add] R1 accepts `system=vedic&basis=moon` | Dashboard should call R3 when authenticated, falling back to R1. |
| G-09 | M | `ChartPage.tsx` re-implements astrology client-side: `detectAdditionalYogas`, `calculateVedicAspects`, `generateCoreSignature`, `ensureRahuKetu`, plus large interpretation tables. That's two sources of truth, and they will drift. | The engine always returns Ketu, the full yoga list, graha drishti and the house lords (see `astrology-engine.md` §9). | v1: delete the client-side derivations and render the server data. |
| G-10 | M | `sendMessage` is non-streaming with no client timeout. A slow LLM means 10–25 s of spinner. | Server deadline 25 s → 503. | v1: H6 streaming; set an axios `timeout: 30000` on chat. |
| G-11 | L | `Message.bookmarked` exists in the type, but no service can set it. | H7 [v1-add]. | Add a bookmark action. |
| G-12 | M | After `deleteAccount` the page navigates to `/` without calling `logout()`, so `localStorage.token` remains (a 401 then cleans it up on the next call). | n/a | Call `useAuthStore.logout()` after delete. |
| G-13 | L | Spelling drift: `RASHI_DEVANAGARI` uses `Vrischika`, while `RASHI_TO_ENGLISH` uses `Vrishchika`; dignity badge key is `mooltrikona`. | The engine emits `Vrishchika` and `mooltrikona` exactly (`astrology-engine.md` §2). | Fix the Devanagari map key. |
| G-14 | M | `resendOtp` and `verifyEmail` need the bearer token, but `VerifyPage` redirects to `/auth` when not authenticated. A user who registers and closes the tab can only verify after logging in. That's acceptable, but the email should say so. | Email copy: "Log in and enter this code". | none |
| G-15 | L | The compatibility "Ask the Oracle" handoff passes the score in free text via router state. The chat has no link to the report. | [v1-add] H1 accepts `category:"compatibility"` and `context_report_id`. | Pass `context_report_id`. |
| G-16 | M | `User.subscription_tier` is a free string. There are no quota fields, so the UI can't show "3 of 5 questions left" until it hits a 429. | [v1-add] `User.quota`. | Show the remaining count. |
| G-17 | L | There's no `has_password` on `User`, so Profile can't know whether to show "change" or "set" password. | [v1-add] `User.has_password`. | Use it. |
| G-18 | M | Nothing in the API tells the user whether the AI or the geocoder is degraded. | [v1-add] `degraded` flags (G1; R3 `generated_by`). | Show a subtle notice. |
| G-19 | L | `Conversation.status` is typed as a string; `"deleted"` is never used because deletes are hard. | Values limited to `active \| archived`. | none |
| G-20 | M | The `ChartData` type makes `vedic` optional, and `ChartPage` has a non-Vedic fallback branch. | The engine **always** returns both `vedic` and the Western blocks. | none |

## 12. Proposed v2 changes (need a coordinated frontend release)

1. **OAuth one-time code (fixes G-04).** The callback redirects to `/auth/callback?code=<opaque, 60 s, single use>`. The frontend calls `POST /auth/oauth/exchange {code}` → `{access_token}`.
2. **Refresh tokens.** A 15-min access JWT, plus a 30-day rotating refresh token in an `HttpOnly; Secure; SameSite=Lax` cookie scoped to `/api/v1/auth/refresh`, with reuse detection (a family is revoked on replay). Add `POST /auth/refresh` and `POST /auth/logout`. The access token moves out of `localStorage` into memory.
3. **change-password returns a fresh token** and bumps `token_version` (closes the gap noted in A10).
4. **Streaming chat as the default** (H6), and retire the H5 array response.
5. **Typed error codes in the frontend.** `extractError` reads `code`, so the UI can show CTAs (verify email, upgrade, add chart).
6. **Pagination envelope** for list endpoints: `{ items, next_cursor }`. This is breaking for C2, H2 and K2, so only do it once lists can exceed 50.
7. **`/charts/{id}/view?system=vedic|western&house_system=…&ayanamsa=…`**: on-the-fly alternate calculations without re-storing. Lets enthusiasts switch Placidus ↔ Whole Sign and Lahiri ↔ KP/Raman.
