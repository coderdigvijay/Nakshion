"""AnthropicProvider: the ONLY module that imports the `anthropic` SDK (1.x).

- System is a list of blocks with `cache_control` so the persona+rules prefix and the
  chart-facts block are prompt-cached (cache reads bill at 0.1x).
- Structured output uses `output_config.format` (json_schema). The spec's forced-tool
  approach is NOT used: forced `tool_choice` returns 400 on Claude Sonnet 5.5.
- `temperature` was removed from the 1.x SDK signature; it is sent via `extra_body`
  only for models that still accept sampling params (Haiku 4.5). Sonnet 5.5 rejects
  non-default values, so it is omitted there.
- Sonnet 5.5 runs adaptive thinking (cannot be disabled); `max_tokens` gets headroom and
  `effort` is set explicitly. Haiku 4.5 gets neither (effort errors on Haiku 4.5).
- A `refusal` stop reason maps to LLMBlocked so the router falls to the next vendor.
- The SDK's own retries are disabled (`max_retries=0`): the router owns retry policy.
"""

from __future__ import annotations

import time
from typing import Any, AsyncIterator

from app.llm.errors import (
    LLMBadRequest,
    LLMBlocked,
    LLMError,
    LLMRateLimited,
    LLMServerError,
    LLMTimeout,
)
from app.llm.types import LLMChunk, LLMRequest, LLMResult


class AnthropicProvider:
    name = "anthropic"

    def __init__(
        self,
        api_key: str | None = None,
        *,
        client: Any = None,
        sampling_models: tuple[str, ...] = ("claude-haiku-4-5", "claude-haiku-4-5-20251001"),
        thinking_models: dict[str, str] | None = None,
        thinking_headroom_tokens: int = 2000,
    ):
        if client is None:
            if not api_key:
                raise LLMBadRequest("ANTHROPIC_API_KEY is not configured", provider=self.name)
            import anthropic

            client = anthropic.AsyncAnthropic(api_key=api_key, max_retries=0)
        self._client = client
        self._sampling = set(sampling_models)
        self._thinking = dict(thinking_models or {"claude-sonnet-5-5": "medium"})
        self._headroom = thinking_headroom_tokens

    # ------------------------------------------------------------------ mapping
    def _params(self, req: LLMRequest, model: str) -> dict[str, Any]:
        system: list[dict[str, Any]] = [
            {"type": "text", "text": req.system, "cache_control": {"type": "ephemeral"}}
        ]
        if req.context_blocks:
            system.append(
                {"type": "text", "text": "\n\n".join(req.context_blocks), "cache_control": {"type": "ephemeral"}}
            )
        params: dict[str, Any] = {
            "model": model,
            "system": system,
            "messages": [{"role": m["role"], "content": m["content"]} for m in req.messages],
            "max_tokens": req.max_output_tokens,
            "timeout": req.timeout_s,
        }
        output_config: dict[str, Any] = {}
        if req.response_schema is not None:
            output_config["format"] = {"type": "json_schema", "schema": req.response_schema}
        if model in self._thinking:
            output_config["effort"] = self._thinking[model]
            params["max_tokens"] = req.max_output_tokens + self._headroom
        if output_config:
            params["output_config"] = output_config
        if model in self._sampling:
            params["extra_body"] = {"temperature": req.temperature}
        return params

    def _map_error(self, exc: Exception, model: str) -> LLMError:
        import anthropic

        kw = {"provider": self.name, "model": model}
        if isinstance(exc, anthropic.APITimeoutError):
            return LLMTimeout("anthropic timeout", **kw)
        if isinstance(exc, anthropic.RateLimitError):
            ra = None
            try:
                ra = float(exc.response.headers.get("retry-after"))
            except (AttributeError, TypeError, ValueError):
                pass
            return LLMRateLimited(f"anthropic 429: {getattr(exc, 'message', '')}", status=429, retry_after_s=ra, **kw)
        if isinstance(exc, anthropic.APIConnectionError):
            return LLMServerError("anthropic connection error", **kw)
        if isinstance(exc, anthropic.APIStatusError):
            status = getattr(exc, "status_code", 0) or 0
            detail = f"anthropic {status}: {getattr(exc, 'message', '')}"
            if status >= 500 or status == 529:
                return LLMServerError(detail, status=status, **kw)
            return LLMBadRequest(detail, status=status, **kw)
        return LLMServerError(f"anthropic {type(exc).__name__}", **kw)

    def _result(self, msg: Any, model: str, t0: float) -> LLMResult:
        stop = getattr(msg, "stop_reason", None)
        if stop == "refusal":
            raise LLMBlocked("anthropic refusal", provider=self.name, model=model)
        text = "".join(getattr(b, "text", "") for b in msg.content if getattr(b, "type", "") == "text")
        u = msg.usage
        read = getattr(u, "cache_read_input_tokens", 0) or 0
        write = getattr(u, "cache_creation_input_tokens", 0) or 0
        return LLMResult(
            text=text,
            provider=self.name,
            model=getattr(msg, "model", None) or model,
            input_tokens=(u.input_tokens or 0) + read + write,
            output_tokens=u.output_tokens or 0,
            cached_input_tokens=read,
            cache_write_tokens=write,
            latency_ms=int((time.monotonic() - t0) * 1000),
            finish_reason="length" if stop == "max_tokens" else "stop",
        )

    # ------------------------------------------------------------------ API
    async def generate(self, req: LLMRequest, model: str) -> LLMResult:
        t0 = time.monotonic()
        try:
            msg = await self._client.messages.create(**self._params(req, model))
        except LLMError:
            raise
        except Exception as exc:  # noqa: BLE001 - mapped, never re-raised raw
            raise self._map_error(exc, model) from None
        return self._result(msg, model, t0)

    async def stream(self, req: LLMRequest, model: str) -> AsyncIterator[LLMChunk]:
        t0 = time.monotonic()
        try:
            async with self._client.messages.stream(**self._params(req, model)) as s:
                async for text in s.text_stream:
                    if text:
                        yield LLMChunk(text=text)
                final = await s.get_final_message()
        except LLMError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise self._map_error(exc, model) from None
        yield LLMChunk(final=self._result(final, model, t0))
