package controller

import (
	"math"

	memoryv1 "github.com/bakebakebakebake/agent-memory/go-server/gen/memory/v1"
)

type ForgettingPolicy struct {
	ShortTermBeta    float64
	LongTermBeta     float64
	PromoteThreshold float64
	DemoteThreshold  float64
}

func NewForgettingPolicy() ForgettingPolicy {
	return ForgettingPolicy{
		ShortTermBeta:    1.2,
		LongTermBeta:     0.8,
		PromoteThreshold: 0.7,
		DemoteThreshold:  0.3,
	}
}

func (policy ForgettingPolicy) EffectiveStrength(memory *memoryv1.MemoryItem, ageDays float64) float64 {
	accessBoost := 1 + math.Log(1+math.Max(float64(memory.AccessCount), 0))
	beta := policy.ShortTermBeta
	if memory.Layer == "long_term" {
		beta = policy.LongTermBeta
	}
	temporalDecay := math.Exp(-memory.DecayRate * math.Pow(ageDays, beta))
	return memory.Importance * memory.TrustScore * accessBoost * temporalDecay
}

func (policy ForgettingPolicy) NextLayer(memory *memoryv1.MemoryItem, ageDays float64) string {
	strength := policy.EffectiveStrength(memory, ageDays)
	if strength >= policy.PromoteThreshold {
		return "long_term"
	}
	if strength <= policy.DemoteThreshold {
		return "short_term"
	}
	return memory.Layer
}
