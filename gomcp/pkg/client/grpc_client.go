package client

import (
	"context"
	"encoding/json"
	"fmt"
	"sync"
	"sync/atomic"
	"time"

	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials"
	"google.golang.org/grpc/credentials/insecure"
	"google.golang.org/grpc/metadata"
)

// GRPCClient communicates with MCP server via gRPC
type GRPCClient struct {
	*BaseClient

	conn      *grpc.ClientConn
	requestID int64

	// Auth
	authToken string
	tenantID  string

	// Streams
	streamMu sync.Mutex
}

// GRPCConfig configures gRPC client
type GRPCConfig struct {
	ClientConfig

	// Server address
	Address string

	// Auth token (JWT)
	AuthToken string

	// Tenant ID for multi-tenancy
	TenantID string

	// TLS
	UseTLS             bool
	InsecureSkipVerify bool
	CertFile           string
}

// NewGRPCClient creates a new gRPC client
func NewGRPCClient(cfg GRPCConfig) *GRPCClient {
	if cfg.ClientConfig.Name == "" {
		cfg.ClientConfig = DefaultConfig()
	}

	return &GRPCClient{
		BaseClient: NewBaseClient(cfg.ClientConfig),
		authToken:  cfg.AuthToken,
		tenantID:   cfg.TenantID,
	}
}

// Connect establishes gRPC connection
func (c *GRPCClient) Connect(ctx context.Context) error {
	if c.IsConnected() {
		return ErrAlreadyConnected
	}

	// Note: Actual gRPC proto would be needed for full implementation
	// This is a placeholder showing the structure
	c.setConnected(true, &ServerInfo{
		Name:    "gomcp",
		Version: "1.0.0",
	}, &ServerCapabilities{})

	return nil
}

// Close disconnects gRPC
func (c *GRPCClient) Close() error {
	if c.conn != nil {
		c.conn.Close()
	}
	c.setConnected(false, nil, nil)
	return nil
}

// ListTools returns available tools via gRPC
func (c *GRPCClient) ListTools(ctx context.Context) ([]Tool, error) {
	if !c.IsConnected() {
		return nil, ErrNotConnected
	}

	// Placeholder - would use generated gRPC client
	return []Tool{}, nil
}

// CallTool invokes a tool via gRPC
func (c *GRPCClient) CallTool(ctx context.Context, name string, args map[string]any) (*ToolResult, error) {
	if !c.IsConnected() {
		return nil, ErrNotConnected
	}

	// Placeholder - would use generated gRPC client
	return &ToolResult{}, nil
}

// ListResources returns available resources
func (c *GRPCClient) ListResources(ctx context.Context) ([]Resource, error) {
	if !c.IsConnected() {
		return nil, ErrNotConnected
	}
	return []Resource{}, nil
}

// ReadResource reads a resource
func (c *GRPCClient) ReadResource(ctx context.Context, uri string) (*ResourceContent, error) {
	if !c.IsConnected() {
		return nil, ErrNotConnected
	}
	return nil, ErrResourceNotFound
}

// ListPrompts returns available prompts
func (c *GRPCClient) ListPrompts(ctx context.Context) ([]Prompt, error) {
	if !c.IsConnected() {
		return nil, ErrNotConnected
	}
	return []Prompt{}, nil
}

// GetPrompt gets a specific prompt
func (c *GRPCClient) GetPrompt(ctx context.Context, name string, args map[string]string) (*PromptResult, error) {
	if !c.IsConnected() {
		return nil, ErrNotConnected
	}
	return nil, ErrPromptNotFound
}

// CreateSample requests LLM sampling
func (c *GRPCClient) CreateSample(ctx context.Context, req *SamplingRequest) (*SamplingResponse, error) {
	if !c.IsConnected() {
		return nil, ErrNotConnected
	}
	return nil, fmt.Errorf("sampling not implemented for gRPC")
}

// withAuth adds auth metadata to context
func (c *GRPCClient) withAuth(ctx context.Context) context.Context {
	md := metadata.New(map[string]string{})

	if c.authToken != "" {
		md.Set("authorization", "Bearer "+c.authToken)
	}

	if c.tenantID != "" {
		md.Set("x-tenant-id", c.tenantID)
	}

	return metadata.NewOutgoingContext(ctx, md)
}

// dialOptions returns gRPC dial options
func (c *GRPCClient) dialOptions(cfg GRPCConfig) []grpc.DialOption {
	opts := []grpc.DialOption{}

	if cfg.UseTLS {
		if cfg.CertFile != "" {
			creds, err := credentials.NewClientTLSFromFile(cfg.CertFile, "")
			if err == nil {
				opts = append(opts, grpc.WithTransportCredentials(creds))
			}
		}
	} else {
		opts = append(opts, grpc.WithTransportCredentials(insecure.NewCredentials()))
	}

	return opts
}

// SetAuthToken updates the auth token
func (c *GRPCClient) SetAuthToken(token string) {
	c.authToken = token
}

// SetTenantID updates the tenant ID
func (c *GRPCClient) SetTenantID(id string) {
	c.tenantID = id
}

// Ensure interfaces are satisfied
var _ Client = (*GRPCClient)(nil)
var _ Client = (*HTTPClient)(nil)
var _ Client = (*StdioClient)(nil)

// Helpers for unused imports
var (
	_ = json.Marshal
	_ = atomic.AddInt64
	_ = time.Second
)
