from __future__ import annotations

from dataclasses import dataclass

from agent_memory.storage.base import StorageBackend


@dataclass(slots=True)
class AuditLogReader:
    backend: StorageBackend

    def recent(self, limit: int = 50) -> list[dict[str, object]]:
        return self.backend.get_audit_events(limit=limit)
