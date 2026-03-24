package governance

import (
	"context"
	"encoding/json"
	"os"

	memoryv1 "github.com/bakebakebakebake/agent-memory/go-server/gen/memory/v1"
)

type ExportBackend interface {
	ListMemories(ctx context.Context, includeDeleted bool) ([]*memoryv1.MemoryItem, error)
	ListRelations(ctx context.Context, memoryID string) ([]*memoryv1.RelationEdge, error)
}

func ExportJSONL(ctx context.Context, backend ExportBackend, path string) (int, error) {
	file, err := os.Create(path)
	if err != nil {
		return 0, err
	}
	defer file.Close()
	count := 0
	memories, err := backend.ListMemories(ctx, true)
	if err != nil {
		return 0, err
	}
	for _, item := range memories {
		payload, err := json.Marshal(map[string]any{"type": "memory", "payload": item})
		if err != nil {
			return 0, err
		}
		if _, err := file.Write(append(payload, '\n')); err != nil {
			return 0, err
		}
		count++
	}
	relations, err := backend.ListRelations(ctx, "")
	if err != nil {
		return 0, err
	}
	for _, edge := range relations {
		payload, err := json.Marshal(map[string]any{"type": "relation", "payload": edge})
		if err != nil {
			return 0, err
		}
		if _, err := file.Write(append(payload, '\n')); err != nil {
			return 0, err
		}
	}
	return count, nil
}
