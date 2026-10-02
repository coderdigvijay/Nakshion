"""Question-type classifier: cheap deterministic rules, no extra LLM call (BUG-025).

Decides HOW the chat answer is shaped:

  general   a question about a concept (a dasha pair, a yoga, a planet in a house, Panchang, a compatibility rule,
            Sade Sati as a idea, remedies for a planet...). Answer the concept FIRST from the retrieved reference
            notes, then at most ONE short line tying it to the user's chart, only if relevant.
  personal  a question about the user's own chart or life ("my career", "my dasha", "will I...", मेरी, mera).
            Lead with the chart facts that answer it.
  smalltalk greeting / thanks.

`wants_tie` is True for "what does X mean *for me*": a concept question that explicitly asks for the personal angle.
`anchors` are the things the first paragraph of a general answer must name (the asked concept), used by the
answer-first validator; `anchor_all` is True when every planet named must appear (a dasha pair).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.llm.lexicon import PLANET_RE, canon_planet
from app.llm.textclean import is_small_talk

_W = r"(?<![\wऀ-ॿ])"
_E = r"(?![\wऀ-ॿ])"

# Strong chart-specific markers (English, Hindi, Hinglish).
_PERSONAL = re.compile(
    rf"{_W}(?:my|mine|myself|i|i'm|im|i've|ive|am i|will i|should i|can i|shall i|do i|did i|would i)(?:{_E})"
    rf"|मेरा|मेरी|मेरे|मुझे|मुझ|मैं|हमारा|हमारी|हमारे"
    rf"|{_W}(?:mera|meri|mere|mujhe|mujhko|mujh|main|mai|hamara|hamari|hamare|meri kundli){_E}",
    re.I)
# "for me" only asks for the personal angle of a concept question.
_FOR_ME = re.compile(
    rf"{_W}(?:for me|to me|in my life|for my chart|in my chart|mere liye|mere lie|mere baare|mere bare|mujhpe|mujh par){_E}"
    r"|मेरे लिए|मेरे बारे|मुझ पर|मुझपर|मेरी कुंडली में|मेरे जीवन",
    re.I)
_STRIP_FOR_ME = re.compile(_FOR_ME.pattern, re.I)

_DASHA = r"(?:maha\s*dasha|mahadasha|antar\s*dasha|antardasha|pratyantar\w*|bhukti|dasha|महादशा|अंतर्दशा|प्रत्यंतर\w*|दशा|भुक्ति)"
_DASHA_RE = re.compile(_DASHA, re.I)
_YOGA_RE = re.compile(r"yoga|yog\b|योग|raja\s*yog|gajakesari|gaja kesari|budhaditya|kendra|trikona|dhana yoga|pancha mahapurusha", re.I)
_HOUSE_RE = re.compile(
    r"\b(?:\d{1,2}(?:st|nd|rd|th)|first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|eleventh|twelfth)\s+(?:house|bhava|lord)|"
    r"\b(?:house|bhava)\s+(?:no\.?\s*)?\d{1,2}\b|\b\d{1,2}\s*(?:th|st|nd|rd)?\s*(?:ghar|bhav)\b|भाव|घर|\b(?:ghar|bhav)\b|\b(?:\d{1,2}|seventh|7th)\s*lord\b", re.I)
_PANCHANG_RE = re.compile(
    r"panchang|panchaang|tithi|rahu\s*kaal|rahukaal|rahu kalam|choghadiya|muhurat|muhurta|abhijit|karana|nakshatra today|"
    r"पंचांग|तिथि|राहु\s*काल|राहुकाल|चौघड़िया|मुहूर्त|अभिजित|एकादशी|अमावस्या|पूर्णिमा|ekadashi|amavasya|purnima",
    re.I)
_COMPAT_RE = re.compile(
    r"compatib|kundli milan|kundali milan|ashtakoota|ashtakuta|guna milan|gun milan|\bkoota\b|\bkuta\b|bhakoot|bhakut|"
    r"\bnadi\b|\bgana\b|\bvarna\b|synastry|\bmanglik\b|mangal dosh|mangal dosha|mangalik|kuja dosh|\bmatch(?:ing)?\b|36 gun|"
    r"मिलान|गुण मिलान|कुंडली मिलान|भकूट|नाड़ी|मांगलिक|मंगल दोष|मेल",
    re.I)
_SADESATI_RE = re.compile(r"sade\s*-?\s*sati|sadesati|saade\s*saati|sadhe\s*sati|dhaiya|dhaiyya|साढ़े\s*साती|साढ़ेसाती|साढ़ेसाती|साढे\s*साती|ढैया", re.I)
_REMEDY_RE = re.compile(r"remed|upay|upaay|mantra|gemstone|pooja|puja|charity|fast(?:ing)?\b|उपाय|मंत्र|पूजा|दान|व्रत", re.I)
_TRANSIT_RE = re.compile(r"transit|gochar|gochara|गोचर|retrograde|vakri|वक्री|eclipse|grahan|ग्रहण", re.I)
_CONCEPT_LEAD = re.compile(
    r"^\s*(?:what(?:'s| is| are| does| do| happens)|explain|define|tell me about|meaning of|how (?:does|do|is|are|many)|"
    r"which|why (?:is|are|does|do)|kya (?:hai|hota|hoti|hote|hain)|\w+ kya (?:hai|hota|hoti|hote|hain)|matlab|"
    r"क्या (?:है|होता|होती|होते|हैं)|\w+ क्या (?:है|होता|होती|होते|हैं)|का (?:मतलब|अर्थ)|क्या मतलब|किसे कहते)",
    re.I)
_CONCEPT_ANY = re.compile(
    r"\bmean(?:s|ing)?\b|\bkya hai\b|\bkya hota\b|\bmatlab\b|\bhow is\b .{0,40}\bcalculated\b|\bresult of\b|\beffects? of\b|"
    r"\bsignificance\b|\bimportance\b|क्या है|मतलब|अर्थ|प्रभाव|फल\b|kya hai", re.I)
_PLANET_FIND = re.compile(rf"{_W}({PLANET_RE}){_E}", re.I)

_HOUSE_ORD = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6, "seventh": 7, "eighth": 8,
              "ninth": 9, "tenth": 10, "eleventh": 11, "twelfth": 12}


@dataclass(frozen=True)
class QuestionType:
    kind: str                       # general | personal | smalltalk
    subtype: str = "other"          # dasha_pair | dasha | yoga | planet_house | panchang | compat | sade_sati | remedy | transit | concept | other
    planets: tuple[str, ...] = ()   # canonical planets named in the question, in order, de-duplicated
    anchors: tuple[str, ...] = ()   # regex alternatives the first paragraph of a general answer must name
    anchor_all: bool = False        # True: every planet must be named (dasha pair)
    wants_tie: bool = False         # "... for me": one personal line is expected
    house: int | None = None
    md: str | None = None           # dasha pair: the Mahadasha lord asked about
    ad: str | None = None           # dasha pair: the Antardasha lord asked about

    @property
    def is_general(self) -> bool:
        return self.kind == "general"


def _planets(text: str) -> tuple[str, ...]:
    out: list[str] = []
    for m in _PLANET_FIND.finditer(text):
        p = canon_planet(m.group(1))
        # "Mars Mahadasha"-style; Moon/Sun counted too. Rahu/Ketu fine.
        if p and p not in out:
            out.append(p)
    return tuple(out)


_MD_RE = re.compile(rf"{_W}({PLANET_RE})\s*(?:ki\s+|ka\s+|की\s+|का\s+)?(?:maha\s*dasha|mahadasha|महादशा)", re.I)
_AD_RE = re.compile(rf"{_W}({PLANET_RE})\s*(?:ki\s+|ka\s+|की\s+|का\s+)?(?:antar\s*dasha|antardasha|bhukti|अंतर्दशा|भुक्ति)", re.I)


def _pair(q: str, planets: tuple[str, ...]) -> tuple[str | None, str | None]:
    """(Mahadasha lord, Antardasha lord) from "Mars mahadasha with Venus antardasha" / "Venus antardasha in Mars
    mahadasha" / "मंगल महादशा में शुक्र की अंतर्दशा". Falls back to order of appearance."""
    m, a = _MD_RE.search(q), _AD_RE.search(q)
    md = canon_planet(m.group(1)) if m else None
    ad = canon_planet(a.group(1)) if a else None
    if md and ad:
        return md, ad
    if len(planets) >= 2:
        return md or planets[0], ad or next((p for p in planets if p != (md or planets[0])), None)
    return md, ad


def _house(text: str) -> int | None:
    m = re.search(r"\b(\d{1,2})\s*(?:st|nd|rd|th)\b", text, re.I)
    if m and 1 <= int(m.group(1)) <= 12:
        return int(m.group(1))
    m = re.search(r"\b(first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|eleventh|twelfth)\b", text, re.I)
    if m:
        return _HOUSE_ORD[m.group(1).lower()]
    m = re.search(r"\b(?:house|bhava|bhav|ghar)\s+(?:no\.?\s*)?(\d{1,2})\b|\b(\d{1,2})\s*(?:ghar|bhav|भाव|घर)", text, re.I)
    if m:
        n = int(m.group(1) or m.group(2))
        return n if 1 <= n <= 12 else None
    return None


def _subtype(q: str, planets: tuple[str, ...]) -> tuple[str, tuple[str, ...], bool]:
    """-> (subtype, anchor regexes, anchor_all)"""
    has_dasha = bool(_DASHA_RE.search(q))
    planet_anchors = tuple(rf"\b{re.escape(p)}\b|{re.escape(p)}" for p in planets)
    if _SADESATI_RE.search(q):
        return "sade_sati", (_SADESATI_RE.pattern,), False
    if has_dasha and len(planets) >= 2:
        return "dasha_pair", tuple(_planet_pattern(p) for p in planets[:2]), True
    if has_dasha and planets:
        return "dasha", (_planet_pattern(planets[0]),), False
    if _PANCHANG_RE.search(q):
        return "panchang", (_PANCHANG_RE.pattern,), False
    if _COMPAT_RE.search(q):
        return "compat", (_COMPAT_RE.pattern + r"|marriage|compatible|कुंडली|विवाह", ), False
    if _YOGA_RE.search(q):
        return "yoga", (_YOGA_RE.pattern,), False
    if planets and (_HOUSE_RE.search(q) or _house(q)):
        return "planet_house", tuple(_planet_pattern(p) for p in planets[:1]), False
    if _REMEDY_RE.search(q) and planets:
        return "remedy", tuple(_planet_pattern(p) for p in planets[:1]), False
    if _REMEDY_RE.search(q):
        return "remedy", (_REMEDY_RE.pattern,), False
    if _TRANSIT_RE.search(q):
        return "transit", (_TRANSIT_RE.pattern,) + (tuple(_planet_pattern(p) for p in planets[:1])), False
    if planets:
        return "concept", tuple(_planet_pattern(p) for p in planets[:1]), False
    return "other", (), False


_STOP = frozenset((
    "what", "whats", "does", "mean", "means", "meaning", "explain", "define", "tell", "about", "which", "while", "that",
    "this", "with", "from", "your", "have", "used", "uses", "work", "works", "when", "where", "there", "their", "they",
    "kya", "hai", "hota", "hoti", "hote", "hain", "matlab", "batao", "bataiye", "samjhao", "detail", "detailed",
    "ke", "ka", "ki", "mein", "isme", "kaise", "kitna", "chart", "usually", "bring", "brings", "good", "bad", "should",
    "would", "could", "also", "much", "many", "more", "most", "some", "into", "than", "then", "them", "being", "been",
    "astrology", "astrological", "vedic", "western", "please", "thing", "things", "important", "importance",
))


def _content_tokens(q: str) -> list[str]:
    """Significant words of a concept question (Latin >= 4 letters, or Devanagari words >= 3 chars)."""
    out: list[str] = []
    for w in re.findall(r"[A-Za-z]{4,}|[\u0900-\u097F]{3,}", q):
        lw = w.lower()
        if lw in _STOP or lw in out:
            continue
        out.append(lw)
    return out


def _planet_pattern(canonical: str) -> str:
    """Regex matching a planet by any of its names (English, Sanskrit, Hindi)."""
    from app.llm.lexicon import PLANET_ALIASES

    names = [canonical, *PLANET_ALIASES.get(canonical, ())]
    return "|".join(re.escape(n) for n in sorted(set(names), key=len, reverse=True))


def classify_question(question: str) -> QuestionType:
    q = (question or "").strip()
    if not q or is_small_talk(q):
        return QuestionType("smalltalk")
    planets = _planets(q)
    q_wo_forme = _STRIP_FOR_ME.sub(" ", q)
    wants_tie = bool(_FOR_ME.search(q))
    strong_personal = bool(_PERSONAL.search(q_wo_forme))
    subtype, anchors, anchor_all = _subtype(q, planets)
    md, ad = _pair(q, planets) if subtype == "dasha_pair" else (None, None)
    concept_shaped = bool(_CONCEPT_LEAD.search(q) or _CONCEPT_ANY.search(q))
    asks_current = bool(re.search(
        r"\b(?:currently|right now|am i in|these days|abhi|ab kal|aajkal|filhaal)\b|इस समय|अभी|आजकल|फिलहाल", q, re.I))
    if subtype == "other":
        toks = _content_tokens(q)
        if concept_shaped and toks and not strong_personal and not asks_current:
            return QuestionType("general", "concept", planets, tuple(re.escape(t) for t in toks[:4]), False, wants_tie)
        return QuestionType("personal", "other", planets, (), False, False)
    if strong_personal or (asks_current and subtype != "panchang"):      # "Rahu Kaal right now" is about the sky, not the chart
        return QuestionType("personal", subtype, planets, anchors, anchor_all, False, _house(q), md, ad)
    # No chart-specific marker: a named concept is a general question. Without a concept-shaped phrasing but with a
    # named subtype (e.g. "Rahu Kaal today?"), still general: the chart is rarely what answers it.
    return QuestionType("general", subtype, planets, anchors, anchor_all, wants_tie, _house(q), md, ad)


# Concepts that rarely connect to a single natal placement: no closing chart line unless the user asked "... for me".
_NO_TIE_SUBTYPES = frozenset(("panchang", "compat", "concept", "remedy", "transit"))


def question_kind_for_prompt(qt: QuestionType) -> str:
    """The ANSWER SHAPE mode the prompt renders: general | general_tie | general_notie | personal | smalltalk."""
    if qt.kind == "general":
        if qt.wants_tie:
            return "general_tie"
        return "general_notie" if qt.subtype in _NO_TIE_SUBTYPES else "general"
    return qt.kind


_HOUSE_WORD = {1: "1st", 2: "2nd", 3: "3rd"}


def focus_line(qt: QuestionType) -> str | None:
    """A one-line QUESTION FOCUS block for general questions, so a small model keeps answering the asked concept and not
    the user's own current period (BUG-025). Deterministic; no model call."""
    if qt.kind != "general":
        return None
    if qt.subtype == "dasha_pair" and qt.md and qt.ad:
        what = f"the {qt.md} Mahadasha with the {qt.ad} Antardasha"
    elif qt.subtype == "dasha" and qt.planets:
        what = f"the {qt.planets[0]} Mahadasha"
    elif qt.subtype == "planet_house" and qt.planets and qt.house:
        what = f"{qt.planets[0]} in the {_HOUSE_WORD.get(qt.house, str(qt.house) + 'th')} house"
    elif qt.subtype == "planet_house" and qt.planets:
        what = f"{qt.planets[0]} in a house"
    else:
        what = "the concept named in the question"
    return (f"QUESTION FOCUS: this is a general question about {what}. Answer about exactly that, for anyone, in the first "
            "sentence. The user's own current period or placements are a different matter: they may appear only in one "
            "short closing sentence, and only if listed in CHART FACTS and relevant.")


def order_notes(notes: list, qt: QuestionType) -> list:
    """Stable re-order: for a dasha pair, notes that contain the exact pair row ("Mars-Venus") come first."""
    if qt.subtype != "dasha_pair" or not (qt.md and qt.ad):
        return notes
    needle = f"{qt.md}-{qt.ad}".lower()
    return sorted(notes, key=lambda n: 0 if needle in str(getattr(n, "content", "")).lower() else 1)
