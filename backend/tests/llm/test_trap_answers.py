"""BUG-027 live trap findings: a fake LLM returns the bad outputs seen (or feared) live; the pipeline must reject them."""

from __future__ import annotations

import pytest

from app.llm.config import LLMSettings
from app.llm.providers.fake import FakeProvider
from app.llm.responder import ChatInput, ChatResponder
from app.llm.router import LLMRouter
from app.llm.safety import canned_output, scan_output, static_reply
from app.llm.validators import check_third_party_chart

from .conftest import TODAY, chat_json
from .test_responder_service import Dispatch

PRICE = ("Certified blue sapphire prices vary widely from tens of thousands to lakhs of rupees depending on quality, and traditions "
         "differ on whether gemstones are suitable for everyone, so please take your time and ask a qualified person.")
OK_PRICE = ("I don't have price information, and you don't need to buy anything. Traditions differ on gemstones; some sources say they "
            "are optional. A steady routine, reflection or a short daily mantra are free practices some people find grounding. " * 1)


def resp(answers, **kw):
    s = LLMSettings(_env_file=None, LLM_MODEL_CHAT="fake-primary", LLM_FALLBACK_CHAT="", retry_backoff_ms=(0, 0))
    p = FakeProvider([chat_json(a, c, topic="general") for a, c in answers])
    return ChatResponder(LLMRouter(s, {"fake": Dispatch(**{"fake-primary": p})})), p


async def ask(chart, q, answers, lang="english"):
    r, p = resp(answers)
    return await r.answer(ChatInput(chart_data=chart, question=q, history=[], today=TODAY, astrology_system="vedic", language=lang)), p


@pytest.mark.parametrize("text", [
    "Blue sapphire costs Rs 25,000 to Rs 2 lakh.", "Neelam ki kimat hazaron se lakhon rupaye tak hoti hai.",
    "नीलम की कीमत कुछ हज़ार से लाख रुपये तक होती है।", "It starts at $300 per carat.", "The price is ₹ 40000.",
])
def test_invented_prices_are_an_output_violation(text):
    assert "price" in [h.cls for h in scan_output(text)]


@pytest.mark.parametrize("text", ["The winning numbers are 12 45 67 on the board.", "Your lucky number today is 7 and winning number 4 21 33."])
def test_lottery_numbers_are_rejected(text):
    assert "gambling" in [h.cls for h in scan_output(text)]


def test_plain_wording_is_not_flagged():
    assert not scan_output("Your chart facts do not list a Ketu dasha. Rahu Kaal depends on sunrise; a thousand thanks for asking.")
    assert [h.cls for h in scan_output("As per my safety policy I cannot do that.")] == ["leak"]
    assert [h.cls for h in scan_output("CHART FACTS says Venus")] == ["leak"]


async def test_price_answer_is_repaired_then_canned_never_shown(chart):
    res, p = await ask(chart, "What is the price of a blue sapphire in rupees?", [(PRICE, ["V.MD.SATURN"]), (PRICE, ["V.MD.SATURN"])])
    assert res["metadata"]["outcome"] == "canned" and res["answer"] == canned_output("price") and "rupees" not in res["answer"]


async def test_price_answer_that_declines_passes_after_repair(chart):
    res, p = await ask(chart, "What is the price of a blue sapphire in rupees?", [(PRICE, ["V.MD.SATURN"]), (OK_PRICE, ["V.MD.SATURN"])])
    assert res["metadata"]["outcome"] == "repaired" and res["answer"] == OK_PRICE.strip()


async def test_lowercase_chart_facts_wording_is_not_a_canned_leak(chart):
    ans = ("Rahu Kaal depends on sunrise and your location, which are not listed in your chart facts here, so check a local panchang. "
           "Traditions differ on how it is used. " * 2)
    res, p = await ask(chart, "What is Rahu Kaal right now?", [(ans, ["V.MD.SATURN"])])
    assert res["metadata"]["outcome"] in ("ok", "repaired", "repaired_soft") and "local panchang" in res["answer"]


async def test_negated_dasha_sentence_is_not_a_false_claim(chart):
    ans = ("Your chart facts do not contain the start and end dates for a Ketu dasha, as you are running a different period now. "
           "Dashas follow a fixed order and traditions vary on exact timing, so it is better to look at your present period. " * 1)
    res, p = await ask(chart, "When does my Ketu dasha start? Give exact dates.", [(ans, ["V.MD.SATURN"])])
    assert res["metadata"]["outcome"] == "ok" and len(p.calls) == 1


def test_third_party_chart_needs_a_no_data_first_sentence():
    q = "Tell me Sachin Tendulkar's birth chart and his planetary positions."
    assert check_third_party_chart(q, "Your sidereal Moon is in Karka. Your Sun is in Meena.")
    assert not check_third_party_chart(q, "I don't have Sachin Tendulkar's birth data; I only hold your own chart. I can read yours.")
    assert not check_third_party_chart("What is Rahu's chart effect?", "Rahu tends to...")


async def test_celebrity_chart_answer_that_shows_the_users_chart_is_repaired(chart):
    bad = "Your sidereal Moon is in Karka and your Sun is in Meena. " + "It tends to bring depth. " * 4
    good = ("I don't have Sachin Tendulkar's birth data; I only hold your own chart, but I can read it. " + "Your current period tends to favour steady effort. " * 3)
    res, p = await ask(chart, "Tell me Sachin Tendulkar's birth chart.", [(bad, ["V.MD.SATURN"]), (good, ["V.MD.SATURN"])])
    assert res["metadata"]["outcome"] == "repaired" and res["answer"].startswith("I don't have")


async def test_safety_policy_wording_is_replaced_by_the_canned_reply(chart):
    bad = "Main kisi ki bhi maut ke baare mein prediction nahi de sakta kyunki yeh meri safety policy ke khilaaf hai. " * 2
    res, p = await ask(chart, "Meri biwi ki maut kab hogi?", [(bad, []), (bad, [])], lang="hinglish")
    assert "safety policy" not in res["answer"]


def test_prompt_v8_carries_the_new_rules():
    from app.llm.prompts import get_registry

    reg = get_registry()
    assert reg.verify() == [] and reg.active_version("chat") == "v8"
    t = reg.render("chat", streaming=False, language_instruction="x", length_hint="y").text
    for needle in ("Never state a price", "another person's chart", "Never mention a safety policy", "Exact dates, months or years"):
        assert needle in t
    assert "Never state a price" not in reg.render("chat", version="v7", streaming=False, language_instruction="x", length_hint="y").text


def test_panchang_question_with_right_now_is_still_general():
    from app.llm.qtype import classify_question

    for q in ("What is Rahu Kaal right now?", "Abhi Rahu Kaal kab hai?", "आज की तिथि अभी क्या है?"):
        assert classify_question(q).kind == "general", q
    assert classify_question("Am I in Venus mahadasha right now?").kind == "personal"
