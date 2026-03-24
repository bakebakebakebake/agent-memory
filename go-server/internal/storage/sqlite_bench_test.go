package storage

import (
	"context"
	"fmt"
	"testing"
	"time"
)

const benchMemoryCount = 100

func newBenchBackend(b testing.TB) *Backend {
	b.Helper()
	backend, err := New(":memory:")
	if err != nil {
		b.Fatal(err)
	}
	b.Cleanup(func() { _ = backend.Close() })
	return backend
}

func populateBenchMemories(b testing.TB, backend *Backend, count int) {
	b.Helper()
	ctx := context.Background()
	for index := 0; index < count; index++ {
		item := buildMemory(fmt.Sprintf("bench-%d", index), fmt.Sprintf("SQLite memory %d for agent benchmarks", index), "")
		item.Embedding = []float32{float32(index%7 + 1), 0.2, 0.3}
		item.Tags = []string{"sqlite", "agent", fmt.Sprintf("tag-%d", index%5)}
		item.EntityRefs = []string{"sqlite", "agent", fmt.Sprintf("entity-%d", index%4)}
		if index > 0 {
			item.CausalParentId = fmt.Sprintf("bench-%d", index-1)
		}
		if _, err := backend.AddMemory(ctx, item); err != nil {
			b.Fatal(err)
		}
	}
}

func BenchmarkAddMemory(b *testing.B) {
	backend := newBenchBackend(b)
	ctx := context.Background()
	b.ReportAllocs()
	b.ResetTimer()
	for index := 0; index < b.N; index++ {
		item := buildMemory(fmt.Sprintf("add-%d", index), fmt.Sprintf("add benchmark %d", index), "")
		item.Embedding = []float32{0.1, 0.2, 0.3}
		if _, err := backend.AddMemory(ctx, item); err != nil {
			b.Fatal(err)
		}
	}
}

func BenchmarkGetMemory(b *testing.B) {
	backend := newBenchBackend(b)
	populateBenchMemories(b, backend, benchMemoryCount)
	ctx := context.Background()
	b.ReportAllocs()
	b.ResetTimer()
	for index := 0; index < b.N; index++ {
		if _, err := backend.GetMemory(ctx, fmt.Sprintf("bench-%d", index%benchMemoryCount)); err != nil {
			b.Fatal(err)
		}
	}
}

func BenchmarkSearchFullText(b *testing.B) {
	backend := newBenchBackend(b)
	populateBenchMemories(b, backend, benchMemoryCount)
	ctx := context.Background()
	b.ReportAllocs()
	b.ResetTimer()
	for index := 0; index < b.N; index++ {
		if _, err := backend.SearchFullText(ctx, "SQLite agent", 10, ""); err != nil {
			b.Fatal(err)
		}
	}
}

func BenchmarkSearchByVector(b *testing.B) {
	backend := newBenchBackend(b)
	populateBenchMemories(b, backend, benchMemoryCount)
	ctx := context.Background()
	query := []float32{0.1, 0.2, 0.3}
	b.ReportAllocs()
	b.ResetTimer()
	for index := 0; index < b.N; index++ {
		if _, err := backend.SearchByVector(ctx, query, 10, ""); err != nil {
			b.Fatal(err)
		}
	}
}

func BenchmarkSearchByEntities(b *testing.B) {
	backend := newBenchBackend(b)
	populateBenchMemories(b, backend, benchMemoryCount)
	ctx := context.Background()
	b.ReportAllocs()
	b.ResetTimer()
	for index := 0; index < b.N; index++ {
		if _, err := backend.SearchByEntities(ctx, []string{"sqlite", "agent"}, 10, ""); err != nil {
			b.Fatal(err)
		}
	}
}

func BenchmarkSoftDeleteMemory(b *testing.B) {
	backend := newBenchBackend(b)
	ctx := context.Background()
	for index := 0; index < b.N; index++ {
		item := buildMemory(fmt.Sprintf("delete-%d", index), fmt.Sprintf("delete benchmark %d", index), "")
		if _, err := backend.AddMemory(ctx, item); err != nil {
			b.Fatal(err)
		}
	}
	b.ReportAllocs()
	b.ResetTimer()
	for index := 0; index < b.N; index++ {
		if _, err := backend.SoftDeleteMemory(ctx, fmt.Sprintf("delete-%d", index)); err != nil {
			b.Fatal(err)
		}
	}
}

func BenchmarkTraceAncestors(b *testing.B) {
	backend := newBenchBackend(b)
	populateBenchMemories(b, backend, benchMemoryCount)
	ctx := context.Background()
	targetID := fmt.Sprintf("bench-%d", benchMemoryCount-1)
	b.ReportAllocs()
	b.ResetTimer()
	for index := 0; index < b.N; index++ {
		if _, err := backend.TraceAncestors(ctx, targetID, 8); err != nil {
			b.Fatal(err)
		}
	}
}

func BenchmarkHealthSnapshot(b *testing.B) {
	backend := newBenchBackend(b)
	populateBenchMemories(b, backend, benchMemoryCount)
	ctx := context.Background()
	staleItem, err := backend.GetMemory(ctx, "bench-0")
	if err != nil {
		b.Fatal(err)
	}
	staleItem.LastAccessed = time.Now().Add(-45 * 24 * time.Hour).UTC().Format(time.RFC3339Nano)
	if _, err := backend.UpdateMemory(ctx, staleItem); err != nil {
		b.Fatal(err)
	}
	b.ReportAllocs()
	b.ResetTimer()
	for index := 0; index < b.N; index++ {
		if _, err := backend.HealthSnapshot(ctx); err != nil {
			b.Fatal(err)
		}
	}
}
