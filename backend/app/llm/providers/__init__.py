"""Provider adapters. Vendor SDKs are imported lazily inside their adapter only."""

from app.llm.providers.base import LLMProvider
from app.llm.providers.fake import FakeProvider

__all__ = ["LLMProvider", "FakeProvider", "build_providers"]


def build_providers(settings) -> dict[str, LLMProvider]:
    """Instantiate the adapters that have credentials. Missing keys = provider absent,
    so the router skips it (and a chain with nothing left raises LLMUnavailable)."""
    providers: dict[str, LLMProvider] = {}
    gemini_keys = settings.gemini_keys()
    if gemini_keys:
        from app.llm.providers.gemini import GeminiProvider

        providers["gemini"] = GeminiProvider(api_keys=gemini_keys, thinking_level=settings.gemini_thinking_level)
    anthropic_keys = settings.anthropic_keys()
    if anthropic_keys:
        from app.llm.providers.claude import AnthropicProvider

        providers["anthropic"] = AnthropicProvider(
            anthropic_keys[0],
            sampling_models=settings.anthropic_sampling_models,
            thinking_models=settings.anthropic_thinking_models,
            thinking_headroom_tokens=settings.anthropic_thinking_headroom_tokens,
        )
    return providers
