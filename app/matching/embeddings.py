from app.llm.factory import get_llm_client


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts using the configured LLM provider."""
    client = get_llm_client()
    return await client.embed(texts)


async def embed_text(text: str) -> list[float]:
    """Embed a single text."""
    results = await embed_texts([text])
    return results[0]