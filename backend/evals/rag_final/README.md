# Final exam: independent retrieval eval (round 3)

`queries.jsonl` has 102 records in the same schema as `../rag_independent` (`split: final`, ids `final:<topic>:<nn>:<lang>`).
Treat it as a held-out set. The earlier sets (`rag_independent`, `rag_independent_hi`) are development sets.

- 90 answerable queries: dasha 15, houses/lords 12, matching 12, nakshatras 10, dignity 8, sade_sati/gochara 8,
  panchang 8, yogas 7, remedies 5, divisional 5. Language: 45 en, 23 hi, 22 hg.
- Tags: 12 `two_sections`, 8 `schools_differ`, 8 `paraphrase`, 6 typo/abbreviation.
- 12 traps (`topic: no_answer`, `gold: []`, `expect: "no_answer"`). Hard ones share vocabulary with KB topics:
  a specific-year prediction, gemstone prices, absent celebrity charts, medical diagnosis, live Rahu Kaal.
  The KB holds only a refusal policy for medical questions and a vague cost range for gems, so the correct
  outcome is low confidence or a refusal-style answer, never a confident factual one.

Labelling: blind, from the KB files only, with no retriever run or output seen. Gold is `{file, h regex, c, g}`,
g=2 for answering sections and g=1 for alternates. All regexes were checked against real heading paths.
None matches a file's H1 title. No question text duplicates an earlier set. 25 random queries were hand-audited.

Run (from `backend/`; traps excluded because empty gold scores 0):

```
python -c "import sys,json,pathlib; sys.argv=['run','--label','final_v1']; import evals.rag.run as r; P=pathlib.Path('evals/rag_final/queries.jsonl'); r.load_queries=lambda limit=None:[q for q in map(json.loads,P.read_text(encoding='utf-8').splitlines()) if q['topic']!='no_answer'][:limit]; sys.exit(r.main())"
```
