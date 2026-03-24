package governance

import (
	"context"
	"os"
	"path/filepath"
	"strings"
	"testing"

	memoryv1 "github.com/bakebakebakebake/agent-memory/go-server/gen/memory/v1"
)

type exportBackendStub struct {
	memories  []*memoryv1.MemoryItem
	relations []*memoryv1.RelationEdge
}

func (stub exportBackendStub) ListMemories(context.Context, bool) ([]*memoryv1.MemoryItem, error) {
	return stub.memories, nil
}

func (stub exportBackendStub) ListRelations(context.Context, string) ([]*memoryv1.RelationEdge, error) {
	return stub.relations, nil
}

func TestExportJSONL(t *testing.T) {
	outputPath := filepath.Join(t.TempDir(), "export.jsonl")
	backend := exportBackendStub{
		memories: []*memoryv1.MemoryItem{
			{Id: "m1", Content: "sqlite", MemoryType: "semantic"},
			{Id: "m2", Content: "go", MemoryType: "semantic"},
		},
		relations: []*memoryv1.RelationEdge{
			{SourceId: "m1", TargetId: "m2", RelationType: "supports"},
		},
	}

	count, err := ExportJSONL(context.Background(), backend, outputPath)
	if err != nil {
		t.Fatal(err)
	}
	if count != 2 {
		t.Fatalf("expected 2 exported memories, got %d", count)
	}
	content, err := os.ReadFile(outputPath)
	if err != nil {
		t.Fatal(err)
	}
	lines := strings.Split(strings.TrimSpace(string(content)), "\n")
	if len(lines) != 3 {
		t.Fatalf("expected 3 jsonl lines, got %d", len(lines))
	}
}
