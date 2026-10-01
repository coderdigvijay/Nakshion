"""Deterministic astrology vocabulary shared by the LLM validators and the RAG indexer.

This module holds *names only* (no calculation). It is used to:
- detect topic and timeframe of a user question (llm-integration.md §3 [2]),
- find placement claims in model output (the claim checker, §3 [7]),
- tag knowledge-base chunks with entities and topics (§6.2).

NOTE: the canonical sign/body/nakshatra tables belong to the astrology engine
(`app/astrology/`, owned by astrology-domain-expert). Once that package exposes them,
replace the literal tables below with imports so there is one source of truth.
"""

from __future__ import annotations

import re
from typing import Literal

Topic = Literal[
    "self", "love", "career", "money", "health", "family", "spiritual", "timing", "compatibility", "general"
]
Timeframe = Literal["today", "this_week", "this_month", "this_year", "next_year", "specific_date", "life"]

# --- Bodies -------------------------------------------------------------------------------

# canonical English name -> aliases (lowercase). Vedic and Hindi names map to the same planet.
PLANET_ALIASES: dict[str, tuple[str, ...]] = {
    "Sun": ("sun", "surya", "सूर्य", "सूरज"),
    "Moon": ("moon", "chandra", "चंद्र", "चन्द्र", "चंद्रमा", "चन्द्रमा"),
    "Mercury": ("mercury", "budha", "budh", "बुध"),
    "Venus": ("venus", "shukra", "shukr", "शुक्र"),
    "Mars": ("mars", "mangala", "mangal", "मंगल"),
    "Jupiter": ("jupiter", "guru", "brihaspati", "गुरु", "बृहस्पति"),
    "Saturn": ("saturn", "shani", "शनि"),
    "Uranus": ("uranus",),
    "Neptune": ("neptune",),
    "Pluto": ("pluto",),
    "Rahu": ("rahu", "north node", "राहु"),
    "Ketu": ("ketu", "south node", "केतु"),
}

# --- Signs --------------------------------------------------------------------------------

SIGNS: tuple[str, ...] = (
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
)

# canonical English sign -> aliases. Rashi names are sidereal by convention.
SIGN_ALIASES: dict[str, tuple[str, ...]] = {
    "Aries": ("aries", "mesha", "mesh", "मेष"),
    "Taurus": ("taurus", "vrishabha", "vrishabh", "वृषभ"),
    "Gemini": ("gemini", "mithuna", "mithun", "मिथुन"),
    "Cancer": ("cancer", "karka", "kark", "कर्क"),
    "Leo": ("leo", "simha", "singh", "सिंह"),
    "Virgo": ("virgo", "kanya", "कन्या"),
    "Libra": ("libra", "tula", "तुला"),
    "Scorpio": ("scorpio", "vrishchika", "vrishchik", "वृश्चिक"),
    "Sagittarius": ("sagittarius", "dhanu", "dhanus", "धनु"),
    "Capricorn": ("capricorn", "makara", "makar", "मकर"),
    "Aquarius": ("aquarius", "kumbha", "kumbh", "कुंभ", "कुम्भ"),
    "Pisces": ("pisces", "meena", "meen", "मीन"),
}

NAKSHATRAS: tuple[str, ...] = (
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra", "Punarvasu", "Pushya",
    "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra", "Swati",
    "Vishakha", "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana",
    "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati",
)

ASPECT_ALIASES: dict[str, tuple[str, ...]] = {
    "conjunction": ("conjunct", "conjunction", "conjoins", "conjoined with", "conj"),
    "opposition": ("opposite", "opposition", "opposes", "opposing"),
    "square": ("square", "squares", "squaring"),
    "trine": ("trine", "trines", "trining"),
    "sextile": ("sextile", "sextiles"),
}

HOUSE_WORDS = ("house", "bhava", "भाव", "घर")

ORDINALS: dict[str, int] = {
    "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6, "seventh": 7,
    "eighth": 8, "ninth": 9, "tenth": 10, "eleventh": 11, "twelfth": 12,
}

MONTHS = (
    "january", "february", "march", "april", "may", "june", "july", "august",
    "september", "october", "november", "december",
)

# --- Reverse lookup helpers ---------------------------------------------------------------


def _reverse(table: dict[str, tuple[str, ...]]) -> dict[str, str]:
    out: dict[str, str] = {}
    for canon, aliases in table.items():
        for a in aliases:
            out[a.lower()] = canon
    return out


PLANET_LOOKUP = _reverse(PLANET_ALIASES)
SIGN_LOOKUP = _reverse(SIGN_ALIASES)
ASPECT_LOOKUP = _reverse(ASPECT_ALIASES)
NAKSHATRA_LOOKUP = {n.lower(): n for n in NAKSHATRAS}


def alternation(words: list[str] | tuple[str, ...]) -> str:
    """Regex alternation, longest first so 'north node' wins over 'north'."""
    return "|".join(re.escape(w) for w in sorted(words, key=len, reverse=True))


PLANET_RE = alternation(list(PLANET_LOOKUP))
SIGN_RE = alternation(list(SIGN_LOOKUP))
ASPECT_RE = alternation(list(ASPECT_LOOKUP))
NAKSHATRA_RE = alternation(list(NAKSHATRA_LOOKUP))


def canon_planet(word: str) -> str | None:
    return PLANET_LOOKUP.get(word.lower().strip())


def canon_sign(word: str) -> str | None:
    return SIGN_LOOKUP.get(word.lower().strip())


# --- Topic and timeframe (deterministic, §3 [2]) ------------------------------------------

TOPIC_KEYWORDS: dict[str, tuple[str, ...]] = {
    "love": ("love", "relationship", "partner", "marriage", "marry", "boyfriend", "girlfriend",
             "husband", "wife", "romance", "dating", "crush", "shaadi", "pyaar", "pyar", "प्यार",
             "शादी", "विवाह", "रिश्ता"),
    "career": ("career", "job", "work", "promotion", "boss", "business", "profession", "office",
               "naukri", "kaam", "नौकरी", "करियर", "व्यापार"),
    "money": ("money", "finance", "financial", "wealth", "income", "salary", "debt", "invest",
              "paisa", "paise", "dhan", "पैसा", "धन"),
    "health": ("health", "illness", "sick", "disease", "energy", "wellness", "stress", "sleep",
               "sehat", "स्वास्थ्य", "सेहत"),
    "family": ("family", "mother", "father", "parent", "sibling", "brother", "sister", "child",
               "children", "home", "ghar", "parivar", "परिवार", "माँ", "पिता"),
    "spiritual": ("spiritual", "meditation", "karma", "dharma", "purpose", "soul", "moksha",
                  "आध्यात्म", "धर्म"),
    "compatibility": ("compatible", "compatibility", "synastry", "match", "guna", "kundli milan",
                      "milan"),
    "timing": ("when will", "dasha", "transit", "period", "timing", "kab", "कब", "महादशा", "दशा"),
    "self": ("personality", "who am i", "my nature", "strengths", "weakness", "myself",
             "swabhav", "स्वभाव"),
}

_TIMEFRAME_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("today", re.compile(r"\b(today|tonight|aaj)\b|आज", re.I)),
    ("this_week", re.compile(r"\b(this week|is hafte|iss hafte)\b|इस हफ्ते|इस सप्ताह", re.I)),
    ("this_month", re.compile(r"\b(this month|is mahine|iss mahine)\b|इस महीने", re.I)),
    ("next_year", re.compile(r"\b(next year|agle saal|agle varsh)\b|अगले साल|अगले वर्ष", re.I)),
    ("this_year", re.compile(r"\b(this year|is saal|iss saal)\b|इस साल|इस वर्ष", re.I)),
    ("specific_date", re.compile(
        r"\b(19|20)\d{2}\b|\b\d{4}-\d{2}-\d{2}\b|\b(" + "|".join(MONTHS) + r")\b", re.I)),
]


def detect_topic(text: str) -> Topic:
    """Highest keyword-hit topic, 'general' when nothing matches."""
    low = text.lower()
    best: tuple[int, str] = (0, "general")
    for topic, words in TOPIC_KEYWORDS.items():
        hits = sum(1 for w in words if w in low)
        if hits > best[0]:
            best = (hits, topic)
    return best[1]  # type: ignore[return-value]


def detect_timeframe(text: str) -> Timeframe:
    for name, pat in _TIMEFRAME_PATTERNS:
        if pat.search(text):
            return name  # type: ignore[return-value]
    return "life"


def detect_entities(text: str) -> list[str]:
    """Entities used as KB chunk tags: planet:/sign:/nakshatra:/aspect:/house: prefixes."""
    low = text.lower()
    found: set[str] = set()
    for m in re.finditer(rf"(?<![\w]){PLANET_RE}(?![\w])", low):
        found.add(f"planet:{canon_planet(m.group(0))}")
    for m in re.finditer(rf"(?<![\w]){SIGN_RE}(?![\w])", low):
        found.add(f"sign:{canon_sign(m.group(0))}")
    for m in re.finditer(rf"(?<![\w]){NAKSHATRA_RE}(?![\w])", low):
        found.add(f"nakshatra:{NAKSHATRA_LOOKUP[m.group(0)]}")
    for m in re.finditer(rf"(?<![\w]){ASPECT_RE}(?![\w])", low):
        found.add(f"aspect:{ASPECT_LOOKUP[m.group(0)]}")
    for m in re.finditer(r"\b(\d{1,2})(?:st|nd|rd|th)\s+house\b", low):
        n = int(m.group(1))
        if 1 <= n <= 12:
            found.add(f"house:{n}")
    return sorted(found)


def detect_topics(text: str) -> list[str]:
    low = text.lower()
    return sorted(t for t, words in TOPIC_KEYWORDS.items() if any(w in low for w in words))
