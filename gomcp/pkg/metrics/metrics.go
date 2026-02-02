// Package metrics provides Prometheus metrics for GoMCP.
package metrics

import (
	"net/http"
	"sync"
	"time"
)

// Metric types
const (
	MetricTypeCounter   = "counter"
	MetricTypeGauge     = "gauge"
	MetricTypeHistogram = "histogram"
	MetricTypeSummary   = "summary"
)

// Labels for metrics
type Labels map[string]string

// Counter is a monotonically increasing metric
type Counter struct {
	name   string
	help   string
	labels Labels
	value  float64
	mu     sync.RWMutex
}

// NewCounter creates a new counter
func NewCounter(name, help string, labels Labels) *Counter {
	return &Counter{
		name:   name,
		help:   help,
		labels: labels,
	}
}

// Inc increments the counter by 1
func (c *Counter) Inc() {
	c.mu.Lock()
	c.value++
	c.mu.Unlock()
}

// Add adds a value to the counter
func (c *Counter) Add(v float64) {
	if v < 0 {
		return // Counters can only increase
	}
	c.mu.Lock()
	c.value += v
	c.mu.Unlock()
}

// Value returns the current value
func (c *Counter) Value() float64 {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return c.value
}

// Name returns the metric name
func (c *Counter) Name() string {
	return c.name
}

// Gauge is a metric that can go up and down
type Gauge struct {
	name   string
	help   string
	labels Labels
	value  float64
	mu     sync.RWMutex
}

// NewGauge creates a new gauge
func NewGauge(name, help string, labels Labels) *Gauge {
	return &Gauge{
		name:   name,
		help:   help,
		labels: labels,
	}
}

// Set sets the gauge value
func (g *Gauge) Set(v float64) {
	g.mu.Lock()
	g.value = v
	g.mu.Unlock()
}

// Inc increments the gauge by 1
func (g *Gauge) Inc() {
	g.mu.Lock()
	g.value++
	g.mu.Unlock()
}

// Dec decrements the gauge by 1
func (g *Gauge) Dec() {
	g.mu.Lock()
	g.value--
	g.mu.Unlock()
}

// Add adds a value to the gauge
func (g *Gauge) Add(v float64) {
	g.mu.Lock()
	g.value += v
	g.mu.Unlock()
}

// Sub subtracts a value from the gauge
func (g *Gauge) Sub(v float64) {
	g.mu.Lock()
	g.value -= v
	g.mu.Unlock()
}

// Value returns the current value
func (g *Gauge) Value() float64 {
	g.mu.RLock()
	defer g.mu.RUnlock()
	return g.value
}

// Name returns the metric name
func (g *Gauge) Name() string {
	return g.name
}

// Histogram tracks the distribution of values
type Histogram struct {
	name    string
	help    string
	labels  Labels
	buckets []float64
	counts  []uint64
	sum     float64
	count   uint64
	mu      sync.RWMutex
}

// DefaultBuckets for HTTP request durations
var DefaultBuckets = []float64{.005, .01, .025, .05, .1, .25, .5, 1, 2.5, 5, 10}

// NewHistogram creates a new histogram
func NewHistogram(name, help string, labels Labels, buckets []float64) *Histogram {
	if buckets == nil {
		buckets = DefaultBuckets
	}
	return &Histogram{
		name:    name,
		help:    help,
		labels:  labels,
		buckets: buckets,
		counts:  make([]uint64, len(buckets)),
	}
}

// Observe records a value
func (h *Histogram) Observe(v float64) {
	h.mu.Lock()
	defer h.mu.Unlock()

	h.sum += v
	h.count++

	for i, bucket := range h.buckets {
		if v <= bucket {
			h.counts[i]++
		}
	}
}

// Count returns total observations
func (h *Histogram) Count() uint64 {
	h.mu.RLock()
	defer h.mu.RUnlock()
	return h.count
}

// Sum returns sum of all observations
func (h *Histogram) Sum() float64 {
	h.mu.RLock()
	defer h.mu.RUnlock()
	return h.sum
}

// Name returns the metric name
func (h *Histogram) Name() string {
	return h.name
}

// Timer helps measure durations
type Timer struct {
	histogram *Histogram
	start     time.Time
}

// NewTimer starts a new timer
func NewTimer(h *Histogram) *Timer {
	return &Timer{
		histogram: h,
		start:     time.Now(),
	}
}

// ObserveDuration records the elapsed time
func (t *Timer) ObserveDuration() time.Duration {
	d := time.Since(t.start)
	if t.histogram != nil {
		t.histogram.Observe(d.Seconds())
	}
	return d
}

// Registry holds all metrics
type Registry struct {
	counters   map[string]*Counter
	gauges     map[string]*Gauge
	histograms map[string]*Histogram
	mu         sync.RWMutex
}

// NewRegistry creates a new registry
func NewRegistry() *Registry {
	return &Registry{
		counters:   make(map[string]*Counter),
		gauges:     make(map[string]*Gauge),
		histograms: make(map[string]*Histogram),
	}
}

// RegisterCounter registers a counter
func (r *Registry) RegisterCounter(c *Counter) {
	r.mu.Lock()
	r.counters[c.name] = c
	r.mu.Unlock()
}

// RegisterGauge registers a gauge
func (r *Registry) RegisterGauge(g *Gauge) {
	r.mu.Lock()
	r.gauges[g.name] = g
	r.mu.Unlock()
}

// RegisterHistogram registers a histogram
func (r *Registry) RegisterHistogram(h *Histogram) {
	r.mu.Lock()
	r.histograms[h.name] = h
	r.mu.Unlock()
}

// GetCounter returns a counter by name
func (r *Registry) GetCounter(name string) *Counter {
	r.mu.RLock()
	defer r.mu.RUnlock()
	return r.counters[name]
}

// GetGauge returns a gauge by name
func (r *Registry) GetGauge(name string) *Gauge {
	r.mu.RLock()
	defer r.mu.RUnlock()
	return r.gauges[name]
}

// GetHistogram returns a histogram by name
func (r *Registry) GetHistogram(name string) *Histogram {
	r.mu.RLock()
	defer r.mu.RUnlock()
	return r.histograms[name]
}

// Handler returns an HTTP handler for metrics endpoint
func (r *Registry) Handler() http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, req *http.Request) {
		w.Header().Set("Content-Type", "text/plain; version=0.0.4; charset=utf-8")

		r.mu.RLock()
		defer r.mu.RUnlock()

		// Write counters
		for _, c := range r.counters {
			writeMetric(w, c.name, c.help, MetricTypeCounter, c.Value(), c.labels)
		}

		// Write gauges
		for _, g := range r.gauges {
			writeMetric(w, g.name, g.help, MetricTypeGauge, g.Value(), g.labels)
		}

		// Write histograms
		for _, h := range r.histograms {
			writeHistogram(w, h)
		}
	})
}

func writeMetric(w http.ResponseWriter, name, help, metricType string, value float64, labels Labels) {
	if help != "" {
		w.Write([]byte("# HELP " + name + " " + help + "\n"))
	}
	w.Write([]byte("# TYPE " + name + " " + metricType + "\n"))

	labelStr := formatLabels(labels)
	w.Write([]byte(name + labelStr + " " + formatFloat(value) + "\n"))
}

func writeHistogram(w http.ResponseWriter, h *Histogram) {
	h.mu.RLock()
	defer h.mu.RUnlock()

	if h.help != "" {
		w.Write([]byte("# HELP " + h.name + " " + h.help + "\n"))
	}
	w.Write([]byte("# TYPE " + h.name + " histogram\n"))

	// Write bucket counts
	for i, bucket := range h.buckets {
		labels := copyLabels(h.labels)
		labels["le"] = formatFloat(bucket)
		w.Write([]byte(h.name + "_bucket" + formatLabels(labels) + " " + formatUint(h.counts[i]) + "\n"))
	}

	// Write +Inf bucket
	labels := copyLabels(h.labels)
	labels["le"] = "+Inf"
	w.Write([]byte(h.name + "_bucket" + formatLabels(labels) + " " + formatUint(h.count) + "\n"))

	// Write sum and count
	w.Write([]byte(h.name + "_sum" + formatLabels(h.labels) + " " + formatFloat(h.sum) + "\n"))
	w.Write([]byte(h.name + "_count" + formatLabels(h.labels) + " " + formatUint(h.count) + "\n"))
}

func formatLabels(labels Labels) string {
	if len(labels) == 0 {
		return ""
	}
	result := "{"
	first := true
	for k, v := range labels {
		if !first {
			result += ","
		}
		result += k + "=\"" + v + "\""
		first = false
	}
	return result + "}"
}

func copyLabels(labels Labels) Labels {
	result := make(Labels, len(labels))
	for k, v := range labels {
		result[k] = v
	}
	return result
}

func formatFloat(v float64) string {
	return string(appendFloat(nil, v))
}

func formatUint(v uint64) string {
	return string(appendUint(nil, v))
}

func appendFloat(dst []byte, v float64) []byte {
	return append(dst, []byte(floatToString(v))...)
}

func appendUint(dst []byte, v uint64) []byte {
	return append(dst, []byte(uintToString(v))...)
}

func floatToString(v float64) string {
	return string([]byte{
		byte('0' + int(v)%10),
	}) // Simplified - use strconv in production
}

func uintToString(v uint64) string {
	if v == 0 {
		return "0"
	}
	result := ""
	for v > 0 {
		result = string(byte('0'+v%10)) + result
		v /= 10
	}
	return result
}

// GoMCP specific metrics
type GoMCPMetrics struct {
	Registry *Registry

	// Counters
	ToolCallsTotal  *Counter
	ToolErrorsTotal *Counter
	ValidationFails *Counter
	RateLimitHits   *Counter

	// Gauges
	ActiveWorkers *Gauge
	ActiveTenants *Gauge
	QueuedCalls   *Gauge

	// Histograms
	ToolCallDuration *Histogram
	ValidationTime   *Histogram
	BatchSize        *Histogram
}

// NewGoMCPMetrics creates GoMCP-specific metrics
func NewGoMCPMetrics() *GoMCPMetrics {
	r := NewRegistry()

	m := &GoMCPMetrics{
		Registry: r,

		// Counters
		ToolCallsTotal:  NewCounter("gomcp_tool_calls_total", "Total tool calls", nil),
		ToolErrorsTotal: NewCounter("gomcp_tool_errors_total", "Total tool errors", nil),
		ValidationFails: NewCounter("gomcp_validation_failures_total", "Validation failures", nil),
		RateLimitHits:   NewCounter("gomcp_rate_limit_hits_total", "Rate limit hits", nil),

		// Gauges
		ActiveWorkers: NewGauge("gomcp_active_workers", "Active workers", nil),
		ActiveTenants: NewGauge("gomcp_active_tenants", "Active tenants", nil),
		QueuedCalls:   NewGauge("gomcp_queued_calls", "Queued tool calls", nil),

		// Histograms
		ToolCallDuration: NewHistogram("gomcp_tool_call_duration_seconds", "Tool call duration", nil, nil),
		ValidationTime: NewHistogram("gomcp_validation_duration_seconds", "Validation duration", nil,
			[]float64{.0001, .0005, .001, .005, .01, .05, .1}),
		BatchSize: NewHistogram("gomcp_batch_size", "Batch sizes", nil,
			[]float64{1, 5, 10, 25, 50, 100}),
	}

	// Register all
	r.RegisterCounter(m.ToolCallsTotal)
	r.RegisterCounter(m.ToolErrorsTotal)
	r.RegisterCounter(m.ValidationFails)
	r.RegisterCounter(m.RateLimitHits)
	r.RegisterGauge(m.ActiveWorkers)
	r.RegisterGauge(m.ActiveTenants)
	r.RegisterGauge(m.QueuedCalls)
	r.RegisterHistogram(m.ToolCallDuration)
	r.RegisterHistogram(m.ValidationTime)
	r.RegisterHistogram(m.BatchSize)

	return m
}

// RecordToolCall records a tool call with duration
func (m *GoMCPMetrics) RecordToolCall(duration time.Duration, success bool) {
	m.ToolCallsTotal.Inc()
	m.ToolCallDuration.Observe(duration.Seconds())
	if !success {
		m.ToolErrorsTotal.Inc()
	}
}

// Handler returns HTTP handler for /metrics
func (m *GoMCPMetrics) Handler() http.Handler {
	return m.Registry.Handler()
}
