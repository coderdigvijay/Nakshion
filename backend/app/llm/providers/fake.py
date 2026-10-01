"""FakeProvider: deterministic, no network. Used by unit tests, the offline eval mode, and
local dev without keys (`LLM_MODEL_CHAT=fake-chat`)."""

from __future__ import annotations

import asyncio
from collections import deque
from typing import AsyncIterator, Callable, Union

from app.llm.types import LLMChunk, LLMRequest, LLMResult

Script = Union[str, Exception, Callable[[LLMRequest, str], str]]


class FakeProvider:
    def __init__(
        self,
        responses: list[Script] | None = None,
        *,
        name: str = "fake",
        default: Script = '{"answer": "ok", "citations": [], "topic": "general", "follow_ups": [], "confidence": "low"}',
        delay_s: float = 0.0,
        chunk_size: int = 12,
        input_tokens: int = 100,
        output_tokens: int = 50,
        finish_reason: str = "stop",
        fail_mid_stream_after: int | None = None,
    ):
        self.name = name
        self._queue: deque[Script] = deque(responses or [])
        self._default = default
        self._delay = delay_s
        self._chunk = chunk_size
        self._in = input_tokens
        self._out = output_tokens
        self._finish = finish_reason
        self._fail_after = fail_mid_stream_after
        self.calls: list[tuple[LLMRequest, str]] = []

    def push(self, *items: Script) -> None:
        self._queue.extend(items)

    def _next(self, req: LLMRequest, model: str) -> str:
        item = self._queue.popleft() if self._queue else self._default
        if isinstance(item, Exception):
            raise item
        if callable(item):
            return item(req, model)
        return item

    def _result(self, text: str, model: str) -> LLMResult:
        return LLMResult(
            text=text, provider=self.name, model=model, input_tokens=self._in,
            output_tokens=self._out, latency_ms=int(self._delay * 1000),
            finish_reason=self._finish,  # type: ignore[arg-type]
        )

    async def generate(self, req: LLMRequest, model: str) -> LLMResult:
        self.calls.append((req, model))
        if self._delay:
            await asyncio.sleep(self._delay)
        return self._result(self._next(req, model), model)

    async def stream(self, req: LLMRequest, model: str) -> AsyncIterator[LLMChunk]:
        self.calls.append((req, model))
        if self._delay:
            await asyncio.sleep(self._delay)
        text = self._next(req, model)
        for i in range(0, len(text), self._chunk):
            if self._fail_after is not None and i // self._chunk >= self._fail_after:
                from app.llm.errors import LLMServerError

                raise LLMServerError("fake mid-stream failure", provider=self.name, model=model)
            await asyncio.sleep(0)
            yield LLMChunk(text=text[i : i + self._chunk])
        yield LLMChunk(final=self._result(text, model))
