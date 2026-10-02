"""Hybrid retrieval (llm-integration.md §3 [4], §6) tuned and measured by evals/rag.

pipeline  plan (question + gloss + relevant factor keys)  ->  embed (one batch)  ->  ONE SQL round trip
          (vectors + pre-embedded keys + weighted full-text, fused server-side with RRF)
          -> metadata boosts (heading hits, topic, tier) -> optional cross-encoder rerank
          -> diversity (heading / near-duplicate / per-file cap) -> top-k within a token budget
safety    timeout + circuit breaker + result cache + metrics; ANY failure returns [] with degraded=True so
          chat degrades to chart-facts-only (never an error)
logging   counts and latencies only. No question text, no birth data, no chunk text.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import time
from collections import deque
from dataclasses import asdict, dataclass, field, replace
from typing import Any, Protocol

from app.llm.resilience import CircuitBreaker
from app.rag.chunking import count_tokens
from app.rag.embeddings import Embedder
from app.rag.query import QueryPlan, apply_idf, build_plan, normalize_question
from app.rag.store import RetrievedChunk, SearchSpec, VectorStore

log = logging.getLogger("nakshion.rag.retriever")
_EXCLUDED_TRIGGERS = ("chinese", "mundane", "world event", "election", "nation", "चीनी")


@dataclass(frozen=True)
class RetrievalConfig:
    top_k: int = 5
    token_cap: int = 1200
    per_query: int = 20
    candidates: int = 30
    # query construction
    use_question: bool = True
    use_gloss: bool = True
    phrasebook: bool = True             # Hinglish phrase -> concept expansion (kb_lang_hinglish_phrasebook.md)
    phonetic: bool = True               # sound-alike bridge for unknown Devanagari loanwords (app/rag/phonetic.py)
    q_weight: float = 1.0
    gloss_weight: float = 1.0
    key_policy: str = "matched"          # matched | all | none
    key_weight: float = 0.35
    max_keys: int = 6
    fts: bool = True
    fts_weight: float = 1.0
    fts_key_weight: float = 0.3
    # IDF-aware full-text planning (BUG-027): Postgres ts_rank has no IDF, so a query like "Moon sign ... Nadi" was won by
    # every Moon-heavy chunk. Terms in > common_df of the chunks are dropped from the OR query, an AND list over the
    # discriminative terms and a phrase list over adjacent question words are added.
    idf: bool = True
    common_df: float = 0.12
    rare_df: float = 0.10
    fts_and_weight: float = 1.5
    fts_rare_weight: float = 1.0
    fts_phrase_weight: float = 2.0
    fts_anchor_weight: float = 2.0
    lang_penalty: float = 0.012       # kb_lang_* (phrasebook / glossary) chunks, unless the question asks for a term's meaning or a translation
    # Low-confidence thresholds on the best fused+boosted score (evals/rag_independent, 10 traps vs 121 answerable):
    # off (keys+FTS): 0.05 flags 5/10 traps and 3/121 answerable (2.5%); local embeddings: 0.06 flags 5/10 and 7/121 (5.8%).
    low_conf_off: float = 0.05
    low_conf_local: float = 0.06
    fts_head_weight: float = 0.0         # optional extra full-text query on the distinctive terms only (measured: no gain)
    # metadata boosts (added to the fused RRF score; one rank-1 hit is ~0.016)
    head_boost: float = 0.02
    topic_boost: float = 0.002
    tier_boost: tuple[float, float, float] = (0.002, 0.0, -0.002)    # tier 1, 2, 3
    confidence_boost: tuple[float, float, float] = (0.002, 0.0, -0.002)   # high, medium, low
    unverified_penalty: float = 0.0015
    definition_boost: float = 0.004      # glossary-style chunks for 'what does X mean' questions
    table_penalty: float = 0.008         # row-level tables answer row-level queries: penalise when <2 query terms hit
    max_per_section: int = 2             # chunks from one H2 section (row groups of one table count together)
    exclude_licences: tuple[str, ...] = ()
    # diversity
    max_per_file: int = 3
    dup_jaccard: float = 0.6
    # rerank
    rerank_model: str | None = None
    rerank_n: int = 15
    rerank_alpha: float = 0.5
    # resilience
    timeout_s: float = 3.0
    cache_ttl_s: int = 6 * 3600

    def fingerprint(self) -> str:
        return hashlib.sha1(json.dumps(asdict(self), sort_keys=True, default=str).encode()).hexdigest()[:10]


@dataclass
class RetrievalResult:
    chunks: list[RetrievedChunk]
    degraded: bool = False
    reason: str | None = None
    stats: dict = field(default_factory=dict)
    # True when the best note scores below the threshold measured on the independent trap queries (or nothing matched):
    # the answer layer should say it has no sourced note instead of presenting the notes as support. Not set when
    # retrieval degraded (that is a different state: the notes are unavailable, not absent).
    low_confidence: bool = False


class JsonCache(Protocol):
    async def get(self, key: str) -> Any | None: ...
    async def set(self, key: str, value: Any, ttl: int) -> None: ...


class RedisJsonCache:
    def __init__(self, redis: Any, prefix: str = "rag:r:") -> None:
        self._r, self._p = redis, prefix

    async def get(self, key: str) -> Any | None:
        raw = await self._r.get(self._p + key)
        return json.loads(raw) if raw else None

    async def set(self, key: str, value: Any, ttl: int) -> None:
        await self._r.set(self._p + key, json.dumps(value, ensure_ascii=False), ex=ttl)


class RagMetrics:
    """In-process counters (one Render instance). `snapshot()` is safe to expose on an admin/health route."""

    def __init__(self) -> None:
        self.n = self.empty = self.degraded = self.cache_hits = self.errors = self.timeouts = 0
        self.key_hits = self.key_total = 0
        self.rerank_calls = self.rerank_moved = 0
        self._lat: deque[float] = deque(maxlen=500)

    def observe(self, ms: float) -> None:
        self._lat.append(ms)

    def snapshot(self) -> dict:
        lat = sorted(self._lat)
        pct = lambda p: round(lat[min(len(lat) - 1, int(p * (len(lat) - 1)))], 1) if lat else None  # noqa: E731
        n = max(1, self.n)
        return {"requests": self.n, "empty_rate": round(self.empty / n, 4), "degraded": self.degraded,
                "cache_hit_rate": round(self.cache_hits / n, 4), "errors": self.errors, "timeouts": self.timeouts,
                "latency_ms_p50": pct(0.5), "latency_ms_p95": pct(0.95),
                "rerank_calls": self.rerank_calls, "rerank_reorder_rate":
                    round(self.rerank_moved / max(1, self.rerank_calls), 3)}


_TRANSLATE_ASK = re.compile(r"translat|phrasebook|hinglish|in hindi|in english|hindi (?:mein|me|word)|english (?:mein|me|word)|अनुवाद|हिंदी में|अंग्रेज़ी|अंग्रेजी", re.I)


def systems_for(user_system: str, question: str = "") -> list[str]:
    base = {"vedic": ["vedic", "both"], "western": ["western", "both"]}.get(user_system, ["vedic", "western", "both"])
    if any(t in question.lower() for t in _EXCLUDED_TRIGGERS):
        base = base + ["excluded"]
    return base


def _shingles(text: str, n: int = 4) -> set[tuple[str, ...]]:
    w = re.findall(r"\w+", text.lower())
    return {tuple(w[i:i + n]) for i in range(max(0, len(w) - n + 1))}


def _jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


def _minmax(xs: list[float]) -> list[float]:
    lo, hi = min(xs), max(xs)
    return [(x - lo) / (hi - lo) if hi > lo else 0.5 for x in xs]


class Retriever:
    def __init__(self, store: VectorStore, embedder: Embedder | None, *, config: RetrievalConfig | None = None,
                 reranker: Any = None, cache: JsonCache | None = None, metrics: RagMetrics | None = None,
                 top_k: int | None = None, token_cap: int | None = None, candidates: int | None = None,
                 max_keys: int | None = None, timeout_s: float | None = None) -> None:
        cfg = config or RetrievalConfig()
        # legacy keyword overrides (kept for callers written against the first version)
        over = {k: v for k, v in dict(top_k=top_k, token_cap=token_cap, per_query=candidates, max_keys=max_keys,
                                      timeout_s=timeout_s).items() if v is not None}
        self.cfg = replace(cfg, **over) if over else cfg
        self.store, self.embedder, self.reranker, self.cache = store, embedder, reranker, cache
        self.metrics = metrics or RagMetrics()
        self.breaker = CircuitBreaker(failures=5, window_s=60.0, open_s=30.0)
        self._multilingual = bool(getattr(getattr(embedder, "spec", None), "multilingual", False))

    # ------------------------------------------------------------------ public
    async def retrieve(self, *, kb_keys: list[str], question: str, system: str = "both", topic: str = "general",
                       language: str = "english") -> list[RetrievedChunk]:
        return (await self.retrieve_ex(kb_keys=kb_keys, question=question, system=system, topic=topic,
                                       language=language)).chunks

    async def retrieve_ex(self, *, kb_keys: list[str], question: str, system: str = "both", topic: str = "general",
                          language: str = "english") -> RetrievalResult:
        t0 = time.perf_counter()
        m = self.metrics
        m.n += 1
        if not self.breaker.allow():
            m.degraded += 1
            return self._finish(RetrievalResult([], True, "breaker_open"), t0)
        try:
            async with asyncio.timeout(self.cfg.timeout_s):
                res = await self._retrieve(kb_keys, question, system, language)
            self.breaker.record_success()
        except TimeoutError:
            m.timeouts += 1
            self.breaker.record_failure()
            log.warning("rag_timeout", extra={"timeout_s": self.cfg.timeout_s})
            return self._finish(RetrievalResult([], True, "timeout"), t0)
        except Exception as exc:  # noqa: BLE001 - graceful degradation to chart-facts-only
            m.errors += 1
            self.breaker.record_failure()
            log.warning("rag_error", extra={"error": type(exc).__name__})
            return self._finish(RetrievalResult([], True, "error"), t0)
        return self._finish(res, t0)

    def _finish(self, res: RetrievalResult, t0: float) -> RetrievalResult:
        ms = (time.perf_counter() - t0) * 1000
        self.metrics.observe(ms)
        if res.degraded:
            self.metrics.degraded += 1 if res.reason in ("no_index",) else 0
        elif not res.chunks:
            self.metrics.empty += 1
        res.stats["latency_ms"] = round(ms, 1)
        log.info("rag_retrieve", extra={"rag": {**res.stats, "hits": len(res.chunks), "degraded": res.degraded,
                                                "reason": res.reason}})
        return res

    # ------------------------------------------------------------------ internals
    def _cache_key(self, version: int, systems: list[str], plan: QueryPlan) -> str:
        raw = json.dumps([version, systems, self.cfg.fingerprint(), plan.keys_used, normalize_question(plan.question),
                          plan.language, getattr(self.embedder, "model_name", None)], ensure_ascii=False)
        return hashlib.sha1(raw.encode()).hexdigest()

    async def _retrieve(self, kb_keys, question, system, language) -> RetrievalResult:
        cfg, m = self.cfg, self.metrics
        version = await self.store.active_version()
        if version is None:
            return RetrievalResult([], True, "no_index")
        systems = systems_for(system, question)
        plan = build_plan(question, language, kb_keys, multilingual=self._multilingual, cfg=cfg)
        if cfg.idf and plan.fts and hasattr(self.store, "term_df"):
            try:
                df, n_docs = await self.store.term_df(version, plan.terms)
                apply_idf(plan, df, n_docs, cfg)
            except Exception:  # noqa: BLE001 - IDF is an optimisation; keep the plain plan
                log.warning("rag_idf_failed")
        stats = {"version": version, "lang": language, "keys_used": len(plan.keys_used),
                 "keys_dropped": len(plan.keys_dropped), "terms": len(plan.terms), "n_fts": len(plan.fts)}
        ck = self._cache_key(version, systems, plan) if self.cache else None
        if ck:
            try:
                hit = await self.cache.get(ck)
            except Exception:  # noqa: BLE001 - cache is best effort
                hit = None
            if hit is not None:
                m.cache_hits += 1
                cached = [RetrievedChunk(**{**h, "entities": tuple(h["entities"]),
                                            "topics": tuple(h["topics"]), "via": tuple(h["via"])}) for h in hit]
                thr = cfg.low_conf_local if self.embedder is not None and plan.vector_texts else cfg.low_conf_off
                return RetrievalResult(cached, stats={**stats, "cache": "hit"},
                                       low_confidence=(not cached) or cached[0].score < thr)
        vectors: list[tuple[str, list[float], float]] = []
        degraded0 = (getattr(self.embedder, "stats", None) or {}).get("degraded", 0)
        if self.embedder is not None and plan.vector_texts:
            vecs = await self.embedder.embed_queries([t for _, t, _ in plan.vector_texts])
            vectors = [(lab, v, w) for (lab, _, w), v in zip(plan.vector_texts, vecs)]
        stats["n_vec"] = len(vectors)
        if not vectors and not plan.fts and not plan.keys_used:
            return RetrievalResult([], stats=stats, low_confidence=True)
        spec = SearchSpec(version=version, systems=systems, vectors=vectors, keys=plan.keys_used,
                          key_weight=cfg.key_weight, fts=plan.fts, per_query=cfg.per_query, limit=cfg.candidates)
        cands = await self.store.hybrid_search(spec)
        if cfg.exclude_licences:
            cands = [c for c in cands if c.meta.get("licence") not in cfg.exclude_licences]
        cands = self._boost(cands, plan)
        if self.reranker is not None and cfg.rerank_model is not None and len(cands) > 1:
            cands = await self._rerank(cands, plan, stats)
        out = self._select(cands)
        m.key_total += len(plan.keys_used) + len(plan.keys_dropped)
        embed_degraded = ((getattr(self.embedder, "stats", None) or {}).get("degraded", 0) > degraded0
                          or (self.embedder is not None and plan.vector_texts and not vectors))
        if ck and out and not embed_degraded:      # never cache a keys+FTS result produced while the embedder was degraded
            try:
                await self.cache.set(ck, [{**asdict(c), "meta": c.meta} for c in out], cfg.cache_ttl_s)
            except Exception:  # noqa: BLE001
                pass
        thr = cfg.low_conf_local if vectors else cfg.low_conf_off
        low = (not out) or out[0].score < thr
        stats["top_score"] = round(out[0].score, 4) if out else 0.0
        return RetrievalResult(out, stats=stats, low_confidence=low)

    def _boost(self, cands: list[RetrievedChunk], plan: QueryPlan) -> list[RetrievedChunk]:
        cfg = self.cfg
        out = []
        for c in cands:
            hp = c.heading_path.lower()
            n_head = sum(1 for t in plan.head_terms if re.search(rf"\b{re.escape(t)}", hp))
            s = c.score + cfg.head_boost * min(n_head, 3)
            if plan.topic != "general" and plan.topic in c.topics:
                s += cfg.topic_boost
            tier = int(c.meta.get("tier", 1))
            s += cfg.tier_boost[min(max(tier, 1), 3) - 1]
            conf = {"high": 0, "medium": 1, "low": 2}.get(str(c.meta.get("confidence", "medium")), 1)
            s += cfg.confidence_boost[conf]
            if c.meta.get("unverified"):
                s -= cfg.unverified_penalty                       # never prefer a chunk with [unverified] claims
            if c.meta.get("kind") == "table" and c.meta.get("language", "en") == "en":
                # a row-level table answers a row-level question: its heading + row labels must name >= 2 query terms
                if sum(1 for t in plan.head_terms if re.search(rf"\b{re.escape(t[:5])}", hp)) < 2:
                    s -= cfg.table_penalty
            if plan.lord_of and re.search(rf"\b{plan.lord_of} lord in", hp):
                s += 2 * cfg.head_boost                           # "7th lord in the 12th house": the lord's own section
            if c.file.startswith("kb_lang_") and not plan.is_definition and not _TRANSLATE_ASK.search(plan.question):
                s -= cfg.lang_penalty
            if plan.is_definition and (c.file.startswith("kb_lang_") or c.meta.get("language") in ("hinglish", "hi")):
                s += cfg.definition_boost
            q = float(c.meta.get("quality", 1.0))
            s -= 0.003 * (1.0 - q)
            out.append(replace(c, score=s))
        out.sort(key=lambda c: c.score, reverse=True)
        return out

    async def _rerank(self, cands: list[RetrievedChunk], plan: QueryPlan, stats: dict) -> list[RetrievedChunk]:
        cfg = self.cfg
        head, tail = cands[: cfg.rerank_n], cands[cfg.rerank_n:]
        q = plan.query_en if (plan.query_en and plan.language != "english") else plan.question
        t0 = time.perf_counter()
        ce = await self.reranker.score(q, [f"{c.heading_path}. {c.content}" for c in head])
        stats["rerank_ms"] = round((time.perf_counter() - t0) * 1000, 1)
        a = cfg.rerank_alpha
        base, cen = _minmax([c.score for c in head]), _minmax(ce)
        rescored = [replace(c, score=(1 - a) * b + a * x) for c, b, x in zip(head, base, cen)]
        rescored.sort(key=lambda c: c.score, reverse=True)
        self.metrics.rerank_calls += 1
        if [c.chunk_id for c in rescored[: cfg.top_k]] != [c.chunk_id for c in head[: cfg.top_k]]:
            self.metrics.rerank_moved += 1
        floor = min((c.score for c in rescored), default=0.0) - 1e-6
        return rescored + [replace(c, score=floor) for c in tail]

    def _select(self, cands: list[RetrievedChunk]) -> list[RetrievedChunk]:
        cfg = self.cfg
        out: list[RetrievedChunk] = []
        seen_paths: set[str] = set()
        per_file: dict[str, int] = {}
        per_section: dict[str, int] = {}
        shingles: list[set] = []
        used = 0
        for c in cands:
            section = c.file + "|" + re.split(r" > rows? ", c.heading_path)[0]
            if (c.heading_path in seen_paths or per_file.get(c.file, 0) >= cfg.max_per_file
                    or per_section.get(section, 0) >= cfg.max_per_section):
                continue
            body = c.content.split("\n\n", 1)[-1]
            sh = _shingles(body)
            if any(_jaccard(sh, o) >= cfg.dup_jaccard for o in shingles):
                continue
            t = count_tokens(c.content)
            if used + t > cfg.token_cap:
                continue
            seen_paths.add(c.heading_path)
            per_file[c.file] = per_file.get(c.file, 0) + 1
            per_section[section] = per_section.get(section, 0) + 1
            shingles.append(sh)
            used += t
            out.append(c)
            if len(out) >= cfg.top_k:
                break
        return out

    # ------------------------------------------------------------------ ops
    async def self_check(self) -> dict:
        """Startup/readiness check. `ok=False` means chat will run chart-facts-only (never fails closed)."""
        problems: list[str] = []
        info: dict = {}
        try:
            info = await self.store.stats()
            if not info.get("active_version"):
                problems.append("no active index version (run python -m app.rag.ingest)")
            elif not info.get("chunks"):
                problems.append("active index has 0 chunks")
            em = getattr(self.embedder, "model_name", None)
            if self.embedder is not None and info.get("embedding_model") and info["embedding_model"] != em:
                if hasattr(self.embedder, "disable"):
                    # incomparable vectors: run keys + full-text only until the index is rebuilt for this model
                    self.embedder.disable("index embedding model mismatch", seconds=24 * 3600.0)
                problems.append(f"embedding model mismatch: index={info['embedding_model']} runtime={em}; "
                                "mixed models silently wreck retrieval. Reindex or fix EMBEDDING_MODEL.")
            if not problems:
                r = await self.retrieve_ex(kb_keys=[], question="saturn transit", system="both")
                if r.degraded or not r.chunks:
                    problems.append(f"probe query returned nothing (degraded={r.degraded}, reason={r.reason})")
        except Exception as exc:  # noqa: BLE001
            problems.append(f"store unreachable: {type(exc).__name__}")
        return {"ok": not problems, "problems": problems, **info, "metrics": self.metrics.snapshot()}


def build_retriever(settings, engine, *, redis=None, reranker=None, config: RetrievalConfig | None = None) -> Retriever:
    """Production wiring: pgvector store on the app's AsyncEngine + lazy fastembed (or none, EMBEDDINGS_RUNTIME=off),
    Redis result cache when a client is given. Call `await retriever.self_check()` at startup and log the result."""
    from app.rag.embeddings import FastEmbedEmbedder
    from app.rag.store import PgVectorStore

    embedder = None if settings.embeddings_runtime == "off" else FastEmbedEmbedder(settings.embedding_model, redis=redis)
    cfg = config or RetrievalConfig(
        top_k=settings.rag_top_k, token_cap=settings.rag_token_cap, per_query=settings.rag_candidates,
        timeout_s=getattr(settings, "rag_timeout_s", 3.0),
        exclude_licences=("modern_author_paraphrase",) if getattr(settings, "rag_exclude_review", False) else (),
        rerank_model=getattr(settings, "rag_rerank_model", None))
    if reranker is None and cfg.rerank_model:
        from app.rag.rerank import CrossEncoderReranker

        reranker = CrossEncoderReranker(cfg.rerank_model)
    return Retriever(PgVectorStore(engine), embedder, config=cfg, reranker=reranker,
                     cache=RedisJsonCache(redis) if redis is not None else None)
