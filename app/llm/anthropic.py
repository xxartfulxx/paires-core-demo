from typing import Any

from anthropic import AsyncAnthropic

from app.core.config import get_settings
from app.llm.base import LLMClient

settings = get_settings()


class AnthropicClient(LLMClient):
    def __init__(self) -> None:
        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError(
            "Anthropic embeddings are not supported yet. Use OpenAI for embeddings."
        )

    async def complete(self, system: str, user: str, **kwargs: Any) -> str:
        response = await self.client.messages.create(
            model=kwargs.get("model", "claude-3-5-sonnet-20241022"),
            max_tokens=kwargs.get("max_tokens", 1024),
            system=system,
            messages=[{"role": "user", "content": user}],
            temperature=kwargs.get("temperature", 0.4),
        )
        return response.content[0].text