# Bug Ledger - Nakshion

Regression-prevention log. **Read the matching entries before diagnosing or fixing a bug**
(grep for the files or feature you are touching; do not read the whole file once it grows).
**Prepend a new entry after every fix**, directly under "Entries" (newest first).

Rules:
- One entry per bug. The heading must start with `## BUG-NNN` (zero-padded, next number). The
  session hooks count and search these headings.
- State the tier (T0/T1/T2, see `.claude/CLAUDE.md`), the confirmed root cause (not the first
  hypothesis), and the evidence that proved it.
- **Regression guard** is mandatory: the test name(s) plus the invariant future changes must keep.
  When you touch a file listed in an entry, re-verify that entry's guard.
- Never paste secrets, tokens, `.env` values, real user emails, or birth data here. Use
  synthetic examples.
- If the bug reveals a release-blocking invariant, add it to
  `.claude/knowledge/Astrology/PITFALLS.md` too.
- Label claims: **[verified]** (reproduced or observed), **[measured]** (counted or queried),
  **[reported]** (from user or agent, not yet confirmed).

Template (copy above the first entry; this fenced block is not an entry):

```
## BUG-NNN: <short title> (YYYY-MM-DD)

- **Tier:** T0 | T1 | T2 - <why>
- **Symptom:** <what the user saw, where> [reported|verified]
- **Root cause:** <file:function - the actual mechanism> [verified]
- **Evidence:** <repro steps / query / log line that proved it>
- **Fix:** <what changed and why this approach>
- **Blast radius:** <who or what data was affected; data corrected? yes/no, with approval?>
- **Files:** <paths>
- **Verified:** <commands run + results, e.g. `pytest tests/x.py -q` 8 passed; Playwright at 375/1440>
- **Regression guard:** <test name(s)> + <invariant to keep, phrased as a rule>
- **Committed:** <sha | not yet>
```

## Entries

## BUG-018: Vedic personal reading carried tropical aspect factors incl. outer planets and ASC; compat had no band (2026-10-01)

- **Tier:** T2 - chart facts fed to the LLM and shown as chips.
- **Symptom:** acceptance QA: a Vedic "Today" card listed `T.PLUTO.SEXTILE.N.ASC`, `T.SATURN.SEXTILE.N.MARS` (tropical) with no system label. [verified]
- **Root cause:** `personal.personal_day` built transit factors from `compute_transits()["western"]` for both systems; only the Moon house and dasha were system-aware.
- **Fix:** one zodiac per reading. Vedic: `G.*` sidereal gochara/graha conjunction-opposition (nine grahas, Lagna only when time known), `V.*` dasha/Sade Sati, `P.*` panchang. Western: `T.*`/`W.*` only. Every factor and key_factor carries `system`. `compute_compatibility` adds `overall_band` from the single band table in `compatBands.tsx`.
- **Blast radius:** readings cached before this fix for Vedic users show mixed factors until regenerated.
- **Files:** backend/app/astrology/personal.py, compatibility.py
- **Verified:** `pytest backend/tests/astrology -q` all passed.
- **Regression guard:** `test_personal_panchang_sadesati.py::test_one_zodiac_per_reading_vedic_has_no_tropical_ids`, `::test_vedic_graha_conjunction_factor_is_sidereal`; `test_compatibility.py::test_overall_band_matches_frontend_table`. Rule: no factor id from the other zodiac in a reading; a self-pair (Sun on natal Sun) is a valid transit.
- **Committed:** not yet

## BUG-011: Unknown-time charts presented pseudo-houses/lagna as fact; compat overall unexplained (2026-10-01)

- **Tier:** T2 - chart calculation and presentation.
- **Symptom:** E2E QA: for unknown birth time the chart carried solar whole-sign houses, a Moon "lagna", house-based yogas, D9/D10 and Mangal-from-lagna; dasha looked exact. Compat overall 5.0 sat below four of five category scores (8.1/3.4/6.9/5.2/9.3) with no explanation. [verified]
- **Root cause:** engine 1.x followed spec 3.5 (pseudo-houses) instead of accuracy rules section 6; overall was a 50/50 blend with an Ashtakoota total the output never explained. Also, "dasha uncertain by about a year" was wrong: the Moon covers ~1 nakshatra per day, so the balance is uncertain by up to the starting lord's whole period (7-20 y).
- **Fix:** engine 2.0.0: houses=[], house=null, vedic.lagna=null, lagna-based yogas/functional nature/vargas withheld, dasha flagged approximate with `candidates`; `score_breakdown`; Ashtakoota `total_range`.
- **Blast radius:** stored unknown-time charts at 1.x keep the old shape; the major bump triggers lazy recompute.
- **Files:** backend/app/astrology/{chart,yogas,dasha,vedic,transits,compatibility,version}.py; docs/astrology-engine.md
- **Verified:** `pytest backend/tests/astrology -q` 325 passed.
- **Regression guard:** `test_chart.py::test_unknown_time_path`, `::test_unknown_time_dasha_everything_approximate`, `test_compatibility.py::test_score_breakdown_reproduces_overall`. Rule: an unknown-time chart never emits a house number, lagna, angle, lagna-based yoga or divisional chart.
- **Committed:** not yet

<!-- Newest first. Prepend BUG-001 here. -->

## BUG-021: New knowledge files: retrieval skipped for most questions, denied Gemini key poisoned the pool, metadata-only re-ingest ignored (2026-10-01)

- **Tier:** T2 - retrieval, ingest, LLM routing.
- **Symptom:** Found during the 29-file corpus integration. (1) "Is my Bhakoot dosha cancelled?" and "Moon in 7th house" got no reference notes. (2) Every chat call failed with LLMUnavailable after one Gemini key returned 403. (3) Re-ingest reported "unchanged" after chunk metadata changed. (4) The model's harmless "CHART FACTS does not list..." was replaced by a canned reply. [verified]
- **Root cause:** (1) retrieval ran only when the keyword topic was not "general". (2) the Gemini adapter rotated keys only on 429, so a 403 key stayed in the pool; all-models-cooling-down then failed the request. (3) change detection compared text hashes only. (4) the output filter treated naming an internal block as a prompt leak.
- **Fix:** Retrieval runs for every non-small-talk question. Denied (401/403) keys are dropped from the pool; when every model is cooling down the one that frees first is tried. Ingest updates metadata in place (`metadata_updated`). Internal block names are rephrased (`deleak`). Also new: front-matter ingestion, row-group table chunking, western-degree chunks tagged `western`, Hinglish phrasebook and glossary-file planner data, confidence/unverified/schools-differ handling.
- **Files:** backend/app/rag/*, backend/app/llm/{responder,router,textclean,validators,builder}.py, providers/gemini.py, prompts/chat/v6.j2
- **Verified:** `pytest backend/tests/rag backend/tests/llm -q` passes (scratch-DB gate on). Dev `astroai` at index version 5 (773 chunks), `/health/ready` rag ok.
- **Regression guard:** `tests/rag/test_new_corpus.py`, `test_ingest_versioning.py::test_metadata_only_change_updates_in_place_without_reembedding`, `tests/llm/test_bug003_provider_failover.py::test_gemini_drops_a_denied_key_and_uses_the_next`, `test_e2e_run2_fixes.py::test_when_every_model_is_cooling_down_the_soonest_one_is_still_tried`. Rule: a bad key or a cooling-down model must never cause a 503 while another route exists.
- **Committed:** not yet

## BUG-020: Compat narrative leaked enum values ("below_average", "PRESENT") into prose (2026-10-01)

- **Tier:** T1 - narrative text.
- **Symptom:** The summary showed raw `below_average` and `PRESENT`. [reported]
- **Root cause:** `compat_fact_lines` wrote raw enum/flag values into REPORT FACTS and the model copied them. [verified]
- **Fix:** Plain-word facts, `plain_words()` applied to every narrative field, prompt `compat@v4`.
- **Files:** backend/app/llm/compat_checks.py, service.py, prompts/compat/v4.j2
- **Verified:** `pytest backend/tests/llm backend/tests/rag -q` passes.
- **Regression guard:** `tests/llm/test_acceptance_d3_d6_d4.py::test_narrative_with_leaked_tokens_is_cleaned`. Rule: no snake_case or ALLCAPS engine tokens in user-facing prose.
- **Committed:** not yet

## BUG-019: Template headline showed a raw ISO date range; machine tokens ("below_average", "PRESENT") could reach prose (2026-10-01)

- **Tier:** T1 - user-visible copy
- **Symptom:** Today's fallback headline read "Today's focus: Mercury Mahadasha (2025-07-03 to 2042-07-03)"; compat summaries showed "below_average" and "PRESENT" [verified in QA]
- **Root cause:** `services/ai.py::_personal_template` interpolated the engine factor label verbatim; narrative strings were passed through without sanitising
- **Fix:** `_headline_subject` strips ISO dates and turns "Mahadasha" into "period" ("Mercury period — steady focus today", localised for hindi/hinglish); `humanize()` runs on every generated narrative (LLM and template) for personal readings and compatibility
- **Files:** backend/app/services/ai.py
- **Verified:** `tests/unit/test_helpers.py` (2 new), `tests/api/test_compatibility.py::test_llm_narrative_machine_tokens_never_reach_the_report`
- **Regression guard:** those tests. Rule: no factor label or enum value is interpolated into prose without going through `_headline_subject` / `humanize`
- **Committed:** not yet

## BUG-017: Acceptance QA: mixed zodiac systems, compat doshas lost in the backend view, Hindi dasha typo, flapping-model latency (2026-10-01)

- **Tier:** T2 - prompts, validators, grounding.
- **Symptom:** (D3) Vedic readings listed "Transiting Pluto sextile natal ASC" chips and a chat answer gave tropical and sidereal Moon. (D4) 12/36 with Bhakoot+Gana got a summary and needs-care list without them; friendship 5.7 said "good overall". (D6) "अंतर्दृशा". TTFT 4-8 s. [reported, verified]
- **Root cause:** (D3) The engine's vedic `personal_day` emits tropical `T.<planet>.<aspect>.N.<point>` factors; `derive_factors` and CHART FACTS mixed both systems. (D4) `services/ai.py::_llm_report_view` drops the `ashtakoota` dict, so BUG-014's dosha checks never saw doshas; bands differed from the frontend. (D6) no spelling check. Latency: a flapping 503 model was retried every 20 s.
- **Fix:** `system_allows` filters facts per system, CHART FACTS/summary/chips carry a system label, `check_system_blend`; `normalize_report` rebuilds doshas from `kootas`, doshas must be in `challenges`, bands match `compatBands.tsx`; `fix_terms`; exponential model cooldown; Gemini thinking `minimal`.
- **Files:** backend/app/llm/ (facts, labels, validators, compat_checks, textclean, router, service, responder, config), prompts chat/v5 and compat/v3
- **Verified:** `pytest backend/tests/llm backend/tests/rag -q` 249 passed. Live TTFT median 2.5 s -> 1.6 s, worst 5.1 s -> 2.6 s.
- **Regression guard:** `tests/llm/test_acceptance_d3_d6_d4.py` (parses the frontend band thresholds). Rule: one zodiac system per answer; compat tone and doshas follow the single band table.
- **Committed:** not yet

## BUG-016: Personal reading survived a primary-chart edit; saved people could become primary (2026-10-01)

- **Tier:** T1 - wrong astrology shown to a user
- **Symptom:** After editing the birth time, Today still showed a reading built from the old chart ("birth time unknown", old dasha) next to the new Lagna; a partner chart could be set primary and then drove readings and chat [verified in acceptance QA]
- **Root cause:** `chart_service` invalidated only Redis; `personal_reading_service` then returned the `personal_readings` row because `chart_id` matched. No freshness, system or engine-version check, and no rule that the primary chart is the user's own
- **Fix:** edit, lazy-upgrade and delete drop the chart's rows in the same transaction; a row is served only if chart, system, `engine_version` and `created_at >= chart.updated_at` all match; primary requires `relationship = 'self'` (API 422 `PRIMARY_MUST_BE_SELF`, `get_primary`, delete-promotion, and DB CHECK `ck_chart_primary_is_self`, migration 009); engine failure is 503 `PERSONAL_READING_UNAVAILABLE` with `Retry-After`, never a cross-system fallback
- **Files:** backend/app/services/{chart,personal_reading}_service.py, app/core/errors.py, alembic/versions/009_*.py
- **Verified:** `tests/api/test_acceptance_fixes.py` (12 tests)
- **Regression guard:** same file. Rule: anything derived from chart data must be deleted with it and validated on read against chart, system and engine version
- **Committed:** not yet

## BUG-015: Production-guard validation error echoed secret fragments into the logs (2026-10-01)

- **Tier:** T1 - secret handling
- **Symptom:** When `Settings` refused a production boot, Pydantic's error text ended with `input_value={'APP_NAME': ..., 'cccc...'}`, a truncated dump of the whole settings input including the tail of secrets [verified by raising the error locally]
- **Root cause:** `Settings.model_config` did not set `hide_input_in_errors`, and Pydantic includes the offending input (the full settings dict for a model validator) in `ValidationError` text. Render log lines would have carried it
- **Fix:** `hide_input_in_errors=True` in `core/config.py`; the guard's own messages name settings, never values
- **Files:** backend/app/core/config.py
- **Verified:** `tests/unit/test_config_prod.py` (asserts `input_value` and the secret strings are absent from the error text, 17 cases)
- **Regression guard:** same test. Rule: any settings or secret-bearing model must be built with input hidden in errors
- **Committed:** not yet

## BUG-014: Chat QA run 2: unknown-time Hindi answers, compat tone vs scores, 429 latency, style nits becoming 503 (2026-10-01)

- **Tier:** T2 - prompts, validators, LLM budgets.
- **Symptom:** (1) A Hindi lagna/10th-house question on an unknown-time chart got a 4-sentence answer starting "नमस्ते! हालांकि,", never said houses were unavailable, ignored "विस्तार से", used feminine verb forms, and showed English chips. (2) A romantic compat narrative said "dynamic and balanced, steady partnership" at 17/36 Below Average with Bhakoot/Gana dosha, and truncated twice on Flash-Lite. (3) 429s on `gemini-3.8-flash` cost latency. [reported by QA, verified]
- **Root cause:** (1) The prompt had no rule for unsupported questions, greetings, connectors, gender or length, and the validator treated "I can't see your lagna without a birth time" as a time-unknown violation. (2) `generate_compat_narrative` read keys the engine does not emit (`aspects`, top-level `kootas`), so the narrative never saw the score band, verdict or doshas. (3) The router retried a 429 on the same model and had no per-model cooldown. While testing: a style violation that survived one repair raised `LLMUnavailable` (503).
- **Fix:** Chat prompt `chat@v4` (answer first, say plainly what the chart cannot support, no greeting or leading connector, no gendered verbs, honour detail/brief). Deterministic `tidy_start` and `neutralize_gender`, a length check for detail/brief requests, and Hindi chip labels via `app/llm/labels.py` (`label` in the reply language, `label_en` kept). Honest unavailability sentences are exempt from the time-unknown guard. Style-only failures are accepted as `repaired_soft`, never 503. Compat `compat@v2` consumes `compute_compatibility()`'s real shape and `consistency_problems` rejects summaries too positive for the band, a missing Ashtakoota/dosha mention, or a negative tone at a strong band; compat budget 2200 tokens. 429: no same-model retry unless Retry-After <= 1.5 s, per-model cooldown from `retryDelay`/`Retry-After` (30 s default, 10 min on per-day quota).
- **Blast radius:** Hindi/Hinglish chat and compat narratives. No stored data changed.
- **Files:** backend/app/llm/{responder,validators,textclean,labels,compat_checks,router,errors,safety,service,builder}.py, providers/{gemini,claude}.py, prompts/chat/v4.j2, prompts/compat/v2.j2
- **Verified:** `pytest backend/tests/llm backend/tests/rag -q` 222 passed, 7 skipped. Live: unknown-time Hindi detail and brief questions answer "birth time unknown" first with Hindi chips; a 10-call burst with `gemini-3.8-flash` 503 served by Flash-Lite in about 2 s each after the first.
- **Regression guard:** `tests/llm/test_e2e_run2_fixes.py`. Rules: an answer never starts with a greeting or connective the user did not earn; a question the chart cannot answer is declined in the first sentence; compat tone must agree with score band and dosha flags; a 429 or 503 puts that model on cooldown and is never retried on the same model; a style nit never becomes a 503.
- **Committed:** not yet

## BUG-013: RAG could not re-index, and retrieval ignored the question (2026-10-01)

- **Tier:** T2 - schema/ingest and retrieval quality.
- **Symptom:** Found by the new retrieval eval. (1) A second `python -m app.rag.ingest` would fail: `kb_chunks` had `PRIMARY KEY (id)` but the protocol inserts the same ids under a new `index_version`. (2) Measured hit@5 was 0.21 over 108 labelled queries, 0.17 in Hindi: chart-generic chunks came back for every question. [verified]
- **Root cause:** (1) The PK ignored `index_version`. (2) The retriever embedded the question and up to six top-factor `kb_keys` and fused them with equal weight, so six factors unrelated to the question outvoted it; Hindi/Hinglish questions were not embedded at all and an English-only model cannot read Devanagari. The FTS query ANDed the words of whole phrases and matched nothing. The same-version dev index also had zero pre-embedded keys.
- **Fix:** Migration 008 (PK `(index_version, id)`, `meta` JSONB, heading-weighted tsvector; applied up/down/up on a scratch DB). Retriever v2: question-led query plan, relevance-gated keys, Hindi/Hinglish glossary and phonetic bridge, one-round-trip hybrid SQL with weighted RRF, boosts, diversity, cache, breaker, timeout. Index keeps the previous version for `--rollback`; unchanged chunks are copied, not re-embedded.
- **Blast radius:** Retrieval quality only; the answers stayed grounded because chart facts always lead. The dev index (v1) still reads fine; re-ingest needs migration 008 first.
- **Files:** backend/app/rag/*, backend/alembic/versions/008_rag_versioned_chunks.py, backend/evals/rag/*
- **Verified:** hit@5 0.213 -> 0.956 (204 queries), blind holdout 0.86, Hindi 0.17 -> 0.91; `pytest backend/tests/rag -q` passes, including the scratch-DB gate. See docs/rag-runbook.md.
- **Regression guard:** `tests/rag/test_eval_gate.py` (thresholds), `test_retriever_ops.py::test_unrelated_factor_keys_do_not_drown_the_question`, `test_ingest_versioning.py`, `test_keys.py`. Rule: a retrieval gate must pass before a corpus, chunking or query-planning change ships, and every kb_key an engine producer emits must be in the pre-embedded vocabulary.
- **Committed:** not yet

## BUG-012: Mixed tropical/sidereal chat suggestions, JSON-offset field names, blank chat messages, 1-minute Rahu Kaal mismatch (2026-10-01)

- **Tier:** T1 - user-visible correctness
- **Symptom:** Suggestions paired a tropical Moon sign with "mahadasha"; malformed JSON reported field "33"; a message of control characters plus a space was accepted blank; R3 and /panchang disagreed on Rahu Kaal by a minute [verified in E2E]
- **Root cause:** `chat_service.suggestions` read tropical `moon_sign` for every user; Pydantic `json_invalid` errors carry a byte offset as `loc`; `SendMessageIn` trimmed BEFORE dropping control characters, leaving " "; R3 passed the birthplace at full precision while `/panchang` rounds to 0.1 degree
- **Fix:** suggestions follow `users.astrology_system` and label the system; `json_invalid` returns "Request body isn't valid JSON."; strip after filtering; one `insight_service.round_coords` convention for both. Panchang items gain `end_local_date` / `end_day_offset`
- **Files:** backend/app/services/chat_service.py, insight_service.py, personal_reading_service.py, app/schemas/chat.py, app/core/errors.py
- **Verified:** `tests/api/test_e2e_round2.py` (5 tests); the blank-message case failed before the fix
- **Regression guard:** same tests. Rule: filter then trim user text; derive Panchang-based output from one rounded coordinate pair; never mix zodiac systems in one prompt list
- **Committed:** not yet

## BUG-010: Streamed chat persisted truncated as ok, wrong reply language, fact IDs visible while streaming (2026-10-01)

- **Tier:** T2 - prompts, validators, streaming.
- **Symptom:** (1) a streamed Hindi answer was stored cut mid-sentence ("...अत्यंत संवेदनशील"), outcome ok, no citations. (2) A Hindi question with language=EN got "I am replying in English as per my guidelines". (3) `[VN.MOON.NAK.ASHLESHA]` showed in deltas. (4) Unknown-time charts could get house-based claims. [reported by QA, verified in tests and live]
- **Root cause:** `responder.stream` ignored the final `finish_reason` and treated a missing or garbled `<<<META>>>` block as a valid answer with default meta. The prompt never told the model which language to use when the question's script differed from the setting, and nothing flagged meta commentary. Deltas were emitted raw. A Hindi false positive was also found: the validator's `भाव` house pattern matched inside स्वभाव/भावना and stripped valid sentences.
- **Fix:** A stream counts as complete only with finish_reason=stop and a parsed META block. Otherwise it regenerates through the structured path, sends `replace`, and records outcome `regenerated`; if that fails it raises and nothing is persisted. `textclean.effective_language` makes a Devanagari question answer in Hindi. Prompt `chat@v3` forbids mentioning rules or guidelines and has the unknown-time rules. Meta commentary is a safety "leak" class. `BracketFilter` strips `[ID]` and `[KB:..]` from deltas and answers, and valid IDs move into citations. Unknown time drops yogas and house-based doshas from facts, labels Moon items approximate, and the validator flags house-based yoga names. Devanagari patterns now use script lookarounds.
- **Blast radius:** Streamed answers only; no stored data was corrected. Frontend needs no change: the H6 event shapes are unchanged, deltas are just clean, citations stay in `done`.
- **Files:** backend/app/llm/{responder,textclean,facts,validators,safety}.py, prompts/chat/v3.j2, prompts/registry.yaml
- **Verified:** `pytest backend/tests/llm -q` 153 passed, 5 skipped. Live Hindi stream on a real unknown-time chart, language hindi and english: outcome ok, Devanagari, no brackets, citations present.
- **Regression guard:** `test_bug_stream_language_ids.py`. Rules: a stream without finish_reason=stop and valid META is never persisted as ok; deltas never contain fact IDs; reply language follows the question's script; no house-based claims when birth time is unknown.
- **Committed:** not yet

## BUG-009: Pydantic wording and a bogus time zone reached the UI; malformed ids gave a retryable 422 (2026-10-01)

- **Tier:** T1 - user-facing errors on every form
- **Symptom:** A 101-character name showed "List should have at most 100 items"; the chat quota 429 said "reset at midnight (UTC)" for IST users; `/compatibility/not-a-uuid` returned 422 so the UI offered "Try again" [verified in E2E]
- **Root cause:** `core/errors.py:_humanise` passed Pydantic's `msg` through; `quota_service._exceeded` printed the stored `users.timezone` (defaults to "UTC", rarely set); path-param validation errors were treated as ordinary 422s
- **Fix:** per-type plain copy ("Name must be 100 characters or fewer."), 429 body now carries `resets_at` (ISO UTC) and `limit` with no zone label, all-path validation errors return 404 `NOT_FOUND`
- **Files:** backend/app/core/errors.py, backend/app/services/quota_service.py
- **Verified:** `tests/api/test_error_copy.py` (3 tests)
- **Regression guard:** same tests. Rule: never forward Pydantic `msg` text or a stored-timezone label to the UI
- **Committed:** not yet

## BUG-008: Request-body cap implemented by raising in `receive` surfaced as 400, not 413 (2026-10-01)

- **Tier:** T1 - abuse protection on every endpoint
- **Symptom:** A chunked upload over the cap returned `400 There was an error parsing the body` instead of 413 `PAYLOAD_TOO_LARGE` [verified]
- **Root cause:** `core/middleware.py:BodyLimitMiddleware` first raised an exception from the wrapped `receive`. FastAPI's request handler catches any exception raised while reading the body and converts it to `HTTPException(400)`, so the mapped 413 never ran. The Content-Length pre-check worked; only the streaming path was wrong [verified]
- **Fix:** On overflow, report `http.disconnect` to the app, swallow whatever response it tries to send, and emit the 413 from the middleware after the app returns
- **Blast radius:** none (pre-release)
- **Files:** backend/app/core/middleware.py
- **Verified:** `tests/api/test_security_hardening.py::test_body_cap_content_length_and_streaming` (fails with the raising version: 400 == 413)
- **Regression guard:** same test. Rule: never signal a body-size violation by raising inside `receive`; FastAPI rewrites it
- **Committed:** not yet

## BUG-007: uvicorn `--proxy-headers --forwarded-allow-ips='*'` trusts the forgeable left-most X-Forwarded-For entry (2026-10-01)

- **Tier:** T1 - rate limits and login lockouts are keyed on client IP
- **Symptom:** Documented start command (`architecture.md` 10.3) made every request on Render share the proxy's IP bucket, and the obvious fix (trust `*`) lets a client choose its own IP by sending `X-Forwarded-For` [reported by security review; helper behaviour verified]
- **Root cause:** uvicorn's `ProxyHeadersMiddleware` rewrites `client` from the left-most entry when all peers are trusted; the left side is client-controlled. Without it, `request.client` is the proxy
- **Fix:** run uvicorn with `--no-proxy-headers` and derive the IP in `core/clientip.py`: the entry `TRUSTED_PROXY_HOPS` from the RIGHT of X-Forwarded-For (what our own proxy appended); fall back to the socket peer when the header is missing/short/invalid
- **Blast radius:** none (pre-release)
- **Files:** backend/app/core/clientip.py, deps.py, middleware.py, README.md
- **Verified:** `tests/unit/test_clientip.py` (4), `tests/api/test_security_hardening.py::test_rate_limit_buckets_per_forwarded_client`
- **Regression guard:** those tests. Rule: never take the left-most X-Forwarded-For value for rate limiting or lockouts
- **Committed:** not yet

## BUG-006: Spec'd disc-centre sunrise is 1-3 min off the Panchang reference; Sade Sati end ignores retrograde dips (2026-10-01)

- **Tier:** T2 - Panchang/Rahu Kaal values shown to users.
- **Symptom:** With `BIT_DISC_CENTER` (spec 5.7) sunrise was late vs Drik Panchang: London 2025-12-25 08:08 vs 08:05, Mumbai 06:58 vs 06:56, Delhi 06:15 vs 06:14; Rahu Kaal shifted by the same. Disc-centre would fail the +-2 min gate at high latitude. Separately, a first Sade Sati end taken at Saturn's first exit from Aries (2029-08) was wrong: Saturn re-enters on retrograde and leaves for good 2030-04-18. [verified]
- **Root cause:** Drik uses the upper limb with refraction (same 1013.25 hPa / 15 C); spec text assumed disc centre. Sade Sati end must be the LAST exit, merging retrograde dips.
- **Fix:** `ephemeris.sun_rise_set` uses the upper limb (documented deviation); `transits.sade_sati_period` merges gaps under 550 days.
- **Blast radius:** None (new feature).
- **Files:** backend/app/astrology/ephemeris.py, panchang.py, transits.py
- **Verified:** `pytest backend/tests/astrology -q` 320 passed; 5 Drik city/dates agree to <=2 min.
- **Regression guard:** `golden/test_panchang.py::test_panchang_matches_drik[*]`, `test_personal_panchang_sadesati.py::test_sade_sati_end_includes_retrograde_return`. Rule: sunrise convention = upper limb; period ends are last exits.
- **Committed:** not yet

## BUG-005: Rolling back the request session expired the auth-loaded User, so the next attribute read raised MissingGreenlet (500) (2026-10-01)

- **Tier:** T1 - concurrency-sensitive write path (chart limit); found during the rebuild before any release
- **Symptom:** Concurrent chart creates at the plan limit returned 500 instead of 403 `CHART_LIMIT_REACHED`; in the test, every request in the batch failed [verified]
- **Root cause:** `app/services/chart_service.py:create_chart` released its read transaction with `await db.rollback()` before the engine computation, and on the limit path built the error after `await db.rollback()`. `AsyncSession.rollback()` expires every loaded instance even with `expire_on_commit=False`. The `User` that `get_current_user` loaded in the same session became expired, and reading `user.subscription_tier` triggered a lazy load outside a greenlet: `sqlalchemy.exc.MissingGreenlet` [verified]
- **Evidence:** I mutated the code back to `await db.rollback(); raise _limit_error(user)` and `tests/api/test_charts.py::test_concurrent_creates_respect_limit` failed with a SQLAlchemy error; with the fix restored it passes
- **Fix:** End read-only transactions with `await db.commit()`, which does not expire instances under `expire_on_commit=False` and still releases the connection before CPU or LLM work. On error paths, build the domain exception before `rollback()`. The same pattern is applied in chart, compatibility, chat and horoscope services
- **Blast radius:** none (pre-release rebuild); no data affected
- **Files:** backend/app/services/chart_service.py
- **Verified:** `pytest tests/api -q` 56 passed; mutation run fails as described
- **Regression guard:** `test_concurrent_creates_respect_limit`, `test_chart_limit`. Rule: never touch an ORM attribute after `session.rollback()`; release a read transaction with `commit()`, not `rollback()`, when request-scoped objects (the current user) must stay usable
- **Committed:** not yet

## BUG-004: Unknown-time chart hid Sun/planet sign changes; node, ayanamsa and input-type defects (2026-10-01)

- **Tier:** T2 - chart calculation output.
- **Symptom:** Found by independent QA. (1) Delhi 2000-03-20, time unknown: Sun Pisces 29.96, `approximate=false`, but the Sun enters Aries 07:35 UT that day; solar whole-sign houses and sidereal rashis flip likewise. (2) True North Node `retrograde=true` with positive speed in 21 of 80 sampled years. (3) str latitude / datetime date / naive `now_utc` raised raw TypeError; a tz-aware `time_of_birth` lost its tzinfo silently. (4) `vedic.ayanamsa_value` was the true value (J2000 23.8532) vs published mean Lahiri 23.8571. [verified]
- **Root cause:** (1) only the Moon was probed at local 00:00/23:59. (2) retrograde forced True for nodes (mean-node convention) on the true-node row. (3) no type validation; `astimezone()` on a naive datetime applies the host zone. (4) the reported value used `FLG_SIDEREAL` without `FLG_NONUT`.
- **Fix:** `chart._probe_day` probes all bodies (tropical, sidereal, nakshatra); per-planet `approximate`/`candidates`, houses flagged when the Sun changes sign, Vedic `house_approximate`. North Node `retrograde` follows speed; `mean_node_retrograde` keeps the convention. `_validate_types` + `require_aware` raise `AstroInputError(INVALID_INPUT)`. `ayanamsa_value` is the mean (JH) value, `ayanamsa_true_value` is the one used; positions are unchanged and equal `swetest -sid1` (nutation cancels), documented in metadata.
- **Blast radius:** None (not in production). Positions unchanged; output additions only.
- **Files:** backend/app/astrology/chart.py, ephemeris.py, timeutil.py, transits.py
- **Verified:** `pytest backend/tests/astrology -q` 300 passed.
- **Regression guard:** `qa/test_qa_attack.py::test_unknown_time_sun_ingress_day_is_flagged_approximate`, `::test_north_node_retrograde_flag_matches_speed`, `::test_bad_types_raise_astro_input_error`; `test_chart.py::test_unknown_time_flags_every_planet_that_changes_sign`, `::test_ayanamsa_reported_mean_matches_jagannatha_hora_convention`. Rule: on unknown time every body is probed across the day, and no emitted flag may contradict emitted numbers.
- **Committed:** not yet

## BUG-003: Non-streaming chat always 503 when gemini-3.8-flash is overloaded and no Anthropic key exists (2026-10-01)

- **Tier:** T2 - LLM routing and budgets; every chat reply failed for users.
- **Symptom:** `generate_chat_reply` raised `LLMUnavailable` on every call. `llm_usage` showed `outcome=failed` with 0/0 tokens at 4.3 s and 12.8 s, and no log said why. A standalone script raised "no configured provider for task chat" instead, because `LLMSettings` read only `GEMINI_API_KEY` while `backend/.env` holds `GEMINI_API_KEY1..3`. [reported by backend-elite, then verified]
- **Root cause:** `gemini-3.8-flash` returns intermittent `503 UNAVAILABLE` ("high demand") on the project's keys. The router retried once, as designed. The chat chain's only fallback was `claude-haiku-4-5`, and with no Anthropic key that model was silently dropped from the chain, so nothing was left (`app/llm/config.py` default `LLM_FALLBACK_CHAT`, `app/llm/router.py::chain`). The breaker was also keyed per vendor, so repeated 503s on one model would have blocked the healthy `gemini-3.5-flash-lite`. Failed attempts recorded only an outcome and logged nothing. [verified]
- **Evidence:** A direct `google-genai` call with the same structured config returned `ServerError 503 ... high demand` for `gemini-3.8-flash`. The identical request to `gemini-3.5-flash-lite` returned STOP with valid JSON, so the schema was not the cause. The live smoke stream test failed and then passed on rerun, which confirms the 503s are intermittent capacity.
- **Fix:** The chat chain is now `gemini-3.8-flash -> claude-haiku-4-5 -> gemini-3.5-flash-lite`, and premium gets the same same-vendor tail. The circuit breaker is keyed by `provider:model`. Every failed attempt logs `llm_attempt_failed` at WARNING, with the error class, status and redacted provider message (keys stripped, no prompt or user text), and stores it in the new `UsageRecord.error`. When no provider is configured, the router raises an actionable `LLMUnavailable` and `configure()` logs it at startup. `LLMSettings` now reads `backend/.env` directly and accepts `GEMINI_API_KEY` or `GEMINI_API_KEY1..5`. The Gemini adapter rotates keys on 429 only, since a 503 is a model capacity problem and is not key-specific.
- **Blast radius:** All non-streaming chat replies in the integration environment returned 503. No data was corrupted, and nothing was persisted for failed replies.
- **Files:** backend/app/llm/config.py, router.py, errors.py, usage.py, service.py, providers/__init__.py, providers/gemini.py, providers/claude.py; tests in backend/tests/llm/test_bug003_provider_failover.py
- **Verified:** `pytest backend/tests/llm -q` 121 passed, 5 skipped. Live run with a synthetic chart: `generate_chat_reply` returned `outcome=ok` (210 words, 8 valid citations, no validator flags); `stream_chat_reply` hit a 503 on 3.8-flash and completed on 3.5-flash-lite.
- **Regression guard:** `test_bug003_provider_failover.py` (`test_default_chat_chain_has_same_vendor_fallback`, `test_primary_503_with_gemini_only_falls_to_flash_lite`, `test_breaker_is_per_model`, `test_no_provider_message_is_actionable`, `test_numbered_keys_from_kwargs_and_env_file`, `test_gemini_rotates_keys_on_429`). Rule: every task chain must keep at least one fallback on a vendor that is actually configured, and every failed provider attempt must leave a redacted cause in logs and `llm_usage.error`.
- **Update 2026-10-01 (live H5 still 503, three more causes found via `llm_usage.error`):** (a) `gemini-3.8-flash` returned valid JSON rejected for `follow_ups.0` over 90 chars: hard caps on soft fields made the whole answer fail. (b) the 503 capacity error above. (c) `gemini-3.5-flash-lite` hit `finish_reason=length` at ~685 tokens: `max_output_tokens=700` is shared with Gemini thinking tokens. Fix: follow-ups, citations, topic and over-long answers are normalised (word-boundary truncate, drop extras, cut at a sentence) in `schemas.py`, while an empty answer, missing fields, bad enums and unknown keys still fail. Truncation is a new `LLMTruncated` error that retries once with double the budget (cap 4096). Chat budget is now 1500 tokens, and prompt `chat@v2` asks for 120-220 words and follow-ups under 80 characters (v1 stays locked). Verified: 6 live chats in a row with a real `compute_natal_chart` chart returned `outcome=ok` (3.8-flash 503, then Flash-Lite).
- **Regression guard (update):** `test_bug003b_soft_fields_and_truncation.py`. Rule: a length cap on a soft field normalises and never fails the answer, and `finish_reason=length` retries with a larger budget before failing.
- **Committed:** not yet

## BUG-002: Births on 1800-01-01 east of Greenwich silently computed on Moshier (2026-10-01)

- **Tier:** T2 - ephemeris engine selection; wrong engine would be stored in chart_data unflagged.
- **Symptom:** Found during engine build: a local 1800-01-01 00:00 birth at lon 179.9 E made `swe.calc_ut` return retflag 260 (MOSEPH) for the Sun while the Moon returned SWIEPH. [verified]
- **Root cause:** The shipped `sepl_18.se1` starts at 1800-01-01 05:45 UT, not 00:00; it ends 2400-01-07 UT (both found by bisection). The spec floor "1800-01-01" was a local date, and +UTC offsets push the UT instant before the file start, where pyswisseph falls back to Moshier without raising. [verified]
- **Evidence:** `swe.calc_ut(swe.julday(1800,1,1,0.0), SUN, FLG_SWIEPH)[1] == 4`; bisection gives the first SWIEPH instant as JD 2378496.7396.
- **Fix:** `timeutil.MIN_DATE = 1800-01-02` (safe for offsets up to +16 h and the unknown-time 00:00 probe) plus a UT-instant guard (`DATE_OUT_OF_RANGE`), and `ephemeris.calc` raises `EphemerisUnavailableError` on any non-SWIEPH retflag, so this can never be silent.
- **Blast radius:** None (engine not yet in production).
- **Files:** backend/app/astrology/timeutil.py, backend/app/astrology/ephemeris.py
- **Verified:** `pytest backend/tests/astrology -q` 291 passed.
- **Regression guard:** `test_timeutil.py::test_date_out_of_range`, `::test_range_edges_compute_on_swieph`, `test_transits_and_engine.py::test_moshier_fallback_is_detected_not_silent`. Rule: every swe call checks `retflag & FLG_SWIEPH`, and accepted dates stay inside the shipped files' UT coverage.
- **Committed:** not yet

## BUG-001: Body exactly on a nakshatra boundary assigned to the previous nakshatra (2026-10-01)

- **Tier:** T2 - nakshatra, pada and dasha lord are stored chart facts.
- **Symptom:** Found by golden test during engine build: sidereal 120.0 (0 Leo, start of Magha) came out as Ashlesha pada 4, and 240.0 (start of Mula) as Jyeshtha 4. The dasha starting lord was Mercury rather than Ketu. [verified]
- **Root cause:** `idx = int(lon // (40/3))`: 40/3 rounds up to 13.333333333333334 in IEEE double, so `120 // (40/3) == 8.0`. Any divide-by-span formula has this problem at exact boundaries. [verified]
- **Evidence:** `python -c "print(120//(40/3))"` prints `8.0`.
- **Fix:** Multiply before dividing: pada index `int(lon * 108 / 360)`, nakshatra fraction `lon * 27 / 360` (exact at every boundary that is a multiple of 10/3 deg).
- **Blast radius:** None (engine not yet in production). It would have affected about 1 in 10^5 random positions, but every chart computed for a body exactly at a boundary.
- **Files:** backend/app/astrology/vedic.py (nakshatra_of), backend/app/astrology/dasha.py (birth_balance)
- **Verified:** `pytest backend/tests/astrology -q` 291 passed; the boundary tests failed before the fix.
- **Regression guard:** `test_vedic.py::test_nakshatra_boundaries[120.0-9-1]`, `[240.0-18-1]`, `test_dasha.py::test_starting_lord_by_nakshatra[240.0-Ketu]`. Rule: never divide a longitude by a non-representable span (40/3, 10/3); scale by an integer ratio first.
- **Committed:** not yet
