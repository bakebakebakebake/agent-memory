from importlib.metadata import PackageNotFoundError
from importlib.metadata import version

from agent_memory.client import MemoryClient
from agent_memory.models import (
    ConflictRecord,
    ConflictResolution,
    ConversationTurn,
    HealthReport,
    MaintenanceReport,
    MemoryDraft,
    MemoryItem,
    MemoryLayer,
    MemoryType,
    QueryIntent,
    RelationEdge,
    SearchResult,
    TraceReport,
)

__all__ = [
    "ConflictRecord",
    "ConflictResolution",
    "ConversationTurn",
    "HealthReport",
    "MaintenanceReport",
    "MemoryClient",
    "MemoryDraft",
    "MemoryItem",
    "MemoryLayer",
    "MemoryType",
    "QueryIntent",
    "RelationEdge",
    "SearchResult",
    "TraceReport",
]

try:
    __version__ = version("agent-memory-engine")
except PackageNotFoundError:
    __version__ = "0.0.0"
