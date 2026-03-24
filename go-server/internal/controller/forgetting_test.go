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

func TestForgettingPolicyThresholdEdgesAndBetas(t *testing.T) {
	policy := NewForgettingPolicy()

	promote := &memoryv1.MemoryItem{Importance: 0.7, TrustScore: 1, AccessCount: 0, DecayRate: 0, Layer: "short_term"}
	if strength := policy.EffectiveStrength(promote, 0); strength != 0.7 {
		t.Fatalf("expected exact promote threshold strength, got %f", strength)
	}
	if layer := policy.NextLayer(promote, 0); layer != "long_term" {
		t.Fatalf("expected promote edge to become long_term, got %s", layer)
	}

	demote := &memoryv1.MemoryItem{Importance: 0.3, TrustScore: 1, AccessCount: 0, DecayRate: 0, Layer: "long_term"}
	if strength := policy.EffectiveStrength(demote, 0); strength != 0.3 {
		t.Fatalf("expected exact demote threshold strength, got %f", strength)
	}
	if layer := policy.NextLayer(demote, 0); layer != "short_term" {
		t.Fatalf("expected demote edge to become short_term, got %s", layer)
	}

	shortTerm := &memoryv1.MemoryItem{Importance: 0.8, TrustScore: 0.9, AccessCount: 0, DecayRate: 0.05, Layer: "short_term"}
	longTerm := &memoryv1.MemoryItem{Importance: 0.8, TrustScore: 0.9, AccessCount: 0, DecayRate: 0.05, Layer: "long_term"}
	if policy.EffectiveStrength(longTerm, 10) <= policy.EffectiveStrength(shortTerm, 10) {
		t.Fatal("expected long_term beta to decay more slowly")
	}
}
