package observability

import (
	"context"

	"go.opentelemetry.io/otel"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
)

func InitTracing() func(context.Context) error {
	provider := sdktrace.NewTracerProvider()
	otel.SetTracerProvider(provider)
	return provider.Shutdown
}
