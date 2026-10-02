# Independent retrieval eval (blind labels)

`queries.jsonl` holds 131 queries in the same record schema as `evals/rag/queries.jsonl`
(`id, source, split, chart, lang, text, topic, system, gold[{file,h,c,g}]`), with extra keys the
loader ignores (`tags`, `note`, `expect`, `trap_reason`).

- 121 answerable queries: 41 matching/doshas, 30 dignity, 30 nakshatras, 20 other
  (Sade Sati, panchang, gochara, yogas). Language: 55 en, 36 hi, 30 hg (Roman and mixed script).
- 10 trap queries (`topic: no_answer`, `gold: []`, `expect: "no_answer"`): the KB has no answer,
  so the system should return nothing or low confidence.
- `split` is `indep` and `source` is `independent`, so the runner reports them as their own groups.

## Labelling method

Written without running the retriever and without looking at any retrieval output or retriever code.
Each label comes from reading the knowledge-base file itself. Gold entries are
`{file: <stem>, h: <regex on heading path>, g: 2|1}`. Grade 2 is the section that answers the query.
Grade 1 is an acceptable alternate (duplicate coverage in another file, or supporting detail).
Questions that need two sections have two grade-2 entries. Heading regexes avoid text that is also in
the file's H1 title, so a regex never selects every chunk of a file. A script checked that every regex
matches at least one real heading in its file. Tags: `schools_differ`, `paraphrase`, `typo`,
`abbreviation`, `mixed_script`, `two_sections`, `trap`. Where the KB files disagree (for example
Sun exaltation 10 vs 19 degrees, Saturn 20 vs 21), both sources are graded 2 and the `note` field says so.

## Running (not run yet)

The existing runner reads only `evals/rag/queries.jsonl` and has no query-path flag, so patch the
loader at call time. From `backend/`:

```
python -c "import sys,json,pathlib; sys.argv=['run','--label','indep_v1']; import evals.rag.run as r; P=pathlib.Path('evals/rag_independent/queries.jsonl'); r.load_queries=lambda limit=None:[q for q in map(json.loads,P.read_text(encoding='utf-8').splitlines()) if q['topic']!='no_answer'][:limit]; sys.exit(r.main())"
```

Add the runner's usual `--config` and `--embedder` flags to `sys.argv` as needed. The report goes to
`evals/rag/reports/indep_v1.json`. Trap queries are excluded above because the metric code scores an
empty gold set as 0; evaluate them separately by checking that the top retrieval score is below the
system's confidence threshold.
