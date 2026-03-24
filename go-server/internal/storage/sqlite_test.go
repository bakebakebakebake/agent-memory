package storage

import (
	"context"
	"testing"
	"time"

	memoryv1 "github.com/bakebakebakebake/agent-memory/go-server/gen/memory/v1"
)

func buildMemory(memoryID string, content string, parentID string) *memoryv1.MemoryItem {
	now := time.Now().UTC().Format(time.RFC3339Nano)
	entities := []string{"agent"}
	if content == "SQLite works well for local agent memory" {
		entities = append(entities, "sqlite")
	}
	return &memoryv1.MemoryItem{
		Id:             memoryID,
		Content:        content,
		MemoryType:     "semantic",
		Embedding:      []float32{0.1, 0.2, 0.3},
		CreatedAt:      now,
		LastAccessed:   now,
		SourceId:       "go-test",
		CausalParentId: parentID,
		EntityRefs:     entities,
		Tags:           []string{"test"},
		Layer:          "short_term",
		DecayRate:      0.1,
		TrustScore:     0.75,
		Importance:     0.5,
	}
}

func TestBackendAddGetSearchAndDelete(t *testing.T) {
	backend, err := New(":memory:")
	if err != nil {
		t.Fatal(err)
	}
	defer backend.Close()
	ctx := context.Background()
	stored, err := backend.AddMemory(ctx, buildMemory("m1", "SQLite works well for local agent memory", ""))
	if err != nil {
		t.Fatal(err)
	}
	found, err := backend.GetMemory(ctx, stored.Id)
	if err != nil {
		t.Fatal(err)
	}
	if found == nil || found.Content != stored.Content {
		t.Fatalf("unexpected memory: %#v", found)
	}
	results, err := backend.SearchFullText(ctx, "SQLite", 5, "")
	if err != nil {
		t.Fatal(err)
	}
	if len(results) == 0 || results[0].Item.Id != "m1" {
		t.Fatalf("unexpected full text results: %#v", results)
	}
	deleted, err := backend.SoftDeleteMemory(ctx, "m1")
	if err != nil {
		t.Fatal(err)
	}
	if !deleted {
		t.Fatal("expected delete to succeed")
	}
}
