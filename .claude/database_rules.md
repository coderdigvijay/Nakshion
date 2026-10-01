# Database Rules - PostgreSQL (Neon) / SQLAlchemy 2.0 / Alembic

Owner: `database-architect`. Any migration is **T2** and needs plan approval.

## 1. Schema source of truth: `backend/alembic/versions/`

Read the migration files before writing a model or a query. Do not trust summaries,
including this one. Snapshot (2026-10-01):

| Table | Notes |
|---|---|
| `users` | UUID pk, `email` unique, `password_hash` **nullable** (OAuth users), `oauth_provider/oauth_id`, `email_verified`, `subscription_tier` (default `free`), `timezone`, `last_login_at` |
| `password_resets` | `token` unique, `used`, `expires_at`; FK users CASCADE |
| `birth_charts` | FK users CASCADE; `date_of_birth`, `time_of_birth` nullable, `has_exact_time`, `latitude/longitude` Numeric(10,7), `timezone`, `chart_data` JSONB, `is_primary` |
| `conversations` | FK users CASCADE; `chart_id` FK birth_charts **without ondelete**; `message_count`, `status`, `category` |
| `messages` | FK conversations CASCADE; `role`, `content`, `metadata` JSONB, `tokens_used`, `created_at` indexed |
| `daily_horoscopes` | unique `(zodiac_sign, date)`; `transit_data` JSONB; reading columns; no user FK |
| `compatibility_reports` (002) | FK users, chart1, chart2 all CASCADE; `overall_score` Numeric(3,1); `compatibility_data` JSONB |

Known schema hazards (also in PITFALLS):
- Deleting a `birth_charts` row referenced by a conversation raises an FK violation. Decide
  `SET NULL` (keep chat history) in a migration, or delete/detach conversations in the service
  first.
- The `messages.metadata` column name collides with SQLAlchemy's reserved `metadata` attribute
  on declarative models. Map it as `meta: Mapped[dict | None] = mapped_column("metadata", JSONB)`.
- No partial unique index enforces one primary chart per user yet.
- `daily_horoscopes` has no zodiac-system column, so sidereal readings need a migration.
- Missing indexes worth adding with the rebuild: `birth_charts(user_id)`, `conversations(user_id, updated_at)`,
  `messages(conversation_id, created_at)`, `compatibility_reports(user_id)`.

## 2. Migrations

- Alembic only. Revisions are hand-numbered: `revision = "003"`, `down_revision = "002"`,
  file `003_<what>.py`. Keep one linear head (`alembic heads` shows exactly one).
- New migrations are **idempotent** (`IF NOT EXISTS` / `IF EXISTS`, or inspector checks) so a
  partial apply can be re-run. (001/002 predate this rule.)
- Every migration has a real `downgrade()`. If data loss is unavoidable, say so in the
  docstring and still provide the best-effort reverse.
- Test `upgrade head`, then `downgrade -1`, then `upgrade head` on a scratch DB before merging.
- Model column added means migration in the same change, then `alembic upgrade head` locally
  at once. The ORM selects every mapped column, so a model ahead of the DB breaks every query
  on that table.
- `env.py` uses a sync URL (it strips `+asyncpg`), so a sync driver (`psycopg2-binary`, or
  `psycopg`) must be in `requirements.txt`. It imports `app.database` and `app.models`, so the rebuilt
  app must keep those module paths or update `env.py` in the same change.
- Neon free tier: build indexes on big tables with `CREATE INDEX CONCURRENTLY` inside
  `op.get_context().autocommit_block()`. At this app's size, a plain index is usually fine.
  Say which you chose.
- Data backfills are separate, reviewed steps. Never hide a bulk `UPDATE` of user data inside a
  schema migration without plan approval.

## 3. Conventions

- `postgresql.UUID(as_uuid=True)` primary keys. `DateTime(timezone=True)` everywhere, with
  `server_default=sa.func.now()`. Never add a naive datetime column (this app is all about time
  zones).
- `updated_at` is set by the service on update (or by `onupdate=func.now()`). It is not maintained
  by the server default alone.
- JSONB for flexible payloads (`chart_data`, `compatibility_data`, `metadata`). Document the
  shape in a Pydantic model and validate before writing. Put a `meta.engine_version` inside
  `chart_data` (`astrology_accuracy_rules.md`).
- Enumerated strings (`subscription_tier`, `role`, `relationship`, `status`) get a `CHECK`
  constraint or a Python `Enum` validated in schemas.
- Every user-owned table: FK to `users.id` with `ondelete="CASCADE"`, plus an index on `user_id`.
- Constraints over code: uniqueness, one-primary-chart, and one-reading-per-key belong in the DB.

## 4. Queries

- Every read of a user-owned table filters by the authenticated `user_id` in the same query
  (`security_rules.md`). Fetching by id and checking afterwards is acceptable only when it
  raises NotFound on mismatch.
- No N+1: `selectinload` for collections (messages of a conversation), joins or aggregates for
  counts. No query inside a loop.
- Paginate messages and charts (`created_at` keyset or limit/offset with a cap).
- Raw SQL only via `text()` with bound parameters. No f-strings.
- Never swallow `IntegrityError`. Map it to a domain `Conflict` and log it. Never return its text.

## 5. Neon and pool reality

- Small async pool (`pool_size` 5, `max_overflow` 5), `pool_pre_ping=True`, and a modest
  `pool_recycle`. Neon free tier suspends on idle and limits connections, so the first query after
  idle can be slow. Do not treat that as an outage.
- Use Neon's pooled connection string for the app. Use the direct (unpooled) string for
  Alembic migrations.
- Account deletion relies on the CASCADE chain. Verify it covers every new user-owned table.

## Checklist (schema or query change)

- [ ] Read the actual migration files first
- [ ] Migration numbered, idempotent, real downgrade, up/down/up tested
- [ ] Model and migration in the same change; `alembic upgrade head` run
- [ ] FK + CASCADE + `user_id` index on new user-owned tables
- [ ] Invariants enforced by constraints, not Python
- [ ] No N+1; lists paginated; ownership filter present
