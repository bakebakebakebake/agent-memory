from datetime import datetime, timedelta, timezone

from agent_memory import MemoryClient
from agent_memory.config import AgentMemoryConfig
from agent_memory.models import MemoryLayer
from agent_memory.storage.sqlite_backend import SQLiteBackend


class DummyEmbeddingProvider:
    dimension = 2

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, float(index + 1)] for index, _ in enumerate(texts)]


def build_client():
    from agent_memory import MemoryClient

    backend = SQLiteBackend(":memory:")
    return MemoryClient(
        config=AgentMemoryConfig(database_path=":memory:"),
        backend=backend,
        embedding_provider=DummyEmbeddingProvider(),
    )


def test_health_report_includes_suggestions() -> None:
    client = build_client()
    old = client.add("The user prefers SQLite.", source_id="old")
    stale_time = datetime.now(timezone.utc) - timedelta(days=45)
    client.update(old, last_accessed=stale_time, created_at=stale_time, layer=MemoryLayer.SHORT_TERM)

    report = client.health()
    assert report.total_memories == 1
    assert report.stale_ratio > 0
    assert report.suggestions


def test_export_import_round_trip(tmp_path) -> None:
    client = build_client()
    parent = client.add("User values traceability.", source_id="root")
    child = client.add(
        "SQLite is chosen because traceability matters.",
        source_id="child",
        causal_parent_id=parent.id,
    )
    path = tmp_path / "memories.jsonl"
    exported = client.export_jsonl(str(path))
    assert exported == 2

    imported_backend = SQLiteBackend(":memory:")
    imported_client = MemoryClient(
        config=AgentMemoryConfig(database_path=":memory:"),
        backend=imported_backend,
        embedding_provider=DummyEmbeddingProvider(),
    )
    imported = imported_client.import_jsonl(str(path))
    assert imported == 2
    assert len(imported_backend.list_memories()) == 2
    assert imported_backend.trace_ancestors(child.id)[0].id == parent.id


def test_maintain_is_idempotent_for_existing_conflicts() -> None:
    client = build_client()
    first_memory = client.add("The user prefers SQLite.", source_id="a")
    second_memory = client.add("The user does not prefer SQLite.", source_id="b")

    first = client.maintain()
    second = client.maintain()

    assert client.backend.relation_exists_between(first_memory.id, second_memory.id, relation_types=["contradicts"])
    assert first.consolidated >= 1
    assert second.conflicts_resolved == 0
    assert second.consolidated == 0


def test_consolidate_merges_overlapping_memories() -> None:
    client = build_client()
    first = client.add("SQLite is preferred for local-first demos.", source_id="s1", entity_refs=["SQLite"])
    second = client.add("SQLite is preferred for zero-config demos.", source_id="s2", entity_refs=["SQLite"])

    consolidated = client.consolidate()
    assert consolidated == 1
    merged = [memory for memory in client.backend.list_memories() if "consolidated" in memory.tags]
    assert merged
    assert merged[0].supersedes_id in {first.id, second.id}
