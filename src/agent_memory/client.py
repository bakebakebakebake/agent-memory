from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from datetime import datetime, timezone
import uuid

from agent_memory.controller.conflict import ConflictDetector
from agent_memory.controller.consolidation import ConsolidationPlanner
from agent_memory.controller.forgetting import ForgettingPolicy
from agent_memory.config import AgentMemoryConfig
from agent_memory.controller.router import IntentRouter, reciprocal_rank_fusion, strip_intent_markers
from agent_memory.controller.trust import TrustScorer
from agent_memory.embedding.local_provider import LocalEmbeddingProvider
from agent_memory.governance.audit import AuditLogReader
from agent_memory.governance.export import MemoryExporter, MemoryImporter
from agent_memory.governance.health import MemoryHealthMonitor
from agent_memory.extraction.entity_extractor import EntityExtractor
from agent_memory.extraction.pipeline import ConversationMemoryPipeline
from agent_memory.llm.base import LLMClient
from agent_memory.models import (
    ConflictRecord,
    ConversationTurn,
    MaintenanceReport,
    MemoryDraft,
    MemoryItem,
    MemoryLayer,
    MemoryType,
    RelationEdge,
    RelationType,
    SearchResult,
    TraceReport,
)
from agent_memory.storage.sqlite_backend import SQLiteBackend


class MemoryClient:
    def __init__(
        self,
        config: AgentMemoryConfig | None = None,
        backend: SQLiteBackend | None = None,
        embedding_provider: LocalEmbeddingProvider | None = None,
        entity_extractor: EntityExtractor | None = None,
        llm_client: LLMClient | None = None,
    ) -> None:
        self.config = config or AgentMemoryConfig.from_env()
        self.backend = backend or SQLiteBackend(
            self.config.database_path,
            prefer_sqlite_vec=self.config.enable_sqlite_vec,
        )
        self.embedding_provider = embedding_provider or LocalEmbeddingProvider()
        self.entity_extractor = entity_extractor or EntityExtractor()
        self.router = IntentRouter()
        self.llm_client = llm_client
        self.pipeline = ConversationMemoryPipeline(entity_extractor=self.entity_extractor, llm_client=self.llm_client)
        self.turn_model = ConversationTurn
        self.forgetting_policy = ForgettingPolicy()
        self.trust_scorer = TrustScorer()
        self.conflict_detector = ConflictDetector(self.backend, llm_client=self.llm_client)
        self.consolidation_planner = ConsolidationPlanner()
        self.health_monitor = MemoryHealthMonitor(self.backend)
        self.audit_reader = AuditLogReader(self.backend)
        self.exporter = MemoryExporter(self.backend)
        self.importer = MemoryImporter(self.backend)

    def close(self) -> None:
        self.backend.close()

    def add(
        self,
        content: str,
        *,
        source_id: str,
        memory_type: MemoryType | str = MemoryType.SEMANTIC,
        importance: float = 0.5,
        trust_score: float = 0.75,
        tags: list[str] | None = None,
        entity_refs: list[str] | None = None,
        causal_parent_id: str | None = None,
        supersedes_id: str | None = None,
    ) -> MemoryItem:
        memory_type = MemoryType(memory_type)
        embedding = self.embedding_provider.embed([content])[0]
        now = datetime.now(timezone.utc)
        base_trust = self.trust_scorer.score(source_reliability=trust_score)
        item = MemoryItem(
            id=str(uuid.uuid4()),
            content=content,
            memory_type=memory_type,
            embedding=embedding,
            created_at=now,
            last_accessed=now,
            importance=importance,
            trust_score=base_trust,
            source_id=source_id,
            entity_refs=entity_refs or self.entity_extractor.extract(content),
            tags=tags or [],
            causal_parent_id=causal_parent_id,
            supersedes_id=supersedes_id,
        )
        item = self.backend.add_memory(item)
        self._attach_structural_relations(item)
        conflicts = self.detect_conflicts(item)
        if conflicts:
            item, _ = self._apply_conflicts(item, conflicts)
        return item

    def get(self, memory_id: str) -> MemoryItem | None:
        return self.backend.get_memory(memory_id)

    def delete(self, memory_id: str) -> bool:
        return self.backend.soft_delete_memory(memory_id)

    def search(self, query: str, limit: int | None = None) -> list[SearchResult]:
        search_limit = limit or self.config.default_search_limit
        plan = self.router.plan(query)
        rankings: dict[str, list[str]] = {}
        results_by_id: dict[str, MemoryItem] = {}
        matched_by: dict[str, set[str]] = defaultdict(set)
        memory_type = plan.filters.get("memory_type")
        normalized_query = strip_intent_markers(query) or query

        if "semantic" in plan.strategies:
            embedding = self.embedding_provider.embed([normalized_query])[0]
            semantic_results = self.backend.search_by_vector(embedding, limit=self.config.semantic_limit, memory_type=memory_type)
            rankings["semantic"] = [item.id for item, _ in semantic_results]
            for item, _ in semantic_results:
                results_by_id[item.id] = item
                matched_by[item.id].add("semantic")

        if "full_text" in plan.strategies:
            lexical_results = self.backend.search_full_text(normalized_query, limit=self.config.lexical_limit, memory_type=memory_type)
            rankings["full_text"] = [item.id for item, _ in lexical_results]
            for item, _ in lexical_results:
                results_by_id[item.id] = item
                matched_by[item.id].add("full_text")

        if "entity" in plan.strategies:
            entities = self.entity_extractor.extract(normalized_query)
            entity_results = self.backend.search_by_entities(entities, limit=self.config.entity_limit, memory_type=memory_type)
            rankings["entity"] = [item.id for item, _ in entity_results]
            for item, _ in entity_results:
                results_by_id[item.id] = item
                matched_by[item.id].add("entity")

        if "causal_trace" in plan.strategies:
            seed_ids = rankings.get("semantic", [])[:2] or rankings.get("full_text", [])[:2]
            trace_ids: list[str] = []
            for seed_id in seed_ids:
                for ancestor in self.backend.trace_ancestors(seed_id, max_depth=5):
                    results_by_id[ancestor.id] = ancestor
                    matched_by[ancestor.id].add("causal_trace")
                    trace_ids.append(ancestor.id)
            if trace_ids:
                rankings["causal_trace"] = trace_ids

        fused = reciprocal_rank_fusion(rankings, k=self.config.rrf_k)
        final_ids = list(fused.keys())
        if plan.filters.get("sort") == "recency":
            final_ids.sort(
                key=lambda item_id: (
                    fused.get(item_id, 0.0),
                    results_by_id[item_id].created_at,
                ),
                reverse=True,
            )

        output: list[SearchResult] = []
        for memory_id in final_ids[:search_limit]:
            self.backend.touch_memory(memory_id)
            refreshed = self.backend.get_memory(memory_id)
            if refreshed is None:
                continue
            output.append(
                SearchResult(
                    item=refreshed,
                    score=fused.get(memory_id, 0.0),
                    matched_by=sorted(matched_by[memory_id]),
                )
            )
        return output

    def ingest_conversation(self, turns: list[ConversationTurn], source_id: str) -> list[MemoryItem]:
        drafts = self.pipeline.extract(turns, source_id=source_id)
        created: list[MemoryItem] = []
        for draft in drafts:
            created.append(self.add_from_draft(draft))
        return created

    def add_from_draft(self, draft: MemoryDraft) -> MemoryItem:
        return self.add(
            draft.content,
            source_id=draft.source_id,
            memory_type=draft.memory_type,
            importance=draft.importance,
            trust_score=draft.trust_score,
            tags=list(draft.tags),
            entity_refs=list(draft.entity_refs),
            causal_parent_id=draft.causal_parent_id,
            supersedes_id=draft.supersedes_id,
        )

    def update(self, item: MemoryItem, **changes: object) -> MemoryItem:
        if "memory_type" in changes and isinstance(changes["memory_type"], str):
            changes["memory_type"] = MemoryType(changes["memory_type"])
        updated = replace(item, **changes)
        updated = self.backend.update_memory(updated)
        self._attach_structural_relations(updated)
        if "content" in changes or "entity_refs" in changes:
            conflicts = self.detect_conflicts(updated)
            if conflicts:
                updated, _ = self._apply_conflicts(updated, conflicts)
        return updated

    def trace(self, memory_id: str, max_depth: int = 10) -> list[MemoryItem]:
        return self.backend.trace_ancestors(memory_id, max_depth=max_depth)

    def trace_graph(self, memory_id: str, max_depth: int = 10) -> TraceReport:
        focus = self.get(memory_id)
        if focus is None:
            raise ValueError(f"Memory {memory_id} not found")
        return TraceReport(
            focus=focus,
            ancestors=self.backend.trace_ancestors(memory_id, max_depth=max_depth),
            descendants=self.backend.trace_descendants(memory_id, max_depth=max_depth),
            relations=self.backend.list_relations(memory_id),
            evolution_events=self.backend.get_evolution_events(memory_id=memory_id, limit=100),
        )

    def detect_conflicts(self, item: MemoryItem) -> list[ConflictRecord]:
        return self.conflict_detector.detect(item)

    def health(self):
        return self.health_monitor.generate()

    def audit_events(self, limit: int = 50) -> list[dict[str, object]]:
        return self.audit_reader.recent(limit=limit)

    def evolution_events(self, memory_id: str | None = None, limit: int = 50) -> list[dict[str, object]]:
        return self.backend.get_evolution_events(memory_id=memory_id, limit=limit)

    def export_jsonl(self, path: str) -> int:
        return self.exporter.export_jsonl(path)

    def import_jsonl(self, path: str) -> int:
        return self.importer.import_jsonl(path)

    def maintain(self) -> MaintenanceReport:
        report = MaintenanceReport()
        now = datetime.now(timezone.utc)
        for memory in self.backend.list_memories():
            age_days = max((now - memory.last_accessed).total_seconds() / 86400.0, 0.0)
            strength = self.forgetting_policy.effective_strength(memory, age_days=age_days)
            next_layer = self.forgetting_policy.next_layer(memory, age_days=age_days)
            updated = memory
            if next_layer is not memory.layer:
                updated = replace(updated, layer=next_layer)
                if next_layer is MemoryLayer.LONG_TERM:
                    report.promoted += 1
                else:
                    report.demoted += 1
            if strength < 0.1 and age_days > 60:
                if self.backend.soft_delete_memory(memory.id):
                    report.decayed += 1
                continue
            if updated is not memory:
                self.backend.update_memory(updated)
        for memory in self.backend.list_memories():
            conflicts = self.detect_conflicts(memory)
            report.conflicts_found += len(conflicts)
            if conflicts:
                report.conflicts_resolved += self._apply_conflicts(memory, conflicts)[1]
        report.consolidated = self.consolidate()
        return report

    def consolidate(self) -> int:
        memories = self.backend.list_memories()
        groups = self.consolidation_planner.find_merge_groups(memories)
        consolidated = 0
        for index, group in enumerate(groups, start=1):
            primary = max(group, key=lambda item: (item.importance, item.trust_score, item.created_at))
            if any(
                memory.supersedes_id == primary.id and "consolidated" in memory.tags
                for memory in memories
            ):
                continue
            draft = self.consolidation_planner.create_merged_draft(
                group,
                source_id=f"consolidation:{index}",
                llm_client=self.llm_client,
            )
            merged = self.add_from_draft(
                replace(
                    draft,
                    supersedes_id=primary.id,
                    causal_parent_id=primary.causal_parent_id,
                )
            )
            for memory in group:
                if memory.id == primary.id:
                    continue
                self.backend.add_relation(
                    RelationEdge(
                        source_id=merged.id,
                        target_id=memory.id,
                        relation_type=RelationType.SUPERSEDES,
                    )
                )
            consolidated += 1
        return consolidated

    def _attach_structural_relations(self, item: MemoryItem) -> None:
        if item.causal_parent_id:
            self.backend.add_relation(
                RelationEdge(
                    source_id=item.id,
                    target_id=item.causal_parent_id,
                    relation_type=RelationType.DERIVED_FROM,
                )
            )
        if item.supersedes_id:
            self.backend.add_relation(
                RelationEdge(
                    source_id=item.id,
                    target_id=item.supersedes_id,
                    relation_type=RelationType.SUPERSEDES,
                )
            )

    def _apply_conflicts(self, item: MemoryItem, conflicts: list[ConflictRecord]) -> tuple[MemoryItem, int]:
        contradiction_count = 0
        inserted_relations = 0
        for conflict in conflicts:
            contradiction_count += 1
            inserted_relations += int(
                self.backend.add_relation(
                RelationEdge(
                    source_id=item.id,
                    target_id=conflict.existing_id,
                    relation_type=(
                        RelationType.SUPERSEDES
                        if conflict.resolution.value == "supersede"
                        else RelationType.CONTRADICTS
                    ),
                )
            )
            )
        age_days = max((datetime.now(timezone.utc) - item.created_at).total_seconds() / 86400.0, 0.0)
        adjusted_trust = self.trust_scorer.score(
            source_reliability=item.trust_score,
            contradiction_count=contradiction_count,
            age_days=age_days,
        )
        updated = replace(item, trust_score=adjusted_trust)
        return self.backend.update_memory(updated), inserted_relations
