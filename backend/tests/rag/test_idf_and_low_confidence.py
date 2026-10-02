"""BUG-027: IDF-aware full-text planning and the low-confidence signal."""

from __future__ import annotations

import re

from app.rag.query import apply_idf, build_plan
from app.rag.retriever import RetrievalConfig, Retriever

from .test_retriever_ops import make

CFG = RetrievalConfig()
SAFE = re.compile(r"^[a-z0-9 |&<>\-ऀ-ॿ]*$")


def plan_for(q, df, n=100, lang="english"):
    p = build_plan(q, lang, [], multilingual=False, cfg=CFG)
    apply_idf(p, {**{t: 0 for t in p.terms}, **df}, n, CFG)
    return p


def test_common_terms_leave_the_or_query_and_rare_terms_get_and_and_phrase_lists():
    p = plan_for("Is Rahu exalted in Taurus or in Gemini?", {"rahu": 8, "exalted": 3, "taurus": 6, "gemini": 5, "moon": 40})
    by = {label: q for label, q, _ in p.fts}
    assert "f:and" in by and " & " in by["f:and"] and "exalted" in by["f:and"]
    assert "rahu <-> exalted" in by["f:p"]
    assert "moon" not in by["f:t"]


def test_very_common_terms_are_dropped_unless_nothing_else_is_left():
    p = plan_for("Moon sign nadi mismatch", {"moon": 60, "sign": 50, "nadi": 3, "mismatch": 2})
    by = {label: q for label, q, _ in p.fts}
    assert "sign" not in by["f:t"] and "nadi" in by["f:t"] and "moon" in by["f:t"]      # a named planet is never "common"
    p = plan_for("moon sign", {"moon": 60, "sign": 50})
    assert "moon" in {label: q for label, q, _ in p.fts}["f:t"]


def test_hindi_questions_get_no_phrase_list_and_all_queries_are_tsquery_safe():
    p = plan_for("मंगल की नीच राशि कौन सी है?", {"mars": 4, "debilitation": 3, "sign": 30}, lang="hindi")
    assert "f:p" not in {label for label, _, _ in p.fts}
    for q in ("Is Rahu exalted in Taurus; DROP TABLE x -- or in Gemini?", "a' | b <-> c & d"):
        p = plan_for(q, {"rahu": 4, "exalted": 3, "taurus": 5, "gemini": 5})
        assert all(SAFE.match(text) for _, text, _ in p.fts), p.fts


def test_idf_off_keeps_the_original_plan():
    cfg = RetrievalConfig(idf=False)
    assert cfg.idf is False and RetrievalConfig().idf is True


async def test_unrelated_question_is_low_confidence_and_matching_one_is_not():
    _, _, r = await make(embedder=False)
    miss = await r.retrieve_ex(kb_keys=[], question="Explain Varshaphal Muntha progression rules", system="both")
    assert miss.low_confidence is True and not miss.degraded
    hit = await r.retrieve_ex(kb_keys=[], question="What is sade sati and the Saturn transit over the Moon?", system="vedic")
    assert hit.chunks and hit.stats["top_score"] > 0


async def test_degraded_retrieval_is_not_reported_as_low_confidence():
    class Boom:
        async def active_version(self):
            raise RuntimeError("down")

    r = Retriever(Boom(), None)
    out = await r.retrieve_ex(kb_keys=[], question="saturn", system="both")
    assert out.degraded and out.low_confidence is False


def test_thresholds_are_documented_defaults():
    assert CFG.low_conf_off == 0.05 and CFG.low_conf_local == 0.06


class DegradedEmbedder:
    model_name = "stub-model"
    spec = None

    def __init__(self, vectors):
        self.vectors, self.stats, self.disabled = vectors, {"degraded": 0}, None

    async def embed_queries(self, texts):
        if not self.vectors:
            self.stats["degraded"] += 1
            return []
        return [[0.0] * 384 for _ in texts]

    def disable(self, reason, seconds=0):
        self.disabled = reason


class MemCache:
    def __init__(self):
        self.d = {}

    async def get(self, k):
        return self.d.get(k)

    async def set(self, k, v, ttl):
        self.d[k] = v


async def test_degraded_embedder_result_is_not_cached_but_a_healthy_one_is():
    from app.rag.embeddings import HashEmbedder

    _, _, base = await make(embedder=False)
    for vectors, cached in ((False, 0), (True, 1)):
        cache = MemCache()
        emb = DegradedEmbedder(vectors)
        r = Retriever(base.store, emb, cache=cache)
        r._multilingual = True
        out = await r.retrieve(kb_keys=[], question="What is sade sati and the Saturn transit?", system="vedic")
        assert out and len(cache.d) == cached


async def test_self_check_disables_the_embedder_on_model_mismatch():
    _, _, base = await make(embedder=False)
    emb = DegradedEmbedder(True)
    r = Retriever(base.store, emb)
    base.store.meta["embedding_model"] = "other-model"
    rep = await r.self_check()
    assert not rep["ok"] and emb.disabled and "mismatch" in emb.disabled


def test_planet_in_house_lord_and_dasha_pair_anchor_phrases():
    p = plan_for("Saturn in the 10th house career", {"saturn": 40, "10th": 14, "house": 60, "career": 50})
    assert "saturn <3> 10th" in {l: q for l, q, _ in p.fts}["f:a"]
    p = plan_for("What if the 7th lord is in the 12th house", {"7th": 9, "12th": 9, "lord": 20, "house": 60})
    assert "7th <-> lord" in {l: q for l, q, _ in p.fts}["f:a"]
    p = plan_for("Saturn Mahadasha Venus Antardasha", {"saturn": 40, "venus": 40, "mahadasha": 20, "antardasha": 5, "dasha": 12})
    assert "saturn <-> venus | venus <-> saturn" in {l: q for l, q, _ in p.fts}["f:a"]


def test_romanised_function_words_do_not_become_search_terms():
    from app.rag.glossary import gloss_terms

    t = gloss_terms("Saturn 10th house me ho to career kaisa rehta hai")
    assert "saturn" in t and "10th" in t and not {"kaisa", "rehta"} & set(t)
    assert gloss_terms("uttra bhadrapad ka lord kaun sa planet hai")[:2] == ["uttara", "bhadrapada"]
