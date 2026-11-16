package soc

import (
	"fmt"
	"sync"
	"time"
)

// ZeroGMode implements §13.4 — manual approval workflow for Strike Force operations.
// Events in Zero-G mode require explicit analyst approval before auto-response executes.
type ZeroGMode struct {
	mu       sync.RWMutex
	enabled  bool
	queue    []ZeroGRequest
	resolved []ZeroGRequest
	maxQueue int
}

// ZeroGRequest represents a pending approval request.
type ZeroGRequest struct {
	ID          string         `json:"id"`
	EventID     string         `json:"event_id"`
	IncidentID  string         `json:"incident_id,omitempty"`
	Action      string         `json:"action"` // What would auto-execute
	Severity    string         `json:"severity"`
	Description string         `json:"description"`
	Status      ZeroGStatus    `json:"status"`
	CreatedAt   time.Time      `json:"created_at"`
	ResolvedAt  *time.Time     `json:"resolved_at,omitempty"`
	ResolvedBy  string         `json:"resolved_by,omitempty"`
	Verdict     ZeroGVerdict   `json:"verdict,omitempty"`
}

// ZeroGStatus tracks the request lifecycle.
type ZeroGStatus string

const (
	ZeroGPending  ZeroGStatus = "PENDING"
	ZeroGApproved ZeroGStatus = "APPROVED"
	ZeroGDenied   ZeroGStatus = "DENIED"
	ZeroGExpired  ZeroGStatus = "EXPIRED"
)

// ZeroGVerdict is the analyst's decision.
type ZeroGVerdict string

const (
	ZGVerdictApprove  ZeroGVerdict = "APPROVE"
	ZGVerdictDeny     ZeroGVerdict = "DENY"
	ZGVerdictEscalate ZeroGVerdict = "ESCALATE"
)

// NewZeroGMode creates the Zero-G approval engine.
func NewZeroGMode() *ZeroGMode {
	return &ZeroGMode{
		enabled:  false,
		maxQueue: 200,
	}
}

// Enable activates Zero-G mode (manual approval required).
func (z *ZeroGMode) Enable() {
	z.mu.Lock()
	defer z.mu.Unlock()
	z.enabled = true
}

// Disable deactivates Zero-G mode (auto-response resumes).
func (z *ZeroGMode) Disable() {
	z.mu.Lock()
	defer z.mu.Unlock()
	z.enabled = false
}

// IsEnabled returns whether Zero-G mode is active.
func (z *ZeroGMode) IsEnabled() bool {
	z.mu.RLock()
	defer z.mu.RUnlock()
	return z.enabled
}

// RequestApproval queues an action for manual approval. Returns the request ID.
func (z *ZeroGMode) RequestApproval(eventID, incidentID, action, severity, description string) string {
	z.mu.Lock()
	defer z.mu.Unlock()

	if !z.enabled {
		return "" // Not in Zero-G mode, skip
	}

	reqID := fmt.Sprintf("zg-%d", time.Now().UnixNano())
	req := ZeroGRequest{
		ID:          reqID,
		EventID:     eventID,
		IncidentID:  incidentID,
		Action:      action,
		Severity:    severity,
		Description: description,
		Status:      ZeroGPending,
		CreatedAt:   time.Now(),
	}

	// Enforce max queue size
	if len(z.queue) >= z.maxQueue {
		// Expire oldest
		expired := z.queue[0]
		expired.Status = ZeroGExpired
		now := time.Now()
		expired.ResolvedAt = &now
		z.resolved = append(z.resolved, expired)
		z.queue = z.queue[1:]
	}

	z.queue = append(z.queue, req)
	return reqID
}

// Resolve processes an analyst's verdict on a pending request.
func (z *ZeroGMode) Resolve(requestID string, verdict ZeroGVerdict, analyst string) error {
	z.mu.Lock()
	defer z.mu.Unlock()

	for i, req := range z.queue {
		if req.ID == requestID {
			now := time.Now()
			z.queue[i].ResolvedAt = &now
			z.queue[i].ResolvedBy = analyst
			z.queue[i].Verdict = verdict

			switch verdict {
			case ZGVerdictApprove:
				z.queue[i].Status = ZeroGApproved
			case ZGVerdictDeny:
				z.queue[i].Status = ZeroGDenied
			case ZGVerdictEscalate:
				z.queue[i].Status = ZeroGPending // Stay pending, but mark escalated
			}

			// Move to resolved
			z.resolved = append(z.resolved, z.queue[i])
			z.queue = append(z.queue[:i], z.queue[i+1:]...)
			return nil
		}
	}
	return fmt.Errorf("zero-g request %s not found", requestID)
}

// PendingRequests returns all pending approval requests.
func (z *ZeroGMode) PendingRequests() []ZeroGRequest {
	z.mu.RLock()
	defer z.mu.RUnlock()
	result := make([]ZeroGRequest, len(z.queue))
	copy(result, z.queue)
	return result
}

// Stats returns Zero-G mode statistics.
func (z *ZeroGMode) Stats() map[string]any {
	z.mu.RLock()
	defer z.mu.RUnlock()

	approved := 0
	denied := 0
	expired := 0
	for _, r := range z.resolved {
		switch r.Status {
		case ZeroGApproved:
			approved++
		case ZeroGDenied:
			denied++
		case ZeroGExpired:
			expired++
		}
	}

	return map[string]any{
		"enabled":          z.enabled,
		"pending":          len(z.queue),
		"total_resolved":   len(z.resolved),
		"approved":         approved,
		"denied":           denied,
		"expired":          expired,
	}
}
