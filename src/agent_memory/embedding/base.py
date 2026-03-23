from __future__ import annotations

from typing import Protocol


class EmbeddingProvider(Protocol):
    dimension: int

    def embed(self, texts: list[str]) -> list[list[float]]:
        ...

