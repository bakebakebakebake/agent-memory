package gateway

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	memoryv1 "github.com/bakebakebakebake/agent-memory/go-server/gen/memory/v1"
	"github.com/bakebakebakebake/agent-memory/go-server/internal/config"
	"github.com/bakebakebakebake/agent-memory/go-server/internal/observability"
	"github.com/bakebakebakebake/agent-memory/go-server/internal/search"
	"github.com/bakebakebakebake/agent-memory/go-server/internal/storage"
	"github.com/golang-jwt/jwt/v5"
)

func TestRoutesExposeMetricsAndHonorAuth(t *testing.T) {
	backend, err := storage.New(":memory:")
	if err != nil {
		t.Fatal(err)
	}
	defer backend.Close()
	metrics := observability.NewMetrics()
	defer unregisterMetrics(metrics)
	logger := slog.New(slog.NewTextHandler(io.Discard, nil))
	cfg := config.Config{
		APIKey:          "test-key",
		JWTSecret:       "test-secret",
		RequestTimeoutS: 1,
		SemanticLimit:   10,
		LexicalLimit:    10,
		EntityLimit:     10,
		DefaultLimit:    5,
		RRFK:            60,
	}
	orchestrator := search.New(backend, search.Config{
		SemanticLimit: 10,
		LexicalLimit:  10,
		EntityLimit:   10,
		DefaultLimit:  5,
		RRFK:          60,
	})
	handler := NewHandler(backend, orchestrator, cfg, metrics)
	server := httptest.NewServer(handler.Routes(logger))
	defer server.Close()

	response, err := http.Get(server.URL + "/health")
	if err != nil {
		t.Fatal(err)
	}
	defer response.Body.Close()
	if response.StatusCode != http.StatusUnauthorized {
		t.Fatalf("expected unauthorized, got %d", response.StatusCode)
	}

	request, err := http.NewRequest(http.MethodGet, server.URL+"/health", nil)
	if err != nil {
		t.Fatal(err)
	}
	request.Header.Set("X-API-Key", "test-key")
	response, err = http.DefaultClient.Do(request)
	if err != nil {
		t.Fatal(err)
	}
	defer response.Body.Close()
	if response.StatusCode != http.StatusOK {
		t.Fatalf("expected 200, got %d", response.StatusCode)
	}
	var health map[string]any
	if err := json.NewDecoder(response.Body).Decode(&health); err != nil {
		t.Fatal(err)
	}
	if len(health) != 0 && fmt.Sprint(health["total_memories"]) != "0" {
		t.Fatalf("unexpected health payload: %#v", health)
	}

	infoRequest, err := http.NewRequest(http.MethodGet, server.URL+"/api/v1/info", nil)
	if err != nil {
		t.Fatal(err)
	}
	infoRequest.Header.Set("X-API-Key", "test-key")
	infoResponse, err := http.DefaultClient.Do(infoRequest)
	if err != nil {
		t.Fatal(err)
	}
	defer infoResponse.Body.Close()
	var infoPayload map[string]any
	if err := json.NewDecoder(infoResponse.Body).Decode(&infoPayload); err != nil {
		t.Fatal(err)
	}
	if infoResponse.StatusCode != http.StatusOK {
		t.Fatalf("expected info endpoint to return 200, got %d", infoResponse.StatusCode)
	}
	if infoPayload["sqlite_vec_status"] != "not_applicable_in_go_server" {
		t.Fatalf("unexpected info payload: %#v", infoPayload)
	}

	now := time.Now().UTC().Format(time.RFC3339Nano)
	for _, item := range []*memoryv1.MemoryItem{
		{Id: "left", Content: "left memory", MemoryType: "semantic", Embedding: []float32{0.1}, CreatedAt: now, LastAccessed: now, TrustScore: 0.8, Importance: 0.5, Layer: "short_term", DecayRate: 0.1, SourceId: "test"},
		{Id: "right", Content: "right memory", MemoryType: "semantic", Embedding: []float32{0.2}, CreatedAt: now, LastAccessed: now, TrustScore: 0.8, Importance: 0.5, Layer: "short_term", DecayRate: 0.1, SourceId: "test"},
	} {
		if _, err := backend.AddMemory(context.Background(), item); err != nil {
			t.Fatal(err)
		}
	}

	jwtToken := jwt.NewWithClaims(jwt.SigningMethodHS256, jwt.MapClaims{"sub": "tester"})
	signed, err := jwtToken.SignedString([]byte("test-secret"))
	if err != nil {
		t.Fatal(err)
	}
	request, err = http.NewRequest(http.MethodGet, server.URL+"/metrics", nil)
	if err != nil {
		t.Fatal(err)
	}
	request.Header.Set("Authorization", "Bearer "+signed)
	response, err = http.DefaultClient.Do(request)
	if err != nil {
		t.Fatal(err)
	}
	defer response.Body.Close()
	body, err := io.ReadAll(response.Body)
	if err != nil {
		t.Fatal(err)
	}
	if response.StatusCode != http.StatusOK {
		t.Fatalf("expected 200, got %d body=%s", response.StatusCode, string(body))
	}
	if !strings.Contains(string(body), "memory_http_duration_seconds") {
		t.Fatalf("expected metrics output, got %s", string(body))
	}
	if !strings.Contains(string(body), "memory_total") {
		t.Fatalf("expected memory_total metric, got %s", string(body))
	}

	relationRequest, err := http.NewRequest(
		http.MethodPost,
		server.URL+"/api/v1/relations",
		strings.NewReader(`{"source_id":"left","target_id":"right","relation_type":"contradicts","created_at":"2026-03-25T00:00:00Z"}`),
	)
	if err != nil {
		t.Fatal(err)
	}
	relationRequest.Header.Set("Content-Type", "application/json")
	relationRequest.Header.Set("X-API-Key", "test-key")
	response, err = http.DefaultClient.Do(relationRequest)
	if err != nil {
		t.Fatal(err)
	}
	defer response.Body.Close()

	request, err = http.NewRequest(http.MethodGet, server.URL+"/metrics", nil)
	if err != nil {
		t.Fatal(err)
	}
	request.Header.Set("X-API-Key", "test-key")
	response, err = http.DefaultClient.Do(request)
	if err != nil {
		t.Fatal(err)
	}
	defer response.Body.Close()
	body, err = io.ReadAll(response.Body)
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(string(body), "memory_conflicts_detected_total") {
		t.Fatalf("expected conflict metric, got %s", string(body))
	}
}

func unregisterMetrics(metrics *observability.Metrics) {
	observability.Unregister(metrics)
}
