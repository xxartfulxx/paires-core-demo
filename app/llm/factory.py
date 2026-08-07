from app.core.config import get_settings
from app.llm.anthropic import AnthropicClient
from app.llm.base import LLMClient
from app.llm.openai import OpenAIClient

settings = get_settings()


def get_llm_client() -> LLMClient:
    provider = settings.llm_provider.lower()
    if provider == "openai":
        return OpenAIClient()
    if provider == "anthropic":
        return AnthropicClient()
    raise ValueError(f"Unsupported LLM provider: {provider}")