package controller

import (
	"testing"

	memoryv1 "github.com/bakebakebakebake/agent-memory/go-server/gen/memory/v1"
)

func TestForgettingPolicyNextLayer(t *testing.T) {
	policy := NewForgettingPolicy()
	item := &memoryv1.MemoryItem{
		Importance:  0.9,
		TrustScore:  0.9,
		AccessCount: 5,
		DecayRate:   0.05,
		Layer:       "short_term",
	}
	if layer := policy.NextLayer(item, 1); layer != "long_term" {
		t.Fatalf("expected long_term, got %s", layer)
	}
}
