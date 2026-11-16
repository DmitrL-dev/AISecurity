package shadow_ai

import (
	"fmt"
	"log/slog"
	"sync"
	"time"
)

// --- Tiered Approval Workflow ---
// Implements §6 of the ТЗ: data classification → approval tier → SLA tracking.

// ApprovalStatus tracks the state of an approval request.
type ApprovalStatus string

const (
	ApprovalPending  ApprovalStatus = "pending"
	ApprovalApproved ApprovalStatus = "approved"
	ApprovalDenied   ApprovalStatus = "denied"
	ApprovalExpired  ApprovalStatus = "expired"
	ApprovalAutoApproved ApprovalStatus = "auto_approved"
)

// DefaultApprovalTiers defines the approval requirements per data classification.
func DefaultApprovalTiers() []ApprovalTier {
	return []ApprovalTier{
		{
			Name:           "Tier 1: Public Data",
			DataClass:      DataPublic,
			ApprovalNeeded: nil, // Auto-approve
			SLA:            0,
			AutoApprove:    true,
		},
		{
			Name:           "Tier 2: Internal Data",
			DataClass:      DataInternal,
			ApprovalNeeded: []string{"manager"},
			SLA:            4 * time.Hour,
			AutoApprove:    false,
		},
		{
			Name:           "Tier 3: Confidential Data",
			DataClass:      DataConfidential,
			ApprovalNeeded: []string{"manager", "soc"},
			SLA:            24 * time.Hour,
			AutoApprove:    false,
		},
		{
			Name:           "Tier 4: Critical Data",
			DataClass:      DataCritical,
			ApprovalNeeded: []string{"ciso"},
			SLA:            0, // Manual only, no auto-expire
			AutoApprove:    false,
		},
	}
}

// ApprovalEngine manages the tiered approval workflow.
type ApprovalEngine struct {
	mu       sync.RWMutex
	tiers    []ApprovalTier
	requests map[string]*ApprovalRequest
	logger   *slog.Logger
}

// NewApprovalEngine creates an engine with default tiers.
func NewApprovalEngine() *ApprovalEngine {
	return &ApprovalEngine{
		tiers:    DefaultApprovalTiers(),
		requests: make(map[string]*ApprovalRequest),
		logger:   slog.Default().With("component", "shadow-ai-approvals"),
	}
}

// SubmitRequest creates a new approval request based on data classification.
// Returns the request or auto-approves if the tier allows it.
func (ae *ApprovalEngine) SubmitRequest(userID, docID string, dataClass DataClassification) *ApprovalRequest {
	ae.mu.Lock()
	defer ae.mu.Unlock()

	tier := ae.findTier(dataClass)

	req := &ApprovalRequest{
		ID:        genApprovalID(),
		DocID:     docID,
		UserID:    userID,
		Tier:      tier.Name,
		DataClass: dataClass,
		Status:    string(ApprovalPending),
		CreatedAt: time.Now(),
	}

	// Set expiry based on SLA.
	if tier.SLA > 0 {
		req.ExpiresAt = req.CreatedAt.Add(tier.SLA)
	}

	// Auto-approve for public data.
	if tier.AutoApprove {
		req.Status = string(ApprovalAutoApproved)
		req.ApprovedBy = "system"
		req.ResolvedAt = time.Now()
		ae.logger.Info("auto-approved",
			"request_id", req.ID,
			"user", userID,
			"data_class", dataClass,
		)
	} else {
		ae.logger.Info("approval required",
			"request_id", req.ID,
			"user", userID,
			"data_class", dataClass,
			"tier", tier.Name,
			"approvers", tier.ApprovalNeeded,
		)
	}

	ae.requests[req.ID] = req
	return req
}

// Approve approves a pending request.
func (ae *ApprovalEngine) Approve(requestID, approvedBy string) error {
	ae.mu.Lock()
	defer ae.mu.Unlock()

	req, ok := ae.requests[requestID]
	if !ok {
		return fmt.Errorf("request %s not found", requestID)
	}

	if req.Status != string(ApprovalPending) {
		return fmt.Errorf("request %s is not pending (status: %s)", requestID, req.Status)
	}

	req.Status = string(ApprovalApproved)
	req.ApprovedBy = approvedBy
	req.ResolvedAt = time.Now()

	ae.logger.Info("approved",
		"request_id", requestID,
		"approved_by", approvedBy,
	)
	return nil
}

// Deny denies a pending request.
func (ae *ApprovalEngine) Deny(requestID, deniedBy, reason string) error {
	ae.mu.Lock()
	defer ae.mu.Unlock()

	req, ok := ae.requests[requestID]
	if !ok {
		return fmt.Errorf("request %s not found", requestID)
	}

	if req.Status != string(ApprovalPending) {
		return fmt.Errorf("request %s is not pending (status: %s)", requestID, req.Status)
	}

	req.Status = string(ApprovalDenied)
	req.DeniedBy = deniedBy
	req.Reason = reason
	req.ResolvedAt = time.Now()

	ae.logger.Info("denied",
		"request_id", requestID,
		"denied_by", deniedBy,
		"reason", reason,
	)
	return nil
}

// GetRequest returns an approval request by ID.
func (ae *ApprovalEngine) GetRequest(requestID string) (*ApprovalRequest, bool) {
	ae.mu.RLock()
	defer ae.mu.RUnlock()
	req, ok := ae.requests[requestID]
	if !ok {
		return nil, false
	}
	cp := *req
	return &cp, true
}

// PendingRequests returns all pending approval requests.
func (ae *ApprovalEngine) PendingRequests() []ApprovalRequest {
	ae.mu.RLock()
	defer ae.mu.RUnlock()

	var result []ApprovalRequest
	for _, req := range ae.requests {
		if req.Status == string(ApprovalPending) {
			result = append(result, *req)
		}
	}
	return result
}

// ExpireOverdue marks overdue pending requests as expired.
// Returns the number of expired requests.
func (ae *ApprovalEngine) ExpireOverdue() int {
	ae.mu.Lock()
	defer ae.mu.Unlock()

	now := time.Now()
	expired := 0

	for _, req := range ae.requests {
		if req.Status == string(ApprovalPending) && !req.ExpiresAt.IsZero() && now.After(req.ExpiresAt) {
			req.Status = string(ApprovalExpired)
			req.ResolvedAt = now
			expired++
			ae.logger.Warn("request expired",
				"request_id", req.ID,
				"user", req.UserID,
				"expired_at", req.ExpiresAt,
			)
		}
	}
	return expired
}

// Stats returns approval workflow statistics.
func (ae *ApprovalEngine) Stats() map[string]int {
	ae.mu.RLock()
	defer ae.mu.RUnlock()

	stats := map[string]int{
		"total":         len(ae.requests),
		"pending":       0,
		"approved":      0,
		"denied":        0,
		"expired":       0,
		"auto_approved": 0,
	}
	for _, req := range ae.requests {
		switch ApprovalStatus(req.Status) {
		case ApprovalPending:
			stats["pending"]++
		case ApprovalApproved:
			stats["approved"]++
		case ApprovalDenied:
			stats["denied"]++
		case ApprovalExpired:
			stats["expired"]++
		case ApprovalAutoApproved:
			stats["auto_approved"]++
		}
	}
	return stats
}

// Tiers returns the approval tier configuration.
func (ae *ApprovalEngine) Tiers() []ApprovalTier {
	return ae.tiers
}

func (ae *ApprovalEngine) findTier(dataClass DataClassification) ApprovalTier {
	for _, t := range ae.tiers {
		if t.DataClass == dataClass {
			return t
		}
	}
	// Default to most restrictive.
	return ae.tiers[len(ae.tiers)-1]
}

var approvalCounter uint64
var approvalCounterMu sync.Mutex

func genApprovalID() string {
	approvalCounterMu.Lock()
	approvalCounter++
	id := approvalCounter
	approvalCounterMu.Unlock()
	return fmt.Sprintf("apr-%d-%d", time.Now().UnixMilli(), id)
}
