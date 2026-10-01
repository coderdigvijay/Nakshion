# Backend Coding Rules - FastAPI / Service Layer

Stack (verify against `backend/requirements.txt`): FastAPI 0.115, SQLAlchemy 2.0 async +
asyncpg, Alembic, redis[hiredis], python-jose, bcrypt, pydantic 2 + pydantic-settings, httpx,
pyswisseph, timezonefinder, chromadb, google-generativeai (behind the LLM adapter only).

`backend/app/` is being rebuilt. Paths below are the **target layout** (`system_prompt.md`).

## 1. Layering (non-negotiable)

| Layer | Does | Must not |
|---|---|---|
| `routers/` | parse/validate (Pydantic), get `current_user`, call **one** service function, map result or domain error to HTTP | run SQL, hold business rules, call Redis/chromadb/LLM/LocationIQ/Brevo |
| `services/` | business rules, DB access, cache, external calls, atomic ops | import `fastapi.Request`, raise `HTTPException`, return `Response` objects |
| `models/` | ORM mapping only | contain logic |
| `schemas/` | request/response shapes, field whitelists | be skipped: never return an ORM object directly |

Services raise domain exceptions (`NotFound`, `Conflict`, `QuotaExceeded`, `ValidationFailed`,
`UpstreamUnavailable`). One set of exception handlers in `main.py` maps them to status codes
and a generic body.

```python
# router: validate -> delegate -> respond
@router.get("/charts/{chart_id}", response_model=ChartOut)
async def get_chart(chart_id: UUID, user: User = Depends(current_user), db=Depends(get_db)):
    return await chart_service.get_owned_chart(db, user.id, chart_id)   # raises NotFound

# service: owns the rule, no HTTP
async def get_owned_chart(db, user_id: UUID, chart_id: UUID) -> BirthChart:
    chart = await db.scalar(select(BirthChart).where(
        BirthChart.id == chart_id, BirthChart.user_id == user_id))
    if chart is None:
        raise NotFound("chart")
    return chart
```

## 2. Reuse first, no duplicate logic

- Before writing a helper, search for an existing one (`graphify query`, grep `services/`).
  Extend it rather than adding a near-copy.
- The same rule in two places (for example an ownership check or a quota check) is a bug waiting
  to diverge. Extract it to one service function and make both callers use it. The write path
  and the read path of the same rule must share code.
- Library first: a maintained library beats hand-rolled code (for example `slowapi` or a Redis
  `INCR` limiter rather than a custom rate limiter). Propose new dependencies; do not install them silently.

## 3. Async discipline

- All DB I/O is `async` via the async session. Never use a sync session in a request path.
- Swiss Ephemeris and other CPU-bound work runs through `run_in_threadpool`.
- Every external call (LLM, LocationIQ, Brevo) has an explicit timeout and specific exception
  handling inside its service. Raw `httpx` or SDK exceptions never reach a router.
- Do not hold a DB session across a slow external call (LLM stream, geocoding). Read what you
  need, release, call out, then open a short session to write.
- Streaming and background tasks: cleanup in `finally` (client disconnect is `GeneratorExit` /
  `CancelledError`, which `except Exception` misses).

## 4. Concurrency (atomic at DB level)

Forbidden: `SELECT` then a Python check then `INSERT/UPDATE` on shared state.
Use `UPDATE ... RETURNING`, `INSERT ... ON CONFLICT`, `SELECT ... FOR UPDATE`, or a unique
constraint. Hot spots in this app:
- `is_primary` on `birth_charts`: unset the others and set the new one in one transaction, backed by a
  partial unique index (`database_rules.md`).
- `conversations.message_count` and usage/quota counters: `UPDATE ... SET n = n + 1 RETURNING n`.
- Password reset consumption: `UPDATE password_resets SET used = true WHERE token = :t AND used = false
  AND expires_at > now() RETURNING user_id`.
- Daily reading generation: one generator per `(system, sign, date)` (unique constraint plus
  `ON CONFLICT DO NOTHING`, or a Redis lock).

## 5. API contract

- All routes under `/api/v1/`. Do not change a response shape without checking
  `frontend/src/services/` and `frontend/src/types/` usage. Additive changes only, unless
  the frontend is updated in the same change.
- Lists are paginated with a capped `limit` (for example max 50).
- Errors: `{"detail": "<generic message>", "code": "<stable_code>"}`. 401 unauthenticated,
  404 for not-found **or not-yours**, 409 conflict, 422 validation, 429 quota/rate,
  503 upstream unavailable.

## 6. Config and startup

- `config.py` via pydantic-settings. A missing required secret (`JWT_SECRET_KEY`, `DATABASE_URL`)
  fails startup. There are no in-code defaults for secrets.
- Startup self-checks: DB reachable, ephemeris path present (Swiss engine, not Moshier), RAG
  index loaded (degraded mode allowed and logged).
- Pin the Python version for Render to match local (the venv is 3.14, see
  `knowledge/Astrology/backend/python314-compatibility.md`).

## 7. Logging

- Structured logs for critical operations: `user_id`, `action`, `resource_id`, outcome,
  latency. Covers chart create/update/delete, auth events, LLM calls (tokens), quota denials.
- Never log passwords, tokens, reset codes, full birth data, prompt bodies, or API keys.

## 8. Domain rules live elsewhere

- Chart math: `astrology_accuracy_rules.md`. LLM/RAG: `ai_llm_rules.md`. Caching:
  `caching_rules.md`. Auth/ownership: `security_rules.md`. Schema: `database_rules.md`.

## Done checklist (backend)

- [ ] Router is validate -> delegate -> respond; no HTTPException in services
- [ ] Searched for existing helpers; no duplicated rule
- [ ] Ownership filter on every user-owned query (404 for not-yours)
- [ ] Concurrency-sensitive writes atomic
- [ ] External calls: timeout, mapped errors, no session held across them
- [ ] Cache invalidated on every mutation of cached data
- [ ] Response shape backward compatible or frontend updated
- [ ] Tests per `testing_rules.md`; touched modules import cleanly
- [ ] PITFALLS.md items re-checked for the touched area
