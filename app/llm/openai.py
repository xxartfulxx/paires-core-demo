from typing import Any

from openai import AsyncOpenAI

from app.core.config import get_settings
from app.llm.base import LLMClient

settings = get_settings()


class OpenAIClient(LLMClient):
    def __init__(self) -> None:
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.embedding_model = settings.embedding_model

    async def embed(self, texts: list[str]) -> list[list[float]]:
        response = await self.client.embeddings.create(
            model=self.embedding_model,
            input=texts,
        )
        return [item.embedding for item in response.data]

    async def complete(self, system: str, user: str, **kwargs: Any) -> str:
        response = await self.client.chat.completions.create(
            model=kwargs.get("model", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=kwargs.get("temperature", 0.4),
        )
        return response.choices[0].message.content or ""