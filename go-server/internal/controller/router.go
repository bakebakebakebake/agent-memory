package controller

import (
	"regexp"
	"sort"
	"strings"
)

type Intent string

const (
	IntentFactual     Intent = "factual"
	IntentTemporal    Intent = "temporal"
	IntentCausal      Intent = "causal"
	IntentExploratory Intent = "exploratory"
	IntentProcedural  Intent = "procedural"
	IntentGeneral     Intent = "general"
)

type RetrievalPlan struct {
	Intent     Intent
	Strategies []string
	Filters    map[string]string
}

var intentPatterns = []struct {
	Intent   Intent
	Patterns []string
}{
	{IntentCausal, []string{"为什么", "为何", "导致", "cause", "caused", "why"}},
	{IntentTemporal, []string{"上周", "最近", "之前", "刚才", "when", "recent", "before"}},
	{IntentProcedural, []string{"如何", "怎么", "步骤", "how to", "how do", "step"}},
	{IntentExploratory, []string{"关于", "all about", "everything about", "related to"}},
	{IntentFactual, []string{"什么是", "谁是", "what is", "who is", "which"}},
}

type Router struct{}

func (Router) Classify(query string) Intent {
	normalized := strings.ToLower(query)
	for _, entry := range intentPatterns {
		for _, pattern := range entry.Patterns {
			if strings.Contains(normalized, pattern) {
				return entry.Intent
			}
		}
	}
	return IntentGeneral
}

func (router Router) Plan(query string) RetrievalPlan {
	intent := router.Classify(query)
	switch intent {
	case IntentFactual:
		return RetrievalPlan{Intent: intent, Strategies: []string{"semantic", "entity", "full_text"}, Filters: map[string]string{}}
	case IntentTemporal:
		return RetrievalPlan{Intent: intent, Strategies: []string{"semantic", "full_text"}, Filters: map[string]string{"sort": "recency"}}
	case IntentCausal:
		return RetrievalPlan{Intent: intent, Strategies: []string{"semantic", "full_text", "causal_trace"}, Filters: map[string]string{}}
	case IntentExploratory:
		return RetrievalPlan{Intent: intent, Strategies: []string{"entity", "semantic", "full_text"}, Filters: map[string]string{}}
	case IntentProcedural:
		return RetrievalPlan{Intent: intent, Strategies: []string{"semantic", "full_text"}, Filters: map[string]string{"memory_type": "procedural"}}
	default:
		return RetrievalPlan{Intent: intent, Strategies: []string{"semantic", "full_text"}, Filters: map[string]string{}}
	}
}

func ReciprocalRankFusion(rankings map[string][]string, k int) map[string]float64 {
	scores := map[string]float64{}
	for _, rankedIDs := range rankings {
		for rank, itemID := range rankedIDs {
			scores[itemID] += 1.0 / float64(k+rank+1)
		}
	}
	ordered := make([]struct {
		ID    string
		Score float64
	}, 0, len(scores))
	for id, score := range scores {
		ordered = append(ordered, struct {
			ID    string
			Score float64
		}{ID: id, Score: score})
	}
	sort.Slice(ordered, func(i, j int) bool { return ordered[i].Score > ordered[j].Score })
	output := make(map[string]float64, len(ordered))
	for _, item := range ordered {
		output[item.ID] = item.Score
	}
	return output
}

var intentMarkerPattern = regexp.MustCompile(`(?i)(为什么|为何|导致|what is|who is|how to|how do|all about|everything about)`)

func StripIntentMarkers(query string) string {
	return strings.TrimSpace(intentMarkerPattern.ReplaceAllString(query, " "))
}
