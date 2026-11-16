package httpserver

import (
	"encoding/json"
	"net/http"
	"strings"
	"time"

	"github.com/syntrex/gomcp/internal/application/resilience"
)

// ResilienceAPI holds references to the SARL engines for HTTP handlers.
type ResilienceAPI struct {
	healthMonitor *resilience.HealthMonitor
	healingEngine *resilience.HealingEngine
	preservation  *resilience.PreservationEngine
	behavioral    *resilience.BehavioralAnalyzer
	playbooks     *resilience.RecoveryPlaybookEngine
}

// NewResilienceAPI creates a new resilience API handler.
// Any engine can be nil — the handler will return 503 for that subsystem.
func NewResilienceAPI(
	hm *resilience.HealthMonitor,
	he *resilience.HealingEngine,
	pe *resilience.PreservationEngine,
	ba *resilience.BehavioralAnalyzer,
	pb *resilience.RecoveryPlaybookEngine,
) *ResilienceAPI {
	return &ResilienceAPI{
		healthMonitor: hm,
		healingEngine: he,
		preservation:  pe,
		behavioral:    ba,
		playbooks:     pb,
	}
}

// RegisterRoutes registers all resilience API endpoints on the given mux.
func (api *ResilienceAPI) RegisterRoutes(mux *http.ServeMux, rbac *RBACMiddleware) {
	// All dependencies own process-global state; only operators may access them.
	mux.HandleFunc("GET /api/v1/resilience/health",
		rbac.Require(RoleSuperadmin, api.handleHealth))
	mux.HandleFunc("GET /api/v1/resilience/metrics/{component}",
		rbac.Require(RoleSuperadmin, api.handleComponentMetrics))
	mux.HandleFunc("GET /api/v1/resilience/audit",
		rbac.Require(RoleSuperadmin, api.handleAudit))
	mux.HandleFunc("GET /api/v1/resilience/healing/{id}",
		rbac.Require(RoleSuperadmin, api.handleHealingStatus))

	// Process-global mutations share the same operator boundary.
	mux.HandleFunc("POST /api/v1/resilience/healing/initiate",
		rbac.Require(RoleSuperadmin, api.handleInitiateHealing))
	mux.HandleFunc("POST /api/v1/resilience/mode/activate",
		rbac.Require(RoleSuperadmin, api.handleActivateMode))
}

// GET /api/v1/resilience/health
func (api *ResilienceAPI) handleHealth(w http.ResponseWriter, r *http.Request) {
	if api.healthMonitor == nil {
		writeError(w, http.StatusServiceUnavailable, "health monitor not initialized")
		return
	}

	health := api.healthMonitor.GetHealth()

	// Add emergency mode info from preservation engine.
	response := map[string]any{
		"overall_status":        health.OverallStatus,
		"components":            health.Components,
		"quorum_valid":          health.QuorumValid,
		"last_check":            health.LastCheck,
		"anomalies_detected":    health.AnomaliesDetected,
		"active_emergency_mode": string(resilience.ModeNone),
	}

	if api.preservation != nil {
		response["active_emergency_mode"] = string(api.preservation.CurrentMode())
	}

	writeJSON(w, http.StatusOK, response)
}

// GET /api/v1/resilience/metrics/{component}
func (api *ResilienceAPI) handleComponentMetrics(w http.ResponseWriter, r *http.Request) {
	component := r.PathValue("component")
	if component == "" {
		writeError(w, http.StatusBadRequest, "missing component path parameter")
		return
	}

	if api.healthMonitor == nil {
		writeError(w, http.StatusServiceUnavailable, "health monitor not initialized")
		return
	}

	writeJSON(w, http.StatusOK, map[string]any{
		"component":  component,
		"time_range": "1h",
		"status":     "ok",
	})
}

// GET /api/v1/resilience/audit
func (api *ResilienceAPI) handleAudit(w http.ResponseWriter, r *http.Request) {
	var entries []any

	// Combine healing operations + preservation events.
	if api.healingEngine != nil {
		ops := api.healingEngine.RecentOperations(50)
		for _, op := range ops {
			entries = append(entries, map[string]any{
				"type":      "healing",
				"timestamp": op.StartedAt,
				"component": op.Component,
				"strategy":  op.StrategyID,
				"result":    op.Result,
				"error":     op.Error,
			})
		}
	}

	if api.preservation != nil {
		for _, evt := range api.preservation.History() {
			entries = append(entries, map[string]any{
				"type":      "preservation",
				"timestamp": evt.Timestamp,
				"mode":      evt.Mode,
				"action":    evt.Action,
				"success":   evt.Success,
				"error":     evt.Error,
			})
		}
	}

	if api.playbooks != nil {
		execs := api.playbooks.RecentExecutions(50)
		for _, exec := range execs {
			entries = append(entries, map[string]any{
				"type":      "playbook",
				"timestamp": exec.StartedAt,
				"playbook":  exec.PlaybookID,
				"component": exec.Component,
				"status":    exec.Status,
				"error":     exec.Error,
			})
		}
	}

	writeJSON(w, http.StatusOK, map[string]any{
		"entries": entries,
		"total":   len(entries),
	})
}

// GET /api/v1/resilience/healing/{id}
func (api *ResilienceAPI) handleHealingStatus(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	if id == "" {
		writeError(w, http.StatusBadRequest, "missing healing operation ID")
		return
	}

	if api.healingEngine != nil {
		op, ok := api.healingEngine.GetOperation(id)
		if ok {
			writeJSON(w, http.StatusOK, op)
			return
		}
	}

	if api.playbooks != nil {
		exec, ok := api.playbooks.GetExecution(id)
		if ok {
			writeJSON(w, http.StatusOK, exec)
			return
		}
	}

	writeError(w, http.StatusNotFound, "operation not found")
}

// POST /api/v1/resilience/healing/initiate
func (api *ResilienceAPI) handleInitiateHealing(w http.ResponseWriter, r *http.Request) {
	var req struct {
		Component string `json:"component"`
		Strategy  string `json:"strategy,omitempty"`
		Playbook  string `json:"playbook,omitempty"`
		Force     bool   `json:"force"`
	}

	if err := json.NewDecoder(http.MaxBytesReader(w, r.Body, 1<<20)).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid request body")
		return
	}

	if req.Component == "" {
		writeError(w, http.StatusBadRequest, "component is required")
		return
	}

	// Run playbook if specified.
	if req.Playbook != "" && api.playbooks != nil {
		execID, err := api.playbooks.Execute(r.Context(), req.Playbook, req.Component)
		if err != nil {
			writeJSON(w, http.StatusOK, map[string]any{
				"healing_id": execID,
				"status":     "FAILED",
				"error":      err.Error(),
			})
			return
		}
		writeJSON(w, http.StatusOK, map[string]any{
			"healing_id": execID,
			"status":     "COMPLETED",
		})
		return
	}

	writeJSON(w, http.StatusAccepted, map[string]any{
		"component": req.Component,
		"status":    "INITIATED",
		"message":   "healing request queued",
	})
}

// POST /api/v1/resilience/mode/activate
func (api *ResilienceAPI) handleActivateMode(w http.ResponseWriter, r *http.Request) {
	if api.preservation == nil {
		writeError(w, http.StatusServiceUnavailable, "preservation engine not initialized")
		return
	}

	var req struct {
		Mode     string `json:"mode"`
		Reason   string `json:"reason"`
		Duration string `json:"duration,omitempty"`
	}

	if err := json.NewDecoder(http.MaxBytesReader(w, r.Body, 1<<20)).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid request body")
		return
	}

	var mode resilience.EmergencyMode
	switch strings.ToUpper(req.Mode) {
	case "SAFE":
		mode = resilience.ModeSafe
	case "LOCKDOWN":
		mode = resilience.ModeLockdown
	case "APOPTOSIS":
		mode = resilience.ModeApoptosis
	case "NONE", "":
		if err := api.preservation.DeactivateMode("api"); err != nil {
			writeError(w, http.StatusConflict, err.Error())
			return
		}
		writeJSON(w, http.StatusOK, map[string]any{
			"mode_activated": "NONE",
			"activated_at":   time.Now(),
		})
		return
	default:
		writeError(w, http.StatusBadRequest, "invalid mode: "+req.Mode)
		return
	}

	if err := api.preservation.ActivateMode(mode, req.Reason, "api"); err != nil {
		writeError(w, http.StatusConflict, err.Error())
		return
	}

	activation := api.preservation.Activation()
	writeJSON(w, http.StatusOK, map[string]any{
		"mode_activated": string(mode),
		"activated_at":   activation.ActivatedAt,
		"auto_exit_at":   activation.AutoExitAt,
	})
}

// writeJSON and writeJSONError are defined in server.go (shared across package).
