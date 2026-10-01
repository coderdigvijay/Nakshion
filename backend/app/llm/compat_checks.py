"""Compatibility narrative consistency: the numbers are the engine's, the tone must agree with them.

SINGLE THRESHOLD TABLE (overall score 0-10). It is the frontend's (`frontend/src/lib/compatBands.tsx::bandFor`);
`tests/llm/test_acceptance_d3_d6_d4.py` parses that file and fails if the two drift:

    >= 8.5  Exceptional      >= 6.5  Harmonious      >= 4.0  Workable      < 4.0  Challenging

Ashtakoota keeps the engine's own /36 verdict (>= 33 excellent, >= 25 good, >= 18 average, else below_average);
it is a separate scale and is never relabelled with the 0-10 band names.
"""

from __future__ import annotations

import re

BANDS: list[tuple[float, str]] = [(8.5, "Exceptional"), (6.5, "Harmonious"), (4.0, "Workable")]
LOWEST = "Challenging"

DOSHA_NAMES = {"bhakoot": ("bhakoot", "bhakut", "भकूट"), "gana": ("gana", "गण"), "nadi": ("nadi", "नाड़ी", "नाडी")}
# score rules mirror app/astrology/compatibility.py::guna_milan
_DOSHA_RULE = {"bhakoot": lambda s: s == 0, "nadi": lambda s: s == 0, "gana": lambda s: s <= 1.0}

_STRONG_POSITIVE = (r"perfect|ideal|seamless|effortless|soul\s?mates?|made for each other|excellent (?:match|compatibility)|"
                    r"highly compatible|very compatible|dynamic and balanced|harmonious|flawless|extremely compatible|"
                    r"(?:great|strong|wonderful|excellent|solid) (?:match|connection|bond|compatibility|pairing|partnership)|"
                    r"good overall|great overall|works? (?:very )?well together|thrive")
_TOO_POSITIVE_STRONG = re.compile(rf"\b(?:{_STRONG_POSITIVE})\b|आदर्श|परफेक्ट|बिल्कुल सही|उत्तम जोड़ी", re.I)
_TOO_NEGATIVE = re.compile(
    r"\b(incompatible|doomed|poor match|unlikely to work|not compatible|bad match|cannot work|won'?t work)\b|असंगत|बेमेल", re.I)
_HEDGE = re.compile(r"need|work|differen|care|effort|patience|friction|challeng|mixed|growth|attention|understand|"
                    r"चुनौती|मेहनत|धैर्य|अंतर|ध्यान", re.I)
_ASHTAKOOTA_WORDS = re.compile(r"ashtakoota|ashta koota|guna milan|gun milan|guna|अष्टकूट|गुण मिलान|गुण", re.I)


def band(overall: float | None) -> str:
    if overall is None:
        return "unknown"
    for threshold, label in BANDS:
        if overall >= threshold:
            return label
    return LOWEST


BAND_TEXT = {
    "Exceptional": "Exceptional: unusually supportive, with small growth areas",
    "Harmonious": "Harmonious: natural ease with a few areas that ask for care",
    "Workable": "Workable: real strengths beside real differences; understanding them is half the work. Not a smooth match",
    "Challenging": "Challenging: describe real friction and what the pair would need to work on",
    "unknown": "not scored",
}


def _verdict(total: float) -> str:
    if total >= 33:
        return "excellent"
    if total >= 25:
        return "good"
    if total >= 18:
        return "average"
    return "below_average"


def normalize_report(report: dict) -> dict:
    """Accept the engine's full compute_compatibility() dict OR the backend's reduced view (which carries only
    top-level `kootas`). Derives `ashtakoota` (total, verdict, dosha flags) from koota scores when it is absent, using
    the engine's own dosha rules, so the narrative can never lose the doshas."""
    if report.get("ashtakoota"):
        return report
    kootas = report.get("kootas") or []
    if not kootas:
        return report
    by = {str(k.get("name", "")).lower(): k.get("score") for k in kootas}
    ak: dict = {"total": round(sum(float(k.get("score") or 0) for k in kootas), 1), "kootas": kootas}
    ak["verdict"] = _verdict(ak["total"])
    for d, rule in _DOSHA_RULE.items():
        score = by.get(d)
        ak[f"{d}_dosha"] = bool(score is not None and rule(float(score)))
    return {**report, "ashtakoota": ak}


def flagged_doshas(report: dict) -> list[str]:
    ak = normalize_report(report).get("ashtakoota") or {}
    return [n for n in ("bhakoot", "gana", "nadi") if ak.get(f"{n}_dosha")]


def _mentions(text: str, dosha: str) -> bool:
    low = text.lower()
    return any(w in low for w in DOSHA_NAMES[dosha])


def consistency_problems(summary: str, others_text: str, report: dict, *, challenges_text: str | None = None) -> list[str]:
    """`challenges_text` is the needs-care list; when omitted `others_text` stands in for it."""
    report = normalize_report(report)
    probs: list[str] = []
    b = band(report.get("overall_score"))
    ak = report.get("ashtakoota") or {}
    if b in ("Challenging", "Workable") and _TOO_POSITIVE_STRONG.search(summary):
        probs.append(f"summary is too positive for the '{b}' band ({report.get('overall_score')}/10); describe what needs work")
    if b == "Workable" and not _HEDGE.search(summary):
        probs.append("a 'Workable' pairing must name the differences that need understanding")
    if b in ("Harmonious", "Exceptional") and _TOO_NEGATIVE.search(summary):
        probs.append(f"summary is too negative for the '{b}' band")
    needs_care = challenges_text if challenges_text is not None else others_text
    for d in flagged_doshas(report):
        if not _mentions(needs_care, d):
            probs.append(f"the {d.title()} dosha is flagged in REPORT FACTS; name it in the challenges (needs-care) list, "
                         "with traditional cancellations noted, not as doom")
    if ak.get("verdict") == "below_average" and not _ASHTAKOOTA_WORDS.search(f"{summary} {needs_care}"):
        probs.append("Ashtakoota is below average; mention the Ashtakoota / Guna Milan result")
    return probs


_ENUM_WORDS = {"below_average": "below average", "above_average": "above average", "average": "average",
               "excellent": "excellent", "good": "good"}
_SNAKE = re.compile(r"\b[a-z]+(?:_[a-z0-9]+)+\b")
_ALLCAPS = re.compile(r"\b[A-Z]{4,}\b")
_ACRONYMS = {"ASCII"}


def plain_words(text: str) -> str:
    """Engine enum/flag values must never reach prose: below_average -> below average, PRESENT -> present."""
    text = _SNAKE.sub(lambda m: _ENUM_WORDS.get(m.group(0), m.group(0).replace("_", " ")), text)
    return _ALLCAPS.sub(lambda m: m.group(0) if m.group(0) in _ACRONYMS else m.group(0).lower(), text)


def leaked_tokens(text: str) -> list[str]:
    return _SNAKE.findall(text) + [w for w in _ALLCAPS.findall(text) if w not in _ACRONYMS]
