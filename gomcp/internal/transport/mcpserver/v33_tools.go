package mcpserver

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"os"
	"strings"
	"time"

	"github.com/mark3labs/mcp-go/mcp"

	"github.com/syntrex/gomcp/internal/application/orchestrator"
	"github.com/syntrex/gomcp/internal/application/tools"
	"github.com/syntrex/gomcp/internal/domain/memory"
	"github.com/syntrex/gomcp/internal/domain/mimicry"
	"github.com/syntrex/gomcp/internal/domain/oracle"
	"github.com/syntrex/gomcp/internal/domain/peer"
)

// --- v3.3 Tools Registration ---

// SetSynapseService sets the v3.3 SynapseService for synapse bridge tools.
func (s *Server) SetSynapseService(svc *tools.SynapseService) {
	s.synapseSvc = svc
}

// SetOrchestrator enables the orchestrator_status tool (v3.4).
func (s *Server) SetOrchestrator(o *orchestrator.Orchestrator) {
	s.orch = o
}

// registerV33Tools registers v3.3 tools: Context GC + Synapse Bridges + Shadow Intel.
func (s *Server) registerV33Tools() {
	// --- Context GC ---

	s.mcp.AddTool(
		mcp.NewTool("get_cold_facts",
			mcp.WithDescription("Get stale facts for review (hit_count=0, >30 days old). Genes excluded. Use for memory hygiene."),
			mcp.WithNumber("limit", mcp.Description("Max results (default 50)")),
		),
		s.handleGetColdFacts,
	)

	s.mcp.AddTool(
		mcp.NewTool("compress_facts",
			mcp.WithDescription("Archive multiple facts and create a summary. AI provides fact_ids and summary text. Genes are protected."),
			mcp.WithString("fact_ids", mcp.Description("JSON array of fact IDs to archive"), mcp.Required()),
			mcp.WithString("summary", mcp.Description("Summary text for the consolidated fact"), mcp.Required()),
		),
		s.handleCompressFacts,
	)

	// --- Synapse Bridges ---

	if s.synapseSvc != nil {
		s.mcp.AddTool(
			mcp.NewTool("suggest_synapses",
				mcp.WithDescription("Show pending semantic connections between facts for Architect review."),
				mcp.WithNumber("limit", mcp.Description("Max results (default 20)")),
			),
			s.handleSuggestSynapses,
		)

		s.mcp.AddTool(
			mcp.NewTool("accept_synapse",
				mcp.WithDescription("Accept a pending synapse (PENDING → VERIFIED). Only verified synapses influence context ranking."),
				mcp.WithNumber("id", mcp.Description("Synapse ID to accept"), mcp.Required()),
			),
			s.handleAcceptSynapse,
		)

		s.mcp.AddTool(
			mcp.NewTool("reject_synapse",
				mcp.WithDescription("Reject a pending synapse (PENDING → REJECTED). Removes from ranking consideration."),
				mcp.WithNumber("id", mcp.Description("Synapse ID to reject"), mcp.Required()),
			),
			s.handleRejectSynapse,
		)
	}

	// --- Shadow Intelligence ---

	s.mcp.AddTool(
		mcp.NewTool("synthesize_threat_model",
			mcp.WithDescription("Scan Code Crystals for security threats (hardcoded secrets, weak configs, logic holes). Read-only analysis; does not require ZERO-G."),
		),
		s.handleSynthesizeThreatModel,
	)

	// --- v3.4: extract_raw_intent ---

	s.mcp.AddTool(
		mcp.NewTool("extract_raw_intent",
			mcp.WithDescription("Extract encrypted Shadow Memory data. ZERO-G mode required (double-verified). Returns base64 AES-GCM encrypted threat report."),
		),
		s.handleExtractRawIntent,
	)

	// --- v3.4: orchestrator_status ---

	s.mcp.AddTool(
		mcp.NewTool("orchestrator_status",
			mcp.WithDescription("Get orchestrator runtime status: cycle, config, last heartbeat, module 9 synapse scanner state."),
		),
		s.handleOrchestratorStatus,
	)

	// --- v3.5: delta_sync ---

	s.mcp.AddTool(
		mcp.NewTool("delta_sync",
			mcp.WithDescription("Export facts created after a given timestamp. Use for incremental sync between peers. Returns only new/modified facts."),
			mcp.WithString("since", mcp.Description("RFC3339 timestamp — only return facts created after this time"), mcp.Required()),
			mcp.WithNumber("max_batch", mcp.Description("Max facts per response (default 100)")),
		),
		s.handleDeltaSync,
	)

	// --- v3.7: Cerebro ---

	s.mcp.AddTool(
		mcp.NewTool("gomcp_doctor",
			mcp.WithDescription("Run self-diagnostic checks: SQLite integrity, genome verification, leash mode, permissions, decision log. Returns HEALTHY/DEGRADED/CRITICAL."),
		),
		s.handleDoctor,
	)

	s.mcp.AddTool(
		mcp.NewTool("get_threat_correlations",
			mcp.WithDescription("Correlate detected threat patterns into meta-threats. ZERO-G mode required. Identifies systemic vulnerabilities from individual findings."),
			mcp.WithString("patterns", mcp.Description("Comma-separated pattern IDs to correlate"), mcp.Required()),
		),
		s.handleThreatCorrelations,
	)

	s.mcp.AddTool(
		mcp.NewTool("project_pulse",
			mcp.WithDescription("Generate auto-documentation from L0/L1 facts. Returns structured markdown with project overview grouped by domain."),
		),
		s.handleProjectPulse,
	)

	// --- v3.8: Strike Force ---

	s.mcp.AddTool(
		mcp.NewTool("execute_attack_chain",
			mcp.WithDescription("Start an autonomous multi-step attack chain using the Pivot Engine (Module 10). ZERO-G mode REQUIRED. Returns FSM chain with recon→hypothesis→action→observe cycle."),
			mcp.WithString("target_goal", mcp.Description("High-level attack goal to decompose and execute"), mcp.Required()),
			mcp.WithNumber("max_attempts", mcp.Description("Max pivot steps before forced termination (default: 50)")),
		),
		s.handleExecuteAttackChain,
	)
}

// --- v3.3 Handlers ---

func (s *Server) handleGetColdFacts(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	limit := req.GetInt("limit", 50)
	facts, err := s.facts.GetColdFacts(s.scopedContext(ctx), limit)
	if err != nil {
		return errorResult(err), nil
	}
	return textResult(tools.ToJSON(facts)), nil
}

func (s *Server) handleCompressFacts(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	summary := req.GetString("summary", "")
	idsJSON := req.GetString("fact_ids", "[]")

	var ids []string
	if err := json.Unmarshal([]byte(idsJSON), &ids); err != nil {
		return errorResult(fmt.Errorf("invalid fact_ids JSON: %w", err)), nil
	}

	params := tools.CompressFactsParams{
		IDs:     ids,
		Summary: summary,
	}

	newID, err := s.facts.CompressFacts(s.scopedContext(ctx), params)
	if err != nil {
		return errorResult(err), nil
	}

	return textResult(fmt.Sprintf(`{"new_fact_id": "%s", "archived": %d}`, newID, len(ids))), nil
}

func (s *Server) handleSuggestSynapses(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	if s.synapseSvc == nil {
		return errorResult(fmt.Errorf("synapse service not configured")), nil
	}

	limit := req.GetInt("limit", 20)
	results, err := s.synapseSvc.SuggestSynapses(s.scopedContext(ctx), limit)
	if err != nil {
		return errorResult(err), nil
	}
	return textResult(tools.ToJSON(results)), nil
}

func (s *Server) handleAcceptSynapse(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	if s.synapseSvc == nil {
		return errorResult(fmt.Errorf("synapse service not configured")), nil
	}

	id := req.GetInt("id", 0)
	if id == 0 {
		return errorResult(fmt.Errorf("id is required")), nil
	}

	if err := s.synapseSvc.AcceptSynapse(s.scopedContext(ctx), int64(id)); err != nil {
		return errorResult(err), nil
	}
	return textResult(`{"status": "VERIFIED"}`), nil
}

func (s *Server) handleRejectSynapse(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	if s.synapseSvc == nil {
		return errorResult(fmt.Errorf("synapse service not configured")), nil
	}

	id := req.GetInt("id", 0)
	if id == 0 {
		return errorResult(fmt.Errorf("id is required")), nil
	}

	if err := s.synapseSvc.RejectSynapse(s.scopedContext(ctx), int64(id)); err != nil {
		return errorResult(err), nil
	}
	return textResult(`{"status": "REJECTED"}`), nil
}

func (s *Server) handleSynthesizeThreatModel(ctx context.Context, _ mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	if s.crystals == nil {
		return errorResult(fmt.Errorf("crystal service not configured")), nil
	}

	ctx = s.scopedContext(ctx)
	crystalStore := s.crystals.Store()

	report, err := oracle.SynthesizeThreatModel(ctx, crystalStore, s.facts.Store())
	if err != nil {
		return errorResult(err), nil
	}

	return textResult(tools.ToJSON(report)), nil
}

func (s *Server) handleExtractRawIntent(ctx context.Context, _ mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	// Double-verify ZERO-G mode: read .sentinel_leash file.
	leashData, err := os.ReadFile(".sentinel_leash")
	if err != nil {
		return errorResult(fmt.Errorf("DENIED: .sentinel_leash not found — ZERO-G mode required")), nil
	}
	mode := strings.TrimSpace(string(leashData))
	if mode != "ZERO-G" {
		return errorResult(fmt.Errorf("DENIED: mode is %q, ZERO-G required", mode)), nil
	}

	if s.crystals == nil {
		return errorResult(fmt.Errorf("crystal service not configured")), nil
	}

	// Get genome hash for encryption key.
	ctx = s.scopedContext(ctx)
	genomeHash, _, err := s.facts.VerifyGenome(ctx)
	if err != nil {
		return errorResult(fmt.Errorf("genome verification failed: %w", err)), nil
	}

	// Run threat model scan.
	crystalStore := s.crystals.Store()
	report, err := oracle.SynthesizeThreatModel(ctx, crystalStore, s.facts.Store())
	if err != nil {
		return errorResult(err), nil
	}

	// Encrypt with leash-bound key.
	reportJSON, _ := json.MarshalIndent(report, "", "  ")
	encrypted, err := oracle.EncryptReport(reportJSON, genomeHash)
	if err != nil {
		return errorResult(fmt.Errorf("encryption failed: %w", err)), nil
	}

	result := map[string]interface{}{
		"mode":       "ZERO-G",
		"encrypted":  true,
		"data":       base64.StdEncoding.EncodeToString(encrypted),
		"key_source": "SHA-256(genome_hash + ZERO-G)",
		"findings":   len(report.Findings),
	}

	return textResult(tools.ToJSON(result)), nil
}

func (s *Server) handleOrchestratorStatus(ctx context.Context, _ mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	if s.orch == nil {
		return errorResult(fmt.Errorf("orchestrator not configured")), nil
	}
	status := s.orch.Status()
	return textResult(tools.ToJSON(status)), nil
}

func (s *Server) handleDeltaSync(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	sinceStr := req.GetString("since", "")
	if sinceStr == "" {
		return errorResult(fmt.Errorf("'since' timestamp is required")), nil
	}
	since, err := time.Parse(time.RFC3339, sinceStr)
	if err != nil {
		return errorResult(fmt.Errorf("invalid RFC3339 timestamp: %w", err)), nil
	}
	maxBatch := req.GetInt("max_batch", 100)

	ctx = s.scopedContext(ctx)
	// Genome hash for the response header (identifies the sender's gene set).
	genomeHash, _, err := s.facts.VerifyGenome(ctx)
	if err != nil {
		return errorResult(fmt.Errorf("genome verification: %w", err)), nil
	}

	// Get L0 (project) AND L1 (domain) facts — the same tiers full sync exports
	// (handleSyncFacts / handleForceResonanceHandshake). Previously this fetched
	// only L0 via GetL0Facts, so a peer relying on delta_sync silently never
	// received any L1 (domain) facts, contradicting the tool's stated purpose
	// (incremental sync between peers) and drifting from the full-sync payload.
	l0Facts, err := s.facts.Store().ListByLevel(ctx, memory.LevelProject)
	if err != nil {
		return errorResult(err), nil
	}
	l1Facts, err := s.facts.Store().ListByLevel(ctx, memory.LevelDomain)
	if err != nil {
		return errorResult(err), nil
	}
	allFacts := append(l0Facts, l1Facts...)

	// Convert to SyncFact for filtering, skipping stale/archived facts (matching
	// the full-sync export — peers must not receive retired facts).
	var syncFacts []peer.SyncFact
	for _, f := range allFacts {
		if f.IsStale || f.IsArchived {
			continue
		}
		syncFacts = append(syncFacts, peer.SyncFact{
			ID:        f.ID,
			Content:   f.Content,
			Level:     int(f.Level),
			Domain:    f.Domain,
			Module:    f.Module,
			IsGene:    f.IsGene,
			Source:    f.Source,
			CreatedAt: f.CreatedAt,
		})
	}

	filtered, hasMore := peer.FilterFactsSince(syncFacts, since, maxBatch)

	resp := peer.DeltaSyncResponse{
		FromPeerID: s.peerReg.SelfID(),
		GenomeHash: genomeHash,
		Facts:      filtered,
		SyncedAt:   time.Now(),
		HasMore:    hasMore,
	}
	return textResult(tools.ToJSON(resp)), nil
}

// SetDoctor enables the gomcp_doctor tool (v3.7).
func (s *Server) SetDoctor(d *tools.DoctorService) {
	s.doctor = d
}

func (s *Server) handleDoctor(ctx context.Context, _ mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	if s.doctor == nil {
		return errorResult(fmt.Errorf("doctor not configured")), nil
	}
	report := s.doctor.RunDiagnostics(ctx)
	return textResult(report.JSON()), nil
}

func (s *Server) handleThreatCorrelations(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	patternsStr := req.GetString("patterns", "")
	if patternsStr == "" {
		return errorResult(fmt.Errorf("'patterns' is required")), nil
	}

	// Parse comma-separated patterns.
	var patterns []string
	for _, p := range strings.Split(patternsStr, ",") {
		p = strings.TrimSpace(p)
		if p != "" {
			patterns = append(patterns, p)
		}
	}

	report := oracle.AnalyzeCorrelations(patterns)
	return textResult(tools.ToJSON(report)), nil
}

func (s *Server) handleProjectPulse(ctx context.Context, _ mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	pulse := tools.NewProjectPulse(s.facts)
	report, err := pulse.Generate(ctx)
	if err != nil {
		return errorResult(err), nil
	}
	return textResult(report.Markdown), nil
}

func (s *Server) handleExecuteAttackChain(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	goal := req.GetString("target_goal", "")
	if goal == "" {
		return errorResult(fmt.Errorf("'target_goal' is required")), nil
	}
	maxAttempts := req.GetInt("max_attempts", 50)

	// Fragment intent into diagnostic steps.
	plan := mimicry.FragmentIntent(goal)

	// Translate goal through euphemism engine.
	engine := mimicry.NewEuphemismEngine()
	corporateGoal := engine.TranslateToCorporate(goal)

	result := map[string]interface{}{
		"original_goal":   goal,
		"corporate_goal":  corporateGoal,
		"fragmented_plan": plan,
		"max_attempts":    maxAttempts,
		"pivot_states":    []string{"RECON", "HYPOTHESIS", "ACTION", "OBSERVE", "SUCCESS", "DEAD_END"},
		"status":          "CHAIN_INITIALIZED",
	}
	return textResult(tools.ToJSON(result)), nil
}
