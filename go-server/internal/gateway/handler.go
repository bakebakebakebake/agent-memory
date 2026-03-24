package gateway

import (
	"context"
	"encoding/json"
	"log/slog"
	"net/http"
	"runtime"
	"runtime/debug"
	"strconv"
	"strings"
	"time"

	memoryv1 "github.com/bakebakebakebake/agent-memory/go-server/gen/memory/v1"
	"github.com/bakebakebakebake/agent-memory/go-server/internal/config"
	"github.com/bakebakebakebake/agent-memory/go-server/internal/observability"
	"github.com/bakebakebakebake/agent-memory/go-server/internal/search"
	"github.com/bakebakebakebake/agent-memory/go-server/internal/storage"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

type Handler struct {
	backend      *storage.Backend
	orchestrator *search.Orchestrator
	config       config.Config
	metrics      *observability.Metrics
	startedAt    time.Time
}

func NewHandler(backend *storage.Backend, orchestrator *search.Orchestrator, cfg config.Config, metrics *observability.Metrics) *Handler {
	return &Handler{
		backend:      backend,
		orchestrator: orchestrator,
		config:       cfg,
		metrics:      metrics,
		startedAt:    time.Now().UTC(),
	}
}

func (handler *Handler) Routes(logger *slog.Logger) http.Handler {
	mux := http.NewServeMux()
	mux.Handle("/metrics", promhttp.Handler())
	mux.HandleFunc("/health", handler.handleHealth)
	mux.HandleFunc("/api/v1/info", handler.handleInfo)
	mux.HandleFunc("/api/v1/memories", handler.handleMemories)
	mux.HandleFunc("/api/v1/memories/", handler.handleMemoryByID)
	mux.HandleFunc("/api/v1/search/full-text", handler.handleSearchFullText)
	mux.HandleFunc("/api/v1/search/entities", handler.handleSearchEntities)
	mux.HandleFunc("/api/v1/search/vector", handler.handleSearchVector)
	mux.HandleFunc("/api/v1/search/query", handler.handleSearchQuery)
	mux.HandleFunc("/api/v1/touch", handler.handleTouchMemory)
	mux.HandleFunc("/api/v1/trace/ancestors", handler.handleTraceAncestors)
	mux.HandleFunc("/api/v1/trace/descendants", handler.handleTraceDescendants)
	mux.HandleFunc("/api/v1/relations", handler.handleRelations)
	mux.HandleFunc("/api/v1/relations/exists", handler.handleRelationExists)
	mux.HandleFunc("/api/v1/evolution", handler.handleEvolution)
	mux.HandleFunc("/api/v1/audit", handler.handleAudit)
	return withMiddleware(mux, handler.config, logger, handler.metrics)
}

func (handler *Handler) context(request *http.Request) (context.Context, context.CancelFunc) {
	return context.WithTimeout(request.Context(), time.Duration(handler.config.RequestTimeoutS*float64(time.Second)))
}

func (handler *Handler) handleHealth(writer http.ResponseWriter, request *http.Request) {
	ctx, cancel := handler.context(request)
	defer cancel()
	snapshot, err := handler.backend.HealthSnapshot(ctx)
	if err != nil {
		writeError(writer, err)
		return
	}
	handler.metrics.MemoryTotal.Set(float64(snapshot.TotalMemories))
	writeJSON(writer, http.StatusOK, snapshot)
}

func (handler *Handler) handleInfo(writer http.ResponseWriter, _ *http.Request) {
	buildVersion := "dev"
	buildPath := ""
	buildSettings := map[string]string{}
	if info, ok := debug.ReadBuildInfo(); ok {
		if info.Main.Version != "" && info.Main.Version != "(devel)" {
			buildVersion = info.Main.Version
		}
		buildPath = info.Main.Path
		for _, setting := range info.Settings {
			if strings.HasPrefix(setting.Key, "vcs.") {
				buildSettings[setting.Key] = setting.Value
			}
		}
	}

	writeJSON(writer, http.StatusOK, map[string]any{
		"version":            buildVersion,
		"build":              map[string]any{"path": buildPath, "settings": buildSettings},
		"go_version":         runtime.Version(),
		"sqlite_vec_status":  "not_applicable_in_go_server",
		"vector_search_mode": "cosine_scan",
		"started_at":         handler.startedAt.Format(time.RFC3339Nano),
		"uptime_seconds":     time.Since(handler.startedAt).Seconds(),
	})
}

func (handler *Handler) handleMemories(writer http.ResponseWriter, request *http.Request) {
	ctx, cancel := handler.context(request)
	defer cancel()
	switch request.Method {
	case http.MethodPost:
		var item memoryv1.MemoryItem
		if err := json.NewDecoder(request.Body).Decode(&item); err != nil {
			writeJSON(writer, http.StatusBadRequest, map[string]string{"error": err.Error()})
			return
		}
		start := time.Now()
		stored, err := handler.backend.AddMemory(ctx, &item)
		handler.metrics.StoreDuration.WithLabelValues("http").Observe(time.Since(start).Seconds())
		if err != nil {
			writeError(writer, err)
			return
		}
		handler.refreshMemoryTotal(ctx)
		writeJSON(writer, http.StatusCreated, map[string]any{"item": stored})
	case http.MethodGet:
		includeDeleted := request.URL.Query().Get("include_deleted") == "true"
		items, err := handler.backend.ListMemories(ctx, includeDeleted)
		if err != nil {
			writeError(writer, err)
			return
		}
		writeJSON(writer, http.StatusOK, map[string]any{"items": items})
	default:
		writer.WriteHeader(http.StatusMethodNotAllowed)
	}
}

func (handler *Handler) handleMemoryByID(writer http.ResponseWriter, request *http.Request) {
	ctx, cancel := handler.context(request)
	defer cancel()
	memoryID := strings.TrimPrefix(request.URL.Path, "/api/v1/memories/")
	switch request.Method {
	case http.MethodGet:
		item, err := handler.backend.GetMemory(ctx, memoryID)
		if err != nil {
			writeError(writer, err)
			return
		}
		writeJSON(writer, http.StatusOK, map[string]any{"found": item != nil, "item": item})
	case http.MethodPut:
		var item memoryv1.MemoryItem
		if err := json.NewDecoder(request.Body).Decode(&item); err != nil {
			writeJSON(writer, http.StatusBadRequest, map[string]string{"error": err.Error()})
			return
		}
		item.Id = memoryID
		updated, err := handler.backend.UpdateMemory(ctx, &item)
		if err != nil {
			writeError(writer, err)
			return
		}
		writeJSON(writer, http.StatusOK, map[string]any{"item": updated})
	case http.MethodDelete:
		start := time.Now()
		deleted, err := handler.backend.SoftDeleteMemory(ctx, memoryID)
		if err != nil {
			writeError(writer, err)
			return
		}
		handler.metrics.StoreDuration.WithLabelValues("http").Observe(time.Since(start).Seconds())
		handler.refreshMemoryTotal(ctx)
		writeJSON(writer, http.StatusOK, map[string]any{"deleted": deleted})
	default:
		writer.WriteHeader(http.StatusMethodNotAllowed)
	}
}

func (handler *Handler) handleSearchFullText(writer http.ResponseWriter, request *http.Request) {
	var payload struct {
		Query      string `json:"query"`
		Limit      int32  `json:"limit"`
		MemoryType string `json:"memory_type"`
	}
	if err := json.NewDecoder(request.Body).Decode(&payload); err != nil {
		writeJSON(writer, http.StatusBadRequest, map[string]string{"error": err.Error()})
		return
	}
	ctx, cancel := handler.context(request)
	defer cancel()
	start := time.Now()
	results, err := handler.backend.SearchFullText(ctx, payload.Query, payload.Limit, payload.MemoryType)
	handler.metrics.SearchDuration.WithLabelValues("http", "full_text").Observe(time.Since(start).Seconds())
	if err != nil {
		writeError(writer, err)
		return
	}
	writeJSON(writer, http.StatusOK, map[string]any{"results": results})
}

func (handler *Handler) handleSearchEntities(writer http.ResponseWriter, request *http.Request) {
	var payload struct {
		Entities   []string `json:"entities"`
		Limit      int32    `json:"limit"`
		MemoryType string   `json:"memory_type"`
	}
	if err := json.NewDecoder(request.Body).Decode(&payload); err != nil {
		writeJSON(writer, http.StatusBadRequest, map[string]string{"error": err.Error()})
		return
	}
	ctx, cancel := handler.context(request)
	defer cancel()
	start := time.Now()
	results, err := handler.backend.SearchByEntities(ctx, payload.Entities, payload.Limit, payload.MemoryType)
	handler.metrics.SearchDuration.WithLabelValues("http", "entity").Observe(time.Since(start).Seconds())
	if err != nil {
		writeError(writer, err)
		return
	}
	writeJSON(writer, http.StatusOK, map[string]any{"results": results})
}

func (handler *Handler) handleSearchVector(writer http.ResponseWriter, request *http.Request) {
	var payload struct {
		Embedding  []float32 `json:"embedding"`
		Limit      int32     `json:"limit"`
		MemoryType string    `json:"memory_type"`
	}
	if err := json.NewDecoder(request.Body).Decode(&payload); err != nil {
		writeJSON(writer, http.StatusBadRequest, map[string]string{"error": err.Error()})
		return
	}
	ctx, cancel := handler.context(request)
	defer cancel()
	start := time.Now()
	results, err := handler.backend.SearchByVector(ctx, payload.Embedding, payload.Limit, payload.MemoryType)
	handler.metrics.SearchDuration.WithLabelValues("http", "semantic").Observe(time.Since(start).Seconds())
	if err != nil {
		writeError(writer, err)
		return
	}
	writeJSON(writer, http.StatusOK, map[string]any{"results": results})
}

func (handler *Handler) handleSearchQuery(writer http.ResponseWriter, request *http.Request) {
	var payload struct {
		Query     string    `json:"query"`
		Embedding []float32 `json:"embedding"`
		Entities  []string  `json:"entities"`
		Limit     int32     `json:"limit"`
	}
	if err := json.NewDecoder(request.Body).Decode(&payload); err != nil {
		writeJSON(writer, http.StatusBadRequest, map[string]string{"error": err.Error()})
		return
	}
	ctx, cancel := handler.context(request)
	defer cancel()
	start := time.Now()
	results, err := handler.orchestrator.Search(ctx, payload.Query, payload.Embedding, payload.Entities, payload.Limit)
	handler.metrics.SearchDuration.WithLabelValues("http", "fused").Observe(time.Since(start).Seconds())
	if err != nil {
		writeError(writer, err)
		return
	}
	writeJSON(writer, http.StatusOK, map[string]any{"results": results})
}

func (handler *Handler) handleTouchMemory(writer http.ResponseWriter, request *http.Request) {
	var payload struct {
		MemoryID string `json:"memory_id"`
	}
	if err := json.NewDecoder(request.Body).Decode(&payload); err != nil {
		writeJSON(writer, http.StatusBadRequest, map[string]string{"error": err.Error()})
		return
	}
	ctx, cancel := handler.context(request)
	defer cancel()
	if err := handler.backend.TouchMemory(ctx, payload.MemoryID); err != nil {
		writeError(writer, err)
		return
	}
	writeJSON(writer, http.StatusOK, map[string]any{"ok": true})
}

func (handler *Handler) handleTraceAncestors(writer http.ResponseWriter, request *http.Request) {
	ctx, cancel := handler.context(request)
	defer cancel()
	maxDepth, _ := strconv.Atoi(request.URL.Query().Get("max_depth"))
	items, err := handler.backend.TraceAncestors(ctx, request.URL.Query().Get("memory_id"), int32(defaultInt(maxDepth, 10)))
	if err != nil {
		writeError(writer, err)
		return
	}
	writeJSON(writer, http.StatusOK, map[string]any{"items": items})
}

func (handler *Handler) handleTraceDescendants(writer http.ResponseWriter, request *http.Request) {
	ctx, cancel := handler.context(request)
	defer cancel()
	maxDepth, _ := strconv.Atoi(request.URL.Query().Get("max_depth"))
	items, err := handler.backend.TraceDescendants(ctx, request.URL.Query().Get("memory_id"), int32(defaultInt(maxDepth, 10)))
	if err != nil {
		writeError(writer, err)
		return
	}
	writeJSON(writer, http.StatusOK, map[string]any{"items": items})
}

func (handler *Handler) handleRelations(writer http.ResponseWriter, request *http.Request) {
	ctx, cancel := handler.context(request)
	defer cancel()
	switch request.Method {
	case http.MethodGet:
		items, err := handler.backend.ListRelations(ctx, request.URL.Query().Get("memory_id"))
		if err != nil {
			writeError(writer, err)
			return
		}
		writeJSON(writer, http.StatusOK, map[string]any{"items": items})
	case http.MethodPost:
		var edge memoryv1.RelationEdge
		if err := json.NewDecoder(request.Body).Decode(&edge); err != nil {
			writeJSON(writer, http.StatusBadRequest, map[string]string{"error": err.Error()})
			return
		}
		created, err := handler.backend.AddRelation(ctx, &edge)
		if err != nil {
			writeError(writer, err)
			return
		}
		if created && edge.RelationType == "contradicts" {
			handler.metrics.ConflictsDetected.Inc()
		}
		writeJSON(writer, http.StatusCreated, map[string]any{"created": created})
	default:
		writer.WriteHeader(http.StatusMethodNotAllowed)
	}
}

func (handler *Handler) handleRelationExists(writer http.ResponseWriter, request *http.Request) {
	ctx, cancel := handler.context(request)
	defer cancel()
	relationTypes := strings.Split(strings.TrimSpace(request.URL.Query().Get("relation_types")), ",")
	if len(relationTypes) == 1 && relationTypes[0] == "" {
		relationTypes = nil
	}
	exists, err := handler.backend.RelationExistsBetween(ctx, request.URL.Query().Get("left_id"), request.URL.Query().Get("right_id"), relationTypes)
	if err != nil {
		writeError(writer, err)
		return
	}
	writeJSON(writer, http.StatusOK, map[string]any{"exists": exists})
}

func (handler *Handler) handleEvolution(writer http.ResponseWriter, request *http.Request) {
	ctx, cancel := handler.context(request)
	defer cancel()
	limit, _ := strconv.Atoi(request.URL.Query().Get("limit"))
	items, err := handler.backend.GetEvolutionEvents(ctx, request.URL.Query().Get("memory_id"), int32(defaultInt(limit, 100)))
	if err != nil {
		writeError(writer, err)
		return
	}
	writeJSON(writer, http.StatusOK, map[string]any{"items": items})
}

func (handler *Handler) handleAudit(writer http.ResponseWriter, request *http.Request) {
	ctx, cancel := handler.context(request)
	defer cancel()
	limit, _ := strconv.Atoi(request.URL.Query().Get("limit"))
	items, err := handler.backend.GetAuditEvents(ctx, int32(defaultInt(limit, 100)))
	if err != nil {
		writeError(writer, err)
		return
	}
	writeJSON(writer, http.StatusOK, map[string]any{"items": items})
}

func writeJSON(writer http.ResponseWriter, status int, payload any) {
	writer.Header().Set("Content-Type", "application/json")
	writer.WriteHeader(status)
	_ = json.NewEncoder(writer).Encode(payload)
}

func writeError(writer http.ResponseWriter, err error) {
	writeJSON(writer, http.StatusInternalServerError, map[string]string{"error": err.Error()})
}

func defaultInt(value int, fallback int) int {
	if value == 0 {
		return fallback
	}
	return value
}

func (handler *Handler) refreshMemoryTotal(ctx context.Context) {
	snapshot, err := handler.backend.HealthSnapshot(ctx)
	if err == nil {
		handler.metrics.MemoryTotal.Set(float64(snapshot.TotalMemories))
	}
}
