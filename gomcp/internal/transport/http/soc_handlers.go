package httpserver

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"log/slog"
	"net"
	"net/http"
	"os"
	"strconv"
	"strings"
	"sync"
	"time"

	appsoc "github.com/syntrex/gomcp/internal/application/soc"
	"github.com/syntrex/gomcp/internal/domain/engines"
	domsoc "github.com/syntrex/gomcp/internal/domain/soc"
	"github.com/syntrex/gomcp/internal/infrastructure/auth"
	"github.com/syntrex/gomcp/internal/infrastructure/onnx"
)

// MaxRequestBodySize limits POST body size to prevent OOM (T3-3).
const MaxRequestBodySize = 1 << 20 // 1 MB

// limitBody wraps r.Body with http.MaxBytesReader to enforce size limits.
func limitBody(w http.ResponseWriter, r *http.Request) {
	r.Body = http.MaxBytesReader(w, r.Body, MaxRequestBodySize)
}

// tenantFromRequest extracts TenantID from JWT claims in request context.
// Returns empty string for unauthenticated/public requests (backward compatible).
func tenantFromRequest(r *http.Request) string {
	if claims := auth.GetClaims(r.Context()); claims != nil {
		return claims.TenantID
	}
	return ""
}

// handleDashboard returns SOC KPI metrics.
// GET /api/soc/dashboard
func (s *Server) handleDashboard(w http.ResponseWriter, r *http.Request) {
	dash, err := s.socSvc.Dashboard(tenantFromRequest(r))
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, dash)
}

// handleEvents returns recent SOC events with optional limit.
// GET /api/soc/events?limit=50
func (s *Server) handleEvents(w http.ResponseWriter, r *http.Request) {
	limit := 50 // default
	if v := r.URL.Query().Get("limit"); v != "" {
		if parsed, err := strconv.Atoi(v); err == nil && parsed > 0 {
			limit = parsed
		}
	}
	// SEC-RT2-INFO-1: Cap to prevent resource exhaustion via API.
	if limit > 200 {
		limit = 200
	}

	events, err := s.socSvc.ListEvents(tenantFromRequest(r), limit)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}

	writeJSON(w, http.StatusOK, map[string]any{
		"events": events,
		"count":  len(events),
		"limit":  limit,
	})
}

// handleIncidents returns SOC incidents with optional status filter and limit.
// GET /api/soc/incidents?status=open&limit=20
func (s *Server) handleIncidents(w http.ResponseWriter, r *http.Request) {
	status := r.URL.Query().Get("status")
	limit := 20 // default
	if v := r.URL.Query().Get("limit"); v != "" {
		if parsed, err := strconv.Atoi(v); err == nil && parsed > 0 {
			limit = parsed
		}
	}
	// SEC-RT2-HIGH-1: Cap to prevent resource exhaustion.
	if limit > 200 {
		limit = 200
	}

	incidents, err := s.socSvc.ListIncidents(tenantFromRequest(r), status, limit)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}

	writeJSON(w, http.StatusOK, map[string]any{
		"incidents": incidents,
		"count":     len(incidents),
		"status":    status,
		"limit":     limit,
	})
}

// handleHealth returns a simple health check response.
// GET /health
func (s *Server) handleHealth(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{
		"status": "ok",
	})
}

// handleHealthz is a K8s liveness probe — returns 200 if the server process is alive.
// GET /healthz
func (s *Server) handleHealthz(w http.ResponseWriter, _ *http.Request) {
	w.Header().Set("Content-Type", "text/plain")
	w.WriteHeader(http.StatusOK)
	w.Write([]byte("ok"))
}

// handleReadyz is a K8s readiness probe — returns 200 when ready to accept traffic,
// 503 when draining (zero-downtime rolling update, §15.7).
// GET /readyz
func (s *Server) handleReadyz(w http.ResponseWriter, _ *http.Request) {
	if s.socSvc.IsDraining() {
		w.Header().Set("Content-Type", "text/plain")
		w.WriteHeader(http.StatusServiceUnavailable)
		w.Write([]byte("draining"))
		return
	}
	// P0 fail-CLOSED (Review 14.06): a gateway serving the allow-all stub engine
	// must NOT report ready — an LB/k8s would route real traffic to a
	// non-detecting node. 503 unless an operator opted into stub mode.
	if !s.scanEngineReady() && !stubScanAllowed() {
		w.Header().Set("Content-Type", "text/plain")
		w.WriteHeader(http.StatusServiceUnavailable)
		w.Write([]byte("detection engine unavailable (stub mode)"))
		return
	}
	w.Header().Set("Content-Type", "text/plain")
	w.WriteHeader(http.StatusOK)
	w.Write([]byte("ok"))
}

// handleSensors returns registered sensors with health status.
// GET /api/soc/sensors
func (s *Server) handleSensors(w http.ResponseWriter, r *http.Request) {
	sensors, err := s.socSvc.ListSensors(tenantFromRequest(r))
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}

	writeJSON(w, http.StatusOK, map[string]any{
		"sensors": sensors,
		"count":   len(sensors),
	})
}

// getSecureIncident retrieves an incident and verifies tenant boundaries (IDOR prevention).
func (s *Server) getSecureIncident(r *http.Request, id string, fullDetail bool) (*domsoc.Incident, error) {
	claims := auth.GetClaims(r.Context())
	if claims == nil || strings.TrimSpace(claims.Sub) == "" || (claims.Role != "superadmin" && claims.TenantID == "") {
		return nil, fmt.Errorf("incident not found")
	}
	var inc *domsoc.Incident
	var err error
	if fullDetail {
		inc, err = s.socSvc.GetIncidentDetail(id)
	} else {
		inc, err = s.socSvc.GetIncident(id)
	}
	if err != nil {
		return nil, err
	}
	if inc == nil || (claims.Role != "superadmin" && inc.TenantID != claims.TenantID) {
		return nil, fmt.Errorf("incident not found") // Opaque error to avoid existence leak
	}
	return inc, nil
}

// incidentTenantScope returns the tenant filter for list/export endpoints: the
// caller's tenant, or "" for superadmin (all tenants). Review 13.06 (audit):
// advanced-list/export must be scoped to this, not to all tenants.
func (s *Server) incidentTenantScope(r *http.Request) string {
	if claims := auth.GetClaims(r.Context()); claims != nil {
		if claims.Role == "superadmin" {
			return ""
		}
		return claims.TenantID
	}
	return tenantFromRequest(r)
}

// writeIncidentMutationError reports audit failure without exposing backend details.
func writeIncidentMutationError(w http.ResponseWriter, err error) {
	if errors.Is(err, appsoc.ErrDecisionAuditUnavailable) {
		writeError(w, http.StatusServiceUnavailable, "decision audit unavailable")
		return
	}
	writeError(w, http.StatusNotFound, err.Error())
}

// handleIncidentDetail returns a single incident by ID.
// GET /api/soc/incidents/{id}
func (s *Server) handleIncidentDetail(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	if id == "" {
		writeError(w, http.StatusBadRequest, "missing incident ID")
		return
	}

	incident, err := s.getSecureIncident(r, id, false)
	if err != nil {
		writeError(w, http.StatusNotFound, err.Error())
		return
	}

	writeJSON(w, http.StatusOK, incident)
}

// requireGlobalSOCOperator protects process-wide views until they have a
// verified tenant-scoped data source. It does not authenticate the context.
func requireGlobalSOCOperator(w http.ResponseWriter, r *http.Request) bool {
	claims := auth.GetClaims(r.Context())
	if claims == nil || strings.TrimSpace(claims.Sub) == "" {
		writeError(w, http.StatusUnauthorized, "authentication required")
		return false
	}
	if claims.Role != "superadmin" {
		writeError(w, http.StatusForbidden, "operator access required")
		return false
	}
	return true
}

// handleClusters returns Alert Clustering statistics (§7.6).
// GET /api/soc/clusters
func (s *Server) handleClusters(w http.ResponseWriter, r *http.Request) {
	claims := auth.GetClaims(r.Context())
	if claims == nil || strings.TrimSpace(claims.Sub) == "" {
		writeError(w, http.StatusUnauthorized, "authentication required")
		return
	}
	if !hasPermission(Role(claims.Role), RoleViewer) {
		writeError(w, http.StatusForbidden, "insufficient role for cluster statistics")
		return
	}
	if claims.Role == string(RoleSuperadmin) {
		writeJSON(w, http.StatusOK, s.socSvc.ClusterStats())
		return
	}
	stats, err := s.socSvc.ClusterStatsForTenant(claims.TenantID)
	if err != nil {
		writeError(w, http.StatusForbidden, "tenant context required")
		return
	}
	writeJSON(w, http.StatusOK, stats)
}

// handleRules returns all active correlation rules.
// GET /api/soc/rules
func (s *Server) handleRules(w http.ResponseWriter, _ *http.Request) {
	rules := s.socSvc.ListRules()
	writeJSON(w, http.StatusOK, map[string]any{
		"rules": rules,
		"count": len(rules),
	})
}

// handleThreatIntel returns IOC database, feeds, and stats (§6).
// GET /api/soc/threat-intel
//
// Prefers the LIVE threat-intel store (operator-configured feeds fetched in the
// background via FeedSync / RefreshAll) so configured IOCs are actually visible.
// Falls back to the built-in sample engine only when no live IOCs are loaded
// (unconfigured / demo), preserving prior behavior.
func (s *Server) handleThreatIntel(w http.ResponseWriter, _ *http.Request) {
	if s.threatIntel != nil {
		if iocs := s.threatIntel.ListIOCs(); len(iocs) > 0 {
			writeJSON(w, http.StatusOK, map[string]any{
				"enabled": true,
				"source":  "live-feeds",
				"iocs":    iocs,
				"feeds":   s.threatIntel.GetFeeds(),
				"stats":   s.threatIntel.Stats(),
			})
			return
		}
	}

	ti := s.socSvc.ThreatIntelEngine()
	writeJSON(w, http.StatusOK, map[string]any{
		"enabled":     true,
		"source":      "sample",
		"iocs":        ti.ListIOCs(),
		"feeds":       ti.ListFeeds(),
		"stats":       ti.ThreatIntelStats(),
		"recent_hits": ti.RecentHits(20),
	})
}

// handleWebhookStats returns SOAR webhook delivery statistics.
// GET /api/soc/webhook-stats
func (s *Server) handleWebhookStats(w http.ResponseWriter, _ *http.Request) {
	stats := s.socSvc.WebhookStats()
	writeJSON(w, http.StatusOK, stats)
}

// handleAnalytics returns SOC analytics report.
// GET /api/soc/analytics?window=24
func (s *Server) handleAnalytics(w http.ResponseWriter, r *http.Request) {
	windowHours := 24 // default
	if v := r.URL.Query().Get("window"); v != "" {
		if parsed, err := strconv.Atoi(v); err == nil && parsed > 0 {
			windowHours = parsed
		}
	}

	report, err := s.socSvc.Analytics(s.incidentTenantScope(r), windowHours)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, report)
}

// handleIngestEvent processes a security event through the full SOC pipeline.
// POST /api/v1/soc/events
//
// Pipeline: Sensor Auth → Secret Scanner → Rate Limit → Decision Logger → Persist → Correlate → Playbook → Webhook
func (s *Server) handleIngestEvent(w http.ResponseWriter, r *http.Request) {
	// Review 13.06 (audit HIGH): cap the body. This is the ONLY POST handler that
	// omitted limitBody; the route is rate-limit-exempt and (when misconfigured)
	// unauthenticated, so an unbounded ReadAll was a memory-exhaustion DoS.
	limitBody(w, r)
	var req struct {
		Source      string            `json:"source"`
		SensorID    string            `json:"sensor_id"`
		SensorKey   string            `json:"sensor_key"`
		Severity    string            `json:"severity"`
		Category    string            `json:"category"`
		Subcategory string            `json:"subcategory"`
		Confidence  float64           `json:"confidence"`
		Description string            `json:"description"`
		Payload     string            `json:"payload"`
		SessionID   string            `json:"session_id"`
		ZeroGMode   bool              `json:"zero_g_mode"`
		Metadata    map[string]string `json:"metadata"`
	}

	defer r.Body.Close()
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON: "+err.Error())
		return
	}

	// Validate required fields.
	if req.Source == "" || req.Severity == "" || req.Category == "" || req.Description == "" {
		writeError(w, http.StatusBadRequest, "required fields: source, severity, category, description")
		return
	}

	// Build domain event.
	event := domsoc.NewSOCEvent(
		domsoc.EventSource(req.Source),
		domsoc.EventSeverity(req.Severity),
		req.Category,
		req.Description,
	)
	event.SensorID = req.SensorID
	if event.SensorID == "" {
		// Auto-assign sensor ID from source name.
		switch req.Source {
		case "sentinel-core":
			event.SensorID = "sensor-core-01"
		case "shield":
			event.SensorID = "sensor-shield-01"
		case "immune":
			event.SensorID = "sensor-immune-01"
		case "micro-swarm":
			event.SensorID = "sensor-swarm-01"
		case "gomcp":
			event.SensorID = "sensor-gomcp-01"
		default:
			event.SensorID = "sensor-ext-01"
		}
	}
	event.SensorKey = req.SensorKey
	event.Subcategory = req.Subcategory
	event.Confidence = req.Confidence
	event.Payload = req.Payload
	event.SessionID = req.SessionID
	event.ZeroGMode = req.ZeroGMode
	event.Metadata = req.Metadata
	if event.Metadata == nil {
		event.Metadata = make(map[string]string)
	}

	// Auto-enrich: inject source IP from HTTP request if not provided by client.
	if event.Metadata["src_ip"] == "" {
		ip := r.RemoteAddr
		if host, _, err := net.SplitHostPort(ip); err == nil {
			ip = host
		}
		event.Metadata["src_ip"] = ip
	}

	// Auto-enrich: set confidence from top-level field if not in metadata.
	if event.Metadata["confidence"] == "" && event.Confidence > 0 {
		event.Metadata["confidence"] = fmt.Sprintf("%.2f", event.Confidence)
	}

	// Run full pipeline.
	eventID, incident, err := s.socSvc.IngestEvent(event)
	if err != nil {
		// Map domain errors to HTTP status codes.
		switch {
		case errors.Is(err, domsoc.ErrInvalidInput):
			// Return 422 with field-level validation details.
			var ve *domsoc.ValidationErrors
			if errors.As(err, &ve) {
				writeJSON(w, http.StatusUnprocessableEntity, map[string]any{
					"error":  err.Error(),
					"fields": ve.Errors,
				})
			} else {
				writeError(w, http.StatusUnprocessableEntity, err.Error())
			}
		case errors.Is(err, appsoc.ErrDecisionAuditUnavailable):
			writeError(w, http.StatusServiceUnavailable, "decision audit unavailable")
		case errors.Is(err, domsoc.ErrDraining):
			writeError(w, http.StatusServiceUnavailable, err.Error())
		case errors.Is(err, domsoc.ErrCapacityFull):
			// §20.1: Scan semaphore at capacity — backpressure with Retry-After.
			w.Header().Set("Retry-After", "1")
			writeError(w, http.StatusServiceUnavailable, err.Error())
		case errors.Is(err, domsoc.ErrAuthFailed), errors.Is(err, domsoc.ErrSecretDetected):
			writeError(w, http.StatusForbidden, err.Error())
		case errors.Is(err, domsoc.ErrRateLimited):
			writeError(w, http.StatusTooManyRequests, err.Error())
		default:
			writeError(w, http.StatusInternalServerError, err.Error())
		}
		return
	}

	// Prometheus counters (Review 14.06 round-2: previously never incremented, so
	// /metrics reported 0 events/incidents forever).
	if s.metrics != nil {
		s.metrics.IncEvents()
		if incident != nil {
			s.metrics.IncIncidents()
		}
	}

	resp := map[string]any{
		"event_id": eventID,
		"status":   "ingested",
	}
	if incident != nil {
		resp["incident"] = incident
		resp["status"] = "ingested_with_incident"
	}

	writeJSON(w, http.StatusCreated, resp)
}

// MaxBatchSize limits the number of events in a single batch request (§5.3).
const MaxBatchSize = 1000

// handleBatchIngest processes multiple security events through the SOC pipeline (§5.3).
// POST /api/v1/soc/events/batch
func (s *Server) handleBatchIngest(w http.ResponseWriter, r *http.Request) {
	var events []struct {
		Source      string            `json:"source"`
		SensorID    string            `json:"sensor_id"`
		SensorKey   string            `json:"sensor_key"`
		Severity    string            `json:"severity"`
		Category    string            `json:"category"`
		Subcategory string            `json:"subcategory"`
		Confidence  float64           `json:"confidence"`
		Description string            `json:"description"`
		Payload     string            `json:"payload"`
		SessionID   string            `json:"session_id"`
		ZeroGMode   bool              `json:"zero_g_mode"`
		Metadata    map[string]string `json:"metadata"`
	}

	limitBody(w, r)
	defer r.Body.Close()
	if err := json.NewDecoder(r.Body).Decode(&events); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON array: "+err.Error())
		return
	}

	if len(events) == 0 {
		writeError(w, http.StatusBadRequest, "empty batch")
		return
	}
	if len(events) > MaxBatchSize {
		writeError(w, http.StatusBadRequest, fmt.Sprintf("batch size %d exceeds max %d", len(events), MaxBatchSize))
		return
	}

	type batchResult struct {
		Index    int    `json:"index"`
		EventID  string `json:"event_id,omitempty"`
		Status   string `json:"status"`
		Incident any    `json:"incident,omitempty"`
		Error    string `json:"error,omitempty"`
	}

	results := make([]batchResult, len(events))
	ingested := 0
	backpressured := 0
	auditUnavailable := 0

	for i, req := range events {
		event := domsoc.NewSOCEvent(
			domsoc.EventSource(req.Source),
			domsoc.EventSeverity(req.Severity),
			req.Category,
			req.Description,
		)
		event.SensorID = req.SensorID
		event.SensorKey = req.SensorKey
		event.Subcategory = req.Subcategory
		event.Confidence = req.Confidence
		event.Payload = req.Payload
		event.SessionID = req.SessionID
		event.ZeroGMode = req.ZeroGMode
		event.Metadata = req.Metadata

		eventID, incident, err := s.socSvc.IngestEvent(event)
		if err != nil {
			status := "rejected"
			if errors.Is(err, appsoc.ErrDecisionAuditUnavailable) {
				status = "unavailable"
				auditUnavailable++
			} else if errors.Is(err, domsoc.ErrCapacityFull) {
				status = "backpressure"
				backpressured++
			}
			results[i] = batchResult{Index: i, Status: status, Error: err.Error()}
			continue
		}

		result := batchResult{Index: i, EventID: eventID, Status: "ingested"}
		if incident != nil {
			result.Status = "ingested_with_incident"
			result.Incident = incident
		}
		results[i] = result
		ingested++
		if s.metrics != nil {
			s.metrics.IncEvents()
			if incident != nil {
				s.metrics.IncIncidents()
			}
		}
	}

	// §20.1: If the entire batch was rejected by backpressure, signal 503 so the
	// client retries. Only do this when the failures were actually backpressure —
	// a batch of purely malformed events (validation rejects) must NOT return a
	// retryable 503, since retrying the same bad input cannot succeed.
	httpStatus := http.StatusCreated
	if ingested == 0 && auditUnavailable > 0 {
		httpStatus = http.StatusServiceUnavailable
	} else if ingested == 0 && backpressured > 0 {
		w.Header().Set("Retry-After", "1")
		httpStatus = http.StatusServiceUnavailable
	}

	writeJSON(w, httpStatus, map[string]any{
		"total":    len(events),
		"ingested": ingested,
		"rejected": len(events) - ingested,
		"results":  results,
	})
}

// handleSensorHeartbeat records a sensor heartbeat (§11.3).
// POST /api/soc/sensors/heartbeat
func (s *Server) handleSensorHeartbeat(w http.ResponseWriter, r *http.Request) {
	var req struct {
		SensorID  string `json:"sensor_id"`
		SensorKey string `json:"sensor_key"`
	}
	limitBody(w, r)
	defer r.Body.Close()
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON: "+err.Error())
		return
	}

	if req.SensorID == "" {
		writeError(w, http.StatusBadRequest, "required field: sensor_id")
		return
	}

	ok, err := s.socSvc.RecordHeartbeat(req.SensorID, req.SensorKey)
	if err != nil {
		// Auth failure → 403 (and no sensor-existence oracle when PSK is on);
		// otherwise sensor-not-found → 404 (Review 14.06 round-4).
		if errors.Is(err, domsoc.ErrAuthFailed) {
			writeError(w, http.StatusForbidden, err.Error())
			return
		}
		writeError(w, http.StatusNotFound, err.Error())
		return
	}

	writeJSON(w, http.StatusOK, map[string]any{
		"sensor_id": req.SensorID,
		"recorded":  ok,
	})
}

// handleSSEStream provides Server-Sent Events for real-time event streaming.
// GET /api/soc/stream
func (s *Server) handleSSEStream(w http.ResponseWriter, r *http.Request) {
	flusher, ok := w.(http.Flusher)
	if !ok {
		writeError(w, http.StatusInternalServerError, "SSE not supported")
		return
	}

	// Cap concurrent SSE connections BEFORE writing any stream headers (Review
	// 14.06 round-5): each subscription holds a goroutine + FD + a buffered
	// channel, and this route is rate-limit exempt, so one principal could open
	// thousands and exhaust FDs/goroutines/heap for ALL tenants. Mirrors the
	// WSHub guard.
	const maxSSEConnections = 500
	if s.socSvc.EventBus().SubscriberCount() >= maxSSEConnections {
		w.Header().Set("Retry-After", "30")
		writeError(w, http.StatusServiceUnavailable, "max concurrent event streams reached")
		return
	}

	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("Connection", "keep-alive")
	// Note: CORS is already handled by corsMiddleware — no need to set it here.
	w.Header().Set("X-Accel-Buffering", "no") // Disable nginx/proxy buffering

	// Explicitly write status and flush headers so EventSource.onopen fires immediately.
	w.WriteHeader(http.StatusOK)
	flusher.Flush()

	// Subscribe to event bus with a cryptographically-random id (Review 14.06
	// round-5): a UnixNano()-only id can collide under concurrent connects (esp.
	// the coarse Windows wall clock), and a colliding id overwrites another
	// stream's channel in the bus map — silently dropping that stream's events and
	// killing it on Unsubscribe. Mirrors the WSHub crypto/rand client id.
	var rnd [16]byte
	_, _ = rand.Read(rnd[:])
	subID := "sse-" + hex.EncodeToString(rnd[:])
	ch := s.socSvc.EventBus().SubscribeTenant(subID, s.incidentTenantScope(r))
	defer s.socSvc.EventBus().Unsubscribe(subID)

	// SEC (multi-tenant isolation): the EventBus is a single global stream that
	// carries every tenant's events. Without filtering, any authenticated viewer
	// would receive other tenants' event descriptions/session IDs in real time
	// (cross-tenant data leak). Scope this stream to the caller's tenant.
	// "" = superadmin / single-tenant-or-test deployments → see all.
	scope := s.incidentTenantScope(r)

	// Send initial comment to establish connection
	fmt.Fprintf(w, ": connected to syntrex event stream\n\n")
	flusher.Flush()

	// Keepalive ticker
	ticker := time.NewTicker(15 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case event, ok := <-ch:
			if !ok {
				return
			}
			// Drop events that belong to a different tenant.
			if scope != "" && event.TenantID != scope {
				continue
			}
			data, _ := json.Marshal(event)
			fmt.Fprintf(w, "event: soc_event\ndata: %s\n\n", data)
			flusher.Flush()

		case <-ticker.C:
			fmt.Fprintf(w, ": keepalive\n\n")
			flusher.Flush()

		case <-r.Context().Done():
			return
		}
	}
}

// handleKillChain reconstructs the Kill Chain for an incident (§8).
// GET /api/soc/killchain/{id}
func (s *Server) handleKillChain(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	if id == "" {
		writeError(w, http.StatusBadRequest, "missing incident ID")
		return
	}

	// Review 13.06 (audit): enforce the tenant boundary before reconstructing the
	// kill chain. GetKillChain takes no tenant, so this was a cross-tenant IDOR.
	if _, err := s.getSecureIncident(r, id, false); err != nil {
		writeError(w, http.StatusNotFound, "incident not found")
		return
	}

	kc, err := s.socSvc.GetKillChain(id)
	if err != nil {
		writeError(w, http.StatusNotFound, err.Error())
		return
	}

	writeJSON(w, http.StatusOK, kc)
}

// handleAuditTrail returns decision log entries for forensic review (§9).
// GET /api/soc/audit
func (s *Server) handleAuditTrail(w http.ResponseWriter, r *http.Request) {
	// The decision logger stores entries in the audit database.
	// For now, return basic audit metadata from service.
	result := map[string]any{
		"status":  "operational",
		"message": "Audit trail available via decision logger",
	}

	// Add recent decisions if available via service
	decisions := s.socSvc.GetRecentDecisions(50)
	result["decisions"] = decisions
	result["total"] = len(decisions)

	writeJSON(w, http.StatusOK, result)
}

// handleListKeys returns registered RBAC API keys (masked) for admin review (§17).
// GET /api/soc/keys
func (s *Server) handleListKeys(w http.ResponseWriter, r *http.Request) {
	keys := s.rbac.ListKeys()
	writeJSON(w, http.StatusOK, map[string]any{
		"keys":  keys,
		"total": len(keys),
	})
}

// handleZeroGStatus returns Zero-G mode status and pending requests (§13.4).
// GET /api/soc/zerog
func (s *Server) handleZeroGStatus(w http.ResponseWriter, r *http.Request) {
	zg := s.socSvc.ZeroG()
	writeJSON(w, http.StatusOK, map[string]any{
		"stats":   zg.Stats(),
		"pending": zg.PendingRequests(),
	})
}

// handleZeroGToggle enables or disables Zero-G mode (§13.4).
// POST /api/soc/zerog/toggle  body: {"enabled": true}
func (s *Server) handleZeroGToggle(w http.ResponseWriter, r *http.Request) {
	var req struct {
		Enabled bool `json:"enabled"`
	}
	limitBody(w, r)
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON")
		return
	}

	zg := s.socSvc.ZeroG()
	if req.Enabled {
		zg.Enable()
	} else {
		zg.Disable()
	}

	writeJSON(w, http.StatusOK, map[string]any{
		"zero_g_enabled": zg.IsEnabled(),
	})
}

// handleZeroGResolve processes an analyst verdict on a pending Zero-G request (§13.4).
// POST /api/soc/zerog/resolve  body: {"request_id": "zg-...", "verdict": "APPROVE", "analyst": "admin"}
func (s *Server) handleZeroGResolve(w http.ResponseWriter, r *http.Request) {
	var req struct {
		RequestID string `json:"request_id"`
		Verdict   string `json:"verdict"`
		Analyst   string `json:"analyst"`
	}
	limitBody(w, r)
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON")
		return
	}
	if req.RequestID == "" || req.Verdict == "" {
		writeError(w, http.StatusBadRequest, "request_id and verdict required")
		return
	}

	zg := s.socSvc.ZeroG()
	err := zg.Resolve(req.RequestID, domsoc.ZeroGVerdict(req.Verdict), req.Analyst)
	if err != nil {
		writeError(w, http.StatusNotFound, err.Error())
		return
	}

	writeJSON(w, http.StatusOK, map[string]string{"status": "resolved"})
}

// handleVerdict updates an incident's status (manual analyst verdict).
// POST /api/soc/incidents/{id}/verdict  body: {"status": "RESOLVED"}
func (s *Server) handleVerdict(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	if id == "" {
		writeError(w, http.StatusBadRequest, "incident ID required")
		return
	}

	var req struct {
		Status string `json:"status"`
	}
	limitBody(w, r)
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON")
		return
	}
	if req.Status == "" {
		writeError(w, http.StatusBadRequest, "status required (INVESTIGATING, RESOLVED)")
		return
	}

	// Verify access
	inc, err := s.getSecureIncident(r, id, false)
	if err != nil {
		writeError(w, http.StatusNotFound, "incident not found")
		return
	}

	if err := s.socSvc.UpdateVerdict(id, domsoc.IncidentStatus(req.Status)); err != nil {
		writeIncidentMutationError(w, err)
		return
	}

	// Data-capture flywheel: a terminal disposition (RESOLVED/FALSE_POSITIVE) is
	// the supervised signal — write the label back onto the related scan samples
	// (gated/async/best-effort; no-op when capture is unwired).
	s.attachOrchestratorLabel(inc, domsoc.IncidentStatus(req.Status))

	writeJSON(w, http.StatusOK, map[string]string{
		"incident_id": id,
		"status":      req.Status,
	})
}

// === Case Management Endpoints ===

// POST /api/soc/incidents/{id}/assign  body: {"analyst": "john.doe"}
func (s *Server) handleIncidentAssign(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	if id == "" {
		writeError(w, http.StatusBadRequest, "incident ID required")
		return
	}

	var req struct {
		Analyst string `json:"analyst"`
	}
	limitBody(w, r)
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON")
		return
	}
	if req.Analyst == "" {
		writeError(w, http.StatusBadRequest, "analyst name required")
		return
	}

	// Verify access
	if _, err := s.getSecureIncident(r, id, false); err != nil {
		writeError(w, http.StatusNotFound, "incident not found")
		return
	}

	if err := s.socSvc.AssignIncident(id, req.Analyst); err != nil {
		writeIncidentMutationError(w, err)
		return
	}

	writeJSON(w, http.StatusOK, map[string]string{
		"incident_id": id,
		"assigned_to": req.Analyst,
		"status":      "assigned",
	})
}

// POST /api/soc/incidents/{id}/status  body: {"status": "INVESTIGATING", "actor": "john.doe"}
func (s *Server) handleIncidentStatus(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	if id == "" {
		writeError(w, http.StatusBadRequest, "incident ID required")
		return
	}

	var req struct {
		Status string `json:"status"`
		Actor  string `json:"actor"`
	}
	limitBody(w, r)
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON")
		return
	}
	if req.Status == "" {
		writeError(w, http.StatusBadRequest, "status required")
		return
	}
	if claims := auth.GetClaims(r.Context()); claims != nil {
		req.Actor = claims.Sub
	} else {
		writeError(w, http.StatusUnauthorized, "authenticated actor required")
		return
	}

	// Validate status
	validStatuses := map[string]bool{
		"OPEN": true, "INVESTIGATING": true, "RESOLVED": true, "FALSE_POSITIVE": true,
	}
	if !validStatuses[req.Status] {
		writeError(w, http.StatusBadRequest, "invalid status (OPEN, INVESTIGATING, RESOLVED, FALSE_POSITIVE)")
		return
	}

	// Verify access
	inc, err := s.getSecureIncident(r, id, false)
	if err != nil {
		writeError(w, http.StatusNotFound, "incident not found")
		return
	}

	if err := s.socSvc.ChangeIncidentStatus(id, domsoc.IncidentStatus(req.Status), req.Actor); err != nil {
		writeIncidentMutationError(w, err)
		return
	}

	// Data-capture flywheel: a terminal disposition (RESOLVED/FALSE_POSITIVE) is
	// the supervised signal — write the label back onto the related scan samples
	// (gated/async/best-effort; no-op when capture is unwired).
	s.attachOrchestratorLabel(inc, domsoc.IncidentStatus(req.Status))

	writeJSON(w, http.StatusOK, map[string]string{
		"incident_id": id,
		"status":      req.Status,
		"actor":       req.Actor,
	})
}

// POST /api/soc/incidents/{id}/notes  body: {"author": "john.doe", "content": "Found C2 callback"}
// GET  /api/soc/incidents/{id}/notes  → returns notes array
func (s *Server) handleIncidentNotes(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	if id == "" {
		writeError(w, http.StatusBadRequest, "incident ID required")
		return
	}

	if r.Method == http.MethodGet {
		inc, err := s.getSecureIncident(r, id, true)
		if err != nil {
			writeError(w, http.StatusNotFound, err.Error())
			return
		}
		writeJSON(w, http.StatusOK, map[string]any{
			"incident_id": id,
			"notes":       inc.Notes,
			"count":       len(inc.Notes),
		})
		return
	}

	// POST — add note
	var req struct {
		Author  string `json:"author"`
		Content string `json:"content"`
	}
	limitBody(w, r)
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON")
		return
	}
	if req.Content == "" {
		writeError(w, http.StatusBadRequest, "content required")
		return
	}
	if claims := auth.GetClaims(r.Context()); claims != nil {
		req.Author = claims.Sub
	} else {
		writeError(w, http.StatusUnauthorized, "authenticated author required")
		return
	}

	// Verify access before mutating
	if _, err := s.getSecureIncident(r, id, false); err != nil {
		writeError(w, http.StatusNotFound, "incident not found")
		return
	}

	note, err := s.socSvc.AddIncidentNote(id, req.Author, req.Content)
	if err != nil {
		writeIncidentMutationError(w, err)
		return
	}

	writeJSON(w, http.StatusCreated, note)
}

// GET /api/soc/incidents/{id}/timeline → full incident timeline
func (s *Server) handleIncidentTimeline(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	if id == "" {
		writeError(w, http.StatusBadRequest, "incident ID required")
		return
	}

	inc, err := s.getSecureIncident(r, id, true)
	if err != nil {
		writeError(w, http.StatusNotFound, err.Error())
		return
	}

	writeJSON(w, http.StatusOK, map[string]any{
		"incident_id": id,
		"timeline":    inc.Timeline,
		"count":       len(inc.Timeline),
		"status":      inc.Status,
		"assigned_to": inc.AssignedTo,
		"severity":    inc.Severity,
	})
}

// GET /api/soc/incidents/{id}/detail → full incident with notes + timeline
func (s *Server) handleIncidentFullDetail(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	if id == "" {
		writeError(w, http.StatusBadRequest, "incident ID required")
		return
	}

	inc, err := s.getSecureIncident(r, id, true)
	if err != nil {
		writeError(w, http.StatusNotFound, err.Error())
		return
	}

	writeJSON(w, http.StatusOK, inc)
}

// === Webhook Management Endpoints (SOAR §15) ===

// GET /api/soc/webhooks → returns webhook config + delivery stats
func (s *Server) handleWebhooksGet(w http.ResponseWriter, r *http.Request) {
	stats := s.socSvc.WebhookStats()
	config := s.socSvc.GetWebhookConfig()

	result := map[string]any{
		"stats": stats,
	}
	if config != nil {
		result["config"] = config
	} else {
		result["config"] = map[string]any{
			"endpoints":   []string{},
			"headers":     map[string]string{},
			"max_retries": 3,
			"timeout_sec": 10,
		}
	}
	writeJSON(w, http.StatusOK, result)
}

// POST /api/soc/webhooks → configure webhook endpoints
// body: {"endpoints": ["https://hooks.slack.com/..."], "headers": {"Authorization": "Bearer xyz"}, "max_retries": 3}
func (s *Server) handleWebhooksSet(w http.ResponseWriter, r *http.Request) {
	var config appsoc.WebhookConfig
	limitBody(w, r)
	if err := json.NewDecoder(r.Body).Decode(&config); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON: "+err.Error())
		return
	}
	if config.MaxRetries <= 0 {
		config.MaxRetries = 3
	}
	if config.TimeoutSec <= 0 {
		config.TimeoutSec = 10
	}

	// SSRF guard at the config entry point: reject bad/internal endpoints on input
	// so an operator can't persist a URL that targets loopback/metadata/private IPs.
	// The notifier re-validates and SafeDialContext re-resolves at dial time too.
	for _, ep := range config.Endpoints {
		if err := domsoc.ValidateWebhookURL(ep); err != nil {
			writeError(w, http.StatusBadRequest, "invalid webhook endpoint "+ep+": "+err.Error())
			return
		}
	}

	s.socSvc.SetWebhookConfig(config)

	writeJSON(w, http.StatusOK, map[string]any{
		"status":    "configured",
		"endpoints": len(config.Endpoints),
		"retries":   config.MaxRetries,
	})
}

// POST /api/soc/webhooks/test → send test ping to all endpoints
func (s *Server) handleWebhooksTest(w http.ResponseWriter, r *http.Request) {
	results := s.socSvc.TestWebhook()
	if results == nil {
		writeJSON(w, http.StatusOK, map[string]any{
			"status":  "no_webhooks",
			"message": "No webhook endpoints configured",
		})
		return
	}

	writeJSON(w, http.StatusOK, map[string]any{
		"status":  "tested",
		"results": results,
	})
}

// handleSensorRegister registers a new sensor with the SOC.
// POST /api/soc/sensors/register  body: {"id":"s-1","name":"Shield-1","type":"shield"}
func (s *Server) handleSensorRegister(w http.ResponseWriter, r *http.Request) {
	var req struct {
		ID   string `json:"id"`
		Name string `json:"name"`
		Type string `json:"type"`
	}
	limitBody(w, r)
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON")
		return
	}
	if req.ID == "" || req.Name == "" {
		writeError(w, http.StatusBadRequest, "id and name required")
		return
	}

	if err := s.socSvc.RegisterSensor(req.ID, req.Name, req.Type); err != nil {
		if errors.Is(err, domsoc.ErrCapacityFull) {
			writeError(w, http.StatusServiceUnavailable, "sensor capacity full")
		} else {
			writeError(w, http.StatusConflict, err.Error())
		}
		return
	}

	writeJSON(w, http.StatusCreated, map[string]string{
		"sensor_id": req.ID,
		"status":    "registered",
	})
}

// handleSensorDelete removes a sensor from the SOC.
// DELETE /api/soc/sensors/{id}
func (s *Server) handleSensorDelete(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	if id == "" {
		writeError(w, http.StatusBadRequest, "sensor ID required")
		return
	}

	s.socSvc.DeregisterSensor(id)

	writeJSON(w, http.StatusOK, map[string]string{
		"sensor_id": id,
		"status":    "deregistered",
	})
}

// handleRateLimitStats returns rate limiter statistics.
// GET /api/soc/ratelimit
func (s *Server) handleRateLimitStats(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, s.rateLimiter.Stats())
}

// handleP2PPeers returns all P2P SOC peers and sync stats (§14).
// GET /api/soc/p2p/peers
func (s *Server) handleP2PPeers(w http.ResponseWriter, r *http.Request) {
	p2p := s.socSvc.P2PSync()
	writeJSON(w, http.StatusOK, map[string]any{
		"peers": p2p.ListPeers(),
		"stats": p2p.Stats(),
	})
}

// handleP2PAddPeer registers a new SOC peer for synchronization (§14).
// POST /api/soc/p2p/peers  body: {"id":"soc-2","name":"Site-B","endpoint":"http://b:9100","trust":"full"}
func (s *Server) handleP2PAddPeer(w http.ResponseWriter, r *http.Request) {
	var req struct {
		ID       string `json:"id"`
		Name     string `json:"name"`
		Endpoint string `json:"endpoint"`
		Trust    string `json:"trust"`
	}
	limitBody(w, r)
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON")
		return
	}
	if req.ID == "" || req.Endpoint == "" {
		writeError(w, http.StatusBadRequest, "id and endpoint required")
		return
	}
	if req.Trust == "" {
		req.Trust = "readonly"
	}

	s.socSvc.P2PSync().AddPeer(req.ID, req.Name, req.Endpoint, req.Trust)
	writeJSON(w, http.StatusCreated, map[string]string{
		"peer_id": req.ID,
		"status":  "registered",
	})
}

// handleP2PRemovePeer deregisters a SOC peer (§14).
// DELETE /api/soc/p2p/peers/{id}
func (s *Server) handleP2PRemovePeer(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	if id == "" {
		writeError(w, http.StatusBadRequest, "peer ID required")
		return
	}
	s.socSvc.P2PSync().RemovePeer(id)
	writeJSON(w, http.StatusOK, map[string]string{"peer_id": id, "status": "removed"})
}

// handleEngineStatus returns status of security engines (§3, §4).
// GET /api/soc/engines
func (s *Server) handleEngineStatus(w http.ResponseWriter, r *http.Request) {
	coreEngine := s.getEngine("sentinel-core")
	var shieldEng engines.Shield
	if s.shieldEngine != nil {
		shieldEng = s.shieldEngine
	} else {
		shieldEng = engines.NewStubShield()
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"engines": []map[string]any{
			{
				"name":    coreEngine.Name(),
				"status":  coreEngine.Status(),
				"version": coreEngine.Version(),
				"type":    "prompt_scanner",
			},
			{
				"name":    shieldEng.Name(),
				"status":  shieldEng.Status(),
				"version": shieldEng.Version(),
				"type":    "network_protection",
			},
		},
	})
}

// getEngine returns the named SentinelCore engine or a stub.
func (s *Server) getEngine(name string) engines.SentinelCore {
	if s.sentinelCore != nil && name == "sentinel-core" {
		return s.sentinelCore
	}
	return engines.NewStubSentinelCore()
}

// handleSovereignConfig returns the Sovereign Mode configuration (§21).
// GET /api/soc/sovereign
func (s *Server) handleSovereignConfig(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{
		"sovereign": map[string]any{
			"enabled":      s.sovereignEnabled,
			"mode":         s.sovereignMode,
			"air_gapped":   s.sovereignMode == "airgap",
			"external_api": !s.sovereignEnabled,
			"local_only":   s.sovereignMode == "airgap",
		},
	})
}

// handleAnomalyAlerts returns recent anomaly alerts (§5).
// GET /api/soc/anomaly/alerts
func (s *Server) handleAnomalyAlerts(w http.ResponseWriter, r *http.Request) {
	if !requireGlobalSOCOperator(w, r) {
		return
	}
	limit := 50
	if l := r.URL.Query().Get("limit"); l != "" {
		if n, err := strconv.Atoi(l); err == nil && n > 0 {
			limit = n
			if limit > 1000 {
				limit = 1000 // T4-5 FIX: hard cap prevents memory exhaustion DoS
			}
		}
	}
	detector := s.socSvc.AnomalyDetector()
	writeJSON(w, http.StatusOK, map[string]any{
		"alerts": detector.Alerts(limit),
		"stats":  detector.Stats(),
	})
}

// handleAnomalyBaselines returns tracked metric baselines (§5).
// GET /api/soc/anomaly/baselines
func (s *Server) handleAnomalyBaselines(w http.ResponseWriter, r *http.Request) {
	if !requireGlobalSOCOperator(w, r) {
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"baselines": s.socSvc.AnomalyDetector().Baselines(),
	})
}

// handlePlaybooks returns all playbooks and execution stats (§10).
// GET /api/soc/playbooks
func (s *Server) handlePlaybooks(w http.ResponseWriter, r *http.Request) {
	pe := s.socSvc.PlaybookEngine()
	var executionLog any
	if claims := auth.GetClaims(r.Context()); claims != nil && claims.Role == "superadmin" {
		executionLog = pe.ExecutionLog(20)
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"playbooks": pe.ListPlaybooks(),
		"stats":     pe.PlaybookStats(),
		"log":       executionLog,
	})
}

// handleDeepHealth returns deep system health across all components.
// GET /api/soc/health/deep
func (s *Server) handleDeepHealth(w http.ResponseWriter, r *http.Request) {
	overallStatus := "HEALTHY"

	// Anomaly detector
	anomalyStats := s.socSvc.AnomalyDetector().Stats()

	// Playbook engine
	pbStats := s.socSvc.PlaybookEngine().PlaybookStats()

	// P2P Sync
	p2pStats := s.socSvc.P2PSync().Stats()

	// Engine status
	engineStatus := "stub"
	if s.sentinelCore != nil {
		st := s.sentinelCore.Status()
		engineStatus = string(st)
		if st == engines.EngineDegraded {
			overallStatus = "DEGRADED"
		}
	}

	// Check for critical anomalies
	if alerts := s.socSvc.AnomalyDetector().Alerts(5); len(alerts) > 0 {
		for _, a := range alerts {
			if a.Severity == "CRITICAL" {
				overallStatus = "DEGRADED"
				break
			}
		}
	}

	writeJSON(w, http.StatusOK, map[string]any{
		"status":    overallStatus,
		"timestamp": time.Now().Format(time.RFC3339),
		"components": map[string]any{
			"database":         "HEALTHY",
			"correlation":      "HEALTHY",
			"anomaly_detector": anomalyStats,
			"playbook_engine":  pbStats,
			"p2p_sync":         p2pStats,
			"sentinel_core":    engineStatus,
		},
	})
}

// handleComplianceReport returns EU AI Act Article 15 compliance summary (§12.3).
// GET /api/soc/compliance
//
// WS8: delegates to the single honest assessment in soc.Service.ComplianceReport
// rather than maintaining a second, divergent copy that hardcoded COMPLIANT from
// static strings. The service reports SELF_ATTESTED / NOT_ASSESSED where there is
// no machine-verifiable evidence, so this endpoint never overstates conformity.
func (s *Server) handleComplianceReport(w http.ResponseWriter, r *http.Request) {
	report, err := s.socSvc.ComplianceReport()
	if err != nil {
		writeError(w, http.StatusInternalServerError, "compliance: report unavailable: "+err.Error())
		return
	}
	writeJSON(w, http.StatusOK, report)
}

// handleSOC2ComplianceReport returns a SOC 2 Common Criteria (CC4/CC7)
// self-assessment (§12.3, IMP8). GET /api/soc/compliance/soc2
//
// Like the EU AI Act report it delegates to the single honest assessment in
// soc.Service so each control is backed by live, machine-verifiable evidence
// (decision-chain integrity, SOC metrics) and degrades truthfully when that
// evidence is absent (a broken/empty chain reports NON_COMPLIANT, not COMPLIANT).
func (s *Server) handleSOC2ComplianceReport(w http.ResponseWriter, r *http.Request) {
	report, err := s.socSvc.SOC2ComplianceReport()
	if err != nil {
		writeError(w, http.StatusInternalServerError, "compliance: soc2 report unavailable: "+err.Error())
		return
	}
	writeJSON(w, http.StatusOK, report)
}

// handleAuditTrailPage returns decision chain entries for the audit page.
// GET /api/soc/audit?limit=100
func (s *Server) handleAuditTrailPage(w http.ResponseWriter, r *http.Request) {
	limit := 100
	if l := r.URL.Query().Get("limit"); l != "" {
		if n, err := strconv.Atoi(l); err == nil && n > 0 {
			limit = n
			if limit > 5000 {
				limit = 5000 // T4-5 FIX: hard cap on audit entries
			}
		}
	}
	tenantID := tenantFromRequest(r)
	events, _ := s.socSvc.ListEvents(tenantID, limit)
	incidents, _ := s.socSvc.ListIncidents(tenantID, "", 50)

	// Build audit entries from events
	entries := make([]map[string]any, 0, len(events))
	for _, e := range events {
		entries = append(entries, map[string]any{
			"timestamp": e.Timestamp.Format(time.RFC3339),
			"type":      "event",
			"source":    e.Source,
			"severity":  e.Severity,
			"category":  e.Category,
			"verdict":   e.Verdict,
			"id":        e.ID,
		})
	}
	for _, inc := range incidents {
		entries = append(entries, map[string]any{
			"timestamp":  inc.CreatedAt.Format(time.RFC3339),
			"type":       "incident",
			"severity":   inc.Severity,
			"status":     inc.Status,
			"title":      inc.Title,
			"id":         inc.ID,
			"chain_hash": inc.DecisionChainAnchor,
		})
	}

	writeJSON(w, http.StatusOK, map[string]any{
		"entries": entries,
		"total":   len(entries),
	})
}

// handleThreatIntelMatch checks a value against the IOC database (§6).
// POST /api/soc/threat-intel/match
func (s *Server) handleThreatIntelMatch(w http.ResponseWriter, r *http.Request) {
	var req struct {
		Value   string `json:"value"`
		EventID string `json:"event_id"`
	}
	limitBody(w, r)
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid body")
		return
	}
	// Live store first (operator-configured feeds). When the store is populated
	// it is authoritative; otherwise fall back to the built-in sample engine.
	if s.threatIntel != nil && s.threatIntel.IOCCount() > 0 {
		matches := s.threatIntel.LookupAny(req.Value)
		if matches == nil {
			matches = []*appsoc.IOC{}
		}
		writeJSON(w, http.StatusOK, map[string]any{
			"source":  "live-feeds",
			"value":   req.Value,
			"matches": matches,
		})
		return
	}

	ti := s.socSvc.ThreatIntelEngine()
	if req.EventID != "" {
		hits := ti.MatchEvent(req.EventID, req.Value)
		writeJSON(w, http.StatusOK, map[string]any{
			"hits": hits,
		})
		return
	}
	ioc := ti.Match(req.Value)
	writeJSON(w, http.StatusOK, map[string]any{
		"match": ioc,
	})
}

// handleRetentionPolicies returns data retention policies and stats (§19).
// GET /api/soc/retention
func (s *Server) handleRetentionPolicies(w http.ResponseWriter, r *http.Request) {
	rp := s.socSvc.RetentionPolicy()
	writeJSON(w, http.StatusOK, map[string]any{
		"policies": rp.ListPolicies(),
		"stats":    rp.RetentionStats(),
	})
}

// handleIncidentExplain returns human-readable explanation of an incident (§12.3 EU AI Act Art.15).
// GET /api/soc/incidents/{id}/explain
func (s *Server) handleIncidentExplain(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	if id == "" {
		writeError(w, http.StatusBadRequest, "missing incident ID")
		return
	}

	incident, err := s.getSecureIncident(r, id, false)
	if err != nil {
		writeError(w, http.StatusNotFound, err.Error())
		return
	}

	// Build human-readable explanation
	explanation := map[string]any{
		"incident_id": incident.ID,
		"summary":     fmt.Sprintf("Incident '%s' (%s severity) was created by correlation rule '%s'.", incident.Title, incident.Severity, incident.CorrelationRule),
		"trigger": map[string]any{
			"rule_id":    incident.CorrelationRule,
			"severity":   incident.Severity,
			"created_at": incident.CreatedAt.Format(time.RFC3339),
		},
		"kill_chain": map[string]any{
			"phase":       incident.KillChainPhase,
			"mitre_ids":   incident.MITREMapping,
			"description": fmt.Sprintf("This incident is classified in the '%s' phase of the Cyber Kill Chain.", incident.KillChainPhase),
		},
		"evidence": map[string]any{
			"event_count":    len(incident.Events),
			"event_ids":      incident.Events,
			"decision_chain": incident.DecisionChainAnchor,
		},
		"response": map[string]any{
			"playbook_applied": incident.PlaybookApplied,
			"status":           incident.Status,
		},
		"explainability_note": "This explanation is auto-generated from correlation rules and event metadata. For detailed rule logic, see /api/soc/rules.",
	}

	writeJSON(w, http.StatusOK, explanation)
}

// ── Sprint 2: Incident Management Enhancements ─────────────────────────

// handleIncidentsAdvanced returns filtered, paginated incidents.
// GET /api/soc/incidents/advanced?status=OPEN&severity=HIGH&assigned_to=&search=&page=1&limit=20&sort_by=created_at&sort_order=desc
func (s *Server) handleIncidentsAdvanced(w http.ResponseWriter, r *http.Request) {
	q := r.URL.Query()
	page, _ := strconv.Atoi(q.Get("page"))
	limit, _ := strconv.Atoi(q.Get("limit"))
	// Input-boundary clamp: the service computes start=(page-1)*limit and slices
	// filtered[start:end]. A huge page (e.g. ?page=922337203685477580) overflows
	// that int multiplication to a negative start, which slips past the
	// start>=total guard and panics with "slice bounds out of range". Bound both
	// values here so the downstream arithmetic can never overflow. The service
	// still applies its own <=0 defaults; we only enforce sane upper limits and
	// drop negatives (consistent with the limit cap used by handleEvents).
	if page < 1 {
		page = 1
	}
	if page > 1_000_000 {
		page = 1_000_000
	}
	if limit < 1 {
		limit = 20
	}
	if limit > 200 {
		limit = 200
	}
	filter := appsoc.IncidentFilter{
		Status:     q.Get("status"),
		Severity:   q.Get("severity"),
		AssignedTo: q.Get("assigned_to"),
		Search:     q.Get("search"),
		Source:     q.Get("source"),
		DateFrom:   q.Get("date_from"),
		DateTo:     q.Get("date_to"),
		Page:       page,
		Limit:      limit,
		SortBy:     q.Get("sort_by"),
		SortOrder:  q.Get("sort_order"),
	}
	// Review 13.06 (audit CRITICAL): scope to the caller's tenant (superadmin → all).
	filter.TenantID = s.incidentTenantScope(r)

	result, err := s.socSvc.ListIncidentsAdvanced(filter)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}

	// Enrich with SLA status
	type incidentWithSLA struct {
		domsoc.Incident
		SLA *appsoc.SLAStatus `json:"sla,omitempty"`
	}
	enriched := make([]incidentWithSLA, len(result.Incidents))
	for i, inc := range result.Incidents {
		enriched[i] = incidentWithSLA{Incident: inc, SLA: appsoc.CalculateSLA(&inc)}
	}

	writeJSON(w, http.StatusOK, map[string]any{
		"incidents":   enriched,
		"total":       result.Total,
		"page":        result.Page,
		"limit":       result.Limit,
		"total_pages": result.TotalPages,
	})
}

// handleIncidentsBulk performs batch operations on incidents.
// POST /api/soc/incidents/bulk
func (s *Server) handleIncidentsBulk(w http.ResponseWriter, r *http.Request) {
	limitBody(w, r)
	var action appsoc.BulkAction
	if err := json.NewDecoder(r.Body).Decode(&action); err != nil {
		writeError(w, http.StatusBadRequest, "invalid request body")
		return
	}
	if len(action.IncidentIDs) == 0 {
		writeError(w, http.StatusBadRequest, "incident_ids required")
		return
	}
	if action.Action == "" {
		writeError(w, http.StatusBadRequest, "action required (assign, status, close)")
		return
	}

	// Get actor from JWT claims
	if claims := auth.GetClaims(r.Context()); claims != nil {
		action.Actor = claims.Sub
	}

	// Review 13.06 (audit CRITICAL): the bulk path mutated incidents by raw ID
	// with NO tenant check (cross-tenant IDOR write). Keep only the IDs this
	// caller is authorized to touch (getSecureIncident enforces tenant/superadmin).
	allowed := make([]string, 0, len(action.IncidentIDs))
	for _, id := range action.IncidentIDs {
		if _, err := s.getSecureIncident(r, id, false); err == nil {
			allowed = append(allowed, id)
		}
	}
	if len(allowed) == 0 {
		writeError(w, http.StatusNotFound, "no accessible incidents in request")
		return
	}
	action.IncidentIDs = allowed

	result, err := s.socSvc.BulkUpdateIncidents(action)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}

	writeJSON(w, http.StatusOK, result)
}

// handleIncidentsExport exports incidents as CSV or JSON.
// GET /api/soc/incidents/export?format=csv&status=OPEN&severity=HIGH
func (s *Server) handleIncidentsExport(w http.ResponseWriter, r *http.Request) {
	q := r.URL.Query()
	format := q.Get("format")
	if format == "" {
		format = "csv"
	}

	filter := appsoc.IncidentFilter{
		Status:   q.Get("status"),
		Severity: q.Get("severity"),
		Limit:    10000, // export all matching
		// Review 13.06 (audit CRITICAL): scope export to the caller's tenant.
		TenantID: s.incidentTenantScope(r),
	}

	switch format {
	case "csv":
		data, err := s.socSvc.ExportIncidentsCSV(filter)
		if err != nil {
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
		w.Header().Set("Content-Type", "text/csv")
		w.Header().Set("Content-Disposition", "attachment; filename=incidents.csv")
		w.WriteHeader(http.StatusOK)
		w.Write(data)
	case "json":
		result, err := s.socSvc.ListIncidentsAdvanced(filter)
		if err != nil {
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
		w.Header().Set("Content-Disposition", "attachment; filename=incidents.json")
		writeJSON(w, http.StatusOK, result)
	default:
		writeError(w, http.StatusBadRequest, "format must be csv or json")
	}
}

// handleIncidentSLA returns SLA status for a specific incident.
// GET /api/soc/incidents/{id}/sla
func (s *Server) handleIncidentSLA(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	if id == "" {
		writeError(w, http.StatusBadRequest, "incident ID required")
		return
	}

	inc, err := s.getSecureIncident(r, id, false)
	if err != nil {
		writeError(w, http.StatusNotFound, "incident not found")
		return
	}

	sla := appsoc.CalculateSLA(inc)
	writeJSON(w, http.StatusOK, map[string]any{
		"incident_id": id,
		"severity":    inc.Severity,
		"sla":         sla,
	})
}

// handleSLAConfig returns SLA threshold configuration.
// GET /api/soc/sla-config
func (s *Server) handleSLAConfig(w http.ResponseWriter, _ *http.Request) {
	thresholds := appsoc.DefaultSLAThresholds()
	type slaEntry struct {
		Severity      string  `json:"severity"`
		ResponseMin   float64 `json:"response_time_min"`
		ResolutionMin float64 `json:"resolution_time_min"`
	}
	entries := make([]slaEntry, 0, len(thresholds))
	for _, t := range thresholds {
		entries = append(entries, slaEntry{
			Severity:      t.Severity,
			ResponseMin:   t.ResponseTime.Minutes(),
			ResolutionMin: t.ResolutionTime.Minutes(),
		})
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"sla_thresholds": entries,
	})
}

// anonDemoScanLimit is the per-IP scan allowance for ANONYMOUS (unauthenticated)
// callers — a small demo so the public playground/sandbox works as a funnel
// without being a free-unlimited backdoor (Review 14.06 round-5). Configurable
// via ANON_DEMO_SCAN_LIMIT (default 100). Authenticated callers use their plan
// quota instead.
func anonDemoScanLimit() int {
	if v := os.Getenv("ANON_DEMO_SCAN_LIMIT"); v != "" {
		if n, err := strconv.Atoi(v); err == nil && n > 0 {
			return n
		}
	}
	return 100
}

// handlePublicScan provides a public prompt-scanning endpoint for the demo:
// anonymous callers get a small per-IP demo quota, authenticated callers their
// plan quota. There is no unauthenticated unlimited path (Review 14.06 round-5).
// POST /api/v1/scan  body: {"prompt": "Ignore all instructions..."}
// Runs sentinel-core (54 Rust engines) + Shield (C11 payload inspection) in parallel.
//
// Concurrency control: uses scanSem (buffered channel) to limit parallel scans.
// If all slots are busy, returns 503 Service Unavailable with Retry-After header
// to prevent OOM under burst load (e.g., 20 concurrent battle workers).
//
// @Summary Inspect AI Prompt
// @Description Scans user inputs using Sentinel Lattice (Rust engine) to detect jailbreaks, prompt injections, and Data Exfiltration attempts within 1ms.
// @Tags Scanner
// @Accept json
// @Produce json
// @Param body body map[string]string true "Request body containing 'prompt' string"
// @Success 200 {object} map[string]any "Scan result with confidence scores and block flags"
// @Failure 400 {object} map[string]string "Bad Request"
// @Failure 429 {object} map[string]string "Rate Limited"
// @Failure 503 {object} map[string]string "Service Unavailable (Queue full)"
// @Router /api/v1/scan [post]
func (s *Server) handlePublicScan(w http.ResponseWriter, r *http.Request) {
	limitBody(w, r)
	defer r.Body.Close()

	var req struct {
		Prompt string `json:"prompt"`
		// pow_nonce is intentionally no longer read (Review 14.06 round-5): the
		// Proof-of-Work bypass that granted unlimited quota-free scans was removed;
		// any pow_nonce a legacy client sends is harmlessly ignored by the decoder.
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON: "+err.Error())
		return
	}

	// Validate input
	if req.Prompt == "" {
		writeError(w, http.StatusBadRequest, "prompt is required")
		return
	}
	if len(req.Prompt) > 2000 {
		writeError(w, http.StatusBadRequest, "prompt too long (max 2000 chars)")
		return
	}
	// Reject interior NUL bytes (Review 14.06 round-4): encoding/json decodes a
	// \u0000 escape into a real NUL, and on the native build C.CString → Rust
	// CStr::from_ptr truncates analysis at the first NUL, so "hello\x00<attack>"
	// would be scanned as only "hello" — a trivial detection bypass. A NUL has no
	// place in a text prompt; reject it outright.
	if strings.IndexByte(req.Prompt, 0) >= 0 {
		writeError(w, http.StatusBadRequest, "prompt contains NUL byte")
		return
	}

	// P0 fail-CLOSED (Review 14.06): if no real detection engine is wired, the
	// stub reports every prompt clean (silent allow-all). Refuse to serve a
	// verdict — return 503 + blocked:true — unless an operator has explicitly
	// opted into stub mode (SENTINEL_ALLOW_STUB=1, dev only).
	if !s.scanEngineReady() && !stubScanAllowed() {
		w.Header().Set("Retry-After", "30")
		writeJSON(w, http.StatusServiceUnavailable, map[string]any{
			"blocked":     true,
			"detected":    true,
			"severity":    "HIGH",
			"threat_type": "engine_unavailable",
			"confidence":  1.0,
			"indicators":  []string{"gateway/detection_engine_unavailable"},
			"error":       "detection engine unavailable — failing closed",
			"engine_mode": "stub",
		})
		return
	}

	// Usage quota — ALWAYS enforced; there is NO Proof-of-Work / unlimited bypass
	// (Review 14.06 round-5, owner-decided). The old PoW path granted unlimited
	// quota-free scans to anyone who solved a trivial 16-bit hash — a revenue leak
	// and CPU-abuse vector. Authenticated callers get their plan quota; anonymous
	// callers get a small per-IP DEMO allowance so the public playground/sandbox
	// stays usable as a funnel without being a free-unlimited backdoor (sign up
	// free for the real quota). Both are metered per period; nobody is unmetered.
	if s.usageTracker != nil {
		userID, legacyEmail := "", ""
		planLimit := anonDemoScanLimit() // anonymous: small per-IP demo cap
		if claims := auth.GetClaims(r.Context()); claims != nil {
			// Authenticated requests require current owner and plan authority.
			// A missing/failed tenant lookup must never turn into a demo grant.
			if s.tenantStore == nil || s.userStore == nil {
				writeError(w, http.StatusServiceUnavailable, "scan plan temporarily unavailable")
				return
			}
			if claims.Sub == "" || claims.TenantID == "" {
				writeError(w, http.StatusForbidden, "scan tenant required")
				return
			}
			owner, err := s.userStore.GetByID(claims.Sub)
			if errors.Is(err, auth.ErrUserNotFound) {
				owner, err = s.userStore.GetByEmail(claims.Sub)
			}
			if err != nil {
				if errors.Is(err, auth.ErrStoreUnavailable) {
					writeError(w, http.StatusServiceUnavailable, "scan owner temporarily unavailable")
				} else {
					writeError(w, http.StatusForbidden, "scan owner unavailable")
				}
				return
			}
			platformAdmin := owner.Role == "superadmin" && claims.Role == "superadmin"
			if !owner.Active || (!platformAdmin && owner.TenantID != claims.TenantID) {
				writeError(w, http.StatusForbidden, "scan tenant access denied")
				return
			}
			tenant, err := s.tenantStore.GetTenant(claims.TenantID)
			if err != nil {
				if errors.Is(err, auth.ErrTenantNotFound) {
					writeError(w, http.StatusForbidden, "scan tenant unavailable")
				} else {
					writeError(w, http.StatusServiceUnavailable, "scan plan temporarily unavailable")
				}
				return
			}
			if !tenant.Active {
				writeError(w, http.StatusForbidden, "scan tenant disabled")
				return
			}
			if _, known := auth.DefaultPlans[tenant.PlanID]; !known {
				writeError(w, http.StatusServiceUnavailable, "scan plan temporarily unavailable")
				return
			}
			planLimit = tenant.ScanLimit()
			if planLimit < -1 {
				writeError(w, http.StatusServiceUnavailable, "scan plan temporarily unavailable")
				return
			}
			if planLimit == 0 {
				writeError(w, http.StatusForbidden, "scanning unavailable on current plan")
				return
			}
			userID, legacyEmail = owner.ID, owner.Email

		}
		// Key on the real client IP. clientIP returns the TCP peer (never the
		// spoofable X-Forwarded-For) unless the peer is a configured trusted proxy
		// (SOC_TRUSTED_PROXIES) — so behind nginx the per-IP demo cap is per real
		// client, not one global bucket, while a direct client still can't spoof it.
		ip := clientIP(r)
		var remaining int
		var err error
		if userID != "" {
			remaining, err = s.usageTracker.RecordScanForOwner(userID, legacyEmail, ip, planLimit)
		} else {
			remaining, err = s.usageTracker.RecordScanWithLimit("", ip, planLimit)
		}
		if err != nil {
			w.Header().Set("X-RateLimit-Remaining", "0")
			if errors.Is(err, auth.ErrQuotaExceeded) {
				writeError(w, http.StatusTooManyRequests, "scan quota exceeded — sign up free or upgrade at spectorn.ai/pricing")
			} else {
				writeError(w, http.StatusServiceUnavailable, "scan quota temporarily unavailable")
			}
			return
		}
		if remaining >= 0 {
			w.Header().Set("X-RateLimit-Remaining", strconv.Itoa(remaining))
		}
	} else {
		writeError(w, http.StatusServiceUnavailable, "scan quota temporarily unavailable")
		return
	}

	// ── Scan cache: return cached result for identical prompts ──
	cacheKey := promptHash(req.Prompt)
	s.scanCacheMu.RLock()
	if cached, ok := s.scanCache[cacheKey]; ok && time.Now().Before(cached.expiry) {
		s.scanCacheMu.RUnlock()
		resp := make(map[string]any, len(cached.response)+1)
		for k, v := range cached.response {
			resp[k] = v
		}
		resp["cached"] = true
		slog.Debug("scan cache hit", "key", cacheKey[:8])
		// A cache hit must still feed the tenant SOC (Review 14.06 round-2:
		// cached blocked verdicts previously bypassed the gateway→SOC seam).
		// Ingest dedup prevents flooding on repeated identical prompts.
		if blockedAny, _ := resp["blocked"].(bool); blockedAny {
			if claims := auth.GetClaims(r.Context()); claims != nil && claims.TenantID != "" {
				tt, _ := resp["threat_type"].(string)
				conf, _ := resp["confidence"].(float64)
				inds, _ := resp["indicators"].([]string)
				s.emitScanSOCEvent(claims.TenantID, tt, conf, req.Prompt, inds)
			}
		}
		writeJSON(w, http.StatusOK, resp)
		return
	}
	s.scanCacheMu.RUnlock()

	// ── Concurrency limiter: queue up to 5s before 503 ──
	select {
	case s.scanSem <- struct{}{}:
		defer func() { <-s.scanSem }()
	case <-time.After(5 * time.Second):
		// Waited 5s, still no slot → 503
		w.Header().Set("Retry-After", "3")
		slog.Warn("scan backpressure: queue timeout", "capacity", cap(s.scanSem))
		writeError(w, http.StatusServiceUnavailable, "scan engine busy — retry in 3 seconds")
		return
	case <-r.Context().Done():
		return
	}

	// ── Scan timeout: 30s hard limit ──
	scanCtx, cancel := context.WithTimeout(r.Context(), 30*time.Second)
	defer cancel()

	// ── Parallel scan: sentinel-core + shield + ML classifier run concurrently ──
	// Latency = max(core, shield, ml) instead of core + shield + ml
	coreEngine := s.getEngine("sentinel-core")
	var shieldEng engines.Shield
	if s.shieldEngine != nil {
		shieldEng = s.shieldEngine
	} else {
		shieldEng = engines.NewStubShield()
	}

	var (
		coreResult   *engines.ScanResult
		coreErr      error
		shieldResult *engines.ScanResult
		shieldErr    error
		mlResult     *onnx.ClassificationResult
		mlErr        error
		wg           sync.WaitGroup
	)

	wg.Add(3)

	// Goroutine 1: sentinel-core (54 Rust engines) — the heavy path
	go func() {
		defer wg.Done()
		coreResult, coreErr = coreEngine.ScanPrompt(scanCtx, req.Prompt)
	}()

	// Goroutine 2: shield (C11 payload inspection) — lighter path
	go func() {
		defer wg.Done()
		shieldResult, shieldErr = shieldEng.InspectTraffic(scanCtx, []byte(req.Prompt), nil)
	}()

	// Goroutine 3: Safety Classifier v2 (16-class ML threat detection)
	go func() {
		defer wg.Done()
		if s.safetyClassifier != nil {
			mlResult, mlErr = s.safetyClassifier.Classify(scanCtx, req.Prompt)
		}
	}()

	wg.Wait()

	// Build response — merge both engines
	response := map[string]any{}

	if coreErr != nil {
		writeError(w, http.StatusInternalServerError, "scan failed: "+coreErr.Error())
		return
	}

	// Merge indicators from both engines
	allIndicators := coreResult.Indicators
	blocked := coreResult.ThreatFound
	maxConfidence := coreResult.Confidence
	threatType := coreResult.ThreatType

	coreBlocked := coreResult.ThreatFound
	shieldBlocked := false
	mlBlocked := false

	// Add Shield results if available
	shieldStatus := "offline"
	if shieldErr == nil && shieldResult != nil {
		shieldStatus = "active"
		if shieldResult.ThreatFound {
			blocked = true
			shieldBlocked = true
			if shieldResult.Confidence > maxConfidence {
				maxConfidence = shieldResult.Confidence
				threatType = shieldResult.ThreatType
			}
			allIndicators = append(allIndicators, "shield/"+shieldResult.Details)
		}
	}

	// Add Safety Classifier v2 results if available
	mlStatus := "offline"
	if mlErr == nil && mlResult != nil {
		mlStatus = "active"
		response["ml_category"] = mlResult.Category
		response["ml_confidence"] = mlResult.Confidence
		response["ml_severity"] = mlResult.Severity
		response["ml_probabilities"] = mlResult.Probabilities
		if mlResult.IsThreat {
			blocked = true
			mlBlocked = true
			if mlResult.Confidence > maxConfidence {
				maxConfidence = mlResult.Confidence
				threatType = string(mlResult.Category)
			}
			allIndicators = append(allIndicators, "ml/"+string(mlResult.Category))
		}
	}

	// ── LAYER 3: gated LLM-judge escalation (default-OFF no-op) ──
	// When an escalation judge is wired AND the engine risk lands in the
	// operator's ambiguity band, consult the (BYO-key, on-prem) judge and merge
	// per the conservative policy. When OFF or out-of-band this is a pure no-op
	// and `blocked`/`maxConfidence` are unchanged. Honest-degrade: a judge error
	// keeps the engine verdict (never fabricated).
	jd := s.maybeEscalateToJudge(scanCtx, req.Prompt, blocked, maxConfidence, threatType, allIndicators)
	if jd.Consulted {
		if jd.Blocked != blocked {
			// The judge changed the decision (escalate-to-block, or an
			// operator-opted high-confidence downgrade). Reflect it in indicators.
			allIndicators = append(allIndicators, "judge/"+jd.Action)
		}
		blocked = jd.Blocked
		judgeInfo := map[string]any{
			"consulted": true,
			"action":    jd.Action,
			"vendor":    jd.Vendor,
		}
		if jd.Err != nil {
			// Honest-degrade: tell the caller the judge was attempted but errored,
			// and that the engine verdict was kept. No prompt/key in the message.
			judgeInfo["error"] = "judge_unavailable"
			judgeInfo["degraded"] = true
		} else {
			judgeInfo["confidence"] = jd.Confidence
			judgeInfo["reason"] = jd.Reason
		}
		response["judge"] = judgeInfo
	}

	severity := "NONE"
	if blocked {
		severity = "HIGH"
	}

	response["blocked"] = blocked
	response["threat_type"] = threatType
	response["severity"] = severity
	response["confidence"] = maxConfidence
	response["details"] = coreResult.Details
	response["indicators"] = allIndicators
	response["engine"] = "sentinel-core" // legacy field
	response["engines"] = map[string]bool{
		"core":   coreBlocked,
		"shield": shieldBlocked,
		"ml":     mlBlocked,
	}
	response["latency_ms"] = float64(coreResult.Duration.Microseconds()) / 1000.0
	response["shield_status"] = shieldStatus
	response["ml_status"] = mlStatus

	// ── Gateway IS the sensor (Review 14.06 R3): a blocked verdict from an
	// AUTHENTICATED tenant auto-populates that tenant's SOC (async; raw prompt
	// redacted). Anonymous demo scans are skipped so they never pollute a real
	// tenant's SOC. This replaces the demo-simulator fiction with real traffic.
	if blocked {
		if claims := auth.GetClaims(r.Context()); claims != nil && claims.TenantID != "" {
			s.emitScanSOCEvent(claims.TenantID, threatType, maxConfidence, req.Prompt, allIndicators)
		}
	}

	// ── Data-capture flywheel: persist a training row for this scan (gated +
	// async + best-effort). Captures EVERY scan from an authenticated tenant
	// (blocked AND allowed) — the learned combiner needs both classes. Metadata
	// only: the per-engine confidence features + verdict + a SHA-256 prompt hash,
	// never the raw prompt. No-op when ORCHESTRATOR_CAPTURE_ENABLED!=1 (default)
	// or unwired, so the scan path is byte-identical with the feature off. The
	// supervised label is attached later when the related incident is dispositioned.
	if claims := auth.GetClaims(r.Context()); claims != nil && claims.TenantID != "" {
		var shieldConf, mlConf float64
		if shieldErr == nil && shieldResult != nil {
			shieldConf = shieldResult.Confidence
		}
		if mlErr == nil && mlResult != nil {
			mlConf = mlResult.Confidence
		}
		s.captureOrchestratorSample(captureInputs{
			tenantID:   claims.TenantID,
			promptHash: promptHash(req.Prompt),
			risk:       maxConfidence,
			blocked:    blocked,
			threatType: threatType,
			indicators: allIndicators,
			// Dense per-engine vector from sentinel-core's fan-out (nil when the stub
			// bridge is in use or an older sentinel binary omits it → aggregate
			// fallback). This is the one real win: REAL per-engine training features.
			engineVector:     coreResult.EngineVector,
			coreConfidence:   coreResult.Confidence,
			shieldConfidence: shieldConf,
			mlConfidence:     mlConf,
			coreBlocked:      coreBlocked,
			shieldBlocked:    shieldBlocked,
			mlBlocked:        mlBlocked,
			modelVersion:     coreEngine.Version(),
		})
	}

	// ── Store in cache (5 min TTL, evict oldest if >500 entries) ──
	s.scanCacheMu.Lock()
	if len(s.scanCache) >= 500 {
		// Simple eviction: remove any expired entries
		now := time.Now()
		for k, v := range s.scanCache {
			if now.After(v.expiry) {
				delete(s.scanCache, k)
			}
		}
		// If still full, clear oldest 25%
		if len(s.scanCache) >= 500 {
			i := 0
			for k := range s.scanCache {
				delete(s.scanCache, k)
				i++
				if i >= 125 {
					break
				}
			}
		}
	}
	s.scanCache[cacheKey] = &cachedScan{
		response: response,
		expiry:   time.Now().Add(5 * time.Minute),
	}
	s.scanCacheMu.Unlock()

	writeJSON(w, http.StatusOK, response)
}

// handleUsage returns current scan usage and quota for the caller.
// GET /api/v1/usage
func (s *Server) handleUsage(w http.ResponseWriter, r *http.Request) {
	if s.usageTracker == nil {
		writeError(w, http.StatusServiceUnavailable, "scan quota temporarily unavailable")
		return
	}

	ip := clientIP(r)
	var info *auth.UsageInfo
	var err error
	if claims := auth.GetClaims(r.Context()); claims != nil {
		if s.userStore == nil {
			writeError(w, http.StatusServiceUnavailable, "scan owner temporarily unavailable")
			return
		}
		owner, lookupErr := s.userStore.GetByID(claims.Sub)
		if errors.Is(lookupErr, auth.ErrUserNotFound) {
			owner, lookupErr = s.userStore.GetByEmail(claims.Sub)
		}
		if lookupErr != nil {
			if errors.Is(lookupErr, auth.ErrStoreUnavailable) {
				writeError(w, http.StatusServiceUnavailable, "scan owner temporarily unavailable")
			} else {
				writeError(w, http.StatusForbidden, "scan owner unavailable")
			}
			return
		}
		platformAdmin := owner.Role == "superadmin" && claims.Role == "superadmin"
		if !owner.Active || (!platformAdmin && owner.TenantID != claims.TenantID) {
			writeError(w, http.StatusForbidden, "scan tenant access denied")
			return
		}
		info, err = s.usageTracker.GetUsageForOwnerChecked(owner.ID, owner.Email, ip)
	} else {
		info, err = s.usageTracker.GetUsageChecked("", ip)
	}

	if err != nil {
		writeError(w, http.StatusServiceUnavailable, "scan quota temporarily unavailable")
		return
	}
	writeJSON(w, http.StatusOK, info)
}

// handleWaitlist captures registration interest when signups are closed.
// POST /api/waitlist  body: {"email": "user@corp.com", "company": "CorpX", "use_case": "LLM protection"}
// Public endpoint, no auth required. Rate-limited globally.
func (s *Server) handleWaitlist(w http.ResponseWriter, r *http.Request) {
	limitBody(w, r)
	defer r.Body.Close()

	var req struct {
		Email   string `json:"email"`
		Company string `json:"company"`
		UseCase string `json:"use_case"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON")
		return
	}

	// Validate email
	if req.Email == "" || len(req.Email) < 5 || len(req.Email) > 254 {
		writeError(w, http.StatusBadRequest, "valid email is required")
		return
	}
	// Basic email format check
	hasAt := false
	for _, c := range req.Email {
		if c == '@' {
			hasAt = true
			break
		}
	}
	if !hasAt {
		writeError(w, http.StatusBadRequest, "valid email is required")
		return
	}

	// Sanitize
	if len(req.Company) > 200 {
		req.Company = req.Company[:200]
	}
	if len(req.UseCase) > 1000 {
		req.UseCase = req.UseCase[:1000]
	}
	// SEC: Sanitize CRLF to prevent log injection in tamper-evident decision logs
	req.Company = strings.ReplaceAll(strings.ReplaceAll(req.Company, "\n", " "), "\r", "")
	req.UseCase = strings.ReplaceAll(strings.ReplaceAll(req.UseCase, "\n", " "), "\r", "")

	// T4-6 FIX: mask email to domain + mask IP for the operational log. Company
	// (free-text, may carry PII) is NOT logged — it lives only in the deletable
	// waitlist store now (round-6 B-2: no cleartext PII in application logs).
	redactedEmail := "***@" + req.Email[strings.LastIndex(req.Email, "@")+1:]
	maskedIP := r.RemoteAddr
	if idx := strings.LastIndex(maskedIP, "."); idx > 0 {
		maskedIP = maskedIP[:idx] + ".0"
	}
	slog.Info("waitlist submission",
		"email_domain", redactedEmail,
		"ip_masked", maskedIP,
	)

	// Persist to the deletable waitlist store. A persist failure is logged but does
	// NOT fail the request — the audit chain already recorded the signup hash and we
	// don't punish the visitor for a transient DB issue.
	if s.socSvc != nil {
		if err := s.socSvc.AddWaitlistEntry(req.Email, req.Company, req.UseCase); err != nil {
			slog.Error("waitlist persist failed (lead not stored)", "error", err)
		}
	}

	writeJSON(w, http.StatusOK, map[string]any{
		"status":  "ok",
		"message": "You've been added to the waitlist. We'll notify you when registration opens.",
	})
}
