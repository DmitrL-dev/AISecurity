package httpserver

import (
	"encoding/json"
	"io"
	"net/http"
	"strconv"
	"time"

	shadowai "github.com/syntrex/gomcp/internal/application/shadow_ai"
	"github.com/syntrex/gomcp/internal/infrastructure/auth"
)

func shadowAIActor(r *http.Request) string {
	if claims := auth.GetClaims(r.Context()); claims != nil && claims.Sub != "" {
		return claims.Sub
	}
	return "api"
}

// --- POST /api/v1/shadow-ai/ingest ---
//
// Honest live-telemetry ingest. An EXTERNAL forwarder (proxy/firewall access
// logs, a CASB streaming API, or the gateway egress hook) POSTs real
// NetworkEvents here; each is run through the detection engine, which may enforce
// (via configured plugins) and emit a SOC event. There is NO synthetic data path
// and NO demo simulator for shadow-AI — the event store stays empty until a real
// forwarder feeds it.
func (s *Server) handleShadowAINetworkIngest(w http.ResponseWriter, r *http.Request) {
	if s.shadowAI == nil {
		writeError(w, http.StatusServiceUnavailable, "shadow AI module not configured")
		return
	}

	var evt shadowai.NetworkEvent
	limitBody(w, r)
	if err := json.NewDecoder(r.Body).Decode(&evt); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON: "+err.Error())
		return
	}
	if evt.Destination == "" {
		writeError(w, http.StatusBadRequest, "destination is required")
		return
	}
	if evt.Timestamp.IsZero() {
		evt.Timestamp = time.Now()
	}

	detected := s.shadowAI.ProcessNetworkEvent(r.Context(), evt)
	writeJSON(w, http.StatusOK, map[string]any{
		"detected": detected != nil,
		"event":    detected, // nil when the destination is not a known AI service
	})
}

// --- GET /api/v1/shadow-ai/stats ---

func (s *Server) handleShadowAIStats(w http.ResponseWriter, r *http.Request) {
	if s.shadowAI == nil {
		writeError(w, http.StatusServiceUnavailable, "shadow AI module not configured")
		return
	}

	timeRange := r.URL.Query().Get("range")
	if timeRange == "" {
		timeRange = "24h"
	}

	stats := s.shadowAI.GetStats(timeRange)
	writeJSON(w, http.StatusOK, stats)
}

// --- GET /api/v1/shadow-ai/events ---

func (s *Server) handleShadowAIEvents(w http.ResponseWriter, r *http.Request) {
	if s.shadowAI == nil {
		writeError(w, http.StatusServiceUnavailable, "shadow AI module not configured")
		return
	}

	limit := 50
	if v := r.URL.Query().Get("limit"); v != "" {
		if parsed, err := strconv.Atoi(v); err == nil && parsed > 0 {
			limit = parsed
		}
	}
	if limit > 500 {
		limit = 500
	}

	events := s.shadowAI.GetEvents(limit)
	if events == nil {
		events = []shadowai.ShadowAIEvent{}
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"events": events,
		"count":  len(events),
		"limit":  limit,
	})
}

// --- GET /api/v1/shadow-ai/events/{id} ---

func (s *Server) handleShadowAIEventDetail(w http.ResponseWriter, r *http.Request) {
	if s.shadowAI == nil {
		writeError(w, http.StatusServiceUnavailable, "shadow AI module not configured")
		return
	}

	id := r.PathValue("id")
	if id == "" {
		writeError(w, http.StatusBadRequest, "event id required")
		return
	}

	event, ok := s.shadowAI.GetEvent(id)
	if !ok {
		writeError(w, http.StatusNotFound, "event not found")
		return
	}
	writeJSON(w, http.StatusOK, event)
}

// --- POST /api/v1/shadow-ai/block ---

func (s *Server) handleShadowAIBlock(w http.ResponseWriter, r *http.Request) {
	if s.shadowAI == nil {
		writeError(w, http.StatusServiceUnavailable, "shadow AI module not configured")
		return
	}

	var req struct {
		TargetType string `json:"target_type"` // "domain", "ip", "host"
		Target     string `json:"target"`
		Duration   string `json:"duration"` // "24h", "48h", etc.
		Reason     string `json:"reason"`
	}

	limitBody(w, r)
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON: "+err.Error())
		return
	}

	if req.TargetType == "" || req.Target == "" {
		writeError(w, http.StatusBadRequest, "target_type and target are required")
		return
	}

	duration := 24 * time.Hour
	if req.Duration != "" {
		if d, err := time.ParseDuration(req.Duration); err == nil {
			duration = d
		}
	}

	blockedBy := shadowAIActor(r)

	err := s.shadowAI.ManualBlock(r.Context(), shadowai.BlockRequest{
		TargetType: req.TargetType,
		Target:     req.Target,
		Duration:   duration,
		Reason:     req.Reason,
		BlockedBy:  blockedBy,
	})
	if err != nil {
		writeError(w, http.StatusInternalServerError, "block failed: "+err.Error())
		return
	}

	writeJSON(w, http.StatusOK, map[string]string{"status": "blocked", "target": req.Target})
}

// --- POST /api/v1/shadow-ai/unblock ---

func (s *Server) handleShadowAIUnblock(w http.ResponseWriter, r *http.Request) {
	if s.shadowAI == nil {
		writeError(w, http.StatusServiceUnavailable, "shadow AI module not configured")
		return
	}

	var req struct {
		TargetType string `json:"target_type"`
		Target     string `json:"target"`
	}

	limitBody(w, r)
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON: "+err.Error())
		return
	}

	writeError(w, http.StatusNotImplemented, "unblock executor unavailable")
}

// --- POST /api/v1/shadow-ai/scan ---

func (s *Server) handleShadowAIScan(w http.ResponseWriter, r *http.Request) {
	if s.shadowAI == nil {
		writeError(w, http.StatusServiceUnavailable, "shadow AI module not configured")
		return
	}

	body, err := io.ReadAll(io.LimitReader(r.Body, 1<<20))
	if err != nil {
		writeError(w, http.StatusBadRequest, "failed to read body")
		return
	}

	var req struct {
		Content string `json:"content"`
	}
	if err := json.Unmarshal(body, &req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON: "+err.Error())
		return
	}

	keyType, isInjected := s.shadowAI.ScanContent(req.Content)
	writeJSON(w, http.StatusOK, map[string]any{
		"detected":    keyType != "" || isInjected,
		"key_type":    keyType,
		"is_injected": isInjected,
		"timestamp":   time.Now(),
	})
}

// --- GET /api/v1/shadow-ai/integrations ---

func (s *Server) handleShadowAIIntegrations(w http.ResponseWriter, r *http.Request) {
	if s.shadowAI == nil {
		writeError(w, http.StatusServiceUnavailable, "shadow AI module not configured")
		return
	}

	health := s.shadowAI.IntegrationHealth()
	writeJSON(w, http.StatusOK, map[string]any{
		"integrations": health,
		"count":        len(health),
	})
}

// --- GET /api/v1/shadow-ai/integrations/{vendor}/health ---

func (s *Server) handleShadowAIVendorHealth(w http.ResponseWriter, r *http.Request) {
	if s.shadowAI == nil {
		writeError(w, http.StatusServiceUnavailable, "shadow AI module not configured")
		return
	}

	vendor := r.PathValue("vendor")
	if vendor == "" {
		writeError(w, http.StatusBadRequest, "vendor required")
		return
	}

	health, ok := s.shadowAI.VendorHealth(vendor)
	if !ok {
		writeError(w, http.StatusNotFound, "vendor not found")
		return
	}
	writeJSON(w, http.StatusOK, health)
}

// --- GET /api/v1/shadow-ai/compliance ---

func (s *Server) handleShadowAICompliance(w http.ResponseWriter, r *http.Request) {
	if s.shadowAI == nil {
		writeError(w, http.StatusServiceUnavailable, "shadow AI module not configured")
		return
	}

	period := r.URL.Query().Get("period")
	if period == "" {
		period = "30d"
	}
	report := s.shadowAI.GenerateComplianceReport(period)
	writeJSON(w, http.StatusOK, report)
}

// --- POST /api/v1/shadow-ai/doc-review ---

func (s *Server) handleShadowAIDocReview(w http.ResponseWriter, r *http.Request) {
	if s.shadowAI == nil {
		writeError(w, http.StatusServiceUnavailable, "shadow AI module not configured")
		return
	}

	var req struct {
		DocID   string `json:"doc_id"`
		Content string `json:"content"`
		UserID  string `json:"user_id"`
	}
	limitBody(w, r)
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON: "+err.Error())
		return
	}
	if req.Content == "" {
		writeError(w, http.StatusBadRequest, "content is required")
		return
	}
	if req.DocID == "" {
		req.DocID = "doc-" + time.Now().Format("20060102-150405")
	}
	if req.UserID == "" {
		req.UserID = shadowAIActor(r)
	}

	result, approval := s.shadowAI.ReviewDocument(req.DocID, req.Content, req.UserID)
	resp := map[string]any{
		"scan_result": result,
	}
	if approval != nil {
		resp["approval"] = approval
	}
	writeJSON(w, http.StatusOK, resp)
}

// --- GET /api/v1/shadow-ai/doc-review/{id} ---

func (s *Server) handleShadowAIDocReviewStatus(w http.ResponseWriter, r *http.Request) {
	if s.shadowAI == nil {
		writeError(w, http.StatusServiceUnavailable, "shadow AI module not configured")
		return
	}

	id := r.PathValue("id")
	if id == "" {
		writeError(w, http.StatusBadRequest, "doc_id required")
		return
	}

	result, ok := s.shadowAI.DocBridge().GetReview(id)
	if !ok {
		writeError(w, http.StatusNotFound, "review not found")
		return
	}
	writeJSON(w, http.StatusOK, result)
}

// --- POST /api/v1/shadow-ai/approvals/{id}/verdict ---

func (s *Server) handleShadowAIApprovalVerdict(w http.ResponseWriter, r *http.Request) {
	if s.shadowAI == nil {
		writeError(w, http.StatusServiceUnavailable, "shadow AI module not configured")
		return
	}

	id := r.PathValue("id")
	if id == "" {
		writeError(w, http.StatusBadRequest, "approval id required")
		return
	}

	var req struct {
		Verdict string `json:"verdict"` // "approve" or "deny"
		Reason  string `json:"reason"`
	}
	limitBody(w, r)
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON: "+err.Error())
		return
	}

	analyst := shadowAIActor(r)

	var err error
	switch req.Verdict {
	case "approve":
		err = s.shadowAI.ApprovalEngine().Approve(id, analyst)
	case "deny":
		err = s.shadowAI.ApprovalEngine().Deny(id, analyst, req.Reason)
	default:
		writeError(w, http.StatusBadRequest, "verdict must be 'approve' or 'deny'")
		return
	}

	if err != nil {
		writeError(w, http.StatusNotFound, err.Error())
		return
	}

	writeJSON(w, http.StatusOK, map[string]string{"status": req.Verdict + "d", "request_id": id})
}

// --- GET /api/v1/shadow-ai/approvals ---

func (s *Server) handleShadowAIPendingApprovals(w http.ResponseWriter, r *http.Request) {
	if s.shadowAI == nil {
		writeError(w, http.StatusServiceUnavailable, "shadow AI module not configured")
		return
	}

	pending := s.shadowAI.ApprovalEngine().PendingRequests()
	stats := s.shadowAI.ApprovalEngine().Stats()
	writeJSON(w, http.StatusOK, map[string]any{
		"pending": pending,
		"stats":   stats,
	})
}

// --- GET /api/v1/shadow-ai/approvals/tiers ---

func (s *Server) handleShadowAIApprovalTiers(w http.ResponseWriter, r *http.Request) {
	if s.shadowAI == nil {
		writeError(w, http.StatusServiceUnavailable, "shadow AI module not configured")
		return
	}

	tiers := s.shadowAI.ApprovalEngine().Tiers()
	writeJSON(w, http.StatusOK, map[string]any{
		"tiers": tiers,
		"count": len(tiers),
	})
}
