from __future__ import annotations

import pytest

from app.rag.chunking import chunk_markdown
from app.rag.embeddings import HashEmbedder
from app.rag.ingest import run_ingest
from app.rag.store import MemoryStore

A = chunk_markdown("## Saturn\n\nSaturn teaches discipline and structure in the natal chart over long cycles.", "planets.md")
B = chunk_markdown("## Venus\n\nVenus governs love, beauty and values in relationships and money matters.", "houses.md")
B2 = chunk_markdown("## Venus\n\nVenus governs love, beauty and values; this text was rewritten for version two.", "houses.md")
C = chunk_markdown("## Jupiter\n\nJupiter expands optimism, learning and fortune through growth and generosity.", "aspects.md")


class Counting(HashEmbedder):
    def __init__(self, name="hash-bow-384"):
        super().__init__(name)
        self.docs = 0

    async def embed_documents(self, texts):
        self.docs += len(texts)
        return await super().embed_documents(texts)


async def test_idempotent_and_incremental_reuse():
    store, emb = MemoryStore(), Counting()
    r1 = await run_ingest(store, emb, A + B, kb_keys=["saturn transit"], smoke=False)
    assert r1.status == "indexed" and r1.version == 1 and r1.embedded == 2
    r2 = await run_ingest(store, emb, A + B, kb_keys=["saturn transit"], smoke=False)
    assert r2.status == "unchanged" and emb.docs == 2                       # nothing re-embedded
    r3 = await run_ingest(store, emb, A + B2 + C, kb_keys=["saturn transit"], smoke=False)
    assert r3.status == "indexed" and r3.version == 2 and (r3.embedded, r3.copied) == (2, 1)   # only changed + new
    assert emb.docs == 4 and await store.active_version() == 2


async def test_keys_added_without_reindexing_chunks():
    store, emb = MemoryStore(), Counting()
    await run_ingest(store, emb, A, kb_keys=["saturn transit"], smoke=False)
    rep = await run_ingest(store, emb, A, kb_keys=["saturn transit", "venus in libra"], smoke=False)
    assert rep.status == "keys_updated" and rep.version == 1 and await store.key_embedding("venus in libra", 1)


async def test_zero_downtime_readers_see_old_version_until_flip_then_rollback():
    store, emb = MemoryStore(), HashEmbedder()
    await run_ingest(store, emb, A + B, smoke=False)
    seen = []
    orig = store.activate

    async def spy_activate(version, model):
        seen.append(await store.active_version())          # still the OLD version right before the flip
        await orig(version, model)

    store.activate = spy_activate
    await run_ingest(store, emb, A + B2, smoke=False)
    assert seen == [1] and await store.active_version() == 2
    assert set(store.rows) == {1, 2}                                 # previous kept for rollback
    assert await store.rollback() == 1 and await store.active_version() == 1
    assert await store.rollback() == 2                               # and forward again
    await run_ingest(store, emb, A + B2 + C, smoke=False)            # next reindex prunes the oldest
    assert set(store.rows) <= {2, 3}


async def test_model_change_reindexes_everything_and_never_mixes():
    store = MemoryStore()
    await run_ingest(store, Counting("model-a"), A + B, smoke=False)
    emb_b = Counting("model-b")
    rep = await run_ingest(store, emb_b, A + B, smoke=False)
    assert rep.status == "indexed" and rep.copied == 0 and emb_b.docs == 2
    assert await store.model_of(rep.version) == "model-b"


async def test_failed_smoke_test_does_not_activate():
    store, emb = MemoryStore(), HashEmbedder()
    await run_ingest(store, emb, A + B, smoke=False)

    class Broken(MemoryStore):
        pass

    store2 = MemoryStore()
    with pytest.raises(RuntimeError, match="smoke test failed"):
        await run_ingest(store2, emb, [], smoke=True)
    assert await store2.active_version() is None


async def test_rollback_without_previous_raises():
    store = MemoryStore()
    await run_ingest(store, HashEmbedder(), A, smoke=False)
    with pytest.raises(RuntimeError):
        await store.rollback()


async def test_metadata_only_change_updates_in_place_without_reembedding():
    from dataclasses import replace

    store, emb = MemoryStore(), Counting()
    await run_ingest(store, emb, A + B, smoke=False)
    changed = [replace(c, meta={**c.meta, "confidence": "low", "unverified": True}) for c in A + B]
    rep = await run_ingest(store, emb, changed, smoke=False)
    assert rep.status == "metadata_updated" and rep.version == 1 and emb.docs == 2
    assert (await store.existing_meta(1))[A[0].id]["confidence"] == "low"
    again = await run_ingest(store, emb, changed, smoke=False)
    assert again.status == "unchanged"
