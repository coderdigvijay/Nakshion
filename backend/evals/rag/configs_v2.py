from __future__ import annotations

from dataclasses import replace

from app.rag.retriever import RetrievalConfig
from evals.rag.configs import Config

# The ablation ladder: each step changes ONE thing relative to the previous.
LEGACY_LIKE = RetrievalConfig(use_gloss=False, phonetic=False, key_policy="all", key_weight=1.0, fts_key_weight=0.0, head_boost=0.0,
                              topic_boost=0.0, tier_boost=(0, 0, 0), max_per_file=99, dup_jaccard=1.1)
LADDER = {
    "A0-legacy-like": LEGACY_LIKE,
    "A1-keys-matched": replace(LEGACY_LIKE, key_policy="matched", key_weight=0.35),
    "A2-gloss": replace(LEGACY_LIKE, key_policy="matched", key_weight=0.35, use_gloss=True),
    "A3-fts-keys": replace(LEGACY_LIKE, key_policy="matched", key_weight=0.35, use_gloss=True, fts_key_weight=0.3),
    "A4-boosts": replace(LEGACY_LIKE, key_policy="matched", key_weight=0.35, use_gloss=True, fts_key_weight=0.3,
                         head_boost=0.006, topic_boost=0.002, tier_boost=(0.002, 0.0, -0.002)),
    "A5-diversity": replace(RetrievalConfig(), phonetic=False),
    "A6-phonetic": RetrievalConfig(),
    "A6-no-review": replace(RetrievalConfig(), exclude_licences=("modern_author_paraphrase",)),
    "A5-nogloss": replace(RetrievalConfig(), use_gloss=False),
}


def build_v2(name: str) -> Config:
    rerank = None
    base = name
    if name.endswith("+rerank-minilm6"):
        base, rerank = name[: -len("+rerank-minilm6")], "Xenova/ms-marco-MiniLM-L-6-v2"
    elif name.endswith("+rerank-jina-tiny"):
        base, rerank = name[: -len("+rerank-jina-tiny")], "jinaai/jina-reranker-v1-tiny-en"
    elif name.endswith("+rerank-minilm12"):
        base, rerank = name[: -len("+rerank-minilm12")], "Xenova/ms-marco-MiniLM-L-12-v2"
    if base == "v2":
        base = "A6-phonetic"
    overrides = {}
    if ":" in base:                      # "A5-diversity:key_weight=0.2,head_boost=0.01"
        base, kv = base.split(":", 1)
        for pair in kv.split(","):
            k, v = pair.split("=")
            overrides[k] = type(getattr(LADDER[base], k))(v) if not isinstance(getattr(LADDER[base], k), bool) else v == "1"
    cfg = replace(LADDER[base], **overrides) if overrides else LADDER[base]
    return Config(name, cfg, rerank=rerank)
