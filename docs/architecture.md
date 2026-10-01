# Nakshion Architecture

**Status:** Build spec for the backend rebuild · **Version:** 1.0 · **Date:** 2026-10-01
**Companion docs:** `api-contract.md` (HTTP surface), `astrology-engine.md` (calculation), `llm-integration.md` (AI/RAG).
Project rules in `.claude/*.md` (backend, database, caching, security) apply on top of this document.

---

## 1. Constraints that drive every choice

| Constraint | Consequence |
|---|---|
| Solo developer | One deployable backend. No microservices, no queue broker, no Kubernetes. Boring, well-documented libraries |
| Render free web service: **0.1 vCPU, 512 MB RAM**, ephemeral filesystem, spins down after 15 min idle, 750 instance-hours / workspace / month | One uvicorn worker. CPU-heavy work (ephemeris) goes on a dedicated thread. Nothing durable on local disk (so chromadb is replaced by pgvector). Keep-awake ping (24 × 31 = 744 h fits inside 750 h, so only **one** always-on free service is possible) |
| Neon free: 0.5 GB storage, **100 CU-hours/month**, autosuspend | The keep-awake ping must **not** touch the DB (`/health/live`). Charts stored as JSONB are about 15–25 KB each, so 0.5 GB holds roughly 20k charts plus chat |
| Upstash Redis free: 256 MB, **500k commands/month**, 10 GB bandwidth | Redis only for cross-request state that needs a TTL (OTP, OAuth state, caches, locks). Quotas live in Postgres; general rate limiting is in-process. In-process L1 cache in front of hot keys |
| Gemini paid tier, pay-as-you-go | Daily budget guard (`llm-integration.md` §7.2) |
| LocationIQ free: 5k req/day, 2 req/s, attribution required | Cache every query for 30 days; global token bucket; secondary provider |
| Brevo free: 300 emails/day (marketing + transactional combined) | Transactional only (OTP, reset, deletion confirmation). No daily-horoscope emails on the free plan. Weekly digest only when opted in and only under 200 subscribers |
| Users: hundreds to low thousands | No sharding, read replicas or CDN for the API. Revisit at more than 5k MAU (§11) |

---

## 2. System overview

```
            ┌───────────────────────────── Browser (React 19 SPA, Render static site) ─────────────────────────────┐
            │  services/*.ts (axios, Bearer JWT)            Web Push SW (v1)                                       │
            └───────────────┬───────────────────────────────────────────────────────────────────────────────────────┘
                            │ HTTPS  /api/v1/*
┌───────────────────────────▼──────────────────────────────────────────────────────────────────────────────────────┐
│ FastAPI app (Render free, 1 uvicorn worker)                                                                          │
│  middleware: request-id → security headers → CORS → in-proc rate limit → auth dep                                  │
│  routers/  (validate → delegate → respond)                                                                          │
│  services/ auth · user · chart · chat · compatibility · horoscope · geocoding · quota · email · cache · ai/ · rag/  │
│  astro/    pure engine (pyswisseph on single-thread executor)                                                       │
│  prompts/  versioned Jinja templates + builder                                                                      │
└───────┬──────────────────────┬─────────────────────┬──────────────────────┬────────────────────────┬───────────────┘
        │ asyncpg              │ redis-py (TLS)      │ httpx                │ google-genai / anthropic│ httpx
   ┌────▼─────┐         ┌──────▼──────┐      ┌───────▼────────┐     ┌───────▼────────┐       ┌──────▼──────┐
   │ Neon PG  │         │ Upstash     │      │ LocationIQ     │     │ Gemini (paid)  │       │ Brevo       │
   │ +pgvector│         │ Redis       │      │ (+ Geoapify fb)│     │ Claude (fb)    │       │ (email)     │
   └──────────┘         └─────────────┘      └────────────────┘     └────────────────┘       └─────────────┘
   cron-job.org ──► GET /health/live every 14 min (no DB)   and   POST /internal/cron/{job} (secret header)
```

---

## 3. Backend layout (rebuild target)

```
backend/
  app/
    main.py                 # app factory: settings, logging, middleware, exception handlers, routers, lifespan (ephemeris self-test, engine executor, http clients)
    core/
      config.py             # pydantic-settings; refuses prod boot with default secrets
      security.py           # bcrypt (cost 12), JWT encode/decode (python-jose), token_version check
      errors.py             # AppError(code, status, detail) + handlers producing {detail, code, errors}
      deps.py               # get_db, get_current_user, require_verified, get_redis
      ratelimit.py          # in-process sliding-window limiter (per IP / per user), Redis-backed only for auth brute-force keys
      logging.py            # JSON logs, request_id contextvar, PII scrubbing filter
    db/  session.py base.py
    models/                 # SQLAlchemy 2.0 typed models, one file per domain (user, chart, chat, compatibility, horoscope, usage, kb, notification)
    schemas/                # Pydantic v2 request/response — routers never return ORM objects
    routers/                # auth, users, charts, chat, compatibility, horoscopes, geocoding, panchang (v1), health, internal
    services/
      auth_service.py  user_service.py  chart_service.py  chat_service.py  compatibility_service.py
      horoscope_service.py  geocoding_service.py  quota_service.py  email_service.py  cache.py  consent_service.py
      ai/  router.py  providers/{gemini.py,anthropic.py,fake.py}  pipeline.py  validators.py  safety.py  lexicon.py  templates/
      rag/ retriever.py  embedder.py
    astro/                  # pure; see astrology-engine.md (engine.py, timezones.py, western.py, vedic.py, dasha.py, vargas.py, yogas.py, panchang.py, transits.py, scoring.py, compatibility.py, ashtakoota.py, data/)
    prompts/  builder.py  registry.yaml  chat/v1.j2  daily_personal/v1.j2  daily_sign/v1.j2  compat/v1.j2
  ephe/                     # sepl_18.se1 semo_18.se1 seas_18.se1 (committed)
  alembic/versions/         # 001, 002 (existing) + 003, 004, 005 (below)
  knowledge_base/  _manifest.yaml
  scripts/  index_kb.py  recompute_charts.py  create_db.py  make_golden_fixtures.py
  evals/    cases.jsonl  run.py  reports/
  tests/    unit/ astro/golden/ api/ contract/ ai/
```

**Dependency changes to `requirements.txt`** (pin exact versions at implementation time):

| Change | Package | Why |
|---|---|---|
| remove | `google-generativeai` | End of support 2025-11-30 |
| remove | `chromadb` | Replaced by pgvector (§4, `llm-integration.md` §6.4) |
| add | `google-genai` | Supported Gemini SDK |
| add | `anthropic` | Fallback provider |
| add | `pgvector` | SQLAlchemy vector type |
| add | `fastembed` | Local ONNX embeddings, no torch |
| add | `tzdata` | Pinned IANA data, independent of the host OS |
| add | `jinja2` | Prompt templates |
| add (v1) | `pywebpush` | Web Push notifications |
| propose | `sentry-sdk` | Error tracking, free tier. Needs owner approval (not currently installed) |
| dev | `pytest`, `pytest-asyncio`, `hypothesis`, `fakeredis`, `respx`, `pytest-benchmark`, `pip-audit` | Testing and security |

There's no new web framework, task queue or OAuth library. Google OAuth is implemented with `httpx` plus `python-jose` JWKS verification (about 120 lines).

---

## 4. Data model

### 4.1 Existing tables (migrations 001, 002), which are kept

`users`, `password_resets`, `birth_charts`, `conversations`, `messages`, `daily_horoscopes`, `compatibility_reports`. Their column shapes are in the migration files. Mapping notes:

- `birth_charts.relationship` ↔ API `relationship_label`.
- `messages.metadata` holds citations, provider, prompt_version and validator flags (`llm-integration.md` §3 [9]).
- `password_resets.token` stores the **SHA-256 of the raw token** (the column type is unchanged).

### 4.2 Migration 003: integrity and auth hardening (MVP, reversible)

```sql
-- users
ALTER TABLE users ADD COLUMN token_version INT NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN preferred_language VARCHAR(10) NOT NULL DEFAULT 'english'
  CHECK (preferred_language IN ('english','hindi','hinglish'));
ALTER TABLE users ADD COLUMN astrology_system VARCHAR(10) NOT NULL DEFAULT 'vedic'
  CHECK (astrology_system IN ('vedic','western'));
ALTER TABLE users ADD COLUMN terms_accepted_at TIMESTAMPTZ;      -- set at register / first OAuth
ALTER TABLE users ADD COLUMN age_confirmed_at TIMESTAMPTZ;       -- 18+ checkbox
ALTER TABLE users ADD COLUMN ai_consent_at TIMESTAMPTZ;          -- explicit consent to process birth data with AI providers
ALTER TABLE users ADD COLUMN ai_consent_withdrawn_at TIMESTAMPTZ;
ALTER TABLE users ADD CONSTRAINT ck_users_tier CHECK (subscription_tier IN ('free','premium'));
CREATE UNIQUE INDEX uq_users_oauth ON users (oauth_provider, oauth_id) WHERE oauth_provider IS NOT NULL;

-- birth_charts
ALTER TABLE birth_charts ADD COLUMN engine_version VARCHAR(20) NOT NULL DEFAULT '0.0.0';
ALTER TABLE birth_charts ADD CONSTRAINT ck_chart_relationship
  CHECK (relationship IN ('self','partner','friend','family','coworker','other'));
CREATE UNIQUE INDEX uq_birth_charts_one_primary ON birth_charts (user_id) WHERE is_primary;
CREATE INDEX ix_birth_charts_user_order ON birth_charts (user_id, is_primary DESC, created_at);

-- conversations: chart deletion must not delete or block chat history
ALTER TABLE conversations DROP CONSTRAINT conversations_chart_id_fkey;
ALTER TABLE conversations ADD CONSTRAINT conversations_chart_id_fkey
  FOREIGN KEY (chart_id) REFERENCES birth_charts(id) ON DELETE SET NULL;
ALTER TABLE conversations ADD CONSTRAINT ck_conv_status CHECK (status IN ('active','archived'));
CREATE INDEX ix_conversations_user_updated ON conversations (user_id, updated_at DESC);

-- messages
ALTER TABLE messages ADD CONSTRAINT ck_msg_role CHECK (role IN ('user','assistant'));
CREATE INDEX ix_messages_conv_created ON messages (conversation_id, created_at);
-- (the existing single-column created_at index can be dropped in the same migration)

-- compatibility
CREATE INDEX ix_compat_user_created ON compatibility_reports (user_id, created_at DESC);
CREATE INDEX ix_compat_dedupe ON compatibility_reports (user_id, chart1_id, chart2_id, relationship_type, created_at DESC);
ALTER TABLE compatibility_reports ADD CONSTRAINT ck_compat_score CHECK (overall_score BETWEEN 0 AND 10);

-- horoscopes: allow a sidereal/moon-sign variant
ALTER TABLE daily_horoscopes ADD COLUMN system VARCHAR(10) NOT NULL DEFAULT 'western';
ALTER TABLE daily_horoscopes DROP CONSTRAINT uq_horoscope_sign_date;
ALTER TABLE daily_horoscopes ADD CONSTRAINT uq_horoscope_sign_date_system UNIQUE (zodiac_sign, date, system);

-- quotas (atomic, Postgres-backed; saves Redis commands)
CREATE TABLE usage_counters (
  user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  kind        VARCHAR(30) NOT NULL,      -- 'chat_reply' | 'compat_report' | 'premium_report' | 'chart_create'
  period      VARCHAR(10) NOT NULL,      -- 'day' | 'month'
  period_start DATE NOT NULL,            -- in the user's timezone
  count       INT NOT NULL DEFAULT 0,
  PRIMARY KEY (user_id, kind, period, period_start)
);
```

Downgrade reverses each statement. The `daily_horoscopes` downgrade first deletes the rows where `system <> 'western'`. That's the only lossy step; it's documented in the migration docstring, as `database_rules.md` requires.

The partial unique index needs a pre-step: `UPDATE birth_charts SET is_primary=false WHERE id NOT IN (SELECT DISTINCT ON (user_id) id FROM birth_charts WHERE is_primary ORDER BY user_id, created_at)`. Existing production data may hold more than one primary per user.

### 4.3 Migration 004: AI, RAG and feedback (MVP)

- `kb_chunks`, `kb_meta`: as in `llm-integration.md` §6.4.
- `kb_key_embeddings (key TEXT, index_version INT, embedding VECTOR(384), PRIMARY KEY(key, index_version))`.
- `llm_usage`:

  ```sql
  CREATE TABLE llm_usage (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NULL REFERENCES users(id) ON DELETE SET NULL,   -- NULL for sign horoscopes; keeps cost history after account deletion
    task VARCHAR(30) NOT NULL, provider VARCHAR(20) NOT NULL, model VARCHAR(60) NOT NULL,
    prompt_version VARCHAR(20) NOT NULL,
    input_tokens INT NOT NULL, cached_input_tokens INT NOT NULL DEFAULT 0, output_tokens INT NOT NULL,
    cost_usd NUMERIC(10,6) NOT NULL, latency_ms INT NOT NULL,
    outcome VARCHAR(12) NOT NULL,          -- ok | repaired | fallback | failed | blocked
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
  );
  CREATE INDEX ix_llm_usage_created ON llm_usage (created_at);
  CREATE INDEX ix_llm_usage_user_created ON llm_usage (user_id, created_at);
  ```

- `message_feedback (message_id UUID PK REFERENCES messages ON DELETE CASCADE, user_id UUID NOT NULL REFERENCES users ON DELETE CASCADE, rating VARCHAR(4) CHECK (rating IN ('up','down')), reason VARCHAR(20), comment VARCHAR(500), created_at TIMESTAMPTZ)`.
- `personal_readings (user_id, chart_id, date, system, reading JSONB, generated_by, created_at, PRIMARY KEY (user_id, date, system))`. Rows older than 90 days are deleted by cron.

### 4.4 Migration 005: engagement and monetisation (v1)

- `push_subscriptions (id, user_id, endpoint TEXT UNIQUE, p256dh, auth, user_agent, created_at, last_success_at)`.
- `notification_prefs (user_id PK, daily_push BOOL, push_hour_local SMALLINT DEFAULT 7, transit_alerts BOOL, weekly_email BOOL)`.
- `subscriptions (id, user_id, provider 'razorpay', provider_sub_id UNIQUE, plan, status, current_period_end, created_at, updated_at)`, plus `payment_events (id, provider_event_id UNIQUE, payload JSONB, received_at)` for idempotent webhooks.
- `deletion_log (id, user_id_sha256, deleted_at)`.
- `users.subscription_tier` remains the **denormalised** flag that request paths read. Only the webhook handler writes it, in the same transaction as `subscriptions`.

### 4.5 Storage estimate (Neon 0.5 GB)

| Item | Size | Supports |
|---|---|---|
| Chart row | ~20 KB (with D9/D10 and the dasha timeline) | 5k users × 3 charts ≈ 300 MB (the dominant term) |
| Message | ~1 KB | 200k messages ≈ 200 MB |
| KB | ~3 MB with vectors | |

**Mitigations:**

- Store the dasha `timeline` with antardashas compressed (dates only).
- Prune `personal_readings` after 90 days.
- Upgrade trigger: storage over 70 % → Neon Launch plan (owner decision; PRD §14).

---

## 5. Authentication and authorisation

- Passwords use bcrypt with cost 12. **bcrypt only reads 72 bytes**, so passwords are limited to 8–72 UTF-8 **bytes**. Validation enforces this (rather than truncating silently) and returns `PASSWORD_TOO_LONG` (see `api-contract.md` A1).
- JWT details are in `api-contract.md` §1.5. **Revocation:** `token_version` is compared on every authenticated request. That's one indexed PK lookup, which the `get_current_user` dependency already does when it loads the user, so it costs nothing extra.
- **Ownership:** every chart, conversation, message and report query filters `WHERE user_id = :current_user` in the service layer. A cross-user access returns 404. This is covered by a parametrised IDOR test suite that hits every resource route with a second user's token.
- **`require_verified` dependency** applies to: H5, H6, K1, R3 and the premium report.
- **OAuth:** Google only (MVP), using `state` + PKCE as described in `api-contract.md` A8/A9. Facebook is dropped (low value for the audience, high review overhead).
- **Internal cron endpoints** require the `X-Cron-Secret` header, compared in constant time, and are rate-limited to 1 call per job per 5 minutes.
- **Security headers** (on the API):
  - `Strict-Transport-Security: max-age=31536000`
  - `X-Content-Type-Options: nosniff`
  - `Referrer-Policy: no-referrer`
  - `X-Frame-Options: DENY`
  - `Content-Security-Policy: default-src 'none'; frame-ancestors 'none'` (JSON API)

  The static frontend gets a CSP from Render static-site headers (owned by the frontend).

---

## 6. Caching

The rules in `.claude/caching_rules.md` apply. Key prefixes are greppable, and every key that has a mutation path gets explicit invalidation.

| Key | Owner service | TTL | Invalidated by |
|---|---|---|---|
| `otp:{user_id}` | auth | 10 min | verify success, resend |
| `oauth_state:{state}` | auth | 10 min | consumed on callback |
| `authfail:{ip}:{email_sha1}` | auth | 15 min | successful login |
| `geo:q:{sha1}` | geocoding | 30 d | none (places don't move) |
| `transits:{date}` | astro (via chart_service) | 48 h | none |
| `factors:{chart_id}:{engine_ver}` | chart | 30 d | chart PUT/DELETE |
| `transits:{chart_id}:{yyyy-mm}` | chart | 35 d | chart PUT/DELETE |
| `chart_summary:{chart_id}` | chart | 30 d | chart PUT/DELETE |
| `horoscope:{sign}:{date}:{system}` | horoscope | until 06:00 UTC + 1 d | none (immutable per date) |
| `daily_personal:{user_id}:{date}` | horoscope | local midnight + 2 h | primary chart change, chart PUT |
| `emb:q:{sha1}` | rag | 7 d | re-index (version is in the value) |
| `chat_lock:{conversation_id}` | chat | 60 s | released in `finally` |
| `lock:horoscope:{sign}:{date}` | horoscope | 30 s | released after write |
| `llm_spend:{date}` | ai | 48 h | none |

- **L1 in-process cache** (a TTL dict, ≤ 5k entries) in front of `transits:{date}`, `horoscope:*` and `kb_meta`. It's safe because there's a single instance, and it cuts Redis commands by 60–80 % for the dashboard's hot path.
- **Redis down:** every cache read is fail-open (treated as a miss, logged). Locks fail-open with a short in-process lock fallback. OTP and OAuth state fail-closed (503 `DEPENDENCY_UNAVAILABLE`), because they're security state.
- **Command budget check:** a 300-DAU estimate of roughly 12 commands per user-day comes to about 108k commands a month, against Upstash's 500k. An alert fires at 70 % (weekly digest).

---

## 7. Rate limits and quotas

**Rate limits** (anti-abuse; in-process sliding window unless marked Redis):

| Scope | Limit |
|---|---|
| Any route per IP | 120/min |
| Login failures (Redis) | 10 / 15 min per (IP, email); 50 / 15 min per IP |
| Register | 5/h per IP |
| Forgot password | 3/h per email, 10/h per IP |
| OTP resend | 1/min, 5/day per user |
| Geocoding | 30/min per user; global 2 req/s to LocationIQ |
| Chat send | 6/min per user, plus a 1-in-flight lock per conversation |
| Chart create | 20/h per user |
| Compatibility create | 10/h per user |

**Quotas** (product limits, Postgres `usage_counters`, user-local periods):

| Kind | Free | Premium |
|---|---|---|
| `chat_reply` / day | 5 | 60 |
| `compat_report` / month | 3 | 50 |
| `premium_report` / month | 0 | 4 |
| charts total | 10 | 100 |

**Atomic consume:**

```sql
INSERT INTO usage_counters (user_id, kind, period, period_start, count) VALUES (:u, :k, :p, :d, 1)
ON CONFLICT (user_id, kind, period, period_start)
DO UPDATE SET count = usage_counters.count + 1 WHERE usage_counters.count < :limit
RETURNING count;
```

No row returned means the quota is exceeded. The consume runs **after** the LLM succeeds, in the same transaction as the message insert. A pre-check (a read) before the LLM call avoids wasting a call on a user who is already at the limit. The race window (two parallel requests both passing the pre-check) is closed by the per-conversation lock, and across conversations by the `WHERE count < limit` guard. At worst, the final call costs tokens and then returns 429. That's acceptable.

---

## 8. External services and failure modes

| Service | Use | Timeout | Fallback | User-visible degradation |
|---|---|---|---|---|
| Neon Postgres | everything durable | 5 s connect, 10 s statement | none | 503 everywhere except `/health/live` |
| Upstash Redis | caches, OTP, locks | 1 s | fail-open (except OTP/OAuth) | slower; OTP/OAuth temporarily unavailable |
| Gemini (paid) | chat and daily text | 15 s | Claude Haiku 4.5, then templates | "Simplified reading"; chat 503 only if both fail |
| Anthropic | fallback, premium, eval judge | 15 s | Gemini Flash | — |
| LocationIQ | place autocomplete | 3 s | **Geoapify** autocomplete (free: 3k/day, results may be stored, attribution required) | empty results with a `degraded` flag |
| Brevo | OTP, reset, deletion email | 5 s, retried 3× in a background task | log + allow resend | "Didn't get it? Resend" |
| Google OAuth | sign-in | 5 s | email/password | error on the callback page |
| cron-job.org | keep-awake, scheduled jobs | — | manual trigger | missed pre-generation is regenerated lazily on demand |

**Geocoder decision:** LocationIQ stays primary. It's already integrated, has the most generous free daily quota (5k/day) and an OSM-based global gazetteer with good Indian village coverage. **Geoapify** is the configured fallback (`GEOCODER_FALLBACK=geoapify`), because its terms explicitly allow storing and caching results. Google Places was rejected: it's paid, and its terms restrict caching. Nominatim's public instance was rejected: 1 req/s and no autocomplete use allowed. Attribution links for both providers are a frontend requirement.

**Scheduled jobs** (`POST /internal/cron/{job}`, called by cron-job.org):

| Job | Schedule (UTC) | Work |
|---|---|---|
| `pregen_horoscopes` | 18:00 daily | 12 signs × {today+1} × {western, vedic-moon}: 24 Flash-Lite calls, batched |
| `hourly` | every hour at :05 | expire `password_resets` older than 24 h, prune `personal_readings` > 90 d; v1: send web-push dailies to users whose `push_hour_local` = now |
| `weekly_digest` | Mon 03:30 | owner email: spend, repair rate, feedback, Redis/Neon usage |
| `charts_upgrade` | daily 21:00 | recompute up to 200 charts below the current engine major |

---

## 9. Configuration (env vars)

Existing variables in `.env.example` are kept. The ones below are **added** (the `.env.example` update ships with the rebuild):

```
API_PUBLIC_URL=http://localhost:8000          # for the OAuth redirect URI
CRON_SECRET=...                                # internal cron auth
OTP_PEPPER=...                                 # hashing OTPs
ANTHROPIC_API_KEY=...
LLM_MODEL_CHAT=gemini-3.8-flash
LLM_MODEL_DAILY=gemini-3.5-flash-lite
LLM_MODEL_PREMIUM=claude-sonnet-5-5
LLM_FALLBACK_CHAT=claude-haiku-4-5
LLM_FALLBACK_DAILY=gemini-3.1-flash-lite
LLM_DAILY_BUDGET_USD=1.50
LLM_MONTHLY_BUDGET_USD=40
LLM_RPM_GEMINI=60
LLM_RPM_ANTHROPIC=50
EMBEDDINGS_RUNTIME=local                       # local | off
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
GEOAPIFY_API_KEY=...
GEOCODER_FALLBACK=geoapify
EPHE_PATH=./ephe
ASTRO_NODE_VEDIC=mean
ASTRO_NODE_WESTERN=true
ASTRO_DASHA_YEAR_DAYS=365.25
DEFAULT_ANON_TZ=Asia/Kolkata
SENTRY_DSN=                                    # optional, if sentry-sdk approved
VAPID_PUBLIC_KEY= / VAPID_PRIVATE_KEY=         # v1 web push
RAZORPAY_KEY_ID= / RAZORPAY_KEY_SECRET= / RAZORPAY_WEBHOOK_SECRET=   # v1 premium
```

`config.py` refuses to start with `APP_ENV=production` if `JWT_SECRET_KEY`, `CRON_SECRET` or `OTP_PEPPER` is missing or still the example value, or if `GEMINI_API_KEY` belongs to a project without billing. The billing case is checked once at startup with a cheap `models.list` call plus a config flag `GEMINI_PAID_TIER_CONFIRMED=true`.

---

## 10. Observability, testing, deployment

### 10.1 Observability

- **Logs:** JSON to stdout, one line per request: `request_id`, `route`, `status`, `latency_ms`, `user_id_hash` (SHA-256 truncated to 12 chars, never the email), and dependency timings.
  - A **PII scrubber** removes emails, birth dates and times, coordinates, and message content from logs. Message content is never logged.
  - Render keeps logs only briefly, so the weekly digest summarises what matters.
- **Errors:** Sentry free tier, if approved (with PII scrubbing). Otherwise, an ERROR-level log line plus an owner email for `5xx` bursts (more than 10 per 5 min).
- **Uptime:** cron-job.org failure notifications on `/health/live`. Render's health check uses `/health/ready`.
- **Product analytics:** a first-party, minimal `events` table (v1). Events: `signup`, `verify`, `chart_created`, `first_chat`, `daily_open`, `compat_created`, `upgrade`. Fields: user_id, event, ts, props without PII. No third-party trackers in MVP (privacy positioning, DPDP).

### 10.2 Testing (release gates)

| Layer | Tooling | Gate |
|---|---|---|
| Engine golden and property tests | pytest + hypothesis + pytest-benchmark | 100 % pass (`astrology-engine.md` §11) |
| Service unit tests | pytest-asyncio, fakeredis, provider `FakeLLM` | ≥ 80 % line coverage on `services/` and `astro/` |
| API tests | httpx `AsyncClient` against a Postgres service container (CI) | every endpoint in `api-contract.md`: success plus each documented error code |
| Contract tests | `tests/contract/`: JSON fixtures of each response type compared against the key sets and types in `frontend/src/types/index.ts` (a script extracts them) | no missing or renamed keys |
| IDOR suite | parametrised over every resource route | all 404 |
| AI evals | `evals/` | gates in `llm-integration.md` §9 on any prompt, model or retrieval change |
| E2E | Playwright: signup → verify → onboarding → dashboard → chat → compatibility → delete account | green before deploy |
| Security | `pip-audit`, `npm audit --omit=dev`, secret scan (gitleaks) | no high or critical findings |
| Migrations | `alembic upgrade head && alembic downgrade base && alembic upgrade head` on an empty DB in CI | pass |

### 10.3 Deployment

- **Backend:** Render web service (free).
  - Build: `pip install -r requirements.txt`.
  - Start: `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1 --proxy-headers --forwarded-allow-ips='*'`.

  Running migrations at start is acceptable for a single instance. Risk: a failed migration blocks boot, which is the desired fail-safe. Migrations must be backward-compatible with the previous app version (expand → migrate → contract) so a rollback redeploy works.
- **Frontend:** Vercel (`frontend/vercel.json`: SPA rewrite, CSP and cache headers), `VITE_API_URL` set as a Vercel env var. **Superseded deployment details live in `docs/deployment.md`** (backend start command is `bash scripts/start.sh`, which runs migrations under an advisory lock and starts uvicorn with `--no-proxy-headers`; `render.yaml` is the Blueprint).
- **CI:** GitHub Actions on PR runs lint (ruff, eslint), type check (mypy on `astro/` and `services/`; `tsc -b`), tests, migration round-trip and `pip-audit`. Deploys on merge to `main` via the Render auto-deploy hook.
- **Environments:** `development` (local docker-compose with Postgres 16 + pgvector and Redis 7) and `production`. Staging is a Neon **branch** and a second Render service only when needed. There's no permanent staging, because the free-hour budget allows one always-on service.
- **Backups:** Neon's built-in restore window, plus a weekly `pg_dump` from GitHub Actions. The dump is encrypted with `age` to the owner's key and stored as a private release artifact with 90-day retention. A restore drill runs once per quarter.

---

## 11. Scale triggers (when to spend money)

| Signal | Action | Est. cost |
|---|---|---|
| p95 API > 1.5 s, or cold starts complained about | Render Starter instance (always on, 0.5 CPU) | ~$7/mo |
| Neon storage > 350 MB or CU-hours > 80/mo | Neon Launch | ~$19/mo |
| Upstash > 350k commands/mo | Upstash pay-as-you-go | ~$0.20 per 100k |
| LocationIQ > 4k/day | Increase cache TTL, then the LocationIQ paid tier | — |
| Brevo > 250/day | Brevo Starter | ~$9/mo |
| LLM monthly spend > budget for 2 consecutive months | Tighten free quota, or move free chat to Flash-Lite | — |
| > 5k MAU | Second instance, which means moving the rate limiter and L1 caches to Redis, and the circuit breaker to Redis | — |
