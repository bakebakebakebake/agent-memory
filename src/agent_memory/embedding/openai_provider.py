from __future__ import annotations


class OpenAIEmbeddingProvider:
    def __init__(self, model: str = "text-embedding-3-small", dimension: int = 1536) -> None:
        self.model = model
        self.dimension = dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        raise RuntimeError("Install the OpenAI SDK and wire API calls before using OpenAIEmbeddingProvider.")

