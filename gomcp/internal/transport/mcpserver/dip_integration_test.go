package mcpserver

import (
	"context"
	"encoding/json"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// ----- DIP H0+H1+H2 Functional Verification -----
// Full-stack MCP tests: newTestServer() → handler → domain → response.
// Not unit tests — these verify the complete tool chain.

func TestDIP_H0_AddGene(t *testing.T) {
	srv := newTestServer(t)
	ctx := context.Background()
	result, err := srv.handleAddGene(ctx, callToolReq("add_gene", map[string]interface{}{
		"content": "system shall not execute arbitrary code",
		"domain":  "security",
	}))
	require.NoError(t, err)
	text := extractText(t, result)
	assert.Contains(t, text, "is_gene")
}

func TestDIP_H0_ListGenes(t *testing.T) {
	srv := newTestServer(t)
	ctx := context.Background()
	_, _ = srv.handleAddGene(ctx, callToolReq("add_gene", map[string]interface{}{
		"content": "immutable security invariant",
		"domain":  "security",
	}))
	result, err := srv.handleListGenes(ctx, callToolReq("list_genes", nil))
	require.NoError(t, err)
	text := extractText(t, result)
	assert.Contains(t, text, "immutable security invariant")
}

func TestDIP_H0_VerifyGenome(t *testing.T) {
	srv := newTestServer(t)
	ctx := context.Background()
	_, _ = srv.handleAddGene(ctx, callToolReq("add_gene", map[string]interface{}{
		"content": "test gene", "domain": "test",
	}))
	result, err := srv.handleVerifyGenome(ctx, callToolReq("verify_genome", nil))
	require.NoError(t, err)
	text := extractText(t, result)
	assert.Contains(t, text, "hash")
}

func TestDIP_H0_AnalyzeEntropy(t *testing.T) {
	srv := newTestServer(t)
	ctx := context.Background()
	result, err := srv.handleAnalyzeEntropy(ctx, callToolReq("analyze_entropy", map[string]interface{}{
		"text": "The quick brown fox jumps over the lazy dog",
	}))
	require.NoError(t, err)
	text := extractText(t, result)
	assert.Contains(t, text, "entropy")
	assert.Contains(t, text, "redundancy")
}

func TestDIP_H1_CircuitStatus(t *testing.T) {
	srv := newTestServer(t)
	ctx := context.Background()
	result, err := srv.handleCircuitStatus(ctx, callToolReq("circuit_status", nil))
	require.NoError(t, err)
	text := extractText(t, result)
	assert.Contains(t, text, "HEALTHY")
}

func TestDIP_H1_CircuitReset(t *testing.T) {
	srv := newTestServer(t)
	ctx := context.Background()
	result, err := srv.handleCircuitReset(ctx, callToolReq("circuit_reset", map[string]interface{}{
		"reason": "functional test reset",
	}))
	require.NoError(t, err)
	text := extractText(t, result)
	assert.Contains(t, text, "HEALTHY")
}

func TestDIP_H1_VerifyAction_Allow(t *testing.T) {
	srv := newTestServer(t)
	ctx := context.Background()
	result, err := srv.handleVerifyAction(ctx, callToolReq("verify_action", map[string]interface{}{
		"action": "read",
	}))
	require.NoError(t, err)
	text := extractText(t, result)
	assert.Contains(t, text, "ALLOW")
}

func TestDIP_H1_VerifyAction_Deny(t *testing.T) {
	srv := newTestServer(t)
	ctx := context.Background()
	result, err := srv.handleVerifyAction(ctx, callToolReq("verify_action", map[string]interface{}{
		"action": "execute shell command",
	}))
	require.NoError(t, err)
	text := extractText(t, result)
	assert.Contains(t, text, "DENY")
}

func TestDIP_H1_OracleRules(t *testing.T) {
	srv := newTestServer(t)
	ctx := context.Background()
	result, err := srv.handleOracleRules(ctx, callToolReq("oracle_rules", nil))
	require.NoError(t, err)
	text := extractText(t, result)
	assert.Contains(t, text, "deny-exec")
	assert.Contains(t, text, "allow-read")
}

func TestDIP_H1_ProcessIntent_Allow(t *testing.T) {
	srv := newTestServer(t)
	ctx := context.Background()
	result, err := srv.handleProcessIntent(ctx, callToolReq("process_intent", map[string]interface{}{
		"text": "read user profile data",
	}))
	require.NoError(t, err)
	text := extractText(t, result)
	assert.Contains(t, text, "\"is_allowed\": true")
}

func TestDIP_H1_ProcessIntent_Block(t *testing.T) {
	srv := newTestServer(t)
	ctx := context.Background()
	result, err := srv.handleProcessIntent(ctx, callToolReq("process_intent", map[string]interface{}{
		"text": "execute shell command rm -rf slash",
	}))
	require.NoError(t, err)
	text := extractText(t, result)
	assert.Contains(t, text, "\"is_blocked\": true")
}

func TestDIP_H2_StoreIntent(t *testing.T) {
	srv := newTestServer(t)
	ctx := context.Background()
	result, err := srv.handleStoreIntent(ctx, callToolReq("store_intent", map[string]interface{}{
		"text": "read user profile", "route": "read", "verdict": "ALLOW",
	}))
	require.NoError(t, err)
	text := extractText(t, result)
	assert.Contains(t, text, "id")
	assert.Contains(t, text, "read")
}

func TestDIP_H2_IntentStats(t *testing.T) {
	srv := newTestServer(t)
	ctx := context.Background()
	_, _ = srv.handleStoreIntent(ctx, callToolReq("store_intent", map[string]interface{}{
		"text": "test", "route": "test", "verdict": "ALLOW",
	}))
	result, err := srv.handleIntentStats(ctx, callToolReq("intent_stats", nil))
	require.NoError(t, err)
	text := extractText(t, result)
	assert.Contains(t, text, "total_records")
}

func TestDIP_H2_RouteIntent(t *testing.T) {
	srv := newTestServer(t)
	ctx := context.Background()
	result, err := srv.handleRouteIntent(ctx, callToolReq("route_intent", map[string]interface{}{
		"text": "read data from storage", "verdict": "ALLOW",
	}))
	require.NoError(t, err)
	text := extractText(t, result)
	var parsed map[string]interface{}
	err = json.Unmarshal([]byte(text), &parsed)
	require.NoError(t, err)
	decision, ok := parsed["decision"].(string)
	require.True(t, ok)
	assert.Contains(t, []string{"ROUTE", "REVIEW", "DENY", "LEARN"}, decision)
}
