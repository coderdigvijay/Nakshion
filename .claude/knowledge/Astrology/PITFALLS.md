# Nakshion Release Pitfalls

Release-blocking invariants. The `pre-push-validator` agent audits every diff against this
list before a push. Read it once per session (CLAUDE.md, session start).

Keep it short and concrete: 2-4 lines per item. Add an item after any incident or any
verified hazard. Ask the user before **removing** one. Items marked *(hazard)* were found by
inspection and have not caused an incident yet.

## Invariants

1. **The LLM never produces positions.** Every sign, degree, house, aspect, nakshatra, and dasha
   shown or stored comes from Swiss Ephemeris. Prompts get CHART FACTS; structured outputs
   reference placements by key. (`astrology_accuracy_rules.md` section 1)

2. **Ownership on every user-owned row.** Charts, conversations, messages, compatibility
   reports, and resets are filtered by the token's `user_id`; not-yours returns 404. Composite
   requests (two charts in a compatibility report, the chart behind a conversation) check
   every id. (`security_rules.md` section 2)

3. **Birth time is converted through the IANA zone, to UT.** Never a fixed offset, never local
   time passed to `calc_ut`. Ambiguous or nonexistent DST times are flagged, not guessed.

4. **Zodiac system and house system are always explicit and labelled.** Tropical and sidereal
   (Lahiri default) are never mixed in one output. Cache keys and prompts include the system.

5. **Unknown birth time hides time-sensitive output.** No Ascendant, MC, houses, or dasha
   dates. The Moon sign is shown as ambiguous if it changes that day.

6. **Chart edits invalidate everything derived from the chart.** Recompute `chart_data` and
   delete `chart_summary` / `compat` keys after commit. Frontend invalidates query keys.
   (`caching_rules.md` section 2)

7. **Free-tier quotas are protected.** Every LLM, LocationIQ, or Brevo-calling endpoint and every auth
   endpoint is rate-limited. The LLM has per-user plus global daily caps. Quota checks fail closed.

8. **Safety policy holds.** No medical, legal, or financial certainty; no death or illness
   predictions; no fear-based or paid-remedy pressure. The crisis response is static and
   tested. (`ai_llm_rules.md` section 8)

9. **Migrations: Alembic, numbered, idempotent, reversible, single head.** A model column ships with
   its migration in the same change, and `alembic upgrade head` runs immediately.

10. **No internal detail leaks.** No raw `IntegrityError`, stack traces, SDK error text,
    `password_hash`, tokens, or birth data in responses or INFO logs.

11. **Streaming cleanup in `finally`.** Client disconnect is `GeneratorExit` / `CancelledError`.
    No DB session is held across an LLM call.

## Known hazards in the current code/schema (verified 2026-10-01)

12. *(hazard)* **No ephemeris files installed.** `backend/venv` pyswisseph returns
    `retflag=260` (Moshier fallback). Ship `.se1` files plus `set_ephe_path`, and add the startup check.

13. *(hazard)* **`conversations.chart_id` has no ON DELETE.** Deleting a chart that has
    conversations raises an FK violation (500). Migration to `SET NULL`, or detach in the service.

14. *(hazard)* **`messages.metadata` collides with SQLAlchemy's reserved `metadata`.** Map
    it as `mapped_column("metadata", JSONB)` under another attribute name.

15. *(hazard)* **`daily_horoscopes` unique key is `(zodiac_sign, date)` only.** Adding sidereal
    readings without a `zodiac_system` column and key change would overwrite tropical ones.

16. *(hazard)* **Alembic cannot run until `app.database` / `app.models` exist** (`env.py`
    imports them) and it needs a sync driver (`psycopg2-binary` is not in `requirements.txt`).

17. *(hazard)* **JWT in `localStorage`** (`frontend/src/services/api.ts`, `store/authStore.ts`).
    It is XSS-readable. Do not store anything else sensitive there. The target is an httpOnly refresh cookie.

18. *(hazard)* **Placidus/Koch raise `swisseph.Error` above about 66 degrees latitude.** Catch it and
    fall back (Porphyry or Whole Sign), recorded in `chart_data.meta`.

<!-- Add new pitfalls below this line. 2-4 lines each. Link the BUG_LEDGER entry if one exists. -->

19. **Ephemeris coverage is narrower than "1800-2399".** The shipped `.se1` files give SWIEPH only from
    1800-01-01 05:45 UT to 2400-01-07 UT; outside, pyswisseph silently returns Moshier (retflag 260). Check
    `retflag & FLG_SWIEPH` on every call and validate the UT instant. (BUG-002)

20. **Never divide a longitude by 40/3 or 10/3.** `120 // (40/3) == 8.0` in IEEE doubles, so a body at
    0 Leo lands in Ashlesha 4 and the dasha lord is wrong. Scale by an integer ratio first
    (`lon*108/360`). (BUG-001)

21. **Unknown-time charts: probe every body, not just the Moon.** Any planet that changes sign (tropical or
    sidereal) during the birth day must be flagged approximate, along with houses built on it. (BUG-004)
