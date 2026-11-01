import logging
from typing import Optional
from app.core.config import settings
from app.services.llm.base import BaseLLMAdapter
from app.services.llm.gemini_adapter import GeminiAdapter
from app.services.llm.openai_adapter import OpenAIAdapter
from app.services.llm.anthropic_adapter import AnthropicAdapter
from app.services.llm.mock_adapter import MockLLMAdapter

logger = logging.getLogger(__name__)

def get_llm_adapter(provider: Optional[str] = None) -> BaseLLMAdapter:
    """Instantiate and return the requested LLM provider adapter or fallback gracefully."""
    selected_provider = (provider or settings.DEFAULT_LLM_PROVIDER).lower()

    if selected_provider == "gemini" and settings.GEMINI_API_KEY and not settings.GEMINI_API_KEY.startswith("mock-"):
        return GeminiAdapter(api_key=settings.GEMINI_API_KEY)
    elif selected_provider == "openai" and settings.OPENAI_API_KEY:
        return OpenAIAdapter(api_key=settings.OPENAI_API_KEY)
    elif selected_provider == "anthropic" and settings.ANTHROPIC_API_KEY:
        return AnthropicAdapter(api_key=settings.ANTHROPIC_API_KEY)

    logger.info(f"Using MockLLMAdapter for provider='{selected_provider}' (no live API key provided).")
    return MockLLMAdapter()
