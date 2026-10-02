"""Phonetic bridge for Devanagari loanwords and names that are not in the glossary.

Hindi writes English/Sanskrit astrology terms by sound: काइरॉन (Chiron), स्टेलियम (stellium), अष्टकवर्ग
(ashtakavarga). Transliterate to Roman, reduce both sides to a consonant skeleton, and match against the
knowledge-base vocabulary (heading words + lexicon names) within a small edit distance. No hand list:
generalises to words nobody listed. Precision guards: skeleton >= 3 consonants, unique best match, never
applied to stopwords or glossary hits.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

_IND = {
    "अ": "a", "आ": "a", "इ": "i", "ई": "i", "उ": "u", "ऊ": "u", "ऋ": "ri", "ए": "e", "ऐ": "e", "ओ": "o", "औ": "o",
    "ऑ": "o", "ऍ": "e",
    "ा": "a", "ि": "i", "ी": "i", "ु": "u", "ू": "u", "ृ": "ri", "े": "e", "ै": "e", "ो": "o", "ौ": "o", "ॉ": "o", "ॅ": "e",
    "क": "k", "ख": "k", "ग": "g", "घ": "g", "ङ": "n", "च": "k", "छ": "k", "ज": "j", "झ": "j", "ञ": "n", "ट": "t",
    "ठ": "t", "ड": "d", "ढ": "d", "ण": "n", "त": "t", "थ": "t", "द": "d", "ध": "d", "न": "n", "प": "p", "फ": "f",
    "ब": "b", "भ": "b", "म": "m", "य": "y", "र": "r", "ल": "l", "व": "v", "श": "s", "ष": "s", "स": "s", "ह": "h",
    "ं": "n", "ँ": "n", "ः": "h", "़": "",
}
_NUKTA_Z = {"ज": "s", "फ": "f", "ड": "r", "ढ": "r"}   # ज़ (z) -> s; फ़ -> f; ड़ ढ़ -> r
_VIRAMA = "्"
_CONS = set("कखगघङचछजझञटठडढणतथदधनपफबभमयरलवशषसह")
_MATRAS = set("ािीुूृेैोौॉॅ")


def translit(word: str) -> str:
    """Devanagari -> rough Roman (consonant skeleton quality; vowels are not trusted)."""
    out: list[str] = []
    chars = list(word)
    for i, ch in enumerate(chars):
        if ch == _VIRAMA:
            continue
        nxt = chars[i + 1] if i + 1 < len(chars) else ""
        out.append(_NUKTA_Z[ch] if (ch in _NUKTA_Z and nxt == "़") else _IND.get(ch, ""))
        if ch in _CONS and nxt not in _MATRAS and nxt != _VIRAMA and nxt not in ("ं", "ँ", "ः", "़"):
            out.append("a")  # inherent vowel (skeleton drops it anyway)
    return "".join(out)


_DIG = [("ph", "f"), ("sh", "s"), ("ch", "k"), ("th", "t"), ("dh", "d"), ("kh", "k"), ("gh", "g"), ("ck", "k"),
        ("ps", "s"), ("x", "ks"), ("c", "k"), ("q", "k"), ("w", "v"), ("z", "s")]


def skeleton(roman: str) -> str:
    s = roman.lower()
    s = re.sub(r"(?:t|s)ion", "shn", s)
    for a, b in _DIG:
        s = s.replace(a, b)
    s = re.sub(r"[aeiouy]", "", s)
    s = re.sub(r"(.)\1+", r"\1", s)
    return s


def _lev(a: str, b: str, cap: int) -> int:
    if abs(len(a) - len(b)) > cap:
        return cap + 1
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


_FREQ: dict[str, int] = {}


@lru_cache(maxsize=1)
def vocabulary() -> dict[str, list[str]]:
    """skeleton -> English KB words, from knowledge_base headings + lexicon names."""
    from app.llm.lexicon import NAKSHATRAS, PLANET_ALIASES, SIGNS

    words: dict[str, int] = {}
    kb = Path(__file__).resolve().parents[2] / "knowledge_base"
    for p in kb.glob("*.md"):
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.startswith("#"):
                for w in re.findall(r"[a-z]{4,}", line.lower()):
                    words[w] = words.get(w, 0) + 1
    names = [x.lower() for n in NAKSHATRAS for x in re.findall(r"[a-z]{3,}", n.lower())]
    names += [k.lower() for k in PLANET_ALIASES] + [s.lower() for s in SIGNS]
    for w in names:
        words[w] = words.get(w, 0) + 3
    for w in ("overview", "guide", "section", "system", "systems", "practical", "common", "basic", "about", "other"):
        words.pop(w, None)
    sk: dict[str, list[str]] = {}
    for w, _ in sorted(words.items(), key=lambda kv: (-kv[1], kv[0])):   # most frequent first
        s = skeleton(w)
        if len(s) >= 3:
            sk.setdefault(s, []).append(w)
    _FREQ.update(words)
    return sk


def match_all(devanagari_token: str, max_candidates: int = 2) -> list[str]:
    """KB words that sound like the token. Exact consonant-skeleton matches only (or a unique one-edit match for
    skeletons of 6+ consonants). An ambiguous skeleton returns its few most frequent words: both go into an OR
    full-text query, so a wrong guess costs a little noise and a right one is kept."""
    sk = skeleton(translit(devanagari_token))
    if len(sk) < 3:
        return []
    vocab = vocabulary()
    if sk in vocab:
        ws = vocab[sk]
        return ws[:max_candidates] if len(ws) <= 4 else []
    if len(sk) < 6:
        return []
    found = [ws[0] for s2, ws in vocab.items() if _lev(sk, s2, 1) <= 1 and len(vocab[s2]) == 1]
    return found[:1] if len(found) == 1 else []


def match(devanagari_token: str) -> str | None:
    """Single best KB word, or None when the sound is ambiguous (see match_all)."""
    ws = match_all(devanagari_token)
    return ws[0] if len(ws) == 1 else None


def match_roman_all(token: str, max_candidates: int = 2) -> list[str]:
    """Roman-Hindi spelling variants of KB words ("uttra bhadrapad" -> uttara bhadrapada, "sani" -> shani): same consonant
    skeleton as a KB word, exact or a unique one-edit match for 6+ consonants. Tokens already known to the KB vocabulary
    are not touched by the caller."""
    sk = skeleton(token)
    if len(sk) < 3:
        return []
    vocab = vocabulary()
    if sk in vocab:
        ws = vocab[sk]
        return ws[:max_candidates] if len(ws) <= 3 else []
    return []
