"""BUG-025: answer-first chat (chat@v7), the question-type classifier and the answer-shape validators.

Live finding: "What does Mars mahadasha with Venus antardasha mean?" was answered with the user's own Venus/Mercury
period. The claim checker flagged "Mars Mahadasha" as "not the current dasha", the repair then rewrote the answer
around the chart. These tests pin the classifier, the generic-claim exemption, the shape validators and the prompt."""

from __future__ import annotations

import pytest

from app.llm.config import LLMSettings
from app.llm.facts import ChartIndex, build_chart_facts, focus_factors
from app.llm.providers.fake import FakeProvider
from app.llm.qtype import classify_question, focus_line, order_notes, question_kind_for_prompt
from app.llm.responder import ChatInput, ChatResponder
from app.llm.router import LLMRouter
from app.llm.validators import (
    check_answer_shape,
    check_claims,
    check_hinglish,
    opens_with_concept,
    validate_answer,
)

from .conftest import TODAY, chat_json
from .test_responder_service import Dispatch


@pytest.fixture(scope="module")
def chart_a():
    """A real engine chart (Venus Mahadasha / Mercury Antardasha today), synthetic birth data."""
    from datetime import date, datetime, time, timezone

    from app.astrology import compute_natal_chart

    return compute_natal_chart(date_of_birth=date(1992, 4, 12), time_of_birth=time(9, 30), has_exact_time=True, latitude=28.61,
                               longitude=77.21, timezone="Asia/Kolkata", now_utc=datetime(2026, 10, 1, 6, 0, tzinfo=timezone.utc))


@pytest.fixture(scope="module")
def chart_b():
    from datetime import date, datetime, timezone

    from app.astrology import compute_natal_chart

    return compute_natal_chart(date_of_birth=date(1988, 8, 3), time_of_birth=None, has_exact_time=False, latitude=19.07,
                               longitude=72.88, timezone="Asia/Kolkata", now_utc=datetime(2026, 10, 1, 6, 0, tzinfo=timezone.utc))

LIVE_Q = "What does Mars mahadasha with Venus antardasha mean?"

# (question, kind, subtype, wants_tie): the exact live question plus 15+ across types, Hindi and Hinglish
CASES = [
    (LIVE_Q, "general", "dasha_pair", False),
    ("What does Rahu Mahadasha with Jupiter antardasha mean for me?", "general", "dasha_pair", True),
    ("Venus antardasha in Mars mahadasha kya hota hai", "general", "dasha_pair", False),
    ("मंगल महादशा में शुक्र की अंतर्दशा का क्या मतलब होता है?", "general", "dasha_pair", False),
    ("Mangal mahadasha mein Shukra ki antardasha ka kya matlab hota hai?", "general", "dasha_pair", False),
    ("What does Saturn Mahadasha usually bring?", "general", "dasha", False),
    ("What is Gajakesari yoga and how does it form?", "general", "yoga", False),
    ("What is the result of the Moon in the 7th house?", "general", "planet_house", False),
    ("What does Ketu in the 12th house mean?", "general", "planet_house", False),
    ("What is today's tithi and is it good for starting something new?", "general", "panchang", False),
    ("Rahu Kaal kya hota hai aur kya isme kaam shuru karna chahiye?", "general", "panchang", False),
    ("How does Ashtakoota matching work and what is a good score?", "general", "compat", False),
    ("Is Manglik dosha a problem in marriage?", "general", "compat", False),
    ("What is Sade Sati?", "general", "sade_sati", False),
    ("शनि की साढ़ेसाती क्या होती है?", "general", "sade_sati", False),
    ("Which remedies are traditionally suggested for a weak Saturn?", "general", "remedy", False),
    ("What is the Navamsa chart used for?", "general", "concept", False),
    ("How is my career looking?", "personal", "other", False),
    ("What is my current dasha and what does it mean?", "personal", "other", False),
    ("मेरी कुंडली में अभी कौन सी दशा चल रही है?", "personal", "other", False),
    ("Meri Shani ki sade sati kaisi rahegi?", "personal", "sade_sati", False),
    ("My Saturn mahadasha ends when?", "personal", "dasha", False),
    ("Should I wear a blue sapphire for Saturn?", "personal", "concept", False),
    ("Will I get married soon?", "personal", "other", False),
    ("hi", "smalltalk", "other", False),
]


@pytest.mark.parametrize("q,kind,subtype,tie", CASES)
def test_classifier(q, kind, subtype, tie):
    t = classify_question(q)
    assert (t.kind, t.subtype, t.wants_tie) == (kind, subtype, tie), t


def test_dasha_pair_lords_are_ordered_by_role_not_by_appearance():
    t = classify_question("Venus antardasha in Mars mahadasha kya hota hai")
    assert (t.md, t.ad) == ("Mars", "Venus")
    t = classify_question("मंगल महादशा में शुक्र की अंतर्दशा का क्या मतलब होता है?")
    assert (t.md, t.ad) == ("Mars", "Venus")
    assert "Mars Mahadasha with the Venus Antardasha" in focus_line(classify_question(LIVE_Q))
    assert focus_line(classify_question("How is my career looking?")) is None


def test_prompt_mode_per_type():
    assert question_kind_for_prompt(classify_question(LIVE_Q)) == "general"
    assert question_kind_for_prompt(classify_question("What does Rahu Mahadasha with Jupiter antardasha mean for me?")) == "general_tie"
    assert question_kind_for_prompt(classify_question("What is today's tithi?")) == "general_notie"
    assert question_kind_for_prompt(classify_question("How is my career looking?")) == "personal"


class Note:
    def __init__(self, cid, content):
        self.chunk_id, self.file, self.heading_path, self.content = cid, "f.md", "H", content


def test_pair_note_is_moved_to_the_front():
    notes = [Note("a", "| **Venus-Venus** | row"), Note("b", "| **Mars-Venus** | 14 months | Drive meets desire")]
    assert [n.chunk_id for n in order_notes(notes, classify_question(LIVE_Q))] == ["b", "a"]
    assert order_notes(notes, classify_question("What is Sade Sati?")) == notes


# ----------------------------------------------------------------------------- shape validators

GOOD_GENERAL = ("Mars Mahadasha with Venus Antardasha is a period where drive meets desire, bringing relationships, property and "
                "creative pursuits into focus.\n\nSome sources say it tends to bring moderate impulsiveness in love and spending, "
                "so a measured pace helps. " + "It is a time to channel energy into steady, structured goals. " * 3 +
                "In your chart, Mars rules the 7th and 12th houses.")
CHART_FIRST = ("Your chart is currently running your Venus Mahadasha with the Mercury Antardasha, which shapes your whole outlook. "
               "Your Moon in Karka and your Lagna in Vrishabha add to that. Mars and Venus together tend to bring drive and desire "
               "into relationships, property and creative pursuits, with some impulsiveness around spending and love.")


def test_general_answer_must_name_the_asked_concept_first():
    qt = classify_question(LIVE_Q)
    assert opens_with_concept(GOOD_GENERAL, qt)
    assert not opens_with_concept(CHART_FIRST, qt)
    flags = check_answer_shape(CHART_FIRST, qt)
    assert any("FIRST sentence" in v.detail for v in flags) and all(v.kind in ("style", "length") for v in flags)
    assert not [v for v in check_answer_shape(GOOD_GENERAL, qt) if v.kind == "style"]


def test_all_dasha_pair_planets_must_be_named():
    qt = classify_question(LIVE_Q)
    assert not opens_with_concept("Venus Mahadasha with Mercury Antardasha is a period of commerce and creativity. " * 2, qt)
    assert opens_with_concept("In this pairing Mars supplies the drive while Venus adds desire and comfort. It tends to...", qt)


@pytest.mark.parametrize("opening", [
    "Your birth chart is a map of the sky at the moment you were born, and it shows a lot about you.",
    "Based on your chart, this period is about growth.",
    "आपकी जन्म कुंडली के अनुसार यह समय विकास का है।",
    "Aapki janam kundli ke anusaar yeh samay achha hai.",
])
def test_boilerplate_opening_is_flagged(opening):
    for q in (LIVE_Q, "How is my career looking?"):
        assert any("boilerplate" in v.detail for v in check_answer_shape(opening + " " + "word " * 80, classify_question(q)))


def test_general_answer_with_chart_recital_is_flagged():
    text = (GOOD_GENERAL + " Your Moon is in Karka. Your Sun is in Meena. Your Lagna is Vrishabha. Your Mars is in Kumbha.")
    assert any("own chart" in v.detail for v in check_answer_shape(text, classify_question(LIVE_Q)))


def test_length_bounds_are_soft_except_when_far_too_long():
    qt = classify_question(LIVE_Q)
    short = "Mars Mahadasha with Venus Antardasha is a period where drive meets desire."
    assert [v.kind for v in check_answer_shape(short, qt)] == ["length"]            # never repaired
    long = "Mars Mahadasha with Venus Antardasha is a period of drive. " + "More words follow here. " * 90
    assert [v.kind for v in check_answer_shape(long, qt)] == ["style"]               # repaired once
    assert check_answer_shape(long, qt, detail="detailed") == []                     # detail requests keep their own bounds


def test_hinglish_reply_must_not_be_plain_english():
    english = ("Mars Mahadasha with Venus Antardasha brings a meeting of drive and desire where relationships, property and creative "
               "pursuits become active, along with some impulsiveness in love and spending, so a measured and steady pace tends to help.")
    assert check_hinglish(english, "hinglish") and not check_hinglish(english, "english")
    hing = "Mangal mahadasha mein Shukra ki antardasha ek aisa samay hai jisme rishte aur sampatti ke maamle sakriya hote hain, aur aap ko sambhal kar chalna accha rehta hai kyunki kharch badh sakta hai"
    assert check_hinglish(hing, "hinglish") == []


# ----------------------------------------------------------------------------- the root cause: generic claims

def test_generic_sentence_about_a_non_current_dasha_is_not_a_claim(chart):
    facts, idx = build_chart_facts(chart, today=TODAY), ChartIndex.from_chart(chart)       # the chart's period is Saturn/Mercury
    text = "Mars Mahadasha with Venus Antardasha is a period where drive meets desire."
    assert [v for v in check_claims(text, idx, facts) if v.kind == "claim"]                  # old behaviour: "Mars dasha is not current"
    assert not [v for v in check_claims(text, idx, facts, generic=True) if v.kind == "claim"]
    # a sentence that addresses the user, and any year, are still checked
    mine = "Your Mars Mahadasha is running now."
    assert [v for v in check_claims(mine, idx, facts, generic=True) if v.kind == "claim"]
    assert [v for v in check_claims("This period peaks around 2041.", idx, facts, generic=True) if v.kind == "claim"]


def test_generic_house_statement_is_ok_for_unknown_time(chart_unknown):
    facts, idx = build_chart_facts(chart_unknown, today=TODAY), ChartIndex.from_chart(chart_unknown)
    text = "The Moon in the 7th house tends to tie emotional security to partnership."
    assert [v for v in check_claims(text, idx, facts) if v.kind == "time_unknown"]
    assert not check_claims(text, idx, facts, generic=True)
    assert [v for v in check_claims("Your Moon in the 7th house shows this.", idx, facts, generic=True) if v.kind == "time_unknown"]


def test_validate_answer_passes_generic_for_general_questions_only(chart):
    facts, idx = build_chart_facts(chart, today=TODAY), ChartIndex.from_chart(chart)
    ans = "Mars Mahadasha with Venus Antardasha is a period where drive meets desire. " + "It tends to favour steady effort. " * 8
    kw = dict(facts=facts, idx=idx, language="english", question=LIVE_Q)
    assert not [v for v in validate_answer(ans, ["KB1"], "general", qtype=classify_question(LIVE_Q), **kw) if v.kind == "claim"]
    assert [v for v in validate_answer(ans, ["KB1"], "general", qtype=None, **kw) if v.kind == "claim"]


# ----------------------------------------------------------------------------- focus facts

def test_focus_factors_give_placement_and_lordship_without_computing(chart_a):
    out = focus_factors(chart_a, ["Mars", "Venus"], system="vedic", approx=False)
    ids = {f.id for f in out}
    assert "VN.MARS.RASHI.AQUARIUS" in ids and "VN.VENUS.RASHI.PISCES" in ids
    assert next(f for f in out if f.id == "VN.MARS.LORDS").label.startswith("Mars rules the 7th and 12th houses")
    assert next(f for f in out if f.id == "VN.VENUS.LORDS").label.startswith("Venus rules the 1st and 6th houses")
    assert not [f for f in focus_factors(chart_a, ["Mars"], system="western", approx=False) if f.id.endswith(".LORDS")]


def test_focus_factors_skip_houses_when_time_unknown(chart_b):
    out = focus_factors(chart_b, ["Mars"], system="vedic", approx=True)
    assert out and not [f for f in out if f.id.endswith(".LORDS")] and not any("house" in f.label for f in out)


def test_facts_for_general_question_are_compact_and_focused(chart_a):
    qt = classify_question(LIVE_Q)
    facts = build_chart_facts(chart_a, system="vedic", today=TODAY, focus_planets=qt.planets, k=7)
    ids = [f.id for f in facts.factors]
    assert "V.MD.VENUS" in ids and "VN.MARS.LORDS" in ids and "VN.VENUS.LORDS" in ids and len(ids) <= 10
    assert len(set(ids)) == len(ids)


# ----------------------------------------------------------------------------- the prompt and the responder


def test_chat_v7_renders_the_answer_shape_and_keeps_v6_locked():
    from app.llm.prompts import get_registry

    reg = get_registry()
    assert reg.verify() == [] and reg.active_version("chat") == "v7"
    kw = dict(streaming=False, language_instruction="English.", length_hint="100 to 180 words")
    g = reg.render("chat", answer_mode="general", **kw).text
    assert "general question" in g and "Name the thing asked about" in g
    assert "Never open with a sentence about the chart as a whole" in g and "14416" in g          # safety v2 line
    assert "Do not mention the user's chart" in reg.render("chat", answer_mode="general_notie", **kw).text
    p = reg.render("chat", answer_mode="personal", **kw).text
    assert "personal question" in p and "Name the thing asked about" not in p
    old = reg.render("chat", version="v6", **kw).text
    assert "ANSWER SHAPE" not in old and "14416" not in old                                          # v6 text untouched


def _resp(answers, retriever=None):
    s = LLMSettings(_env_file=None, LLM_MODEL_CHAT="fake-primary", LLM_FALLBACK_CHAT="", retry_backoff_ms=(0, 0))
    p = FakeProvider([chat_json(a, c, topic="general") for a, c in answers])
    return ChatResponder(LLMRouter(s, {"fake": Dispatch(**{"fake-primary": p})}), retriever=retriever), p


async def test_general_question_answered_about_the_asked_pair_needs_no_repair(chart_a):
    chart = chart_a
    r, p = _resp([(GOOD_GENERAL, ["VN.MARS.LORDS"])])
    res = await r.answer(ChatInput(chart_data=chart, question=LIVE_Q, history=[], today=TODAY, astrology_system="vedic"))
    assert len(p.calls) == 1 and res["metadata"]["outcome"] == "ok"
    assert res["answer"].startswith("Mars Mahadasha with Venus Antardasha")
    req = p.calls[0][0]
    assert any(b.startswith("QUESTION FOCUS") and "Mars Mahadasha with the Venus Antardasha" in b for b in req.context_blocks)
    assert "[VN.MARS.LORDS]" in req.context_blocks[0]
    assert res["metadata"]["question_kind"] == "general" and res["metadata"]["question_subtype"] == "dasha_pair"


async def test_chart_first_answer_to_a_general_question_is_repaired_to_answer_first(chart_a):
    chart = chart_a
    r, p = _resp([(CHART_FIRST, ["V.MD.VENUS"]), (GOOD_GENERAL, ["VN.MARS.LORDS"])])
    res = await r.answer(ChatInput(chart_data=chart, question=LIVE_Q, history=[], today=TODAY, astrology_system="vedic"))
    assert res["metadata"]["outcome"] == "repaired" and "style" in res["metadata"]["first_draft_flags"]
    assert res["answer"] == GOOD_GENERAL
    repair_note = p.calls[1][0].messages[-1]["content"]
    assert "FIRST sentence" in repair_note


async def test_chart_first_is_never_a_failed_reply(chart_a):
    chart = chart_a
    r, p = _resp([(CHART_FIRST, ["V.MD.VENUS"]), (CHART_FIRST, ["V.MD.VENUS"])])
    res = await r.answer(ChatInput(chart_data=chart, question=LIVE_Q, history=[], today=TODAY, astrology_system="vedic"))
    assert res["metadata"]["outcome"] == "repaired_soft"          # style nits never 503


async def test_personal_question_still_leads_with_the_chart(chart):
    ans = ("Your current Saturn Mahadasha with Mercury Antardasha puts the focus on steady, structured work. " + "It tends to reward patience. " * 8)
    r, p = _resp([(ans, ["V.MD.SATURN"])])
    res = await r.answer(ChatInput(chart_data=chart, question="What is my current dasha and what does it mean?", history=[],
                                   today=TODAY, astrology_system="vedic"))
    assert res["metadata"]["outcome"] == "ok" and len(p.calls) == 1
    assert res["metadata"]["question_kind"] == "personal"


async def test_general_answer_citing_only_its_notes_is_valid(chart):
    r, p = _resp([(GOOD_GENERAL.replace("In your chart, Mars rules the 7th and 12th houses.", ""), ["KB1"])])

    class Retr:
        async def retrieve(self, **kw):
            return [Note("kb#1", "Mars-Venus: drive meets desire")]

    r.retriever = Retr()
    res = await r.answer(ChatInput(chart_data=chart, question=LIVE_Q, history=[], today=TODAY, astrology_system="vedic"))
    assert res["metadata"]["outcome"] == "ok" and "citation" not in (res["metadata"]["first_draft_flags"] or [])


def test_closing_line_about_the_users_own_other_period_is_flagged_for_a_plain_general_question():
    qt = classify_question(LIVE_Q)
    tail = " In your chart, your current period is actually Venus Mahadasha and Mercury Antardasha."
    assert any("own current period" in v.detail for v in check_answer_shape(GOOD_GENERAL.replace(
        " In your chart, Mars rules the 7th and 12th houses.", "") + tail, qt))
    assert not [v for v in check_answer_shape(GOOD_GENERAL, qt) if v.kind == "style"]                      # lordship tie is fine
    tie = classify_question("What does Rahu Mahadasha with Jupiter antardasha mean for me?")
    assert not [v for v in check_answer_shape(
        "Rahu Mahadasha with Jupiter Antardasha is a time where ambition meets wisdom. " + "It tends to reward ethics. " * 8 + tail, tie)
        if "own current period" in v.detail]                                                              # "for me": telling them is useful


def test_bare_fact_id_in_prose_is_removed_not_a_canned_leak():
    from app.llm.textclean import strip_fact_ids

    text, found = strip_fact_ids("Your VN.MOON.RASHI.CANCER placement shows depth. Version 1.2.3 and U.S.A stay.")
    assert "VN.MOON" not in text and found == ["VN.MOON.RASHI.CANCER"] and "1.2.3" in text and "U.S.A" in text
    assert strip_fact_ids("Plain text with Moon.rashi")[0] == "Plain text with Moon.rashi"


def test_paragraph_breaks_survive_the_text_pipeline():
    from app.llm.textclean import neutralize_gender

    t = "आप कर सकती हैं। दूसरा वाक्य।\n\nनया अनुच्छेद यहाँ है।"
    out = neutralize_gender(t)
    assert "\n\n" in out and "सकते हैं" in out
