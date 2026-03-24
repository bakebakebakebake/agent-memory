package grpcserver

import (
	"context"
	"time"

	memoryv1 "github.com/bakebakebakebake/agent-memory/go-server/gen/memory/v1"
	"github.com/bakebakebakebake/agent-memory/go-server/internal/observability"
	"github.com/bakebakebakebake/agent-memory/go-server/internal/search"
	"github.com/bakebakebakebake/agent-memory/go-server/internal/storage"
)

type Server struct {
	memoryv1.UnimplementedStorageServiceServer
	backend      *storage.Backend
	orchestrator *search.Orchestrator
	metrics      *observability.Metrics
}

func New(backend *storage.Backend, orchestrator *search.Orchestrator, metrics *observability.Metrics) *Server {
	return &Server{backend: backend, orchestrator: orchestrator, metrics: metrics}
}

func (server *Server) AddMemory(ctx context.Context, request *memoryv1.AddMemoryRequest) (*memoryv1.AddMemoryResponse, error) {
	start := time.Now()
	item, err := server.backend.AddMemory(ctx, request.Item)
	if err != nil {
		return nil, err
	}
	server.observeStore("grpc", start)
	server.refreshMemoryTotal(ctx)
	return &memoryv1.AddMemoryResponse{Item: item}, nil
}

func (server *Server) GetMemory(ctx context.Context, request *memoryv1.GetMemoryRequest) (*memoryv1.GetMemoryResponse, error) {
	item, err := server.backend.GetMemory(ctx, request.MemoryId)
	if err != nil {
		return nil, err
	}
	return &memoryv1.GetMemoryResponse{Found: item != nil, Item: item}, nil
}

func (server *Server) UpdateMemory(ctx context.Context, request *memoryv1.UpdateMemoryRequest) (*memoryv1.UpdateMemoryResponse, error) {
	start := time.Now()
	item, err := server.backend.UpdateMemory(ctx, request.Item)
	if err != nil {
		return nil, err
	}
	server.observeStore("grpc", start)
	return &memoryv1.UpdateMemoryResponse{Item: item}, nil
}

func (server *Server) DeleteMemory(ctx context.Context, request *memoryv1.DeleteMemoryRequest) (*memoryv1.DeletedResponse, error) {
	start := time.Now()
	deleted, err := server.backend.SoftDeleteMemory(ctx, request.MemoryId)
	if err != nil {
		return nil, err
	}
	server.observeStore("grpc", start)
	server.refreshMemoryTotal(ctx)
	return &memoryv1.DeletedResponse{Deleted: deleted}, nil
}

func (server *Server) SearchQuery(ctx context.Context, request *memoryv1.SearchQueryRequest) (*memoryv1.SearchResultList, error) {
	start := time.Now()
	results, err := server.orchestrator.Search(ctx, request.Query, request.Embedding, request.Entities, request.Limit)
	if err != nil {
		return nil, err
	}
	server.observeSearch("grpc", "fused", start)
	return &memoryv1.SearchResultList{Results: results}, nil
}

func (server *Server) SearchFullText(ctx context.Context, request *memoryv1.SearchFullTextRequest) (*memoryv1.SearchResultList, error) {
	start := time.Now()
	results, err := server.backend.SearchFullText(ctx, request.Query, request.Limit, request.MemoryType)
	if err != nil {
		return nil, err
	}
	server.observeSearch("grpc", "full_text", start)
	return &memoryv1.SearchResultList{Results: results}, nil
}

func (server *Server) SearchByEntities(ctx context.Context, request *memoryv1.SearchByEntitiesRequest) (*memoryv1.SearchResultList, error) {
	start := time.Now()
	results, err := server.backend.SearchByEntities(ctx, request.Entities, request.Limit, request.MemoryType)
	if err != nil {
		return nil, err
	}
	server.observeSearch("grpc", "entity", start)
	return &memoryv1.SearchResultList{Results: results}, nil
}

func (server *Server) SearchByVector(ctx context.Context, request *memoryv1.SearchByVectorRequest) (*memoryv1.SearchResultList, error) {
	start := time.Now()
	results, err := server.backend.SearchByVector(ctx, request.Embedding, request.Limit, request.MemoryType)
	if err != nil {
		return nil, err
	}
	server.observeSearch("grpc", "semantic", start)
	return &memoryv1.SearchResultList{Results: results}, nil
}

func (server *Server) TouchMemory(ctx context.Context, request *memoryv1.TouchMemoryRequest) (*memoryv1.BoolResponse, error) {
	if err := server.backend.TouchMemory(ctx, request.MemoryId); err != nil {
		return nil, err
	}
	return &memoryv1.BoolResponse{Value: true}, nil
}

func (server *Server) TraceAncestors(ctx context.Context, request *memoryv1.TraceAncestorsRequest) (*memoryv1.MemoryList, error) {
	items, err := server.backend.TraceAncestors(ctx, request.MemoryId, request.MaxDepth)
	if err != nil {
		return nil, err
	}
	return &memoryv1.MemoryList{Items: items}, nil
}

func (server *Server) TraceDescendants(ctx context.Context, request *memoryv1.TraceDescendantsRequest) (*memoryv1.MemoryList, error) {
	items, err := server.backend.TraceDescendants(ctx, request.MemoryId, request.MaxDepth)
	if err != nil {
		return nil, err
	}
	return &memoryv1.MemoryList{Items: items}, nil
}

func (server *Server) ListMemories(ctx context.Context, request *memoryv1.ListMemoriesRequest) (*memoryv1.MemoryList, error) {
	items, err := server.backend.ListMemories(ctx, request.IncludeDeleted)
	if err != nil {
		return nil, err
	}
	return &memoryv1.MemoryList{Items: items}, nil
}

func (server *Server) AddRelation(ctx context.Context, request *memoryv1.AddRelationRequest) (*memoryv1.CreatedResponse, error) {
	created, err := server.backend.AddRelation(ctx, request.Edge)
	if err != nil {
		return nil, err
	}
	if created && request.Edge != nil && request.Edge.RelationType == "contradicts" && server.metrics != nil {
		server.metrics.ConflictsDetected.Inc()
	}
	return &memoryv1.CreatedResponse{Created: created}, nil
}

func (server *Server) ListRelations(ctx context.Context, request *memoryv1.ListRelationsRequest) (*memoryv1.RelationList, error) {
	items, err := server.backend.ListRelations(ctx, request.MemoryId)
	if err != nil {
		return nil, err
	}
	return &memoryv1.RelationList{Items: items}, nil
}

func (server *Server) RelationExists(ctx context.Context, request *memoryv1.RelationExistsRequest) (*memoryv1.BoolResponse, error) {
	exists, err := server.backend.RelationExistsBetween(ctx, request.LeftId, request.RightId, request.RelationTypes)
	if err != nil {
		return nil, err
	}
	return &memoryv1.BoolResponse{Value: exists}, nil
}

func (server *Server) GetEvolutionEvents(ctx context.Context, request *memoryv1.GetEvolutionEventsRequest) (*memoryv1.EvolutionEventList, error) {
	items, err := server.backend.GetEvolutionEvents(ctx, request.MemoryId, request.Limit)
	if err != nil {
		return nil, err
	}
	return &memoryv1.EvolutionEventList{Items: items}, nil
}

func (server *Server) GetAuditEvents(ctx context.Context, request *memoryv1.GetAuditEventsRequest) (*memoryv1.AuditEventList, error) {
	items, err := server.backend.GetAuditEvents(ctx, request.Limit)
	if err != nil {
		return nil, err
	}
	return &memoryv1.AuditEventList{Items: items}, nil
}

func (server *Server) HealthCheck(ctx context.Context, _ *memoryv1.HealthCheckRequest) (*memoryv1.HealthCheckResponse, error) {
	snapshot, err := server.backend.HealthSnapshot(ctx)
	if err != nil {
		return nil, err
	}
	if server.metrics != nil {
		server.metrics.MemoryTotal.Set(float64(snapshot.TotalMemories))
	}
	return &memoryv1.HealthCheckResponse{Snapshot: snapshot}, nil
}

func (server *Server) observeStore(transport string, start time.Time) {
	if server.metrics != nil {
		server.metrics.StoreDuration.WithLabelValues(transport).Observe(time.Since(start).Seconds())
	}
}

func (server *Server) observeSearch(transport string, strategy string, start time.Time) {
	if server.metrics != nil {
		server.metrics.SearchDuration.WithLabelValues(transport, strategy).Observe(time.Since(start).Seconds())
	}
}

func (server *Server) refreshMemoryTotal(ctx context.Context) {
	if server.metrics == nil {
		return
	}
	snapshot, err := server.backend.HealthSnapshot(ctx)
	if err == nil {
		server.metrics.MemoryTotal.Set(float64(snapshot.TotalMemories))
	}
}
