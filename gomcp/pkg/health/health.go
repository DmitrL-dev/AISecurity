// Package health provides health check endpoints for GoMCP supervisors.
package health

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"runtime"
	"sync"
	"time"
)

// Status represents component health status
type Status string

const (
	StatusHealthy   Status = "healthy"
	StatusDegraded  Status = "degraded"
	StatusUnhealthy Status = "unhealthy"
)

// ComponentHealth represents individual component health
type ComponentHealth struct {
	Name    string            `json:"name"`
	Status  Status            `json:"status"`
	Message string            `json:"message,omitempty"`
	Details map[string]string `json:"details,omitempty"`
}

// HealthResponse is the full health check response
type HealthResponse struct {
	Status     Status            `json:"status"`
	Timestamp  time.Time         `json:"timestamp"`
	Version    string            `json:"version"`
	Uptime     string            `json:"uptime"`
	Components []ComponentHealth `json:"components,omitempty"`
	Metrics    *Metrics          `json:"metrics,omitempty"`
}

// Metrics for the health endpoint
type Metrics struct {
	TotalRequests  int64 `json:"total_requests"`
	ActiveWorkers  int   `json:"active_workers"`
	HealthyWorkers int   `json:"healthy_workers"`
	TotalToolCalls int64 `json:"total_tool_calls"`
	MemoryAllocMB  int64 `json:"memory_alloc_mb"`
	NumGoroutines  int   `json:"num_goroutines"`
	NumCPU         int   `json:"num_cpu"`
}

// Checker provides health check functionality
type Checker interface {
	Check(ctx context.Context) ComponentHealth
}

// CheckerFunc wraps a function as a Checker
type CheckerFunc func(ctx context.Context) ComponentHealth

func (f CheckerFunc) Check(ctx context.Context) ComponentHealth {
	return f(ctx)
}

// Server provides HTTP health endpoints
type Server struct {
	mu        sync.RWMutex
	startTime time.Time
	version   string
	checkers  []Checker
	metrics   *Metrics

	// Metrics tracking
	totalRequests  int64
	totalToolCalls int64
}

// NewServer creates a new health server
func NewServer(version string) *Server {
	return &Server{
		startTime: time.Now(),
		version:   version,
		checkers:  make([]Checker, 0),
		metrics:   &Metrics{NumCPU: runtime.NumCPU()},
	}
}

// RegisterChecker adds a health checker
func (s *Server) RegisterChecker(checker Checker) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.checkers = append(s.checkers, checker)
}

// IncrementRequests increments the request counter
func (s *Server) IncrementRequests() {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.totalRequests++
}

// IncrementToolCalls increments the tool call counter
func (s *Server) IncrementToolCalls() {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.totalToolCalls++
}

// SetWorkerCounts updates worker metrics
func (s *Server) SetWorkerCounts(active, healthy int) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.metrics.ActiveWorkers = active
	s.metrics.HealthyWorkers = healthy
}

// GetHealth returns the current health status
func (s *Server) GetHealth(ctx context.Context) HealthResponse {
	s.mu.RLock()
	checkers := make([]Checker, len(s.checkers))
	copy(checkers, s.checkers)
	s.mu.RUnlock()

	// Run all health checks
	components := make([]ComponentHealth, 0, len(checkers))
	overallStatus := StatusHealthy

	for _, checker := range checkers {
		health := checker.Check(ctx)
		components = append(components, health)

		// Degrade overall status based on component status
		if health.Status == StatusUnhealthy {
			overallStatus = StatusUnhealthy
		} else if health.Status == StatusDegraded && overallStatus != StatusUnhealthy {
			overallStatus = StatusDegraded
		}
	}

	// Gather metrics
	var memStats runtime.MemStats
	runtime.ReadMemStats(&memStats)

	s.mu.RLock()
	metrics := &Metrics{
		TotalRequests:  s.totalRequests,
		ActiveWorkers:  s.metrics.ActiveWorkers,
		HealthyWorkers: s.metrics.HealthyWorkers,
		TotalToolCalls: s.totalToolCalls,
		MemoryAllocMB:  int64(memStats.Alloc / 1024 / 1024),
		NumGoroutines:  runtime.NumGoroutine(),
		NumCPU:         runtime.NumCPU(),
	}
	s.mu.RUnlock()

	return HealthResponse{
		Status:     overallStatus,
		Timestamp:  time.Now(),
		Version:    s.version,
		Uptime:     time.Since(s.startTime).String(),
		Components: components,
		Metrics:    metrics,
	}
}

// HandleHealth returns an HTTP handler for health checks
func (s *Server) HandleHealth() http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		ctx := r.Context()
		health := s.GetHealth(ctx)

		w.Header().Set("Content-Type", "application/json")

		// Set status code based on health
		switch health.Status {
		case StatusHealthy:
			w.WriteHeader(http.StatusOK)
		case StatusDegraded:
			w.WriteHeader(http.StatusOK) // Still OK but degraded
		case StatusUnhealthy:
			w.WriteHeader(http.StatusServiceUnavailable)
		}

		json.NewEncoder(w).Encode(health)
	}
}

// HandleLiveness returns a simple liveness probe handler
func (s *Server) HandleLiveness() http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		json.NewEncoder(w).Encode(map[string]string{"status": "alive"})
	}
}

// HandleReadiness returns a readiness probe handler
func (s *Server) HandleReadiness() http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		ctx := r.Context()
		health := s.GetHealth(ctx)

		w.Header().Set("Content-Type", "application/json")

		if health.Status == StatusUnhealthy {
			w.WriteHeader(http.StatusServiceUnavailable)
			json.NewEncoder(w).Encode(map[string]string{"status": "not ready"})
			return
		}

		w.WriteHeader(http.StatusOK)
		json.NewEncoder(w).Encode(map[string]string{"status": "ready"})
	}
}

// HandleMetrics returns a metrics-only handler
func (s *Server) HandleMetrics() http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		var memStats runtime.MemStats
		runtime.ReadMemStats(&memStats)

		s.mu.RLock()
		metrics := &Metrics{
			TotalRequests:  s.totalRequests,
			ActiveWorkers:  s.metrics.ActiveWorkers,
			HealthyWorkers: s.metrics.HealthyWorkers,
			TotalToolCalls: s.totalToolCalls,
			MemoryAllocMB:  int64(memStats.Alloc / 1024 / 1024),
			NumGoroutines:  runtime.NumGoroutine(),
			NumCPU:         runtime.NumCPU(),
		}
		s.mu.RUnlock()

		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		json.NewEncoder(w).Encode(metrics)
	}
}

// RegisterHandlers registers all health endpoints on the given mux
func (s *Server) RegisterHandlers(mux *http.ServeMux) {
	mux.HandleFunc("/health", s.HandleHealth())
	mux.HandleFunc("/healthz", s.HandleHealth())
	mux.HandleFunc("/livez", s.HandleLiveness())
	mux.HandleFunc("/readyz", s.HandleReadiness())
	mux.HandleFunc("/metrics", s.HandleMetrics())
}

// WorkerChecker creates a checker for worker health
func WorkerChecker(getWorkerStatus func() (active, healthy int)) Checker {
	return CheckerFunc(func(ctx context.Context) ComponentHealth {
		active, healthy := getWorkerStatus()

		status := StatusHealthy
		message := fmt.Sprintf("%d/%d workers healthy", healthy, active)

		if active == 0 {
			status = StatusDegraded
			message = "no workers registered"
		} else if healthy == 0 {
			status = StatusUnhealthy
			message = "all workers unhealthy"
		} else if healthy < active {
			status = StatusDegraded
			message = fmt.Sprintf("%d/%d workers healthy", healthy, active)
		}

		return ComponentHealth{
			Name:    "workers",
			Status:  status,
			Message: message,
			Details: map[string]string{
				"active":  fmt.Sprintf("%d", active),
				"healthy": fmt.Sprintf("%d", healthy),
			},
		}
	})
}

// DatabaseChecker creates a checker for database connectivity
func DatabaseChecker(name string, ping func(ctx context.Context) error) Checker {
	return CheckerFunc(func(ctx context.Context) ComponentHealth {
		if err := ping(ctx); err != nil {
			return ComponentHealth{
				Name:    name,
				Status:  StatusUnhealthy,
				Message: err.Error(),
			}
		}
		return ComponentHealth{
			Name:   name,
			Status: StatusHealthy,
		}
	})
}
