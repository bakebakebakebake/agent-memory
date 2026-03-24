package controller

import "testing"

func TestTrustScorer(t *testing.T) {
	scorer := NewTrustScorer()
	score := scorer.Score(0.8, 2, 0, 5)
	if score <= 0.5 {
		t.Fatalf("expected score above 0.5, got %f", score)
	}
}
