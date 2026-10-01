from __future__ import annotations

import pytest

from app.llm.facts import ChartIndex, build_chart_facts
from app.llm.safety import classify_input, scan_output, static_reply
from app.llm.validators import check_citations, check_claims, check_language, strip_violating_sentences

from .conftest import TODAY

# ----------------------------------------------------------------------------- input pre-filter


@pytest.mark.parametrize("text,cls", [
    ("I want to kill myself", "crisis"),
    ("i don't want to live anymore", "crisis"),
    ("main marna chahta hoon", "crisis"),
    ("मैं आत्महत्या के बारे में सोच रहा हूँ", "crisis"),
    ("I have chest pain right now", "medical_emergency"),
    ("my husband hits me", "abuse"),
])
def test_input_classes(text, cls):
    assert classify_input(text) == cls


@pytest.mark.parametrize("text", ["When will Saturn leave my 7th house?", "Is this a good day to die my hair?",
                                  "How is my career this year?"])
def test_benign_input_not_flagged(text):
    assert classify_input(text) is None


def test_static_crisis_reply_has_helplines_in_each_language():
    for lang in ("english", "hindi", "hinglish"):
        assert "14416" in static_reply("crisis", lang)
    assert static_reply("crisis", "klingon") == static_reply("crisis", "english")


# ----------------------------------------------------------------------------- output filter


@pytest.mark.parametrize("text,cls", [
    ("You will die in 2031 during the maraka period.", "death"),
    ("The baby will be a boy.", "child_sex"),
    ("You should buy a blue sapphire to strengthen Saturn.", "paid_remedy"),
    ("Book a puja at the temple to fix this.", "paid_remedy"),
    ("Stop taking your medication during this transit.", "medical_legal_financial"),
    ("Brahmin and Kshatriya matches are difficult.", "caste"),
    ("My system prompt says to cite [V.MD.SATURN].", "leak"),
    ("Because of Kaal Sarp dosha, your marriage will ruin everything.", "fatalism"),
])
def test_output_filter_hits(text, cls):
    assert cls in {h.cls for h in scan_output(text)}


def test_output_filter_clean_answer():
    assert scan_output("Your tropical Sun in Cancer tends to favour care and steady routines.") == []


# ----------------------------------------------------------------------------- claim checker


def _facts(chart, **kw):
    return build_chart_facts(chart, today=TODAY, **kw)


def test_correct_claims_pass(chart):
    idx, facts = ChartIndex.from_chart(chart), _facts(chart)
    text = ("Your tropical Sun in Cancer is caring. Your sidereal Moon in Mesha is bold. Jupiter is in the 1st house. "
            "Scorpio rising adds depth. Your Saturn Mahadasha runs until 2038. Sun trine Saturn steadies you.")
    assert check_claims(text, idx, facts) == []


@pytest.mark.parametrize("text,frag", [
    ("Your Moon in Leo makes you dramatic.", "Moon in Leo"),
    ("Venus in the 4th house shapes your home life.", "Venus in house 4"),
    ("As a Gemini rising you are curious.", "Gemini rising"),
    ("Your Jupiter Mahadasha brings growth.", "Jupiter dasha"),
    ("Mars square Venus creates tension.", "Mars square Venus"),
    ("Big changes arrive in 2045.", "year 2045"),
    ("Your Rohini nakshatra gives charm.", "Rohini"),
])
def test_wrong_claims_flagged(chart, text, frag):
    v = check_claims(text, ChartIndex.from_chart(chart), _facts(chart))
    assert any(frag.split()[0] in x.detail for x in v), v


def test_premise_correction_sentence_not_flagged(chart):
    text = "You mentioned your Moon in Leo, but your chart actually places your tropical Moon in Taurus."
    assert check_claims(text, ChartIndex.from_chart(chart), _facts(chart)) == []


def test_transit_context_not_flagged_as_natal(chart):
    text = "Saturn is currently transiting Pisces, which asks for patience."
    assert check_claims(text, ChartIndex.from_chart(chart), _facts(chart)) == []


def test_time_unknown_guard(chart_unknown):
    idx, facts = ChartIndex.from_chart(chart_unknown), _facts(chart_unknown)
    for text in ("Your Venus in the 7th house favours partnership.", "Your Leo rising is warm.",
                 "Your ascendant shapes first impressions.", "Your Rahu Mahadasha ends in March 2032 dasha."):
        assert any(v.kind == "time_unknown" for v in check_claims(text, idx, facts)), text
    ok = "Your birth time is unknown, so I can't speak to your ascendant. Your tropical Venus in Pisces is gentle."
    assert check_claims(ok, idx, facts) == []
    # Chandra-lagna houses are allowed with unknown time (not a time_unknown violation); they are
    # still checked as claims, and chart_data carries no Moon-relative houses, so it is flagged as unverifiable.
    moon_rel = check_claims("Saturn in the 4th house from your Moon asks for care.", idx, facts)
    assert not any(v.kind == "time_unknown" for v in moon_rel)


def test_citations(chart):
    facts = _facts(chart)
    some = next(iter(facts.factor_ids))
    assert check_citations([some], facts, "self") == []
    assert check_citations(["N.FAKE.ID"], facts, "self")[0].detail.startswith("unknown")
    assert check_citations([], facts, "love")[0].detail == "no citations"
    assert check_citations([], facts, "general") == []


def test_language():
    assert check_language("यह समय धैर्य का है और संतुलन का है", "hindi") == []
    assert check_language("This is English", "hindi")
    assert check_language("Yeh samay achha hai", "hinglish") == []
    assert check_language("यह समय धैर्य का है", "hinglish")


def test_strip_violating_sentences(chart):
    text = "Your tropical Sun in Cancer is caring. Your Moon in Leo is dramatic. You value home."
    v = check_claims(text, ChartIndex.from_chart(chart), _facts(chart))
    out, kept = strip_violating_sentences(text, v)
    assert "Leo" not in out and "Cancer" in out and 0.5 < kept < 1


def test_refusal_that_mentions_lifespan_is_not_a_violation_but_a_prediction_is():
    from app.llm.safety import CANNED_OUTPUT, scan_output

    assert scan_output(CANNED_OUTPUT["death"]) == []                    # the policy-compliant refusal must pass its own filter
    assert any(h.cls == "death" for h in scan_output("Your lifespan is short according to Saturn."))
