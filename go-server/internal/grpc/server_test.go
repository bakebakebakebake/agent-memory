package grpcserver

import (
	"context"
	"net"
	"testing"
	"time"

	memoryv1 "github.com/bakebakebakebake/agent-memory/go-server/gen/memory/v1"
	"github.com/bakebakebakebake/agent-memory/go-server/internal/config"
	"github.com/bakebakebakebake/agent-memory/go-server/internal/observability"
	"github.com/bakebakebakebake/agent-memory/go-server/internal/search"
	"github.com/bakebakebakebake/agent-memory/go-server/internal/storage"
	"github.com/golang-jwt/jwt/v5"
	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/credentials/insecure"
	"google.golang.org/grpc/metadata"
	"google.golang.org/grpc/status"
	"google.golang.org/grpc/test/bufconn"
)

func TestStorageServiceOverGRPC(t *testing.T) {
	backend, err := storage.New(":memory:")
	if err != nil {
		t.Fatal(err)
	}
	defer backend.Close()

	listener := bufconn.Listen(1024 * 1024)
	metrics := observability.NewMetrics()
	defer unregisterGRPCMetrics(metrics)
	orchestrator := search.New(backend, search.Config{
		SemanticLimit: 10,
		LexicalLimit:  10,
		EntityLimit:   10,
		DefaultLimit:  5,
		RRFK:          60,
	})
	server := grpc.NewServer()
	memoryv1.RegisterStorageServiceServer(server, New(backend, orchestrator, metrics))
	defer server.Stop()
	go func() {
		_ = server.Serve(listener)
	}()

	client := dialBufConn(t, listener)

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	now := time.Now().UTC().Format(time.RFC3339Nano)
	_, err = client.AddMemory(ctx, &memoryv1.AddMemoryRequest{
		Item: &memoryv1.MemoryItem{
			Id:           "grpc-1",
			Content:      "SQLite works well for local-first agents.",
			MemoryType:   "semantic",
			Embedding:    []float32{0.1, 0.2, 0.3},
			CreatedAt:    now,
			LastAccessed: now,
			TrustScore:   0.75,
			Importance:   0.5,
			Layer:        "short_term",
			DecayRate:    0.1,
			SourceId:     "grpc-test",
			EntityRefs:   []string{"sqlite"},
			Tags:         []string{"db"},
		},
	})
	if err != nil {
		t.Fatal(err)
	}

	got, err := client.GetMemory(ctx, &memoryv1.GetMemoryRequest{MemoryId: "grpc-1"})
	if err != nil {
		t.Fatal(err)
	}
	if !got.Found || got.Item.Id != "grpc-1" {
		t.Fatalf("unexpected get response: %#v", got)
	}

	health, err := client.HealthCheck(ctx, &memoryv1.HealthCheckRequest{})
	if err != nil {
		t.Fatal(err)
	}
	if health.Snapshot.TotalMemories != 1 {
		t.Fatalf("unexpected health response: %#v", health)
	}

	searchResults, err := client.SearchQuery(ctx, &memoryv1.SearchQueryRequest{
		Query:     "SQLite",
		Embedding: []float32{0.1, 0.2, 0.3},
		Entities:  []string{"sqlite"},
		Limit:     5,
	})
	if err != nil {
		t.Fatal(err)
	}
	if len(searchResults.Results) == 0 || searchResults.Results[0].Item.Id != "grpc-1" {
		t.Fatalf("unexpected search response: %#v", searchResults)
	}
}

func TestGRPCAuthInterceptor(t *testing.T) {
	backend, err := storage.New(":memory:")
	if err != nil {
		t.Fatal(err)
	}
	defer backend.Close()
	metrics := observability.NewMetrics()
	defer unregisterGRPCMetrics(metrics)
	cfg := config.Config{APIKey: "test-key", JWTSecret: "test-secret"}
	orchestrator := search.New(backend, search.Config{
		SemanticLimit: 10,
		LexicalLimit:  10,
		EntityLimit:   10,
		DefaultLimit:  5,
		RRFK:          60,
	})
	listener := bufconn.Listen(1024 * 1024)
	server := grpc.NewServer(grpc.UnaryInterceptor(UnaryAuthInterceptor(cfg)))
	memoryv1.RegisterStorageServiceServer(server, New(backend, orchestrator, metrics))
	defer server.Stop()
	go func() {
		_ = server.Serve(listener)
	}()

	client := dialBufConn(t, listener)

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	_, err = client.HealthCheck(ctx, &memoryv1.HealthCheckRequest{})
	if err == nil {
		t.Fatal("expected unauthenticated error")
	}
	if status.Code(err) != codes.Unauthenticated {
		t.Fatalf("unexpected grpc status: %v", err)
	}

	ctxAPIKey := metadata.NewOutgoingContext(ctx, metadata.Pairs("x-api-key", "test-key"))
	if _, err := client.HealthCheck(ctxAPIKey, &memoryv1.HealthCheckRequest{}); err != nil {
		t.Fatalf("expected api key auth to pass: %v", err)
	}

	token := jwt.NewWithClaims(jwt.SigningMethodHS256, jwt.MapClaims{"sub": "tester"})
	signed, err := token.SignedString([]byte("test-secret"))
	if err != nil {
		t.Fatal(err)
	}
	ctxJWT := metadata.NewOutgoingContext(ctx, metadata.Pairs("authorization", "Bearer "+signed))
	if _, err := client.HealthCheck(ctxJWT, &memoryv1.HealthCheckRequest{}); err != nil {
		t.Fatalf("expected jwt auth to pass: %v", err)
	}
}

func dialBufConn(t *testing.T, listener *bufconn.Listener) memoryv1.StorageServiceClient {
	t.Helper()
	contextDialer := func(context.Context, string) (net.Conn, error) {
		return listener.Dial()
	}
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	connection, err := grpc.DialContext(
		ctx,
		"passthrough:///bufnet",
		grpc.WithContextDialer(contextDialer),
		grpc.WithTransportCredentials(insecure.NewCredentials()),
	)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = connection.Close() })
	return memoryv1.NewStorageServiceClient(connection)
}

func unregisterGRPCMetrics(metrics *observability.Metrics) {
	observability.Unregister(metrics)
}
