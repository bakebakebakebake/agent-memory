from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
import re
from typing import Any

from agent_memory.extraction.prompts import CONFLICT_JUDGE_PROMPT
from agent_memory.llm.base import LLMClient
from agent_memory.models import ConflictRecord, ConflictResolution, MemoryItem
from agent_memory.storage.sqlite_backend import SQLiteBackend


NEGATION_MARKERS = ("不", "没", "不是", "不会", "never", "not", "no ")
PREFERENCE_MARKERS = ("喜欢", "偏好", "prefer", "prefers", "using", "uses", "选择", "selected")
CONFLICT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "label": {"type": "string", "enum": ["contradicts", "supersedes", "supports", "related", "none"]},
        "confidence": {"type": "number"},
        "reason": {"type": "string"},
    },
    "required": ["label", "confidence", "reason"],
    "additionalProperties": False,
}


@dataclass(slots=True)
class ConflictDetector:
    backend: SQLiteBackend
    llm_client: LLMClient | None = None

    def detect(self, candidate: MemoryItem, limit: int = 10) -> list[ConflictRecord]:
        vector_hits = self.backend.search_by_vector(candidate.embedding, limit=limit)
        conflicts: list[ConflictRecord] = []
        for existing, similarity in vector_hits:
            if existing.id == candidate.id:
                continue
            if self.backend.relation_exists_between(
                candidate.id,
                existing.id,
                relation_types=["contradicts", "supersedes"],
            ):
                continue
            label, confidence, reason = self._judge_relationship(candidate, existing, similarity)
            if label not in {"contradicts", "supersedes"} or confidence < 0.55:
                continue
            conflicts.append(
                ConflictRecord(
                    existing_id=existing.id,
                    candidate_id=candidate.id,
                    confidence=confidence,
                    resolution=ConflictResolution.SUPERSEDE if label == "supersedes" else ConflictResolution.KEEP_BOTH,
                    reason=reason,
                )
            )
        conflicts.sort(key=lambda item: item.confidence, reverse=True)
        return conflicts

    def _judge_relationship(self, candidate: MemoryItem, existing: MemoryItem, similarity: float) -> tuple[str, float, str]:
        heuristic_confidence = self._contradiction_confidence(candidate.content, existing.content, similarity)
        heuristic_label = "contradicts" if heuristic_confidence >= 0.55 else "none"
        heuristic_reason = "Heuristic semantic overlap and polarity mismatch."
        if self.llm_client is None or similarity < 0.4:
            return heuristic_label, heuristic_confidence, heuristic_reason
        try:
            response = self.llm_client.generate_json(
                prompt=(
                    f"Memory A: {existing.content}\n"
                    f"Memory B: {candidate.content}\n"
                    "Decide the relationship."
                ),
                schema=CONFLICT_SCHEMA,
                schema_name="memory_conflict_judgement",
                system_prompt=CONFLICT_JUDGE_PROMPT,
            )
        except Exception:
            return heuristic_label, heuristic_confidence, heuristic_reason
        label = str(response.get("label", heuristic_label))
        confidence = float(response.get("confidence", heuristic_confidence))
        reason = str(response.get("reason", heuristic_reason))
        return label, confidence, reason

    def _contradiction_confidence(self, left: str, right: str, similarity: float) -> float:
        left_norm = self._normalize(left)
        right_norm = self._normalize(right)
        ratio = SequenceMatcher(None, left_norm, right_norm).ratio()
        left_negative = any(marker in left_norm for marker in NEGATION_MARKERS)
        right_negative = any(marker in right_norm for marker in NEGATION_MARKERS)
        polarity_bonus = 0.25 if left_negative != right_negative else 0.0
        preference_bonus = 0.15 if any(marker in left_norm or marker in right_norm for marker in PREFERENCE_MARKERS) else 0.0
        return min(1.0, similarity * 0.45 + ratio * 0.25 + polarity_bonus + preference_bonus)

    def _normalize(self, text: str) -> str:
        return " ".join(re.findall(r"[\w\u4e00-\u9fff]+", text.lower()))
