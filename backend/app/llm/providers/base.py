"""The single provider interface. Adapters are the only modules that import a vendor SDK."""

from __future__ import annotations

from typing import AsyncIterator, Protocol, runtime_checkable

from app.llm.types import LLMChunk, LLMRequest, LLMResult


@runtime_checkable
class LLMProvider(Protocol):
    name: str

    async def generate(self, req: LLMRequest, model: str) -> LLMResult: ...

    def stream(self, req: LLMRequest, model: str) -> AsyncIterator[LLMChunk]: ...


def first_user_with_context(req: LLMRequest) -> list[tuple[str, str]]:
    """(role, text) turns with context blocks prepended to the FIRST user turn.

    Keeps the stable prefix (system + chart facts + notes) byte-identical across calls in a
    conversation, which is what implicit prefix caching keys on.
    """
    turns = [(m["role"], m["content"]) for m in req.messages]
    if req.context_blocks:
        ctx = "\n\n".join(req.context_blocks)
        for i, (role, text) in enumerate(turns):
            if role == "user":
                turns[i] = (role, f"{ctx}\n\n{text}")
                break
        else:
            turns.insert(0, ("user", ctx))
    return turns
