# Independent Hindi/Hinglish retrieval eval (round 2)

`queries.jsonl`: 73 records, same schema as `../rag_independent` (`split: indep_hi`, ids `indep_hi:<topic>:<nn>:<lang>`).
- 63 answerable queries: 37 Hinglish (`hg`, including mixed script), 26 Devanagari Hindi (`hi`).
- Topics: dasha, sade_sati, matching, nakshatras, dignity, panchang, gochara, yogas, remedies, houses.
- 10 tagged `two_sections` (two grade-2 gold entries), 6 tagged `schools_differ`.
- 10 traps (`topic: no_answer`, `gold: []`, `expect: "no_answer"`).

Labelling: blind. Labels were written from the knowledge-base files only, with no retriever run or output seen.
Gold is `{file, h (regex on heading path), g}`, with g=2 for answering sections and g=1 for alternates.
A script confirmed every regex matches a real heading and none matches a file's H1 title.
Twenty random queries were hand-audited against the source sections.

Run (from `backend/`; trap rows are excluded because empty gold scores 0):

```
python -c "import sys,json,pathlib; sys.argv=['run','--label','indep_hi_v1']; import evals.rag.run as r; P=pathlib.Path('evals/rag_independent_hi/queries.jsonl'); r.load_queries=lambda limit=None:[q for q in map(json.loads,P.read_text(encoding='utf-8').splitlines()) if q['topic']!='no_answer'][:limit]; sys.exit(r.main())"
```
