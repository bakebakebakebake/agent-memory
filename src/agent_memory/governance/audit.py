from __future__ import annotations

from dataclasses import dataclass

from agent_memory.storage.sqlite_backend import SQLiteBackend


@dataclass(slots=True)
class AuditLogReader:
    backend: SQLiteBackend

    def recent(self, limit: int = 50) -> list[dict[str, object]]:
        return self.backend.get_audit_events(limit=limit)

