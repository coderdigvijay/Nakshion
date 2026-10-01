"""Provider-neutral request/result types (llm-integration.md §2)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, TypedDict

Task = Literal["chat", "daily_personal", "daily_sign", "compat", "premium_report", "judge", "title"]
FinishReason = Literal["stop", "length", "safety", "error"]


class LLMMessage(TypedDict):
    role: Literal["user", "assistant"]
    content: str


@dataclass(frozen=True)
class LLMRequest:
    task: Task
    system: str                                  # stable, cacheable prefix (persona + rules)
    context_blocks: tuple[str, ...]              # chart facts, RAG notes: after system, before history
    messages: tuple[LLMMessage, ...]             # history + current (delimited) user turn
    max_output_tokens: int
    response_schema: dict | None = None          # provider-safe JSON Schema (see schemas.provider_schema)
    temperature: float = 0.6
    timeout_s: float = 15.0
    prompt_id: str = ""                          # e.g. "chat@v1"
    # Never forwarded to a provider. Used for usage rows and logs only.
    metadata: dict = field(default_factory=dict)

    def with_(self, **changes) -> "LLMRequest":
        from dataclasses import replace

        return replace(self, **changes)


@dataclass(frozen=True)
class LLMResult:
    text: str
    provider: str
    model: str
    input_tokens: int              # total prompt tokens, cached ones included
    output_tokens: int             # billed output tokens (thinking included)
    cached_input_tokens: int = 0   # cache reads
    cache_write_tokens: int = 0    # Anthropic cache creation (billed 1.25x)
    latency_ms: int = 0
    finish_reason: FinishReason = "stop"
    parsed: dict | None = None     # validated JSON when a schema was requested


@dataclass(frozen=True)
class LLMChunk:
    """One streaming event. Text deltas until `final` carries usage."""

    text: str = ""
    final: LLMResult | None = None
