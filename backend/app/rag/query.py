"""Query planning: turn (question, language, factor kb_keys) into the set of searches to run.

The legacy design embedded every factor key and the question and fused them with EQUAL weight, so
a chart's six top factors drowned the user's actual question (measured: hit@5 0.21). Here the
question leads, glossed into KB vocabulary for Hindi/Hinglish, and factor keys only contribute when
they relate to what was asked.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.llm.lexicon import detect_entities, detect_topic
from app.rag import phrasebook
from app.rag.glossary import _STOP, gloss_terms, norm

_DEV = re.compile(r"[ऀ-ॿ]")
GENERIC = {"house", "planet", "chart", "birth", "zodiac", "sign", "effects", "influence", "nature", "period",
           "timing", "horoscope", "qualities", "body", "daily", "difference", "comparison", "represent", "signify",
           "astrology", "caution", "handle", "love", "relationship", "career", "profession", "money", "finances",
           "health", "weak", "afflicted", "personality", "traits", "emotional", "emotions"}
_STOP_EN = {"what", "does", "do", "is", "are", "the", "a", "an", "of", "in", "my", "me", "i", "how", "and", "or", "to",
            "for", "with", "on", "it", "this", "that", "mean", "means", "tell", "about", "should", "will", "can",
            "which", "who", "when", "where", "why", "your", "you", "be", "by", "as", "at", "from", "so", "if"}


def is_non_english(text: str, language: str) -> bool:
    return language in ("hindi", "hinglish") or bool(_DEV.search(text))


_ORD_DIGIT = {w: f"{i}{'st' if i == 1 else 'nd' if i == 2 else 'rd' if i == 3 else 'th'}" for i, w in enumerate(
    ("first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth", "eleventh", "twelfth"), 1)}
_DEFINITION = re.compile(r"\b(?:mean|means|meaning|matlab|called|naam|define|definition|kehte|kehlate)\b|मतलब|अर्थ|कहते|नाम|यानी|yaani", re.I)


@dataclass
class QueryPlan:
    question: str
    language: str
    terms: list[str]                       # English search terms (gloss + English words)
    head_terms: list[str]                  # distinctive terms to look for in headings
    topic: str
    lord_of: str = ""                      # '7th' in '7th lord in the 12th house': the house whose lord is asked about
    is_definition: bool = False            # 'what does X mean / X ka matlab': glossary-style chunks are the best home
    keys_used: list[str] = field(default_factory=list)
    keys_dropped: list[str] = field(default_factory=list)
    vector_texts: list[tuple[str, str, float]] = field(default_factory=list)   # (label, text, weight)
    fts: list[tuple[str, str, float]] = field(default_factory=list)            # (label, "a | b", weight)

    @property
    def query_en(self) -> str:
        return " ".join(self.terms)


def _words(s: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", s.lower())


def select_keys(kb_keys: list[str], terms: set[str], policy: str, max_keys: int) -> tuple[list[str], list[str]]:
    keys = list(dict.fromkeys(k.strip().lower() for k in kb_keys if k and k.strip()))
    if policy == "none":
        return [], keys
    if policy == "all":
        return keys[:max_keys], keys[max_keys:]
    # 'matched': a factor key helps only if it shares a distinctive word with the question
    used = [k for k in keys if (set(_words(k)) - GENERIC - _STOP_EN) & terms]
    if not used and len(terms - GENERIC - _STOP_EN) == 0:
        used = keys[:2]            # an open question ("tell me about my chart"): lean on the top factors
    used = used[:max_keys]
    return used, [k for k in keys if k not in used]


def build_plan(question: str, language: str, kb_keys: list[str], *, multilingual: bool, cfg) -> QueryPlan:
    q = question.strip()
    non_en = is_non_english(q, language)
    terms = gloss_terms(q, phonetic=cfg.phonetic) if cfg.use_gloss else [w for w in _words(q) if w not in _STOP_EN]
    ent_names = {e.split(":", 1)[1].lower() for e in detect_entities(" ".join(terms) + " " + q)}
    if non_en and cfg.use_gloss and getattr(cfg, "phrasebook", True):
        for w in phrasebook.expand(q):                    # how users phrase it -> the concepts to retrieve
            if w not in terms:
                terms.append(w)
    for e in ent_names:
        for w in _words(e):
            if w not in terms:
                terms.append(w)
    term_set = set(terms)
    head = [t for t in terms if t not in GENERIC and t not in _STOP_EN and len(t) > 2][:6]
    topic = detect_topic(" ".join(terms) + " " + q)
    used, dropped = select_keys(kb_keys, term_set, cfg.key_policy, cfg.max_keys)
    ords = [t for t in terms if re.fullmatch(r"\d{1,2}(?:st|nd|rd|th)", t)]
    ords = ords or [_ORD_DIGIT[t] for t in terms if t in _ORD_DIGIT]
    lord_of = ords[0] if "lord" in terms and len(ords) >= 2 else ""
    plan = QueryPlan(q, language, terms, head, topic, lord_of, bool(_DEFINITION.search(q)), used, dropped)
    # ---- vector queries
    if cfg.use_question and q:
        if non_en and not multilingual:
            if terms and cfg.use_gloss:
                plan.vector_texts.append(("g", " ".join(terms), cfg.q_weight))      # English-only model: gloss only
        else:
            plan.vector_texts.append(("q", q, cfg.q_weight))
            if non_en and terms and cfg.use_gloss and cfg.gloss_weight > 0:
                plan.vector_texts.append(("g", " ".join(terms), cfg.gloss_weight))
    # ---- full-text
    if cfg.fts and terms:
        # Devanagari words are searchable too: the glossary / core-topic files carry Hindi text verbatim
        dev = [t for t in re.findall(r"[\u0900-\u097F]+", norm(q)) if t not in _STOP and len(t) > 2][:6]
        for t in list(dev):                                  # no Devanagari stemmer in Postgres: add suffix-stripped forms
            for suf in ("ों", "ें", "ओं", "ाओं", "ियों"):
                if t.endswith(suf) and len(t) - len(suf) > 1:
                    dev.append(t[: -len(suf)])
        plan.fts.append(("f:t", " | ".join(terms + dev), cfg.fts_weight))
        if head and cfg.fts_head_weight > 0:
            plan.fts.append(("f:h", " | ".join(head), cfg.fts_head_weight))   # the distinctive terms alone (e.g. "yogini")
    if cfg.fts and used and cfg.fts_key_weight > 0:
        plan.fts.append(("f:k", " | ".join(w for k in used for w in _words(k)), cfg.fts_key_weight))
    return plan


def normalize_question(q: str) -> str:
    return " ".join(norm(q).split())
