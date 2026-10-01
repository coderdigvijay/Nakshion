# Security Rules - Auth / Ownership / Abuse / Personal Data

There is **no RBAC**: `users.subscription_tier` (free/paid) is a feature gate, not a role. Do not
invent admin or moderator roles. If an admin surface is ever needed, propose it as its own T2
design. The real attack surface is per-user isolation (IDOR), auth flows, secrets,
free-tier quota abuse, LLM misuse, and birth data as personal data.

## 1. Authentication

- JWT via python-jose. Set the algorithm explicitly (`algorithms=["HS256"]` on decode; never accept
  `none`). Require `exp`. Use a short-lived access token. `JWT_SECRET_KEY` comes from env, and
  startup fails if it is missing.
- The token's `sub` resolves to a user that still exists on each request (`current_user`
  dependency). A deleted user's token yields 401.
- bcrypt for passwords (`bcrypt.checkpw`, constant time). Never log or return a password,
  hash, reset token, or verification code.
- OAuth users can have `password_hash IS NULL`. Login-with-password and reset flows must handle
  that (no crash, no "set a password via reset" bypass that skips email ownership proof).
- Password reset tokens: random (`secrets.token_urlsafe(32)`), stored hashed if feasible,
  single-use, and expiring, consumed with one atomic `UPDATE ... WHERE used = false AND
  expires_at > now() RETURNING`. "Forgot password" answers identically whether or not the
  email exists.
- Email verification codes: expiring, attempt-limited, compared with `secrets.compare_digest`.

## 2. Authorization = ownership, server-side, every time

For `birth_charts`, `conversations`, `messages`, `compatibility_reports`, `password_resets`:
- `user_id` comes from the verified token, never from the body, query, or path.
- The query filters by `user_id`. Another user's id returns **404** (do not confirm it exists).
- Composite operations check every referenced resource: a compatibility report needs **both**
  `chart1_id` and `chart2_id` owned by the caller; a conversation's `chart_id` must be owned by the
  caller. Authorize the resource, not just the parameter.
- The LLM context builder loads only the caller's own charts and messages.
- Frontend gates are UX only.

```python
# WRONG - any logged-in user can read any chart
chart = await db.get(BirthChart, chart_id)
# RIGHT
chart = await db.scalar(select(BirthChart).where(
    BirthChart.id == chart_id, BirthChart.user_id == user.id))
```

## 3. Input validation and mass assignment

- Every body is a Pydantic model with `model_config = ConfigDict(extra="forbid")` and an explicit
  field whitelist. `user_id`, `subscription_tier`, `email_verified`, `chart_data`, and `is_primary`
  (outside its own endpoint) are never client-writable.
- Birth inputs are bounded: lat/lon ranges, a date within the shipped ephemeris range, no future
  births, an IANA tz name validated against `zoneinfo.available_timezones()`, name length caps.
- Chat input is length-capped before it reaches the LLM (`ai_llm_rules.md`).

## 4. Abuse and quota protection (free tier = shared fate)

One unthrottled endpoint can burn the day's Gemini, LocationIQ (a few thousand/day on the free plan - check current limits), or Brevo (300/day)
quota for every user.
- Per-user **and** per-IP limits on: login, register, forgot-password, verify-email,
  geocoding search, chat send, chart create, compatibility create, daily reading generation.
- Per-user daily LLM budget by tier plus a global daily kill-switch (`ai_llm_rules.md` section 6).
- Rate limiting stays enabled in production. A `DISABLE_RATE_LIMITING`-style flag, if it exists,
  defaults off and is checked in the deploy env.
- Geocoding is proxied server-side and cached, so the LocationIQ key never reaches the browser.

## 5. LLM-specific

- Prompt injection: user text is delimited data in the user turn. The model has no tools or data
  access beyond the caller's own context, so injection cannot cross users.
- Model output is untrusted: render as text or sanitised markdown, never raw HTML.
- Streaming endpoints: cleanup in `finally`. Repeated disconnects must not leak DB connections
  (pool exhaustion is a DoS vector on a 5-connection pool).
- Safety policy (no medical/legal/financial certainty, no fear predictions, a static crisis
  response) is in `ai_llm_rules.md` section 8 and is a release requirement.

## 6. Secrets

- `.env` files are gitignored. Never commit them or paste their values into code, commits, logs,
  ledger entries, or docs. Never read production `.env` files in an agent session.
- Third-party keys are server-side only. Anything in `VITE_*` is public (Vite inlines it).
- If a secret appears in a file, command history, or a settings allowlist, treat it as leaked:
  rotate it and remove it.

## 7. Personal data (birth data is sensitive)

- Birth date, time, and place identify people, and charts often belong to third parties (partner,
  child). Minimise: never log them at INFO, never send email or ids to the LLM, never put them in
  URLs or cache keys.
- Account deletion removes everything via CASCADE (verify when adding tables) and purges the
  user's Redis keys. Provide a data export if the PRD requires it.
- Responses never include `password_hash`, OAuth ids, reset tokens, internal error text, or stack
  traces. Global exception handlers return generic messages.

## 8. Web hardening

- CORS: explicit allowed origins from config (the deployed frontend URL plus localhost in dev),
  never `*` with credentials.
- Security headers on the frontend host (CSP report-only first, `X-Content-Type-Options`,
  `Referrer-Policy`). `rel="noopener noreferrer"` on external links.
- Token storage: currently `localStorage` (known risk, PITFALLS). Do not add more sensitive
  data beside it.

## Security review checklist (every new or changed endpoint)

- [ ] Auth dependency applied (or deliberately public and rate-limited)
- [ ] Ownership filter for every referenced resource; 404 for not-yours
- [ ] Pydantic `extra="forbid"`; no privileged fields writable
- [ ] Rate/quota limit if it calls LLM, LocationIQ, or Brevo, or is an auth endpoint
- [ ] No secrets, PII, or internal errors in responses or logs
- [ ] Streaming/background cleanup in `finally`
- [ ] A filtered or authorized value is the one used on every later branch (retry, error,
      log). Check copy-pasted call sites against each other, not just the base.
