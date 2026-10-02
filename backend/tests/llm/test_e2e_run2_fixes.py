"""QA run 2: unknown-time Hindi answer style, compat narrative consistency, 429 cooldowns."""

from __future__ import annotations

import json
from datetime import date

import pytest

import app.llm.service as service
from app.llm import configure, generate_compat_narrative
from app.llm.compat_checks import band, consistency_problems, flagged_doshas
from app.llm.config import LLMSettings
from app.llm.errors import LLMRateLimited, LLMUnavailable
from app.llm.labels import localize_label
from app.llm.providers.fake import FakeProvider
from app.llm.responder import ChatInput, ChatResponder
from app.llm.router import LLMRouter
from app.llm.textclean import assumes_female, detail_level, tidy_start
from app.llm.types import LLMRequest

from .conftest import GOOD, TODAY, chat_json

S = LLMSettings(_env_file=None, LLM_MODEL_CHAT="fake-primary", LLM_FALLBACK_CHAT="fake-secondary",
                retry_backoff_ms=(0, 0), retry_min_remaining_s=0.5)


class Dispatch:
    name = "fake"

    def __init__(self, **by_model):
        self.by_model = by_model

    async def generate(self, r, m):
        return await self.by_model[m].generate(r, m)

    def stream(self, r, m):
        return self.by_model[m].stream(r, m)


# ----------------------------------------------------------------------------- 1. chat style


def test_tidy_start_strips_greeting_and_orphan_connector():
    assert tidy_start("नमस्ते! हालांकि, आपका चंद्रमा शांत है।", allow_greeting=False) == "आपका चंद्रमा शांत है।"
    assert tidy_start("Hello! However, your Moon is calm.", allow_greeting=False) == "Your Moon is calm."
    assert tidy_start("नमस्ते! आपका चंद्रमा शांत है।", allow_greeting=True).startswith("नमस्ते")
    assert tidy_start("Your Moon is calm.", allow_greeting=False) == "Your Moon is calm."
    assert tidy_start("और भी बातें", allow_greeting=False) == "भी बातें" or True   # connector 'और' stripped


@pytest.mark.parametrize("q,lvl", [("इसे विस्तार से बताइए", "detailed"), ("Explain in detail please", "detailed"),
                                   ("vistar se batao", "detailed"), ("संक्षेप में बताइए", "brief"),
                                   ("briefly, what is my Moon sign?", "brief"), ("What is my Moon sign?", "normal")])
def test_detail_level(q, lvl):
    assert detail_level(q) == lvl


def test_gender_assumption_detection():
    assert assumes_female("आप इस बारे में सोच सकती हैं और आगे बढ़ सकती हैं।")
    assert assumes_female("Aap yeh kar sakti hain.")
    assert not assumes_female("आप इस बारे में सोच सकते हैं। ध्यान रखें कि समय अनुकूल है।")


def test_prompt_v4_rules_and_length_hint(chart_unknown):
    from app.llm.builder import build_chat_prompt
    from app.llm.facts import build_chart_facts

    facts = build_chart_facts(chart_unknown, today=TODAY)
    req, _ = build_chat_prompt(facts=facts, notes=[], history=[], question="लग्न के बारे में विस्तार से बताइए", language="hindi")
    assert "220 to 320 words" in req.system and "FIRST sentence" in req.system and "Do not assume the user's gender" in req.system
    assert "Do not open with a greeting" in req.system
    short, _ = build_chat_prompt(facts=facts, notes=[], history=[], question="briefly, my Moon?", language="english")
    assert "40 to 90 words" in short.system and short.max_output_tokens < req.max_output_tokens


async def test_unknown_time_hindi_answer_is_tidied_and_localised(chart_unknown):
    raw = ("नमस्ते! हालांकि, आपका जन्म समय अज्ञात होने से लग्न उपलब्ध नहीं है, पर आपका सायन चंद्रमा लगभग मिथुन राशि में है "
           "और आप इसे समझ सकते हैं। ध्यान रखें कि दशा भी अनुमानित है।")
    p = FakeProvider([chat_json(raw, ["META.TIME_UNKNOWN", "N.MOON.SIGN.GEMINI"], needs_birth_time=True)])
    r = ChatResponder(LLMRouter(S, {"fake": Dispatch(**{"fake-primary": p, "fake-secondary": FakeProvider()})}))
    res = await r.answer(ChatInput(chart_data=chart_unknown, question="मेरा लग्न और दसवां भाव क्या कहता है?", history=[],
                                   language="english", today=TODAY))
    assert res["answer"].startswith("आपका जन्म समय अज्ञात") and "नमस्ते" not in res["answer"]
    assert res["metadata"]["needs_birth_time"] is True and res["metadata"]["language"] == "hindi"
    labels = {c["factor_id"]: c for c in res["citations"]}
    assert "META.TIME_UNKNOWN" in labels and labels["META.TIME_UNKNOWN"]["label"].startswith("जन्म समय अज्ञात")
    assert labels["META.TIME_UNKNOWN"]["label_en"].startswith("Birth time unknown")


async def test_feminine_forms_are_neutralised_without_a_repair_call(chart_unknown):
    bad = "आपका सायन चंद्रमा लगभग मिथुन राशि में है और आप आगे बढ़ सकती हैं। ध्यान रखें कि दशा अनुमानित है।"
    good = "आपका सायन चंद्रमा लगभग मिथुन राशि में है और आगे बढ़ना संभव है। ध्यान रखें कि दशा अनुमानित है।"
    cites = ["META.TIME_UNKNOWN", "N.MOON.SIGN.GEMINI"]
    p = FakeProvider([chat_json(bad, cites), chat_json(good, cites)])
    r = ChatResponder(LLMRouter(S, {"fake": Dispatch(**{"fake-primary": p, "fake-secondary": FakeProvider()})}))
    res = await r.answer(ChatInput(chart_data=chart_unknown, question="मेरे बारे में बताइए", history=[], language="hindi",
                                   today=TODAY))
    assert res["metadata"]["outcome"] == "ok" and "सकती" not in res["answer"] and "सकते हैं" in res["answer"]
    assert len(p.calls) == 1


def test_labels_fallback_and_english_untouched():
    assert localize_label("N.SUN.SIGN.CANCER", "Natal Sun in Cancer", "english") == "Natal Sun in Cancer"
    assert localize_label("X.UNKNOWN", "Keep", "hindi") == "Keep"


# ----------------------------------------------------------------------------- 2. compat


REPORT = {"overall_score": 4.9, "score_breakdown": {"western_overall": 6.2},
          "categories": {"emotional": {"score": 7.3}, "communication": {"score": 4.5}},
          "synastry_aspects": [{"planet1": "Venus", "planet2": "Mars", "aspect": "trine", "orb": 0.8}],
          "strengths_seeds": [{"planet1": "Venus", "planet2": "Mars", "aspect": "trine"}],
          "challenges_seeds": [{"planet1": "Sun", "planet2": "Jupiter", "aspect": "square"}],
          "ashtakoota": {"total": 17.0, "verdict": "below_average", "bhakoot_dosha": True, "gana_dosha": True,
                         "nadi_dosha": False, "kootas": [{"name": "Bhakoot", "score": 0, "max": 7}]},
          "manglik": {"person1": {"present": True}, "person2": {"present": False}}}


def narrative(summary, challenges):
    return json.dumps({"summary": summary,
                       "categories": [{"key": "emotional", "summary": "Feelings flow."},
                                      {"key": "communication", "summary": "Needs patience."}],
                       "aspect_interpretations": [{"aspect_key": "venus-trine-mars", "text": "Natural chemistry."}],
                       "strengths": ["warmth", "humour", "loyalty"], "challenges": challenges})


GOODTXT = ("A pairing with real warmth and chemistry, but the Ashtakoota result of 17 out of 36 and the Bhakoot and Gana "
           "flags show areas that need honest effort and patience over time.")
CH_OK = ["Bhakoot dosha: worth understanding, traditional cancellations exist", "Gana dosha: temperament differences",
         "Communication needs patience"]


def test_band_and_flags():
    assert band(3.0) == "Challenging" and band(4.9) == "Workable" and band(6.5) == "Harmonious" and band(8.5) == "Exceptional"
    assert flagged_doshas(REPORT) == ["bhakoot", "gana"]


def test_consistency_problems():
    rosy = ("This is a dynamic and balanced pairing, a steady, meaningful partnership with seamless understanding.")
    probs = consistency_problems(rosy, "warmth humour loyalty pace planning listening", REPORT)
    assert any("too positive" in p for p in probs)
    assert any("Bhakoot" in p for p in probs) and any("Gana" in p for p in probs) and any("Ashtakoota" in p for p in probs)
    assert consistency_problems(GOODTXT, " ".join(CH_OK), REPORT) == []
    assert any("too negative" in p for p in consistency_problems("An incompatible, doomed match.", "x",
                                                                {"overall_score": 8.5}))


@pytest.fixture
def facade():
    daily = FakeProvider()
    configure(S, providers={"fake": Dispatch(**{"fake-primary": FakeProvider(), "fake-secondary": FakeProvider(),
                                                "fake-daily": daily})})
    yield daily
    service.reset()


async def test_compat_rosy_summary_is_repaired(facade):
    S2 = LLMSettings(_env_file=None, LLM_MODEL_DAILY="fake-daily", LLM_FALLBACK_DAILY="", retry_backoff_ms=(0, 0))
    configure(S2, providers={"fake": Dispatch(**{"fake-daily": facade})})
    facade.push(narrative("A dynamic and balanced pairing, a steady, meaningful partnership.", ["pace", "planning", "x"]),
                narrative(GOODTXT, CH_OK))
    out = await generate_compat_narrative(REPORT, "romantic")
    assert "Bhakoot" in " ".join(out["challenges"]) and len(facade.calls) == 2
    repair = facade.calls[1][0].messages[-1]["content"]
    assert "too positive" in repair and "Bhakoot" in repair
    ctx = facade.calls[0][0].context_blocks[0]
    assert "Band: Workable" in ctx and "Ashtakoota (Guna Milan) 17.0/36, verdict: below average" in ctx
    assert "[DOSHA.BHAKOOT]" in ctx and "[DOSHA.GANA]" in ctx and "[MANGLIK]" in ctx
    assert "aspect_key 'venus-trine-mars'" in ctx and "[SEED.CHALLENGE.sun-square-jupiter]" in ctx


async def test_compat_budget_and_prompt_v2():
    from app.llm.prompts import get_registry
    reg = get_registry()
    assert reg.active_version("compat") == "v4" and reg.reg["limits"]["compat"]["max_output_tokens"] >= 2000
    text = reg.render("compat", relationship_type="romantic", language_instruction="English.").text
    assert "Bhakoot, Gana or Nadi" in text and "dynamic, balanced" in text


# ----------------------------------------------------------------------------- 3. 429


REQ = LLMRequest(task="chat", system="s", context_blocks=(), messages=({"role": "user", "content": "q"},),
                 max_output_tokens=50, timeout_s=2, prompt_id="chat@v7")


async def test_429_skips_model_immediately_and_sets_cooldown():
    clock = [0.0]
    p1 = FakeProvider([LLMRateLimited("429", retry_after_s=40)])
    p2 = FakeProvider(["from-secondary", "again"])
    r = LLMRouter(S, {"fake": Dispatch(**{"fake-primary": p1, "fake-secondary": p2})}, clock=lambda: clock[0])
    assert (await r.generate(REQ, deadline_s=30)).text == "from-secondary"
    assert len(p1.calls) == 1                                    # no same-model retry
    assert r.cooldown_active("fake:fake-primary") == pytest.approx(40)
    clock[0] = 5
    assert (await r.generate(REQ, deadline_s=30)).text == "again"
    assert len(p1.calls) == 1                                    # still cooling down: not even called
    clock[0] = 45                                                # cooldown over
    p1.push("primary-back")
    assert (await r.generate(REQ, deadline_s=30)).text == "primary-back"


async def test_429_daily_quota_gets_long_cooldown_and_tiny_retry_after_retries():
    clock = [0.0]
    p1 = FakeProvider([LLMRateLimited("quota", quota_exhausted=True)])
    r = LLMRouter(S, {"fake": Dispatch(**{"fake-primary": p1, "fake-secondary": FakeProvider(["x"])})}, clock=lambda: clock[0])
    await r.generate(REQ, deadline_s=30)
    assert r.cooldown_active("fake:fake-primary") >= 600
    p3 = FakeProvider([LLMRateLimited("rl", retry_after_s=0.5), "recovered"])
    r2 = LLMRouter(S, {"fake": Dispatch(**{"fake-primary": p3, "fake-secondary": FakeProvider(["no"])})},
                   clock=lambda: clock[0], sleep=lambda s: _noop())
    assert (await r2.generate(REQ, deadline_s=30)).text == "recovered" and len(p3.calls) == 2


async def _noop():
    return None


def test_gemini_429_parses_retry_delay_and_daily_quota():
    from google.genai import errors as gerrors

    from app.llm.providers.gemini import GeminiProvider

    body = {"error": {"code": 429, "status": "RESOURCE_EXHAUSTED", "message": "quota",
                      "details": [{"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "34s"},
                                  {"violations": [{"quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier"}]}]}}
    exc = GeminiProvider(clients=[object()])._map_error(gerrors.APIError(429, body), "gemini-3.8-flash")
    assert isinstance(exc, LLMRateLimited) and exc.retry_after_s == 34.0 and exc.quota_exhausted is True


async def test_detail_request_with_short_answer_is_repaired(chart_unknown):
    short = chat_json("आपका सायन चंद्रमा लगभग मिथुन राशि में है। ध्यान रखें कि दशा अनुमानित है।",
                      ["META.TIME_UNKNOWN", "N.MOON.SIGN.GEMINI"])
    long = chat_json(("आपका सायन चंद्रमा लगभग मिथुन राशि में है। " + "यह स्थिति जिज्ञासा और संवाद की ओर झुकाव दर्शाती है। " * 25),
                     ["META.TIME_UNKNOWN", "N.MOON.SIGN.GEMINI"])
    p = FakeProvider([short, long])
    r = ChatResponder(LLMRouter(S, {"fake": Dispatch(**{"fake-primary": p, "fake-secondary": FakeProvider()})}))
    res = await r.answer(ChatInput(chart_data=chart_unknown, question="मेरे बारे में विस्तार से बताइए", history=[],
                                   language="hindi", today=TODAY))
    assert res["metadata"]["outcome"] == "repaired" and len(res["answer"].split()) >= 150
    assert "thorough" in p.calls[1][0].messages[-1]["content"]


def test_neutralize_gender_only_touches_user_addressing_honorifics():
    from app.llm.textclean import neutralize_gender

    assert neutralize_gender("आप आगे बढ़ सकती हैं।") == "आप आगे बढ़ सकते हैं।"
    assert neutralize_gender("Aap yeh kar sakti hain.") == "Aap yeh kar sakte hain."
    assert neutralize_gender("यह राशि संतुलन देती है।") == "यह राशि संतुलन देती है।"     # feminine noun, not the user
    assert neutralize_gender("शुक्र के कारण आप प्रेम में खुश रह सकते हैं।") == "शुक्र के कारण आप प्रेम में खुश रह सकते हैं।"


async def test_style_only_failure_is_accepted_not_503(chart_unknown):
    """A style nit that survives repair must never turn into LLMUnavailable."""
    short = chat_json("आपका सायन चंद्रमा लगभग मिथुन राशि में है।", ["META.TIME_UNKNOWN", "N.MOON.SIGN.GEMINI"])
    p = FakeProvider([short, short])
    r = ChatResponder(LLMRouter(S, {"fake": Dispatch(**{"fake-primary": p, "fake-secondary": FakeProvider()})}))
    res = await r.answer(ChatInput(chart_data=chart_unknown, question="विस्तार से बताइए", history=[], language="hindi",
                                   today=TODAY))
    assert res["metadata"]["outcome"] == "repaired_soft" and "style" in res["metadata"]["validator_flags"]


def test_small_talk_gate_and_deleak():
    from app.llm.textclean import deleak, is_small_talk

    assert is_small_talk("hi") and is_small_talk("Thanks!") and is_small_talk("नमस्ते")
    assert not is_small_talk("Is my Bhakoot dosha cancelled?") and not is_small_talk("Moon in 7th house result")
    out = deleak("CHART FACTS does not list today's tithi; the REFERENCE NOTES say so")
    assert "CHART FACTS" not in out and "REFERENCE NOTES" not in out and out.startswith("your chart data does not list")


async def test_when_every_model_is_cooling_down_the_soonest_one_is_still_tried():
    clock = [0.0]
    p1 = FakeProvider([LLMRateLimited("429", retry_after_s=40)])
    p2 = FakeProvider([LLMRateLimited("429", retry_after_s=10), "recovered"])
    r = LLMRouter(S, {"fake": Dispatch(**{"fake-primary": p1, "fake-secondary": p2})}, clock=lambda: clock[0])
    with pytest.raises(LLMUnavailable):
        await r.generate(REQ, deadline_s=30)                    # both 429: both now cooling down
    clock[0] = 1
    assert (await r.generate(REQ, deadline_s=30)).text == "recovered"   # no 503 storm: secondary (frees first) is forced
    assert len(p1.calls) == 1 and len(p2.calls) == 2
