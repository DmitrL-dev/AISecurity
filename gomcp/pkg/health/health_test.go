package health

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
)

func TestServer_GetHealth_NoCheckers(t *testing.T) {
	s := NewServer("1.0.0")

	health := s.GetHealth(context.Background())

	if health.Status != StatusHealthy {
		t.Errorf("expected healthy status, got %s", health.Status)
	}
	if health.Version != "1.0.0" {
		t.Errorf("expected version 1.0.0, got %s", health.Version)
	}
	if health.Metrics == nil {
		t.Error("expected metrics to be present")
	}
}

func TestServer_GetHealth_WithCheckers(t *testing.T) {
	s := NewServer("1.0.0")

	// Add healthy checker
	s.RegisterChecker(CheckerFunc(func(ctx context.Context) ComponentHealth {
		return ComponentHealth{Name: "db", Status: StatusHealthy}
	}))

	// Add degraded checker
	s.RegisterChecker(CheckerFunc(func(ctx context.Context) ComponentHealth {
		return ComponentHealth{Name: "cache", Status: StatusDegraded, Message: "high latency"}
	}))

	health := s.GetHealth(context.Background())

	if health.Status != StatusDegraded {
		t.Errorf("expected degraded status, got %s", health.Status)
	}
	if len(health.Components) != 2 {
		t.Errorf("expected 2 components, got %d", len(health.Components))
	}
}

func TestServer_GetHealth_Unhealthy(t *testing.T) {
	s := NewServer("1.0.0")

	s.RegisterChecker(CheckerFunc(func(ctx context.Context) ComponentHealth {
		return ComponentHealth{Name: "critical", Status: StatusUnhealthy, Message: "down"}
	}))

	health := s.GetHealth(context.Background())

	if health.Status != StatusUnhealthy {
		t.Errorf("expected unhealthy status, got %s", health.Status)
	}
}

func TestServer_HandleHealth_OK(t *testing.T) {
	s := NewServer("1.0.0")

	req := httptest.NewRequest("GET", "/health", nil)
	rec := httptest.NewRecorder()

	s.HandleHealth().ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", rec.Code)
	}

	var resp HealthResponse
	if err := json.NewDecoder(rec.Body).Decode(&resp); err != nil {
		t.Fatalf("failed to decode response: %v", err)
	}

	if resp.Status != StatusHealthy {
		t.Errorf("expected healthy status, got %s", resp.Status)
	}
}

func TestServer_HandleHealth_ServiceUnavailable(t *testing.T) {
	s := NewServer("1.0.0")
	s.RegisterChecker(CheckerFunc(func(ctx context.Context) ComponentHealth {
		return ComponentHealth{Name: "db", Status: StatusUnhealthy}
	}))

	req := httptest.NewRequest("GET", "/health", nil)
	rec := httptest.NewRecorder()

	s.HandleHealth().ServeHTTP(rec, req)

	if rec.Code != http.StatusServiceUnavailable {
		t.Errorf("expected status 503, got %d", rec.Code)
	}
}

func TestServer_HandleLiveness(t *testing.T) {
	s := NewServer("1.0.0")

	req := httptest.NewRequest("GET", "/livez", nil)
	rec := httptest.NewRecorder()

	s.HandleLiveness().ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", rec.Code)
	}

	var resp map[string]string
	json.NewDecoder(rec.Body).Decode(&resp)

	if resp["status"] != "alive" {
		t.Errorf("expected status alive, got %s", resp["status"])
	}
}

func TestServer_HandleReadiness_Ready(t *testing.T) {
	s := NewServer("1.0.0")

	req := httptest.NewRequest("GET", "/readyz", nil)
	rec := httptest.NewRecorder()

	s.HandleReadiness().ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", rec.Code)
	}
}

func TestServer_HandleReadiness_NotReady(t *testing.T) {
	s := NewServer("1.0.0")
	s.RegisterChecker(CheckerFunc(func(ctx context.Context) ComponentHealth {
		return ComponentHealth{Name: "db", Status: StatusUnhealthy}
	}))

	req := httptest.NewRequest("GET", "/readyz", nil)
	rec := httptest.NewRecorder()

	s.HandleReadiness().ServeHTTP(rec, req)

	if rec.Code != http.StatusServiceUnavailable {
		t.Errorf("expected status 503, got %d", rec.Code)
	}
}

func TestServer_HandleMetrics(t *testing.T) {
	s := NewServer("1.0.0")
	s.IncrementRequests()
	s.IncrementRequests()
	s.IncrementToolCalls()
	s.SetWorkerCounts(3, 2)

	req := httptest.NewRequest("GET", "/metrics", nil)
	rec := httptest.NewRecorder()

	s.HandleMetrics().ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", rec.Code)
	}

	var metrics Metrics
	if err := json.NewDecoder(rec.Body).Decode(&metrics); err != nil {
		t.Fatalf("failed to decode metrics: %v", err)
	}

	if metrics.TotalRequests != 2 {
		t.Errorf("expected 2 requests, got %d", metrics.TotalRequests)
	}
	if metrics.TotalToolCalls != 1 {
		t.Errorf("expected 1 tool call, got %d", metrics.TotalToolCalls)
	}
	if metrics.ActiveWorkers != 3 {
		t.Errorf("expected 3 active workers, got %d", metrics.ActiveWorkers)
	}
	if metrics.HealthyWorkers != 2 {
		t.Errorf("expected 2 healthy workers, got %d", metrics.HealthyWorkers)
	}
}

func TestServer_RegisterHandlers(t *testing.T) {
	s := NewServer("1.0.0")
	mux := http.NewServeMux()
	s.RegisterHandlers(mux)

	// Test each endpoint exists
	endpoints := []string{"/health", "/healthz", "/livez", "/readyz", "/metrics"}
	for _, ep := range endpoints {
		req := httptest.NewRequest("GET", ep, nil)
		rec := httptest.NewRecorder()
		mux.ServeHTTP(rec, req)

		if rec.Code == http.StatusNotFound {
			t.Errorf("endpoint %s not registered", ep)
		}
	}
}

func TestWorkerChecker_AllHealthy(t *testing.T) {
	checker := WorkerChecker(func() (int, int) {
		return 5, 5
	})

	health := checker.Check(context.Background())

	if health.Status != StatusHealthy {
		t.Errorf("expected healthy, got %s", health.Status)
	}
}

func TestWorkerChecker_Degraded(t *testing.T) {
	checker := WorkerChecker(func() (int, int) {
		return 5, 3
	})

	health := checker.Check(context.Background())

	if health.Status != StatusDegraded {
		t.Errorf("expected degraded, got %s", health.Status)
	}
}

func TestWorkerChecker_AllUnhealthy(t *testing.T) {
	checker := WorkerChecker(func() (int, int) {
		return 5, 0
	})

	health := checker.Check(context.Background())

	if health.Status != StatusUnhealthy {
		t.Errorf("expected unhealthy, got %s", health.Status)
	}
}

func TestWorkerChecker_NoWorkers(t *testing.T) {
	checker := WorkerChecker(func() (int, int) {
		return 0, 0
	})

	health := checker.Check(context.Background())

	if health.Status != StatusDegraded {
		t.Errorf("expected degraded, got %s", health.Status)
	}
}

func TestDatabaseChecker_Healthy(t *testing.T) {
	checker := DatabaseChecker("postgres", func(ctx context.Context) error {
		return nil
	})

	health := checker.Check(context.Background())

	if health.Name != "postgres" {
		t.Errorf("expected name postgres, got %s", health.Name)
	}
	if health.Status != StatusHealthy {
		t.Errorf("expected healthy, got %s", health.Status)
	}
}

func TestDatabaseChecker_Unhealthy(t *testing.T) {
	checker := DatabaseChecker("postgres", func(ctx context.Context) error {
		return context.DeadlineExceeded
	})

	health := checker.Check(context.Background())

	if health.Status != StatusUnhealthy {
		t.Errorf("expected unhealthy, got %s", health.Status)
	}
}

func TestServer_Uptime(t *testing.T) {
	s := NewServer("1.0.0")
	time.Sleep(50 * time.Millisecond)

	health := s.GetHealth(context.Background())

	if health.Uptime == "" {
		t.Error("expected uptime to be set")
	}
}

// Benchmark
func BenchmarkServer_GetHealth(b *testing.B) {
	s := NewServer("1.0.0")
	s.RegisterChecker(CheckerFunc(func(ctx context.Context) ComponentHealth {
		return ComponentHealth{Name: "db", Status: StatusHealthy}
	}))
	s.RegisterChecker(CheckerFunc(func(ctx context.Context) ComponentHealth {
		return ComponentHealth{Name: "cache", Status: StatusHealthy}
	}))

	ctx := context.Background()
	b.ResetTimer()

	for i := 0; i < b.N; i++ {
		s.GetHealth(ctx)
	}
}
