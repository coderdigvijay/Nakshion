"""Adapter request mapping and error mapping with stub SDK clients (no network)."""

from __future__ import annotations

from types import SimpleNamespace

import anthropic
import httpx2
import pytest
from google.genai import errors as gerrors

from app.llm.errors import LLMBadRequest, LLMBlocked, LLMRateLimited, LLMServerError, LLMTimeout
from app.llm.providers.claude import AnthropicProvider
from app.llm.providers.gemini import GeminiProvider
from app.llm.schemas import ChatAnswer, provider_schema
from app.llm.types import LLMRequest

REQ = LLMRequest(task="chat", system="SYSTEM", context_blocks=("FACTS", "NOTES"),
                 messages=({"role": "user", "content": "Q1"}, {"role": "assistant", "content": "A1"},
                           {"role": "user", "content": "Q2"}),
                 max_output_tokens=700, response_schema=provider_schema(ChatAnswer), temperature=0.6,
                 timeout_s=12, prompt_id="chat@v1", metadata={"user_id": "secret-user"})


# ----------------------------------------------------------------------------- Gemini


class GemStub:
    def __init__(self, resp=None, exc=None):
        self.kw = None
        self.resp, self.exc = resp, exc
        self.aio = SimpleNamespace(models=SimpleNamespace(generate_content=self._gen))

    async def _gen(self, **kw):
        self.kw = kw
        if self.exc:
            raise self.exc
        return self.resp


def gem_resp(text="{}", finish="STOP", block=None):
    return SimpleNamespace(
        text=text, prompt_feedback=SimpleNamespace(block_reason=block) if block else None,
        candidates=[SimpleNamespace(finish_reason=SimpleNamespace(name=finish))],
        usage_metadata=SimpleNamespace(prompt_token_count=1000, candidates_token_count=200,
                                       thoughts_token_count=50, cached_content_token_count=600),
    )


async def test_gemini_request_mapping_and_usage():
    stub = GemStub(gem_resp('{"a":1}'))
    p = GeminiProvider(client=stub, thinking_level="low")
    res = await p.generate(REQ, "gemini-3.8-flash")
    cfg = stub.kw["config"]
    assert stub.kw["model"] == "gemini-3.8-flash"
    assert cfg.system_instruction == "SYSTEM"
    assert cfg.response_mime_type == "application/json" and cfg.response_json_schema["type"] == "object"
    assert cfg.max_output_tokens == 700 and cfg.http_options.timeout == 12000
    contents = stub.kw["contents"]
    assert [c.role for c in contents] == ["user", "model", "user"]
    assert contents[0].parts[0].text.startswith("FACTS\n\nNOTES\n\nQ1")   # context prefix on first user turn
    assert "secret-user" not in repr(stub.kw)                             # metadata never sent
    assert (res.input_tokens, res.output_tokens, res.cached_input_tokens) == (1000, 250, 600)


@pytest.mark.parametrize("finish,exp", [("MAX_TOKENS", "length"), ("STOP", "stop")])
async def test_gemini_finish_reasons(finish, exp):
    res = await GeminiProvider(client=GemStub(gem_resp(finish=finish))).generate(REQ, "m")
    assert res.finish_reason == exp


async def test_gemini_safety_block():
    with pytest.raises(LLMBlocked):
        await GeminiProvider(client=GemStub(gem_resp(finish="SAFETY"))).generate(REQ, "m")
    with pytest.raises(LLMBlocked):
        await GeminiProvider(client=GemStub(gem_resp(block="SAFETY"))).generate(REQ, "m")


@pytest.mark.parametrize("code,exc", [(429, LLMRateLimited), (500, LLMServerError), (503, LLMServerError),
                                      (400, LLMBadRequest), (403, LLMBadRequest), (504, LLMTimeout)])
async def test_gemini_error_mapping(code, exc):
    err = gerrors.APIError(code, {"error": {"message": "x", "status": "S"}})
    with pytest.raises(exc):
        await GeminiProvider(client=GemStub(exc=err)).generate(REQ, "m")


def test_gemini_requires_key():
    with pytest.raises(LLMBadRequest):
        GeminiProvider(api_key=None)


# ----------------------------------------------------------------------------- Anthropic


class AnthStub:
    def __init__(self, msg=None, exc=None):
        self.kw = None
        self.msg, self.exc = msg, exc
        self.messages = SimpleNamespace(create=self._create)

    async def _create(self, **kw):
        self.kw = kw
        if self.exc:
            raise self.exc
        return self.msg


def anth_msg(text='{"a":1}', stop="end_turn", model="claude-haiku-4-5"):
    return SimpleNamespace(
        content=[SimpleNamespace(type="thinking", thinking=""), SimpleNamespace(type="text", text=text)],
        stop_reason=stop, model=model,
        usage=SimpleNamespace(input_tokens=100, output_tokens=40, cache_read_input_tokens=900,
                              cache_creation_input_tokens=0),
    )


async def test_anthropic_haiku_mapping():
    stub = AnthStub(anth_msg())
    res = await AnthropicProvider(client=stub).generate(REQ, "claude-haiku-4-5")
    kw = stub.kw
    assert kw["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert kw["system"][1]["text"] == "FACTS\n\nNOTES" and kw["system"][1]["cache_control"]
    assert kw["output_config"]["format"]["type"] == "json_schema"
    assert "effort" not in kw["output_config"]                       # effort errors on Haiku 4.5
    assert kw["extra_body"] == {"temperature": 0.6}                  # 1.x SDK: sampling via extra_body
    assert "temperature" not in kw and "tool_choice" not in kw
    assert kw["max_tokens"] == 700 and kw["timeout"] == 12
    assert [m["role"] for m in kw["messages"]] == ["user", "assistant", "user"]
    assert "secret-user" not in repr(kw)
    assert res.text == '{"a":1}'                                      # thinking block skipped
    assert (res.input_tokens, res.cached_input_tokens) == (1000, 900)


async def test_anthropic_sonnet_thinking_and_no_temperature():
    stub = AnthStub(anth_msg(model="claude-sonnet-5-5"))
    await AnthropicProvider(client=stub).generate(REQ, "claude-sonnet-5-5")
    assert stub.kw["output_config"]["effort"] == "medium"
    assert stub.kw["max_tokens"] == 700 + 2000
    assert "extra_body" not in stub.kw and "thinking" not in stub.kw


async def test_anthropic_refusal_and_length():
    with pytest.raises(LLMBlocked):
        await AnthropicProvider(client=AnthStub(anth_msg(stop="refusal"))).generate(REQ, "claude-haiku-4-5")
    res = await AnthropicProvider(client=AnthStub(anth_msg(stop="max_tokens"))).generate(REQ, "claude-haiku-4-5")
    assert res.finish_reason == "length"


def _resp(code):
    return httpx2.Response(code, request=httpx2.Request("POST", "https://api.anthropic.com/v1/messages"))


@pytest.mark.parametrize("exc,mapped", [
    (lambda: anthropic.RateLimitError("rl", response=_resp(429), body=None), LLMRateLimited),
    (lambda: anthropic.InternalServerError("5xx", response=_resp(500), body=None), LLMServerError),
    (lambda: anthropic.BadRequestError("bad", response=_resp(400), body=None), LLMBadRequest),
    (lambda: anthropic.APITimeoutError(request=httpx2.Request("POST", "https://x")), LLMTimeout),
    (lambda: anthropic.APIConnectionError(request=httpx2.Request("POST", "https://x")), LLMServerError),
])
async def test_anthropic_error_mapping(exc, mapped):
    with pytest.raises(mapped) as ei:
        await AnthropicProvider(client=AnthStub(exc=exc())).generate(REQ, "claude-haiku-4-5")
    assert ei.value.__cause__ is None  # raw SDK exception does not leak as the cause


def test_provider_schema_is_flat_and_closed():
    s = provider_schema(ChatAnswer)
    assert "$defs" not in s and s["additionalProperties"] is False
    assert set(s["required"]) == set(s["properties"])
    assert "maxLength" not in str(s)
