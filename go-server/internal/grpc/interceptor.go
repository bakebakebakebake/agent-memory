package grpcserver

import (
	"context"

	"github.com/bakebakebakebake/agent-memory/go-server/internal/auth"
	"github.com/bakebakebakebake/agent-memory/go-server/internal/config"
	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/metadata"
	"google.golang.org/grpc/status"
)

func UnaryAuthInterceptor(cfg config.Config) grpc.UnaryServerInterceptor {
	return func(ctx context.Context, request any, info *grpc.UnaryServerInfo, handler grpc.UnaryHandler) (any, error) {
		if cfg.APIKey == "" && cfg.JWTSecret == "" {
			return handler(ctx, request)
		}
		md, _ := metadata.FromIncomingContext(ctx)
		apiKey := firstValue(md.Get("x-api-key"))
		authorization := firstValue(md.Get("authorization"))
		if cfg.APIKey != "" && auth.APIKeyMatches(apiKey, cfg.APIKey) {
			return handler(ctx, request)
		}
		if cfg.JWTSecret != "" && auth.JWTMatches(auth.ParseBearerToken(authorization), cfg.JWTSecret) {
			return handler(ctx, request)
		}
		return nil, status.Error(codes.Unauthenticated, "unauthorized")
	}
}

func firstValue(values []string) string {
	if len(values) == 0 {
		return ""
	}
	return values[0]
}
