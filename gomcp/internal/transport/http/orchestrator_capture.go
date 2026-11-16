package httpserver

import (
	"encoding/json"
	"log/slog"
	"net/http"
	"os"
	"strconv"
	"time"

	"github.com/syntrex/gomcp/internal/domain/orchestrator"
	domsoc "github.com/syntrex/gomcp/internal/domain/soc"
	"github.com/syntrex/gomcp/internal/infrastructure/auth"
)

// ── DATA-CAPTURE FLYWHEEL (gomcp) ───────────────────────────────────────────
//
// This file is the gateway-side plumbing that makes the "self-improving from
// customer traffic" claim REAL: it persists, per scan, a compact TRAINING ROW
// (per-engine confidence features + verdict + an attachable analyst label) and
// exports the labeled rows as JSONL for the sentinel retraining harness.
//
// HONEST SCOPE: this does NOT improve detection today. It is plumbing whose
// payoff is FUTURE — it only yields training value once real traffic flows AND
// analysts disposition the resulting incidents. See the orchestrator domain
// package doc. Capture is DEFAULT-OFF and, when on, best-effort + async, so a
// gateway with capture disabled is byte-identical on the scan path.

// orchestratorCaptureEnabled gates the capture write. Default OFF. An operator
// opts in with ORCHESTRATOR_CAPTURE_ENABLED=1. Read per-call (cheap) so the gate
// can be flipped without restructuring; the scan path already does similar env
// reads (SENTINEL_ALLOW_STUB).
func orchestratorCaptureEnabled() bool {
	return os.Getenv("ORCHESTRATOR_CAPTURE_ENABLED") == "1"
}

// SetOrchestratorRepo wires the training-sample store. nil → capture + export are
// no-ops (the feature is unwired). Mirrors the other Set* injectors.
func (s *Server) SetOrchestratorRepo(repo orchestrator.Repository) {
	s.orchestratorRepo = repo
}

// captureInputs carries the verdict signal handlePublicScan already computed, so
// the capture seam stays a pure projection (testable) with no re-derivation.
type captureInputs struct {
	tenantID   string
	promptHash string
	risk       float64
	blocked    bool
	threatType string
	indicators []string
	// engineVector is the DENSE per-engine confidence vector from sentinel-core
	// (len == orchestrator.DenseVectorLen). Empty/nil when the native bridge is not
	// in use or an older sentinel binary did not emit it — buildSample then falls
	// back to the aggregate-only feature row.
	engineVector     []float64
	coreConfidence   float64
	shieldConfidence float64
	mlConfidence     float64
	coreBlocked      bool
	shieldBlocked    bool
	mlBlocked        bool
	modelVersion     string
}

// buildSample projects the scan verdict into a training Sample. Pure + sync so it
// is unit-testable. It always captures the aggregate scalar features + the SPARSE
// per-engine confidences parsed out of the indicators.
//
// DENSE VECTOR: when the sentinel-core bridge supplied a real dense per-engine
// vector (in.engineVector, len == DenseVectorLen), it is stored as the row's
// EngineVector with VectorComplete=true and the dense-v1 schema — the real
// per-engine feature the learned combiner/router wants. When it is absent (stub
// bridge, shield-only, or an older sentinel binary), the row falls back to the
// aggregate-only layout (VectorComplete=false, agg-v1) exactly as before.
func buildSample(in captureInputs) orchestrator.Sample {
	scores := orchestrator.ParseEngineScores(in.indicators)

	// Default: aggregate-only fallback (unchanged behavior).
	engineVector := []float64(nil)
	vectorComplete := false
	vectorSchema := orchestrator.VectorSchema
	if len(in.engineVector) == orchestrator.DenseVectorLen {
		engineVector = in.engineVector
		vectorComplete = true
		vectorSchema = orchestrator.DenseVectorSchema
	}

	return orchestrator.Sample{
		ID:           orchestrator.GenID("orch"),
		TenantID:     in.tenantID,
		Timestamp:    time.Now(),
		PromptHash:   in.promptHash, // SHA-256 of prompt — never the raw prompt
		EngineVector: engineVector,  // dense per-engine vector when the bridge emits one
		EngineScores: scores,        // sparse: only engines that fired
		Aggregate: orchestrator.AggregateFeatures{
			Risk:             in.risk,
			CoreConfidence:   in.coreConfidence,
			ShieldConfidence: in.shieldConfidence,
			MLConfidence:     in.mlConfidence,
			// EnginesTriggered = distinct engines that fired with a recoverable
			// confidence, derived from the same indicator source as EngineScores
			// (the bridge's engines_triggered count is not exposed as an int here).
			EnginesTriggered: len(scores),
			CoreBlocked:      in.coreBlocked,
			ShieldBlocked:    in.shieldBlocked,
			MLBlocked:        in.mlBlocked,
		},
		VectorComplete: vectorComplete,
		VectorSchema:   vectorSchema,
		Blocked:        in.blocked,
		Risk:           in.risk,
		ThreatType:     in.threatType,
		ModelVersion:   in.modelVersion,
		Label:          orchestrator.LabelUnlabeled,
	}
}

// captureOrchestratorSample persists a training row for one scan. Best-effort and
// async: it NEVER blocks or fails the scan. A no-op when the feature is disabled,
// unwired, or the request is anonymous (no tenant) — scan-derived training rows
// must never be attributed to no tenant (mirrors emitScanSOCEvent).
func (s *Server) captureOrchestratorSample(in captureInputs) {
	if !orchestratorCaptureEnabled() || s.orchestratorRepo == nil || in.tenantID == "" {
		return
	}
	sample := buildSample(in)
	go func() {
		defer func() {
			if rec := recover(); rec != nil {
				slog.Error("orchestrator capture panicked", "tenant", in.tenantID, "panic", rec)
			}
		}()
		if err := s.orchestratorRepo.Insert(sample); err != nil {
			slog.Warn("orchestrator capture: insert failed", "tenant", in.tenantID, "error", err)
		}
	}()
}

// orchestratorLabelWindow is how far BEFORE an incident's earliest event time the
// label-attach join reaches, to cover the small lag between a scan being captured
// and the SOC event/incident being correlated. Generous but bounded.
const orchestratorLabelWindow = 10 * time.Minute

// attachOrchestratorLabel writes the supervised label back onto the scan samples
// related to a dispositioned incident.
//
// JOIN GRANULARITY (honest): the gateway scan path is the single producer of both
// the SOC event AND the orchestrator sample, but the SOC event persists only an
// 8-hex prefix of the prompt hash (in its description) — not the full hash — so a
// sample cannot be joined to an incident by exact prompt hash. The available join
// is therefore TENANT + TIME WINDOW: label every still-unlabeled sample for the
// incident's tenant whose timestamp falls within the incident's event window
// (widened by orchestratorLabelWindow). This is coarse weak-supervision — it can
// mislabel concurrent unrelated scans in the same window — which the retraining
// harness should treat as noisy labels (the export weight already flags coarse
// features). A precise per-prompt join becomes possible if the SOC event is ever
// extended to carry the full prompt hash.
//
// Best-effort: errors are logged, never surfaced to the disposition caller.
func (s *Server) attachOrchestratorLabel(inc *domsoc.Incident, status domsoc.IncidentStatus) {
	if s.orchestratorRepo == nil || inc == nil || inc.TenantID == "" {
		return
	}
	var label orchestrator.Label
	switch status {
	case domsoc.StatusFalsePositive:
		label = orchestrator.LabelBenign // a blocked scan that was actually safe
	case domsoc.StatusResolved:
		label = orchestrator.LabelMalicious // a confirmed real threat
	default:
		return // only terminal dispositions produce a supervised label
	}

	// Window: [earliest event time - slack, now]. Prefer FirstEventAt (the MTTD
	// anchor); fall back to CreatedAt when it is unset (pre-migration incidents).
	from := inc.FirstEventAt
	if from.IsZero() {
		from = inc.CreatedAt
	}
	from = from.Add(-orchestratorLabelWindow)
	to := time.Now()

	tenantID := inc.TenantID
	source := "incident:" + string(status)
	go func() {
		defer func() {
			if rec := recover(); rec != nil {
				slog.Error("orchestrator label-attach panicked", "tenant", tenantID, "panic", rec)
			}
		}()
		n, err := s.orchestratorRepo.AttachLabel(tenantID, from, to, label, source)
		if err != nil {
			slog.Warn("orchestrator label-attach failed", "tenant", tenantID, "error", err)
			return
		}
		if n > 0 {
			slog.Info("orchestrator label-attach", "tenant", tenantID, "label", label, "rows", n, "source", source)
		}
	}()
}

// handleOrchestratorTrainingExport streams the tenant's LABELED training rows as
// JSONL ({vector, label, weight, ...}) for the sentinel retraining harness.
//
// GET /api/admin/orchestrator/training-export?limit=&include_unlabeled=
//
// AUTH: admin-gated at the route (RoleAdmin). TENANCY: strictly scoped to the
// caller's tenant — a platform superadmin may target another tenant via
// ?tenant_id=, but a non-superadmin's tenant is force-locked to their own claim
// (scope-lock, mirroring the SOC handlers' IDOR guards). A request with no tenant
// claim is refused.
func (s *Server) handleOrchestratorTrainingExport(w http.ResponseWriter, r *http.Request) {
	if s.orchestratorRepo == nil {
		writeError(w, http.StatusServiceUnavailable, "orchestrator capture not configured")
		return
	}

	claims := auth.GetClaims(r.Context())
	if claims == nil || claims.TenantID == "" {
		writeError(w, http.StatusForbidden, "tenant context required")
		return
	}

	// Scope-lock: default to the caller's own tenant. Only a superadmin may
	// override via ?tenant_id=; everyone else is pinned to their claim so the
	// export can never read another tenant's samples.
	tenantID := claims.TenantID
	if req := r.URL.Query().Get("tenant_id"); req != "" && req != tenantID {
		if Role(claims.Role) != RoleSuperadmin {
			writeError(w, http.StatusForbidden, "cross-tenant export requires platform admin")
			return
		}
		tenantID = req
	}

	limit := 10000
	if v := r.URL.Query().Get("limit"); v != "" {
		if n, err := strconv.Atoi(v); err == nil && n > 0 {
			limit = n
		}
	}
	// Default export is labeled-only (the training corpus). A platform admin may
	// include unlabeled rows for corpus inspection.
	onlyLabeled := true
	if r.URL.Query().Get("include_unlabeled") == "1" {
		if Role(claims.Role) != RoleSuperadmin {
			writeError(w, http.StatusForbidden, "include_unlabeled requires platform admin")
			return
		}
		onlyLabeled = false
	}

	samples, err := s.orchestratorRepo.ExportLabeled(tenantID, limit, onlyLabeled)
	if err != nil {
		slog.Warn("orchestrator export failed", "tenant", tenantID, "error", err)
		writeError(w, http.StatusInternalServerError, "export failed")
		return
	}

	// JSONL: one ExportRow per line. Content-Disposition makes it a downloadable
	// artifact for the offline retraining harness.
	w.Header().Set("Content-Type", "application/x-ndjson")
	w.Header().Set("Content-Disposition", `attachment; filename="orchestrator_training.jsonl"`)
	w.Header().Set("X-Vector-Schema", orchestrator.VectorSchema)
	w.WriteHeader(http.StatusOK)

	enc := json.NewEncoder(w)
	for i := range samples {
		row := samples[i].ToExportRow()
		if err := enc.Encode(row); err != nil {
			// Mid-stream encode error: log and stop; headers already sent.
			slog.Warn("orchestrator export: encode row failed", "tenant", tenantID, "error", err)
			return
		}
	}
}
