package controller

type TrustScorer struct {
	RecencyWeight       float64
	CorroborationWeight float64
	ContradictionWeight float64
	SourceWeight        float64
}

func NewTrustScorer() TrustScorer {
	return TrustScorer{
		RecencyWeight:       0.15,
		CorroborationWeight: 0.15,
		ContradictionWeight: 0.2,
		SourceWeight:        0.5,
	}
}

func (scorer TrustScorer) Score(sourceReliability float64, corroborationCount int, contradictionCount int, ageDays float64) float64 {
	recencyBonus := 1.0 - min(ageDays, 90.0)/90.0
	if recencyBonus < 0 {
		recencyBonus = 0
	}
	corroborationBonus := min(float64(corroborationCount), 5) / 5.0
	contradictionPenalty := min(float64(contradictionCount), 5) / 5.0
	rawScore := sourceReliability*scorer.SourceWeight +
		recencyBonus*scorer.RecencyWeight +
		corroborationBonus*scorer.CorroborationWeight -
		contradictionPenalty*scorer.ContradictionWeight
	if rawScore < 0 {
		return 0
	}
	if rawScore > 1 {
		return 1
	}
	return rawScore
}

func min(left float64, right float64) float64 {
	if left < right {
		return left
	}
	return right
}
