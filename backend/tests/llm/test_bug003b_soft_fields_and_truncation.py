"""BUG-003 (part 2): soft-field caps must not fail an answer; finish_reason=length retries bigger."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from app.llm.config import LLMSettings
from app.llm.errors import LLMOutputInvalid
from app.llm.providers.fake import FakeProvider
from app.llm.router import LLMRouter
from app.llm.schemas import ChatAnswer, ChatMeta, DailySign
from app.llm.types import LLMRequest

REQ = LLMRequest(task="chat", system="s", context_blocks=(), messages=({"role": "user", "content": "q"},),
                 max_output_tokens=700, timeout_s=2, prompt_id="chat@v3")
S = LLMSettings(_env_file=None, LLM_MODEL_CHAT="fake-primary", LLM_FALLBACK_CHAT="")


def test_overlong_followup_is_truncated_not_rejected():
    long = "What should I focus on in my career over the next several months given everything above? " * 2
    a = ChatAnswer.model_validate({"answer": "ok", "citations": [], "topic": "x" * 80, "confidence": "low",
                                   "follow_ups": [long, "", "short one", "b", "c"]})
    assert all(len(f) <= 90 for f in a.follow_ups) and len(a.follow_ups) == 3
    assert a.follow_ups[0].endswith("…") and a.follow_ups[1] == "short one"
    assert len(a.topic) <= 40


def test_citation_overflow_and_long_answer_are_normalised():
    a = ChatAnswer.model_validate({"answer": "Sentence one. " * 400, "citations": [f"N.X.{i}" for i in range(12)],
                                   "topic": "t", "confidence": "high", "follow_ups": []})
    assert len(a.citations) == 8 and len(a.answer) <= 2400 and a.answer.endswith(".")
    m = ChatMeta.model_validate({"citations": [], "topic": "t", "confidence": "low", "follow_ups": ["z" * 200]})
    assert len(m.follow_ups[0]) <= 90
    d = DailySign.model_validate({"general": "A" * 20 + ". " * 1 + "word " * 400, "love": "x" * 20 + " y" * 400,
                                  "career": "c" * 30, "wellness": "w" * 30, "citations": []})
    assert len(d.general) <= 900 and len(d.love) <= 500


@pytest.mark.parametrize("bad", [
    {"answer": "", "citations": [], "topic": "t", "confidence": "low", "follow_ups": []},
    {"citations": [], "topic": "t", "confidence": "low", "follow_ups": []},
    {"answer": "x", "citations": [], "topic": "t", "confidence": "maybe", "follow_ups": []},
    {"answer": "x", "citations": [], "topic": "t", "confidence": "low", "follow_ups": [], "extra": 1},
])
def test_truly_unusable_output_still_rejected(bad):
    with pytest.raises(Exception):
        ChatAnswer.model_validate(bad)


def ok_json(answer="fine", **kw):
    return json.dumps({"answer": answer, "citations": [], "topic": "t", "follow_ups": kw.get("f", []),
                       "confidence": "low"})


async def test_router_accepts_answer_with_overlong_followup():
    fp = FakeProvider([ok_json(f=["q" * 150])])
    res = await LLMRouter(S, {"fake": fp}).generate(REQ, schema=ChatAnswer)
    assert len(res.parsed["follow_ups"][0]) <= 90 and len(fp.calls) == 1


async def test_truncated_output_retries_with_larger_budget():
    budgets = []

    def script(req, model):
        budgets.append(req.max_output_tokens)
        return ok_json("complete") if req.max_output_tokens >= 1400 else '{"answer": "cut off mid'

    class Len(FakeProvider):
        async def generate(self, req, model):
            res = await super().generate(req, model)
            from dataclasses import replace
            return replace(res, finish_reason="length" if req.max_output_tokens < 1400 else "stop")

    fp = Len(default=script)
    res = await LLMRouter(S, {"fake": fp}).generate(REQ, schema=ChatAnswer)
    assert res.parsed["answer"] == "complete" and budgets == [700, 1400]


async def test_truncation_gives_up_after_one_growth():
    class AlwaysLen(FakeProvider):
        async def generate(self, req, model):
            from dataclasses import replace
            return replace(await super().generate(req, model), finish_reason="length")

    fp = AlwaysLen(default=ok_json())
    with pytest.raises(Exception):
        await LLMRouter(S, {"fake": fp}).generate(REQ, schema=ChatAnswer)
    assert [c[0].max_output_tokens for c in fp.calls] == [700, 1400]


def test_chat_default_budget_has_headroom():
    from app.llm.prompts import get_registry
    reg = get_registry()
    assert reg.active_version("chat") == "v6" and reg.reg["limits"]["chat"]["max_output_tokens"] >= 1200
    assert reg.verify() == []


# ----------------------------------------------------------------------------- DB isolation (BUG-003 #4)

LLM_TEST_DB = "astroai_test_llm"


def llm_test_database_url() -> str:
    """DB-backed llm/rag tests must use their OWN database, never astroai_test (backend-elite truncates it)."""
    url = os.environ.get("LLM_TEST_DATABASE_URL") or os.environ.get("TEST_DATABASE_URL", "")
    if not url:
        pytest.skip("LLM_TEST_DATABASE_URL not set")
    base, _, name = url.rpartition("/")
    name = name.split("?")[0]
    if name == "astroai_test":
        url = f"{base}/{LLM_TEST_DB}" + (("?" + url.split("?", 1)[1]) if "?" in url else "")
    return url


def test_llm_db_name_never_collides():
    os.environ["LLM_TEST_DATABASE_URL"] = "postgresql+asyncpg://u:p@localhost/astroai_test"
    try:
        assert llm_test_database_url().endswith("/astroai_test_llm")
    finally:
        del os.environ["LLM_TEST_DATABASE_URL"]
    assert not any("astroai_test\"" in line or "/astroai_test'" in line
                   for f in Path(__file__).parent.glob("test_*.py") if f != Path(__file__)
                   for line in f.read_text().splitlines())
