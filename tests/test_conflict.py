from agent_memory import MemoryClient
from agent_memory.config import AgentMemoryConfig
from agent_memory.controller.conflict import ConflictDetector
from agent_memory.models import MemoryItem, MemoryType, RelationType
from agent_memory.storage.sqlite_backend import SQLiteBackend


class DummyEmbeddingProvider:
    dimension = 3

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        for text in texts:
            normalized = text.lower()
            vectors.append(
                [
                    1.0 if "sqlite" in normalized else 0.0,
                    1.0 if ("not" in normalized or "不" in normalized) else 0.0,
                    1.0 if "prefer" in normalized or "喜欢" in normalized else 0.0,
                ]
            )
        return vectors


def test_conflict_detector_flags_polarity_mismatch() -> None:
    backend = SQLiteBackend(":memory:")
    existing = MemoryItem(
        id="existing",
        content="The user prefers SQLite for local-first memory.",
        memory_type=MemoryType.SEMANTIC,
        embedding=[1.0, 0.0, 1.0],
        source_id="test",
        entity_refs=["SQLite"],
    )
    backend.add_memory(existing)

    candidate = MemoryItem(
        id="candidate",
        content="The user does not prefer SQLite for local-first memory.",
        memory_type=MemoryType.SEMANTIC,
        embedding=[1.0, 1.0, 1.0],
        source_id="test",
        entity_refs=["SQLite"],
    )
    conflicts = ConflictDetector(backend).detect(candidate)
    assert conflicts
    assert conflicts[0].existing_id == "existing"


def test_client_add_creates_contradiction_relation() -> None:
    backend = SQLiteBackend(":memory:")
    client = MemoryClient(
        config=AgentMemoryConfig(database_path=":memory:"),
        backend=backend,
        embedding_provider=DummyEmbeddingProvider(),
    )
    first = client.add("The user prefers SQLite for agent memory.", source_id="s1")
    second = client.add("The user does not prefer SQLite for agent memory.", source_id="s2")

    relations = backend.list_relations(second.id)
    assert any(edge.relation_type is RelationType.CONTRADICTS for edge in relations)
    assert second.trust_score < first.trust_score
