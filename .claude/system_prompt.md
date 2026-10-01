# System Prompt - Nakshion (codename Cosmic Intelligence)

Read this first for orientation. `.claude/CLAUDE.md` has the agent/team protocol.

## What this is

An AI-powered astrology app. Users create birth charts (computed with Swiss Ephemeris, Western
tropical and Vedic sidereal), chat with an AI guide grounded in their chart plus a RAG knowledge
base, read daily readings, and run compatibility (synastry) reports. The shipped UI brands it
**Nakshion**. "Cosmic Intelligence" is the internal codename used in `.claude/` docs.

Solo-built, hosted on free tiers: Render (API), Neon (Postgres), Upstash (Redis), Gemini free
tier (LLM, provider under evaluation), LocationIQ (geocoding), Brevo (email). The target
scale is hundreds to low thousands of users. Calibrate engineering to that: rigor on
correctness, security and data safety, no over-engineering for scale that does not exist.

## Current state (verified 2026-10-01)

| Path | State |
|---|---|
| `backend/app/` | **Missing. Being rebuilt from scratch.** No git history to recover from. |
| `backend/alembic/versions/` | `001_initial_schema.py`, `002_add_compatibility_reports.py` exist |
| `backend/alembic/env.py` | Imports `app.database.Base` and `app.models`, so Alembic cannot run until those exist |
| `backend/knowledge_base/*.md` | 26 astrology reference files (RAG source) |
| `backend/data/chroma_db/` | Local vector store (gitignored, rebuildable) |
| `backend/requirements.txt` | Pinned deps. Incomplete versus the venv (missing `sentence-transformers`, `psycopg2-binary`) |
| `backend/scripts/create_db.py` | Local DB bootstrap |
| `frontend/` | React 19 + Vite 8 + TS 5.9 + Tailwind 4. Pages, services, `authStore` exist |
| Ephemeris files | **None installed**: pyswisseph is silently on the Moshier fallback |

Whenever a doc names a backend file under `backend/app/`, it is the **target layout** below
unless you have just verified the file exists.

## Target backend layout

```
backend/app/
  main.py              # app factory, middleware, exception handlers, router includes
  config.py            # pydantic-settings; fail fast on missing secrets
  database.py          # async engine/session (asyncpg), Base
  models/              # SQLAlchemy models, one file per domain, matching the migrations
  schemas/             # Pydantic request/response models
  routers/             # auth, users, charts, chat, horoscopes, compatibility, geocoding
  services/
    astro/             # Swiss Ephemeris: chart, houses, aspects, nakshatra, dasha, transits
    llm/               # provider abstraction (ai_llm_rules.md)
    rag/               # chunking, indexing, retrieval
    auth_service.py, chart_service.py, chat_service.py, horoscope_service.py,
    compatibility_service.py, geocoding_service.py, email_service.py, cache.py, budget.py
  prompts/             # versioned prompt files
backend/tests/         # unit / integration / golden / evals (testing_rules.md)
```

## Frontend layout (exists)

```
frontend/src/
  pages/        Landing, Auth, Onboarding, Dashboard, Chart, Chat, Compatibility, Profile, ...
  components/   ui/ (Button, GlassCard, Input), astrology/, chat/, landing/, layout/, auth/
  services/     api.ts (axios instance) + auth, charts, chat, compatibility, geocoding, horoscope, user
  hooks/, store/ (authStore - Zustand), types/, lib/utils.ts
```

## Data model (from `alembic/versions/001`, `002`)

`users` (email + password or OAuth; `password_hash` nullable; `subscription_tier` free/paid;
`timezone`) owns `birth_charts` (many per user, `is_primary`, `has_exact_time`,
`time_of_birth` nullable, `latitude`/`longitude`/`timezone`, `chart_data` JSONB). Charts are
used by `conversations` (`chart_id` nullable, **no ON DELETE rule**), which own `messages`
(`role`, `content`, `metadata` JSONB, `tokens_used`). Also `password_resets` (single-use,
expiring), `daily_horoscopes` (unique `(zodiac_sign, date)`), and `compatibility_reports`
(user, chart1, chart2, `overall_score`, `compatibility_data`).

## Rule files (all mandatory, see CLAUDE.md for the reading order)

`coding_rules_backend.md`, `coding_rules_frontend.md`, `database_rules.md`,
`caching_rules.md`, `security_rules.md`, `ai_llm_rules.md`,
`astrology_accuracy_rules.md`, `testing_rules.md`, plus
`.claude/knowledge/Astrology/PITFALLS.md` and `BUG_LEDGER.md`.
