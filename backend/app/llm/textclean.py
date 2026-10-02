"""Answer text hygiene: internal fact IDs never reach the user, and the reply language follows
the user (script detection is enough for Devanagari)."""

from __future__ import annotations

import re

_ID_INNER = re.compile(r"^(?:KB:[^\]]{1,120}|KB\d{1,2}|[A-Z][A-Z0-9_]{0,12}(?:\.[A-Z0-9_]+)+)$")
_ID_BRACKET = re.compile(r"\s?\[((?:KB:[^\]]{1,120})|(?:KB\d{1,2})|(?:[A-Z][A-Z0-9_]{0,12}(?:\.[A-Z0-9_]+)+))\]")
_MAX_HOLD = 140
_DEV = re.compile(r"[ऀ-ॿ]")
_LET = re.compile(r"[A-Za-zऀ-ॿ]")


# A bare ID typed into a sentence ("... your VN.MOON.RASHI.CANCER placement ...") is not a leak worth a canned reply:
# remove it (BUG-025: a repaired answer that named an ID was replaced by "I can't share how I'm set up").
_ID_BARE = re.compile(r"[ \t]?(?<![\w.\[/])(?:META|VN|V|N|A|T|G|Y|D|P|W)\.[A-Z][A-Z0-9_]*(?:\.[A-Z0-9_]+)+(?![\w.]*[a-z])")


def strip_fact_ids(text: str) -> tuple[str, list[str]]:
    """Remove "[N.SUN.SIGN.CANCER]"-style markers and bare IDs. Returns (clean_text, ids_found)."""
    found = [m.group(1) for m in _ID_BRACKET.finditer(text)]
    text = _ID_BRACKET.sub("", text)
    bare = [m.group(0).strip() for m in _ID_BARE.finditer(text)]
    if bare:
        found += bare
        text = re.sub(r"[ \t]{2,}", " ", _ID_BARE.sub("", text)).replace(" ,", ",").replace(" .", ".")
    return text, found


class BracketFilter:
    """Streaming version of strip_fact_ids: holds back from '[' until it closes (or is clearly
    not an ID), so markers split across chunks never leak."""

    def __init__(self) -> None:
        self._pending = ""
        self.found: list[str] = []

    def feed(self, text: str) -> str:
        data = self._pending + text
        self._pending = ""
        out: list[str] = []
        i = 0
        while i < len(data):
            j = data.find("[", i)
            if j < 0:
                out.append(data[i:])
                break
            out.append(data[i:j])
            k = data.find("]", j)
            if k < 0:
                tail = data[j:]
                if len(tail) > _MAX_HOLD:
                    out.append(tail)
                else:
                    joined = "".join(out)
                    stripped = joined.rstrip()
                    self._pending = joined[len(stripped):] + tail   # keep the space before '[' with it
                    return stripped
                break
            inner = data[j + 1:k]
            if _ID_INNER.match(inner):
                self.found.append(inner)
                if out and out[-1].endswith(" "):
                    out[-1] = out[-1][:-1]
            else:
                out.append(data[j:k + 1])
            i = k + 1
        joined = "".join(out)
        stripped = joined.rstrip()
        # hold trailing whitespace: it must vanish if the next chunk turns out to start an ID marker
        self._pending = joined[len(stripped):] + self._pending
        return stripped

    def flush(self) -> str:
        rest, self._pending = self._pending, ""
        return rest


def devanagari_ratio(text: str) -> float:
    letters = _LET.findall(text)
    return len(_DEV.findall(text)) / len(letters) if letters else 0.0


def effective_language(question: str, setting: str) -> str:
    """A Devanagari question is answered in Hindi even if the setting says English/Hinglish.
    Otherwise the user's language setting wins (a Roman Hindi question stays on the setting)."""
    if setting != "hindi" and devanagari_ratio(question) >= 0.5:
        return "hindi"
    return setting


# ----------------------------------------------------------------------------- reply style

_GREETING = re.compile(r"^\s*(?:नमस्ते|नमस्कार|हेलो|हैलो|हाय|namaste|namaskar|hello|hi|hey|dear user)(?![\w\u0900-\u0963\u0966-\u097F])[\s!,.\-–—]*", re.I)
_CONNECTOR = re.compile(
    r"^\s*(?:हालांकि|हालाँकि|लेकिन|परंतु|परन्तु|किंतु|और|तथा|अतः|इसलिए|साथ ही|however|but|although|though|moreover|"
    r"furthermore|also|and|so|yet|still|that said|having said that)(?![\w\u0900-\u0963\u0966-\u097F])[\s,;:\-–—]*", re.I)


def user_greeted(question: str) -> bool:
    return bool(_GREETING.match(question or ""))


def tidy_start(text: str, *, allow_greeting: bool) -> str:
    """Remove boilerplate greetings (unless the user greeted first) and orphaned leading connectors
    ("हालांकि, ..." with nothing before it). Capitalises the next letter for Latin script."""
    t = text.lstrip()
    for _ in range(3):
        before = t
        if not allow_greeting:
            t = _GREETING.sub("", t, count=1)
        t = _CONNECTOR.sub("", t, count=1)
        if t == before:
            break
    t = t.lstrip()
    return (t[:1].upper() + t[1:]) if t and t[0].isascii() and t[0].isalpha() else t


_DETAIL = re.compile(
    r"in detail|detailed|elaborate|explain (?:fully|thoroughly)|step by step|at length|in depth|"
    r"विस्तार|विस्तृत|विस्तारपूर्वक|पूरी जानकारी|गहराई से|vistar se|vistaar se|detail (?:mein|me)|detail se|poori jaankari",
    re.I)
_BRIEF = re.compile(
    r"briefly|in short|short answer|one line|in a nutshell|tl;?dr|संक्षेप|संक्षिप्त|सार में|कम शब्दों|sankshep|short mein|short me|"
    r"seedha batao|ek line",
    re.I)


def detail_level(question: str) -> str:
    """'detailed' | 'brief' | 'normal' from explicit user wording in English, Hindi or Hinglish."""
    if _DETAIL.search(question):
        return "detailed"
    if _BRIEF.search(question):
        return "brief"
    return "normal"


LENGTH_HINT_GENERAL = {"normal": "100 to 180 words in 2 to 4 short paragraphs", "detailed": "220 to 320 words, well organised",
                       "brief": "40 to 90 words, short and direct"}
LENGTH_HINT = {"normal": "120 to 220 words, concise", "detailed": "220 to 320 words, thorough and well organised",
               "brief": "40 to 90 words, short and direct"}

_FEM = re.compile(r"(?:सकती|चाहती|करती|रहती|पाती|लेती|देती|जाती|सोचती|मानती|रखती)\s*(?:हैं|हो|है)|"
                  r"\b(?:sakti|chahti|karti|rehti|paati|leti|deti|jaati)\s+(?:hain|ho|hai)\b", re.I)


def assumes_female(text: str) -> bool:
    """Feminine verb forms in an answer addressed to a user whose gender is unknown."""
    return bool(_FEM.search(text))


_FEM_FIX = {"सकती": "सकते", "चाहती": "चाहते", "करती": "करते", "रहती": "रहते", "पाती": "पाते", "लेती": "लेते",
            "देती": "देते", "जाती": "जाते", "सोचती": "सोचते", "मानती": "मानते", "रखती": "रखते",
            "sakti": "sakte", "chahti": "chahte", "karti": "karte", "rehti": "rehte", "paati": "paate", "leti": "lete",
            "deti": "dete", "jaati": "jaate"}
_FEM_PAT = re.compile(r"(" + "|".join(sorted(map(re.escape, _FEM_FIX), key=len, reverse=True)) + r")(\s+)(हैं|हो|hain|ho)(?![\w\u0900-\u0963\u0966-\u097F])")
_ADDRESS = re.compile(r"आप|aap", re.I)


def neutralize_gender(text: str) -> str:
    """Rewrite feminine honorific verb forms addressed to the user ("आप कर सकती हैं") to the conventional
    gender-neutral honorific ("आप कर सकते हैं"). Only plural/honorific forms in sentences that address the
    user, so feminine nouns (राशि ... करती है) are untouched."""
    # Keep the separators: paragraph breaks ("\n\n") must survive (chat@v7 asks for 2-3 short paragraphs).
    parts = re.split(r"((?<=[.!?।])\s+)", text)
    out = []
    for sent in parts:
        if _ADDRESS.search(sent):
            sent = _FEM_PAT.sub(lambda m: f"{_FEM_FIX[m.group(1)]}{m.group(2)}{m.group(3)}", sent)
        out.append(sent)
    return "".join(out)


# Common misspellings of dasha / nakshatra vocabulary (e.g. "अंतर्दृशा": दृश = "sight", not दशा) -> correct form.
_TERM_FIXES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"अं?न?्?तर्?दृशा|अन्तर्दृशा|अंतरदृशा|अन्तर्दशा|अंतरदशा"), "अंतर्दशा"),
    (re.compile(r"प्रत्यं?न्?तर्?दृशा|प्रत्यन्तर्दशा|प्रत्यंतरदशा"), "प्रत्यंतर्दशा"),
    (re.compile(r"महा\s?दृशा"), "महादशा"),
    (re.compile(r"नक्षेत्र|नक्शत्र|नछत्र"), "नक्षत्र"),
    (re.compile(r"विंशोतरी|विम्शोत्तरी|विंशोत्री|विंशौत्तरी"), "विंशोत्तरी"),
    (re.compile(r"\bmahadasa\b", re.I), "mahadasha"), (re.compile(r"\bantardasa\b", re.I), "antardasha"),
    (re.compile(r"\bnakshtra\b|\bnakshetra\b|\bnakshatara\b", re.I), "nakshatra"),
    (re.compile(r"\bvimshotari\b", re.I), "vimshottari"),
]


def fix_terms(text: str) -> str:
    """Deterministically correct known misspellings of core dasha/nakshatra terms (never touches other words)."""
    for pat, good in _TERM_FIXES:
        text = pat.sub(good, text)
    return text


_SMALL_TALK = re.compile(r"^\s*(?:hi|hello|hey|namaste|thanks?|thank you|ok(?:ay)?|good (?:morning|evening|night)|bye|dhanyavad|shukriya|"
                         r"नमस्ते|धन्यवाद|शुक्रिया)(?![\w\u0900-\u0963\u0966-\u097F])[\s!.,?।]*$", re.I)


def is_small_talk(question: str) -> bool:
    """Greetings / thanks: nothing to retrieve. Every other question gets retrieval (an astrology question need not
    contain a topic keyword: "Is my Bhakoot dosha cancelled?" has none)."""
    q = question.strip()
    return len(q) < 4 or bool(_SMALL_TALK.match(q))


_LEAKY = [(re.compile(r"\bCHART FACTS\b"), "your chart data"), (re.compile(r"\bREFERENCE NOTES?\b", re.I), "the reference material"),
          (re.compile(r"\bkb_note\b|\bKB\d+\b"), "the reference material")]


def deleak(text: str) -> str:
    """The model sometimes names our internal blocks while explaining what it lacks ("CHART FACTS does not include...").
    That is harmless wording, not a leak: rephrase it instead of discarding a good answer for a canned reply."""
    for pat, rep in _LEAKY:
        text = pat.sub(rep, text)
    return text
