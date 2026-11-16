package httpserver

import (
	"fmt"
	"io"
	"net/http"
	"runtime"
	"sync/atomic"
	"time"
)

// Metrics collects runtime metrics for Prometheus-style /metrics endpoint.
type Metrics struct {
	requestsTotal  atomic.Int64
	requestErrors  atomic.Int64
	eventsIngested atomic.Int64
	incidentsTotal atomic.Int64
	rateLimited    atomic.Int64
	startTime      time.Time

	// socWriter, when set, appends the SOC-plane self-observability exposition
	// (IMP7) to /metrics after the generic runtime series. It is the SOC
	// Service.WriteMetrics method, wired in at server construction.
	socWriter func(io.Writer)
}

// SetSOCWriter wires the SOC-plane metrics writer into /metrics (IMP7).
func (m *Metrics) SetSOCWriter(fn func(io.Writer)) { m.socWriter = fn }

// NewMetrics creates a metrics collector.
func NewMetrics() *Metrics {
	return &Metrics{
		startTime: time.Now(),
	}
}

// IncRequests increments total request count.
func (m *Metrics) IncRequests() { m.requestsTotal.Add(1) }

// IncErrors increments error count.
func (m *Metrics) IncErrors() { m.requestErrors.Add(1) }

// IncEvents increments ingested events count.
func (m *Metrics) IncEvents() { m.eventsIngested.Add(1) }

// IncIncidents increments incident count.
func (m *Metrics) IncIncidents() { m.incidentsTotal.Add(1) }

// IncRateLimited increments rate-limited request count.
func (m *Metrics) IncRateLimited() { m.rateLimited.Add(1) }

// Middleware counts all requests.
func (m *Metrics) Middleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		m.IncRequests()
		next.ServeHTTP(w, r)
	})
}

// Handler returns /metrics in Prometheus text exposition format.
func (m *Metrics) Handler() http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		var memStats runtime.MemStats
		runtime.ReadMemStats(&memStats)

		w.Header().Set("Content-Type", "text/plain; charset=utf-8")

		uptime := time.Since(m.startTime).Seconds()

		fmt.Fprintf(w, "# HELP syntrex_uptime_seconds Time since server start\n")
		fmt.Fprintf(w, "syntrex_uptime_seconds %.2f\n\n", uptime)

		fmt.Fprintf(w, "# HELP syntrex_requests_total Total HTTP requests\n")
		fmt.Fprintf(w, "syntrex_requests_total %d\n\n", m.requestsTotal.Load())

		fmt.Fprintf(w, "# HELP syntrex_request_errors_total Total request errors\n")
		fmt.Fprintf(w, "syntrex_request_errors_total %d\n\n", m.requestErrors.Load())

		fmt.Fprintf(w, "# HELP syntrex_events_ingested_total Total events ingested\n")
		fmt.Fprintf(w, "syntrex_events_ingested_total %d\n\n", m.eventsIngested.Load())

		fmt.Fprintf(w, "# HELP syntrex_incidents_total Total incidents created\n")
		fmt.Fprintf(w, "syntrex_incidents_total %d\n\n", m.incidentsTotal.Load())

		fmt.Fprintf(w, "# HELP syntrex_rate_limited_total Total rate-limited requests\n")
		fmt.Fprintf(w, "syntrex_rate_limited_total %d\n\n", m.rateLimited.Load())

		fmt.Fprintf(w, "# HELP syntrex_goroutines Current goroutine count\n")
		fmt.Fprintf(w, "syntrex_goroutines %d\n\n", runtime.NumGoroutine())

		fmt.Fprintf(w, "# HELP syntrex_memory_alloc_bytes Current memory allocation\n")
		fmt.Fprintf(w, "syntrex_memory_alloc_bytes %d\n\n", memStats.Alloc)

		fmt.Fprintf(w, "# HELP syntrex_memory_sys_bytes Total memory from OS\n")
		fmt.Fprintf(w, "syntrex_memory_sys_bytes %d\n\n", memStats.Sys)

		fmt.Fprintf(w, "# HELP syntrex_gc_runs_total Total GC runs\n")
		fmt.Fprintf(w, "syntrex_gc_runs_total %d\n", memStats.NumGC)

		// Append SOC-plane self-observability metrics (IMP7), if wired.
		if m.socWriter != nil {
			fmt.Fprintf(w, "\n")
			m.socWriter(w)
		}
	}
}
