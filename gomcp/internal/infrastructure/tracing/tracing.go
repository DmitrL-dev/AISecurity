// Package tracing provides OpenTelemetry instrumentation for the SOC platform.
//
// Usage:
//
//	OTEL_EXPORTER_OTLP_ENDPOINT=localhost:4317 go run ./cmd/soc/
//
// If OTEL_EXPORTER_OTLP_ENDPOINT is not set, tracing is disabled (noop).
package tracing

import (
	"context"
	"log/slog"
	"time"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.26.0"
	"go.opentelemetry.io/otel/trace"
)

const (
	ServiceName    = "sentinel-soc"
	ServiceVersion = "1.0.0"
)

// InitTracer sets up the OpenTelemetry TracerProvider with OTLP gRPC exporter.
// Returns the provider (for shutdown) and any error.
// If endpoint is empty, returns a noop provider (safe to use, no overhead).
func InitTracer(ctx context.Context, endpoint string) (*sdktrace.TracerProvider, error) {
	if endpoint == "" {
		slog.Info("tracing disabled: OTEL_EXPORTER_OTLP_ENDPOINT not set")
		return nil, nil
	}

	exporter, err := otlptracegrpc.New(ctx,
		otlptracegrpc.WithEndpoint(endpoint),
		otlptracegrpc.WithInsecure(), // Use TLS in production
		otlptracegrpc.WithTimeout(5*time.Second),
	)
	if err != nil {
		return nil, err
	}

	res, err := resource.New(ctx,
		resource.WithAttributes(
			semconv.ServiceName(ServiceName),
			semconv.ServiceVersion(ServiceVersion),
		),
	)
	if err != nil {
		return nil, err
	}

	tp := sdktrace.NewTracerProvider(
		sdktrace.WithBatcher(exporter,
			sdktrace.WithMaxQueueSize(2048),
			sdktrace.WithBatchTimeout(5*time.Second),
		),
		sdktrace.WithResource(res),
		sdktrace.WithSampler(sdktrace.ParentBased(sdktrace.TraceIDRatioBased(1.0))),
	)

	otel.SetTracerProvider(tp)

	slog.Info("tracing enabled",
		"endpoint", endpoint,
		"service", ServiceName,
		"version", ServiceVersion,
	)

	return tp, nil
}

// Tracer returns a named tracer from the global provider.
func Tracer(name string) trace.Tracer {
	return otel.Tracer(name)
}

// Shutdown gracefully flushes and stops the tracer provider.
func Shutdown(ctx context.Context, tp *sdktrace.TracerProvider) {
	if tp == nil {
		return
	}
	shutdownCtx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()
	if err := tp.Shutdown(shutdownCtx); err != nil {
		slog.Error("tracer shutdown error", "error", err)
	}
}
