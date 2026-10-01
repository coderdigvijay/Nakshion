"""BUG-003 regression guards: chat must survive a primary-model 503 when only Gemini keys
exist; failures must be logged with a redacted cause and stored in usage; numbered keys load."""

from __future__ import annotations

import logging
from types import SimpleNamespace

import pytest
from google.genai import errors as gerrors

from app.llm.config import LLMSettings
from app.llm.errors import LLMRateLimited, LLMServerError, LLMUnavailable
from app.llm.providers.fake import FakeProvider
from app.llm.providers.gemini import GeminiProvider
from app.llm.router import LLMRouter
from app.llm.schemas import ChatAnswer
from app.llm.types import LLMRequest
from app.llm.usage import MemoryUsageSink

from .conftest import chat_json

REQ = LLMRequest(task="chat", system="s", context_blocks=(), messages=({"role": "user", "content": "q"},),
                 max_output_tokens=50, timeout_s=2, prompt_id="chat@v1")
FAKE_KEY = "AIza" + "X" * 35


class GeminiByModel:
    name = "gemini"

    def __init__(self, **by_model):
        self.by_model = by_model

    async def generate(self, r, model):
        return await self.by_model[model].generate(r, model)

    def stream(self, r, model):
        return self.by_model[model].stream(r, model)


def test_default_chat_chain_has_same_vendor_fallback():
    s = LLMSettings(_env_file=None)
    assert s.chain_for("chat") == ["gemini-3.8-flash", "claude-haiku-4-5", "gemini-3.5-flash-lite"]


async def test_primary_503_with_gemini_only_falls_to_flash_lite(caplog):
    s = LLMSettings(_env_file=None, retry_backoff_ms=(0, 0))
    overloaded = LLMServerError(f"gemini 503 UNAVAILABLE: high demand key={FAKE_KEY}", status=503)
    sink = MemoryUsageSink()
    prov = GeminiByModel(**{"gemini-3.8-flash": FakeProvider([overloaded]),
                            "gemini-3.5-flash-lite": FakeProvider([chat_json("ok", [])])})
    router = LLMRouter(s, {"gemini": prov}, usage_sink=sink)  # no anthropic provider configured
    with caplog.at_level(logging.WARNING, logger="nakshion.llm.router"):
        res = await router.generate(REQ, schema=ChatAnswer, deadline_s=30)
    assert res.model == "gemini-3.5-flash-lite" and res.parsed["answer"] == "ok"
    failed = [u for u in sink.records if u.outcome == "failed"]
    assert len(failed) == 1 and failed[0]  # 503: no same-model retry, straight to the next model.error.startswith("LLMServerError 503")
    assert FAKE_KEY not in failed[0].error and "[REDACTED]" in failed[0].error
    assert any(r.message == "llm_attempt_failed" for r in caplog.records)
    assert FAKE_KEY not in caplog.text


async def test_breaker_is_per_model():
    s = LLMSettings(_env_file=None)
    prov = GeminiByModel(**{"gemini-3.8-flash": FakeProvider(["never"]),
                            "gemini-3.5-flash-lite": FakeProvider([chat_json("lite", [])])})
    router = LLMRouter(s, {"gemini": prov})
    for _ in range(5):
        router.breaker("gemini:gemini-3.8-flash").record_failure()
    res = await router.generate(REQ, schema=ChatAnswer)
    assert res.model == "gemini-3.5-flash-lite"


async def test_no_provider_message_is_actionable():
    with pytest.raises(LLMUnavailable, match="no LLM provider configured.*GEMINI_API_KEY"):
        await LLMRouter(LLMSettings(_env_file=None), {}).generate(REQ)


def test_numbered_keys_from_kwargs_and_env_file(tmp_path, monkeypatch):
    for k in ("GEMINI_API_KEY", "GEMINI_API_KEY1", "GEMINI_API_KEY2", "GEMINI_API_KEY3"):
        monkeypatch.delenv(k, raising=False)
    s = LLMSettings(_env_file=None, GEMINI_API_KEY1="k1", GEMINI_API_KEY3="k3")
    assert s.gemini_keys() == ["k1", "k3"]
    env = tmp_path / ".env"
    env.write_text("GEMINI_API_KEY2=from-file\nUNRELATED=1\n", encoding="utf-8")
    s2 = LLMSettings(_env_file=env)
    assert s2.gemini_keys() == ["from-file"]
    assert "from-file" not in repr(s2)  # SecretStr masks values


class _Stub:
    def __init__(self, exc=None):
        self.calls = 0

        async def gen(**kw):
            self.calls += 1
            if exc:
                raise exc
            return SimpleNamespace(text="{}", prompt_feedback=None,
                                   candidates=[SimpleNamespace(finish_reason=SimpleNamespace(name="STOP"))],
                                   usage_metadata=None)

        self.aio = SimpleNamespace(models=SimpleNamespace(generate_content=gen))


async def test_gemini_rotates_keys_on_429():
    rl = gerrors.APIError(429, {"error": {"message": "quota", "status": "RESOURCE_EXHAUSTED"}})
    a, b = _Stub(rl), _Stub()
    p = GeminiProvider(clients=[a, b])
    assert (await p.generate(REQ, "gemini-3.8-flash")).text == "{}"
    assert a.calls == 1 and b.calls == 1
    with pytest.raises(LLMRateLimited):
        await GeminiProvider(clients=[_Stub(rl), _Stub(rl)]).generate(REQ, "m")


async def test_gemini_503_not_rotated():
    over = gerrors.APIError(503, {"error": {"message": "high demand", "status": "UNAVAILABLE"}})
    a, b = _Stub(over), _Stub()
    with pytest.raises(LLMServerError) as ei:
        await GeminiProvider(clients=[a, b]).generate(REQ, "m")
    assert ei.value.status == 503 and "high demand" in str(ei.value) and b.calls == 0


async def test_503_skips_same_model_retry_but_network_error_retries():
    s = LLMSettings(_env_file=None, retry_backoff_ms=(0, 0))
    p1 = FakeProvider([LLMServerError("gemini 503", status=503)])
    r = LLMRouter(s, {"gemini": GeminiByModel(**{"gemini-3.8-flash": p1, "gemini-3.5-flash-lite": FakeProvider(["x"]),
                                                  "claude-haiku-4-5": FakeProvider(["y"])})})
    await r.generate(REQ, deadline_s=30)
    assert len(p1.calls) == 1
    p2 = FakeProvider([LLMServerError("connection reset"), "recovered"])  # no status: transient network error
    r2 = LLMRouter(s, {"gemini": GeminiByModel(**{"gemini-3.8-flash": p2})})
    assert (await r2.generate(REQ, models=["gemini-3.8-flash"], deadline_s=30)).text == "recovered"
    assert len(p2.calls) == 2


async def test_gemini_drops_a_denied_key_and_uses_the_next():
    denied = gerrors.APIError(403, {"error": {"message": "denied", "status": "PERMISSION_DENIED"}})
    bad, good = _Stub(denied), _Stub()
    p = GeminiProvider(clients=[bad, good])
    assert (await p.generate(REQ, "m")).text == "{}"
    assert await p.generate(REQ, "m")                       # the denied key is gone for good
    assert bad.calls == 1 and good.calls == 2
    with pytest.raises(Exception):                          # the last remaining key's 403 is reported, not hidden
        await GeminiProvider(clients=[_Stub(denied)]).generate(REQ, "m")
