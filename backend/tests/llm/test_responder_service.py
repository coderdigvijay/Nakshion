"""End-to-end chat pipeline and the module-level facade, with FakeProvider only."""

from __future__ import annotations

import json

import pytest

import app.llm.service as service
from app.llm import (
    LLMUnavailable,
    configure,
    generate_chat_reply,
    generate_compat_narrative,
    generate_daily_personal,
    generate_daily_sign,
    stream_chat_reply,
)
from app.llm.errors import LLMServerError
from app.llm.providers.fake import FakeProvider
from app.llm.responder import META_DELIM, ChatInput, ChatResponder
from app.llm.router import LLMRouter

from .conftest import GOOD, TODAY, chat_json

CITES = ["N.SUN.SIGN.CANCER", "V.MD.SATURN"]


class Dispatch:
    """One 'fake' provider key, separate scripted fakes per model ID."""

    name = "fake"

    def __init__(self, **by_model):
        self.by_model = by_model

    async def generate(self, r, model):
        return await self.by_model[model].generate(r, model)

    def stream(self, r, model):
        return self.by_model[model].stream(r, model)


def responder(settings, primary, secondary=None, retriever=None):
    prov = Dispatch(**{"fake-primary": primary, "fake-secondary": secondary or FakeProvider()})
    return ChatResponder(LLMRouter(settings, {"fake": prov}), retriever=retriever)


def inp(chart, q="What does my chart say about my personality?", **kw):
    return ChatInput(chart_data=chart, question=q, history=[], today=TODAY, **kw)


async def test_happy_path_grounded_answer(chart):
    p = FakeProvider([chat_json(GOOD, CITES)])
    from app.llm.config import LLMSettings

    s = LLMSettings(_env_file=None, LLM_MODEL_CHAT="fake-primary", LLM_FALLBACK_CHAT="fake-secondary")
    res = await responder(s, p).answer(inp(chart))
    assert res["answer"] == GOOD
    assert [c["factor_id"] for c in res["citations"]] == CITES
    assert res["citations"][0]["label"].startswith("Natal Sun in Cancer")
    md = res["metadata"]
    assert md["outcome"] == "ok" and md["prompt_version"] == "chat@v6" and md["validator_flags"] == []
    assert md["chart_engine_version"] == "1.0.0-synthetic" and "factor_ids_provided" in md
    assert res["tokens_used"] == 150


async def test_crisis_skips_llm(settings, chart):
    p = FakeProvider()
    res = await responder(settings, p).answer(inp(chart, q="I want to end my life"))
    assert p.calls == [] and res["metadata"]["safety"] == "crisis" and "14416" in res["answer"]


async def test_wrong_placement_is_repaired(settings, chart):
    bad = chat_json("Your Moon in Leo makes you dramatic. " + GOOD, CITES)
    p = FakeProvider([bad, chat_json(GOOD, CITES)])
    res = await responder(settings, p).answer(inp(chart))
    assert res["metadata"]["outcome"] == "repaired" and "Leo" not in res["answer"]
    assert "Moon in Leo not in chart" in p.calls[1][0].messages[-1]["content"]
    assert res["metadata"]["first_draft_flags"] == ["claim"]


async def test_repair_failure_strips_sentence(settings, chart):
    bad = chat_json(GOOD + " Your Moon in Leo is dramatic.", CITES)
    p = FakeProvider([bad, bad])
    res = await responder(settings, p).answer(inp(chart))
    assert res["metadata"]["outcome"] == "stripped" and "Leo" not in res["answer"]
    assert res["metadata"]["confidence"] == "low"


async def test_mostly_wrong_answer_falls_to_next_provider(settings, chart):
    bad = chat_json("Your Moon in Leo is dramatic. Your Venus in Aries is bold.", CITES)
    p1 = FakeProvider([bad, bad])
    p2 = FakeProvider([chat_json(GOOD, CITES)])
    res = await responder(settings, p1, p2).answer(inp(chart))
    assert res["metadata"]["outcome"] == "fallback" and res["answer"] == GOOD


async def test_safety_violation_twice_returns_canned(settings, chart):
    bad = chat_json("You should buy a blue sapphire for Saturn. " + GOOD, CITES)
    res = await responder(settings, FakeProvider([bad, bad])).answer(inp(chart))
    assert res["metadata"]["outcome"] == "canned" and "don't need to buy" in res["answer"]


async def test_unknown_citation_is_violation(settings, chart):
    p = FakeProvider([chat_json(GOOD, ["N.MADE.UP"]), chat_json(GOOD, CITES)])
    res = await responder(settings, p).answer(inp(chart))
    assert res["metadata"]["outcome"] == "repaired"


async def test_retrieval_failure_degrades(settings, chart):
    class Boom:
        async def retrieve(self, **kw):
            raise RuntimeError("db down")

    res = await responder(settings, FakeProvider([chat_json(GOOD, CITES)]), retriever=Boom()).answer(inp(chart))
    assert res["metadata"]["kb_chunk_ids"] == []


async def test_retrieved_notes_reach_prompt(settings, chart):
    from app.rag.store import RetrievedChunk

    class R:
        async def retrieve(self, **kw):
            self.kw = kw
            return [RetrievedChunk("planets#sun#0", "planets.md", "Planets > Sun", "both", "The Sun is vitality.")]

    r = R()
    p = FakeProvider([chat_json(GOOD, CITES)])
    res = await responder(settings, p, retriever=r).answer(inp(chart))
    assert res["metadata"]["kb_chunk_ids"] == ["planets#sun#0"]
    assert "The Sun is vitality." in p.calls[0][0].context_blocks[1]
    assert r.kw["kb_keys"]


async def test_all_fail_raises_unavailable(settings, chart):
    r = responder(settings, FakeProvider([LLMServerError("x")] * 2), FakeProvider([LLMServerError("y")] * 2))
    with pytest.raises(LLMUnavailable):
        await r.answer(inp(chart))


# ----------------------------------------------------------------------------- streaming


def stream_text(answer, cites):
    return f"{answer}\n{META_DELIM}\n" + json.dumps({"citations": cites, "topic": "self", "follow_ups": [],
                                                     "confidence": "high", "needs_birth_time": False})


async def test_stream_hides_meta_and_finishes(settings, chart):
    p = FakeProvider([stream_text(GOOD, CITES)], chunk_size=7)
    events = [e async for e in responder(settings, p).stream(inp(chart))]
    deltas = "".join(t for k, t in events if k == "delta")
    assert META_DELIM not in deltas and "{" not in deltas and deltas.strip() == GOOD
    kind, done = events[-1]
    assert kind == "done" and done["answer"] == GOOD and done["metadata"]["citations"] == CITES


async def test_stream_violation_sends_replace(settings, chart):
    p = FakeProvider([stream_text("Your Moon in Leo is dramatic. " + GOOD, CITES), chat_json(GOOD, CITES)])
    events = [e async for e in responder(settings, p).stream(inp(chart))]
    kinds = [k for k, _ in events]
    assert "replace" in kinds and events[-1][1]["answer"] == GOOD
    assert events[-1][1]["metadata"]["outcome"] == "repaired"


async def test_stream_mid_failure_raises_and_yields_no_done(settings, chart):
    p = FakeProvider([stream_text(GOOD, CITES)], chunk_size=5, fail_mid_stream_after=3)
    events = []
    with pytest.raises(LLMUnavailable):
        async for e in responder(settings, p).stream(inp(chart)):
            events.append(e)
    assert events and all(k == "delta" for k, _ in events)


async def test_stream_crisis_static(settings, chart):
    events = [e async for e in responder(settings, FakeProvider()).stream(inp(chart, q="I want to kill myself"))]
    assert events[-1][0] == "done" and events[-1][1]["metadata"]["safety"] == "crisis"


# ----------------------------------------------------------------------------- facade


@pytest.fixture
def facade(settings):
    p1, p2 = FakeProvider(), FakeProvider()
    daily = FakeProvider()
    configure(settings, providers={"fake": Dispatch(**{"fake-primary": p1, "fake-secondary": p2,
                                                       "fake-daily": daily})})
    yield p1, daily
    service.reset()


async def test_facade_chat(facade, chart):
    p1, _ = facade
    p1.push(chat_json(GOOD, CITES))
    res = await generate_chat_reply(chart_data=chart, question="Tell me about me", history=[], language="english",
                                    user_id_hash="h", astrology_system="both", today=TODAY)
    assert set(res) == {"answer", "citations", "sources", "tokens_used", "metadata"}


async def test_facade_stream(facade, chart):
    p1, _ = facade
    p1.push(stream_text(GOOD, CITES))
    evs = [e async for e in stream_chat_reply(chart_data=chart, question="Tell me about me", history=[],
                                              language="english", user_id_hash="h", astrology_system="both")]
    assert evs[-1][0] == "done"


SKY = {"planets": [{"name": "Moon", "sign": "Leo", "house": 5}, {"name": "Saturn", "sign": "Pisces", "retrograde": True}]}


async def test_facade_daily_sign_llm_and_template(facade):
    _, daily = facade
    daily.push(json.dumps({"general": "A warm and creative day for you, with the Moon in Leo lighting up play.",
                           "love": "Lead with warmth today.", "career": "Finish one task well.",
                           "wellness": "Rest early tonight.", "citations": ["S.MOON.SIGN.LEO"]}))
    out = await generate_daily_sign("Aries", "2026-10-01", SKY)
    assert out["generated_by"] == "llm" and out["citations"] == ["S.MOON.SIGN.LEO"]
    daily.push(LLMServerError("down"), LLMServerError("down"))
    out2 = await generate_daily_sign("Aries", "2026-10-01", SKY)
    assert out2["generated_by"] == "template" and set(out2) >= {"general", "love", "career", "wellness"}


async def test_facade_daily_sign_rejects_invented_position(facade):
    _, daily = facade
    bad = json.dumps({"general": "With Venus in Aries today, romance is bold and fast moving for you.",
                      "love": "Lead with warmth today.", "career": "Finish one task well.",
                      "wellness": "Rest early tonight.", "citations": []})
    daily.push(bad, bad)
    out = await generate_daily_sign("Aries", "2026-10-01", SKY)
    assert out["generated_by"] == "template"


async def test_facade_compat(facade):
    _, daily = facade
    report = {"overall_score": 72, "categories": {"emotional": {"score": 8}, "communication": {"score": 6}},
              "aspects": [{"planet1": "Venus", "planet2": "Mars", "type": "trine", "orb": 1.1}]}
    daily.push(json.dumps({
        "summary": "A warm pairing with easy affection and some work needed on how you talk things through.",
        "categories": [{"key": "emotional", "summary": "Feelings flow easily."},
                       {"key": "communication", "summary": "Slow down and listen."}],
        "aspect_interpretations": [{"aspect_key": "venus-trine-mars", "text": "Natural chemistry."}],
        "strengths": ["warmth", "humour", "loyalty"], "challenges": ["pace", "planning", "listening"]}))
    out = await generate_compat_narrative(report, "romantic")
    assert out["categories"]["emotional"]["summary"] and out["generated_by"] == "llm"
    assert len(out["strengths"]) == 3


async def test_facade_compat_unknown_key_repaired_or_unavailable(facade):
    _, daily = facade
    report = {"categories": {"emotional": {"score": 8}}, "aspects": []}
    bad = json.dumps({"summary": "A warm pairing with easy affection and a lot of shared humour overall.",
                      "categories": [{"key": "invented", "summary": "x"}], "aspect_interpretations": [],
                      "strengths": ["a", "b", "c"], "challenges": ["d", "e", "f"]})
    daily.push(bad, bad)
    with pytest.raises(LLMUnavailable):
        await generate_compat_narrative(report, "friendship")


# ----------------------------------------------------------------------------- personal daily (R3)

PFACTS = {"date": "2026-10-01", "system": "vedic",
          "areas": {"love": {"score": 4}, "career": {"score": 2}, "wellness": {"score": 3}, "money": {"score": 3}},
          "key_factors": [{"factor_id": "T.MOON.H6", "label": "Transiting Moon in house 6 from your natal Moon (Vedic)", "weight": 0.9},
                          {"factor_id": "V.MD.JUPITER", "label": "Current Jupiter Mahadasha", "weight": 1.0}],
          "dasha_context": {"maha": "Jupiter", "antar": "Venus", "note": "A growth-oriented phase."},
          "lucky": {"number": 7, "color": "blue"}}


def pjson(**over):
    d = {"headline": "A steady day for patient progress",
         "overview": "The Moon's passage through your sixth house asks for patience today, while your Jupiter period keeps a "
                     "wider sense of growth in view. Move at a measured pace and notice what supports you.",
         "areas": {k: {"text": f"A calm, practical note for {k} today: take it one step at a time."} for k in
                   ("love", "career", "wellness", "money")},
         "affirmation": "I move with patience and clarity.", "citations": ["T.MOON.H6", "V.MD.JUPITER"]}
    d.update(over)
    return json.dumps(d)


async def test_facade_daily_personal(facade):
    _, daily = facade
    daily.push(pjson())
    out = await generate_daily_personal(PFACTS, language="english")
    assert out["generated_by"] == "llm" and out["overview"] and set(out["areas"]) == {"love", "career", "wellness", "money"}
    assert all(set(v) == {"text"} for v in out["areas"].values())      # no scores from the LLM
    assert out["citations"] == ["T.MOON.H6", "V.MD.JUPITER"]
    req = daily.calls[0][0]
    assert "career 2" in req.context_blocks[1] and "[V.MD.JUPITER]" in req.context_blocks[0]
    assert "score" not in req.response_schema["properties"]


async def test_personal_unknown_citation_or_invented_position_repaired_then_fails(facade):
    _, daily = facade
    daily.push(pjson(citations=["N.MADE.UP"]), pjson(citations=["N.MADE.UP"]))
    with pytest.raises(LLMUnavailable):
        await generate_daily_personal(PFACTS)
    daily.push(pjson(overview="With Venus in Aries pushing hard today you should act boldly and quickly on every idea."),
              pjson())
    assert (await generate_daily_personal(PFACTS))["generated_by"] == "llm"
    assert len(daily.calls) == 4


async def test_personal_requires_factors_and_blocks_unsafe(facade):
    _, daily = facade
    with pytest.raises(LLMUnavailable):
        await generate_daily_personal({"areas": {}, "key_factors": []})
    bad = pjson(areas={k: {"text": "You should buy a blue sapphire to fix this today."} for k in
                       ("love", "career", "wellness", "money")})
    daily.push(bad, bad)
    with pytest.raises(LLMUnavailable):
        await generate_daily_personal(PFACTS)
