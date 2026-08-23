from __future__ import annotations

from functools import lru_cache

from ...config import get_settings
from .base import LLMAdapter


@lru_cache
def get_llm() -> LLMAdapter:
    settings = get_settings()
    if settings.llm_provider == "openai":
        if not settings.openai_api_key:
            raise RuntimeError("LLM_PROVIDER=openai requires OPENAI_API_KEY")
        from .openai import OpenAIAdapter

        return OpenAIAdapter(settings.openai_api_key)
    from .mock import MockLLMAdapter

    return MockLLMAdapter()

