package entity

import "time"

// Context map for carrying metadata through the pipeline
type Context map[string]string

// Target represents the attack surface
type Target struct {
	ID      string
	URL     string
	Method  string
	Headers map[string]string
	Body    string
	Context Context
}

// Payload represents a specific attack vector
type Payload struct {
	ID        string
	Value     string
	Type      string // "SQLi", "XSS", "MCP", "Worm", etc.
	Technique string // "Union", "Error", "ToolPoisoning"
}

// Result represents the outcome of an attack attempt
type Result struct {
	TargetID    string
	PayloadID   string
	Success     bool
	Blocked     bool   // WAF blocked
	Technique   string // The technique used (e.g. "SQLi")
	Environment string // "WAF", "Origin", "Honeypot"
	Latency     time.Duration
	StatusCode  int
	Response    string
	Error       error
	Timestamp   time.Time
}

// AttackProfile defines the configuration for a strike campaign
type AttackProfile struct {
	Name            string
	Concurrency     int
	Timeout         time.Duration
	EvasionLevel    int    // 0-5
	UserAgentMode   string // "Random", "Chrome", "Bot"
	Modules         []string
	TargetVectors   []string
	RequiredVectors []string // For Artemis exhaustion
}
