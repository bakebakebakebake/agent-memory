package governance

import (
	"context"
	"testing"

	memoryv1 "github.com/bakebakebakebake/agent-memory/go-server/gen/memory/v1"
)

type healthBackendStub struct {
	snapshot *memoryv1.HealthSnapshot
	err      error
}

func (stub healthBackendStub) HealthSnapshot(context.Context) (*memoryv1.HealthSnapshot, error) {
	return stub.snapshot, stub.err
}

func TestReadHealth(t *testing.T) {
	expected := &memoryv1.HealthSnapshot{
		TotalMemories:       7,
		AverageTrustScore:   0.81,
		UnresolvedConflicts: 1,
		AuditEvents:         9,
	}
	got, err := ReadHealth(context.Background(), healthBackendStub{snapshot: expected})
	if err != nil {
		t.Fatal(err)
	}
	if got.TotalMemories != expected.TotalMemories || got.AverageTrustScore != expected.AverageTrustScore {
		t.Fatalf("unexpected snapshot: %#v", got)
	}
}
