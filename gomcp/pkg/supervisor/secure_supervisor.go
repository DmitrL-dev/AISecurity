// Package supervisor provides tool worker management with security integration.
package supervisor

import (
	"context"
	"fmt"
	"time"

	"github.com/sentinel-community/gomcp/pkg/security"
)

// SecureSupervisor wraps Supervisor with security features
type SecureSupervisor struct {
	*Supervisor
	validator   *security.Validator
	auditLog    security.AuditLogger
	rateLimiter *security.RateLimiter
}

// SecureConfig extends Config with security options
type SecureConfig struct {
	Config
	// RateLimitPerClient limits requests per client per window
	RateLimitPerClient int
	// RateLimitWindow is the sliding window for rate limiting
	RateLimitWindow time.Duration
	// MaxAuditEvents limits in-memory audit log size
	MaxAuditEvents int
	// AuditLogger allows custom audit output (optional)
	AuditLogger security.AuditLogger
}

// NewSecure creates a supervisor with security features enabled
func NewSecure(cfg SecureConfig) *SecureSupervisor {
	baseSupervisor := New(cfg.Config)

	// Set defaults
	if cfg.RateLimitPerClient == 0 {
		cfg.RateLimitPerClient = 100 // 100 requests per window
	}
	if cfg.RateLimitWindow == 0 {
		cfg.RateLimitWindow = time.Minute // 1 minute window
	}
	if cfg.MaxAuditEvents == 0 {
		cfg.MaxAuditEvents = 10000
	}

	var auditLog security.AuditLogger
	if cfg.AuditLogger != nil {
		auditLog = cfg.AuditLogger
	} else {
		auditLog = security.NewInMemoryAuditLogger(cfg.MaxAuditEvents)
	}

	return &SecureSupervisor{
		Supervisor:  baseSupervisor,
		validator:   security.DefaultValidator(),
		auditLog:    auditLog,
		rateLimiter: security.NewRateLimiter(cfg.RateLimitPerClient, cfg.RateLimitWindow),
	}
}

// CallToolSecure executes a tool with full security checks
func (s *SecureSupervisor) CallToolSecure(ctx context.Context, clientID string, call *ToolCall) *ToolResult {
	started := time.Now()

	// 1. Rate limiting check
	if !s.rateLimiter.Allow(clientID) {
		s.logEvent(security.AuditRateLimited, call.ToolName, clientID, call.RequestID, false, 0, "rate limit exceeded")
		return &ToolResult{
			Error: &ToolError{
				Code:    ErrPermissionDenied,
				Message: "rate limit exceeded",
			},
		}
	}

	// 2. Input validation
	validationResult := s.validator.ValidateJSON(call.Arguments)
	if !validationResult.Valid {
		errMsg := "validation failed"
		if len(validationResult.Errors) > 0 {
			errMsg = validationResult.Errors[0].Error()
		}
		s.logEvent(security.AuditValidationFail, call.ToolName, clientID, call.RequestID, false, 0, errMsg)
		return &ToolResult{
			Error: &ToolError{
				Code:    ErrInvalidArguments,
				Message: errMsg,
			},
		}
	}

	// 3. Log tool call start
	s.logEvent(security.AuditToolCall, call.ToolName, clientID, call.RequestID, true, 0, "")

	// 4. Execute tool via base supervisor
	result := s.Supervisor.CallTool(ctx, call)

	// 5. Log tool result
	duration := time.Since(started)
	success := result.Error == nil
	errMsg := ""
	if result.Error != nil {
		errMsg = result.Error.Message
	}
	s.logEvent(security.AuditToolResult, call.ToolName, clientID, call.RequestID, success, duration, errMsg)

	return result
}

func (s *SecureSupervisor) logEvent(eventType security.AuditEventType, toolName, clientID, requestID string, success bool, duration time.Duration, errMsg string) {
	event := &security.AuditEvent{
		ID:        fmt.Sprintf("%s-%d", requestID, time.Now().UnixNano()),
		Timestamp: time.Now(),
		EventType: eventType,
		ToolName:  toolName,
		ClientID:  clientID,
		RequestID: requestID,
		Success:   success,
		Duration:  duration,
		Error:     errMsg,
	}
	s.auditLog.Log(event)
}

// AuditEvents returns recent audit events (if using in-memory logger)
func (s *SecureSupervisor) AuditEvents() []*security.AuditEvent {
	if logger, ok := s.auditLog.(*security.InMemoryAuditLogger); ok {
		return logger.Events()
	}
	return nil
}

// RemainingRequests returns remaining rate limit for a client
func (s *SecureSupervisor) RemainingRequests(clientID string) int {
	return s.rateLimiter.Remaining(clientID)
}

// ShutdownSecure stops all security goroutines
func (s *SecureSupervisor) ShutdownSecure() {
	s.rateLimiter.Stop()
	s.Supervisor.Shutdown()
}
