from __future__ import annotations

import asyncio

import pytest

from app.llm.budget import BudgetGuard, MemoryCounter
from app.llm.errors import (
    LLMBadRequest,
    LLMBlocked,
    LLMRateLimited,
    LLMServerError,
    LLMUnavailable,
)
from app.llm.providers.fake import FakeProvider
from app.llm.resilience import CircuitBreaker, TokenBucket
from app.llm.router import LLMRouter
from app.llm.schemas import ChatAnswer
from app.llm.types import LLMRequest
from app.llm.usage import MemoryUsageSink

from .conftest import chat_json


def req(**kw) -> LLMRequest:
    base = dict(task="chat", system="sys", context_blocks=("facts",),
                messages=({"role": "user", "content": "hi"},), max_output_tokens=100, timeout_s=2.0,
                prompt_id="chat@v1", metadata={"user_id": "u1", "user_id_hash": "h1"})
    base.update(kw)
    return LLMRequest(**base)


def two(settings, p1: FakeProvider, p2: FakeProvider, **kw) -> LLMRouter:
    # both fakes share provider key "fake"; route by model via a dispatching provider
    class Dispatch:
        name = "fake"

        async def generate(self, r, model):
            return await (p1 if model == "fake-primary" else p2).generate(r, model)

        def stream(self, r, model):
            return (p1 if model == "fake-primary" else p2).stream(r, model)

    return LLMRouter(settings, {"fake": Dispatch()}, **kw)


async def test_primary_success_records_usage(settings):
    sink = MemoryUsageSink()
    p1 = FakeProvider([chat_json("hello there", [])])
    r = two(settings, p1, FakeProvider(), usage_sink=sink)
    res = await r.generate(req(), schema=ChatAnswer)
    assert res.parsed["answer"] == "hello there"
    assert [u.outcome for u in sink.records] == ["ok"]
    assert sink.records[0].user_id_hash == "h1" and sink.records[0].prompt_version == "chat@v1"
    # metadata is never forwarded to the provider beyond the request object; adapters ignore it
    assert sink.records[0].cost_usd > 0


async def test_retryable_error_retries_once_then_falls_over(settings):
    from app.llm.errors import LLMTimeout

    p1 = FakeProvider([LLMTimeout("slow"), LLMServerError("503", status=503)])   # timeout retries; 503 does not
    p2 = FakeProvider(["ok-from-secondary"])
    r = two(settings, p1, p2)
    res = await r.generate(req(), deadline_s=20)
    assert res.text == "ok-from-secondary"
    assert len(p1.calls) == 2 and len(p2.calls) == 1


async def test_non_retryable_skips_retry(settings):
    p1 = FakeProvider([LLMBadRequest("400")])
    p2 = FakeProvider(["second"])
    r = two(settings, p1, p2)
    assert (await r.generate(req(), deadline_s=20)).text == "second"
    assert len(p1.calls) == 1


async def test_safety_block_moves_to_next_provider(settings):
    sink = MemoryUsageSink()
    p1 = FakeProvider([LLMBlocked("refusal")])
    r = two(settings, p1, FakeProvider(["fine"]), usage_sink=sink)
    assert (await r.generate(req(), deadline_s=20)).text == "fine"
    assert "blocked" in [u.outcome for u in sink.records]


async def test_schema_invalid_repairs_once_on_same_provider(settings):
    sink = MemoryUsageSink()
    p1 = FakeProvider(["not json", chat_json("fixed", [])])
    r = two(settings, p1, FakeProvider(), usage_sink=sink)
    res = await r.generate(req(), schema=ChatAnswer)
    assert res.parsed["answer"] == "fixed"
    assert len(p1.calls) == 2
    repair_msgs = p1.calls[1][0].messages
    assert repair_msgs[-2]["role"] == "assistant" and "not valid JSON" in repair_msgs[-1]["content"]
    assert [u.outcome for u in sink.records] == ["invalid", "repaired"]


async def test_schema_invalid_twice_goes_to_next_provider(settings):
    p1 = FakeProvider(["{}", '{"answer": ""}'])
    p2 = FakeProvider([chat_json("from p2", [])])
    res = await two(settings, p1, p2).generate(req(), schema=ChatAnswer)
    assert res.parsed["answer"] == "from p2"


async def test_truncated_structured_output_is_failure(settings):
    p1 = FakeProvider([chat_json("x", [])] * 2, finish_reason="length")
    p2 = FakeProvider([chat_json("complete", [])])
    res = await two(settings, p1, p2).generate(req(), schema=ChatAnswer)
    assert res.parsed["answer"] == "complete"


async def test_all_fail_raises_unavailable(settings):
    r = two(settings, FakeProvider([LLMBadRequest("x")]), FakeProvider([LLMBadRequest("y")]))
    with pytest.raises(LLMUnavailable):
        await r.generate(req(), deadline_s=20)


async def test_timeout_falls_over(settings):
    slow = FakeProvider(["late"], delay_s=5)
    r = two(settings, slow, FakeProvider(["fast"]))
    res = await r.generate(req(timeout_s=0.2), deadline_s=20)
    assert res.text == "fast"


async def test_no_configured_provider(settings):
    with pytest.raises(LLMUnavailable):
        await LLMRouter(settings, {}).generate(req())


async def test_budget_records_spend(settings):
    counter = MemoryCounter()
    guard = BudgetGuard(settings, counter)
    r = two(settings, FakeProvider(["a"]), FakeProvider(), budget=guard)
    await r.generate(req())
    assert await guard.ratio() > 0


def test_circuit_breaker_opens_and_half_opens():
    t = [0.0]
    br = CircuitBreaker(failures=5, window_s=60, open_s=60, clock=lambda: t[0])
    for _ in range(5):
        br.record_failure()
    assert br.state == "open" and not br.allow()
    t[0] = 61
    assert br.state == "half_open" and br.allow() and not br.allow()  # one probe only
    br.record_success()
    assert br.state == "closed"


async def test_open_breaker_skips_provider(settings):
    p1, p2 = FakeProvider(["p1"]), FakeProvider(["p2"])
    r = two(settings, p1, p2)
    for key in ("fake:fake-primary", "fake:fake-secondary"):
        for _ in range(5):
            r.breaker(key).record_failure()
    with pytest.raises(LLMUnavailable):
        await r.generate(req())
    assert not p1.calls and not p2.calls


async def test_token_bucket_denies_when_wait_too_long():
    b = TokenBucket(rpm=1)
    assert await b.acquire(0.01)
    assert not await b.acquire(0.01)


async def test_stream_falls_over_before_first_token(settings):
    p1 = FakeProvider([LLMServerError("down")])
    p2 = FakeProvider(["streamed text"])
    chunks = [c async for c in two(settings, p1, p2).stream(req())]
    assert "".join(c.text for c in chunks) == "streamed text" and chunks[-1].final is not None


async def test_stream_failure_after_first_token_raises(settings):
    p1 = FakeProvider(["a" * 100], chunk_size=10, fail_mid_stream_after=2)
    r = two(settings, p1, FakeProvider(["never"]))
    got = []
    with pytest.raises(LLMUnavailable):
        async for c in r.stream(req()):
            got.append(c.text)
    assert got  # some text was emitted before the failure, and no fallback happened


async def test_stream_cancel_closes_upstream(settings):
    closed = asyncio.Event()

    class Slow:
        name = "fake"

        async def generate(self, r, m):
            raise NotImplementedError

        async def stream(self, r, m):
            try:
                from app.llm.types import LLMChunk

                yield LLMChunk(text="x")
                await asyncio.sleep(10)
            finally:
                closed.set()

    r = LLMRouter(settings, {"fake": Slow()})

    async def consume():
        async for _ in r.stream(req()):
            pass

    task = asyncio.create_task(consume())
    await asyncio.sleep(0.05)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert closed.is_set()
