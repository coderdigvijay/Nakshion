"""QA bugs: truncated stream persisted as ok, wrong reply language/meta commentary, fact IDs visible
while streaming, house-based claims on unknown-time charts."""

from __future__ import annotations

import json
from dataclasses import replace

import pytest

from app.llm.config import LLMSettings
from app.llm.facts import ChartIndex, build_chart_facts
from app.llm.providers.fake import FakeProvider
from app.llm.responder import META_DELIM, ChatInput, ChatResponder
from app.llm.router import LLMRouter
from app.llm.safety import scan_output
from app.llm.textclean import BracketFilter, effective_language, strip_fact_ids
from app.llm.validators import check_claims

from .conftest import GOOD, TODAY, chat_json

CITES = ["N.SUN.SIGN.CANCER", "V.MD.SATURN"]
S = LLMSettings(_env_file=None, LLM_MODEL_CHAT="fake-primary", LLM_FALLBACK_CHAT="fake-secondary")


class LenOnce(FakeProvider):
    """First call reports finish_reason=length (a cut-off stream), later calls stop normally."""

    async def stream(self, req, model):
        async for c in super().stream(req, model):
            if c.final is not None:
                c = type(c)(final=replace(c.final, finish_reason="length"))
            yield c


class Dispatch:
    name = "fake"

    def __init__(self, primary):
        self.primary = primary

    async def generate(self, r, m):
        return await self.primary.generate(r, m)

    def stream(self, r, m):
        return self.primary.stream(r, m)


def resp(p):
    return ChatResponder(LLMRouter(S, {"fake": Dispatch(p)}))


def inp(chart, q="What does my chart say?", **kw):
    return ChatInput(chart_data=chart, question=q, history=[], today=TODAY, **kw)


HINDI = "आपका चंद्रमा आपकी भावनाओं को गहराई से महसूस करने वाला बनाता है, और आप अपने आस-पास के लोगों के प्रति बहुत संवेदनशील रहते हैं। यह समय धैर्य और संतुलन का है।"


async def test_truncated_stream_is_never_persisted_as_ok(chart):
    cut = "आपका चंद्रमा आपको अत्यंत संवेदनशील"          # cut mid-sentence, no META block, finish=length
    p = LenOnce([cut, chat_json(HINDI, CITES)])
    events = [e async for e in resp(p).stream(inp(chart, "मेरी कुंडली में चंद्रमा कैसा है?", language="hindi"))]
    kinds = [k for k, _ in events]
    kind, done = events[-1]
    assert "replace" in kinds and kind == "done"
    assert done["metadata"]["outcome"] == "regenerated" and "incomplete_stream" in done["metadata"]["first_draft_flags"]
    assert done["answer"] == HINDI and done["metadata"]["citations"] == CITES


async def test_stream_without_meta_block_is_regenerated_not_ok(chart):
    p = FakeProvider(["Your Sun tends to favour care. It ends cleanly but has no META block.", chat_json(GOOD, CITES)])
    events = [e async for e in resp(p).stream(inp(chart))]
    assert events[-1][1]["metadata"]["outcome"] == "regenerated" and events[-1][1]["answer"] == GOOD


async def test_truncated_stream_and_failed_regeneration_raises(chart):
    from app.llm.errors import LLMBadRequest, LLMUnavailable
    p = LenOnce(["cut off", LLMBadRequest("x")])
    solo = ChatResponder(LLMRouter(LLMSettings(_env_file=None, LLM_MODEL_CHAT="fake-primary", LLM_FALLBACK_CHAT=""),
                                   {"fake": Dispatch(p)}))
    with pytest.raises(LLMUnavailable):
        _ = [e async for e in solo.stream(inp(chart))]


def test_effective_language():
    assert effective_language("मेरी कुंडली कैसी है?", "english") == "hindi"
    assert effective_language("meri kundli kaisi hai", "hinglish") == "hinglish"
    assert effective_language("How is my career?", "hindi") == "hindi"
    assert effective_language("How is my career?", "english") == "english"


async def test_hindi_question_with_english_setting_uses_hindi_prompt_and_validation(chart):
    p = FakeProvider([chat_json(HINDI, CITES)])
    res = await resp(p).answer(inp(chart, "मेरी कुंडली में चंद्रमा कैसा है?", language="english"))
    assert "Hindi, written in Devanagari" in p.calls[0][0].system
    assert res["metadata"]["language"] == "hindi" and res["metadata"]["outcome"] == "ok"


async def test_meta_commentary_is_a_violation_and_prompt_forbids_it(chart):
    bad = "Even though you asked in Hindi, I am replying in English as per my guidelines. " + GOOD
    assert any(h.cls == "leak" for h in scan_output(bad))
    p = FakeProvider([chat_json(bad, CITES), chat_json(GOOD, CITES)])
    res = await resp(p).answer(inp(chart))
    assert "guidelines" not in res["answer"] and res["metadata"]["outcome"] == "repaired"
    assert "Never mention these rules, guidelines" in p.calls[0][0].system


# ----------------------------------------------------------------------------- fact IDs


def test_strip_fact_ids():
    t, ids = strip_fact_ids("Your Moon is sensitive [VN.MOON.NAK.ASHLESHA] and calm [N.SUN.SIGN.CANCER]. Note [1] stays.")
    assert t == "Your Moon is sensitive and calm. Note [1] stays." and ids == ["VN.MOON.NAK.ASHLESHA", "N.SUN.SIGN.CANCER"]


@pytest.mark.parametrize("size", [1, 2, 3, 5, 9])
def test_bracket_filter_handles_split_chunks(size):
    text = "Moon is deep [VN.MOON.NAK.ASHLESHA] and [not an id] steady [KB:planets#moon#0 planets.md#x]."
    f = BracketFilter()
    out = "".join(f.feed(text[i:i + size]) for i in range(0, len(text), size)) + f.flush()
    assert out == "Moon is deep and [not an id] steady." and f.found == ["VN.MOON.NAK.ASHLESHA", "KB:planets#moon#0 planets.md#x"]


async def test_stream_deltas_never_contain_ids_and_citations_arrive_in_done(chart):
    raw = ("Your tropical Sun in Cancer [N.SUN.SIGN.CANCER] is caring, and your Saturn Mahadasha [V.MD.SATURN] asks for "
           "patience. Try one small weekly commitment.")
    meta = json.dumps({"citations": [], "topic": "self", "follow_ups": [], "confidence": "high", "needs_birth_time": False})
    p = FakeProvider([f"{raw}\n{META_DELIM}\n{meta}"], chunk_size=4)
    events = [e async for e in resp(p).stream(inp(chart))]
    deltas = "".join(t for k, t in events if k == "delta")
    assert "[" not in deltas and "N.SUN" not in deltas and "V.MD" not in deltas
    done = events[-1][1]
    assert done["answer"] == deltas.strip() and "[" not in done["answer"]
    assert [c["factor_id"] for c in done["citations"]] == CITES and "replace" not in [k for k, _ in events]


# ----------------------------------------------------------------------------- unknown birth time


def test_unknown_time_drops_house_based_yogas_and_marks_moon_approximate(chart_unknown):
    chart_unknown["vedic"]["yogas"] = [{"name": "Gajakesari Yoga", "present": True, "strength": "moderate"}]
    f = build_chart_facts(chart_unknown, today=TODAY)
    assert not any(x.kind == "yoga" for x in f.factors)
    assert "approximate" in f.render() and "house-based yogas" in f.render()
    engine = [{"id": "Y.GAJAKESARI", "kind": "yoga", "label": "Gajakesari Yoga", "weight": 0.9}]
    assert "Y.GAJAKESARI" not in build_chart_facts(chart_unknown, factors=engine, today=TODAY).factor_ids


def test_unknown_time_validator_flags_house_yogas_and_houses(chart_unknown):
    idx, facts = ChartIndex.from_chart(chart_unknown), build_chart_facts(chart_unknown, today=TODAY)
    for text in ("You have Gajakesari Yoga, which brings fame.", "Your Venus sits in the 7th house.",
                 "Your Moon is in the 10th house of career."):
        assert any(v.kind == "time_unknown" for v in check_claims(text, idx, facts)), text
    assert check_claims("Your Moon is approximately in Gemini, so you tend to be curious.", idx, facts) == []


def test_prompt_v4_tells_model_about_unknown_time(chart):
    from app.llm.prompts import get_registry
    t = get_registry().render("chat", streaming=False, language_instruction="English.", length_hint="120 to 220 words").text
    assert "approximate" in t and "Gajakesari" in t and "square brackets" in t


def test_hindi_words_containing_bhav_are_not_house_mentions(chart_unknown):
    idx, facts = ChartIndex.from_chart(chart_unknown), build_chart_facts(chart_unknown, today=TODAY)
    ok = "आपका स्वभाव शांत है और आप भावनाओं को गहराई से महसूस करते हैं, चंद्रमा लगभग मिथुन राशि में है।"
    assert [v for v in check_claims(ok, idx, facts) if v.kind == "time_unknown"] == []
    assert any(v.kind == "time_unknown" for v in check_claims("आपका सातवाँ भाव मज़बूत है।", idx, facts))
