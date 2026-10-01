"""Final acceptance QA: D4 compat tone/doshas/bands (exact QA cases), D3 system separation, D6 Hindi dasha spelling."""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

import pytest

import app.llm.service as service
from app.llm import configure, generate_compat_narrative
from app.llm.compat_checks import BANDS, band, consistency_problems, normalize_report
from app.llm.config import LLMSettings
from app.llm.errors import LLMUnavailable
from app.llm.providers.fake import FakeProvider

from .conftest import GOOD, TODAY, chat_json

ROOT = Path(__file__).resolve().parents[3]


class Dispatch:
    name = "fake"

    def __init__(self, **m):
        self.m = m

    async def generate(self, r, model):
        return await self.m[model].generate(r, model)

    def stream(self, r, model):
        return self.m[model].stream(r, model)


# ---- the backend's reduced report view (services/ai.py::_llm_report_view): NO `ashtakoota` dict, only `kootas`
def koota(name, score, mx):
    return {"name": name, "score": score, "max": mx}


KOOTAS_12 = [koota("Varna", 1, 1), koota("Vashya", 0, 2), koota("Tara", 1.5, 3), koota("Yoni", 0.5, 4),
             koota("Graha Maitri", 1, 5), koota("Gana", 0, 6), koota("Bhakoot", 0, 7), koota("Nadi", 8, 8)]
CASE_12 = {"overall_score": 4.7, "categories": {"emotional": {"score": 6.0}}, "aspects": [], "kootas": KOOTAS_12,
           "score_breakdown": {"western_overall": 6.1}}
CASE_46 = {"overall_score": 4.6, "categories": {"emotional": {"score": 5.0}}, "aspects": [], "kootas": []}
CASE_57 = {"overall_score": 5.7, "categories": {"emotional": {"score": 6.0}}, "aspects": [], "kootas": []}


def test_normalize_report_derives_ashtakoota_and_doshas_from_kootas():
    ak = normalize_report(CASE_12)["ashtakoota"]
    assert ak["total"] == 12.0 and ak["verdict"] == "below_average"
    assert ak["bhakoot_dosha"] and ak["gana_dosha"] and not ak["nadi_dosha"]


def test_d4_exact_case_12_of_36_with_bhakoot_and_gana():
    smooth = "A mixed pairing with real strengths, but not a smooth match overall."
    probs = consistency_problems(smooth, "emotional depth shared interests humour", CASE_12)
    assert any("Bhakoot" in p for p in probs) and any("Gana" in p for p in probs)
    # dosha names in the SUMMARY alone are not enough: they must be in the needs-care list (challenges)
    probs = consistency_problems("Bhakoot and Gana doshas are present; a mixed pairing.", "pace planning listening", CASE_12,
                                 challenges_text="pace planning listening")
    assert any("challenges" in p for p in probs)
    ok = consistency_problems("A mixed pairing; the Ashtakoota score of 12 out of 36 asks for care.",
                              "x", CASE_12, challenges_text="Bhakoot dosha: worth understanding, cancellations exist. "
                                                            "Gana dosha: temperament differences. Pace.")
    assert ok == []


def test_d4_exact_case_friendship_5_7_cannot_say_good_overall():
    probs = consistency_problems("A good overall dynamic with plenty of warmth.", "x", CASE_57, challenges_text="x")
    assert any("too positive" in p for p in probs)
    assert consistency_problems("Real strengths sit beside real differences; understanding them takes patience.", "x",
                                CASE_57, challenges_text="x") == []


def test_d4_exact_case_4_6_is_workable_and_must_not_be_called_harmonious():
    assert band(4.6) == "Workable"
    assert any("too positive" in p for p in consistency_problems("A harmonious and strong match.", "x", CASE_46, challenges_text="x"))


def test_single_band_table_matches_the_frontend():
    ts = (ROOT / "frontend" / "src" / "lib" / "compatBands.tsx").read_text()
    nums = [float(x) for x in re.findall(r"s10 >= ([0-9.]+)", ts)]
    assert nums == [t for t, _ in BANDS]
    for score, label in [(9.0, "Exceptional"), (8.4, "Harmonious"), (6.5, "Harmonious"), (6.4, "Workable"), (4.0, "Workable"),
                         (3.9, "Challenging")]:
        assert band(score) == label


@pytest.fixture
def daily():
    p = FakeProvider()
    s = LLMSettings(_env_file=None, LLM_MODEL_DAILY="fake-daily", LLM_FALLBACK_DAILY="", retry_backoff_ms=(0, 0))
    configure(s, providers={"fake": Dispatch(**{"fake-daily": p})})
    yield p
    service.reset()


def narrative(summary, challenges):
    return json.dumps({"summary": summary, "categories": [{"key": "emotional", "summary": "Feelings flow."}],
                       "aspect_interpretations": [], "strengths": ["warmth", "humour", "loyalty"], "challenges": challenges})


async def test_pipeline_with_reduced_backend_view_enforces_doshas(daily):
    bad = narrative("A mixed pairing, not a smooth match overall, with some real strengths and areas to work on.",
                    ["pace of life", "planning", "listening"])
    good = narrative("A mixed pairing; the Ashtakoota result of 12 out of 36 shows areas that need care and patience.",
                     ["Bhakoot dosha: worth understanding; traditional cancellations exist", "Gana dosha: temperament differences",
                      "Listening takes patience"])
    daily.push(bad, good)
    out = await generate_compat_narrative(CASE_12, "romantic")
    assert "Bhakoot" in " ".join(out["challenges"]) and len(daily.calls) == 2
    ctx = daily.calls[0][0].context_blocks[0]
    assert "[DOSHA.BHAKOOT]" in ctx and "[DOSHA.GANA]" in ctx and "verdict: below average" in ctx and "PRESENT" not in ctx and "Workable" in ctx


async def test_pipeline_friendship_good_overall_is_repaired(daily):
    daily.push(narrative("A good overall dynamic with plenty of ease.", ["a", "b", "c"]),
               narrative("Real strengths sit beside real differences; understanding them takes patience.", ["a", "b", "c"]))
    out = await generate_compat_narrative(CASE_57, "friend")
    assert "differences" in out["summary"] and len(daily.calls) == 2


# ----------------------------------------------------------------------------- D3: one system per answer

import app.llm.service as _svc  # noqa: E402
from app.llm.facts import ChartIndex, build_chart_facts, factor_system  # noqa: E402
from app.llm.responder import ChatInput, ChatResponder  # noqa: E402
from app.llm.router import LLMRouter  # noqa: E402
from app.llm.validators import check_system_blend  # noqa: E402

REAL = json.loads((ROOT / "backend" / "evals" / "fixtures" / "real_charts.json").read_text())
ENGINE_FACTORS = [   # exactly what the engine emits for a VEDIC request (app/astrology/personal.py)
    {"id": "V.MD.MOON", "kind": "dasha", "label": "Moon Mahadasha (2017-11-01 to 2027-11-01)", "weight": 1.0},
    {"id": "T.SATURN.SEXTILE.N.MARS", "kind": "transit", "label": "Transiting Saturn sextile natal Mars (orb 0.6°)", "weight": 0.5},
    {"id": "T.PLUTO.SEXTILE.N.ASC", "kind": "transit", "label": "Transiting Pluto sextile natal ASC (orb 0.5°)", "weight": 0.4},
    {"id": "T.NEPTUNE.CONJUNCTION.N.ASC", "kind": "transit", "label": "Transiting Neptune conjunction natal ASC", "weight": 0.4},
    {"id": "T.MOON.H6", "kind": "transit", "label": "Transiting Moon in house 6 from your natal Moon (Vedic)", "weight": 0.3},
]


def test_vedic_request_drops_tropical_transit_aspects_and_keeps_graha_factors():
    f = build_chart_facts(REAL["delhi_1994"], factors=ENGINE_FACTORS, system="vedic", today=TODAY)
    ids = f.factor_ids
    assert ids == {"V.MD.MOON", "T.MOON.H6"}, ids
    assert factor_system("T.PLUTO.SEXTILE.N.ASC") == "western" and factor_system("T.MOON.H6") == "vedic"
    w = build_chart_facts(REAL["delhi_1994"], factors=ENGINE_FACTORS, system="western", today=TODAY)
    assert "V.MD.MOON" not in w.factor_ids and "T.PLUTO.SEXTILE.N.ASC" in w.factor_ids


def test_derived_facts_and_summary_are_single_system():
    v = build_chart_facts(REAL["delhi_1994"], system="vedic", today=TODAY)
    text = v.render()
    assert not any(i.startswith(("N.", "A.")) for i in v.factor_ids)
    assert "tropical" not in text.lower().split("factors (cite")[0] and "sidereal" in text.lower()
    assert "Preferred system: vedic" in text and "Use ONLY" in text
    assert all("(Vedic, sidereal)" in line for line in text.splitlines() if line.startswith("[V"))
    w = build_chart_facts(REAL["delhi_1994"], system="western", today=TODAY)
    wt = w.render()
    assert not any(i.startswith(("VN.", "V.", "Y.")) for i in w.factor_ids)
    assert "nakshatra" not in wt.lower() and "dasha" not in wt.lower() and "(Western, tropical)" in wt
    b = build_chart_facts(REAL["delhi_1994"], system="both", today=TODAY)
    assert any(i.startswith("N.") for i in b.factor_ids) and any(i.startswith("VN.") for i in b.factor_ids)


def test_chips_carry_a_system_label_in_the_reply_language():
    from app.llm.labels import system_suffix, with_system

    assert with_system("V.MD.MOON", "Current Moon Mahadasha", "english") == "Current Moon Mahadasha · Vedic (sidereal)"
    assert with_system("N.SUN.SIGN.CANCER", "Natal Sun in Cancer (tropical)", "english").endswith("· Western (tropical)")
    assert with_system("T.SATURN.SEXTILE.N.MARS", "x", "hindi").endswith("पाश्चात्य (सायन)")
    assert system_suffix("META.TIME_UNKNOWN", "english") == ""


@pytest.mark.parametrize("system,answer,question,flagged", [
    ("vedic", "Your tropical Moon is in Taurus, while your sidereal Moon is in Aries.", "How is my Moon?", True),
    ("vedic", "आपका सायन चंद्रमा वृषभ में और निरयन चंद्रमा मेष में है।", "मेरा चंद्रमा?", True),
    ("vedic", "Your sidereal Moon in Mesha in Krittika nakshatra feels bold.", "How is my Moon?", False),
    ("vedic", "Your tropical Moon is in Taurus.", "What is my tropical Moon sign?", False),
    ("western", "Your Moon nakshatra is Krittika and the Saturn Mahadasha runs on.", "How is my Moon?", True),
    ("western", "Your tropical Moon in Taurus is steady.", "How is my Moon?", False),
    ("both", "Your tropical Moon is Taurus; sidereal Moon is Aries.", "How is my Moon?", False),
])
def test_system_blend_validator(system, answer, question, flagged):
    assert bool(check_system_blend(answer, system, question)) is flagged


async def test_vedic_chat_answer_that_blends_systems_is_repaired():
    chart = REAL["delhi_1994"]
    blend = ("Your tropical Moon is in Taurus, while your sidereal Moon is in Dhanu (Sagittarius). Your Moon Mahadasha keeps emotions in "
             "focus, so a steady routine will help you.")
    clean = ("Your sidereal Moon in Dhanu (Sagittarius) sits in Purva Ashadha nakshatra. Your Moon Mahadasha keeps emotions in focus, "
             "so a steady routine will help you.")
    cites = ["VN.MOON.RASHI.SAGITTARIUS", "V.MD.MOON"]
    p = FakeProvider([chat_json(blend, cites), chat_json(clean, cites)])
    s = LLMSettings(_env_file=None, LLM_MODEL_CHAT="fake-primary", LLM_FALLBACK_CHAT="", retry_backoff_ms=(0, 0))
    r = ChatResponder(LLMRouter(s, {"fake": Dispatch(**{"fake-primary": p})}))
    res = await r.answer(ChatInput(chart_data=chart, question="How is my Moon?", history=[], astrology_system="vedic", today=TODAY))
    assert res["answer"] == clean and res["metadata"]["outcome"] == "repaired" and "system" in res["metadata"]["first_draft_flags"]
    assert all(c["label"].endswith("· Vedic (sidereal)") for c in res["citations"])


async def test_daily_personal_context_is_vedic_only_for_vedic_users():
    p = FakeProvider([json.dumps({
        "headline": "A steady day for patience", "overview": "Your Moon Mahadasha keeps emotions in focus today, so keep a calm, "
        "measured pace and notice what supports you through the day ahead.",
        "areas": {k: {"text": f"A calm, practical note for {k} today: one step at a time."} for k in ("love", "career", "wellness", "money")},
        "affirmation": "I move with patience.", "citations": ["V.MD.MOON"]})])
    configure(LLMSettings(_env_file=None, LLM_MODEL_DAILY="fake-daily", LLM_FALLBACK_DAILY="", retry_backoff_ms=(0, 0)),
              providers={"fake": Dispatch(**{"fake-daily": p})})
    try:
        facts = {"date": "2026-10-01", "system": "vedic", "areas": {k: {"score": 3} for k in ("love", "career", "wellness", "money")},
                 "key_factors": [{"factor_id": f["id"], "label": f["label"], "weight": f["weight"]} for f in ENGINE_FACTORS]}
        out = await _svc.generate_daily_personal(facts, language="english")
        ctx = p.calls[0][0].context_blocks[0]
        assert "T.PLUTO" not in ctx and "T.NEPTUNE" not in ctx and "T.SATURN.SEXTILE.N.MARS" not in ctx
        assert "[V.MD.MOON]" in ctx and "[T.MOON.H6]" in ctx and "Vedic" in ctx and out["generated_by"] == "llm"
    finally:
        _svc.reset()


# ----------------------------------------------------------------------------- D6: Hindi dasha spelling

from app.llm.textclean import fix_terms  # noqa: E402


@pytest.mark.parametrize("bad,good", [
    ("आपकी शनि अंतर्दृशा चल रही है", "आपकी शनि अंतर्दशा चल रही है"),
    ("अन्तर्दृशा और महादृशा", "अंतर्दशा और महादशा"),
    ("आपकी चंद्र महादशा", "आपकी चंद्र महादशा"),
    ("आपका नक्षेत्र रोहिणी है", "आपका नक्षत्र रोहिणी है"),
    ("Your mahadasa and antardasa", "Your mahadasha and antardasha"),
    ("your nakshtra is Rohini", "your nakshatra is Rohini"),
    ("विंशोतरी दशा", "विंशोत्तरी दशा"),
])
def test_fix_terms(bad, good):
    assert fix_terms(bad) == good


def test_glossary_and_prompt_know_the_correct_terms():
    from app.llm.prompts import get_registry
    from app.rag.glossary import gloss_terms

    assert "antardasha" in gloss_terms("अंतर्दशा क्या है") and "mahadasha" in gloss_terms("महादशा")
    assert "antardasha" in gloss_terms("अंतर्दृशा")                       # the misspelling still retrieves the right note
    t = get_registry().render("chat", streaming=False, language_instruction="x", length_hint="x").text
    assert "अंतर्दशा" in t and "महादशा" in t and "नक्षत्र" in t


# ----------------------------------------------------------------------------- enum leakage

from app.llm.compat_checks import leaked_tokens, plain_words  # noqa: E402
from app.llm.service import compat_fact_lines  # noqa: E402


def test_plain_words_maps_enums_and_flags():
    assert plain_words("The verdict is below_average and the Bhakoot dosha is PRESENT.") == \
        "The verdict is below average and the Bhakoot dosha is present."
    assert plain_words("good_with_friction") == "good with friction" and leaked_tokens("fine text") == []
    assert leaked_tokens("below_average PRESENT") == ["below_average", "PRESENT"]


def test_report_facts_use_plain_words():
    text = " ".join(l for _, l in compat_fact_lines(CASE_12)[0])
    assert leaked_tokens(text.replace("[", "")) == [] or "PRESENT" not in text and "below_average" not in text


async def test_narrative_with_leaked_tokens_is_cleaned(daily):
    daily.push(narrative("A mixed pairing; Ashtakoota is below_average and the Bhakoot dosha is PRESENT.",
                         ["Bhakoot dosha: PRESENT, worth understanding", "Gana dosha", "Pace"]))
    out = await generate_compat_narrative(CASE_12, "romantic")
    assert leaked_tokens(out["summary"] + " ".join(out["challenges"])) == []
    assert "below average" in out["summary"]
