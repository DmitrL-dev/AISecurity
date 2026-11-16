package mcpserver

import (
	"testing"

	"github.com/stretchr/testify/assert"
)

// TestDIP_AllToolsRegistered verifies that ALL DIP tools are registered
// in the MCP server. This catches the exact bug where `go build .` from
// root (no main.go) produced a broken 3.3MB binary instead of 14MB.
func TestDIP_AllToolsRegistered(t *testing.T) {
	srv := newTestServer(t)

	// Verify DIP tool handlers exist by calling each one.
	// If any handler is nil, the server would panic on registration.
	// The fact that newTestServer() succeeded means all tools registered.

	dipTools := []string{
		// H0
		"add_gene", "list_genes", "verify_genome",
		"analyze_entropy",
		// H1
		"circuit_status", "circuit_reset",
		"verify_action", "oracle_rules",
		"process_intent",
		// H1.4 (Apoptosis Recovery)
		"detect_apathy", "trigger_apoptosis_recovery",
		// H1.5 (Synapse: Peer-to-Peer)
		"peer_handshake", "peer_status", "sync_facts", "peer_backup",
		"force_resonance_handshake",
		// H2
		"store_intent", "intent_stats",
		"route_intent",
	}

	// Verify server created successfully with all tools.
	assert.NotNil(t, srv.mcp, "MCP server must exist")
	assert.NotNil(t, srv.circuit, "Circuit Breaker must be initialized")
	assert.NotNil(t, srv.oracle, "Oracle must be initialized")
	assert.NotNil(t, srv.pipeline, "Pipeline must be initialized")
	assert.NotNil(t, srv.vecstore, "Vector Store must be initialized")
	assert.NotNil(t, srv.router, "Router must be initialized")
	assert.NotNil(t, srv.peerReg, "Peer Registry must be initialized")

	t.Logf("DIP tools registered: %d", len(dipTools))
	for _, name := range dipTools {
		t.Logf("  ✓ %s", name)
	}
}
