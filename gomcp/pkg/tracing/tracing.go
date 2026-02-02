// Package tracing provides OpenTelemetry integration for GoMCP.
package tracing

import (
	"context"
	"sync"
	"time"
)

// SpanKind defines the role of a span
type SpanKind int

const (
	SpanKindInternal SpanKind = iota
	SpanKindServer
	SpanKindClient
	SpanKindProducer
	SpanKindConsumer
)

// SpanStatus represents the status of a span
type SpanStatus int

const (
	StatusUnset SpanStatus = iota
	StatusOK
	StatusError
)

// Attribute is a key-value pair for span attributes
type Attribute struct {
	Key   string
	Value interface{}
}

// String creates a string attribute
func String(key, value string) Attribute {
	return Attribute{Key: key, Value: value}
}

// Int creates an int attribute
func Int(key string, value int) Attribute {
	return Attribute{Key: key, Value: value}
}

// Int64 creates an int64 attribute
func Int64(key string, value int64) Attribute {
	return Attribute{Key: key, Value: value}
}

// Float64 creates a float64 attribute
func Float64(key string, value float64) Attribute {
	return Attribute{Key: key, Value: value}
}

// Bool creates a bool attribute
func Bool(key string, value bool) Attribute {
	return Attribute{Key: key, Value: value}
}

// Event represents a span event
type Event struct {
	Name       string
	Timestamp  time.Time
	Attributes []Attribute
}

// Link represents a link to another span
type Link struct {
	TraceID    string
	SpanID     string
	Attributes []Attribute
}

// Span represents a trace span
type Span struct {
	name       string
	traceID    string
	spanID     string
	parentID   string
	kind       SpanKind
	startTime  time.Time
	endTime    time.Time
	status     SpanStatus
	statusMsg  string
	attributes []Attribute
	events     []Event
	links      []Link
	ended      bool
	mu         sync.RWMutex
}

// SpanContext contains the trace context
type SpanContext struct {
	TraceID string
	SpanID  string
}

// NewSpan creates a new span
func NewSpan(name string, opts ...SpanOption) *Span {
	s := &Span{
		name:      name,
		traceID:   generateID(),
		spanID:    generateID(),
		startTime: time.Now(),
		kind:      SpanKindInternal,
	}

	for _, opt := range opts {
		opt(s)
	}

	return s
}

// SpanOption configures a span
type SpanOption func(*Span)

// WithParent sets the parent span
func WithParent(parent *Span) SpanOption {
	return func(s *Span) {
		if parent != nil {
			s.traceID = parent.traceID
			s.parentID = parent.spanID
		}
	}
}

// WithSpanKind sets the span kind
func WithSpanKind(kind SpanKind) SpanOption {
	return func(s *Span) {
		s.kind = kind
	}
}

// WithAttributes sets initial attributes
func WithAttributes(attrs ...Attribute) SpanOption {
	return func(s *Span) {
		s.attributes = append(s.attributes, attrs...)
	}
}

// WithLinks sets span links
func WithLinks(links ...Link) SpanOption {
	return func(s *Span) {
		s.links = append(s.links, links...)
	}
}

// Name returns the span name
func (s *Span) Name() string {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.name
}

// SpanContext returns the span context
func (s *Span) SpanContext() SpanContext {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return SpanContext{
		TraceID: s.traceID,
		SpanID:  s.spanID,
	}
}

// SetAttribute sets a single attribute
func (s *Span) SetAttribute(attr Attribute) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.attributes = append(s.attributes, attr)
}

// SetAttributes sets multiple attributes
func (s *Span) SetAttributes(attrs ...Attribute) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.attributes = append(s.attributes, attrs...)
}

// AddEvent adds an event to the span
func (s *Span) AddEvent(name string, attrs ...Attribute) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.events = append(s.events, Event{
		Name:       name,
		Timestamp:  time.Now(),
		Attributes: attrs,
	})
}

// SetStatus sets the span status
func (s *Span) SetStatus(status SpanStatus, description string) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.status = status
	s.statusMsg = description
}

// RecordError records an error event
func (s *Span) RecordError(err error) {
	if err == nil {
		return
	}
	s.AddEvent("exception", String("exception.message", err.Error()))
	s.SetStatus(StatusError, err.Error())
}

// End ends the span
func (s *Span) End() {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.ended {
		return
	}
	s.ended = true
	s.endTime = time.Now()
}

// IsEnded returns whether the span has ended
func (s *Span) IsEnded() bool {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.ended
}

// Duration returns the span duration
func (s *Span) Duration() time.Duration {
	s.mu.RLock()
	defer s.mu.RUnlock()
	if s.ended {
		return s.endTime.Sub(s.startTime)
	}
	return time.Since(s.startTime)
}

// Attributes returns all attributes
func (s *Span) Attributes() []Attribute {
	s.mu.RLock()
	defer s.mu.RUnlock()
	result := make([]Attribute, len(s.attributes))
	copy(result, s.attributes)
	return result
}

// Events returns all events
func (s *Span) Events() []Event {
	s.mu.RLock()
	defer s.mu.RUnlock()
	result := make([]Event, len(s.events))
	copy(result, s.events)
	return result
}

// Tracer creates and manages spans
type Tracer struct {
	name     string
	version  string
	spans    []*Span
	exporter SpanExporter
	mu       sync.RWMutex
}

// SpanExporter exports spans
type SpanExporter interface {
	Export(ctx context.Context, spans []*Span) error
	Shutdown(ctx context.Context) error
}

// TracerOption configures a tracer
type TracerOption func(*Tracer)

// WithExporter sets the span exporter
func WithExporter(exp SpanExporter) TracerOption {
	return func(t *Tracer) {
		t.exporter = exp
	}
}

// NewTracer creates a new tracer
func NewTracer(name string, opts ...TracerOption) *Tracer {
	t := &Tracer{
		name:  name,
		spans: make([]*Span, 0),
	}

	for _, opt := range opts {
		opt(t)
	}

	return t
}

// Start creates and starts a new span
func (t *Tracer) Start(ctx context.Context, name string, opts ...SpanOption) (context.Context, *Span) {
	span := NewSpan(name, opts...)

	t.mu.Lock()
	t.spans = append(t.spans, span)
	t.mu.Unlock()

	return context.WithValue(ctx, spanKey{}, span), span
}

type spanKey struct{}

// SpanFromContext returns the current span from context
func SpanFromContext(ctx context.Context) *Span {
	if span, ok := ctx.Value(spanKey{}).(*Span); ok {
		return span
	}
	return nil
}

// Spans returns all recorded spans
func (t *Tracer) Spans() []*Span {
	t.mu.RLock()
	defer t.mu.RUnlock()
	result := make([]*Span, len(t.spans))
	copy(result, t.spans)
	return result
}

// Flush exports all recorded spans
func (t *Tracer) Flush(ctx context.Context) error {
	t.mu.Lock()
	spans := t.spans
	t.spans = make([]*Span, 0)
	t.mu.Unlock()

	if t.exporter != nil && len(spans) > 0 {
		return t.exporter.Export(ctx, spans)
	}
	return nil
}

// Shutdown shuts down the tracer
func (t *Tracer) Shutdown(ctx context.Context) error {
	if err := t.Flush(ctx); err != nil {
		return err
	}
	if t.exporter != nil {
		return t.exporter.Shutdown(ctx)
	}
	return nil
}

// InMemoryExporter stores spans in memory (for testing)
type InMemoryExporter struct {
	spans []*Span
	mu    sync.Mutex
}

// NewInMemoryExporter creates a new in-memory exporter
func NewInMemoryExporter() *InMemoryExporter {
	return &InMemoryExporter{
		spans: make([]*Span, 0),
	}
}

// Export exports spans to memory
func (e *InMemoryExporter) Export(ctx context.Context, spans []*Span) error {
	e.mu.Lock()
	e.spans = append(e.spans, spans...)
	e.mu.Unlock()
	return nil
}

// Shutdown shuts down the exporter
func (e *InMemoryExporter) Shutdown(ctx context.Context) error {
	return nil
}

// Spans returns all exported spans
func (e *InMemoryExporter) Spans() []*Span {
	e.mu.Lock()
	defer e.mu.Unlock()
	result := make([]*Span, len(e.spans))
	copy(result, e.spans)
	return result
}

// Reset clears all spans
func (e *InMemoryExporter) Reset() {
	e.mu.Lock()
	e.spans = make([]*Span, 0)
	e.mu.Unlock()
}

// GoMCP specific tracing
type GoMCPTracer struct {
	*Tracer
}

// NewGoMCPTracer creates a GoMCP-specific tracer
func NewGoMCPTracer(opts ...TracerOption) *GoMCPTracer {
	return &GoMCPTracer{
		Tracer: NewTracer("gomcp", opts...),
	}
}

// TraceToolCall creates a span for a tool call
func (t *GoMCPTracer) TraceToolCall(ctx context.Context, toolName string) (context.Context, *Span) {
	return t.Start(ctx, "tool.call",
		WithSpanKind(SpanKindServer),
		WithAttributes(String("tool.name", toolName)),
	)
}

// TraceValidation creates a span for validation
func (t *GoMCPTracer) TraceValidation(ctx context.Context) (context.Context, *Span) {
	return t.Start(ctx, "validation",
		WithSpanKind(SpanKindInternal),
	)
}

// TraceBatch creates a span for batch processing
func (t *GoMCPTracer) TraceBatch(ctx context.Context, size int) (context.Context, *Span) {
	return t.Start(ctx, "batch.process",
		WithSpanKind(SpanKindServer),
		WithAttributes(Int("batch.size", size)),
	)
}

// Simple ID generator (use crypto/rand in production)
var idCounter uint64
var idMu sync.Mutex

func generateID() string {
	idMu.Lock()
	idCounter++
	id := idCounter
	idMu.Unlock()

	// Simple hex encoding
	return uintToHex(id)
}

func uintToHex(n uint64) string {
	const hexChars = "0123456789abcdef"
	if n == 0 {
		return "0000000000000001"
	}
	result := make([]byte, 16)
	for i := 15; i >= 0; i-- {
		result[i] = hexChars[n&0xf]
		n >>= 4
	}
	return string(result)
}
