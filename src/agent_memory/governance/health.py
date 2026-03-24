from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agent_memory.models import HealthReport
from agent_memory.storage.base import StorageBackend


@dataclass(slots=True)
class MemoryHealthMonitor:
    backend: StorageBackend

    def generate(self) -> HealthReport:
        snapshot = self.backend.health_snapshot()
        suggestions: list[str] = []
        if snapshot["stale_ratio"] >= 0.3:
            suggestions.append("30%+ memories are stale; run a forgetting cycle.")
        if snapshot["orphan_ratio"] >= 0.2:
            suggestions.append("Orphan ratio is high; consolidate or attach relation edges.")
        if snapshot["unresolved_conflicts"] > 0:
            suggestions.append("Resolve contradiction edges to improve trust calibration.")

        size = int(snapshot.get("database_size_bytes", 0))
        database_path = getattr(self.backend, "database_path", "")
        if size == 0 and database_path and database_path not in {":memory:", ":remote:"}:
            path = Path(database_path)
            if path.exists():
                size = path.stat().st_size

        return HealthReport(
            total_memories=int(snapshot["total_memories"]),
            stale_ratio=float(snapshot["stale_ratio"]),
            orphan_ratio=float(snapshot["orphan_ratio"]),
            unresolved_conflicts=int(snapshot["unresolved_conflicts"]),
            average_trust_score=float(snapshot["average_trust_score"]),
            database_size_bytes=size,
            audit_events=int(snapshot["audit_events"]),
            suggestions=suggestions,
        )
