from __future__ import annotations

from dataclasses import dataclass
from math import exp, log

from agent_memory.models import MemoryItem, MemoryLayer


@dataclass(slots=True)
class ForgettingPolicy:
    short_term_beta: float = 1.2
    long_term_beta: float = 0.8
    promote_threshold: float = 0.7
    demote_threshold: float = 0.3

    def effective_strength(self, memory: MemoryItem, age_days: float) -> float:
        access_boost = 1 + log(1 + max(memory.access_count, 0))
        beta = self.long_term_beta if memory.layer is MemoryLayer.LONG_TERM else self.short_term_beta
        temporal_decay = exp(-memory.decay_rate * (age_days**beta))
        return memory.importance * memory.trust_score * access_boost * temporal_decay

    def next_layer(self, memory: MemoryItem, age_days: float) -> MemoryLayer:
        strength = self.effective_strength(memory, age_days=age_days)
        if strength >= self.promote_threshold:
            return MemoryLayer.LONG_TERM
        if strength <= self.demote_threshold:
            return MemoryLayer.SHORT_TERM
        return memory.layer

