package main

import (
	"context"
	"log/slog"
	"net"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	memoryv1 "github.com/bakebakebakebake/agent-memory/go-server/gen/memory/v1"
	"github.com/bakebakebakebake/agent-memory/go-server/internal/config"
	"github.com/bakebakebakebake/agent-memory/go-server/internal/gateway"
	grpcserver "github.com/bakebakebakebake/agent-memory/go-server/internal/grpc"
	"github.com/bakebakebakebake/agent-memory/go-server/internal/observability"
	"github.com/bakebakebakebake/agent-memory/go-server/internal/search"
	"github.com/bakebakebakebake/agent-memory/go-server/internal/storage"
	"google.golang.org/grpc"
)

func main() {
	cfg := config.Load()
	logger := observability.NewLogger(cfg.LogLevel)
	shutdownTracing := observability.InitTracing()
	defer func() {
		_ = shutdownTracing(context.Background())
	}()

	metrics := observability.NewMetrics()
	backend, err := storage.New(cfg.DatabasePath)
	if err != nil {
		logger.Error("init storage failed", "error", err)
		os.Exit(1)
	}
	defer backend.Close()

	orchestrator := search.New(backend, search.Config{
		SemanticLimit: int32(cfg.SemanticLimit),
		LexicalLimit:  int32(cfg.LexicalLimit),
		EntityLimit:   int32(cfg.EntityLimit),
		DefaultLimit:  int32(cfg.DefaultLimit),
		RRFK:          cfg.RRFK,
	})

	httpHandler := gateway.NewHandler(backend, orchestrator, cfg, metrics)
	httpServer := &http.Server{
		Addr:    cfg.HTTPAddress,
		Handler: httpHandler.Routes(logger),
	}

	grpcServer := grpc.NewServer(grpc.UnaryInterceptor(grpcserver.UnaryAuthInterceptor(cfg)))
	memoryv1.RegisterStorageServiceServer(grpcServer, grpcserver.New(backend, orchestrator, metrics))
	grpcListener, err := net.Listen("tcp", cfg.GRPCAddress)
	if err != nil {
		logger.Error("listen grpc failed", "error", err)
		os.Exit(1)
	}

	go func() {
		logger.Info("http server started", "address", cfg.HTTPAddress)
		if err := httpServer.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			logger.Error("http server failed", "error", err)
		}
	}()

	go func() {
		logger.Info("grpc server started", "address", cfg.GRPCAddress)
		if err := grpcServer.Serve(grpcListener); err != nil {
			logger.Error("grpc server failed", "error", err)
		}
	}()

	waitForShutdown(logger, httpServer, grpcServer)
}

func waitForShutdown(logger *slog.Logger, httpServer *http.Server, grpcServer *grpc.Server) {
	stop := make(chan os.Signal, 1)
	signal.Notify(stop, syscall.SIGINT, syscall.SIGTERM)
	<-stop
	logger.Info("shutting down servers")
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	_ = httpServer.Shutdown(ctx)
	grpcServer.GracefulStop()
}
