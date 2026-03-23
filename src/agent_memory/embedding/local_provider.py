from __future__ import annotations

import hashlib


class LocalEmbeddingProvider:
    def __init__(self, dimension: int = 384, model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
        self.dimension = dimension
        self.model_name = model_name
        self._model = None

    def embed(self, texts: list[str]) -> list[list[float]]:
        model = self._load_model()
        if model is None:
            return [self._hash_embed(text) for text in texts]
        return [list(vector) for vector in model.encode(texts, normalize_embeddings=True)]

    def _load_model(self):
        if self._model is not None:
            return self._model
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            return None
        self._model = SentenceTransformer(self.model_name)
        return self._model

    def _hash_embed(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        values: list[float] = []
        while len(values) < self.dimension:
            for byte in digest:
                values.append((byte / 255.0) * 2 - 1)
                if len(values) == self.dimension:
                    break
            digest = hashlib.sha256(digest).digest()
        return values

