from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
import json
from pathlib import Path

from agent_memory.models import MemoryItem, MemoryLayer, MemoryType, RelationEdge, RelationType
from agent_memory.storage.sqlite_backend import SQLiteBackend


def _serialize_value(value: object) -> object:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, list):
        return [_serialize_value(item) for item in value]
    return value


@dataclass(slots=True)
class MemoryExporter:
    backend: SQLiteBackend

    def export_jsonl(self, path: str) -> int:
        destination = Path(path)
        count = 0
        with destination.open("w", encoding="utf-8") as handle:
            for memory in self.backend.list_memories(include_deleted=True):
                payload = {key: _serialize_value(value) for key, value in asdict(memory).items()}
                handle.write(json.dumps({"type": "memory", "payload": payload}, ensure_ascii=False) + "\n")
                count += 1
            for relation in self.backend.list_relations():
                payload = {key: _serialize_value(value) for key, value in asdict(relation).items()}
                handle.write(json.dumps({"type": "relation", "payload": payload}, ensure_ascii=False) + "\n")
        return count


@dataclass(slots=True)
class MemoryImporter:
    backend: SQLiteBackend

    def import_jsonl(self, path: str) -> int:
        source = Path(path)
        count = 0
        memories: list[MemoryItem] = []
        relations: list[RelationEdge] = []
        with source.open("r", encoding="utf-8") as handle:
            for line in handle:
                entry = json.loads(line)
                if entry["type"] == "memory":
                    payload = entry["payload"]
                    for key in ("created_at", "last_accessed", "valid_from", "valid_until", "deleted_at"):
                        if payload.get(key):
                            payload[key] = datetime.fromisoformat(payload[key])
                    payload["memory_type"] = MemoryType(payload["memory_type"])
                    payload["layer"] = MemoryLayer(payload["layer"])
                    memories.append(MemoryItem(**payload))
                elif entry["type"] == "relation":
                    payload = entry["payload"]
                    payload["created_at"] = datetime.fromisoformat(payload["created_at"])
                    payload["relation_type"] = RelationType(payload["relation_type"])
                    relations.append(RelationEdge(**payload))
        for memory in sorted(memories, key=lambda item: (item.causal_parent_id is not None, item.created_at)):
            if self.backend.get_memory(memory.id) is None:
                self.backend.add_memory(memory)
                count += 1
        for edge in relations:
            self.backend.add_relation(edge)
        return count
