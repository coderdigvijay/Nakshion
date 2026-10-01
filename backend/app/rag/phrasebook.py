"""Hinglish phrase -> concept expansion, driven by knowledge_base/kb_lang_hinglish_phrasebook.md.

The phrasebook's tables map how users actually type ("meri shaadi kab hogi") to the concepts to retrieve ("7th house,
7th lord, Venus, Jupiter transit, dasha, navamsha"). We parse it once and, when a question covers most of a phrase's
words, add that row's concept keywords to the query plan. Spelling variants listed in the file (shaadi/shadi/vivah,
kundli/kundali, sade sati/sadhesati) are folded to one form first. Data stays in the KB: add a row, get the behaviour.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from app.rag.glossary import gloss_terms, norm

PATH = Path(__file__).resolve().parents[2] / "knowledge_base" / "kb_lang_hinglish_phrasebook.md"
_FILLER = set("""kya hai hain ho hoga hogi hoon mera meri mere mein me ka ki ke ko se par aur ya kab kaise kaun kaunsa kyun kyu
kitna kitne karun karu karna kare karein hona ban bana hota hoti toh to bhi hi nahi na ek koi""".split())
_TOKEN = re.compile(r"[ऀ-ॿ]+|[a-z0-9]+")


def _tokens(text: str, variants: dict[str, str], keep_filler: bool = False) -> list[str]:
    out = []
    for t in _TOKEN.findall(norm(text)):
        t = variants.get(t, t)
        if len(t) > 1 and (keep_filler or t not in _FILLER):
            out.append(t)
    return out


@lru_cache(maxsize=1)
def _load() -> tuple[dict[str, str], list[tuple[frozenset[str], frozenset[str], str]]]:
    if not PATH.exists():
        return {}, []
    text = PATH.read_text(encoding="utf-8")
    variants: dict[str, str] = {}
    m = re.search(r"Spelling variants to normalise:(.*?)\n\n", text, re.S)
    if m:
        for group in m.group(1).split(";"):
            forms = [norm(x).strip(" .\n") for x in group.split("/") if x.strip(" .\n")]
            for f in forms[1:]:
                for part in f.split():
                    variants[part] = forms[0].split()[0] if " " in forms[0] else forms[0]
    rows: list[tuple[frozenset[str], frozenset[str], str]] = []
    for line in text.splitlines():
        if not line.startswith("|") or set(line) <= set("|-: "):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3 or cells[0].lower().startswith("hinglish phrase"):
            continue
        content = frozenset(_tokens(cells[0], variants))
        full = frozenset(_tokens(cells[0], variants, keep_filler=True))
        if content:
            rows.append((full, content, cells[2]))
    return variants, rows


def expand(question: str, *, min_cover: float = 0.6, max_rows: int = 2, max_terms: int = 14) -> list[str]:
    """English concept keywords for the best-matching phrasebook rows (empty when nothing matches well)."""
    variants, rows = _load()
    if not rows:
        return []
    q = set(_tokens(question, variants, keep_filler=True))
    qc = set(_tokens(question, variants))
    if not qc:
        return []
    scored = []
    for full, content, concepts in rows:
        hit_c = len(content & qc)
        cover = len(full & q) / len(full)                  # fillers count toward coverage, never toward the match itself
        if hit_c >= 1 and cover >= min_cover and hit_c / len(content) >= 0.6:
            scored.append((cover, hit_c, concepts))
    scored.sort(key=lambda t: (t[0], t[1]), reverse=True)
    out: list[str] = []
    for _, _, concepts in scored[:max_rows]:
        concepts = re.sub(r"\"[^\"]*\"", " ", concepts)               # drop quoted example phrases
        for w in gloss_terms(concepts.replace(";", " ").replace("/", " ")):
            if w not in out:
                out.append(w)
    return out[:max_terms]
