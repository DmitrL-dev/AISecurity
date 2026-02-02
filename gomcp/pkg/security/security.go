// Package security provides security primitives for GoMCP including
// input validation, audit logging, rate limiting, and sandboxing.
package security

import (
	"encoding/json"
	"fmt"
	"regexp"
	"sync"
	"time"
)

// ValidationError represents an input validation failure
type ValidationError struct {
	Field   string `json:"field"`
	Message string `json:"message"`
	Value   string `json:"value,omitempty"`
}

func (e *ValidationError) Error() string {
	return fmt.Sprintf("validation error on %s: %s", e.Field, e.Message)
}

// ValidationResult holds multiple validation errors
type ValidationResult struct {
	Valid  bool               `json:"valid"`
	Errors []*ValidationError `json:"errors,omitempty"`
}

// Validator provides input validation for tool arguments
type Validator struct {
	// MaxStringLength limits string field sizes
	MaxStringLength int
	// MaxArrayLength limits array sizes
	MaxArrayLength int
	// MaxDepth limits JSON nesting depth
	MaxDepth int
	// DangerousPatterns to reject
	DangerousPatterns []*regexp.Regexp
}

// DefaultValidator with sensible security limits
func DefaultValidator() *Validator {
	return &Validator{
		MaxStringLength: 100000, // 100KB per string
		MaxArrayLength:  10000,  // 10K items
		MaxDepth:        20,     // Nesting depth
		DangerousPatterns: []*regexp.Regexp{
			regexp.MustCompile(`(?i)<script.*?>.*?</script.*?>`), // XSS
			regexp.MustCompile(`(?i)javascript:`),                // XSS
			regexp.MustCompile(`;\s*(rm|del|drop|truncate)\s+`),  // SQL/shell injection
			regexp.MustCompile(`\$\{.*?\}`),                      // Template injection
			regexp.MustCompile(`\{\{.*?\}\}`),                    // Template injection
		},
	}
}

// ValidateJSON checks JSON input against security constraints
func (v *Validator) ValidateJSON(data json.RawMessage) *ValidationResult {
	result := &ValidationResult{Valid: true}

	if len(data) == 0 {
		return result
	}

	var parsed interface{}
	if err := json.Unmarshal(data, &parsed); err != nil {
		result.Valid = false
		result.Errors = append(result.Errors, &ValidationError{
			Field:   "root",
			Message: "invalid JSON: " + err.Error(),
		})
		return result
	}

	v.validateValue("root", parsed, 0, result)
	return result
}

func (v *Validator) validateValue(path string, val interface{}, depth int, result *ValidationResult) {
	if depth > v.MaxDepth {
		result.Valid = false
		result.Errors = append(result.Errors, &ValidationError{
			Field:   path,
			Message: fmt.Sprintf("exceeded maximum nesting depth of %d", v.MaxDepth),
		})
		return
	}

	switch typed := val.(type) {
	case string:
		v.validateString(path, typed, result)
	case []interface{}:
		if len(typed) > v.MaxArrayLength {
			result.Valid = false
			result.Errors = append(result.Errors, &ValidationError{
				Field:   path,
				Message: fmt.Sprintf("array length %d exceeds maximum %d", len(typed), v.MaxArrayLength),
			})
			return
		}
		for i, item := range typed {
			v.validateValue(fmt.Sprintf("%s[%d]", path, i), item, depth+1, result)
		}
	case map[string]interface{}:
		for key, item := range typed {
			v.validateValue(path+"."+key, item, depth+1, result)
		}
	}
}

func (v *Validator) validateString(path, val string, result *ValidationResult) {
	if len(val) > v.MaxStringLength {
		result.Valid = false
		result.Errors = append(result.Errors, &ValidationError{
			Field:   path,
			Message: fmt.Sprintf("string length %d exceeds maximum %d", len(val), v.MaxStringLength),
		})
		return
	}

	for _, pattern := range v.DangerousPatterns {
		if pattern.MatchString(val) {
			result.Valid = false
			result.Errors = append(result.Errors, &ValidationError{
				Field:   path,
				Message: "contains potentially dangerous pattern",
				Value:   truncate(val, 50),
			})
			return
		}
	}
}

func truncate(s string, maxLen int) string {
	if len(s) <= maxLen {
		return s
	}
	return s[:maxLen] + "..."
}

// AuditEvent represents a security-relevant event
type AuditEvent struct {
	ID        string          `json:"id"`
	Timestamp time.Time       `json:"timestamp"`
	EventType AuditEventType  `json:"event_type"`
	ToolName  string          `json:"tool_name,omitempty"`
	WorkerID  string          `json:"worker_id,omitempty"`
	ClientID  string          `json:"client_id,omitempty"`
	RequestID string          `json:"request_id,omitempty"`
	Success   bool            `json:"success"`
	Duration  time.Duration   `json:"duration_ns,omitempty"`
	Error     string          `json:"error,omitempty"`
	Metadata  json.RawMessage `json:"metadata,omitempty"`
}

// AuditEventType categorizes audit events
type AuditEventType string

const (
	AuditToolCall       AuditEventType = "tool_call"
	AuditToolResult     AuditEventType = "tool_result"
	AuditWorkerRegister AuditEventType = "worker_register"
	AuditWorkerCrash    AuditEventType = "worker_crash"
	AuditRateLimited    AuditEventType = "rate_limited"
	AuditValidationFail AuditEventType = "validation_fail"
	AuditPermissionDeny AuditEventType = "permission_deny"
)

// AuditLogger interface for audit event output
type AuditLogger interface {
	Log(event *AuditEvent)
}

// InMemoryAuditLogger stores events in memory (for testing)
type InMemoryAuditLogger struct {
	mu     sync.RWMutex
	events []*AuditEvent
	maxLen int
}

// NewInMemoryAuditLogger creates a bounded in-memory logger
func NewInMemoryAuditLogger(maxEvents int) *InMemoryAuditLogger {
	return &InMemoryAuditLogger{
		events: make([]*AuditEvent, 0, maxEvents),
		maxLen: maxEvents,
	}
}

// Log adds an event to the logger
func (l *InMemoryAuditLogger) Log(event *AuditEvent) {
	l.mu.Lock()
	defer l.mu.Unlock()

	if len(l.events) >= l.maxLen {
		// Ring buffer behavior
		l.events = l.events[1:]
	}
	l.events = append(l.events, event)
}

// Events returns all logged events
func (l *InMemoryAuditLogger) Events() []*AuditEvent {
	l.mu.RLock()
	defer l.mu.RUnlock()

	result := make([]*AuditEvent, len(l.events))
	copy(result, l.events)
	return result
}

// RateLimiter provides per-client rate limiting
type RateLimiter struct {
	mu       sync.RWMutex
	clients  map[string]*clientBucket
	limit    int           // requests per window
	window   time.Duration // time window
	cleanup  time.Duration // cleanup interval
	stopChan chan struct{}
}

type clientBucket struct {
	count     int
	windowEnd time.Time
}

// NewRateLimiter creates a rate limiter
func NewRateLimiter(limit int, window time.Duration) *RateLimiter {
	rl := &RateLimiter{
		clients:  make(map[string]*clientBucket),
		limit:    limit,
		window:   window,
		cleanup:  window * 2,
		stopChan: make(chan struct{}),
	}
	go rl.cleanupLoop()
	return rl
}

// Allow checks if a request from clientID is allowed
func (rl *RateLimiter) Allow(clientID string) bool {
	rl.mu.Lock()
	defer rl.mu.Unlock()

	now := time.Now()
	bucket, exists := rl.clients[clientID]

	if !exists || now.After(bucket.windowEnd) {
		// New window
		rl.clients[clientID] = &clientBucket{
			count:     1,
			windowEnd: now.Add(rl.window),
		}
		return true
	}

	if bucket.count >= rl.limit {
		return false
	}

	bucket.count++
	return true
}

// Remaining returns requests remaining for clientID
func (rl *RateLimiter) Remaining(clientID string) int {
	rl.mu.RLock()
	defer rl.mu.RUnlock()

	bucket, exists := rl.clients[clientID]
	if !exists || time.Now().After(bucket.windowEnd) {
		return rl.limit
	}
	return rl.limit - bucket.count
}

func (rl *RateLimiter) cleanupLoop() {
	ticker := time.NewTicker(rl.cleanup)
	defer ticker.Stop()

	for {
		select {
		case <-rl.stopChan:
			return
		case <-ticker.C:
			rl.mu.Lock()
			now := time.Now()
			for id, bucket := range rl.clients {
				if now.After(bucket.windowEnd.Add(rl.window)) {
					delete(rl.clients, id)
				}
			}
			rl.mu.Unlock()
		}
	}
}

// Stop stops the rate limiter cleanup goroutine
func (rl *RateLimiter) Stop() {
	close(rl.stopChan)
}
