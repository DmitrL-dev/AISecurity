// Package shadow_ai implements the Sentinel Shadow AI Control Module.
//
// Five levels of shadow AI management:
//
//	L1 — Universal Integration Layer: plugin-based enforcement (firewall, EDR, proxy)
//	L2 — Detection Engine: network signatures, endpoint, API keys, behavioral
//	L3 — Document Review Bridge: controlled LLM access with PII/secret scanning
//	L4 — Approval Workflow: tiered data classification and manager/SOC approval
//	L5 — SOC Integration: dashboard, correlation rules, playbooks, compliance
package shadow_ai

import (
	"context"
	"time"
)

// --- Plugin Interfaces ---

// NetworkEnforcer is the universal interface for ALL firewalls.
// Implementations: Check Point, Cisco ASA/FMC, Palo Alto, Fortinet.
type NetworkEnforcer interface {
	// BlockIP blocks an IP address for the given duration.
	BlockIP(ctx context.Context, ip string, duration time.Duration, reason string) error

	// BlockDomain blocks a domain name.
	BlockDomain(ctx context.Context, domain string, reason string) error

	// UnblockIP removes an IP block.
	UnblockIP(ctx context.Context, ip string) error

	// UnblockDomain removes a domain block.
	UnblockDomain(ctx context.Context, domain string) error

	// HealthCheck verifies the firewall API is reachable.
	HealthCheck(ctx context.Context) error

	// Vendor returns the vendor identifier (e.g., "checkpoint", "cisco", "paloalto").
	Vendor() string
}

// EndpointController is the universal interface for ALL EDR systems.
// Implementations: CrowdStrike, SentinelOne, Microsoft Defender.
type EndpointController interface {
	// IsolateHost quarantines a host from the network.
	IsolateHost(ctx context.Context, hostname string) error

	// ReleaseHost removes host isolation.
	ReleaseHost(ctx context.Context, hostname string) error

	// KillProcess terminates a process on a remote host.
	KillProcess(ctx context.Context, hostname string, pid int) error

	// QuarantineFile moves a file to quarantine on a remote host.
	QuarantineFile(ctx context.Context, hostname string, path string) error

	// HealthCheck verifies the EDR API is reachable.
	HealthCheck(ctx context.Context) error

	// Vendor returns the vendor identifier (e.g., "crowdstrike", "sentinelone", "defender").
	Vendor() string
}

// WebGateway is the universal interface for ALL proxy/CASB systems.
// Implementations: Zscaler, Netskope, Squid, BlueCoat.
type WebGateway interface {
	// BlockURL adds a URL to the blocklist.
	BlockURL(ctx context.Context, url string, reason string) error

	// UnblockURL removes a URL from the blocklist.
	UnblockURL(ctx context.Context, url string) error

	// BlockCategory blocks an entire URL category (e.g., "Artificial Intelligence").
	BlockCategory(ctx context.Context, category string) error

	// HealthCheck verifies the gateway API is reachable.
	HealthCheck(ctx context.Context) error

	// Vendor returns the vendor identifier (e.g., "zscaler", "netskope", "squid").
	Vendor() string
}

// Initializer is implemented by plugins that need configuration before use.
type Initializer interface {
	Initialize(config map[string]interface{}) error
}

// --- Plugin Configuration ---

// PluginType categorizes enforcement points.
type PluginType string

const (
	PluginTypeFirewall PluginType = "firewall"
	PluginTypeEDR      PluginType = "edr"
	PluginTypeProxy    PluginType = "proxy"
	PluginTypeDNS      PluginType = "dns"
)

// PluginConfig defines a vendor plugin configuration loaded from YAML.
type PluginConfig struct {
	Type    PluginType             `yaml:"type" json:"type"`
	Vendor  string                 `yaml:"vendor" json:"vendor"`
	Enabled bool                   `yaml:"enabled" json:"enabled"`
	Config  map[string]interface{} `yaml:"config" json:"config"`
}

// IntegrationConfig is the top-level Shadow AI configuration.
type IntegrationConfig struct {
	Plugins             []PluginConfig `yaml:"plugins" json:"plugins"`
	FallbackStrategy    string         `yaml:"fallback_strategy" json:"fallback_strategy"`       // "detect_only" | "alert_only"
	HealthCheckInterval time.Duration  `yaml:"health_check_interval" json:"health_check_interval"` // default: 30s
}

// --- Domain Types ---

// DetectionMethod identifies how a shadow AI usage was detected.
type DetectionMethod string

const (
	DetectNetwork    DetectionMethod = "network"     // Domain/IP match
	DetectHTTP       DetectionMethod = "http"        // HTTP header signature
	DetectTLS        DetectionMethod = "tls"         // TLS/JA3 fingerprint
	DetectProcess    DetectionMethod = "process"     // AI tool process execution
	DetectAPIKey     DetectionMethod = "api_key"     // AI API key in payload
	DetectBehavioral DetectionMethod = "behavioral"  // Anomalous AI access pattern
	DetectClipboard  DetectionMethod = "clipboard"   // Large clipboard → AI browser pattern
)

// DataClassification determines the approval tier required.
type DataClassification string

const (
	DataPublic       DataClassification = "PUBLIC"
	DataInternal     DataClassification = "INTERNAL"
	DataConfidential DataClassification = "CONFIDENTIAL"
	DataCritical     DataClassification = "CRITICAL"
)

// ShadowAIEvent is a detected shadow AI usage attempt.
type ShadowAIEvent struct {
	ID              string            `json:"id"`
	UserID          string            `json:"user_id"`
	Hostname        string            `json:"hostname"`
	Destination     string            `json:"destination"`      // Target AI service domain/IP
	AIService       string            `json:"ai_service"`       // "chatgpt", "claude", "gemini", etc.
	DetectionMethod DetectionMethod   `json:"detection_method"`
	Action          string            `json:"action"`           // "blocked", "allowed", "pending"
	EnforcedBy      string            `json:"enforced_by"`      // Plugin vendor that enforced
	DataSize        int64             `json:"data_size"`        // Bytes sent to AI
	Timestamp       time.Time         `json:"timestamp"`
	Metadata        map[string]string `json:"metadata,omitempty"`
}

// AIServiceInfo describes a known AI service for signature matching.
type AIServiceInfo struct {
	Name     string   `json:"name"`      // "ChatGPT", "Claude", "Gemini"
	Vendor   string   `json:"vendor"`    // "OpenAI", "Anthropic", "Google"
	Domains  []string `json:"domains"`   // ["*.openai.com", "chat.openai.com"]
	Category string   `json:"category"`  // "llm", "image_gen", "code_assist"
}

// BlockRequest is an API request to manually block a target.
type BlockRequest struct {
	TargetType string        `json:"target_type"` // "ip", "domain", "user"
	Target     string        `json:"target"`
	Duration   time.Duration `json:"duration"`
	Reason     string        `json:"reason"`
	BlockedBy  string        `json:"blocked_by"` // RBAC user
}

// ShadowAIStats provides aggregate statistics for the dashboard.
type ShadowAIStats struct {
	TimeRange    string         `json:"time_range"` // "24h", "7d", "30d"
	Total        int            `json:"total_attempts"`
	Blocked      int            `json:"blocked"`
	Approved     int            `json:"approved"`
	Pending      int            `json:"pending"`
	ByService    map[string]int `json:"by_service"`
	ByDepartment map[string]int `json:"by_department"`
	TopViolators []Violator     `json:"top_violators"`
}

// Violator tracks a user's shadow AI violation count.
type Violator struct {
	UserID   string `json:"user_id"`
	Attempts int    `json:"attempts"`
}

// ApprovalTier defines the approval requirements for a data classification level.
type ApprovalTier struct {
	Name           string        `yaml:"name" json:"name"`
	DataClass      DataClassification `yaml:"data_class" json:"data_class"`
	ApprovalNeeded []string      `yaml:"approval_needed" json:"approval_needed"` // ["manager"], ["manager", "soc"], ["ciso"]
	SLA            time.Duration `yaml:"sla" json:"sla"`
	AutoApprove    bool          `yaml:"auto_approve" json:"auto_approve"`
}

// ApprovalRequest tracks a pending approval for AI access.
type ApprovalRequest struct {
	ID          string             `json:"id"`
	DocID       string             `json:"doc_id"`
	UserID      string             `json:"user_id"`
	Tier        string             `json:"tier"`
	DataClass   DataClassification `json:"data_class"`
	Status      string             `json:"status"` // "pending", "approved", "denied", "expired"
	ApprovedBy  string             `json:"approved_by,omitempty"`
	DeniedBy    string             `json:"denied_by,omitempty"`
	Reason      string             `json:"reason,omitempty"`
	CreatedAt   time.Time          `json:"created_at"`
	ExpiresAt   time.Time          `json:"expires_at"`
	ResolvedAt  time.Time          `json:"resolved_at,omitempty"`
}

// ComplianceReport is the Shadow AI compliance report for GDPR/SOC2/EU AI Act.
type ComplianceReport struct {
	GeneratedAt       time.Time `json:"generated_at"`
	Period            string    `json:"period"` // "monthly", "quarterly"
	TotalInteractions int       `json:"total_interactions"`
	BlockedAttempts   int       `json:"blocked_attempts"`
	ApprovedReviews   int       `json:"approved_reviews"`
	PIIDetected       int       `json:"pii_detected"`
	SecretsDetected   int       `json:"secrets_detected"`
	AuditComplete     bool      `json:"audit_complete"`
	Regulations       []string  `json:"regulations"` // ["GDPR", "SOC2", "EU AI Act"]
}
