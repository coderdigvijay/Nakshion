# Nakshion: Backend

FastAPI + SQLAlchemy 2 (async) + Postgres/pgvector + Redis. Specs live in `../docs/`
(`api-contract.md` is the HTTP contract; `architecture.md` covers layout, migrations, caching and rate limits).

## Layout

```
app/
  main.py            app factory: middleware, exception handlers, routers, lifespan
  core/              config, security (bcrypt/JWT), errors (single handler module), deps, ratelimit, logging, middleware
  db/                async engine/session, Base          (app/database.py is a shim for alembic/env.py)
  models/            ORM, one file per domain (messages.metadata is mapped as `meta`)
  schemas/           Pydantic request (extra="forbid") / response models
  routers/           validate -> delegate -> respond
  services/          business logic; engine.py and ai.py are the ONLY adapters to app/astrology and app/llm
  astrology/         pure calculation engine            (owned by astrology-domain-expert)
  llm/, rag/         LLM provider layer, prompts, RAG   (owned by ai-genai-specialist)
alembic/versions/    001-006 (hand-numbered, idempotent, reversible)
tests/               api/ unit/ (backend-elite), astrology/ (engine), llm/ (AI)
```

## Setup (local)

Requires Python 3.14, Postgres 16+ with the **pgvector** extension available, and Redis.

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env               # fill in values (see below)
python scripts/create_db.py        # or: createdb astroai
alembic upgrade head               # 001 -> 006
python -m app.rag.ingest --database-url "$DATABASE_URL"   # index knowledge_base/ into pgvector (~2-3 min)
uvicorn app.main:app --reload --port 8010   # dev API port; frontend dev port 5175
```

Env vars you must set for full functionality: `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET_KEY`,
`GEMINI_API_KEY` (or `GEMINI_API_KEY1..5`), `LOCATIONIQ_API_KEY`, `BREVO_API_KEY` plus
`EMAIL_SENDER_ADDRESS` (a Brevo-verified sender), and `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET`
with `API_PUBLIC_URL` (the OAuth redirect is `${API_PUBLIC_URL}/api/v1/auth/oauth/google/callback`).
Dev defaults: API `http://localhost:8010`, frontend `http://localhost:5175` (`API_PUBLIC_URL`, `FRONTEND_URL`, `CORS_ORIGINS`).
Register `http://localhost:8010/api/v1/auth/oauth/google/callback` as an authorised redirect URI in the Google console.
Optional: `ANTHROPIC_API_KEY` (LLM fallback), `GEOAPIFY_API_KEY` (geocoder fallback), `CRON_SECRET`.
Production refuses to boot with weak `JWT_SECRET_KEY` / `CRON_SECRET` / `OTP_PEPPER`.

**Brevo:** if the account has "Authorised IPs" enabled, API calls from an unlisted IP return
401 `unauthorized`. Render's egress IPs are not fixed, so disable the IP restriction (or allow-list
the IPs) before deploying.

## Tests

```bash
pytest -q                          # uses <dev db>_test on localhost (refuses non-local URLs)
TEST_DATABASE_URL=postgresql+asyncpg://.../mydb_test pytest -q tests/api
```

Tests use fakeredis, a fake LLM module injected at `services/ai.py`, captured email, and respx
for LocationIQ/Geoapify. The real astrology engine is used (pure CPU).

## Deploy (Render)

Start command: `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1 --no-proxy-headers`
with env `TRUSTED_PROXY_HOPS=1`. Do **not** use `--proxy-headers --forwarded-allow-ips='*'`: uvicorn then takes the
client-forgeable left-most `X-Forwarded-For` entry. The app derives the client IP itself (`app/core/clientip.py`) from the
right-most trusted hop, which keeps per-IP rate limits and login lockouts per real client.
Neon: set `DATABASE_URL` to the pooled URL (`sslmode`/`channel_binding` params are handled) and `MIGRATION_DATABASE_URL`
to the direct URL for `alembic upgrade head`. Brevo, Redis and DB timeouts are documented in `docs/architecture.md`.
Keep-awake pinger: `GET /health/live` (touches neither Postgres nor Redis). Render health check: `GET /health/ready`.
Cron (cron-job.org): `POST /internal/cron/{pregen_horoscopes|hourly}` with header `X-Cron-Secret`.

## API (all under `/api/v1`; both `/charts` and `/charts/` work without a redirect)

| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | /auth/register | - | 201 token; 409 EMAIL_EXISTS; 5/h/IP |
| POST | /auth/login | - | 400 INVALID_CREDENTIALS (never 401); brute-force limited |
| POST | /auth/verify-email, /auth/resend-otp | Bearer | 6-digit OTP, 5 attempts, resend 1/min 5/day |
| POST | /auth/forgot-password, /auth/reset-password | - | always 200; single-use hashed token; reset revokes sessions |
| GET | /auth/me, /users/me | Bearer | `User` (+ has_password, quota) |
| GET | /auth/oauth/google, /auth/oauth/google/callback | - | state + PKCE; 302 to `${FRONTEND_URL}/auth/callback?token=` |
| POST | /auth/change-password, /auth/set-password, /auth/logout-all | Bearer | |
| PUT/DELETE | /users/me ; PUT /users/me/consents ; POST /users/me/deletion-code | Bearer | DELETE needs `{password}` or `{code}` (re-auth); cascades + purges cache |
| POST | /auth/oauth/exchange | - | trades the one-time `?code=` from the OAuth redirect for a token |
| GET | /charts/{id}/transits ; /charts/{id}/dasha ; /panchang | Bearer ; Bearer ; - | engine data, no LLM |
| POST/GET | /charts | Bearer | tz resolved server-side; list = primary first |
| GET/PUT/DELETE | /charts/{id} ; POST /charts/{id}/primary | Bearer | 404 if not yours |
| POST/GET | /chat/conversations ; GET/PATCH/DELETE /chat/conversations/{id} | Bearer | |
| POST | /chat/conversations/{id}/messages | Bearer | returns exactly [user, assistant] |
| POST | /chat/conversations/{id}/messages/stream | Bearer | SSE: meta, delta*, replace?, done or error |
| PUT/POST | /chat/messages/{id}/bookmark, /chat/messages/{id}/feedback ; GET /chat/suggestions | Bearer | |
| POST/GET | /compatibility ; GET/DELETE /compatibility/{id} | Bearer | 201 new, 200 reused (30-day dedupe) |
| GET | /horoscopes/daily?sign= ; /horoscopes/daily/{date}?sign= | optional | cached per sign/date/system |
| GET | /horoscopes/personal/today | Bearer | R3 (needs engine `personal_day`) |
| GET | /geocoding/search?q= | Bearer | `{results, degraded}` |
| GET | /health, /health/live, /health/ready | - | also outside /api/v1 |
