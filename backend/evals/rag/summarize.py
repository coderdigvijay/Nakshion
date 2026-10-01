"""python -m evals.rag.summarize label1 label2 ...  -> one comparison line per report."""
import json, sys
from pathlib import Path

R = Path(__file__).resolve().parent / "reports"
for lab in sys.argv[1:]:
    m = json.loads((R / f"{lab}.json").read_text())
    a, sp, st = m["all"], m["split"], m["strict_old_gold"]
    print(f"{lab:46} all hit@5 {a['hit@5']:.3f} R@5 {a['recall@5']:.3f} MRR {a['mrr']:.3f} nDCG {a['ndcg@10']:.3f} | "
          + " ".join(f"{k} {v['hit@5']:.2f}/{v['ndcg@10']:.2f}" for k, v in sp.items())
          + f" | strict {st['hit@5']:.3f}/{st['ndcg@10']:.3f} | hi {m['lang']['hi']['hit@5']:.2f} p95 {m['latency_ms']['p95']}ms")
