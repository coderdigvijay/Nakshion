"""Retrieval metrics and gold resolution (pure functions, no I/O)."""

from __future__ import annotations

import math
import re
from typing import Iterable, Sequence


def resolve_gold(gold: list[dict], chunks: Iterable) -> dict[str, int]:
    """matchers -> {chunk_id: grade}. `chunks` need .id .file .heading_path .content.
    A matcher is (file stem, heading regex, content regex, grade); the best grade wins."""
    rel: dict[str, int] = {}
    for c in chunks:
        stem = c.file[:-3] if c.file.endswith(".md") else c.file
        for m in gold:
            if m["file"] != stem:
                continue
            if m.get("h") and not re.search(m["h"], c.heading_path, re.I):
                continue
            if m.get("c") and not re.search(m["c"], c.content, re.I):
                continue
            rel[c.id] = max(rel.get(c.id, 0), int(m["g"]))
    return rel


def _hit(ids: Sequence[str], rel: dict[str, int], k: int, min_grade: int = 1) -> float:
    return 1.0 if any(rel.get(i, 0) >= min_grade for i in ids[:k]) else 0.0


def recall_capped(ids: Sequence[str], rel: dict[str, int], k: int) -> float:
    """Relevant retrieved in top-k / min(|relevant|, k): 1.0 means the top-k is as good as it can be."""
    denom = min(len(rel), k) or 1
    return min(1.0, sum(1 for i in ids[:k] if rel.get(i, 0) >= 1) / denom)


def mrr(ids: Sequence[str], rel: dict[str, int], k: int = 10) -> float:
    for r, i in enumerate(ids[:k], 1):
        if rel.get(i, 0) >= 1:
            return 1.0 / r
    return 0.0


def ndcg(ids: Sequence[str], rel: dict[str, int], k: int = 10) -> float:
    dcg = sum((2 ** rel.get(i, 0) - 1) / math.log2(r + 1) for r, i in enumerate(ids[:k], 1))
    ideal = sorted(rel.values(), reverse=True)[:k]
    idcg = sum((2 ** g - 1) / math.log2(r + 1) for r, g in enumerate(ideal, 1))
    return dcg / idcg if idcg else 0.0


def score_query(ids: Sequence[str], rel: dict[str, int]) -> dict[str, float]:
    return {
        "hit@5": _hit(ids, rel, 5), "hit@10": _hit(ids, rel, 10), "primary@5": _hit(ids, rel, 5, 2),
        "recall@5": recall_capped(ids, rel, 5), "recall@10": recall_capped(ids, rel, 10),
        "mrr": mrr(ids, rel), "ndcg@10": ndcg(ids, rel),
    }


def aggregate(rows: list[dict[str, float]]) -> dict[str, float]:
    if not rows:
        return {}
    return {k: round(sum(r[k] for r in rows) / len(rows), 4) for k in rows[0]}


def percentile(xs: list[float], p: float) -> float:
    if not xs:
        return 0.0
    s = sorted(xs)
    return s[min(len(s) - 1, int(round(p * (len(s) - 1))))]
