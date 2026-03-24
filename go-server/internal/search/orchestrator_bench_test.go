package search

import (
	"context"
	"fmt"
	"testing"
	"time"

	memoryv1 "github.com/bakebakebakebake/agent-memory/go-server/gen/memory/v1"
	"github.com/bakebakebakebake/agent-memory/go-server/internal/storage"
)

func benchmarkMemory(id string, parentID string) *memoryv1.MemoryItem {
	now := time.Now().UTC().Format(time.RFC3339Nano)
	return &memoryv1.MemoryItem{
		Id:             id,
		Content:        fmt.Sprintf("SQLite keeps agent memory local %s", id),
		MemoryType:     "semantic",
		Embedding:      []float32{0.1, 0.2, 0.3},
		CreatedAt:      now,
		LastAccessed:   now,
		SourceId:       "bench",
		CausalParentId: parentID,
		EntityRefs:     []string{"sqlite", "agent"},
		Tags:           []string{"sqlite", "bench"},
		Layer:          "short_term",
		DecayRate:      0.1,
		TrustScore:     0.8,
		Importance:     0.6,
	}
}

func BenchmarkOrchestratorSearch(b *testing.B) {
	backend, err := storage.New(":memory:")
	if err != nil {
		b.Fatal(err)
	}
	defer backend.Close()

	ctx := context.Background()
	for index := 0; index < 100; index++ {
		parentID := ""
		if index > 0 {
			parentID = fmt.Sprintf("bench-%d", index-1)
		}
		if _, err := backend.AddMemory(ctx, benchmarkMemory(fmt.Sprintf("bench-%d", index), parentID)); err != nil {
			b.Fatal(err)
		}
	}

	orchestrator := New(backend, Config{
		SemanticLimit: 10,
		LexicalLimit:  10,
		EntityLimit:   10,
		DefaultLimit:  5,
		RRFK:          60,
	})

	queryEmbedding := []float32{0.1, 0.2, 0.3}
	entities := []string{"sqlite", "agent"}
	b.ReportAllocs()
	b.ResetTimer()
	for index := 0; index < b.N; index++ {
		if _, err := orchestrator.Search(ctx, "为什么 SQLite 适合 Agent 记忆", queryEmbedding, entities, 5); err != nil {
			b.Fatal(err)
		}
	}
}
