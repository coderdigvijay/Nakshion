"""GeminiProvider: the ONLY module that imports the Google Gen AI SDK (`google-genai`).

The deprecated `google-generativeai` package is not used (end of support 2025-11-30).
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
from app.llm.providers.base import first_user_with_context
from app.llm.types import LLMChunk, LLMRequest, LLMResult

_BLOCK_REASONS = {"SAFETY", "PROHIBITED_CONTENT", "BLOCKLIST", "SPII", "RECITATION", "IMAGE_SAFETY"}


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key: str | None = None, *, api_keys: list[str] | None = None, client: Any = None,
                 clients: list[Any] | None = None, thinking_level: str | None = "low"):
        """One client per API key. On a 429 the adapter rotates to the next key and retries
        immediately (each key at most once per call); other errors go back to the router."""
        if clients is None:
            if client is not None:
                clients = [client]
            else:
                keys = [k for k in ([api_key] if api_key else []) + list(api_keys or []) if k]
                if not keys:
                    raise LLMBadRequest("GEMINI_API_KEY is not configured", provider=self.name)
                from google import genai

                clients = [genai.Client(api_key=k) for k in dict.fromkeys(keys)]
        self._clients = clients
        self._next = 0
        self._thinking_level = thinking_level

    @property
    def _client(self) -> Any:  # current client (kept for readability in tests)
        return self._clients[self._next % len(self._clients)]

    def _rotate(self) -> None:
        self._next = (self._next + 1) % len(self._clients)

    # ------------------------------------------------------------------ mapping
    def _config(self, req: LLMRequest) -> Any:
        from google.genai import types

        kwargs: dict[str, Any] = {
            "system_instruction": req.system,
            "max_output_tokens": req.max_output_tokens,
            "temperature": req.temperature,
            "http_options": types.HttpOptions(timeout=int(req.timeout_s * 1000)),
        }
        if req.response_schema is not None:
            kwargs["response_mime_type"] = "application/json"
            kwargs["response_json_schema"] = req.response_schema
        if self._thinking_level:
            kwargs["thinking_config"] = types.ThinkingConfig(thinking_level=self._thinking_level)
        return types.GenerateContentConfig(**kwargs)

    @staticmethod
    def _contents(req: LLMRequest) -> list[Any]:
        from google.genai import types

        return [
            types.Content(role="model" if role == "assistant" else "user", parts=[types.Part(text=text)])
            for role, text in first_user_with_context(req)
        ]

    @staticmethod
    def _rate_info(exc: Exception) -> tuple[float | None, bool]:
        """(retryDelay seconds, per-day quota exhausted) from a Gemini 429 body."""
        import json as _json
        import re as _re

        raw = _json.dumps(getattr(exc, "details", None) or getattr(exc, "response_json", None) or {}, default=str)
        m = _re.search(r'"retryDelay"\s*:\s*"?([0-9.]+)s', raw)
        daily = bool(_re.search(r"PerDay|per day|daily", raw, _re.I))
        return (float(m.group(1)) if m else None), daily

    def _map_error(self, exc: Exception, model: str) -> LLMError:
        from google.genai import errors

        if isinstance(exc, errors.APIError):
            code = getattr(exc, "code", 0) or 0
            detail = f"gemini {code} {getattr(exc, 'status', '') or ''}: {getattr(exc, 'message', '') or ''}"
            kw = {"provider": self.name, "model": model, "status": code}
            if code == 429:
                ra, daily = self._rate_info(exc)
                return LLMRateLimited(detail, retry_after_s=ra, quota_exhausted=daily, **kw)
            if code in (408, 504):
                return LLMTimeout(detail, **kw)
            if code >= 500:
                return LLMServerError(detail, **kw)
            return LLMBadRequest(detail, **kw)
        name = type(exc).__name__
        if "timeout" in name.lower():
            return LLMTimeout(f"gemini {name}", provider=self.name, model=model)
        # connection errors and anything unknown: treat as transient provider failure
        return LLMServerError(f"gemini {name}: {str(exc)[:160]}", provider=self.name, model=model)

    def _usage(self, resp: Any) -> tuple[int, int, int]:
        um = getattr(resp, "usage_metadata", None)
        if um is None:
            return 0, 0, 0
        prompt = um.prompt_token_count or 0
        out = (um.candidates_token_count or 0) + (um.thoughts_token_count or 0)
        cached = um.cached_content_token_count or 0
        return prompt, out, cached

    def _finish(self, resp: Any, model: str) -> str:
        fb = getattr(resp, "prompt_feedback", None)
        if fb is not None and getattr(fb, "block_reason", None):
            raise LLMBlocked("gemini prompt blocked", provider=self.name, model=model)
        cands = getattr(resp, "candidates", None) or []
        if not cands:
            return "stop"
        reason = cands[0].finish_reason
        rname = getattr(reason, "name", str(reason or "")).upper()
        if rname in _BLOCK_REASONS:
            raise LLMBlocked(f"gemini finish {rname}", provider=self.name, model=model)
        if rname == "MAX_TOKENS":
            return "length"
        return "stop"

    # ------------------------------------------------------------------ API
    async def _call(self, model: str, req: LLMRequest, *, stream: bool) -> Any:
        last: LLMError | None = None
        for _ in range(len(self._clients) + 1):
            fn = self._client.aio.models.generate_content_stream if stream else self._client.aio.models.generate_content
            try:
                return await fn(model=model, contents=self._contents(req), config=self._config(req))
            except LLMError:
                raise
            except Exception as exc:  # noqa: BLE001 - mapped, never re-raised raw
                last = self._map_error(exc, model)
                if isinstance(last, LLMRateLimited) and len(self._clients) > 1:
                    self._rotate()
                    continue
                if getattr(last, "status", None) in (401, 403) and len(self._clients) > 1:
                    # a revoked / denied key must not poison the pool: drop it and try the next one at once
                    self._clients.pop(self._next % len(self._clients))
                    self._next = 0
                    continue
                raise last from None
        raise last  # every key rate limited

    async def generate(self, req: LLMRequest, model: str) -> LLMResult:
        t0 = time.monotonic()
        resp = await self._call(model, req, stream=False)
        finish = self._finish(resp, model)
        prompt, out, cached = self._usage(resp)
        return LLMResult(
            text=resp.text or "",
            provider=self.name,
            model=model,
            input_tokens=prompt,
            output_tokens=out,
            cached_input_tokens=cached,
            latency_ms=int((time.monotonic() - t0) * 1000),
            finish_reason=finish,  # type: ignore[arg-type]
        )

    async def stream(self, req: LLMRequest, model: str) -> AsyncIterator[LLMChunk]:
        t0 = time.monotonic()
        parts: list[str] = []
        last = None
        try:
            stream = await self._call(model, req, stream=True)
            async for resp in stream:
                last = resp
                self._finish(resp, model)  # raises on mid-stream block
                text = resp.text or ""
                if text:
                    parts.append(text)
                    yield LLMChunk(text=text)
        except LLMError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise self._map_error(exc, model) from None
        finish = self._finish(last, model) if last is not None else "stop"
        prompt, out, cached = self._usage(last) if last is not None else (0, 0, 0)
        yield LLMChunk(
            final=LLMResult(
                text="".join(parts), provider=self.name, model=model, input_tokens=prompt,
                output_tokens=out, cached_input_tokens=cached,
                latency_ms=int((time.monotonic() - t0) * 1000), finish_reason=finish,  # type: ignore[arg-type]
            )
        )
