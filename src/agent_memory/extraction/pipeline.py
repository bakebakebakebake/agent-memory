from __future__ import annotations

import re
from typing import Any

from agent_memory.extraction.entity_extractor import EntityExtractor
from agent_memory.extraction.prompts import EXTRACT_FACTS_PROMPT
from agent_memory.llm.base import LLMClient
from agent_memory.models import ConversationTurn, MemoryDraft, MemoryType


PREFERENCE_MARKERS = ("喜欢", "偏好", "需要", "负责", "正在做", "prefer", "need", "working on", "building", "goal", "目标", "because", "因为")
IGNORE_PATTERNS = ("谢谢", "收到", "好的", "ok", "okay", "got it", "明白", "哈哈", "lol")
MEMORY_EXTRACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "memories": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "content": {"type": "string"},
                    "memory_type": {"type": "string", "enum": ["semantic", "episodic", "procedural"]},
                    "importance": {"type": "number"},
                    "trust_score": {"type": "number"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["content", "memory_type", "importance", "trust_score", "tags"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["memories"],
    "additionalProperties": False,
}


class ConversationMemoryPipeline:
    def __init__(self, entity_extractor: EntityExtractor | None = None, llm_client: LLMClient | None = None) -> None:
        self.entity_extractor = entity_extractor or EntityExtractor()
        self.llm_client = llm_client

    def extract(self, turns: list[ConversationTurn], source_id: str) -> list[MemoryDraft]:
        if self.llm_client is not None:
            try:
                drafts = self._extract_with_llm(turns=turns, source_id=source_id)
                if drafts:
                    return drafts
            except Exception:
                pass
        return self._extract_heuristically(turns=turns, source_id=source_id)

    def _extract_with_llm(self, turns: list[ConversationTurn], source_id: str) -> list[MemoryDraft]:
        transcript = "\n".join(f"{turn.role}: {turn.content}" for turn in turns)
        response = self.llm_client.generate_json(
            prompt=f"Conversation:\n{transcript}",
            schema=MEMORY_EXTRACTION_SCHEMA,
            schema_name="memory_extraction",
            system_prompt=EXTRACT_FACTS_PROMPT,
        )
        drafts: list[MemoryDraft] = []
        for item in response.get("memories", []):
            content = str(item.get("content", "")).strip()
            if not content:
                continue
            drafts.append(
                MemoryDraft(
                    content=content,
                    memory_type=MemoryType(str(item.get("memory_type", "semantic"))),
                    importance=float(item.get("importance", 0.5)),
                    trust_score=float(item.get("trust_score", 0.7)),
                    source_id=source_id,
                    entity_refs=self.entity_extractor.extract(content),
                    tags=list(item.get("tags", [])),
                )
            )
        return drafts

    def _extract_heuristically(self, turns: list[ConversationTurn], source_id: str) -> list[MemoryDraft]:
        drafts: list[MemoryDraft] = []
        seen_contents: set[str] = set()
        for turn in turns:
            if turn.role != "user":
                continue
            sentences = [segment.strip() for segment in re.split(r"[。！？!?\.]", turn.content) if segment.strip()]
            for sentence in sentences:
                if len(sentence) < 6:
                    continue
                normalized = sentence.lower()
                if any(pattern in normalized for pattern in IGNORE_PATTERNS):
                    continue
                score = self._sentence_score(normalized)
                if score < 1:
                    continue
                content = sentence.strip()
                if content in seen_contents:
                    continue
                seen_contents.add(content)
                drafts.append(
                    MemoryDraft(
                        content=content,
                        memory_type=MemoryType.PROCEDURAL if self._looks_procedural(normalized) else MemoryType.SEMANTIC,
                        importance=min(1.0, 0.4 + 0.15 * score),
                        trust_score=0.75,
                        source_id=source_id,
                        entity_refs=self.entity_extractor.extract(content),
                        tags=["conversation", turn.role, "heuristic"],
                    )
                )
        return drafts

    def _sentence_score(self, normalized_sentence: str) -> int:
        score = 0
        if any(marker in normalized_sentence for marker in PREFERENCE_MARKERS):
            score += 1
        if any(keyword in normalized_sentence for keyword in ("always", "usually", "habit", "习惯", "偏好", "因为", "reason")):
            score += 1
        if len(normalized_sentence) > 32:
            score += 1
        return score

    def _looks_procedural(self, normalized_sentence: str) -> bool:
        return any(marker in normalized_sentence for marker in ("how to", "步骤", "流程", "先", "然后", "最后"))
