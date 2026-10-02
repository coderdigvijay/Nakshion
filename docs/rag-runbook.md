# Nakshion RAG runbook

Owner: ai-genai-specialist. Code: `backend/app/rag/`. Eval: `backend/evals/rag/`. Spec: `docs/llm-integration.md` §3 [4], §6.

## 1. What runs where

| Piece | Where | Notes |
|---|---|---|
| Chunking, provenance, key generation | offline (`python -m app.rag.ingest`) | never in the web process |
| Embedding model (bge-small-en-v1.5 int8, or `minilm-l6-q`, section 2e) | web process, lazy, loads in a background thread, per-query budget 0.4 s | +125 MB (`minilm-l6-q`) to +290 MB (`bge-small`) RSS; `EMBEDDINGS_RUNTIME=off` removes it |
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

## 2d. Off-mode (keys + full-text) retrieval on the independent blind set (BUG-027)

Independent set: 121 answerable + 10 trap queries written without seeing the retriever. Tuned on EVEN ids only; ODD ids are the blind half.
`backend/evals/rag_independent/queries.jsonl`; run through `evals.rag.run` with `load_queries` filtered by id parity.

| Config (hit@5) | even (tuned) | odd (blind) |
|---|---|---|
| off, before (head_boost 0.006, no IDF) | 0.564 | 0.651 |
| off, after | 0.818 | 0.818 |
| local bge-small, after | 0.818 | 0.879 |

Per topic (off, even / odd, before > after): dignity 0.29>0.64 / 0.38>0.62; matching 0.65>0.85 / 0.76>0.90; nakshatras 0.57>0.86 / 0.69>0.88; panchang 0.67>1.00 / 1.00>1.00; sade_sati 1.00 / 0.50>0.75; gochara and yogas unchanged. By language (even / odd): en 0.50>0.81 / 0.76>0.97; hi 0.62>0.88 / 0.55>0.65; hg 0.62>0.77 / 0.59>0.76. The 204-query regression set (off): hit@5 0.831 > 0.863.

What changed: Postgres `ts_rank_cd` has no IDF, so Moon/Rahu/sign-heavy chunks won every OR query. `apply_idf` (app/rag/query.py) uses per-version document frequencies (`PgVectorStore.term_df`, cached in-process): terms in >12% of chunks leave the OR list, an AND list over the rare terms (<=10%, else the rarest three), an OR list of rare terms, and adjacent question words as `a <-> b` phrases (English only, weight 2.0). `head_boost` 0.006 > 0.02. The in-memory twin (`MemoryStore`) deliberately has no `term_df`, so its gates are unchanged.

Even-half failure buckets (before): about 23 misses, nearly all genuine defects (the answer chunk exists: Nadi/Bhakoot cancellations, Graha Maitri, combustion, Ketu-ruled nakshatras, sutak). Acceptable uncredited alternatives: Rahu exaltation (bphs/dignity notes), Ketu nakshatras (the bphs dasha table lists Ketu: Ashwini, Magha, Mula). Remaining misses are mostly Hindi/Hinglish (glossary bridge) and Rahu/Ketu-heavy questions. No missing-knowledge topics found on the even half.

Low-confidence signal: `RetrievalResult.low_confidence` (best fused+boosted score below `low_conf_off` 0.05 / `low_conf_local` 0.06, or no hit; never set when retrieval degraded). Traps: off flags 5/10 at 3/121 answerable (2.5%); local flags 5/10 at 7/121 (5.8%). Several traps share vocabulary with the KB and score as high as answerable queries, so lexical thresholds cannot catch them all; the answer layer must also keep its "cite only what the notes say" rule. Answer layer change needed (app/llm, not edited): in `ChatResponder._prepare` read `r.low_confidence` from `retrieve_ex`, put it in `rag`, and when true add one context line "No sourced note matches this question: say so and answer only from CHART FACTS or general, hedged knowledge".

## 2e. Local query embeddings on a 512 MB instance (BUG-028)

Question: can local query embeddings fit Render's 512 MB free instance? **Measured on macOS arm64 (Python 3.14, onnxruntime 1.24, 1 ONNX thread, arena off). Linux and the 0.1 vCPU box are NOT measured**; expect Linux RSS to be somewhat lower and latency several times higher. RSS is the full process: `import app.main` (120 MB) + `fastembed` import (~45 MB) + model session + 200 distinct queries; macOS compresses pages, so "peak" is `ru_maxrss`, stable to +-1 MB over 3 runs. Latency is p50 / p95 over 200 distinct queries on an otherwise quiet laptop (these swing 2-4x when other jobs run).

| Model (spec key) | disk MB | dim | full-process peak RSS | p50 / p95 ms | cold load (warm page cache) |
|---|---|---|---|---|---|
| **sentence-transformers/all-MiniLM-L6-v2 int8** (`minilm-l6-q`) | 23 | 384 | **245** | 3.4 / 8 | 0.35 s |
| snowflake-arctic-embed-xs fp32 (`arctic-xs`) | 90 | 384 | 350 | 9 / 20 | 0.4 s |
| all-MiniLM-L6-v2 fp32 (`minilm-l6`) | 90 | 384 | 350 | 9 / 20 | 0.4 s |
| bge-small-en-v1.5 fp32 (`bge-small-fp32`) | 133 | 384 | 410 | 17 / 39 | 0.5 s |
| **bge-small-en-v1.5 int8 (`bge-small`, the current default)** | **66** (the old "~130 MB fp32" note was wrong: fastembed ships the int8 file) | 384 | 416 | 17 / 39 | 0.45 s |
| multilingual-e5-small int8 (`e5-small`) | 118 + 17 tokenizer | 384 | 730 | 7 / 9 | 1.0 s |
| paraphrase-multilingual-MiniLM-L12 int8 (`minilm-ml`) | 235 + 17 | 384 | 880 | 16 / 22 | 1.0 s |
| minishlab/potion-base-8M (static, 256-d, not indexed) | 30 | 256 | 292 | 7 / 8 | |

Findings: (1) quantising bge-small does not help memory (fp32 410 vs int8 416): ONNX Runtime's session overhead dominates, not the weights. (2) Arena off (`enable_cpu_mem_arena=False`, now the default) lowers the settled RSS after load (bge-small 376 > 309 MB after 200 queries) but not the peak that decides an OOM kill; graph-optimisation level and prepacking options changed nothing meaningful. (3) The multilingual models need 700-880 MB (a 250k-token vocabulary is expanded to fp32 by the runtime) and gave no Hindi gain (below). (4) Only `minilm-l6-q` is under the ~330 MB budget: 245 MB measured, 85 MB of headroom, plus the ~25 MB the web process adds after the first chat (182 vs 157 MB in `docs/deployment.md`): about 270 MB steady state, 240 MB under 512 MB.

Retrieval, independent blind set (121 answerable queries, `A6-phonetic`, current retriever, scratch DB `astroai_rag_scratch_q`; `python -m evals.rag_independent.run_halves --embedder <key> --label <x>` builds the index, scores EVEN ids / ODD ids / the 409-query regression set with the model, then the same index with the model off). One query is 1.8 points on the even half and 1.5 on the odd half: differences under ~3 points are noise.

| Index / runtime | even hit@5 | odd hit@5 | even nDCG@10 | odd nDCG@10 | 409-set hit@5 / nDCG |
|---|---|---|---|---|---|
| keys + full-text, bge-small key vectors | 0.818 | 0.818 | 0.548 | 0.556 | 0.863 / 0.595 |
| keys + full-text, minilm-l6-q key vectors | 0.782 | 0.818 | 0.534 | 0.552 | 0.870 / 0.600 |
| **local minilm-l6-q** | 0.818 | 0.833 | 0.583 | 0.590 | 0.895 / 0.639 |
| local arctic-xs | 0.818 | 0.864 | 0.579 | 0.594 | 0.912 / 0.636 |
| local minilm-l6 fp32 | 0.800 | 0.818 | 0.561 | 0.587 | 0.902 / 0.644 |
| local bge-small (current) | 0.818 | 0.879 | 0.589 | 0.599 | 0.919 / 0.643 |
| local bge-small fp32 | 0.818 | 0.879 | 0.585 | 0.596 | 0.919 / 0.643 |
| local e5-small (multilingual) | 0.818 | 0.849 | 0.558 | 0.581 | 0.909 / 0.650 |
| local minilm-ml | 0.782 | 0.818 | 0.555 | 0.588 | 0.890 / 0.636 |

By language, hit@5 even / odd: off en 0.77 / 0.97, hg 0.69 / 0.76, hi 0.88 / 0.65. minilm-l6-q: en 0.81 / 0.97, hg 0.77 / 0.82, hi 0.88 / 0.65. bge-small: en 0.81 / 1.00, hg 0.77 / 0.82, hi 0.88 / 0.75. e5-small (multilingual): hi 0.88 / 0.65. A multilingual model does not fix Hindi; the planner's glossary and phonetic bridge do. By topic the gain is concentrated in nakshatras (even 0.71 > 0.86) and dignity (odd 0.62 > 0.75 minilm-l6-q, 0.81 bge-small); matching, panchang, yogas and sade_sati do not move. On the 409 set minilm-l6-q helps planets (0.56 > 0.89), career, gochara and houses, and loses nakshatras (1.00 > 0.85) and jaimini.

**On the English-heavy sets the case for local embeddings is much smaller than BUG-027 recorded (the Hindi/Hinglish exam below reverses this)** (0.61-0.70 off vs 0.785 local): after the query-planning changes the off baseline is 0.82 / 0.82 and bge-small adds +0.00 / +0.06 hit@5, +0.04 nDCG@10; `minilm-l6-q` adds +0.04 / +0.02 hit@5, +0.05 / +0.04 nDCG@10 and +0.025 hit@5 / +0.039 nDCG on the 409 set, at +125 MB (not +290). It gives up 0.00 / 0.05 hit@5 against bge-small, but the loss in nDCG is 0.006 / 0.009 and in the 409-set 0.024 hit@5.

**Fresh blind Hindi/Hinglish set (final exam, `evals/rag_independent_hi`, 63 answerable, each configuration run once, nothing tuned; `python -m evals.rag_independent_hi.run_final --embedder <key>`).**

| Config | hit@5 | hit@10 | MRR | nDCG@10 | Hindi (26) | Hinglish (37) |
|---|---|---|---|---|---|---|
| keys+FTS (index of bge-small / minilm-l6-q / arctic-xs) | 0.682 / 0.698 / 0.714 | 0.76-0.78 | 0.50-0.52 | 0.44-0.45 | 0.62-0.65 | 0.73-0.76 |
| local bge-small | 0.809 | 0.857 | 0.612 | 0.540 | 0.69 | 0.89 |
| **local minilm-l6-q** | **0.809** | 0.825 | 0.610 | 0.530 | **0.73** | 0.86 |
| local arctic-xs | 0.778 | 0.841 | 0.603 | 0.526 | 0.65 | 0.86 |

minilm-l6-q recovers +0.111 of bge-small's +0.127 hit@5 (87%) and +0.077 of +0.088 nDCG (88%) at 245 MB instead of 416 MB. Per topic detail is in `evals/rag_independent_hi/final_*.json`. Earlier English-heavy sets showed little gain because the keys+FTS planner already handles English; the gain is in Roman/Devanagari Hindi, which is the audience that matters.

**Gated mode** (embed only when the query is non-English or keys+FTS is `low_confidence`): on this set the gate opened for 62 of 63 queries, so hit@5 is identical to always-local (0.809) and there is no saving; latency is worse in the harness (p95 73 vs 31 ms) because it runs the off pass first. Gating does not reduce RSS once the model is loaded and brings nothing for a Hindi audience; **not adopted**. Its saving on English traffic was not measured.

**Decision: switch on.** `render.yaml` now defaults to `EMBEDDING_MODEL=minilm-l6-q`, `EMBEDDINGS_RUNTIME=local`. Memory: 245 MB peak measured (macOS arm64) + ~25 MB after the first chat = ~270 MB; with a 25% safety margin ~340 MB of 512 MB. Linux is unmeasured (read `/proc` RSS after deploy, and keep the `off` rollback). Cold start: model load 0.35 s warm cache here, estimated 3-6 s on 0.1 vCPU, in a background thread; requests in that window and any query over 0.4 s run keys+FTS (the quality of today's production). **Order matters: re-ingest BEFORE the deploy**, because chunk and key vectors from two models are not comparable.

**Switch procedure (`minilm-l6-q`, all 384-d, so no schema change).**
1. `cd backend && python -m app.rag.ingest --model minilm-l6-q --force --database-url "$MIGRATION_DATABASE_URL"` (run from a laptop with the Neon direct URL; about 3-5 minutes; check with `--status`). This embeds 776 chunks and 2,952 keys into a new `index_version` (the previous one stays for `--rollback`) and records `embedding_model=sentence-transformers/all-MiniLM-L6-v2@int8`. Ingest refuses to activate when fewer key vectors than keys were produced. Key generation is unchanged (`python -m app.rag.keys --out keys.txt`, then `--kb-keys-file keys.txt`, or the default generated set).
2. Set `EMBEDDING_MODEL=minilm-l6-q` (a spec key or the full recorded name both work) and `EMBEDDINGS_RUNTIME=local`; the build then bakes the 23 MB model into `FASTEMBED_CACHE_PATH` (`scripts/build_check.py` uses the same loader as the app).
3. Check `/health/ready` (`rag.ok`) and the memory graph for a day. Rollback is one env var (`EMBEDDINGS_RUNTIME=off`); the keys in the index are then minilm vectors, which are used only through the stored key vectors.
Never change `EMBEDDING_MODEL` without step 1: vectors from two models are not comparable and `self_check` only reports the mismatch (open item for the retriever owner: call `embedder.disable(...)` in `self_check` on a mismatch).

**Cold start and fallback (`app/rag/embeddings.py`).** The model is lazy: nothing loads at boot, `/health/live` never touches it. On the first retrieval a worker thread loads it once (0.35 s with a warm page cache on this laptop; **estimate 3-6 s on Render's 0.1 vCPU with a cold disk, unmeasured**) and the request never waits for it past the budget: `EMBED_QUERY_TIMEOUT_S` (default 0.4 s, `0` disables) covers load plus inference. Over budget, while loading, after a failed load (5 minute back-off), after three consecutive timeouts (30 s back-off) or after `embedder.disable(...)`, `embed_queries` returns `[]`; the retriever zips it against its plan, so that request runs on pre-embedded keys + full-text (`stats["n_vec"] == 0`, `embedder.stats["degraded"]` increments, `EMBED_DEGRADED` is set for direct callers). Cached queries are always served. Chat never fails because of the embedder. Ingest and evals build the embedder through `make_embedder`, which has no time limit.

### Hindi/Hinglish round (BUG-027)

Changes (all query-side; no KB text or index change, no alias lines at ingest): `glossary.norm` folds ZWJ/ZWNJ and chandrabindu into anusvara (plus the existing nukta fold); `canon_spelling` maps Roman variants to the KB spelling (uttra bhadrapad, poorva, mahadasa, nakshat, sani, gun milan, sade saati...); glossary entries for uch/neech/rajju/vedha/swami; Roman skeleton match (`phonetic.match_roman_all`) for unknown Hinglish tokens only. Tuned on even-id Hindi/Hinglish queries (hit@5 unchanged at hi 0.88 / hg 0.77, nDCG 0.548>0.566); the 204-query set 0.863>0.866.

Fresh blind set `evals/rag_independent_hi` (63 answerable), run once: off hit@5 0.73 hg / 0.62 hi; local 0.89 hg / 0.69 hi. Weakest topics off: houses 0.0, dasha 0.44. Hindi remains the ceiling in off mode; local embeddings help Hinglish most, Hindi little (English-only bge-small).

Eval harness and gates set `EMBED_QUERY_TIMEOUT_S=0` (harness and tests only) so a cold model is not cut off by the production 0.4 s guard. `self_check` disables the embedder on an index/model mismatch; results produced while the embedder was degraded are not cached.

### Houses 0.0 / dasha 0.44 diagnosis (BUG-027, development diagnostic on the spent fresh set)

Not a chunking or label problem: the gold chunks exist and are reachable (`saturn-in-the-houses-saturn-in-the-9th-house-saturn-in-the-10th-house`, `saturn-mahadasha-19-years-antardashas`). Three systematic causes: (1) IDF treated "saturn" (32% of chunks) and "house" as noise although planet + house together ARE the heading; (2) untranslated Hinglish function words ("kaisa", "rehta") looked rare and dominated the OR/AND lists; (3) pair headings ("Saturn-Venus" rows, "7th lord in each house") need phrase matching. Fixes: planets are never dropped as common; Roman tokens that are not KB heading words, planets, signs or sound-alikes are dropped for Hinglish; new `f:a` anchor list (`planet <3> 10th`, `7th <-> lord`, `a <-> b` for dasha pairs, weight 2.0).

Off-mode hit@5 after: even 0.818 (nDCG 0.566>0.529), odd 0.818>0.849, 204-query set 0.866>0.887, fresh Hindi diagnostic 0.68>0.76 (houses 0.0>0.8, dasha 0.44>0.56). The fresh set is spent as a blind set.

## 2f. Final exam (`evals/rag_final`, 90 answerable + 12 traps; EN 45, HI 23, HG 22; independent labeller; run once per configuration, nothing tuned)

`python -m evals.rag_final.run_final --embedder <key>`; JSON in `evals/rag_final/final_*.json` (per-query rows, top-5 headings). Current retriever (anchor lists, named planets kept, Hinglish filler dropped, low_confidence), scratch DB `astroai_rag_scratch_q`, macOS arm64.

| Config | hit@5 | hit@10 | MRR | nDCG@10 | hit@5 en / hi / hg | traps flagged low_confidence | false positives on answerable | p50 / p95 ms |
|---|---|---|---|---|---|---|---|---|
| keys+FTS (minilm-l6-q index) | 0.756 | 0.800 | 0.611 | 0.585 | 0.82 / 0.74 / 0.64 | 0/12 | 2/90 | 39.7 / 74.2 |
| **local minilm-l6-q** | 0.800 | 0.833 | 0.647 | 0.617 | 0.87 / 0.74 / 0.73 | 0/12 | 5/90 | 18.7 / 51.1 |
| keys+FTS (bge-small index) | 0.767 | 0.822 | 0.625 | 0.601 | 0.82 / 0.74 / 0.68 | 0/12 | 2/90 | 39.2 / 75.0 |
| local bge-small (reference) | 0.822 | 0.856 | 0.676 | 0.641 | 0.84 / 0.83 / 0.77 | 0/12 | 4/90 | 38.0 / 66.2 |

By topic, hit@5 (minilm-l6-q off > local): dasha 0.87>0.80, dignity 0.88>0.88, divisional 0.80>1.00, houses 0.58>0.58, matching 0.75>0.83, nakshatras 0.90>0.90, panchang 0.88>0.88, remedies 0.40>0.60, sade_sati 0.75>0.88, yogas 0.57>0.71. Weak either way: houses 0.58, yogas 0.57-0.71, remedies 0.4-0.6.

Reading: local minilm-l6-q adds +0.044 hit@5 and +0.032 nDCG@10 over keys+FTS (Hinglish +0.09, English +0.05, Hindi 0); bge-small adds +0.055 / +0.04 and is the only one that helps Devanagari Hindi (0.74 > 0.83). With the Hindi/Hinglish exam (+0.11) every fresh blind set favours local. Latency stays inside the 250 ms alert on a laptop. **Traps: 0 of 12 flagged by `low_confidence` in any configuration**, so that signal does not detect no-answer questions; it fires on 2-5 of 90 answerable (2-6%). The answer layer must keep its "cite only what the notes say" rule.

Ten worst misses (minilm-l6-q local), categorised. Retrieval/planner defects (7, NOT fixed against this set): `dasha:01:hg` (phrasebook chunk outranks "The order and years"); `dasha:03:hg` ("AD" abbreviation unknown, Rahu/eclipse chunks returned); `houses:04:en` (kendra/trikona/upachaya "House-type guide" never surfaces, house-lord chunks win); `houses:01:hi` (आठवें भाव = 8th house not mapped, Sade Sati chunks returned); `houses:02:hi` (वृषभ not mapped to Taurus: Scorpio lagna chunk returned); `matching:01:hg` ("6/8" not mapped to Bhakoot); `nakshatras:03:hi` (the joined spelling पूर्वाभाद्रपद is not in the glossary). Label strictness / hard paraphrase (3): `houses:02:en` (the per-lagna yogakaraka chunks of the gold file answer the question; only the summary-table chunk is graded), `matching:06:en` (a product-wording question; gold is one section of kb_match_relationship_types), `sade_sati:01:hi` (Rahu/Ketu transit duration; Rahu chunks from four other files returned, gold is the gochara-rules section; partly a defect). Missing knowledge: none found.

**Decision re-confirmed: keep `EMBEDDING_MODEL=minilm-l6-q`, `EMBEDDINGS_RUNTIME=local`.** The gain is small but positive on all three fresh blind sets (+0.04 / +0.11 / +0.03 to +0.06), the cost is +125 MB with a keys+FTS fallback, and rollback is one env var. Condition unchanged: re-ingest Neon first. Caveat: Linux RSS unmeasured.

### Vocabulary classes and live trap test (BUG-027)

`app/rag/vocab.py` maps complete classes (not samples) onto KB words: signs, all 27 nakshatras (spaced and joined Devanagari, Roman variants), ordinals and house-lord words 1-12, kendra/trikona/dusthana/upachaya (reach the "House Classifications" headings), planets and nicknames, MD/AD/PD and D1-D60, kuta/dosha names and 6/8, 2/12, 5/9, Panchang limbs, tithis, weekdays. Unit tests iterate every member (`tests/rag/test_vocab_classes.py`). kb_lang_* chunks carry a 0.012 penalty unless the question asks for a meaning or translation. Off-mode hit@5 after: even 0.855, odd 0.833, 204-set 0.909, fresh-hi diagnostic 0.778. Known ambiguity: "shravan"/"magh" stay lunar months.

Live trap run (`python -m evals.trap_live`, real Gemini, synthetic chart): 25 refusal / no-answer / injection questions; no invented price, date, diagnosis or lottery number, no leak.

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
- **Settings:** `EMBEDDINGS_RUNTIME=local|off`, `EMBEDDING_MODEL` (spec key or full name), `EMBED_QUERY_TIMEOUT_S` (0.4), `RAG_EXCLUDE_REVIEW`, `RAG_RERANK_MODEL`, `RAG_TIMEOUT_S` (3 s), plus `rag_top_k` / `rag_token_cap` / `rag_candidates`.
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
