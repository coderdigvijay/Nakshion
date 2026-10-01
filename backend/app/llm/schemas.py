"""Structured-output contracts. Pydantic is the validator of record (ai_llm_rules §4).

Providers receive a *relaxed* JSON Schema (`provider_schema`): length/count/numeric bounds
are stripped because vendor structured-output engines support them inconsistently. The
full bounds are enforced client-side by Pydantic, so a model that ignores a bound is caught.
Scores are never part of an LLM schema: the engine computes them.
"""

from __future__ import annotations

import copy
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

_STRIP = {"maxLength", "minLength", "maxItems", "minItems", "minimum", "maximum",
          "exclusiveMinimum", "exclusiveMaximum", "pattern", "format", "title", "default"}


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


def cut_words(text: str, limit: int) -> str:
    """Truncate at a word boundary (adds an ellipsis only when something was cut)."""
    text = text.strip()
    if len(text) <= limit:
        return text
    cut = text[: limit - 1].rsplit(" ", 1)[0].rstrip(" ,;:-") or text[: limit - 1]
    return cut + "\u2026"


def cut_sentences(text: str, limit: int) -> str:
    """Truncate an over-long answer at the last sentence end that fits."""
    text = text.strip()
    if len(text) <= limit:
        return text
    head = text[:limit]
    m = max(head.rfind(". "), head.rfind("! "), head.rfind("? "), head.rfind("\u0964 "))
    return head[: m + 1].strip() if m > limit * 0.5 else cut_words(text, limit)


def _soft_list(v, n: int, item_max: int | None = None):
    """Soft list field: keep the first n usable string items, truncate items at a word boundary."""
    if not isinstance(v, list):
        return v
    out = [x for x in v if isinstance(x, str) and x.strip()]
    if item_max:
        out = [cut_words(x, item_max) for x in out]
    return out[:n]


FollowUp = Annotated[str, Field(max_length=90)]


class _SoftChat(_Strict):
    """Length caps on soft fields never fail a whole answer: they are normalised, not rejected.
    Hard failures remain: empty answer, missing/ill-typed required fields, unknown keys."""

    @field_validator("citations", mode="before", check_fields=False)
    @classmethod
    def _cites(cls, v):
        return _soft_list(v, 8)

    @field_validator("follow_ups", mode="before", check_fields=False)
    @classmethod
    def _follow(cls, v):
        return _soft_list(v, 3, 90)

    @field_validator("topic", mode="before", check_fields=False)
    @classmethod
    def _topic(cls, v):
        return cut_words(v, 40) if isinstance(v, str) else v


class ChatAnswer(_SoftChat):
    answer: str = Field(min_length=1, max_length=2400)
    citations: list[str] = Field(default_factory=list, max_length=8)
    topic: str = Field(max_length=40)
    follow_ups: list[FollowUp] = Field(default_factory=list, max_length=3)
    confidence: Literal["high", "medium", "low"]
    needs_birth_time: bool = False

    @field_validator("answer", mode="before")
    @classmethod
    def _answer(cls, v):
        return cut_sentences(v, 2400) if isinstance(v, str) else v


class ChatMeta(_SoftChat):
    """The JSON after the `<<<META>>>` delimiter in streaming mode."""

    citations: list[str] = Field(default_factory=list, max_length=8)
    topic: str = Field(max_length=40)
    follow_ups: list[FollowUp] = Field(default_factory=list, max_length=3)
    confidence: Literal["high", "medium", "low"]
    needs_birth_time: bool = False


def _soft_text(limit):
    return lambda v: cut_sentences(v, limit) if isinstance(v, str) else v


class DailySign(_Strict):
    @field_validator("general", "love", "career", "wellness", mode="before")
    @classmethod
    def _soft(cls, v, info):
        return cut_sentences(v, 900 if info.field_name == "general" else 500) if isinstance(v, str) else v

    @field_validator("citations", mode="before")
    @classmethod
    def _cites(cls, v):
        return _soft_list(v, 8)

    general: str = Field(min_length=20, max_length=900)
    love: str = Field(min_length=10, max_length=500)
    career: str = Field(min_length=10, max_length=500)
    wellness: str = Field(min_length=10, max_length=500)
    citations: list[str] = Field(default_factory=list, max_length=8)


class AreaText(_Strict):
    text: str = Field(min_length=10, max_length=420)

    @field_validator("text", mode="before")
    @classmethod
    def _soft(cls, v):
        return cut_sentences(v, 420) if isinstance(v, str) else v


class PersonalAreas(_Strict):
    love: AreaText
    career: AreaText
    wellness: AreaText
    money: AreaText


class PersonalReadingText(_Strict):
    """R3 narrative. Scores, key_factors, timing, lucky and dasha_context are engine values and are
    deliberately NOT part of this schema, so the model cannot set or alter them."""

    headline: str = Field(min_length=3, max_length=90)
    overview: str = Field(min_length=40, max_length=1100)
    areas: PersonalAreas
    affirmation: str = Field(min_length=3, max_length=160)
    citations: list[str] = Field(default_factory=list, max_length=8)

    @field_validator("headline", mode="before")
    @classmethod
    def _h(cls, v):
        return cut_words(v, 90) if isinstance(v, str) else v

    @field_validator("overview", mode="before")
    @classmethod
    def _o(cls, v):
        return cut_sentences(v, 1100) if isinstance(v, str) else v

    @field_validator("affirmation", mode="before")
    @classmethod
    def _a(cls, v):
        return cut_words(v, 160) if isinstance(v, str) else v

    @field_validator("citations", mode="before")
    @classmethod
    def _c(cls, v):
        return _soft_list(v, 8)


class CategoryText(_Strict):
    key: str = Field(max_length=40)          # must be one of the engine's category keys
    summary: str = Field(min_length=1, max_length=600)


class AspectInterpretation(_Strict):
    aspect_key: str = Field(max_length=80)   # references a computed aspect by key, never a degree
    text: str = Field(max_length=400)


class CompatNarrative(_Strict):
    summary: str = Field(min_length=20, max_length=1200)
    categories: list[CategoryText] = Field(max_length=12)   # list, not a map: portable across vendors
    aspect_interpretations: list[AspectInterpretation] = Field(default_factory=list, max_length=10)
    strengths: list[str] = Field(min_length=3, max_length=3)
    challenges: list[str] = Field(min_length=3, max_length=3)


class JudgeScore(_Strict):
    criterion: Literal["personalisation", "specificity", "actionability", "tone", "coherence"]
    score: int = Field(ge=1, le=5)
    evidence: str = Field(max_length=400)


class JudgeVerdict(_Strict):
    scores: list[JudgeScore] = Field(min_length=5, max_length=5)
    safety_ok: bool


def _strip(node):
    if isinstance(node, dict):
        out = {k: _strip(v) for k, v in node.items() if k not in _STRIP}
        if out.get("type") == "object":
            out.setdefault("additionalProperties", False)
            # every property required: some engines demand it; Optional semantics come from Pydantic defaults
            if "properties" in out:
                out["required"] = list(out["properties"])
        return out
    if isinstance(node, list):
        return [_strip(v) for v in node]
    return node


def _inline_refs(schema: dict) -> dict:
    defs = schema.pop("$defs", {})

    def walk(n):
        if isinstance(n, dict):
            if "$ref" in n:
                return walk(copy.deepcopy(defs[n["$ref"].split("/")[-1]]))
            return {k: walk(v) for k, v in n.items()}
        if isinstance(n, list):
            return [walk(v) for v in n]
        return n

    return walk(schema)


def provider_schema(model: type[BaseModel]) -> dict:
    """Flat, ref-free, bound-free JSON Schema safe for Gemini and Anthropic structured output."""
    return _strip(_inline_refs(model.model_json_schema()))
