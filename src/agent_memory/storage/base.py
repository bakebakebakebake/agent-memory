from __future__ import annotations

from typing import Protocol

from agent_memory.models import MemoryItem, RelationEdge


class StorageBackend(Protocol):
    def add_memory(self, item: MemoryItem) -> MemoryItem:
        ...

    def get_memory(self, memory_id: str) -> MemoryItem | None:
        ...

    def update_memory(self, item: MemoryItem) -> MemoryItem:
        ...

    def soft_delete_memory(self, memory_id: str) -> bool:
        ...

    def search_full_text(self, query: str, limit: int = 10, memory_type: str | None = None) -> list[tuple[MemoryItem, float]]:
        ...

    def search_by_entities(self, entities: list[str], limit: int = 10, memory_type: str | None = None) -> list[tuple[MemoryItem, float]]:
        ...

    def search_by_vector(
        self,
        embedding: list[float],
        limit: int = 10,
        memory_type: str | None = None,
    ) -> list[tuple[MemoryItem, float]]:
        ...

    def touch_memory(self, memory_id: str) -> None:
        ...

    def trace_ancestors(self, memory_id: str, max_depth: int = 10) -> list[MemoryItem]:
        ...

    def list_memories(self, include_deleted: bool = False) -> list[MemoryItem]:
        ...

    def add_relation(self, edge: RelationEdge) -> None:
        ...

    def list_relations(self, memory_id: str | None = None) -> list[RelationEdge]:
        ...

    def trace_descendants(self, memory_id: str, max_depth: int = 10) -> list[MemoryItem]:
        ...

    def relation_exists_between(
        self,
        left_id: str,
        right_id: str,
        relation_types: list[str] | None = None,
    ) -> bool:
        ...
