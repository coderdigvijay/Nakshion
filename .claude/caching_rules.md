# Caching Rules - Redis (Upstash)

Redis is a cache, never a system of record. Every cached value can be rebuilt from Postgres,
Swiss Ephemeris, or the LLM. All cache access goes through one module (`services/cache.py`,
target layout) with typed helpers. Do not scatter raw `redis.get` calls.

## 1. Key registry (add new keys here first)

| Key | Value | TTL | Invalidated by |
|---|---|---|---|
| `geo:v1:{normalized_query}` | lat, lon, display name, IANA tz | 30 days | never (places do not move) |
| `daily:v{prompt_ver}:{system}:{sign}:{date}` | daily reading JSON | 36 h | TTL only (no user mutation path) |
| `transits:v{engine_ver}:{system}:{date}` | day's planetary positions | 36 h | TTL; engine version in key |
| `chart_summary:v{engine_ver}.{prompt_ver}:{chart_id}` | base AI interpretation of a chart | 30 days | chart update/delete **and** version bump (in key) |
| `compat:v{engine_ver}.{prompt_ver}:{report_id}` | rendered report | 30 days | either chart edited/deleted, report deleted |
| `quota:{user_id}:{yyyy-mm-dd}` | LLM requests/tokens used today | until end of day + 1 h | `INCR`/`INCRBY` only |
| `rl:{scope}:{id}:{window}` | rate-limit counter | window | expiry |
| `lock:daily:{system}:{sign}:{date}` | generation lock | 120 s | released in `finally` |

**Implemented in the rebuilt backend (2026-10-01; `backend/app/services/cache.py` is the only Redis
client; names follow `docs/architecture.md` section 6 and supersede the target rows above where they differ):**

| Key | Owner | TTL | Invalidated by / failure mode |
|---|---|---|---|
| `otp:{user_id}` / `otp_attempts:{user_id}` | auth | 10 min | verify success, new OTP; fail-closed (503) |
| `otp_resend_min:{user_id}` / `otp_resend_day:{user_id}` | auth | 60 s / 24 h | expiry; fail-closed |
| `oauth_state:{state}` | oauth | 10 min | GETDEL on callback; fail-closed |
| `authfail:{ip}:{sha1(email)}` / `authfail:{ip}` | auth | 15 min | successful login; Redis down falls back to an in-process limit |
| `geo:q:{sha1(normalised q)}` | geocoding | 30 d (empty: 1 d) | none; degraded results never cached |
| `horoscope:{sign}:{date}:{system}` | horoscope | until 06:00 UTC next day (template: 10 min) | none (immutable per date); L1 in-process |
| `lock:horoscope:{sign}:{date}:{system}` | horoscope | 30 s | released in `finally` |
| `daily_personal:{user_id}:{date}` | personal reading | local midnight + 2 h (template: 10 min) | primary chart change, chart PUT/DELETE of primary, timezone change; also self-validates `chart_id` |
| `chart_summary:{chart_id}`, `factors:{chart_id}:*`, `transits:{chart_id}:*`, `compat:*{chart_id}*` | chart | per producer | chart PUT/DELETE (after commit) |
| `chat_lock:{conversation_id}` | chat | 60 s | released in `finally` (also on SSE disconnect) |
| `llm_spend:*`, `emb:q:*` | app/llm, app/rag | see `llm-integration.md` 7 | owned by the AI layer |
| `*{user_id}*`, `*{chart_id}*` | user | n/a | purged after account deletion |

Rules:
- Prefix every key by domain and include a schema/prompt/engine **version segment** wherever
  the value depends on code. A version bump then orphans old entries without a flush.
- Keys contain only server-derived values (ids, normalised strings). Never use raw user input.
  Normalise geocoding queries (lowercase, trim, collapse whitespace) and hash them if long.
- UUIDs in keys, not sequential ints, so cross-user collisions cannot happen.

## 2. Invalidation (mandatory on every mutation of cached data)

- Chart birth data edited: recompute `chart_data`, then delete `chart_summary:*:{chart_id}` and
  every `compat:*` report containing that chart, in the service that performs the update,
  **after** the DB commit succeeds.
- Chart deleted: the same, plus the frontend invalidates its query keys.
- A stale chart interpretation after a birth-time edit is a **correctness bug**, not staleness.
  Astrology output depends on exact birth data.
- Keys with no mutation path (daily readings, geocoding) rely on TTL. Do not build invalidation
  plumbing for them.
- If invalidation fails (Redis down), log it at WARNING. Because the version segment and TTL
  bound the damage, never fail the user's write for a cache error.

## 3. Daily readings (Swiss Ephemeris + LLM, cached 24 h)

- Generated per `(system, sign, date)`, where the date is the reader's local date (from
  `users.timezone`, or the browser timezone for anonymous users). Positions are computed for one
  documented instant per date (for example 12:00 UTC), and that instant is stored in `transit_data`.
- Read path: Redis, then `daily_horoscopes` row, then generate. Generate under the
  `lock:daily:*` lock (`SET NX EX`) so concurrent first readers trigger one LLM call. Losers
  wait briefly and re-read, or get a "being prepared" state. Persist to Postgres
  (`ON CONFLICT DO NOTHING`), then cache.
- Optionally pre-generate the next day's readings in one scheduled batch (cron-job.org ping is
  already in use for keep-awake).

## 4. Failure behaviour

- Redis unreachable means falling through to the source (Postgres, ephemeris, LLM) with a short
  connect timeout. User requests never hard-fail because Redis is down.
- **Exception, fail closed:** quota and rate-limit checks for LLM, LocationIQ, and Brevo calls. If
  the counter cannot be read, deny with a friendly retry message (or apply a conservative
  in-process limit). Failing open would let one outage drain the free-tier quota.
- Upstash bills per command. Use `MGET`/pipelines for multi-key reads; no per-item loops.

## Checklist

- [ ] New key added to the registry table with TTL and invalidation path
- [ ] Version segment present for code-derived values
- [ ] Invalidation after commit on every mutating path; tested
- [ ] Stampede-prone generation guarded by a lock
- [ ] Fail-open for reads, fail-closed for quota/rate limits
