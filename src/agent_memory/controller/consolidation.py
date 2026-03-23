from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from math import sqrt
from typing import Any

from agent_memory.extraction.prompts import CONSOLIDATION_PROMPT
from agent_memory.llm.base import LLMClient
from agent_memory.models import MemoryDraft, MemoryItem, MemoryType


CONSOLIDATION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "content": {"type": "string"},
        "memory_type": {"type": "string", "enum": ["semantic", "episodic", "procedural"]},
        "importance": {"type": "number"},
        "tags": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["content", "memory_type", "importance", "tags"],
    "additionalProperties": False,
}


@dataclass(slots=True)
class ConsolidationPlanner:
    similarity_threshold: float = 0.9
    recency_window_days: float = 45.0

    def group_by_entities(self, memories: list[MemoryItem]) -> dict[str, list[MemoryItem]]:
        grouped: dict[str, list[MemoryItem]] = defaultdict(list)
        for memory in memories:
            if not memory.entity_refs:
                continue
            grouped[memory.entity_refs[0].lower()].append(memory)
        return {key: value for key, value in grouped.items() if len(value) > 1}

    def find_merge_groups(self, memories: list[MemoryItem]) -> list[list[MemoryItem]]:
        groups: list[list[MemoryItem]] = []
        for entity_memories in self.group_by_entities(memories).values():
            ordered = sorted(entity_memories, key=lambda item: item.created_at)
            current_group: list[MemoryItem] = []
            for memory in ordered:
                if not current_group:
                    current_group = [memory]
                    continue
                if self._should_merge(current_group[-1], memory):
                    current_group.append(memory)
                else:
                    if len(current_group) > 1:
                        groups.append(current_group)
                    current_group = [memory]
            if len(current_group) > 1:
                groups.append(current_group)
        return groups

    def create_merged_draft(
        self,
        memories: list[MemoryItem],
        *,
        source_id: str,
        llm_client: LLMClient | None = None,
    ) -> MemoryDraft:
        if llm_client is not None:
            merged = self._create_merged_draft_with_llm(memories, source_id=source_id, llm_client=llm_client)
            if merged is not None:
                return merged
        return self._create_merged_draft_heuristic(memories, source_id=source_id)

    def _should_merge(self, left: MemoryItem, right: MemoryItem) -> bool:
        age_gap_days = abs((right.created_at - left.created_at).total_seconds()) / 86400.0
        if age_gap_days > self.recency_window_days:
            return False
        if not set(entity.lower() for entity in left.entity_refs) & set(entity.lower() for entity in right.entity_refs):
            return False
        return self._cosine_similarity(left.embedding, right.embedding) >= self.similarity_threshold

    def _create_merged_draft_with_llm(
        self,
        memories: list[MemoryItem],
        *,
        source_id: str,
        llm_client: LLMClient,
    ) -> MemoryDraft | None:
        prompt = "Merge these overlapping memories into one durable memory:\n" + "\n".join(
            f"- {memory.content}" for memory in memories
        )
        response = llm_client.generate_json(
            prompt=prompt,
            schema=CONSOLIDATION_SCHEMA,
            schema_name="memory_consolidation",
            system_prompt=CONSOLIDATION_PROMPT,
        )
        content = str(response.get("content", "")).strip()
        if not content:
            return None
        return MemoryDraft(
            content=content,
            memory_type=MemoryType(str(response.get("memory_type", "semantic"))),
            importance=float(response.get("importance", 0.7)),
            trust_score=max(memory.trust_score for memory in memories),
            source_id=source_id,
            entity_refs=sorted({entity for memory in memories for entity in memory.entity_refs}),
            tags=sorted({tag for memory in memories for tag in memory.tags} | set(response.get("tags", [])) | {"consolidated"}),
        )

    def _create_merged_draft_heuristic(self, memories: list[MemoryItem], *, source_id: str) -> MemoryDraft:
        ordered = sorted(
            memories,
            key=lambda item: (item.importance, item.trust_score, item.created_at),
            reverse=True,
        )
        anchor = ordered[0]
        return MemoryDraft(
            content=anchor.content,
            memory_type=anchor.memory_type,
            importance=max(memory.importance for memory in memories),
            trust_score=max(memory.trust_score for memory in memories),
            source_id=source_id,
            entity_refs=sorted({entity for memory in memories for entity in memory.entity_refs}),
            tags=sorted({tag for memory in memories for tag in memory.tags} | {"consolidated"}),
        )

    def _cosine_similarity(self, left: list[float], right: list[float]) -> float:
        if not left or not right:
            return 0.0
        size = min(len(left), len(right))
        left_trimmed = left[:size]
        right_trimmed = right[:size]
        numerator = sum(a * b for a, b in zip(left_trimmed, right_trimmed, strict=False))
        left_norm = sqrt(sum(a * a for a in left_trimmed))
        right_norm = sqrt(sum(b * b for b in right_trimmed))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return numerator / (left_norm * right_norm)
