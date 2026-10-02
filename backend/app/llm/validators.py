"""Deterministic answer validators (llm-integration.md §3 [7]).

1. citations ⊆ provided factor IDs, >= 1 unless topic is general
2. claim checker: placement / house / rising / dasha / nakshatra / aspect / retrograde / date
   claims are resolved against chart_data and the provided factors
3. time-unknown guard
4. safety output filter (safety.py)
5. language script check
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.llm.facts import ChartFacts, ChartIndex
from app.llm.lexicon import (
    ASPECT_LOOKUP,
    ASPECT_RE,
    MONTHS,
    NAKSHATRA_LOOKUP,
    NAKSHATRA_RE,
    ORDINALS,
    PLANET_RE,
    SIGN_RE,
    canon_planet,
    canon_sign,
)
from app.llm.safety import scan_output
from app.llm.textclean import assumes_female


@dataclass(frozen=True)
class Violation:
    kind: str           # citation | claim | time_unknown | safety:<class> | language
    detail: str
    sentence: str = ""


_SENT_SPLIT = re.compile(r"(?<=[.!?।])\s+|\n+")
_TRANSIT_WORDS = re.compile(r"\b(transit\w*|currently|right now|this (week|month|year)|today|moving|stations?|ingress)\b|गोचर", re.I)
_B = r"(?<![\w])"
_E = r"(?![\w])"

PLANET_IN_SIGN = re.compile(
    rf"{_B}(?P<p>{PLANET_RE}){_E}(?:\s+(?:is|was|sits|placed|located|falls))?\s+(?:in|into)\s+(?:the\s+sign\s+of\s+)?(?P<s>{SIGN_RE}){_E}"
    rf"|{_B}(?P<p2>{PLANET_RE}){_E}\s+(?P<s2>{SIGN_RE})\s+(?:राशि\s+)?में", re.I)
SIGN_PLANET = re.compile(rf"{_B}(?P<s>{SIGN_RE})\s+(?P<p>{PLANET_RE}){_E}", re.I)  # "your Leo Sun"
PLANET_IN_HOUSE = re.compile(
    rf"{_B}(?P<p>{PLANET_RE}){_E}(?:\s+(?:is|sits|placed))?\s+in\s+(?:the\s+|your\s+)?"
    rf"(?:(?P<n>\d{{1,2}})(?:st|nd|rd|th)|(?P<w>{'|'.join(ORDINALS)}))\s+(?:house|bhava)", re.I)
HOUSE_ANY = re.compile(rf"\b(\d{{1,2}}(?:st|nd|rd|th)|{'|'.join(ORDINALS)})\s+(house|bhava)\b|(?<![\u0900-\u097F])भाव(?![\u0900-\u097F])", re.I)
RISING = re.compile(
    rf"{_B}(?P<s>{SIGN_RE})\s+(?:rising|ascendant|lagna){_E}"
    rf"|(?:rising sign|ascendant|lagna)\s+(?:is|in|of)\s+(?P<s2>{SIGN_RE}){_E}", re.I)
ANGLE_ANY = re.compile(r"\b(rising sign|ascendant|lagna|midheaven|\bMC\b)|(?<![\u0900-\u097F])लग्न(?![\u0900-\u097F])", re.I)
DASHA = re.compile(
    rf"{_B}(?P<p>{PLANET_RE}){_E}\s+(?P<k>maha\s*dasha|mahadasha|antar\s*dasha|antardasha|dasha|bhukti|महादशा|अंतर्दशा|दशा)", re.I)
RETRO = re.compile(rf"retrograde\s+(?P<p>{PLANET_RE}){_E}|{_B}(?P<p2>{PLANET_RE})\s+(?:is\s+)?retrograde", re.I)
ASPECT = re.compile(rf"{_B}(?P<a>{PLANET_RE})\s+(?P<t>{ASPECT_RE})\s+(?:your\s+|natal\s+)?(?P<b>{PLANET_RE}){_E}", re.I)
NAK_YOURS = re.compile(rf"\byour\b[^.]{{0,30}}?{_B}(?P<n>{NAKSHATRA_RE}){_E}|(?P<n2>{NAKSHATRA_RE})\s+is\s+your", re.I)
YEAR = re.compile(r"\b(19\d{2}|20\d{2})\b")
ISO_DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
MONTH_YEAR = re.compile(rf"\b({'|'.join(MONTHS)})\s+(19|20)\d{{2}}\b", re.I)
CORRECTION = re.compile(r"\b(not|isn'?t|rather than|instead of|you mentioned|you said|you thought|actually)\b|नहीं", re.I)
HOUSE_YOGA = re.compile(r"\b(gajakesari|gaja kesari|raja yoga|dhana yoga|mangal dosha|manglik|kendra|trikona)\b", re.I)
UNAVAIL = re.compile(
    r"\b(unknown|not (?:known|available)|isn'?t available|can'?t|cannot|without|unavailable|do(?:es)? not have|"
    r"don'?t have|(?:do|does) not (?:contain|include|list|show)|not (?:listed|included|provided)|no (?:start|end|exact) dates?)\b|अज्ञात|ज्ञात नहीं|उपलब्ध नहीं|बिना|नहीं (?:बता|मिल|दे) सक|pata nahi|available nahi|maloom nahi|nahi bata", re.I)
FROM_MOON = re.compile(r"from (your|the) moon|chandra[\s-]?lagna|चंद्र लग्न", re.I)


def sentences(text: str) -> list[str]:
    return [s for s in _SENT_SPLIT.split(text) if s.strip()]


def _aliases(token: str) -> tuple[str, ...]:
    """A planet or sign by every name the lexicon knows: Cancer = Karka = कर्क, Mercury = Budha = बुध (BUG-025: a
    daily reading that wrote "Jupiter in Cancer" for the fact "Jupiter in Karka" was rejected as an invented placement)."""
    from app.llm.lexicon import PLANET_ALIASES, SIGN_ALIASES

    t = token.lower()
    for table in (PLANET_ALIASES, SIGN_ALIASES):
        for canon, names in table.items():
            if t == canon.lower() or t in names:
                return tuple({canon.lower(), *names})
    return (t,)


def _factor_supports(facts: ChartFacts, *tokens: str) -> bool:
    """A claim is also supported when some provided factor label names all its tokens
    (covers transit/compatibility facts that are not in natal chart_data). Planet and sign names match by alias."""
    toks = [_aliases(t) for t in tokens if t]
    return any(all(any(a in f.label.lower() for a in alts) for alts in toks) for f in facts.factors)


def _house_num(m: re.Match) -> int | None:
    if m.group("n"):
        return int(m.group("n"))
    w = m.group("w")
    return ORDINALS.get(w.lower()) if w else None


_SECOND_PERSON = re.compile(r"\b(?:your|you|you're|you'll|yours|yourself|aap|aapki|aapka|aapke|apni|apna|apne)\b|आप|तुम|तेरी|तेरा", re.I)


def check_claims(answer: str, idx: ChartIndex, facts: ChartFacts, *, transit_exempt: bool = True,
                 generic: bool = False) -> list[Violation]:
    """`transit_exempt`: natal-chart answers may describe current transits that are not in the
    natal data; for the daily sky (where the facts ARE the transits) pass False.
    `generic`: the question is a general one ("what does Mars mahadasha with Venus antardasha mean"): a sentence that
    does not address the user ("you", "your", आप) states a general meaning, not a chart fact, so a dasha / house /
    placement named in it is not checked against this chart. Sentences about the user, and every year, still are.
    (Before this, the claim checker "repaired" such answers into restating the user's own dasha: BUG-025.)"""
    out: list[Violation] = []
    allowed_years: set[int] = set()
    for f in facts.factors:
        if f.window:
            y0, y1 = int(f.window[0][:4]), int(f.window[1][:4])
            allowed_years.update(range(y0, y1 + 1))
    if idx.birth_year:
        allowed_years.add(idx.birth_year)
    if facts.today[:4].isdigit():
        allowed_years.add(int(facts.today[:4]))  # "Today" is itself a provided fact

    for sent in sentences(answer):
        transit_ctx = transit_exempt and bool(_TRANSIT_WORDS.search(sent))
        unavail = bool(UNAVAIL.search(sent))   # "I can't see your lagna without your birth time" is the RIGHT answer

        general_sentence = generic and not _SECOND_PERSON.search(sent)

        def bad(kind: str, detail: str, always: bool = False) -> None:
            if general_sentence and not always:
                return
            out.append(Violation(kind, detail, sent.strip()[:300]))

        # planet in sign
        pairs = [(m.group("p") or m.group("p2"), m.group("s") or m.group("s2")) for m in PLANET_IN_SIGN.finditer(sent)]
        pairs += [(m.group("p"), m.group("s")) for m in SIGN_PLANET.finditer(sent)]
        for pw, sw in pairs:
            p, s = canon_planet(pw), canon_sign(sw)
            if not p or not s:
                continue
            natal_ok = (idx.western.get(p, (None,))[0] == s) or (idx.vedic.get(p, (None,))[0] == s)
            if p == "Rahu" and not natal_ok:
                natal_ok = idx.western.get("Rahu", (None,))[0] == s
            if not natal_ok and not _factor_supports(facts, p, s) and not transit_ctx and not CORRECTION.search(sent):
                bad("claim", f"{p} in {s} not in chart")
        # planet in house
        for m in PLANET_IN_HOUSE.finditer(sent):
            p, n = canon_planet(m.group("p")), _house_num(m)
            if not p or not n:
                continue
            if idx.approximate_time and not FROM_MOON.search(sent):
                if not unavail:
                    bad("time_unknown", f"house claim with unknown birth time: {p} in house {n}")
                continue
            ok = idx.western.get(p, (None, None))[1] == n or idx.vedic.get(p, (None, None))[1] == n
            if not ok and not _factor_supports(facts, p, f"{n}") and not transit_ctx:
                bad("claim", f"{p} in house {n} not in chart")
        # rising / lagna
        for m in RISING.finditer(sent):
            s = canon_sign(m.group("s") or m.group("s2") or "")
            if idx.approximate_time:
                if not unavail:
                    bad("time_unknown", "rising sign / lagna mentioned with unknown birth time")
            elif s and s not in (idx.rising, idx.lagna):
                bad("claim", f"{s} rising/lagna not in chart")
        # dasha lords
        for m in DASHA.finditer(sent):
            p = canon_planet(m.group("p"))
            if p and p not in (idx.maha, idx.antar) and not _factor_supports(facts, p, "dasha") and not unavail:
                bad("claim", f"{p} dasha is not current")
        # retrograde
        for m in RETRO.finditer(sent):
            p = canon_planet(m.group("p") or m.group("p2") or "")
            if not p:
                continue
            natal = idx.western.get(p, (None, None, False))[2] or idx.vedic.get(p, (None, None, False, None))[2]
            if not natal and not _factor_supports(facts, p, "retrograde") and not transit_ctx:
                bad("claim", f"{p} retrograde not in chart")
        # aspects
        for m in ASPECT.finditer(sent):
            a, b = canon_planet(m.group("a")), canon_planet(m.group("b"))
            t = ASPECT_LOOKUP.get(m.group("t").lower())
            if not a or not b or not t or a == b:
                continue
            key = tuple(sorted((a, b)))
            if (key[0], t, key[1]) not in idx.aspects and not _factor_supports(facts, a, b) and not transit_ctx:
                bad("claim", f"{a} {t} {b} not in chart")
        # nakshatra claimed as the user's
        for m in NAK_YOURS.finditer(sent):
            n = NAKSHATRA_LOOKUP.get((m.group("n") or m.group("n2") or "").lower())
            if n and n not in idx.nakshatras and not _factor_supports(facts, n):
                bad("claim", f"{n} nakshatra not in chart")
        # dates
        if idx.approximate_time and (ISO_DATE.search(sent) or MONTH_YEAR.search(sent)) and "dasha" in sent.lower():
            bad("time_unknown", "exact dasha date with unknown birth time")
        for m in YEAR.finditer(sent):
            y = int(m.group(1))
            if y not in allowed_years:
                bad("claim", f"year {y} not in any provided factor window", always=True)
        # angles with unknown time (non-specific mentions)
        if idx.approximate_time and not FROM_MOON.search(sent) and not unavail:
            if HOUSE_ANY.search(sent) and not PLANET_IN_HOUSE.search(sent):
                bad("time_unknown", "house mentioned with unknown birth time")
            if HOUSE_YOGA.search(sent):
                bad("time_unknown", "house-based yoga/dosha mentioned with unknown birth time")
            if ANGLE_ANY.search(sent) and not RISING.search(sent) and not re.search(r"\bunknown|not (known|available)|without\b", sent, re.I):
                bad("time_unknown", "angle mentioned with unknown birth time")
    return out


def check_citations(citations: list[str], facts: ChartFacts, topic: str, kb_only_ok: bool = False) -> list[Violation]:
    unknown = [c for c in citations if c not in facts.citable_ids]
    out = [Violation("citation", f"unknown factor id {c}") for c in unknown]
    kb_ok = kb_only_ok and any(c in dict(facts.kb_aliases) for c in citations)   # a general answer citing only its notes
    if not any(c in facts.factor_ids for c in citations) and topic != "general" and facts.factors and not kb_ok:
        out.append(Violation("citation", "no citations"))   # a factor ID is required; KB-only citations are not enough
    return out


_DEVANAGARI = re.compile(r"[ऀ-ॿ]")
_LETTER = re.compile(r"[A-Za-zऀ-ॿ]")


def devanagari_ratio(text: str) -> float:
    letters = _LETTER.findall(text)
    return (len(_DEVANAGARI.findall(text)) / len(letters)) if letters else 0.0


def check_language(text: str, language: str) -> list[Violation]:
    r = devanagari_ratio(text)
    if language == "hindi" and r < 0.70:
        return [Violation("language", f"expected Devanagari, ratio {r:.2f}")]
    if language in ("english", "hinglish") and r > 0.10:
        return [Violation("language", f"expected Latin script, devanagari ratio {r:.2f}")]
    return []


_HINGLISH_WORDS = frozenset((
    "hai", "hain", "ka", "ki", "ke", "ko", "mein", "aur", "kya", "nahi", "yeh", "woh", "hota", "hoti", "hote", "liye", "bhi",
    "aap", "aapki", "aapke", "aapka", "jab", "tab", "iska", "iski", "unka", "kuch", "samay", "rehta", "rehti", "kaafi", "isliye",
    "lekin", "agar", "toh", "se", "par", "wala", "wali", "jaata", "jaati", "karta", "karti", "karein", "kijiye", "rakhein"))


def check_hinglish(text: str, language: str) -> list[Violation]:
    """Hinglish is Hindi in Roman script. A plain-English reply to a Hinglish user passes the script check, so count
    Romanised-Hindi function words. Soft ("style"): one repair, never a failed reply."""
    if language != "hinglish":
        return []
    words = re.findall(r"[a-zA-Z]+", text.lower())
    if len(words) < 25:
        return []
    share = sum(1 for w in words if w in _HINGLISH_WORDS) / len(words)
    if share < 0.04:
        return [Violation("style", "the user writes Hinglish: reply in Hinglish (Hindi in Roman script mixed with English), not plain English")]
    return []


def check_safety(text: str) -> list[Violation]:
    return [Violation(f"safety:{h.cls}", h.match) for h in scan_output(text)]


# --- answer shape (BUG-025): answer-first for general questions, length bounds, boilerplate openings -------------------

_BOILERPLATE_OPEN = re.compile(
    r"^\W*(?:your|aapki|aapka|aapke|आपकी|आपका|आपके)\s+(?:birth|natal|janam|जन्म)\s*(?:chart|kundli|kundali|कुंडली|चार्ट)(?![\w\u0900-\u097F])"
    r"|^\W*(?:based on|according to|looking at|as per|आपकी कुंडली के अनुसार|आपके चार्ट के अनुसार)\s+(?:your|the)\s+(?:birth\s+|natal\s+)?(?:chart|kundli)", re.I)
_CHART_REF = re.compile(
    r"\b(?:your|aapki|aapka|aapke|aap ki|aap ka)\b[^.!?\n]{0,40}?\b(?:chart|kundli|kundali|natal|dasha|mahadasha|antardasha|moon|sun|"
    r"lagna|ascendant|rashi|nakshatra|saturn|jupiter|venus|mars|mercury|rahu|ketu)\b"
    r"|(?:आपकी|आपका|आपके)\s+(?:\S+\s+){0,3}?(?:कुंडली|चार्ट|दशा|महादशा|अंतर्दशा|चंद्र|सूर्य|लग्न|राशि|नक्षत्र|शनि|गुरु|शुक्र|मंगल|बुध|राहु|केतु)"
    r"|\bin your chart\b|\byour (?:current|present) ", re.I)

# Word-count bounds per answer mode (normal detail). Soft: a breach is a "style" nit, never a failed reply.
SHAPE_WORDS = {"general": (60, 230), "general_tie": (70, 250), "personal": (70, 300)}


def paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n|\n", text) if p.strip()]


def _anchor_hit(text: str, anchors: tuple[str, ...]) -> bool:
    return any(re.search(a, text, re.I) for a in anchors)


def first_paragraph(text: str) -> str:
    ps = paragraphs(text)
    return ps[0] if ps else ""


def _hit(text: str, qt) -> bool:
    if not qt.anchors:
        return True
    if qt.anchor_all:
        return all(re.search(a, text, re.I) for a in qt.anchors)
    return _anchor_hit(text, qt.anchors)


def opens_with_concept(answer: str, qt) -> bool:
    """True when the asked concept is named up front: in the first sentence, or in the first two sentences when the
    first one is not a restatement of the user's own chart (every planet of a dasha pair must be named)."""
    sents = sentences(answer)
    if not sents or not qt.anchors:
        return True
    first = sents[0]
    if _hit(first, qt):
        return True
    return not _CHART_REF.search(first) and _hit(" ".join(sents[:2]), qt)


def check_answer_shape(answer: str, qt, detail: str = "normal") -> list[Violation]:
    """Answer-first discipline (soft "style" violations; they trigger one repair and never fail a reply).

    general   the asked concept is named in the first two sentences; the first sentence is not chart boilerplate;
              at most 2 sentences refer to the user's own chart; 60-230 words; at most 5 paragraphs.
    personal  the first sentence is not "Your birth chart is..." boilerplate; 70-300 words.
    Detail requests (asked for "in detail" / "briefly") keep their own bounds in check_style."""
    out: list[Violation] = []
    if qt is None or qt.kind == "smalltalk":
        return out
    sents = sentences(answer)
    first = sents[0] if sents else ""
    if _BOILERPLATE_OPEN.search(first):
        out.append(Violation("style", "do not open with \"Your birth chart is...\" boilerplate; start with the answer itself", first[:200]))
    mode = "general" if qt.kind == "general" else "personal"
    if qt.kind == "general":
        if not opens_with_concept(answer, qt):
            named = ", ".join(dict.fromkeys(qt.planets)) or "the concept asked about"
            out.append(Violation("style", f"this is a general question: your FIRST sentence must answer it by naming {named} and "
                                          "what it means; move any mention of the user's chart to one short last line", first[:200]))
        refs = [s for s in sents if _CHART_REF.search(s)]
        if len(refs) > 2:
            out.append(Violation("style", f"{len(refs)} sentences talk about the user's own chart; a general question gets at most "
                                          "one short personalisation line at the end", refs[0][:200]))
        if len(paragraphs(answer)) > 5:
            out.append(Violation("style", "use 2 to 4 short paragraphs"))
        if qt.subtype in ("dasha_pair", "dasha") and not qt.wants_tie:
            asked = set(qt.planets)
            for s_ in sents:
                lords = {canon_planet(m.group("p")) for m in DASHA.finditer(s_)} - {None}
                if lords - asked and _SECOND_PERSON.search(s_):
                    out.append(Violation("style", "the closing chart line talks about the user's own current period, which is not the "
                                                  "pair asked about; tie it to the asked planets (their sign, house or houses ruled) or leave it out", s_[:200]))
                    break
        if "tie" in getattr(qt, "subtype", "") or getattr(qt, "wants_tie", False):
            mode = "general_tie"
    if detail == "normal":
        lo, hi = SHAPE_WORDS[mode]
        n = len(answer.split())
        if n > hi * 1.25:
            out.append(Violation("style", f"answer has {n} words; aim for {lo + 20} to {hi - 30} words"))
        elif n < lo or n > hi:
            out.append(Violation("length", f"answer has {n} words; the target is {lo + 20} to {hi - 30}"))
    return out


def check_style(answer: str, language: str, detail: str = "normal") -> list[Violation]:
    out = []
    words = len(answer.split())
    if detail == "detailed" and words < 150:
        out.append(Violation("style", f"the user asked for detail but the answer has only {words} words; give a "
                                      "thorough 220-320 word answer from the available facts"))
    if detail == "brief" and words > 130:
        out.append(Violation("style", f"the user asked for a brief answer but it has {words} words; keep it under 90"))
    if language in ("hindi", "hinglish") and assumes_female(answer):
        out.append(Violation("style", "assumes the user's gender (feminine verb forms); use gender-neutral phrasing"))
    return out


_VEDIC_WORDS = re.compile(r"\bsidereal\b|nakshatra|dasha|lagna|\bvedic\b|निरयन|नक्षत्र|दशा|लग्न|वैदिक", re.I)
_WESTERN_WORDS = re.compile(r"\btropical\b|\bwestern\b|सायन|पाश्चात्य", re.I)


def check_system_blend(answer: str, system: str, question: str = "") -> list[Violation]:
    """D3: a vedic user's answer must not mention tropical/Western placements (and vice versa) unless asked."""
    if system == "vedic" and _WESTERN_WORDS.search(answer) and not _WESTERN_WORDS.search(question):
        return [Violation("system", "answer mixes in tropical/Western placements; use only the Vedic (sidereal) system")]
    if system == "western" and _VEDIC_WORDS.search(answer) and not _VEDIC_WORDS.search(question):
        return [Violation("system", "answer mixes in Vedic terms (nakshatra, dasha, sidereal); use only the Western (tropical) system")]
    return []


_HEDGE = re.compile(
    r"some (?:sources|traditions|schools|astrologers|texts)|traditions? (?:differ|vary)|schools? (?:differ|vary)|"
    r"according to (?:some|one)|not (?:universally|all)|\bvaries\b|may differ|opinions? (?:differ|vary)|"
    r"sources? (?:differ|disagree)|कुछ (?:स्रोत|परंपरा|विद्वान|ज्योतिष)|परंपराएं? (?:अलग|भिन्न)|मतभेद|अलग-अलग|"
    r"kuch (?:log|paramparaon|sources)|alag alag|\bvaries\b", re.I)


def check_distress(question: str, answer: str) -> list[Violation]:
    """A question with hopelessness wording must get empathy + the crisis resources, not a prediction (BUG-025)."""
    from app.llm.safety import distress_signals, has_crisis_resources

    if question and distress_signals(question) and not has_crisis_resources(answer):
        return [Violation("safety:crisis", "the question shows distress; the reply must carry the crisis resources")]
    return []


_OTHER_CHART = re.compile(
    r"\b[A-Z][\w.]+(?:\s+[A-Z][\w.]+){0,2}['\u2019]s\s+(?:birth\s+|natal\s+)?(?:chart|kundli|kundali|horoscope|planets?)\b"
    r"|\b(?:chart|kundli|kundali|horoscope)\s+of\s+(?!my\b|mine\b|me\b)[A-Z]"
    r"|\b(?!meri\b|mera\b|apni\b|apna\b|my\b)[A-Za-z]+\s+(?:ki|ka)\s+(?:janam\s+)?(?:kundli|kundali)\b(?<!\bmeri kundli)"
    r"|(?<![\u0900-\u097F])(?!मेरी|मेरा|अपनी)[\u0900-\u097F]+\s+(?:की|का)\s+(?:जन्म\s*)?(?:कुंडली|कुण्डली)", re.U)
_NO_DATA = re.compile(
    r"(?:do(?:es)?\s*n[o']t|don'?t|cannot|can'?t)\s+(?:have|hold|see)|no\s+(?:birth\s+)?(?:data|details)|only\s+(?:have|hold)|"
    r"नहीं\s+(?:है|हैं|हूं|हूँ)|उपलब्ध\s+नहीं|paas\s+.{0,40}nahi|data\s+nahi|nahi\s+(?:hai|hain)", re.I)


def check_third_party_chart(question: str, answer: str) -> list[Violation]:
    """Asked for someone else's chart ("Sachin Tendulkar's chart"): the first sentence must say there is no birth data for that
    person, not present the user's own chart as theirs (BUG-027, live trap test)."""
    m = _OTHER_CHART.search(question or "")
    if m and not any(canon_planet(w.strip("'’s")) or canon_sign(w.strip("'’s")) for w in re.findall(r"[\w.]+", m.group(0))[:3]):
        first = " ".join(sentences(answer)[:2])
        if not _NO_DATA.search(first):
            return [Violation("style", "the user asked about another person's chart: say in the first sentence that you only have the "
                                       "user's own birth data, never present the user's chart as theirs", first[:200])]
    return []


def check_hedge(answer: str, citations: list[str], facts: ChartFacts) -> list[Violation]:
    """Claims taken from a low-confidence / [unverified] / schools-differ note must be hedged, never stated as fact."""
    cited = [c for c in citations if c in facts.kb_hedge]
    if cited and not _HEDGE.search(answer):
        return [Violation("hedge", f"note {cited[0]} is low-confidence/unverified or traditions differ; say \"some sources say\" "
                                   "or \"traditions differ\", or leave the claim out")]
    return []


def uncited_claims(answer: str, citations: list[str], idx: ChartIndex, facts: ChartFacts) -> bool:
    """Soft signal: the answer states chart placements but cites no computed factor."""
    if any(c in facts.factor_ids for c in citations):
        return False
    return bool(PLANET_IN_SIGN.search(answer) or SIGN_PLANET.search(answer) or PLANET_IN_HOUSE.search(answer)
                or DASHA.search(answer))


def validate_answer(answer: str, citations: list[str], topic: str, *, facts: ChartFacts,
                    idx: ChartIndex, language: str, detail: str = "normal", question: str = "",
                    qtype=None) -> list[Violation]:
    from app.llm.safety import distress_signals

    # A caring reply to a distressed message cites no chart factor (it must contain no astrology).
    cites = [] if (question and distress_signals(question)) else check_citations(
        citations, facts, topic, kb_only_ok=bool(qtype and qtype.is_general))
    return (
        check_distress(question, answer)
        + cites
        + check_claims(answer, idx, facts, generic=bool(qtype and qtype.is_general))
        + check_safety(answer)
        + check_language(answer, language)
        + check_hinglish(answer, language)
        + check_style(answer, language, detail)
        + check_answer_shape(answer, qtype, detail)
        + check_system_blend(answer, facts.system, question)
        + check_hedge(answer, citations, facts)
        + check_third_party_chart(question, answer)
    )


def strip_violating_sentences(answer: str, violations: list[Violation]) -> tuple[str, float]:
    """Remove sentences with claim/time violations. Returns (text, kept_fraction by chars)."""
    bad = {v.sentence for v in violations if v.sentence}
    sents = sentences(answer)
    kept = [s for s in sents if s.strip()[:300] not in bad]
    total = sum(len(s) for s in sents) or 1
    return " ".join(s.strip() for s in kept), sum(len(s) for s in kept) / total
