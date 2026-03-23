from datetime import datetime, timezone

from agent_memory.models import MemoryItem, MemoryType
from agent_memory.storage.sqlite_backend import SQLiteBackend


def build_memory(memory_id: str, content: str, parent_id: str | None = None) -> MemoryItem:
    now = datetime.now(timezone.utc)
    entity_refs = ["agent"]
    if "SQLite" in content:
        entity_refs.append("sqlite")
    if "Postgres" in content:
        entity_refs.append("postgres")
    return MemoryItem(
        id=memory_id,
        content=content,
        memory_type=MemoryType.SEMANTIC,
        embedding=[0.1, 0.2, 0.3],
        created_at=now,
        last_accessed=now,
        source_id="test-suite",
        causal_parent_id=parent_id,
        entity_refs=entity_refs,
        tags=["test"],
    )


def test_backend_add_get_and_soft_delete() -> None:
    backend = SQLiteBackend(":memory:")
    stored = backend.add_memory(build_memory("m1", "SQLite is great for local-first agents"))

    found = backend.get_memory(stored.id)
    assert found is not None
    assert found.content == stored.content

    assert backend.soft_delete_memory(stored.id) is True
    assert backend.soft_delete_memory(stored.id) is False


def test_backend_full_text_and_entity_search() -> None:
    backend = SQLiteBackend(":memory:")
    backend.add_memory(build_memory("m1", "SQLite works well for local agent memory"))
    backend.add_memory(build_memory("m2", "Postgres works for remote multi-tenant memory"))

    full_text = backend.search_full_text("SQLite", limit=5)
    entity = backend.search_by_entities(["sqlite"], limit=5)

    assert full_text
    assert full_text[0][0].id == "m1"
    assert entity
    assert entity[0][0].id == "m1"


def test_backend_trace_ancestors() -> None:
    backend = SQLiteBackend(":memory:")
    backend.add_memory(build_memory("root", "User prefers local-first systems"))
    backend.add_memory(build_memory("child", "SQLite is selected because local-first matters", parent_id="root"))
    backend.add_memory(build_memory("grandchild", "Use WAL mode to support concurrent reads", parent_id="child"))

    trace = backend.trace_ancestors("grandchild")
    assert [item.id for item in trace] == ["child", "root"]


def test_backend_creates_expected_indexes() -> None:
    backend = SQLiteBackend(":memory:")
    rows = backend.connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'index' AND name LIKE 'idx_%' ORDER BY name"
    ).fetchall()
    index_names = {row["name"] for row in rows}
    assert "idx_memories_memory_type" in index_names
    assert "idx_memories_last_accessed" in index_names
    assert "idx_relations_source_type" in index_names


def test_backend_dispatches_to_sqlite_vec_when_enabled(monkeypatch) -> None:
    backend = SQLiteBackend(":memory:")
    backend._sqlite_vec_enabled = True
    backend.add_memory(build_memory("m1", "SQLite works well for local agent memory"))

    called = {"sqlite_vec": False}

    def fake_sqlite_vec(*, embedding, limit, memory_type):
        called["sqlite_vec"] = True
        return backend._search_by_vector_fallback(embedding=embedding, limit=limit, memory_type=memory_type)

    monkeypatch.setattr(backend, "_search_by_vector_sqlite_vec", fake_sqlite_vec)
    results = backend.search_by_vector([0.1, 0.2, 0.3], limit=5)
    assert called["sqlite_vec"] is True
    assert results[0][0].id == "m1"
