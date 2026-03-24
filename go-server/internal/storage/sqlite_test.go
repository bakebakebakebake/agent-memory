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

func TestBackendUpdateTraceRelationsAndGovernance(t *testing.T) {
	backend, err := New(":memory:")
	if err != nil {
		t.Fatal(err)
	}
	defer backend.Close()

	ctx := context.Background()
	root := buildMemory("root", "SQLite is the storage layer", "")
	child := buildMemory("child", "Go service exposes REST and gRPC", "root")
	leaf := buildMemory("leaf", "The client queries through fused search", "child")
	for _, item := range []*memoryv1.MemoryItem{root, child, leaf} {
		if _, err := backend.AddMemory(ctx, item); err != nil {
			t.Fatal(err)
		}
	}

	child.Content = "Go service exposes REST, gRPC, and auth middleware"
	child.Tags = append(child.Tags, "updated")
	if _, err := backend.UpdateMemory(ctx, child); err != nil {
		t.Fatal(err)
	}
	updated, err := backend.GetMemory(ctx, "child")
	if err != nil {
		t.Fatal(err)
	}
	if updated == nil || updated.Content != child.Content {
		t.Fatalf("unexpected updated memory: %#v", updated)
	}

	ancestors, err := backend.TraceAncestors(ctx, "leaf", 5)
	if err != nil {
		t.Fatal(err)
	}
	if len(ancestors) != 2 || ancestors[0].Id != "child" || ancestors[1].Id != "root" {
		t.Fatalf("unexpected ancestors: %#v", ancestors)
	}

	descendants, err := backend.TraceDescendants(ctx, "root", 5)
	if err != nil {
		t.Fatal(err)
	}
	if len(descendants) != 2 || descendants[0].Id != "child" || descendants[1].Id != "leaf" {
		t.Fatalf("unexpected descendants: %#v", descendants)
	}

	created, err := backend.AddRelation(ctx, &memoryv1.RelationEdge{
		SourceId:     "root",
		TargetId:     "leaf",
		RelationType: "supports",
		CreatedAt:    time.Now().UTC().Format(time.RFC3339Nano),
	})
	if err != nil {
		t.Fatal(err)
	}
	if !created {
		t.Fatal("expected relation to be created")
	}
	exists, err := backend.RelationExistsBetween(ctx, "root", "leaf", []string{"supports"})
	if err != nil {
		t.Fatal(err)
	}
	if !exists {
		t.Fatal("expected relation to exist")
	}
	relations, err := backend.ListRelations(ctx, "leaf")
	if err != nil {
		t.Fatal(err)
	}
	if len(relations) != 1 {
		t.Fatalf("unexpected relations: %#v", relations)
	}

	evolutionEvents, err := backend.GetEvolutionEvents(ctx, "child", 20)
	if err != nil {
		t.Fatal(err)
	}
	if len(evolutionEvents) == 0 {
		t.Fatal("expected evolution events after add/update")
	}
	auditEvents, err := backend.GetAuditEvents(ctx, 20)
	if err != nil {
		t.Fatal(err)
	}
	if len(auditEvents) == 0 {
		t.Fatal("expected audit events after add/update")
	}

	snapshot, err := backend.HealthSnapshot(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if snapshot.TotalMemories != 3 || snapshot.AuditEvents == 0 {
		t.Fatalf("unexpected health snapshot: %#v", snapshot)
	}
}
