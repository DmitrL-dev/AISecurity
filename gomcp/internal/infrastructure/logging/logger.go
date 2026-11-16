// Package logging provides structured logging via Go's log/slog.
// Production: JSON output. Development: text output with colors.
//
// Usage:
//
//	logger := logging.New("json", "info")  // production
//	logger := logging.New("text", "debug") // development
//	logger.Info("event ingested", "event_id", id, "source", src)
package logging

import (
	"io"
	"log/slog"
	"os"
	"strings"
)

// New creates a structured logger.
// format: "json" (production) or "text" (development).
// level: "debug", "info", "warn", "error".
func New(format, level string) *slog.Logger {
	return NewWithOutput(format, level, os.Stdout)
}

// NewWithOutput creates a logger writing to the given writer.
func NewWithOutput(format, level string, w io.Writer) *slog.Logger {
	lvl := parseLevel(level)
	opts := &slog.HandlerOptions{Level: lvl}

	var handler slog.Handler
	switch strings.ToLower(format) {
	case "json":
		handler = slog.NewJSONHandler(w, opts)
	default:
		handler = slog.NewTextHandler(w, opts)
	}

	return slog.New(handler)
}

// WithComponent returns a logger with a "component" attribute.
func WithComponent(logger *slog.Logger, component string) *slog.Logger {
	return logger.With("component", component)
}

func parseLevel(s string) slog.Level {
	switch strings.ToLower(s) {
	case "debug":
		return slog.LevelDebug
	case "warn", "warning":
		return slog.LevelWarn
	case "error":
		return slog.LevelError
	default:
		return slog.LevelInfo
	}
}
