package search

import (
	"context"
	"sort"

	memoryv1 "github.com/bakebakebakebake/agent-memory/go-server/gen/memory/v1"
	"github.com/bakebakebakebake/agent-memory/go-server/internal/controller"
)

type Backend interface {
	SearchByVector(ctx context.Context, embedding []float32, limit int32, memoryType string) ([]*memoryv1.SearchResult, error)
	SearchFullText(ctx context.Context, query string, limit int32, memoryType string) ([]*memoryv1.SearchResult, error)
	SearchByEntities(ctx context.Context, entities []string, limit int32, memoryType string) ([]*memoryv1.SearchResult, error)
	TraceAncestors(ctx context.Context, memoryID string, maxDepth int32) ([]*memoryv1.MemoryItem, error)
	GetMemory(ctx context.Context, memoryID string) (*memoryv1.MemoryItem, error)
	TouchMemory(ctx context.Context, memoryID string) error
}

type Config struct {
	SemanticLimit int32
	LexicalLimit  int32
	EntityLimit   int32
	DefaultLimit  int32
	RRFK          int
}

type Orchestrator struct {
	backend Backend
	router  controller.Router
	config  Config
}

func New(backend Backend, config Config) *Orchestrator {
	return &Orchestrator{backend: backend, router: controller.Router{}, config: config}
}

func (orchestrator *Orchestrator) Search(ctx context.Context, query string, embedding []float32, entities []string, limit int32) ([]*memoryv1.SearchResult, error) {
	if limit == 0 {
		limit = orchestrator.config.DefaultLimit
	}
	plan := orchestrator.router.Plan(query)
	rankings := map[string][]string{}
	resultsByID := map[string]*memoryv1.MemoryItem{}
	matchedBy := map[string]map[string]bool{}
	memoryType := plan.Filters["memory_type"]
	normalizedQuery := controller.StripIntentMarkers(query)
	if normalizedQuery == "" {
		normalizedQuery = query
	}

	for _, strategy := range plan.Strategies {
		switch strategy {
		case "semantic":
			results, err := orchestrator.backend.SearchByVector(ctx, embedding, orchestrator.config.SemanticLimit, memoryType)
			if err != nil {
				return nil, err
			}
			collectResults("semantic", results, rankings, resultsByID, matchedBy)
		case "full_text":
			results, err := orchestrator.backend.SearchFullText(ctx, normalizedQuery, orchestrator.config.LexicalLimit, memoryType)
			if err != nil {
				return nil, err
			}
			collectResults("full_text", results, rankings, resultsByID, matchedBy)
		case "entity":
			results, err := orchestrator.backend.SearchByEntities(ctx, entities, orchestrator.config.EntityLimit, memoryType)
			if err != nil {
				return nil, err
			}
			collectResults("entity", results, rankings, resultsByID, matchedBy)
		case "causal_trace":
			seedIDs := rankings["semantic"]
			if len(seedIDs) == 0 {
				seedIDs = rankings["full_text"]
			}
			traceIDs := []string{}
			for _, seedID := range take(seedIDs, 2) {
				ancestors, err := orchestrator.backend.TraceAncestors(ctx, seedID, 5)
				if err != nil {
					return nil, err
				}
				for _, item := range ancestors {
					resultsByID[item.Id] = item
					ensureMatch(item.Id, matchedBy)["causal_trace"] = true
					traceIDs = append(traceIDs, item.Id)
				}
			}
			if len(traceIDs) > 0 {
				rankings["causal_trace"] = traceIDs
			}
		}
	}

	fused := controller.ReciprocalRankFusion(rankings, orchestrator.config.RRFK)
	finalIDs := make([]string, 0, len(fused))
	for id := range fused {
		finalIDs = append(finalIDs, id)
	}
	if plan.Filters["sort"] == "recency" {
		sort.Slice(finalIDs, func(i, j int) bool {
			left := resultsByID[finalIDs[i]]
			right := resultsByID[finalIDs[j]]
			if fused[finalIDs[i]] == fused[finalIDs[j]] {
				return left.CreatedAt > right.CreatedAt
			}
			return fused[finalIDs[i]] > fused[finalIDs[j]]
		})
	}
	output := []*memoryv1.SearchResult{}
	for _, memoryID := range take(finalIDs, int(limit)) {
		_ = orchestrator.backend.TouchMemory(ctx, memoryID)
		refreshed, err := orchestrator.backend.GetMemory(ctx, memoryID)
		if err != nil {
			return nil, err
		}
		if refreshed == nil {
			continue
		}
		output = append(output, &memoryv1.SearchResult{
			Item:      refreshed,
			Score:     fused[memoryID],
			MatchedBy: flatten(matchedBy[memoryID]),
		})
	}
	return output, nil
}

func collectResults(strategy string, results []*memoryv1.SearchResult, rankings map[string][]string, resultsByID map[string]*memoryv1.MemoryItem, matchedBy map[string]map[string]bool) {
	ids := make([]string, 0, len(results))
	for _, result := range results {
		ids = append(ids, result.Item.Id)
		resultsByID[result.Item.Id] = result.Item
		ensureMatch(result.Item.Id, matchedBy)[strategy] = true
	}
	if len(ids) > 0 {
		rankings[strategy] = ids
	}
}

func ensureMatch(memoryID string, matchedBy map[string]map[string]bool) map[string]bool {
	if matchedBy[memoryID] == nil {
		matchedBy[memoryID] = map[string]bool{}
	}
	return matchedBy[memoryID]
}

func flatten(values map[string]bool) []string {
	output := make([]string, 0, len(values))
	for value := range values {
		output = append(output, value)
	}
	sort.Strings(output)
	return output
}

func take[T any](values []T, limit int) []T {
	if len(values) <= limit {
		return values
	}
	return values[:limit]
}
