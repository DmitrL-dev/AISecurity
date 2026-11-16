package resilience

import (
	"context"
	"fmt"
	"runtime"
	"runtime/debug"
	"sync/atomic"
)

// RuntimeMetricsCollector is a concrete MetricsCollector that reports REAL
// metrics for the SOC process itself by reading the Go runtime — NO fabricated
// values. For any component other than the self component it returns an error so
// the HealthMonitor marks that component unknown rather than inventing data.
//
// HONESTY (WS6 #21): cross-process/cross-component health (sentinel-core,
// postgres, …) requires a real external metrics source (a /healthz scrape or
// OTLP), which is operator-supplied infra. Until that exists, only this process
// is monitored truthfully; everything else stays unknown.
type RuntimeMetricsCollector struct {
	// selfComponent is the component name that maps to this process's runtime.
	selfComponent string
	// scanSatFn optionally reports scan-semaphore saturation (0.0–1.0) from the
	// HTTP server. Nil → the metric is omitted (not faked as 0).
	scanSatFn func() float64
	// lastNumGC tracks the previous GC count so gc_pause_ms reflects the most
	// recent collection rather than an all-time figure.
	lastNumGC uint32
	// lastPauseNs caches the last observed pause to avoid a 0 when no GC ran
	// between collections.
	lastPauseNs atomic.Uint64
}

// NewRuntimeMetricsCollector creates a collector for the named self component.
// scanSatFn may be nil.
func NewRuntimeMetricsCollector(selfComponent string, scanSatFn func() float64) *RuntimeMetricsCollector {
	if selfComponent == "" {
		selfComponent = "soc-server"
	}
	return &RuntimeMetricsCollector{
		selfComponent: selfComponent,
		scanSatFn:     scanSatFn,
	}
}

// SelfComponent returns the component name this collector reports runtime metrics for.
func (c *RuntimeMetricsCollector) SelfComponent() string { return c.selfComponent }

// Collect implements MetricsCollector. Real runtime stats for the self
// component; an error for anything else (never fabricated).
func (c *RuntimeMetricsCollector) Collect(ctx context.Context, component string) (map[string]float64, error) {
	if component != c.selfComponent {
		return nil, fmt.Errorf("no metrics source for component %q (only %q is self-monitored; "+
			"cross-component health requires an external /healthz or OTLP scrape)", component, c.selfComponent)
	}

	var m runtime.MemStats
	runtime.ReadMemStats(&m)

	metrics := map[string]float64{
		"heap_alloc_mb": float64(m.HeapAlloc) / (1024 * 1024),
		"heap_sys_mb":   float64(m.HeapSys) / (1024 * 1024),
		"goroutines":    float64(runtime.NumGoroutine()),
		"num_gc":        float64(m.NumGC),
		"gc_pause_ms":   c.recentGCPauseMs(&m),
	}

	// Optional, honest: only include if a real source is wired.
	if c.scanSatFn != nil {
		metrics["scan_saturation"] = c.scanSatFn()
	}

	return metrics, nil
}

// recentGCPauseMs returns the most recent GC pause in milliseconds. If a GC has
// run since the last call, use its pause; otherwise reuse the last observed
// value (avoids reporting 0 ms when simply no GC happened in the interval).
func (c *RuntimeMetricsCollector) recentGCPauseMs(m *runtime.MemStats) float64 {
	if m.NumGC != c.lastNumGC {
		c.lastNumGC = m.NumGC
		// PauseNs is a circular buffer; the most recent is at (NumGC+255)%256.
		idx := (m.NumGC + 255) % 256
		pauseNs := m.PauseNs[idx]
		c.lastPauseNs.Store(pauseNs)
		return float64(pauseNs) / 1e6
	}
	return float64(c.lastPauseNs.Load()) / 1e6
}

// GCStats exposes a compact view used by callers that want a one-shot read
// without going through HealthMonitor (kept minimal + real).
func GCStats() debug.GCStats {
	var s debug.GCStats
	debug.ReadGCStats(&s)
	return s
}
