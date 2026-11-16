package httpserver

import (
	"fmt"
	"log/slog"
	"net"
	"net/http"
	"time"
)

// RequestLogger provides structured HTTP access logging.
type RequestLogger struct {
	enabled bool
}

// NewRequestLogger creates a request logger.
func NewRequestLogger(enabled bool) *RequestLogger {
	return &RequestLogger{enabled: enabled}
}

// responseWriter wraps http.ResponseWriter to capture status code.
// Implements http.Flusher to support SSE/streaming endpoints.
type responseWriter struct {
	http.ResponseWriter
	statusCode int
}

func (rw *responseWriter) WriteHeader(code int) {
	rw.statusCode = code
	rw.ResponseWriter.WriteHeader(code)
}

// Flush delegates to the underlying ResponseWriter if it supports http.Flusher.
// Required for SSE streaming (handleSSEStream, WSHub).
func (rw *responseWriter) Flush() {
	if f, ok := rw.ResponseWriter.(http.Flusher); ok {
		f.Flush()
	}
}

// Unwrap returns the underlying ResponseWriter for Go 1.20+ ResponseController.
func (rw *responseWriter) Unwrap() http.ResponseWriter {
	return rw.ResponseWriter
}

// Middleware logs each request with method, path, status, duration, and IP.
func (rl *RequestLogger) Middleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if !rl.enabled {
			next.ServeHTTP(w, r)
			return
		}

		start := time.Now()
		rw := &responseWriter{ResponseWriter: w, statusCode: http.StatusOK}

		next.ServeHTTP(rw, r)

		duration := time.Since(start)
		ip := r.RemoteAddr
		// T5-1 FIX: Use RemoteAddr directly (consistent with rate limiter T4-3).
		if host, _, err := net.SplitHostPort(ip); err == nil {
			ip = host
		}

		logFn := slog.Info
		if rw.statusCode >= 500 {
			logFn = slog.Error
		} else if rw.statusCode >= 400 {
			logFn = slog.Warn
		}

		logFn("http request",
			"method", r.Method,
			"path", r.URL.Path,
			"status", rw.statusCode,
			"duration", formatDuration(duration),
			"ip", ip,
			"ua", r.UserAgent(),
		)
	})
}

func formatDuration(d time.Duration) string {
	if d < time.Millisecond {
		return fmt.Sprintf("%dµs", d.Microseconds())
	}
	if d < time.Second {
		return fmt.Sprintf("%dms", d.Milliseconds())
	}
	return fmt.Sprintf("%.2fs", d.Seconds())
}
