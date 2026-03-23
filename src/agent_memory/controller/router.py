from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import re

from agent_memory.models import QueryIntent, RetrievalPlan


INTENT_PATTERNS: list[tuple[QueryIntent, tuple[str, ...]]] = [
    (QueryIntent.CAUSAL, ("为什么", "为何", "导致", "cause", "caused", "why")),
    (QueryIntent.TEMPORAL, ("上周", "最近", "之前", "刚才", "when", "recent", "before")),
    (QueryIntent.PROCEDURAL, ("如何", "怎么", "步骤", "how to", "how do", "step")),
    (QueryIntent.EXPLORATORY, ("关于", "all about", "everything about", "related to")),
    (QueryIntent.FACTUAL, ("什么是", "谁是", "what is", "who is", "which")),
]


@dataclass(slots=True)
class IntentRouter:
    def classify(self, query: str) -> QueryIntent:
        normalized = query.lower()
        for intent, patterns in INTENT_PATTERNS:
            if any(pattern in normalized for pattern in patterns):
                return intent
        return QueryIntent.GENERAL

    def plan(self, query: str) -> RetrievalPlan:
        intent = self.classify(query)
        if intent is QueryIntent.FACTUAL:
            return RetrievalPlan(intent=intent, strategies=["semantic", "entity", "full_text"])
        if intent is QueryIntent.TEMPORAL:
            return RetrievalPlan(
                intent=intent,
                strategies=["semantic", "full_text"],
                filters={"sort": "recency"},
            )
        if intent is QueryIntent.CAUSAL:
            return RetrievalPlan(intent=intent, strategies=["semantic", "full_text", "causal_trace"])
        if intent is QueryIntent.EXPLORATORY:
            return RetrievalPlan(intent=intent, strategies=["entity", "semantic", "full_text"])
        if intent is QueryIntent.PROCEDURAL:
            return RetrievalPlan(
                intent=intent,
                strategies=["semantic", "full_text"],
                filters={"memory_type": "procedural"},
            )
        return RetrievalPlan(intent=intent, strategies=["semantic", "full_text"])


def reciprocal_rank_fusion(rankings: dict[str, list[str]], k: int = 60) -> dict[str, float]:
    scores: dict[str, float] = defaultdict(float)
    for ranked_ids in rankings.values():
        for rank, item_id in enumerate(ranked_ids, start=1):
            scores[item_id] += 1.0 / (k + rank)
    return dict(sorted(scores.items(), key=lambda item: item[1], reverse=True))


def strip_intent_markers(query: str) -> str:
    pattern = re.compile(r"(为什么|为何|导致|what is|who is|how to|how do|all about|everything about)", re.IGNORECASE)
    return pattern.sub(" ", query).strip()

