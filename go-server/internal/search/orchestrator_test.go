package search

import (
	"context"
	"slices"
	"testing"
	"time"

	memoryv1 "github.com/bakebakebakebake/agent-memory/go-server/gen/memory/v1"
)

type backendStub struct {
	vectorResults   []*memoryv1.SearchResult
	fullTextResults []*memoryv1.SearchResult
	entityResults   []*memoryv1.SearchResult
	ancestors       map[string][]*memoryv1.MemoryItem
	items           map[string]*memoryv1.MemoryItem
	touched         []string
	traceSeeds      []string
}

func (stub *backendStub) SearchByVector(context.Context, []float32, int32, string) ([]*memoryv1.SearchResult, error) {
	return stub.vectorResults, nil
}

func (stub *backendStub) SearchFullText(context.Context, string, int32, string) ([]*memoryv1.SearchResult, error) {
	return stub.fullTextResults, nil
}

func (stub *backendStub) SearchByEntities(context.Context, []string, int32, string) ([]*memoryv1.SearchResult, error) {
	return stub.entityResults, nil
}

func (stub *backendStub) TraceAncestors(_ context.Context, memoryID string, _ int32) ([]*memoryv1.MemoryItem, error) {
	stub.traceSeeds = append(stub.traceSeeds, memoryID)
	return stub.ancestors[memoryID], nil
}

func (stub *backendStub) GetMemory(_ context.Context, memoryID string) (*memoryv1.MemoryItem, error) {
	return stub.items[memoryID], nil
}

func (stub *backendStub) TouchMemory(_ context.Context, memoryID string) error {
	stub.touched = append(stub.touched, memoryID)
	return nil
}

func newResult(item *memoryv1.MemoryItem, score float64, matchedBy ...string) *memoryv1.SearchResult {
	return &memoryv1.SearchResult{Item: item, Score: score, MatchedBy: matchedBy}
}

func newItem(id string, createdAt time.Time) *memoryv1.MemoryItem {
	return &memoryv1.MemoryItem{
		Id:           id,
		Content:      id + " content",
		MemoryType:   "semantic",
		Embedding:    []float32{0.1, 0.2, 0.3},
		CreatedAt:    createdAt.UTC().Format(time.RFC3339Nano),
		LastAccessed: createdAt.UTC().Format(time.RFC3339Nano),
		TrustScore:   0.8,
		Importance:   0.6,
		Layer:        "short_term",
		DecayRate:    0.1,
		SourceId:     "test",
	}
}

func TestOrchestratorSearchFusesStrategiesAndTouchesMemories(t *testing.T) {
	now := time.Now()
	item1 := newItem("m1", now.Add(-time.Minute))
	item2 := newItem("m2", now)
	stub := &backendStub{
		vectorResults: []*memoryv1.SearchResult{
			newResult(item1, 0.9, "semantic"),
			newResult(item2, 0.8, "semantic"),
		},
		fullTextResults: []*memoryv1.SearchResult{
			newResult(item2, 1.0, "full_text"),
			newResult(item1, 0.7, "full_text"),
		},
		entityResults: []*memoryv1.SearchResult{
			newResult(item2, 1.0, "entity"),
		},
		items: map[string]*memoryv1.MemoryItem{"m1": item1, "m2": item2},
	}
	orchestrator := New(stub, Config{SemanticLimit: 10, LexicalLimit: 10, EntityLimit: 10, DefaultLimit: 5, RRFK: 60})

	results, err := orchestrator.Search(context.Background(), "what is SQLite", []float32{0.1, 0.2, 0.3}, []string{"sqlite"}, 5)
	if err != nil {
		t.Fatal(err)
	}
	if len(results) != 2 {
		t.Fatalf("expected 2 results, got %d", len(results))
	}
	if results[0].Item.Id != "m2" {
		t.Fatalf("expected m2 to win fused ranking, got %#v", results)
	}
	if !slices.Equal(results[0].MatchedBy, []string{"entity", "full_text", "semantic"}) {
		t.Fatalf("unexpected matched_by set: %#v", results[0].MatchedBy)
	}
	if !slices.Equal(stub.touched, []string{"m2", "m1"}) {
		t.Fatalf("unexpected touched order: %#v", stub.touched)
	}
}

func TestOrchestratorUsesLexicalSeedForCausalTraceFallback(t *testing.T) {
	now := time.Now()
	child := newItem("child", now)
	parent := newItem("parent", now.Add(-time.Hour))
	stub := &backendStub{
		fullTextResults: []*memoryv1.SearchResult{
			newResult(child, 1.0, "full_text"),
		},
		ancestors: map[string][]*memoryv1.MemoryItem{
			"child": {parent},
		},
		items: map[string]*memoryv1.MemoryItem{"child": child, "parent": parent},
	}
	orchestrator := New(stub, Config{SemanticLimit: 10, LexicalLimit: 10, EntityLimit: 10, DefaultLimit: 5, RRFK: 60})

	results, err := orchestrator.Search(context.Background(), "为什么选择 SQLite", []float32{0.1, 0.2, 0.3}, nil, 5)
	if err != nil {
		t.Fatal(err)
	}
	if !slices.Equal(stub.traceSeeds, []string{"child"}) {
		t.Fatalf("unexpected trace seeds: %#v", stub.traceSeeds)
	}
	if len(results) != 2 {
		t.Fatalf("expected traced result to join output, got %#v", results)
	}
	if results[0].Item.Id != "parent" && results[1].Item.Id != "parent" {
		t.Fatalf("expected parent in output, got %#v", results)
	}
	for _, result := range results {
		if result.Item.Id == "parent" && !slices.Equal(result.MatchedBy, []string{"causal_trace"}) {
			t.Fatalf("unexpected matched_by for parent: %#v", result.MatchedBy)
		}
	}
}

func TestOrchestratorTemporalSortPrefersRecencyOnTie(t *testing.T) {
	oldItem := newItem("old", time.Now().Add(-time.Hour))
	newerItem := newItem("new", time.Now())
	stub := &backendStub{
		vectorResults: []*memoryv1.SearchResult{
			newResult(oldItem, 0.9, "semantic"),
			newResult(newerItem, 0.8, "semantic"),
		},
		fullTextResults: []*memoryv1.SearchResult{
			newResult(newerItem, 1.0, "full_text"),
			newResult(oldItem, 0.7, "full_text"),
		},
		items: map[string]*memoryv1.MemoryItem{"old": oldItem, "new": newerItem},
	}
	orchestrator := New(stub, Config{SemanticLimit: 10, LexicalLimit: 10, EntityLimit: 10, DefaultLimit: 5, RRFK: 60})

	results, err := orchestrator.Search(context.Background(), "最近的 SQLite 记录", []float32{0.1, 0.2, 0.3}, nil, 5)
	if err != nil {
		t.Fatal(err)
	}
	if len(results) != 2 || results[0].Item.Id != "new" {
		t.Fatalf("expected newer record first on tie, got %#v", results)
	}
}
