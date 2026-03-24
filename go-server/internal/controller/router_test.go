package controller

import "testing"

func TestRouterPlan(t *testing.T) {
	router := Router{}
	plan := router.Plan("为什么用户喜欢 SQLite")
	if plan.Intent != IntentCausal {
		t.Fatalf("expected causal intent, got %s", plan.Intent)
	}
	if len(plan.Strategies) != 3 {
		t.Fatalf("expected 3 strategies, got %d", len(plan.Strategies))
	}
}
