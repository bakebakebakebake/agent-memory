package gateway

import (
	"log/slog"
	"net/http"
	"time"

	"github.com/bakebakebakebake/agent-memory/go-server/internal/auth"
	"github.com/bakebakebakebake/agent-memory/go-server/internal/config"
	"github.com/bakebakebakebake/agent-memory/go-server/internal/observability"
)

func withMiddleware(next http.Handler, cfg config.Config, logger *slog.Logger, metrics *observability.Metrics) http.Handler {
	return recoveryMiddleware(loggingMiddleware(authMiddleware(next, cfg), logger, metrics), logger)
}

func authMiddleware(next http.Handler, cfg config.Config) http.Handler {
	return http.HandlerFunc(func(writer http.ResponseWriter, request *http.Request) {
		if cfg.APIKey == "" && cfg.JWTSecret == "" {
			next.ServeHTTP(writer, request)
			return
		}
		if cfg.APIKey != "" && auth.HasAPIKey(request, cfg.APIKey) {
			next.ServeHTTP(writer, request)
			return
		}
		if cfg.JWTSecret != "" && auth.HasValidJWT(request, cfg.JWTSecret) {
			next.ServeHTTP(writer, request)
			return
		}
		http.Error(writer, `{"error":"unauthorized"}`, http.StatusUnauthorized)
	})
}

func loggingMiddleware(next http.Handler, logger *slog.Logger, metrics *observability.Metrics) http.Handler {
	return http.HandlerFunc(func(writer http.ResponseWriter, request *http.Request) {
		start := time.Now()
		next.ServeHTTP(writer, request)
		metrics.HTTPDuration.WithLabelValues(request.Method, request.URL.Path).Observe(time.Since(start).Seconds())
		logger.Info("http request", "method", request.Method, "path", request.URL.Path, "duration", time.Since(start).String())
	})
}

func recoveryMiddleware(next http.Handler, logger *slog.Logger) http.Handler {
	return http.HandlerFunc(func(writer http.ResponseWriter, request *http.Request) {
		defer func() {
			if recovered := recover(); recovered != nil {
				logger.Error("panic recovered", "error", recovered)
				http.Error(writer, `{"error":"internal server error"}`, http.StatusInternalServerError)
			}
		}()
		next.ServeHTTP(writer, request)
	})
}
