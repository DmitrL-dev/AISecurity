package tracing

import (
	"context"
	"errors"
	"sync"
	"testing"
	"time"
)

// Attribute tests
func TestString(t *testing.T) {
	attr := String("key", "value")
	if attr.Key != "key" {
		t.Errorf("expected key, got %s", attr.Key)
	}
	if attr.Value != "value" {
		t.Errorf("expected value, got %v", attr.Value)
	}
}

func TestInt(t *testing.T) {
	attr := Int("count", 42)
	if attr.Key != "count" {
		t.Errorf("expected count, got %s", attr.Key)
	}
	if attr.Value != 42 {
		t.Errorf("expected 42, got %v", attr.Value)
	}
}

func TestInt64(t *testing.T) {
	attr := Int64("bignum", int64(1<<40))
	if attr.Value != int64(1<<40) {
		t.Errorf("expected %d, got %v", int64(1<<40), attr.Value)
	}
}

func TestFloat64(t *testing.T) {
	attr := Float64("rate", 3.14)
	if attr.Value != 3.14 {
		t.Errorf("expected 3.14, got %v", attr.Value)
	}
}

func TestBool(t *testing.T) {
	attr := Bool("enabled", true)
	if attr.Value != true {
		t.Errorf("expected true, got %v", attr.Value)
	}
}

// Span tests
func TestNewSpan(t *testing.T) {
	span := NewSpan("test-span")
	if span == nil {
		t.Fatal("span should not be nil")
	}
	if span.Name() != "test-span" {
		t.Errorf("expected test-span, got %s", span.Name())
	}
}

func TestSpan_SpanContext(t *testing.T) {
	span := NewSpan("test")
	ctx := span.SpanContext()
	if ctx.TraceID == "" {
		t.Error("trace ID should not be empty")
	}
	if ctx.SpanID == "" {
		t.Error("span ID should not be empty")
	}
}

func TestSpan_WithParent(t *testing.T) {
	parent := NewSpan("parent")
	child := NewSpan("child", WithParent(parent))

	if child.traceID != parent.traceID {
		t.Error("child should inherit parent trace ID")
	}
	if child.parentID != parent.spanID {
		t.Error("child parent ID should be parent's span ID")
	}
}

func TestSpan_WithSpanKind(t *testing.T) {
	span := NewSpan("test", WithSpanKind(SpanKindServer))
	if span.kind != SpanKindServer {
		t.Errorf("expected SpanKindServer, got %d", span.kind)
	}
}

func TestSpan_WithAttributes(t *testing.T) {
	span := NewSpan("test", WithAttributes(String("key", "value")))
	attrs := span.Attributes()
	if len(attrs) != 1 {
		t.Errorf("expected 1 attribute, got %d", len(attrs))
	}
}

func TestSpan_WithLinks(t *testing.T) {
	link := Link{TraceID: "trace1", SpanID: "span1"}
	span := NewSpan("test", WithLinks(link))
	if len(span.links) != 1 {
		t.Errorf("expected 1 link, got %d", len(span.links))
	}
}

func TestSpan_SetAttribute(t *testing.T) {
	span := NewSpan("test")
	span.SetAttribute(String("key", "value"))
	attrs := span.Attributes()
	if len(attrs) != 1 {
		t.Errorf("expected 1 attribute, got %d", len(attrs))
	}
}

func TestSpan_SetAttributes(t *testing.T) {
	span := NewSpan("test")
	span.SetAttributes(String("k1", "v1"), String("k2", "v2"))
	attrs := span.Attributes()
	if len(attrs) != 2 {
		t.Errorf("expected 2 attributes, got %d", len(attrs))
	}
}

func TestSpan_AddEvent(t *testing.T) {
	span := NewSpan("test")
	span.AddEvent("event1", String("detail", "info"))
	events := span.Events()
	if len(events) != 1 {
		t.Errorf("expected 1 event, got %d", len(events))
	}
	if events[0].Name != "event1" {
		t.Errorf("expected event1, got %s", events[0].Name)
	}
}

func TestSpan_SetStatus(t *testing.T) {
	span := NewSpan("test")
	span.SetStatus(StatusOK, "success")
	if span.status != StatusOK {
		t.Errorf("expected StatusOK, got %d", span.status)
	}
	if span.statusMsg != "success" {
		t.Errorf("expected success, got %s", span.statusMsg)
	}
}

func TestSpan_RecordError(t *testing.T) {
	span := NewSpan("test")
	span.RecordError(errors.New("test error"))
	if span.status != StatusError {
		t.Error("status should be error")
	}
	events := span.Events()
	if len(events) != 1 {
		t.Error("should have exception event")
	}
}

func TestSpan_RecordError_Nil(t *testing.T) {
	span := NewSpan("test")
	span.RecordError(nil)
	events := span.Events()
	if len(events) != 0 {
		t.Error("should have no events for nil error")
	}
}

func TestSpan_End(t *testing.T) {
	span := NewSpan("test")
	if span.IsEnded() {
		t.Error("span should not be ended")
	}
	span.End()
	if !span.IsEnded() {
		t.Error("span should be ended")
	}
}

func TestSpan_End_Idempotent(t *testing.T) {
	span := NewSpan("test")
	span.End()
	span.End()
	if !span.IsEnded() {
		t.Error("span should be ended")
	}
}

func TestSpan_Duration(t *testing.T) {
	span := NewSpan("test")
	time.Sleep(10 * time.Millisecond)
	span.End()
	d := span.Duration()
	if d < 10*time.Millisecond {
		t.Errorf("duration should be at least 10ms, got %v", d)
	}
}

func TestSpan_Duration_NotEnded(t *testing.T) {
	span := NewSpan("test")
	time.Sleep(5 * time.Millisecond)
	d := span.Duration()
	if d < 5*time.Millisecond {
		t.Errorf("duration should be at least 5ms, got %v", d)
	}
}

func TestSpan_Concurrent(t *testing.T) {
	span := NewSpan("test")
	var wg sync.WaitGroup

	for i := 0; i < 100; i++ {
		wg.Add(1)
		go func(n int) {
			defer wg.Done()
			span.SetAttribute(Int("attr", n))
			span.AddEvent("event")
		}(i)
	}
	wg.Wait()
}

// Tracer tests
func TestNewTracer(t *testing.T) {
	tracer := NewTracer("test-tracer")
	if tracer == nil {
		t.Fatal("tracer should not be nil")
	}
}

func TestTracer_Start(t *testing.T) {
	tracer := NewTracer("test")
	ctx, span := tracer.Start(context.Background(), "span1")
	if span == nil {
		t.Fatal("span should not be nil")
	}
	if ctx == nil {
		t.Fatal("context should not be nil")
	}
}

func TestSpanFromContext(t *testing.T) {
	tracer := NewTracer("test")
	ctx, span := tracer.Start(context.Background(), "span1")

	retrieved := SpanFromContext(ctx)
	if retrieved != span {
		t.Error("should retrieve same span from context")
	}
}

func TestSpanFromContext_Empty(t *testing.T) {
	span := SpanFromContext(context.Background())
	if span != nil {
		t.Error("should return nil for empty context")
	}
}

func TestTracer_Spans(t *testing.T) {
	tracer := NewTracer("test")
	tracer.Start(context.Background(), "span1")
	tracer.Start(context.Background(), "span2")

	spans := tracer.Spans()
	if len(spans) != 2 {
		t.Errorf("expected 2 spans, got %d", len(spans))
	}
}

func TestTracer_WithExporter(t *testing.T) {
	exp := NewInMemoryExporter()
	tracer := NewTracer("test", WithExporter(exp))

	tracer.Start(context.Background(), "span1")
	tracer.Flush(context.Background())

	if len(exp.Spans()) != 1 {
		t.Errorf("expected 1 exported span, got %d", len(exp.Spans()))
	}
}

func TestTracer_Flush(t *testing.T) {
	tracer := NewTracer("test")
	tracer.Start(context.Background(), "span1")

	err := tracer.Flush(context.Background())
	if err != nil {
		t.Errorf("flush error: %v", err)
	}

	if len(tracer.Spans()) != 0 {
		t.Error("spans should be cleared after flush")
	}
}

func TestTracer_Shutdown(t *testing.T) {
	exp := NewInMemoryExporter()
	tracer := NewTracer("test", WithExporter(exp))
	tracer.Start(context.Background(), "span1")

	err := tracer.Shutdown(context.Background())
	if err != nil {
		t.Errorf("shutdown error: %v", err)
	}
}

// InMemoryExporter tests
func TestNewInMemoryExporter(t *testing.T) {
	exp := NewInMemoryExporter()
	if exp == nil {
		t.Fatal("exporter should not be nil")
	}
}

func TestInMemoryExporter_Export(t *testing.T) {
	exp := NewInMemoryExporter()
	span := NewSpan("test")

	err := exp.Export(context.Background(), []*Span{span})
	if err != nil {
		t.Errorf("export error: %v", err)
	}

	if len(exp.Spans()) != 1 {
		t.Errorf("expected 1 span, got %d", len(exp.Spans()))
	}
}

func TestInMemoryExporter_Reset(t *testing.T) {
	exp := NewInMemoryExporter()
	exp.Export(context.Background(), []*Span{NewSpan("test")})
	exp.Reset()

	if len(exp.Spans()) != 0 {
		t.Error("should be empty after reset")
	}
}

func TestInMemoryExporter_Shutdown(t *testing.T) {
	exp := NewInMemoryExporter()
	err := exp.Shutdown(context.Background())
	if err != nil {
		t.Errorf("shutdown error: %v", err)
	}
}

// GoMCPTracer tests
func TestNewGoMCPTracer(t *testing.T) {
	tracer := NewGoMCPTracer()
	if tracer == nil {
		t.Fatal("tracer should not be nil")
	}
}

func TestGoMCPTracer_TraceToolCall(t *testing.T) {
	tracer := NewGoMCPTracer()
	ctx, span := tracer.TraceToolCall(context.Background(), "my-tool")

	if span == nil {
		t.Fatal("span should not be nil")
	}
	if ctx == nil {
		t.Fatal("context should not be nil")
	}
	if span.kind != SpanKindServer {
		t.Error("should be server span")
	}

	// Check tool.name attribute
	attrs := span.Attributes()
	found := false
	for _, attr := range attrs {
		if attr.Key == "tool.name" && attr.Value == "my-tool" {
			found = true
		}
	}
	if !found {
		t.Error("should have tool.name attribute")
	}
}

func TestGoMCPTracer_TraceValidation(t *testing.T) {
	tracer := NewGoMCPTracer()
	_, span := tracer.TraceValidation(context.Background())

	if span.Name() != "validation" {
		t.Errorf("expected validation, got %s", span.Name())
	}
}

func TestGoMCPTracer_TraceBatch(t *testing.T) {
	tracer := NewGoMCPTracer()
	_, span := tracer.TraceBatch(context.Background(), 10)

	attrs := span.Attributes()
	found := false
	for _, attr := range attrs {
		if attr.Key == "batch.size" && attr.Value == 10 {
			found = true
		}
	}
	if !found {
		t.Error("should have batch.size attribute")
	}
}

// Helper tests
func TestGenerateID(t *testing.T) {
	id1 := generateID()
	id2 := generateID()

	if id1 == "" {
		t.Error("ID should not be empty")
	}
	if id1 == id2 {
		t.Error("IDs should be unique")
	}
}

func TestUintToHex(t *testing.T) {
	result := uintToHex(255)
	if len(result) != 16 {
		t.Errorf("expected 16 chars, got %d", len(result))
	}
}

func TestUintToHex_Zero(t *testing.T) {
	result := uintToHex(0)
	if result != "0000000000000001" {
		t.Errorf("expected 0000000000000001, got %s", result)
	}
}

// SpanKind tests
func TestSpanKind_Values(t *testing.T) {
	if SpanKindInternal != 0 {
		t.Error("SpanKindInternal should be 0")
	}
	if SpanKindServer != 1 {
		t.Error("SpanKindServer should be 1")
	}
	if SpanKindClient != 2 {
		t.Error("SpanKindClient should be 2")
	}
}

// SpanStatus tests
func TestSpanStatus_Values(t *testing.T) {
	if StatusUnset != 0 {
		t.Error("StatusUnset should be 0")
	}
	if StatusOK != 1 {
		t.Error("StatusOK should be 1")
	}
	if StatusError != 2 {
		t.Error("StatusError should be 2")
	}
}

// Benchmark tests
func BenchmarkSpan_Create(b *testing.B) {
	for i := 0; i < b.N; i++ {
		NewSpan("test")
	}
}

func BenchmarkSpan_SetAttribute(b *testing.B) {
	span := NewSpan("test")
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		span.SetAttribute(Int("i", i))
	}
}

func BenchmarkSpan_AddEvent(b *testing.B) {
	span := NewSpan("test")
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		span.AddEvent("event")
	}
}

func BenchmarkTracer_Start(b *testing.B) {
	tracer := NewTracer("test")
	ctx := context.Background()
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		tracer.Start(ctx, "span")
	}
}
