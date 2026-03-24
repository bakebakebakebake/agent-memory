package controller

import "testing"

func TestTrustScorer(t *testing.T) {
	scorer := NewTrustScorer()
	score := scorer.Score(0.8, 2, 0, 5)
	if score <= 0.5 {
		t.Fatalf("expected score above 0.5, got %f", score)
	}
}

func TestTrustScorerBoundsAndCaps(t *testing.T) {
	scorer := NewTrustScorer()

	if scorer.Score(0.7, 10, 0, 5) != scorer.Score(0.7, 5, 0, 5) {
		t.Fatal("expected corroboration to clamp at five supporting signals")
	}
	if scorer.Score(0.7, 0, 10, 5) != scorer.Score(0.7, 0, 5, 5) {
		t.Fatal("expected contradiction penalty to clamp at five signals")
	}
	if scorer.Score(0.8, 0, 0, 120) != scorer.Score(0.8, 0, 0, 90) {
		t.Fatal("expected recency bonus to stop decreasing after 90 days")
	}
	if scorer.Score(3.0, 10, 0, 0) != 1 {
		t.Fatal("expected upper bound clamp at 1")
	}
	if scorer.Score(-1.0, 0, 10, 120) != 0 {
		t.Fatal("expected lower bound clamp at 0")
	}
}
