package reflection

import (
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"sync"
	"testing"
)

// MethodInfo tests
func TestMethodInfo_Create(t *testing.T) {
	m := MethodInfo{
		Name:       "TestMethod",
		InputType:  "TestRequest",
		OutputType: "TestResponse",
	}

	if m.Name != "TestMethod" {
		t.Errorf("expected TestMethod, got %s", m.Name)
	}
}

func TestMethodInfo_Streaming(t *testing.T) {
	m := MethodInfo{
		Name:           "StreamMethod",
		IsServerStream: true,
		IsClientStream: false,
	}

	if !m.IsServerStream {
		t.Error("should be server streaming")
	}
	if m.IsClientStream {
		t.Error("should not be client streaming")
	}
}

// ServiceInfo tests
func TestServiceInfo_Create(t *testing.T) {
	s := ServiceInfo{
		Name:    "TestService",
		Package: "test",
		Methods: []MethodInfo{
			{Name: "Method1"},
		},
	}

	if s.Name != "TestService" {
		t.Errorf("expected TestService, got %s", s.Name)
	}
	if len(s.Methods) != 1 {
		t.Errorf("expected 1 method, got %d", len(s.Methods))
	}
}

// Registry tests
func TestNewRegistry(t *testing.T) {
	r := NewRegistry()
	if r == nil {
		t.Fatal("registry should not be nil")
	}
}

func TestRegistry_RegisterService(t *testing.T) {
	r := NewRegistry()
	svc := &ServiceInfo{Name: "test.Service"}

	r.RegisterService(svc)

	got, ok := r.GetService("test.Service")
	if !ok {
		t.Error("service not found")
	}
	if got.Name != "test.Service" {
		t.Error("name mismatch")
	}
}

func TestRegistry_UnregisterService(t *testing.T) {
	r := NewRegistry()
	r.RegisterService(&ServiceInfo{Name: "test.Service"})

	r.UnregisterService("test.Service")

	_, ok := r.GetService("test.Service")
	if ok {
		t.Error("service should be removed")
	}
}

func TestRegistry_GetService_NotFound(t *testing.T) {
	r := NewRegistry()
	_, ok := r.GetService("nonexistent")
	if ok {
		t.Error("should not find service")
	}
}

func TestRegistry_ListServices(t *testing.T) {
	r := NewRegistry()
	r.RegisterService(&ServiceInfo{Name: "svc1"})
	r.RegisterService(&ServiceInfo{Name: "svc2"})

	services := r.ListServices()
	if len(services) != 2 {
		t.Errorf("expected 2 services, got %d", len(services))
	}
}

func TestRegistry_ServiceCount(t *testing.T) {
	r := NewRegistry()
	if r.ServiceCount() != 0 {
		t.Error("should be empty")
	}

	r.RegisterService(&ServiceInfo{Name: "svc1"})
	if r.ServiceCount() != 1 {
		t.Errorf("expected 1, got %d", r.ServiceCount())
	}
}

func TestRegistry_GetMethod(t *testing.T) {
	r := NewRegistry()
	r.RegisterService(&ServiceInfo{
		Name: "test.Service",
		Methods: []MethodInfo{
			{Name: "Method1"},
			{Name: "Method2"},
		},
	})

	m, ok := r.GetMethod("test.Service", "Method1")
	if !ok {
		t.Error("method not found")
	}
	if m.Name != "Method1" {
		t.Error("wrong method")
	}
}

func TestRegistry_GetMethod_ServiceNotFound(t *testing.T) {
	r := NewRegistry()
	_, ok := r.GetMethod("nonexistent", "Method1")
	if ok {
		t.Error("should not find method")
	}
}

func TestRegistry_GetMethod_MethodNotFound(t *testing.T) {
	r := NewRegistry()
	r.RegisterService(&ServiceInfo{Name: "test.Service"})

	_, ok := r.GetMethod("test.Service", "nonexistent")
	if ok {
		t.Error("should not find method")
	}
}

// Registry concurrent tests
func TestRegistry_Concurrent(t *testing.T) {
	r := NewRegistry()
	var wg sync.WaitGroup

	for i := 0; i < 100; i++ {
		wg.Add(2)
		go func(n int) {
			defer wg.Done()
			r.RegisterService(&ServiceInfo{Name: "svc"})
		}(i)
		go func(n int) {
			defer wg.Done()
			r.ListServices()
		}(i)
	}
	wg.Wait()
}

// Handler tests
func TestRegistry_Handler(t *testing.T) {
	r := NewRegistry()
	handler := r.Handler()
	if handler == nil {
		t.Fatal("handler should not be nil")
	}
}

func TestRegistry_Handler_ListServices(t *testing.T) {
	r := NewRegistry()
	r.RegisterService(&ServiceInfo{Name: "test.Service"})

	handler := r.Handler()
	req := httptest.NewRequest("GET", "/reflection/services", nil)
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)

	resp := w.Result()
	if resp.StatusCode != http.StatusOK {
		t.Errorf("expected 200, got %d", resp.StatusCode)
	}

	body, _ := io.ReadAll(resp.Body)
	var result map[string]interface{}
	json.Unmarshal(body, &result)

	services, ok := result["services"].([]interface{})
	if !ok {
		t.Fatal("services not found in response")
	}
	if len(services) != 1 {
		t.Errorf("expected 1 service, got %d", len(services))
	}
}

func TestRegistry_Handler_GetService(t *testing.T) {
	r := NewRegistry()
	r.RegisterService(&ServiceInfo{Name: "test.Service", Description: "Test"})

	handler := r.Handler()
	req := httptest.NewRequest("GET", "/reflection/service/test.Service", nil)
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)

	resp := w.Result()
	if resp.StatusCode != http.StatusOK {
		t.Errorf("expected 200, got %d", resp.StatusCode)
	}
}

func TestRegistry_Handler_GetService_NotFound(t *testing.T) {
	r := NewRegistry()

	handler := r.Handler()
	req := httptest.NewRequest("GET", "/reflection/service/nonexistent", nil)
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)

	resp := w.Result()
	if resp.StatusCode != http.StatusNotFound {
		t.Errorf("expected 404, got %d", resp.StatusCode)
	}
}

func TestRegistry_Handler_MethodNotAllowed(t *testing.T) {
	r := NewRegistry()

	handler := r.Handler()
	req := httptest.NewRequest("POST", "/reflection/services", nil)
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)

	resp := w.Result()
	if resp.StatusCode != http.StatusMethodNotAllowed {
		t.Errorf("expected 405, got %d", resp.StatusCode)
	}
}

// GoMCPReflection tests
func TestNewGoMCPReflection(t *testing.T) {
	r := NewGoMCPReflection()
	if r == nil {
		t.Fatal("should not be nil")
	}
}

func TestGoMCPReflection_HasDefaultServices(t *testing.T) {
	r := NewGoMCPReflection()

	// Should have GoMCP service
	_, ok := r.GetService("gomcp.GoMCP")
	if !ok {
		t.Error("should have gomcp.GoMCP service")
	}

	// Should have Health service
	_, ok = r.GetService("grpc.health.v1.Health")
	if !ok {
		t.Error("should have grpc.health.v1.Health service")
	}
}

func TestGoMCPReflection_GoMCPMethods(t *testing.T) {
	r := NewGoMCPReflection()
	svc, _ := r.GetService("gomcp.GoMCP")

	methodNames := make(map[string]bool)
	for _, m := range svc.Methods {
		methodNames[m.Name] = true
	}

	expected := []string{"ListTools", "CallTool", "BatchCall", "StreamCall"}
	for _, name := range expected {
		if !methodNames[name] {
			t.Errorf("missing method: %s", name)
		}
	}
}

// Builder tests
func TestNewBuilder(t *testing.T) {
	b := NewBuilder("test.Service")
	if b == nil {
		t.Fatal("builder should not be nil")
	}
}

func TestBuilder_Package(t *testing.T) {
	svc := NewBuilder("test.Service").
		Package("test").
		Build()

	if svc.Package != "test" {
		t.Errorf("expected test, got %s", svc.Package)
	}
}

func TestBuilder_Description(t *testing.T) {
	svc := NewBuilder("test.Service").
		Description("Test service").
		Build()

	if svc.Description != "Test service" {
		t.Errorf("expected Test service, got %s", svc.Description)
	}
}

func TestBuilder_AddMethod(t *testing.T) {
	svc := NewBuilder("test.Service").
		AddMethod("Method1", "Input", "Output").
		Build()

	if len(svc.Methods) != 1 {
		t.Errorf("expected 1 method, got %d", len(svc.Methods))
	}
	if svc.Methods[0].Name != "Method1" {
		t.Error("wrong method name")
	}
}

func TestBuilder_AddStreamingMethod(t *testing.T) {
	svc := NewBuilder("test.Service").
		AddStreamingMethod("Stream", "In", "Out", false, true).
		Build()

	if len(svc.Methods) != 1 {
		t.Fatal("expected 1 method")
	}
	if !svc.Methods[0].IsServerStream {
		t.Error("should be server streaming")
	}
}

func TestBuilder_Chaining(t *testing.T) {
	svc := NewBuilder("test.Service").
		Package("test").
		Description("Test").
		AddMethod("M1", "I1", "O1").
		AddMethod("M2", "I2", "O2").
		Build()

	if svc.Name != "test.Service" {
		t.Error("name not set")
	}
	if svc.Package != "test" {
		t.Error("package not set")
	}
	if len(svc.Methods) != 2 {
		t.Errorf("expected 2 methods, got %d", len(svc.Methods))
	}
}

// Type descriptor tests
func TestServiceDescriptor(t *testing.T) {
	sd := ServiceDescriptor{
		FullName: "test.Service",
		Methods:  []MethodDescriptor{},
	}

	if sd.FullName != "test.Service" {
		t.Error("fullname mismatch")
	}
}

func TestTypeDescriptor(t *testing.T) {
	td := TypeDescriptor{
		Name:   "TestMessage",
		Fields: []Field{{Name: "field1", Number: 1, Type: "string"}},
	}

	if td.Name != "TestMessage" {
		t.Error("name mismatch")
	}
	if len(td.Fields) != 1 {
		t.Error("expected 1 field")
	}
}

func TestField(t *testing.T) {
	f := Field{
		Name:     "items",
		Number:   1,
		Type:     "string",
		Repeated: true,
	}

	if !f.Repeated {
		t.Error("should be repeated")
	}
}

// Benchmark tests
func BenchmarkRegistry_GetService(b *testing.B) {
	r := NewRegistry()
	r.RegisterService(&ServiceInfo{Name: "test.Service"})

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		r.GetService("test.Service")
	}
}

func BenchmarkRegistry_ListServices(b *testing.B) {
	r := NewRegistry()
	for i := 0; i < 10; i++ {
		r.RegisterService(&ServiceInfo{Name: uintToString(uint64(i))})
	}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		r.ListServices()
	}
}

func uintToString(n uint64) string {
	if n == 0 {
		return "0"
	}
	result := make([]byte, 0, 20)
	for n > 0 {
		result = append([]byte{byte('0' + n%10)}, result...)
		n /= 10
	}
	return string(result)
}
