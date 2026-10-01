"""Vector store: pgvector on Neon (llm-integration.md §6.4) plus an in-memory twin for tests/eval.

Tables (alembic 004/006/007/008):
  kb_chunks          PK (index_version, id); embedding VECTOR(384); content_tsv weighted (heading A, body B);
                     meta JSONB (source title/author/tradition/tier/licence/language/quality)
  kb_meta            key/value: active_index_version, previous_index_version, embedding_model
  kb_key_embeddings  (index_version, key, embedding, embedding_model): factor kb_keys pre-embedded at index time

`hybrid_search` is ONE SQL round trip: every query vector, the pre-embedded factor keys and every
full-text query run server-side, are fused with weighted Reciprocal Rank Fusion, and only the top
`limit` fused rows come back (content once). The MemoryStore implements the same contract in Python
so unit tests and the eval can cross-check the SQL path.

Versioning: `insert` writes a new index_version beside the live one; `activate` flips
`active_index_version` (remembering the previous one for `rollback`) in a single transaction and
prunes everything older than the previous version. Readers always filter by the active version.
"""

from __future__ import annotations

import json
import math
import re
import time
from dataclasses import dataclass, field
from typing import Any, Iterable, Protocol, Sequence

from app.rag.chunking import Chunk
from app.rag.embeddings import cosine

RRF_K = 60.0


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: str
    file: str
    heading_path: str
    system: str
    content: str
    entities: tuple[str, ...] = ()
    score: float = 0.0
    topics: tuple[str, ...] = ()
    meta: dict = field(default_factory=dict)
    via: tuple[str, ...] = ()          # which queries retrieved it ("q1", "k:saturn dasha", "f:t")

    @property
    def source_title(self) -> str:
        return str(self.meta.get("source_title") or self.file)


@dataclass(frozen=True)
class SearchSpec:
    """Everything one retrieval needs, so a store can run it in a single round trip."""

    version: int
    systems: Sequence[str]
    vectors: Sequence[tuple[str, list[float], float]] = ()   # (label, embedding, weight)
    keys: Sequence[str] = ()                                  # pre-embedded factor keys
    key_weight: float = 0.4
    fts: Sequence[tuple[str, str, float]] = ()                # (label, tsquery text "a | b", weight)
    per_query: int = 20                                       # candidates per query before fusion
    limit: int = 30                                           # fused rows returned


class VectorStore(Protocol):
    async def active_version(self) -> int | None: ...
    async def hybrid_search(self, spec: SearchSpec) -> list[RetrievedChunk]: ...
    async def key_embedding(self, key: str, version: int) -> list[float] | None: ...
    async def stats(self) -> dict: ...


def vec_literal(v: list[float]) -> str:
    return "[" + ",".join(f"{x:.7f}" for x in v) + "]"


def _words(s: str) -> list[str]:
    return re.findall(r"[a-z0-9]+|[\u0900-\u097F]+", s.lower())


def tsquery_text(terms: Iterable[str]) -> str:
    """OR query for to_tsquery. Only [a-z0-9] and Devanagari letters survive, so nothing can inject tsquery syntax."""
    seen: dict[str, None] = {}
    for t in terms:
        for w in _words(t):
            if len(w) > 1:
                seen.setdefault(w, None)
    return " | ".join(seen)


# ----------------------------------------------------------------------------- in-memory


class MemoryStore:
    def __init__(self) -> None:
        self.rows: dict[int, dict[str, tuple[Chunk, list[float]]]] = {}
        self.keys: dict[int, dict[str, list[float]]] = {}
        self.meta: dict[str, str] = {}

    # ---- writes
    async def insert(self, version: int, chunks: list[Chunk], vectors: list[list[float]], model: str) -> None:
        self.rows.setdefault(version, {}).update({c.id: (c, v) for c, v in zip(chunks, vectors)})
        self.meta[f"model:{version}"] = model

    async def insert_keys(self, version: int, keys: list[str], vectors: list[list[float]], model: str) -> None:
        self.keys.setdefault(version, {}).update(dict(zip(keys, vectors)))

    async def existing(self, version: int) -> dict[str, str]:
        return {cid: c.content_sha256 for cid, (c, _) in self.rows.get(version, {}).items()}

    async def model_of(self, version: int) -> str | None:
        return self.meta.get(f"model:{version}")

    async def existing_meta(self, version: int) -> dict[str, dict]:
        return {cid: dict(c.meta) for cid, (c, _) in self.rows.get(version, {}).items()}

    async def update_meta(self, version: int, items: dict[str, dict], chunks: dict[str, Chunk]) -> None:
        from dataclasses import replace

        rows = self.rows.get(version, {})
        for cid, meta in items.items():
            if cid in rows:
                old, vec = rows[cid]
                rows[cid] = (replace(old, meta=meta, system=chunks[cid].system, topics=chunks[cid].topics,
                                     entities=chunks[cid].entities), vec)

    async def max_version(self) -> int:
        return max(self.rows, default=0)

    async def key_count(self, version: int) -> int:
        return len(self.keys.get(version, {}))

    async def copy_rows(self, src: int, dst: int, ids: list[str]) -> None:
        rows = self.rows.get(src, {})
        self.rows.setdefault(dst, {}).update({i: rows[i] for i in ids if i in rows})
        self.meta[f"model:{dst}"] = self.meta.get(f"model:{src}", "")

    async def activate(self, version: int, model: str) -> None:
        old = self.meta.get("active_index_version")
        self.meta["active_index_version"] = str(version)
        self.meta["embedding_model"] = model
        if old and int(old) != version:
            self.meta["previous_index_version"] = old
        keep = {version, int(self.meta.get("previous_index_version", version))}
        for v in list(self.rows):
            if v not in keep:
                self.rows.pop(v, None)
                self.keys.pop(v, None)

    async def rollback(self) -> int:
        prev = self.meta.get("previous_index_version")
        if not prev or int(prev) not in self.rows:
            raise RuntimeError("no previous index version to roll back to")
        cur = self.meta["active_index_version"]
        self.meta["active_index_version"], self.meta["previous_index_version"] = prev, cur
        self.meta["embedding_model"] = self.meta.get(f"model:{prev}", self.meta.get("embedding_model", ""))
        return int(prev)

    # ---- reads
    async def active_version(self) -> int | None:
        v = self.meta.get("active_index_version")
        return int(v) if v else None

    async def key_embedding(self, key, version):
        return self.keys.get(version, {}).get(key)

    async def stats(self) -> dict:
        v = await self.active_version()
        return {"active_version": v, "chunks": len(self.rows.get(v, {})) if v else 0,
                "embedding_model": self.meta.get("embedding_model")}

    @staticmethod
    def _rc(c: Chunk, score: float, via: tuple[str, ...] = ()) -> RetrievedChunk:
        return RetrievedChunk(c.id, c.file, c.heading_path, c.system, c.content, c.entities, score,
                              c.topics, dict(c.meta), via)

    def _fts_rank(self, c: Chunk, terms: set[str]) -> float:
        head, body = set(_words(c.heading_path)), _words(c.content)
        bset = set(body)
        s = 2.0 * len(terms & head) + 1.0 * len(terms & bset)
        s += 0.05 * sum(1 for w in body if w in terms)
        return s

    async def hybrid_search(self, spec: SearchSpec) -> list[RetrievedChunk]:
        systems = set(spec.systems)
        pool = [(c, v) for c, v in self.rows.get(spec.version, {}).values() if c.system in systems]
        fused: dict[str, float] = {}
        via: dict[str, list[tuple[float, str]]] = {}
        by_id = {c.id: c for c, _ in pool}

        def add(label: str, w: float, ranked: list[str]) -> None:
            for rn, cid in enumerate(ranked[: spec.per_query], 1):
                s = w / (RRF_K + rn)
                fused[cid] = fused.get(cid, 0.0) + s
                via.setdefault(cid, []).append((s, label))

        vecs = list(spec.vectors)
        for k in spec.keys:
            kv = self.keys.get(spec.version, {}).get(k)
            if kv is not None:
                vecs.append((f"k:{k}", kv, spec.key_weight))
        for label, emb, w in vecs:
            ranked = sorted(pool, key=lambda cv: cosine(emb, cv[1]), reverse=True)
            add(label, w, [c.id for c, _ in ranked])
        for label, q, w in spec.fts:
            terms = set(_words(q.replace("|", " ")))
            scored = [(self._fts_rank(c, terms), c.id) for c, _ in pool]
            scored = [x for x in scored if x[0] > 0]
            scored.sort(key=lambda x: x[0], reverse=True)
            add(label, w, [cid for _, cid in scored])
        top = sorted(fused.items(), key=lambda kv: kv[1], reverse=True)[: spec.limit]
        return [self._rc(by_id[cid], s, tuple(l for _, l in sorted(via[cid], reverse=True))) for cid, s in top]


# ----------------------------------------------------------------------------- pgvector

_HYBRID_SQL = """
WITH qv AS (
  SELECT 'q' || t.ord AS label, t.w AS w, CAST(t.v AS vector) AS emb
  FROM unnest(CAST(:vecs AS text[]), CAST(:vw AS float8[])) WITH ORDINALITY AS t(v, w, ord)
), kv AS (
  SELECT 'k:' || key AS label, CAST(:kw AS float8) AS w, embedding AS emb
  FROM kb_key_embeddings WHERE index_version = :v AND key = ANY(CAST(:keys AS text[]))
), allq AS (
  SELECT label, w, emb FROM qv UNION ALL SELECT label, w, emb FROM kv
), vhits AS (
  SELECT a.label, a.w, c.id, c.rn FROM allq a CROSS JOIN LATERAL (
    SELECT id, row_number() OVER (ORDER BY embedding <=> a.emb) AS rn
    FROM kb_chunks WHERE index_version = :v AND system = ANY(CAST(:systems AS text[]))
    ORDER BY embedding <=> a.emb LIMIT :per) c
), fq AS (
  SELECT t.label, t.w, to_tsquery('english', t.q) AS q
  FROM unnest(CAST(:fl AS text[]), CAST(:fq AS text[]), CAST(:fw AS float8[])) AS t(label, q, w)
), fhits AS (
  SELECT f.label, f.w, c.id, c.rn FROM fq f CROSS JOIN LATERAL (
    SELECT id, row_number() OVER (ORDER BY ts_rank_cd(content_tsv, f.q, 32) DESC) AS rn
    FROM kb_chunks WHERE index_version = :v AND system = ANY(CAST(:systems AS text[])) AND content_tsv @@ f.q
    ORDER BY ts_rank_cd(content_tsv, f.q, 32) DESC LIMIT :per) c
), hits AS (
  SELECT * FROM vhits UNION ALL SELECT * FROM fhits
), fused AS (
  SELECT id, sum(w / (60.0 + rn)) AS score, array_agg(label ORDER BY w / (60.0 + rn) DESC) AS via
  FROM hits GROUP BY id ORDER BY score DESC LIMIT :lim
)
SELECT c.id, c.file, c.heading_path, c.system, c.content, c.entities, c.topics, {meta} AS meta, f.score, f.via
FROM fused f JOIN kb_chunks c ON c.index_version = :v AND c.id = f.id
ORDER BY f.score DESC
"""


class PgVectorStore:
    """`engine` is a SQLAlchemy AsyncEngine (asyncpg). Short-lived connections per query, so no
    pooled connection is held across an LLM call."""

    ACTIVE_TTL_S = 300.0

    def __init__(self, engine: Any) -> None:
        self.engine = engine
        self._active: tuple[int | None, float] = (None, 0.0)
        self._has_meta: bool | None = None

    async def _fetch(self, sql: str, **params) -> list[Any]:
        from sqlalchemy import text

        async with self.engine.connect() as conn:
            res = await conn.execute(text(sql), params)
            return list(res.mappings().all())

    def invalidate_cache(self) -> None:
        self._active = (None, 0.0)

    async def active_version(self) -> int | None:
        v, at = self._active
        if v is not None and time.monotonic() - at < self.ACTIVE_TTL_S:
            return v
        rows = await self._fetch("SELECT value FROM kb_meta WHERE key = 'active_index_version'")
        v = int(rows[0]["value"]) if rows else None
        self._active = (v, time.monotonic())
        return v

    async def _meta_col(self) -> str:
        if self._has_meta is None:
            rows = await self._fetch("SELECT 1 FROM information_schema.columns "
                                     "WHERE table_name = 'kb_chunks' AND column_name = 'meta'")
            self._has_meta = bool(rows)
        return "c.meta" if self._has_meta else "'{}'::jsonb"

    async def hybrid_search(self, spec: SearchSpec) -> list[RetrievedChunk]:
        vecs = [(vec_literal(v), w) for _, v, w in spec.vectors]
        fts = [(lab, q, w) for lab, q, w in spec.fts if q.strip()]
        sql = _HYBRID_SQL.format(meta=await self._meta_col())
        rows = await self._fetch(
            sql, v=spec.version, systems=list(spec.systems), vecs=[a for a, _ in vecs], vw=[float(b) for _, b in vecs],
            keys=list(spec.keys), kw=float(spec.key_weight), fl=[a for a, _, _ in fts], fq=[b for _, b, _ in fts],
            fw=[float(c) for _, _, c in fts], per=spec.per_query, lim=spec.limit)
        out = []
        for r in rows:
            meta = r["meta"] if isinstance(r["meta"], dict) else json.loads(r["meta"] or "{}")
            out.append(RetrievedChunk(r["id"], r["file"], r["heading_path"], r["system"], r["content"],
                                      tuple(r["entities"] or ()), float(r["score"]), tuple(r["topics"] or ()),
                                      meta, tuple(r["via"] or ())))
        return out

    async def key_embedding(self, key, version):
        rows = await self._fetch(
            "SELECT embedding::text AS e FROM kb_key_embeddings WHERE index_version = :v AND key = :k", v=version, k=key)
        if not rows:
            return None
        return [float(x) for x in rows[0]["e"].strip("[]").split(",")]

    async def stats(self) -> dict:
        v = await self.active_version()
        rows = await self._fetch("SELECT count(*) AS n FROM kb_chunks WHERE index_version = :v", v=v or -1)
        meta = {r["key"]: r["value"] for r in await self._fetch("SELECT key, value FROM kb_meta")}
        keys = await self._fetch("SELECT count(*) AS n FROM kb_key_embeddings WHERE index_version = :v", v=v or -1)
        return {"active_version": v, "chunks": int(rows[0]["n"]), "key_embeddings": int(keys[0]["n"]),
                "embedding_model": meta.get("embedding_model"), "previous_version": meta.get("previous_index_version")}

    # ---- writes (offline ingest only) ----
    async def existing(self, version: int) -> dict[str, str]:
        rows = await self._fetch("SELECT id, content_sha256 FROM kb_chunks WHERE index_version = :v", v=version)
        return {r["id"]: r["content_sha256"] for r in rows}

    async def existing_meta(self, version: int) -> dict[str, dict]:
        if await self._meta_col() == "'{}'::jsonb":
            return {}
        rows = await self._fetch("SELECT id, meta FROM kb_chunks WHERE index_version = :v", v=version)
        return {r["id"]: (r["meta"] if isinstance(r["meta"], dict) else json.loads(r["meta"] or "{}")) for r in rows}

    async def update_meta(self, version: int, items: dict[str, dict], chunks: dict[str, Chunk]) -> None:
        """Metadata-only change: UPDATE in place (no re-embedding). `system`, topics and entities ride along."""
        from sqlalchemy import text

        sql = text("UPDATE kb_chunks SET meta = CAST(:m AS jsonb), system = :sys, topics = :t, entities = :e "
                   "WHERE index_version = :v AND id = :id")
        async with self.engine.begin() as conn:
            await conn.execute(sql, [{"m": json.dumps(meta, ensure_ascii=False), "sys": chunks[cid].system,
                                      "t": list(chunks[cid].topics), "e": list(chunks[cid].entities), "v": version, "id": cid}
                                     for cid, meta in items.items()])

    async def model_of(self, version: int) -> str | None:
        rows = await self._fetch(
            "SELECT DISTINCT embedding_model FROM kb_chunks WHERE index_version = :v", v=version)
        models = {r["embedding_model"] for r in rows}
        if len(models) > 1:
            raise RuntimeError(f"index version {version} mixes embedding models: {models}")
        return next(iter(models), None)

    async def insert(self, version: int, chunks: list[Chunk], vectors: list[list[float]], model: str) -> None:
        from sqlalchemy import text

        has_meta = (await self._meta_col()) != "'{}'::jsonb"
        cols = "id, index_version, file, heading_path, system, topics, entities, content, embedding, embedding_model, content_sha256"
        vals = ":id, :v, :file, :hp, :system, :topics, :entities, :content, CAST(:emb AS vector), :model, :sha"
        if has_meta:
            cols += ", meta"
            vals += ", CAST(:meta AS jsonb)"
        sql = text(f"INSERT INTO kb_chunks ({cols}) VALUES ({vals})")
        rows = []
        for c, vec in zip(chunks, vectors):
            r = {"id": c.id, "v": version, "file": c.file, "hp": c.heading_path, "system": c.system,
                 "topics": list(c.topics), "entities": list(c.entities), "content": c.content,
                 "emb": vec_literal(vec), "model": model, "sha": c.content_sha256}
            if has_meta:
                r["meta"] = json.dumps(c.meta, ensure_ascii=False)
            rows.append(r)
        async with self.engine.begin() as conn:
            await conn.execute(sql, rows)

    async def insert_keys(self, version: int, keys: list[str], vectors: list[list[float]], model: str) -> None:
        from sqlalchemy import text

        sql = text("""INSERT INTO kb_key_embeddings (index_version, key, embedding, embedding_model)
                      VALUES (:v, :k, CAST(:emb AS vector), :model)
                      ON CONFLICT (index_version, key) DO UPDATE SET embedding = EXCLUDED.embedding,
                                                                     embedding_model = EXCLUDED.embedding_model""")
        async with self.engine.begin() as conn:
            await conn.execute(sql, [{"v": version, "k": k, "emb": vec_literal(v), "model": model}
                                     for k, v in zip(keys, vectors)])

    async def activate(self, version: int, model: str) -> None:
        """Flip the active version in ONE transaction; keep the previous version for rollback and
        prune everything older. Readers never see a half-built index."""
        from sqlalchemy import text

        async with self.engine.begin() as conn:
            old = (await conn.execute(text("SELECT value FROM kb_meta WHERE key='active_index_version' FOR UPDATE"))).scalar()
            upserts = [("active_index_version", str(version)), ("embedding_model", model)]
            if old is not None and int(old) != version:
                upserts.append(("previous_index_version", str(old)))
            for k, v in upserts:
                await conn.execute(text("""INSERT INTO kb_meta (key, value) VALUES (:k, :v)
                                           ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value"""), {"k": k, "v": v})
            prev = (await conn.execute(text("SELECT value FROM kb_meta WHERE key='previous_index_version'"))).scalar()
            keep = [version] + ([int(prev)] if prev is not None else [])
            await conn.execute(text("DELETE FROM kb_chunks WHERE index_version <> ALL(CAST(:keep AS int[]))"), {"keep": keep})
            await conn.execute(text("DELETE FROM kb_key_embeddings WHERE index_version <> ALL(CAST(:keep AS int[]))"),
                               {"keep": keep})
        self._active = (version, time.monotonic())

    async def rollback(self) -> int:
        """Swap active and previous. Instant; no data is rebuilt."""
        from sqlalchemy import text

        async with self.engine.begin() as conn:
            cur = (await conn.execute(text("SELECT value FROM kb_meta WHERE key='active_index_version' FOR UPDATE"))).scalar()
            prev = (await conn.execute(text("SELECT value FROM kb_meta WHERE key='previous_index_version'"))).scalar()
            if prev is None:
                raise RuntimeError("no previous index version to roll back to")
            n = (await conn.execute(text("SELECT count(*) FROM kb_chunks WHERE index_version = :v"), {"v": int(prev)})).scalar()
            if not n:
                raise RuntimeError(f"previous version {prev} has no rows (already pruned)")
            model = (await conn.execute(text("SELECT embedding_model FROM kb_chunks WHERE index_version=:v LIMIT 1"),
                                        {"v": int(prev)})).scalar()
            for k, v in (("active_index_version", str(prev)), ("previous_index_version", str(cur)),
                         ("embedding_model", model or "")):
                await conn.execute(text("""INSERT INTO kb_meta (key, value) VALUES (:k, :v)
                                           ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value"""), {"k": k, "v": v})
        self._active = (int(prev), time.monotonic())
        return int(prev)

    async def max_version(self) -> int:
        rows = await self._fetch("SELECT COALESCE(MAX(index_version), 0) AS m FROM kb_chunks")
        return int(rows[0]["m"])

    async def key_count(self, version: int) -> int:
        rows = await self._fetch("SELECT count(*) AS n FROM kb_key_embeddings WHERE index_version = :v", v=version)
        return int(rows[0]["n"])

    async def copy_rows(self, src: int, dst: int, ids: list[str]) -> None:
        """Copy unchanged chunks (embedding included) from the live version: no re-embedding."""
        from sqlalchemy import text

        meta = "meta" if await self._meta_col() != "'{}'::jsonb" else None
        cols = ("id, file, heading_path, system, topics, entities, content, embedding, embedding_model, content_sha256"
                + (", meta" if meta else ""))
        async with self.engine.begin() as conn:
            await conn.execute(text(f"INSERT INTO kb_chunks (index_version, {cols}) SELECT :dst, {cols} FROM kb_chunks "
                                    f"WHERE index_version = :src AND id = ANY(CAST(:ids AS text[]))"),
                               {"src": src, "dst": dst, "ids": ids})
