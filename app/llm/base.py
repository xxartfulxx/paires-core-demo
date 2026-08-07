from abc import ABC, abstractmethod
from typing import Any


class LLMClient(ABC):
    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Return embeddings for a list of texts."""
        ...

    @abstractmethod
    async def complete(self, system: str, user: str, **kwargs: Any) -> str:
        """Simple chat completion."""
        ...