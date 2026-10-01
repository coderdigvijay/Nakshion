"""Offline knowledge-base indexer (llm-integration.md §6.2-6.4). Never runs in the web process.

    python -m app.rag.ingest --dry-run                       # chunk/tier/dup stats, no DB, no model
    python -m app.rag.ingest --status   --database-url ...   # active/previous version, chunk + key counts
    python -m app.rag.ingest            --database-url ...   # incremental, zero-downtime reindex
    python -m app.rag.ingest --rollback --database-url ...   # flip back to the previous index version
        [--kb-dir backend/knowledge_base] [--kb-keys-file keys.txt | --no-keys] [--model e5-small] [--force]

Protocol: build version n+1 beside the live one (unchanged chunks are COPIED from n, only new/changed text
is embedded), pre-embed the factor kb_keys, run a retrieval smoke test on n+1, then flip
`kb_meta.active_index_version` in one transaction. The previous version is kept for `--rollback` and
pruned on the NEXT reindex. Idempotent: an unchanged corpus + model + key set is a no-op. Refuses to mix
embedding models inside one version.
"""

from __future__ import annotations

import argparse
import asyncio
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path

from app.rag.chunking import Chunk, chunk_corpus, near_duplicates
from app.rag.embeddings import Embedder
from app.rag.sources import load_override, source_info
from app.rag.store import SearchSpec

DEFAULT_KB = Path(__file__).resolve().parents[2] / "knowledge_base"
SMOKE_QUERIES = ("saturn transit", "moon nakshatra", "venus in libra", "seventh house partnership")


@dataclass
class IngestReport:
    status: str           # unchanged | indexed | keys_updated | metadata_updated | dry_run
    version: int | None
    chunks: int
    keys: int = 0
    embedded: int = 0     # chunks actually embedded (the rest were copied)
    copied: int = 0


def _norm_meta(meta: dict | None) -> str:
    import json as _json

    return _json.dumps(meta or {}, sort_keys=True, ensure_ascii=False)


async def _smoke(store, embedder, version: int) -> None:
    for q in SMOKE_QUERIES:
        vec = await embedder.embed_query(q)
        hits = await store.hybrid_search(SearchSpec(version=version, systems=["vedic", "western", "both"],
                                                    vectors=[("q1", vec, 1.0)], limit=3))
        if not hits:
            raise RuntimeError(f"smoke test failed for {q!r}; version {version} not activated")


async def run_ingest(store, embedder: Embedder, chunks: list[Chunk], *, kb_keys: list[str] | None = None,
                     force: bool = False, batch: int = 64, smoke: bool = True) -> IngestReport:
    want = {c.id: c.content_sha256 for c in chunks}
    keys = sorted({k.strip().lower() for k in (kb_keys or []) if k.strip()})
    active = await store.active_version()
    same_model = False
    by_id = {c.id: c for c in chunks}
    if active is not None:
        same_model = (await store.model_of(active)) == embedder.model_name
        existing = await store.existing(active)
        if same_model and existing == want and not force:
            # text identical: refresh metadata in place when it changed (confidence, system tag, flags) - no re-embedding
            old_meta = await store.existing_meta(active) if hasattr(store, "existing_meta") else {}
            stale = {cid: c.meta for cid, c in by_id.items() if _norm_meta(old_meta.get(cid)) != _norm_meta(c.meta)}
            if stale and hasattr(store, "update_meta"):
                await store.update_meta(active, stale, by_id)
                return IngestReport("metadata_updated", active, len(chunks), len(keys), embedded=0, copied=len(stale))
            if keys and hasattr(store, "key_count") and await store.key_count(active) != len(keys):
                await store.insert_keys(active, keys, await embedder.embed_queries(keys), embedder.model_name)
                return IngestReport("keys_updated", active, len(chunks), len(keys))
            return IngestReport("unchanged", active, len(chunks), len(keys))
    version = (await store.max_version() if hasattr(store, "max_version") else (active or 0)) + 1
    # reuse embeddings of chunks whose text AND model are unchanged
    reuse: list[str] = []
    if active is not None and same_model and not force and hasattr(store, "copy_rows"):
        old = await store.existing(active)
        reuse = [cid for cid, sha in want.items() if old.get(cid) == sha]
        if reuse:
            await store.copy_rows(active, version, reuse)
    todo = [c for c in chunks if c.id not in set(reuse)]
    for i in range(0, len(todo), batch):
        part = todo[i: i + batch]
        vecs = await embedder.embed_documents([c.content for c in part])
        if any(len(v) != embedder.dim for v in vecs):
            raise RuntimeError("embedding dimension mismatch")
        await store.insert(version, part, vecs, embedder.model_name)
    if keys:
        await store.insert_keys(version, keys, await embedder.embed_queries(keys), embedder.model_name)
    if smoke:
        await _smoke(store, embedder, version)
    if await store.model_of(version) != embedder.model_name:
        raise RuntimeError("model mismatch inside new version")
    await store.activate(version, embedder.model_name)
    return IngestReport("indexed", version, len(chunks), len(keys), embedded=len(todo), copied=len(reuse))


def dry_run_report(chunks: list[Chunk]) -> str:
    toks = [c.tokens for c in chunks]
    by_sys: dict[str, int] = {}
    by_tier: dict[int, int] = {}
    review = 0
    for c in chunks:
        by_sys[c.system] = by_sys.get(c.system, 0) + 1
        by_tier[c.meta.get("tier", 1)] = by_tier.get(c.meta.get("tier", 1), 0) + 1
        review += bool(c.meta.get("review"))
    dups = near_duplicates(chunks, 0.6)
    low = sorted(chunks, key=lambda c: c.quality)[:3]
    lines = [f"chunks={len(chunks)} tokens: min={min(toks)} median={int(statistics.median(toks))} max={max(toks)} "
             f"total={sum(toks)}",
             f"by_system={by_sys} by_tier={dict(sorted(by_tier.items()))} review_flagged={review}",
             f"near-duplicate pairs (jaccard>=0.6): {len(dups)}",
             "lowest quality: " + ", ".join(f"{c.id.split('#')[0]}:{c.quality}" for c in low)]
    return "\n".join(lines)


def _async_url(url: str) -> str:
    for p in ("postgres://", "postgresql://"):
        if url.startswith(p):
            return "postgresql+asyncpg://" + url[len(p):]
    return url


async def _main(args) -> int:
    kb = Path(args.kb_dir)
    load_override(kb)
    chunks = chunk_corpus(kb)
    print(dry_run_report(chunks))
    if args.dry_run:
        from app.rag.keys import generate_keys

        print(f"factor kb_keys to pre-embed: {len(generate_keys())}")
        return 0
    if not args.database_url:
        print("--database-url (or DATABASE_URL) is required", file=sys.stderr)
        return 2
    from sqlalchemy.ext.asyncio import create_async_engine

    from app.rag.embeddings import make_embedder
    from app.rag.keys import generate_keys
    from app.rag.store import PgVectorStore

    engine = create_async_engine(_async_url(args.database_url), pool_size=1, max_overflow=0)
    store = PgVectorStore(engine)
    try:
        if args.status:
            print(await store.stats())
            return 0
        if args.rollback:
            print(f"rolled back: active index version is now {await store.rollback()}")
            return 0
        if args.kb_keys_file:
            keys = Path(args.kb_keys_file).read_text(encoding="utf-8").splitlines()
        else:
            keys = [] if args.no_keys else generate_keys()
        rep = await run_ingest(store, make_embedder(args.model, threads=None), chunks, kb_keys=keys, force=args.force)
    finally:
        await engine.dispose()
    print(f"{rep.status}: version={rep.version} chunks={rep.chunks} keys={rep.keys} "
          f"embedded={rep.embedded} copied={rep.copied}")
    return 0


def main() -> int:
    import os

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kb-dir", default=str(DEFAULT_KB))
    ap.add_argument("--database-url", default=os.environ.get("DATABASE_URL"))
    ap.add_argument("--kb-keys-file", default=None, help="newline-separated factor kb_keys (default: generated)")
    ap.add_argument("--no-keys", action="store_true", help="skip pre-embedding factor keys")
    ap.add_argument("--model", default=os.environ.get("RAG_EMBEDDER", "bge-small"),
                    help="embedder spec: bge-small | bge-small-q | minilm-ml | e5-small | e5-small-fp32")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--rollback", action="store_true")
    return asyncio.run(_main(ap.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
