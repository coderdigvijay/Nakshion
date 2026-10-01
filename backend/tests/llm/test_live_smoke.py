"""OPTIONAL live smoke tests. Skipped by default; never run in CI.

    NAKSHION_LIVE_LLM=1 GEMINI_API_KEY=... ANTHROPIC_API_KEY=... pytest tests/llm/test_live_smoke.py
    NAKSHION_LIVE_EMBED=1 pytest tests/llm/test_live_smoke.py -k embed    # downloads bge-small (~67 MB)

Uses a synthetic chart only (no real user data). Costs a fraction of a cent per run.
"""

from __future__ import annotations

import os

import pytest

from app.llm.config import LLMSettings
from app.llm.errors import LLMError
from app.llm.providers import build_providers
from app.llm.router import LLMRouter
from app.llm.schemas import ChatAnswer, provider_schema
from app.llm.types import LLMRequest

LIVE = os.environ.get("NAKSHION_LIVE_LLM") == "1"
_S = LLMSettings()  # env + backend/.env, numbered keys supported
HAS_GEMINI = bool(_S.gemini_keys())
HAS_ANTHROPIC = bool(_S.anthropic_keys())

REQ = LLMRequest(task="chat", system="You are a terse test assistant. Reply in JSON only.",
                 context_blocks=("CHART FACTS\n[N.SUN.SIGN.CANCER] Natal Sun in Cancer (tropical)",),
                 messages=({"role": "user", "content": "In one sentence, what does my Sun sign suggest? Cite the ID."},),
                 max_output_tokens=300, response_schema=provider_schema(ChatAnswer), temperature=0.3, timeout_s=30,
                 prompt_id="smoke@v0")


@pytest.mark.skipif(not (LIVE and HAS_GEMINI), reason="live Gemini smoke disabled")
async def test_live_gemini_structured():
    s = LLMSettings()
    router = LLMRouter(s, {"gemini": build_providers(s)["gemini"]})
    res = await router.generate(REQ, schema=ChatAnswer, models=[s.model_chat], deadline_s=60)
    assert res.parsed["answer"] and res.input_tokens > 0


@pytest.mark.skipif(not (LIVE and HAS_ANTHROPIC), reason="live Anthropic smoke disabled")
@pytest.mark.parametrize("task", ["chat", "premium_report"])
async def test_live_anthropic_structured(task):
    s = LLMSettings()
    router = LLMRouter(s, {"anthropic": build_providers(s)["anthropic"]})
    model = next(m for m in s.chain_for(task) if m.startswith("claude-"))
    try:
        res = await router.generate(REQ, schema=ChatAnswer, models=[model], deadline_s=90)
    except LLMError as exc:  # surface the mapped class, never the raw SDK text
        pytest.fail(f"{type(exc).__name__}: {exc}")
    assert res.parsed["answer"]


@pytest.mark.skipif(not (LIVE and HAS_GEMINI), reason="live Gemini smoke disabled")
async def test_live_gemini_stream():
    s = LLMSettings()
    router = LLMRouter(s, {"gemini": build_providers(s)["gemini"]})
    chunks = [c async for c in router.stream(REQ.with_(response_schema=None), models=[s.model_chat])]
    assert "".join(c.text for c in chunks) and chunks[-1].final is not None


@pytest.mark.skipif(os.environ.get("NAKSHION_LIVE_EMBED") != "1", reason="live embedding model download disabled")
async def test_live_embed_bge_small():
    from app.rag.embeddings import FastEmbedEmbedder, cosine

    e = FastEmbedEmbedder()
    docs = await e.embed_documents(["Saturn transits test structure and patience.", "Venus rules love and beauty."])
    q = await e.embed_query("saturn transit")
    assert len(q) == 384 and cosine(q, docs[0]) > cosine(q, docs[1])
