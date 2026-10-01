"""Named retrieval configurations the eval can compare (ablation ladder)."""

from __future__ import annotations

from dataclasses import dataclass, replace

from evals.rag.run import legacy_keys


@dataclass
class Config:
    name: str
    cfg: "RetrievalConfig"
    rerank: str | None = None
    keys: str = "legacy"            # legacy: top-6 factors' kb_keys as production did; none

    def preembed_keys(self, chunks) -> list[str]:
        from app.rag.keys import generate_keys

        return generate_keys()

    def make(self, store, embedder):
        from app.rag.rerank import CrossEncoderReranker
        from app.rag.retriever import Retriever

        rr = CrossEncoderReranker(self.rerank, threads=None) if self.rerank else None
        cfg = replace(self.cfg, rerank_model=self.rerank, token_cap=10**9, top_k=10, timeout_s=30.0)
        r = Retriever(store, embedder, config=cfg, reranker=rr)
        return r, (lambda chart, q: legacy_keys(chart, q["system"]))


def build_config(name: str) -> Config:
    from evals.rag.configs_v2 import build_v2

    return build_v2(name)
