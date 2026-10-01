# Testing & Verification Rules

There is no test suite yet (the backend is being rebuilt). Build it alongside the code. Every
rebuilt service lands with tests, and a fix lands with the test that would have caught it.

## Layout (target)

```
backend/tests/
  unit/          # pure functions: sign math, orbs, nakshatra, prompt builders, schemas
  integration/   # FastAPI app + real Postgres (test DB) + fakeredis + FakeProvider
  golden/        # reference charts (astrology_accuracy_rules.md section 9)
  evals/         # manual LLM eval set (ai_llm_rules.md section 10), never in CI
frontend/src/**/*.test.ts(x)   # Vitest + Testing Library (propose adding; not installed yet)
```

- Backend: `pytest` + `pytest-asyncio` + `httpx.AsyncClient(app=...)`. Add them to a
  `requirements-dev.txt`. Integration tests run against a disposable Postgres database migrated
  with `alembic upgrade head`, never against Neon production.
- No real network in tests: `FakeProvider` for the LLM, stubbed LocationIQ and Brevo clients.

## What every change must prove

| Change | Required tests |
|---|---|
| New endpoint touching a user-owned row | happy path + **other user's id returns 404** + unauthenticated 401 |
| Chart calculation | golden fixtures for both systems + unknown-time + edge latitudes |
| Counter / quota / `is_primary` / anything concurrent | two concurrent requests via `asyncio.gather`, assert the invariant |
| Cache read/write | cache hit, miss, invalidation on the mutating path, Redis-down fallback |
| LLM feature | FakeProvider: valid output, malformed output (fallback), timeout, budget exceeded |
| Streaming endpoint | early client disconnect cancels the upstream stream and releases the session |
| Migration | `upgrade head` then `downgrade -1` then `upgrade head` on a scratch DB |
| Bug fix | a regression test reproducing the bug, failing before the fix |

## Verification evidence (what "done" means)

Report observed results, not assumptions:
- Backend: `pytest -q --tb=short <paths>` while iterating; full suite once before commit.
  Pipe long output through `tail`.
- Import check of touched modules (`python -c "import app.main"`). Without git history, a
  broken import is invisible until the server starts.
- Exercise the real endpoint with `curl` against the dev server for behaviour changes.
- Frontend: `npm run build` (runs `tsc -b`) and `npm run lint`. For UI changes, drive the
  running app with a Playwright script: no console errors, no failed requests, key DOM state
  asserted, 1-2 screenshots at 375px and 1440px.
- Playwright runs in its own headed browser window, never attached to the user's browser.
  Leave no tabs behind.

## Rules

- Positive and negative cases for every changed path. A test that passes with the fix
  reverted is not a regression test.
- Mocks must be realistic. An axios error mock has `isAxiosError: true` and a
  `response.status`. A plain `new Error()` lets status-branching code pass for the wrong reason.
- Never widen a golden-test tolerance or delete a failing test to get green. Fix the code
  or escalate.
- Stop after the same error twice and report. Do not loop.
