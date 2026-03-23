from __future__ import annotations

import pytest

from agent_memory import MemoryClient
from agent_memory.config import AgentMemoryConfig
from agent_memory.storage.sqlite_backend import SQLiteBackend


class DummyEmbeddingProvider:
    dimension = 3

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, float(index + 1), float(len(text))] for index, text in enumerate(texts)]


@pytest.fixture
def backend() -> SQLiteBackend:
    return SQLiteBackend(":memory:")


@pytest.fixture
def client(backend: SQLiteBackend) -> MemoryClient:
    return MemoryClient(
        config=AgentMemoryConfig(database_path=":memory:"),
        backend=backend,
        embedding_provider=DummyEmbeddingProvider(),
    )


@pytest.fixture
def tmp_db_path(tmp_path) -> str:
    return str(tmp_path / "test.db")
