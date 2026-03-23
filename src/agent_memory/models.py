from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MemoryType(str, Enum):
    SEMANTIC = "semantic"
    EPISODIC = "episodic"
    PROCEDURAL = "procedural"


class MemoryLayer(str, Enum):
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"


class QueryIntent(str, Enum):
    FACTUAL = "factual"
    TEMPORAL = "temporal"
    CAUSAL = "causal"
    EXPLORATORY = "exploratory"
    PROCEDURAL = "procedural"
    GENERAL = "general"


class RelationType(str, Enum):
    DERIVED_FROM = "derived_from"
    SUPERSEDES = "supersedes"
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    RELATED_TO = "related_to"


class ConflictResolution(str, Enum):
    SUPERSEDE = "supersede"
    KEEP_BOTH = "keep_both"
    MANUAL = "manual"


@dataclass(slots=True)
class MemoryItem:
    id: str
    content: str
    memory_type: MemoryType
    embedding: list[float]
    created_at: datetime = field(default_factory=utc_now)
    last_accessed: datetime = field(default_factory=utc_now)
    access_count: int = 0
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    trust_score: float = 0.75
    importance: float = 0.5
    layer: MemoryLayer = MemoryLayer.SHORT_TERM
    decay_rate: float = 0.1
    source_id: str = "manual"
    causal_parent_id: str | None = None
    supersedes_id: str | None = None
    entity_refs: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    deleted_at: datetime | None = None


@dataclass(slots=True)
class MemoryDraft:
    content: str
    memory_type: MemoryType = MemoryType.SEMANTIC
    importance: float = 0.5
    trust_score: float = 0.7
    source_id: str = "conversation"
    causal_parent_id: str | None = None
    supersedes_id: str | None = None
    entity_refs: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ConversationTurn:
    role: str
    content: str
    timestamp: datetime | None = None


@dataclass(slots=True)
class SearchResult:
    item: MemoryItem
    score: float
    matched_by: list[str]


@dataclass(slots=True)
class RetrievalPlan:
    intent: QueryIntent
    strategies: list[str]
    filters: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RelationEdge:
    source_id: str
    target_id: str
    relation_type: RelationType
    created_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class ConflictRecord:
    existing_id: str
    candidate_id: str | None
    confidence: float
    resolution: ConflictResolution
    reason: str


@dataclass(slots=True)
class MaintenanceReport:
    promoted: int = 0
    demoted: int = 0
    decayed: int = 0
    conflicts_found: int = 0
    conflicts_resolved: int = 0
    consolidated: int = 0


@dataclass(slots=True)
class HealthReport:
    total_memories: int
    stale_ratio: float
    orphan_ratio: float
    unresolved_conflicts: int
    average_trust_score: float
    database_size_bytes: int
    audit_events: int
    suggestions: list[str] = field(default_factory=list)


@dataclass(slots=True)
class TraceReport:
    focus: MemoryItem
    ancestors: list[MemoryItem] = field(default_factory=list)
    descendants: list[MemoryItem] = field(default_factory=list)
    relations: list[RelationEdge] = field(default_factory=list)
    evolution_events: list[dict[str, Any]] = field(default_factory=list)
