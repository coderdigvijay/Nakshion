# Nakshion deployment runbook

**Targets:** backend on **Render** (free web service) · frontend on **Vercel** · Postgres on **Neon** · Redis on **Upstash**.
**Status:** every file referenced here exists locally and was exercised against a local Postgres, Redis and `uvicorn`.
**Nothing has been deployed.** Section 14 lists what could only be checked in the real cloud.

Files: `render.yaml` (backend Blueprint), `frontend/vercel.json`, `backend/scripts/start.sh`,
`backend/scripts/build_check.py`, `.github/workflows/ci.yml`, `scripts/smoke_prod.sh`.

## 1. Shape of the system

```
Browser ──https──> Vercel (static React SPA, CSP/headers from vercel.json)
   │  JWT bearer in `Authorization` (no cookies, so nothing depends on same-site)
   └──https──> Render web service `nakshion-api` ──> Neon Postgres (pgvector)   [pooled URL for the app, direct URL for migrations]
                      │                       └────> Upstash Redis (TLS)        [caches, OTP, locks, counters]
                      └──> Gemini / Anthropic / LocationIQ / Geoapify / Brevo / Google OAuth
cron-job.org ──> GET /health/live (every 14 min)   POST /internal/cron/{pregen_horoscopes,daily_maintenance} (daily, X-Cron-Secret)
```

The frontend and API are different origins, so the API sends CORS headers for **exact** frontend origins only.

## 2. Free-tier limits that shape the design (verified 2026-10-01)

| Service | Limit | What happens at the limit | Plan B |
|---|---|---|---|
| Render web (free) | 0.1 vCPU, **512 MB RAM**, 750 instance-hours / month / workspace, spins down after 15 min idle (~1 min spin-up), ephemeral disk | OOM kill and restart; after the hours run out the service is suspended until next month | Starter ($7/mo, always on, 512 MB then 2 GB tiers) |
| Neon (free) | 0.5 GB storage, **100 CU-hours / month**, compute scales to zero after 5 idle minutes (cannot be disabled), 6 h restore window | compute is suspended until the next period: API answers 503 "database is waking up" | Neon Launch (~$19/mo) |
| Upstash Redis (free) | **500K commands / month** (~16K/day), 256 MB, 10 MB max request | commands rejected: OTP/OAuth/login throttling return 503 (fail closed); caches simply miss | Render Key Value (free) or pay-as-you-go (~$0.20 / 100K) |
| Vercel Hobby | non-commercial use only | n/a | see section 12 |
| Brevo (free) | 300 emails / day | OTP / reset emails stop | Brevo Starter |
| LocationIQ (free) | 5K requests / day, 2 req/s | geocoder falls back to Geoapify, then `degraded` | paid tier |
| Gemini | pay-as-you-go | `LLM_DAILY_BUDGET_USD` guard degrades to templates | raise the budget |

**One always-on free service is the maximum** (744 h in a 31-day month fits in 750 h; a second free service would not).

## 3. Memory budget (512 MB) — measured

Measured with the project venv on macOS x86_64 / Python 3.14 (Linux will differ; **re-measure on Render**):

| State | RSS |
|---|---|
| Python alone | 16 MB |
| `import app.main` (all dependencies) | ~113 MB |
| server idle, embeddings off | **157 MB** |
| after chart creation | 177 MB |
| after first chat with `EMBEDDINGS_RUNTIME=off` (full-text + pre-embedded keys retrieval) | **182 MB** |
| after first chat with `EMBEDDINGS_RUNTIME=local` (bge-small ONNX model loaded) | **422 MB peak** |
| `import app.main` + local embedder `minilm-l6-q` (23 MB int8) after 200 queries, macOS arm64 | **245 MB peak** (BUG-028; adds ~25 MB for the first chat, so about 270 MB expected) |
| same with `arctic-xs` / `minilm-l6` (90 MB fp32) | 350 MB peak |
| same with `bge-small` (66 MB int8, current default) | 416 MB peak |
| same with multilingual-e5-small / paraphrase-multilingual-MiniLM | 730 / 880 MB peak (do not fit) |

The RAG agent measured ~396 MB with the model on macOS arm64. Linux x86 usually reports a bit less, but ONNX runtime arenas and
request spikes on a 0.1 vCPU box make 420 MB too close to 512 MB for a free instance, so **`render.yaml` defaults to
`EMBEDDINGS_RUNTIME=off`** (retrieval hit@5 0.907 vs 0.956, a 5-point quality cost; see `docs/rag-runbook.md`).

Update (BUG-028): `minilm-l6-q` is the one local model that fits 512 MB on paper (245 MB peak measured on macOS arm64; **Linux and the 0.1 vCPU Render box are not measured**, so treat 245 MB as an estimate with an unknown but probably favourable Linux offset and expect load and inference to be several times slower than on a laptop). It is now the `render.yaml` default (fresh blind Hindi/Hinglish hit@5 0.70 to 0.81, runbook section 2e); the Neon index must be re-ingested with it BEFORE deploying. Procedure: `python -m app.rag.ingest --model minilm-l6-q --force`, then set `EMBEDDING_MODEL=minilm-l6-q` and `EMBEDDINGS_RUNTIME=local`. The model loads lazily in a background thread after the first retrieval, so boot and `/health/live` are unaffected, and a load failure or a query over `EMBED_QUERY_TIMEOUT_S` (0.4 s) falls back to keys + full-text for that request.

Switch: set `EMBEDDINGS_RUNTIME=local` in the Render dashboard on a plan with 1 GB+ RAM. The build then pre-downloads the model
into `backend/.fastembed_cache` (`scripts/build_check.py`, `FASTEMBED_CACHE_PATH`), so it is **never downloaded at boot** (ephemeral disk).

Other memory rules already in place: one uvicorn worker, no `--reload`, DB pool 3 + 2 overflow, single-thread ephemeris executor,
no chromadb, no torch.

## 4. Boot time and keep-alive

* Local: process start to first `/health/live` = **1.7 s**, plus a one-off ~0.8 s the first time the embedding model loads.
  On Render's 0.1 vCPU expect several times slower (estimate 10-25 s: imports + `alembic upgrade head` + ephemeris self-check). **Unmeasured on Render.**
* When the service is asleep, the first request waits for Render's spin-up (~1 min) plus boot. Browsers should show a loading state; the pinger below avoids it.
* **Keep-alive plan:** cron-job.org `GET https://<api>/health/live` every **14 minutes** (Render idles out at 15). That is ~744 instance-hours/month, inside the
  750-hour allowance only because this is the workspace's single free web service.
* `/health/live` touches neither Postgres nor Redis (covered by `test_health_live_never_touches_db_or_redis`), so pinging does not wake Neon.
  `healthCheckPath` in `render.yaml` is also `/health/live`. `/health/ready` checks DB + Redis + engine (result cached 5 s, 10 requests/min per client). Its public body is only `{"status":"ok"|"degraded"}`; send `X-Cron-Secret` to see the per-dependency detail. `/health/live` shows the 7-character deploy commit (`RENDER_GIT_COMMIT`).

## 5. Migrations on Render free (no pre-deploy command)

**Chosen design:** `backend/scripts/start.sh` runs `alembic upgrade head` and then `exec uvicorn ...`.

* `alembic/env.py` uses `MIGRATION_DATABASE_URL` (Neon's **direct** endpoint) when set, so DDL never goes through pgbouncer.
* It holds a Postgres **advisory lock** (key 727274) for the whole upgrade. Render overlaps the old and new instance during a deploy; if both start together the second waits, then finds nothing to do (tested with two concurrent `alembic upgrade head` runs).
* A failed migration exits non-zero, so the new instance never becomes healthy and **Render keeps the previous version serving** (fail-safe).
* Rule for every migration: backward compatible with the previous app version (expand, migrate, contract), idempotent, with a real `downgrade()`.
* Why not a separate job: Render free has no pre-deploy command and no free cron job, so a one-off job would be a manual step people forget. The cost is a few seconds of boot time on each deploy.
* Manual escape hatch (from your laptop): `MIGRATION_DATABASE_URL=... alembic upgrade head` / `alembic downgrade -1`.

## 6. Production configuration guard

With `APP_ENV=production`, `app/core/config.py` **refuses to start** (listing the setting names, never the values) if:
`JWT_SECRET_KEY`, `CRON_SECRET` or `OTP_PEPPER` is missing, an example value, shorter than 32 characters, or two of them are equal ·
`DATABASE_URL` is localhost or lacks `sslmode=require` · `REDIS_URL` is localhost or not `rediss://` (unless `REDIS_ALLOW_PLAINTEXT=true`, only for Render's private Key Value) ·
`CORS_ORIGINS` contains `*`, `http://`, localhost or a path · `FRONTEND_URL` / `API_PUBLIC_URL` are not public https URLs · rate limiting is disabled.
API docs (`/docs`, `/openapi.json`) are off in production. Validation errors never echo input values (a bug found while writing this: BUG-015).

Connection notes:
* **Neon:** use the *pooled* host (`...-pooler...`) in `DATABASE_URL` with `?sslmode=require&channel_binding=require`. The app strips the libpq-only parameters for asyncpg, enables TLS, and turns off prepared statements (pgbouncer transaction mode). Use the *direct* host in `MIGRATION_DATABASE_URL`.
* **Upstash:** copy the `rediss://default:<password>@<host>:6379` URL (TLS). Pick the same region as Render.

## 6a. Client IP and abuse limits (read this before the first deploy)

**What Render sends is not yet known.** A live test suggested the right-most `X-Forwarded-For` entry can be client-supplied. Until verified, assume it is, and rely on three layers:

1. **Fail-closed derivation** (`backend/app/core/clientip.py`). With `TRUSTED_PROXY_HOPS=N` the client is the Nth entry from the *right* of `X-Forwarded-For`; if the header is shorter than N or malformed the client is **"unknown"**, never the socket peer (that is the proxy). "unknown" is one shared bucket with *half* the normal limit on auth routes (and 5x on the global limit) so a bypass attempt degrades to strict limits instead of disabling them. `CLIENT_IP_HEADER` (below) is the better option when available. Production refuses to boot with neither `TRUSTED_PROXY_HOPS>=1` nor `CLIENT_IP_HEADER`.
2. **IP-independent backstops:** 10 failed logins per **email** per 15 minutes from any IP (then 429 with `Retry-After`, generic copy; the window is short so an attacker can lock a victim out for at most 15 minutes, and success clears it); per-email limits on forgot-password and OTP resend; a global **200 emails/hour** cap on OTP/reset/deletion emails (protects Brevo's 300/day free quota; password-reset requests over the cap are dropped silently with the usual 200 answer).
3. **Diagnostic:** `LOG_CLIENT_IP_DEBUG=1` (set in `render.yaml` for the first deploy) logs one `client_ip_shape` line for each of the first 20 requests: number of `X-Forwarded-For` entries, whether each is public/private/loopback, which of `x-real-ip`, `true-client-ip`, `cf-connecting-ip`, `x-forwarded-proto`, `forwarded` are present, whether the peer is private, and every address masked to /24 (IPv4) or /48 (IPv6). No full address is logged.

**How to decide once you have read the logs** (Render dashboard > Logs, filter `client_ip_shape`; send one request from your phone and one from your laptop, with and without a forged `X-Forwarded-For: 1.2.3.4` header):

| What the log shows | Setting |
|---|---|
| A forged value appears as the **right-most** entry, or the real client is not the last entry | the right side is attacker-controlled: do **not** rely on XFF. Put Cloudflare (or similar) in front and use its header, see next row |
| A single header carries the real client (`true-client-ip` or `cf-connecting-ip`) and it is not forgeable | `CLIENT_IP_HEADER=true-client-ip` (or `cf-connecting-ip`); XFF is then ignored |
| The real client is always the **last** XFF entry and a forged left entry stays to the left of it | keep `TRUSTED_PROXY_HOPS=1` |
| Two proxies (CDN + Render) append, real client second from the right | `TRUSTED_PROXY_HOPS=2` |
| Nothing useful (`derived_is_unknown: true` for all requests) | per-IP limits cannot be trusted; every client shares the strict "unknown" bucket. The per-email and global backstops still protect accounts and Brevo; consider a paid plan or a CDN in front |

After deciding, delete `LOG_CLIENT_IP_DEBUG` and re-run the smoke test. Never enable `uvicorn --proxy-headers`.

## 7. Upstash command budget (500K / month) — measured per route

Counted with `INFO stats` deltas on a throwaway local Redis while calling each route once (embeddings off):

| Route | Redis commands |
|---|---|
| `/health/live` | 0 |
| `GET /auth/me`, `GET /charts`, any authenticated read | 0 |
| `POST /auth/login` success / wrong password | 1 / 5 |
| `POST /auth/register` (issues the OTP) | 6 |
| `POST /charts` (first, primary) / `PUT /charts/{id}` | 1 / 2 |
| `GET /horoscopes/daily` cold / warm (in-process cache) | 2 / 0 |
| `GET /panchang` cold / warm | 2 / 1 |
| `GET /geocoding/search` cold / warm | 2 / 1 |
| `GET /horoscopes/personal/today` cold / warm | 17 / 1 |
| `POST /chat/.../messages` (lock + LLM budget counters) | 12-22 |

Reductions already made: `MGET` for login counters, plain 2-command pipelines for counters (was 4), no `DEL` on a clean login, one `SCAN` pattern instead of five on chart edits, health/static routes never touch Redis, in-process cache for horoscopes.

**Estimate (assumes each DAU opens the dashboard once, 30% chat 3 times, 0.3 logins/day):** about 36 commands per DAU-day, i.e.
300 DAU ~ 10.8K/day ~ **325K/month (65%)**, 500 DAU ~ 18K/day ~ **540K/month (over)**. The LLM budget counters are ~10 commands per LLM call, the largest share.

Levers, in order: (1) `LLM_BUDGET_COUNTERS=memory` (counters in-process; cuts the per-DAU figure to ~13, i.e. 500 DAU ~ 195K/month; the daily spend guard then resets on restart, so keep a Google Cloud billing alert); (2) Render **Key Value (free)** for everything: set `REDIS_URL` to its internal URL plus `REDIS_ALLOW_PLAINTEXT=true`; it has no persistence, so pending OTPs and caches vanish on restart (users re-request a code); (3) Upstash pay-as-you-go.
Watch the Upstash dashboard; alert at 70%.

## 8. Neon compute budget (100 CU-hours / month)

* Compute stays awake **5 minutes after the last query**; a session of *m* minutes keeps it up ~*m*+5. At the free plan's smallest size (0.25 CU) 100 CU-hours is ~400 awake hours/month ~ **13 h/day**; if Neon scales the compute up under load, the same budget shrinks proportionally.
* **Rough break point:** ~65 well-spread sessions/day keep the DB awake 13 h/day; traffic concentrated in the evening stretches that to a few hundred DAU. Treat **~150-300 DAU** as the ceiling for the free plan. **Symptom at the limit:** compute is suspended, every DB-backed request returns **503 `DEPENDENCY_UNAVAILABLE` "The database is waking up"** until the next period (health/live and public cached endpoints like Panchang keep working).
* Already done: `/health/*` never touches the DB; cron maintenance runs **once a day** (`daily_maintenance`, alias `hourly` kept), not hourly; daily horoscope, Panchang, transits and geocoding are served from Redis/in-process caches without the DB; the first query after idle has a 10 s connect timeout and a clear 503 + `Retry-After: 5` instead of a 500.
* Not done on purpose: caching the authenticated user lookup (it would delay token revocation / account deletion by the cache TTL).
* Monitor: Neon console > Usage (CU-hours) weekly; alert at 80 CU-hours. Upgrade trigger: > 70% of CU-hours or storage > 350 MB.

## 9. Environment variables

Set in the Render dashboard (secrets are `sync: false` in `render.yaml` and prompted on Blueprint creation).

| Variable | Required | Where to get it / value |
|---|---|---|
| `APP_ENV` | yes | `production` (in render.yaml) |
| `JWT_SECRET_KEY`, `OTP_PEPPER`, `CRON_SECRET` | yes | Render generates them (`generateValue`); read `CRON_SECRET` in the dashboard for cron-job.org |
| `DATABASE_URL` | yes | Neon > Connection details > **Pooled** string, append `?sslmode=require` |
| `MIGRATION_DATABASE_URL` | yes | Neon > Connection details > **Direct** (unpooled) string |
| `REDIS_URL` | yes | Upstash > Redis > Details > `rediss://` URL |
| `API_PUBLIC_URL` | yes | `https://<service>.onrender.com` (no trailing slash) |
| `FRONTEND_URL` | yes | your Vercel production URL or custom domain |
| `CORS_ORIGINS` | yes | same exact origin(s), comma separated, https only |
| `TRUSTED_PROXY_HOPS` / `CLIENT_IP_HEADER` | yes (one of them) | `1` until the logs say otherwise; see section 6a |
| `LOG_CLIENT_IP_DEBUG` | temporary | `1` for the first deploy only (section 6a) |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | set | `2880` (2 days; there is no refresh flow yet, so users sign in again every 2 days) |
| `TERMS_VERSION` | set | `2026-10-01`; recorded with each acceptance, bump when Terms/Privacy change |
| `GEMINI_API_KEY` | yes | Google AI Studio, on a **billing-enabled** project (the free tier may train on prompts) |
| `ANTHROPIC_API_KEY` | optional | console.anthropic.com (fallback provider) |
| `LOCATIONIQ_API_KEY` | yes | locationiq.com dashboard (show "Search by LocationIQ.com" in the UI) |
| `GEOAPIFY_API_KEY` | optional | geoapify.com (fallback geocoder) |
| `BREVO_API_KEY`, `EMAIL_SENDER_ADDRESS` | yes | Brevo > SMTP & API > API keys; sender must be verified |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | yes | Google Cloud console > Credentials (OAuth client, Web) |
| `LLM_DAILY_BUDGET_USD`, `LLM_MONTHLY_BUDGET_USD` | yes | `1.50` and `40` (see section 11) |
| `RAG_EXCLUDE_REVIEW` | yes | `0` (default): index every knowledge file. Set `1` only if you ever need to hide the tier-3 notes by in-copyright authors (public or commercial use). |
| `EMBEDDINGS_RUNTIME` | yes | `off` on the free plan (section 3), `local` with 1 GB+ RAM |
| `LLM_BUDGET_COUNTERS` | optional | `redis` (default) or `memory` (section 7) |
| `SOURCE_CODE_URL` | licence | public repo URL; shown in `/health/live` (AGPL, section 13) |
| `DB_POOL_SIZE`, `DB_MAX_OVERFLOW` | set | `3` and `2` |
| `PYTHON_VERSION` | set | `3.14.3` (unverified on Render, section 14) |

Vercel (project settings > Environment Variables, Production): `VITE_API_URL=https://<service>.onrender.com/api/v1`. Nothing secret belongs in `VITE_*`.

## 10. Step-by-step first deploy

Order matters: the backend refuses to boot until it knows the frontend's https origin, so create the Vercel project first.

1. **Neon:** create a project in the region nearest your users (Singapore for India), same region as Render. In the SQL editor run `CREATE EXTENSION IF NOT EXISTS vector;` (migration 004 also does it). Copy the pooled and direct connection strings.
2. **Upstash:** create a Redis database in the same region, TLS on, eviction off. Copy the `rediss://` URL.
3. **Git:** push the repo to GitHub (see the licence note in section 13 before choosing public/private). CI (`.github/workflows/ci.yml`) must be green; Render deploys on `checksPass`.
4. **Vercel:** Import the repo, **Root Directory = `frontend`**, framework preset Vite (taken from `vercel.json`: `npm ci`, `npm run build`, output `dist`). Add `VITE_API_URL`. Note the production URL (or attach your custom domain first). If your Render service name is not `nakshion-api`, edit the API origin in `frontend/vercel.json` `connect-src` before the first build.
5. **Render:** New > Blueprint, point at the repo, review `render.yaml` (service name, region `singapore`), fill the `sync: false` secrets. First deploy: the build runs `build_check.py` (ephemeris files present, single Alembic head, optional model bake) and the start script migrates then boots.
6. **Knowledge base index** (once, and whenever `knowledge_base/` changes), from your machine with the project venv:
   `EMBEDDINGS_RUNTIME=local python -m app.rag.ingest --database-url "$MIGRATION_DATABASE_URL"` (about 2-3 minutes; it embeds locally and writes a new `index_version`). Then check `GET /health/ready` shows `"rag":{"ok":true,...}`.
7. **Google OAuth** (Cloud console > OAuth client): Authorised redirect URI `https://<service>.onrender.com/api/v1/auth/oauth/google/callback` (keep the localhost one for dev). The callback stays on the API; after login the API redirects the browser to `FRONTEND_URL/auth/callback?code=...`, which the SPA trades via `POST /auth/oauth/exchange`. Publish the consent screen (or add test users).
8. **Brevo:** verify the sender address/domain. **Turn off "Authorised IPs"** (Security > Authorised IPs): Render's egress IPs are shared and change, so an allow-list yields `401 unauthorized` (logged as `email_send_failed brevo_code=unauthorized`). If you must keep it, allow Render's published outbound ranges for your region.
9. **cron-job.org** (timeout 60 s; Render may need a minute to wake):
   * `GET https://<api>/health/live` every 14 minutes (keep-awake).
   * `POST https://<api>/internal/cron/pregen_horoscopes` daily 18:00 UTC with header `X-Cron-Secret: <CRON_SECRET>`. It answers `{"status":"started"}` immediately and generates the 24 horoscopes in the background, so cron-job.org's 30 s timeout is not a problem.
   * `POST https://<api>/internal/cron/daily_maintenance` daily 22:00 UTC, same header (purges expired resets, old readings and LLM/usage rows). **Do not run it hourly** (it wakes Neon).
10. **Smoke test:** `BASE_URL=https://<api> FRONTEND_ORIGIN=https://<frontend> EXPECT_PROD=1 scripts/smoke_prod.sh` (no secrets, mutates nothing).
11. **By hand once:** register, verify the emailed code, create a chart, ask one chat question, sign in with Google, delete the test account.

### First-deploy checklist
- [ ] Neon pgvector extension on; pooled and direct URLs saved
- [ ] Upstash `rediss://` URL saved
- [ ] Render boot log shows `alembic ... Running upgrade` then `engine_self_test ok`, no `Refusing production boot`
- [ ] `/health/ready` is 200 with database, redis, engine true and `rag.ok` true
- [ ] `smoke_prod.sh` prints `failed=0`
- [ ] KB ingested (all files; `RAG_EXCLUDE_REVIEW=0`)
- [ ] Brevo OTP email arrives; Google sign-in lands on the app
- [ ] cron-job.org jobs show 200
- [ ] Billing alerts: Google Cloud (Gemini), Neon CU-hours, Upstash commands

## 11. Cost ceiling and LLM budget guard

Infrastructure is $0 on the free tiers (until a limit above is hit). LLM spend is the only variable cost:
`LLM_DAILY_BUDGET_USD=1.50` / `LLM_MONTHLY_BUDGET_USD=40`. At 80% the app logs an alert; at 100% free chat drops to cheaper models and daily readings/compatibility use templates; at 150% chat answers 503 "Nakshion is resting" (`llm-integration.md` 7.2). Set an independent billing budget and alert in Google Cloud: the guard is application-level, so a bug or restart (with `LLM_BUDGET_COUNTERS=memory`) must not be the only line of defence.

## 12. Domain, HTTPS, CORS and Vercel licensing

* TLS is automatic on Render and Vercel. `vercel.json` sets HSTS, a strict CSP (script hash for the one inline theme script, Google Fonts, API origin in `connect-src`), `X-Frame-Options: DENY`, long immutable cache for `/assets/*` and `no-cache` for `index.html`. **If `frontend/index.html`'s inline script changes, recompute its `sha256-...` hash in the CSP.**
* Custom domains: add the domain in Vercel, then update `FRONTEND_URL` and `CORS_ORIGINS` on Render (both domains while migrating) and redeploy.
* **Preview deployments:** CORS uses exact origins only (no `*.vercel.app` wildcard: anyone can create a `*.vercel.app` project, which would let a hostile page call the API with a user's token). To test a preview, add that one preview origin to `CORS_ORIGINS` temporarily, or use a stable alias (`<project>-git-<branch>-<team>.vercel.app`), then remove it.
* No cookies are used (bearer token in `Authorization`), so nothing relies on same-site; OAuth completes via a one-time `?code=` and `POST /auth/oauth/exchange`.
* **Vercel Hobby is for non-commercial use only.** A product with a paid Premium tier needs **Vercel Pro** (per-seat, ~$20/mo) or a static host that allows commercial use on its free plan. Recommendation: stay on Hobby only while the product is a free beta; before charging anyone, move the static frontend to **Cloudflare Pages** (free, commercial use allowed, unlimited bandwidth; replace `vercel.json` with `_headers` and `_redirects` files carrying the same CSP/cache/rewrite rules) or buy Vercel Pro. The backend does not care which one hosts the SPA.

## 13. Licence note

`pyswisseph` and the Swiss Ephemeris are dual-licensed AGPL-3.0 / Swiss Ephemeris Professional License. The three ephemeris data files (`backend/app/astrology/ephe/*.se1`, ~1.9 MB) **must ship with the deploy and are deliberately not git-ignored**; `build_check.py` fails the build if they are missing or if pyswisseph would fall back to the lower-accuracy Moshier mode. Running a public network service on AGPL code means offering users the complete source: publish the repo and set `SOURCE_CODE_URL`, or buy the professional licence (CHF 750) before launching Premium (`astrology-engine.md` 1.1, PRD OQ-1).

## 14. Operations

**Monitoring (what to watch):** Render logs (JSON, one line per request; retained briefly) for `database_unavailable`, `rag_self_check_failed`, `email_send_failed` (check `brevo_code`), `llm_unavailable`, `chat_deadline_exceeded`, 5xx counts; Neon CU-hours and storage; Upstash daily commands; Gemini spend; cron-job.org failure e-mails. Sentry (free tier) is a **proposal only**, not installed; add it only after you approve the dependency.

**Rollback:**
* Backend: Render dashboard > Events/Deploys > roll back to the previous deploy (seconds). Migrations are forward-only in production: because every migration is backward compatible, the old code runs on the new schema. If a migration itself is bad, restore from backup (below) or run `alembic downgrade -1` with the direct URL.
* Frontend: Vercel > Deployments > **Instant Rollback** to a previous production deployment.

**Backups:** Neon free keeps only a **6-hour** restore window, which is not a backup. Take a weekly logical dump yourself: `pg_dump "$MIGRATION_DATABASE_URL" --format=custom --no-owner -f nakshion-$(date +%F).dump`, encrypt it (`age`) and store it off-site; test a restore into a scratch Neon branch quarterly. (An automated GitHub Actions job is proposed in `architecture.md` 10.3 but not created.)

**Scale-up points and what users see:**

| Limit hit | User-visible symptom | Fix |
|---|---|---|
| Render 512 MB | random 502/restarts during chat (only with `EMBEDDINGS_RUNTIME=local`) | keep `off`, or Starter plan |
| Render 750 h | service suspended until next month | Starter plan |
| Neon CU-hours | 503 "database is waking up" on every DB route | Neon Launch |
| Neon 0.5 GB | writes fail (503/500) | Neon Launch, prune `llm_usage`/readings |
| Upstash 500K | OTP/login/OAuth 503, slower pages | `LLM_BUDGET_COUNTERS=memory`, Key Value, pay-as-you-go |
| Brevo 300/day | verification emails missing | Brevo Starter |
| Gemini budget | "Simplified reading" templates, then chat 503 | raise budget |

## 15. Not verified locally (needs the real cloud)

Render accepting `PYTHON_VERSION=3.14.3` and the `autoDeployTrigger: checksPass` key; Linux RSS and real boot time on 0.1 vCPU; first-request latency after a Neon scale-to-zero; Upstash TLS (`rediss://`) connectivity; Render `bash scripts/start.sh` under their runtime; the cron-job.org to Render wake-up round trip; the CSP in a real browser against the deployed frontend; Google OAuth with production redirect URIs; Brevo delivery with the IP restriction removed; GitHub Actions (the YAML parses; the steps were run locally, not on GitHub); `pip-audit` / `npm audit` results.

## 16. Security and privacy notes (live assessment follow-ups)

* **Sessions:** access tokens last 2 days. `change-password` and `reset-password` bump `token_version`, which revokes every other session (a stolen token dies); `change-password` returns a fresh token so the user stays signed in. `POST /auth/logout-all` revokes everything. **Single-session logout is not implemented:** it needs a per-request Redis denylist lookup (one extra Upstash command per authenticated request); the client simply drops its token.
* **Dependencies:** `pydantic-settings==2.15.0` (the advisory needs >= 2.14.2). Re-run `pip-audit -r backend/requirements.txt` before each release (CI runs it, informational).
* **Terms/Privacy:** password sign-up requires `terms_accepted: true`; Google sign-up requires `?terms=1` for a new account (the SPA shows the checkbox first). Stored as `users.terms_accepted_at` + `users.terms_version`.
* **Deletion log:** `deletion_log` has exactly three columns: `id`, `user_id_sha256` (SHA-256 of the random user UUID) and `deleted_at`. No email, name or birth data.
* **What is sent to Gemini/Anthropic** (chat): the question and the last 6 turns of that conversation (free text typed by the user); a "CHART FACTS" block with computed placements (signs, nakshatra, current dasha and transit labels, house numbers, whether birth time is known), the preferred system and language, today's date; and retrieved reference notes. **Not sent:** email, user id (only a 12-character hash in logs/usage rows, never in the request), the chart name (a constant "the user" is sent; the chart label is often a real person's name), birth date, birth time, birthplace, coordinates, timezone. Daily and compatibility readings send only computed factors and scores. Free text the user types can of course contain anything; the safety layer handles crisis phrases only.
