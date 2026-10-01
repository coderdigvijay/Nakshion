# Nakshion RAG runbook

Owner: ai-genai-specialist. Code: `backend/app/rag/`. Eval: `backend/evals/rag/`. Spec: `docs/llm-integration.md` §3 [4], §6.

## 1. What runs where

| Piece | Where | Notes |
|---|---|---|
| Chunking, provenance, key generation | offline (`python -m app.rag.ingest`) | never in the web process |
| Embedding model (bge-small-en-v1.5) | web process, lazy, ~280 MB RSS | `EMBEDDINGS_RUNTIME=off` removes it |
| Query planning (glossary, phonetic bridge) | web process, pure Python | no model |
| Hybrid search + RRF fusion | Postgres (one round trip) | pgvector + weighted tsvector |
| Boosts, diversity, token cap | web process | |
| Result cache | Redis `rag:r:{sha1}` 6 h | keyed on index version, so a re-index invalidates it |

## 2. Quality: how to measure and what we measured

Eval set: `backend/evals/rag/queries.jsonl`, **204 labelled queries** (EN 69, HI 68, Hinglish 67). 48 are generated from **real engine charts** (`evals/fixtures/real_charts.json`, computed by `app.astrology`: Delhi, Mumbai, London, New York, Sydney, Tromso (high latitude), Berlin and Chennai (unknown time), Kolkata, Bengaluru) from each chart's own Moon nakshatra, Sun sign, Mahadasha, Saturn house and a natal aspect. The other 156 are topical questions (houses, nakshatras, dashas, yogas, transits, remedies, compatibility, career, love, health, daily guidance, ...) written in three languages with the same gold. Gold is a set of `(file, heading regex, grade)` matchers, so it survives re-chunking; the builder refuses a query whose gold resolves to nothing.

Three splits: `dev` (used while tuning), `holdout` (written after the glossary was frozen, but its failures then drove the phonetic bridge, so it is no longer blind), `holdout2` (**written after everything was frozen; the generalisation estimate**).

```bash
cd backend
python -m evals.rag.build_queries                        # regenerate queries.jsonl (deterministic)
RAG_EVAL_DATABASE_URL=postgresql+asyncpg://.../astroai_rag_scratch \
python -m evals.rag.run --label mytry --config v2 --embedder bge-small --worst 8    # scratch DB only (name must contain "scratch")
python -m evals.rag.answer_eval --label mytry --per-lang 8   # live LLM, needs GEMINI_API_KEY*; scratch DB index
pytest tests/rag/test_eval_gate.py                       # CI gates; DB gate runs when RAG_EVAL_DATABASE_URL is set
```

### Retrieval, ablation ladder (all 204 queries, bge-small, pgvector scratch DB, 354 chunks)

| Step | hit@5 | R@5 | MRR | nDCG@10 | hi hit@5 | blind holdout2 hit@5 | p50 / p95 ms |
|---|---|---|---|---|---|---|---|
| Baseline (pre-change code, 108 dev queries) | 0.213 | 0.108 | 0.126 | 0.091 | 0.17 | n/a | 38 / 87 |
| A0 legacy parameters on the new engine | 0.167 | 0.081 | 0.109 | 0.083 | 0.09 | 0.00 | 10 / 17 |
| A1 + factor keys only when relevant | 0.627 | 0.472 | 0.496 | 0.459 | 0.26 | 0.58 | 10 / 16 |
| A2 + Hindi/Hinglish glossary | 0.858 | 0.657 | 0.703 | 0.644 | 0.71 | 0.69 | 13 / 17 |
| A3 + key terms in full-text | 0.858 | 0.664 | 0.705 | 0.646 | 0.69 | 0.69 | 13 / 20 |
| A4 + heading/topic/tier boosts | 0.902 | 0.718 | 0.800 | 0.725 | 0.75 | 0.75 | 13 / 18 |
| A5 + diversity (heading, near-dup, per-file) | 0.907 | 0.715 | 0.801 | 0.718 | 0.76 | 0.75 | 13 / 19 |
| **A6 + phonetic bridge (shipped)** | **0.956** | **0.760** | **0.847** | **0.760** | **0.91** | **0.86** | **12 / 18** |

hit@k = any relevant chunk in the top k. R@k = relevant in top k / min(|relevant|, k). Parameter sweeps around A6 (key weight, heading boost, FTS weight, per-file cap, gloss weight) moved nDCG by at most ±0.02, so the defaults were left alone.

### Decisions, with measurements (macOS arm64, 1 thread; app import alone is 113 MB)

| Option | hit@5 | nDCG@10 | RSS after load | Latency | Decision |
|---|---|---|---|---|---|
| **bge-small-en-v1.5 + glossary (shipped)** | 0.956 | 0.760 | **396 MB** | query embed 13-30 ms | keep |
| multilingual-e5-small (int8) + glossary | 0.941 | 0.747 | 693 MB | 7 ms | **reject**: no gain, does not fit 512 MB |
| paraphrase-multilingual-MiniLM-L12 + glossary | 0.899 (older run) | 0.654 | 645 MB | 27 ms | **reject** |
| e5-small without glossary | 0.716 | 0.542 | 693 MB | | Hindi hit@5 0.34: a multilingual model alone does not fix Hindi |
| `EMBEDDINGS_RUNTIME=off` (keys + full-text) | 0.907 | 0.728 | ~113 MB | 7 ms | **memory-guard mode**, -5 points hit@5 |
| + cross-encoder rerank (ms-marco MiniLM-L6) | 0.966 | 0.804 | 538 MB (+145) | **+490 ms p50** (15 docs) | **off by default**: +0.04 nDCG is not worth 0.5 s and +145 MB (several seconds on a 0.1 vCPU). `RAG_RERANK_MODEL=Xenova/ms-marco-MiniLM-L-6-v2` turns it on |
| + hide tier-3 notes (`RAG_EXCLUDE_REVIEW=1`, optional) | 0.961 | 0.761 | | | the shipped default indexes everything; hit@5 0.946 with all 366 chunks vs 0.956 without 12 case-study chunks |

If the Render free instance exceeds its RAM budget in a load test, set `EMBEDDINGS_RUNTIME=off`. On Linux x86 the RSS of the same model is typically lower than the macOS numbers above; re-measure on Render before relying on either figure.

### Answer level (live Gemini, 24 answers + 4 poisoned-chunk + 8 safety prompts, real charts, production retriever)

| Metric | Result |
|---|---|
| Groundedness (claim checker on the final text) | 24/24 |
| First-draft grounding violations (repaired before the user sees them) | 1/24 (4.2 %) |
| Citation validity (cited ids exist and were shown) | 100 % |
| Answers that cite a retrieved note when notes were provided | 100 %; every source chip has a title |
| Uncited chart claims (soft flag) | 0 % |
| "Chart facts beat RAG": poisoned chunk obeyed (wrong placement, "buy a sapphire", prompt-leak request, fake CHART FACTS header) | 0/4 |
| Safety prompts handled (death, child sex, paid remedy, injection, medical, crisis, caste, certainty) | 8/8 |
| Latency p50 / p95 (includes provider 503 fallbacks) | 4.2 s / 13.0 s |
| Cost per answer | $0.0023 at list prices (free tier in dev) |

The optional LLM-judge groundedness score is not run (it needs an Anthropic key); `evals/run.py --judge` covers answer quality.

## 2b. Researched knowledge files (`kb_*`, 29 files) and the 773-chunk corpus

The corpus grew from 366 to **773 chunks** (393 from the 29 researched files: Ashtakoota and doshas, panchang and muhurta, gochara, dasha foundations / all 81 antardasha pairs / Sade Sati, house lords, planets in houses, yogas, dignity, divisional charts, remedies, and a Hindi/Hinglish glossary, core topics and phrasebook). Raw downloads in `knowledge_sources/` are never indexed.

**Registration.** Every file has an entry in `app/rag/sources.yaml` generated from its YAML front-matter. Ingestion also reads front-matter itself (title, tradition, system, tier, language, confidence, school_notes, sources), so a future file needs no manual entry; a malformed block or an invalid `system`/`tier` logs a warning and falls back to defaults. `sources` are counted, never stored, never shown; URLs are stripped from notes.

**Chunking for the new structures.** Tables over 340 tokens are split into row groups with the header repeated and the first/last row named in the heading path (`Saturn Mahadasha (19 years) - Antardashas > rows Saturn-Saturn to Saturn-Sun`); every one of the 81 pairs is in exactly one chunk. House-lord sections (one per lord, 12 rows) and planet-in-house entries (at most 4 per chunk) stay addressable by heading. Western exaltation degrees (`planets.md`) are isolated in their own `western`-tagged chunk (`meta.degree_system = western`), so a Vedic user is never given them; the Vedic degrees come from `kb_chart_planets_in_signs_dignity`.

**Query planning.** The planner now (a) folds the Devanagari/Roman glossary file into its vocabulary, (b) expands Hinglish questions through the phrasebook ("meri shaadi kab hogi" -> 7th house, 7th lord, Venus, Jupiter, dasha, navamsha), (c) searches Devanagari words directly (the glossary rows are Hindi text) with Hindi suffixes stripped, (d) treats "7th lord in the 12th house" as a request for the 7th lord's own section, and (e) prefers glossary-style chunks for "what does X mean". Row-level tables are penalised unless the question names at least two of their heading/row terms.

**Confidence.** `meta` carries `confidence`, `schools_differ` (only on chunks that actually describe a disagreement), `unverified` (chunk contains `[unverified]`). Ranking: high +0.002, low -0.002, unverified -0.0015, tier as before. The model sees `confidence="low"`, `unverified="true"` and `schools="differ"` on the note and must write "some sources say" / "traditions differ"; a validator (`hedge`) repairs an answer that cites such a note without hedging, and accepts it after one failed repair rather than failing the reply.

**Ingest.** Re-ingest now detects metadata-only changes and updates them in place (`metadata_updated`, no re-embedding); text changes still build version n+1 beside the live one (dev: version 5, previous 4 kept for `--rollback`).

### Retrieval, 409 queries (EN 136, HI 137, Hinglish 136), pgvector scratch DB, bge-small

| Set | n | hit@5 | nDCG@10 |
|---|---|---|---|
| Old 204 queries, ORIGINAL gold, before (366 chunks) | 204 | 0.946 | 0.760 |
| Old 204 queries, ORIGINAL gold, after (773 chunks) | 204 | 0.868 | 0.670 |
| Old 204 queries, gold extended with the new files | 204 | 0.90 (dev split) | 0.60 |
| **Blind holdout 3** (written from headings before any retrieval), first measurement | 163 | 0.779 | 0.514 |
| Holdout 3 after the planner fixes it exposed (no longer blind) | 163 | 0.86 | 0.56 |
| **Blind holdout 4** (written after the fixes were frozen) | 42 | **0.833** | 0.60 |
| All | 409 | 0.885 | 0.613 |

By language (hit@5): EN 0.926, Hinglish 0.89, Hindi 0.839. Weakest topics: compatibility 0.67, dignity 0.67, nakshatras 0.69, aspects 0.74. p50/p95 latency 23/47 ms. The old-set drop is displacement, not breakage: with five slots, the new files (for example the Mars-Mahadasha table or the remedies file) now outrank the old chunks the original gold named. The gate thresholds in `tests/rag/test_eval_gate.py` were re-set to the measured values with ~3 points of margin.

### Live answer spot check (dev index, 10 questions the new files cover)

Grounded 10/10 after repair, citation valid 9/10 first draft, cited a retrieved note in 8/10, no `[unverified]` marker stated, no raw-token leak, no safety hit; low-confidence Yogini-dasha answer was hedged. Memory: planner data adds ~8 MB; RSS is 121 MB with `EMBEDDINGS_RUNTIME=off` and 395 MB with the local model (both unchanged by the bigger corpus, which lives in Postgres: 773 chunks + 2,952 keys is a few MB on Neon).

## 3. Operations

```bash
python -m app.rag.ingest --dry-run                          # chunk, tier, duplicate stats; no DB
python -m app.rag.ingest --status   --database-url "$DATABASE_URL"
python -m app.rag.ingest            --database-url "$DATABASE_URL"   # incremental, zero-downtime
python -m app.rag.ingest --rollback --database-url "$DATABASE_URL"   # swap back to the previous version
python -m app.rag.keys --out keys.txt                       # the factor kb_keys that get pre-embedded
python -m app.rag.ingest --kb-keys-file keys.txt ...        # or let ingest generate them (default)
```

- **Run 008 first.** `kb_chunks` had `PRIMARY KEY (id)`, so a re-index (same ids, new `index_version`) failed with a unique violation. Migration 008 makes it `(index_version, id)`, adds `meta JSONB` and a heading-weighted tsvector. The code also works against the 007 schema for reads.
- **Deploy order for a corpus or chunking change:** `--dry-run`, ingest to the scratch DB, run `evals.rag.run` and compare to the table above, then ingest to prod. The indexer copies unchanged chunks, embeds only new ones, runs a 4-query smoke test, flips the version and keeps the previous one. Roll back with `--rollback` (instant).
- **Startup:** call `await retriever.self_check()` once and log it. It reports no active version, an empty index, an embedding-model mismatch (index vs runtime) and a failing probe query. A failed check never blocks the app; chat degrades to chart facts.
- **Settings:** `EMBEDDINGS_RUNTIME=local|off`, `EMBEDDING_MODEL`, `RAG_EXCLUDE_REVIEW`, `RAG_RERANK_MODEL`, `RAG_TIMEOUT_S` (3 s), plus `rag_top_k` / `rag_token_cap` / `rag_candidates`.
- **Resilience:** per-request timeout, in-process circuit breaker (5 failures in 60 s opens it for 30 s), Redis cache failures ignored, store failure returns no chunks and `metadata.rag.degraded=true`.
- **Metrics:** `retriever.metrics.snapshot()` returns request count, empty rate, degraded, cache hit rate, errors, timeouts, p50/p95 latency and rerank reorder rate. Logs (`rag_retrieve`) carry counts and latencies only, never question text, birth data or chunk text.
- **Alerts to set:** empty-result rate above 5 %, degraded above 2 %, p95 above 250 ms, any `rag_error`.
- **Cache invalidation:** nothing to do on re-index (the version is part of the key). After editing `sources.yaml` without re-indexing, the cache key does not change, so flush `rag:r:*`.

## 4. Provenance note (study use)

Decision by the owner: this is a study project, so **every knowledge file is indexed** (773 chunks now, including `famous_charts_analysis.md` and the "Famous Examples" sections, as tier 3). Nothing is excluded or deleted.

Facts recorded in case the project is ever made public or commercial:

- All 26 files were scanned: no long verbatim quotation, no blockquote, no archaic prose. Every `books_*` file is a 1,600-3,000 word "Key Teachings Synthesized" paraphrase. We do not hold the source books, so close paraphrase cannot be ruled out by a script.
- `books_ptolemy_tetrabiblos.md` and `books_lilly_christian_astrology.md` summarise public-domain works (the author is named on chips).
- `books_arroyo_chart_interpretation.md`, `books_greene_saturn.md` and `books_rudhyar_humanistic.md` follow the structure of in-copyright books by named authors (two living). They are tier 3, flagged `review`, shown under a generic title, and `RAG_EXCLUDE_REVIEW=1` hides them without re-indexing.
- `famous_charts_analysis.md` and the "Famous Examples" sections name real people. They are tier 3 (lowest retrieval weight).
- The Ashtakoota tables in the engine are CC BY-SA 4.0 (`data/ashtakoota.py`); attribution belongs on a legal page if the app is published.
- Display rules stay on regardless: citation chips show source titles only, no author for in-copyright works, and the API never returns chunk text or long verbatim passages to the client.

## 5. Known limits

- Gold covers the topics in the corpus; there are no queries about things the KB does not contain (those should retrieve low-score, off-topic chunks; there is no "I don't know" threshold yet).
- The glossary is hand-built; the phonetic bridge generalises to unseen loanwords but not to translated terms (e.g. ग्रहण needed a glossary entry). Hindi hit@5 is 0.91 vs 0.97 for English.
- `derive_factors` kb_keys come from `app/llm/facts.py` until the engine's `select_factors` lands; `tests/rag/test_keys.py` fails if either producer emits a key the vocabulary lacks.
- Retrieval quality was measured at 354 chunks; revisit the exact-scan decision (no HNSW) above ~5,000 chunks.
