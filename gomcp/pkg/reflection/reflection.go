// Package reflection provides gRPC reflection support for GoMCP.
package reflection

import (
	"encoding/json"
	"net/http"
	"sync"
)

// MethodInfo describes a gRPC method
type MethodInfo struct {
	Name           string          `json:"name"`
	InputType      string          `json:"inputType"`
	OutputType     string          `json:"outputType"`
	IsClientStream bool            `json:"isClientStream,omitempty"`
	IsServerStream bool            `json:"isServerStream,omitempty"`
	Description    string          `json:"description,omitempty"`
	InputSchema    json.RawMessage `json:"inputSchema,omitempty"`
	OutputSchema   json.RawMessage `json:"outputSchema,omitempty"`
}

// ServiceInfo describes a gRPC service
type ServiceInfo struct {
	Name        string       `json:"name"`
	Package     string       `json:"package,omitempty"`
	Description string       `json:"description,omitempty"`
	Methods     []MethodInfo `json:"methods"`
}

// Registry holds service metadata for reflection
type Registry struct {
	services map[string]*ServiceInfo
	mu       sync.RWMutex
}

// NewRegistry creates a new reflection registry
func NewRegistry() *Registry {
	return &Registry{
		services: make(map[string]*ServiceInfo),
	}
}

// RegisterService registers a service
func (r *Registry) RegisterService(service *ServiceInfo) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.services[service.Name] = service
}

// UnregisterService removes a service
func (r *Registry) UnregisterService(name string) {
	r.mu.Lock()
	defer r.mu.Unlock()
	delete(r.services, name)
}

// GetService returns a service by name
func (r *Registry) GetService(name string) (*ServiceInfo, bool) {
	r.mu.RLock()
	defer r.mu.RUnlock()
	svc, ok := r.services[name]
	return svc, ok
}

// ListServices returns all registered services
func (r *Registry) ListServices() []*ServiceInfo {
	r.mu.RLock()
	defer r.mu.RUnlock()

	result := make([]*ServiceInfo, 0, len(r.services))
	for _, svc := range r.services {
		result = append(result, svc)
	}
	return result
}

// ServiceCount returns the number of registered services
func (r *Registry) ServiceCount() int {
	r.mu.RLock()
	defer r.mu.RUnlock()
	return len(r.services)
}

// GetMethod returns a method by service and method name
func (r *Registry) GetMethod(serviceName, methodName string) (*MethodInfo, bool) {
	r.mu.RLock()
	defer r.mu.RUnlock()

	svc, ok := r.services[serviceName]
	if !ok {
		return nil, false
	}

	for i, m := range svc.Methods {
		if m.Name == methodName {
			return &svc.Methods[i], true
		}
	}
	return nil, false
}

// Handler returns an HTTP handler for reflection API
func (r *Registry) Handler() http.Handler {
	mux := http.NewServeMux()

	// List all services
	mux.HandleFunc("/reflection/services", func(w http.ResponseWriter, req *http.Request) {
		if req.Method != http.MethodGet {
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}

		services := r.ListServices()
		writeJSON(w, map[string]interface{}{
			"services": services,
		})
	})

	// Get service details
	mux.HandleFunc("/reflection/service/", func(w http.ResponseWriter, req *http.Request) {
		if req.Method != http.MethodGet {
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}

		name := req.URL.Path[len("/reflection/service/"):]
		if name == "" {
			http.Error(w, "service name required", http.StatusBadRequest)
			return
		}

		svc, ok := r.GetService(name)
		if !ok {
			http.Error(w, "service not found", http.StatusNotFound)
			return
		}

		writeJSON(w, svc)
	})

	return mux
}

func writeJSON(w http.ResponseWriter, data interface{}) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(data)
}

// GoMCPReflection provides GoMCP-specific reflection
type GoMCPReflection struct {
	*Registry
}

// NewGoMCPReflection creates a GoMCP reflection instance with default services
func NewGoMCPReflection() *GoMCPReflection {
	r := &GoMCPReflection{
		Registry: NewRegistry(),
	}

	// Register GoMCP service
	r.RegisterService(&ServiceInfo{
		Name:        "gomcp.GoMCP",
		Package:     "gomcp",
		Description: "GoMCP tool execution service",
		Methods: []MethodInfo{
			{
				Name:        "ListTools",
				InputType:   "gomcp.ListToolsRequest",
				OutputType:  "gomcp.ListToolsResponse",
				Description: "List all available tools",
			},
			{
				Name:        "CallTool",
				InputType:   "gomcp.CallToolRequest",
				OutputType:  "gomcp.CallToolResponse",
				Description: "Execute a single tool",
			},
			{
				Name:        "BatchCall",
				InputType:   "gomcp.BatchCallRequest",
				OutputType:  "gomcp.BatchCallResponse",
				Description: "Execute multiple tools in batch",
			},
			{
				Name:           "StreamCall",
				InputType:      "gomcp.StreamCallRequest",
				OutputType:     "gomcp.StreamCallResponse",
				IsServerStream: true,
				Description:    "Execute tool with streaming response",
			},
		},
	})

	// Register Health service
	r.RegisterService(&ServiceInfo{
		Name:        "grpc.health.v1.Health",
		Package:     "grpc.health.v1",
		Description: "gRPC health checking protocol",
		Methods: []MethodInfo{
			{
				Name:        "Check",
				InputType:   "grpc.health.v1.HealthCheckRequest",
				OutputType:  "grpc.health.v1.HealthCheckResponse",
				Description: "Check health status",
			},
			{
				Name:           "Watch",
				InputType:      "grpc.health.v1.HealthCheckRequest",
				OutputType:     "grpc.health.v1.HealthCheckResponse",
				IsServerStream: true,
				Description:    "Watch health status changes",
			},
		},
	})

	return r
}

// ServiceDescriptor provides detailed service information
type ServiceDescriptor struct {
	FullName string             `json:"fullName"`
	Methods  []MethodDescriptor `json:"methods"`
	Options  map[string]string  `json:"options,omitempty"`
}

// MethodDescriptor provides detailed method information
type MethodDescriptor struct {
	Name    string            `json:"name"`
	Input   TypeDescriptor    `json:"input"`
	Output  TypeDescriptor    `json:"output"`
	Options map[string]string `json:"options,omitempty"`
}

// TypeDescriptor describes a message type
type TypeDescriptor struct {
	Name   string  `json:"name"`
	Fields []Field `json:"fields"`
}

// Field describes a message field
type Field struct {
	Name     string `json:"name"`
	Number   int    `json:"number"`
	Type     string `json:"type"`
	Repeated bool   `json:"repeated,omitempty"`
}

// Builder helps construct service definitions
type Builder struct {
	service *ServiceInfo
}

// NewBuilder creates a new service builder
func NewBuilder(name string) *Builder {
	return &Builder{
		service: &ServiceInfo{
			Name:    name,
			Methods: make([]MethodInfo, 0),
		},
	}
}

// Package sets the package name
func (b *Builder) Package(pkg string) *Builder {
	b.service.Package = pkg
	return b
}

// Description sets the service description
func (b *Builder) Description(desc string) *Builder {
	b.service.Description = desc
	return b
}

// AddMethod adds a method to the service
func (b *Builder) AddMethod(name, inputType, outputType string) *Builder {
	b.service.Methods = append(b.service.Methods, MethodInfo{
		Name:       name,
		InputType:  inputType,
		OutputType: outputType,
	})
	return b
}

// AddStreamingMethod adds a streaming method
func (b *Builder) AddStreamingMethod(name, inputType, outputType string, clientStream, serverStream bool) *Builder {
	b.service.Methods = append(b.service.Methods, MethodInfo{
		Name:           name,
		InputType:      inputType,
		OutputType:     outputType,
		IsClientStream: clientStream,
		IsServerStream: serverStream,
	})
	return b
}

// Build returns the constructed service
func (b *Builder) Build() *ServiceInfo {
	return b.service
}
