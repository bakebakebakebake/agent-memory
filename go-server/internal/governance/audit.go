package governance

import (
	"context"

	memoryv1 "github.com/bakebakebakebake/agent-memory/go-server/gen/memory/v1"
)

type AuditBackend interface {
	GetAuditEvents(ctx context.Context, limit int32) ([]*memoryv1.AuditEvent, error)
}

func ReadAudit(ctx context.Context, backend AuditBackend, limit int32) ([]*memoryv1.AuditEvent, error) {
	return backend.GetAuditEvents(ctx, limit)
}
