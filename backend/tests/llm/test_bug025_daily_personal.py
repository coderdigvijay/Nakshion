"""BUG-025: the personal daily reading fell back to the generic template on production.

Causes found live (real engine facts, Gemini):
  1. "Jupiter in Cancer" was rejected as an invented placement because the fact says "Jupiter in Karka"; the repair often
     repeated it, so the reading was thrown away (2 of 7 readings became the template).
  2. The dasha context ("Mercury Antardasha") was not part of what the claim checker accepted.
  3. Unknown/missing citation ids failed the whole reading (citations are metadata).
  4. Time: retrieval (RAG_TIMEOUT_S=10 on the slow CPU) + the model + a repair ran under a 20 s outer timeout in the
     adapter, so a slow embed left the model no time.
These tests pin the fixes and the new, language-aware template."""

from __future__ import annotations

import asyncio
import json
import time

import pytest

import app.llm.service as service
from app.llm import LLMUnavailable, configure, generate_daily_personal, template_daily_personal
from app.llm.config import LLMSettings
from app.llm.providers.fake import FakeProvider

from .test_responder_service import PFACTS, Dispatch, pjson

AREAS = ("love", "career", "wellness", "money")


@pytest.fixture
def facade():
    """daily provider + helper to (re)configure with a retriever; always reset."""
    made = {}

    def make(*, delay=0.0, retriever=None, responses=None):
        daily = FakeProvider(responses or [], delay_s=delay)
        configure(LLMSettings(_env_file=None, LLM_MODEL_DAILY="fake-daily", LLM_FALLBACK_DAILY="", retry_backoff_ms=(0, 0)),
                  providers={"fake": Dispatch(**{"fake-daily": daily})}, retriever=retriever)
        made["daily"] = daily
        return daily

    yield make
    service.reset()


KARKA = {"date": "2026-10-02", "system": "vedic",
         "areas": {k: {"score": 3} for k in AREAS},
         "key_factors": [{"factor_id": "G.JUPITER.H1", "label": "Transiting Jupiter in Karka, house 1 from your natal Moon (gochara)", "weight": 0.9},
                         {"factor_id": "V.MD.VENUS", "label": "Venus Mahadasha (2009-09-23 to 2029-09-23)", "weight": 1.0}],
         "dasha_context": {"maha": "Venus", "antar": "Mercury", "note": "Venus Mahadasha until 2029-09-23, Mercury Antardasha until 2028-07-24"}}


def reading(**over):
    d = {"headline": "Venus period: steady focus", "overview": "Under your Venus Mahadasha and Mercury Antardasha, today favours learning and "
         "connection, while Jupiter in Cancer in the first house from your Moon widens your outlook and keeps a hopeful tone.",
         "areas": {k: {"text": f"A calm, practical note for {k} today: take one step at a time."} for k in AREAS},
         "affirmation": "I move with patience.", "citations": ["G.JUPITER.H1", "V.MD.VENUS"]}
    d.update(over)
    return json.dumps(d)


async def test_sign_names_match_by_alias_and_dasha_context_is_accepted(facade):
    daily = facade(responses=[reading()])
    out = await generate_daily_personal(KARKA, language="english", system="vedic")
    assert out["generated_by"] == "llm" and len(daily.calls) == 1             # "Cancer" == "Karka"; "Mercury Antardasha" from the context


async def test_missing_or_unknown_citations_never_fail_a_reading(facade):
    daily = facade(responses=[reading(citations=["N.MADE.UP"]), reading(citations=[])])
    a = await generate_daily_personal(KARKA, language="english", system="vedic")
    b = await generate_daily_personal(KARKA, language="english", system="vedic")
    assert a["citations"] == b["citations"] == ["G.JUPITER.H1", "V.MD.VENUS"] and len(daily.calls) == 2


async def test_unsupported_sentence_is_dropped_instead_of_losing_the_reading(facade):
    bad = reading(overview="With Mars in Leo pushing hard you should act fast on every idea today. Your Venus Mahadasha keeps a steady, "
                           "learning-oriented tone through the day, and small, patient steps tend to work best for you.")
    daily = facade(responses=[bad, bad])
    out = await generate_daily_personal(KARKA, language="english", system="vedic")
    assert out["generated_by"] == "llm" and "Mars in Leo" not in out["overview"] and "Venus Mahadasha" in out["overview"]
    assert len(daily.calls) == 2                                           # first draft + one repair, then salvage


async def test_a_field_with_nothing_left_gets_the_template_line(facade):
    bad = reading(areas={**{k: {"text": f"A calm note for {k}: one step at a time today."} for k in AREAS},
                         "love": {"text": "Venus in Aries makes you bold in love today and you will meet someone."}})
    facade(responses=[bad, bad])
    out = await generate_daily_personal(KARKA, language="english", system="vedic")
    assert "Venus in Aries" not in out["areas"]["love"]["text"] and len(out["areas"]["love"]["text"]) > 20


async def test_safety_hit_still_fails_the_reading(facade):
    bad = reading(areas={k: {"text": "You should buy a blue sapphire to fix this today, it is necessary."} for k in AREAS})
    facade(responses=[bad, bad])
    with pytest.raises(LLMUnavailable):
        await generate_daily_personal(KARKA, language="english", system="vedic")


class SlowRetriever:
    def __init__(self, delay):
        self.delay, self.calls = delay, 0

    async def retrieve(self, **kw):
        self.calls += 1
        await asyncio.sleep(self.delay)
        return []


async def test_slow_retrieval_is_capped_and_does_not_eat_the_model_budget(facade, monkeypatch):
    monkeypatch.setattr(service, "DAILY_RAG_CAP_S", 0.2)
    r = SlowRetriever(5.0)                                                  # the free CPU embedding for 5+ s
    daily = facade(retriever=r, responses=[reading()])
    t0 = time.monotonic()
    out = await generate_daily_personal(KARKA, language="english", system="vedic", budget_s=8)
    assert out["generated_by"] == "llm" and time.monotonic() - t0 < 2.0 and r.calls == 1 and out["metadata"]["kb_chunk_ids"] == []
    assert "REFERENCE NOTES" not in "".join(daily.calls[0][0].context_blocks)


async def test_whole_call_respects_the_budget(facade):
    facade(delay=5.0, responses=[reading()])
    t0 = time.monotonic()
    with pytest.raises(LLMUnavailable):
        await generate_daily_personal(KARKA, language="english", system="vedic", budget_s=2.5)
    assert time.monotonic() - t0 < 3.0                                      # not 20-40 s


async def test_repair_is_skipped_when_no_time_is_left(facade):
    daily = facade(delay=0.0, responses=[reading(overview="With Mars in Leo you should act now on every idea today, boldly and fast.")])
    # budget so small that after the first call there is no room for a repair: salvage instead of a second call
    out = await generate_daily_personal(KARKA, language="english", system="vedic", budget_s=3.0)
    assert out["generated_by"] == "llm" and len(daily.calls) == 1 and "Mars in Leo" not in out["overview"]


def test_prompt_v2_is_short_and_v1_stays_locked():
    from app.llm.prompts import get_registry

    reg = get_registry()
    assert reg.verify() == [] and reg.active_version("daily_personal") == "v2"
    v2 = reg.render("daily_personal", system_label="sidereal zodiac", language_instruction="English.").text
    v1 = reg.render("daily_personal", version="v1", system_label="sidereal zodiac", language_instruction="English.").text
    assert "60 to 100 words" in v2 and "90 to 150 words" in v1
    lim = reg.reg["limits"]["daily_personal"]
    assert lim["timeout_s"] <= 12 and 1000 <= lim["max_output_tokens"] <= 1400


# ----------------------------------------------------------------------------- the template (served when the LLM is slow)

@pytest.mark.parametrize("language", ["english", "hindi", "hinglish"])
def test_template_is_specific_and_in_the_users_language(language):
    facts = {**PFACTS, "areas": {"love": {"score": 4}, "career": {"score": 2}, "wellness": {"score": 3}, "money": {"score": 3}},
             "dasha_context": {"maha": "Venus", "antar": "Mercury", "note": ""}, "moon_transit": {"house": 11, "from": "natal Moon", "sign": "Vrishabha"}}
    t = template_daily_personal(facts, language)
    assert set(t["areas"]) == set(AREAS) and all(t["areas"][k]["text"] for k in AREAS)
    assert len(t["headline"]) <= 90 and t["overview"] and t["affirmation"]
    names = {"english": ("Venus", "Mercury"), "hindi": ("शुक्र", "बुध"), "hinglish": ("Shukra", "Budh")}[language]
    assert all(n in t["headline"] for n in names) and all(n in t["overview"] for n in names)
    if language == "hindi":
        assert "Venus" not in t["headline"] + t["overview"]
        # no gendered verb endings addressed to the user
        from app.llm.textclean import assumes_female

        assert not assumes_female(" ".join([t["overview"], t["affirmation"], *[a["text"] for a in t["areas"].values()]]))
    # the highest and lowest areas differ in text and are named in the headline
    assert t["areas"]["love"]["text"] != t["areas"]["career"]["text"]


def test_template_is_not_the_old_generic_headline_and_follows_the_scores():
    flat = {**PFACTS, "areas": {k: {"score": 3} for k in AREAS}}
    assert "steady focus today" not in template_daily_personal(flat, "english")["headline"]
    t = template_daily_personal({**flat, "areas": {**flat["areas"], "money": {"score": 5}}}, "english")
    assert "money flows" in t["headline"].lower() and "5 of 5" in t["overview"]
    t = template_daily_personal({**flat, "areas": {**flat["areas"], "career": {"score": 1}}}, "english")
    assert "career" in t["headline"] and "gently" in t["headline"] and "1 of 5" in t["overview"]


def test_template_without_dasha_or_scores_still_reads_well():
    t = template_daily_personal({"key_factors": []}, "english")
    assert t["headline"] and t["overview"] and all(t["areas"][k]["text"] for k in AREAS)
