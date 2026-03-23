from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class TrustScorer:
    recency_weight: float = 0.15
    corroboration_weight: float = 0.15
    contradiction_weight: float = 0.2
    source_weight: float = 0.5

    def score(
        self,
        *,
        source_reliability: float,
        corroboration_count: int = 0,
        contradiction_count: int = 0,
        age_days: float = 0.0,
    ) -> float:
        recency_bonus = max(0.0, 1.0 - min(age_days, 90.0) / 90.0)
        corroboration_bonus = min(corroboration_count, 5) / 5.0
        contradiction_penalty = min(contradiction_count, 5) / 5.0
        raw_score = (
            source_reliability * self.source_weight
            + recency_bonus * self.recency_weight
            + corroboration_bonus * self.corroboration_weight
            - contradiction_penalty * self.contradiction_weight
        )
        return max(0.0, min(1.0, raw_score))

