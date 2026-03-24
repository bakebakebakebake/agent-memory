package governance

import (
	"context"

	memoryv1 "github.com/bakebakebakebake/agent-memory/go-server/gen/memory/v1"
)

type HealthBackend interface {
	HealthSnapshot(ctx context.Context) (*memoryv1.HealthSnapshot, error)
}

func ReadHealth(ctx context.Context, backend HealthBackend) (*memoryv1.HealthSnapshot, error) {
	return backend.HealthSnapshot(ctx)
}
