package mcpserver

import (
	"context"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"strings"
	"testing"

	"github.com/stretchr/testify/require"
	modernsqlite "modernc.org/sqlite"
	sqlitelib "modernc.org/sqlite/lib"

	"github.com/syntrex/gomcp/internal/application/tools"
	"github.com/syntrex/gomcp/internal/domain/causal"
	"github.com/syntrex/gomcp/internal/infrastructure/sqlite"
)

func TestBoundedCausalToolStructuredFrameAndLegacyCompatibility(t *testing.T) {
	srv := newTestServer(t)
	ctx := context.Background()
	content := "decision <tag>\\u0000 " + strings.Repeat("<&\\n", 8*1024)
	_, err := srv.handleAddCausalNode(ctx, callToolReq("add_causal_node", map[string]interface{}{
		"node_type": "decision", "content": content,
	}))
	require.NoError(t, err)

	legacyBefore, err := srv.handleGetCausalChain(ctx, callToolReq("get_causal_chain", map[string]interface{}{
		"query": "decision", "max_depth": 5,
	}))
	require.NoError(t, err)
	legacyBeforeJSON, err := json.Marshal(legacyBefore)
	require.NoError(t, err)

	result, err := srv.handleGetDefaultCausalChainBounded(ctx, callToolReq(
		"get_default_causal_chain_bounded",
		map[string]interface{}{
			"query": "decision", "max_depth": 1, "max_nodes": 10,
			"max_result_bytes": boundedCausalMaxResultBytes,
		},
	))
	require.NoError(t, err)
	require.False(t, result.IsError)
	envelope := decodeStructuredResult[boundedCausalEnvelope](t, result)
	require.Equal(t, factPageMemoryScope{
		Version: 1, Kind: "project", TenantID: "local", ProjectID: "default",
	}, envelope.MemoryScope)
	raw, err := base64.StdEncoding.DecodeString(envelope.Result.Frame.DataBase64)
	require.NoError(t, err)
	require.Len(t, raw, envelope.Result.Frame.TotalBytes)
	digest := sha256.Sum256(raw)
	require.Equal(t, hex.EncodeToString(digest[:]), envelope.Result.Frame.SHA256)
	var decoded map[string]interface{}
	require.NoError(t, json.Unmarshal(raw, &decoded))
	require.Contains(t, decoded, "chain")
	require.Contains(t, decoded, "mermaid")

	wire, err := json.Marshal(result)
	require.NoError(t, err)
	require.Less(t, len(wire), 1024*1024, "one MCP response line must stay below 1 MiB")

	legacyAfter, err := srv.handleGetCausalChain(ctx, callToolReq("get_causal_chain", map[string]interface{}{
		"query": "decision", "max_depth": 5,
	}))
	require.NoError(t, err)
	legacyAfterJSON, err := json.Marshal(legacyAfter)
	require.NoError(t, err)
	require.Equal(t, legacyBeforeJSON, legacyAfterJSON, "bounded tool must not alter the legacy response")
}

func TestBoundedCausalToolAdvertisesAndEnforcesDirectNeighbourDepth(t *testing.T) {
	srv := newTestServer(t)
	tool := srv.mcp.GetTool("get_default_causal_chain_bounded")
	require.NotNil(t, tool)
	depth, ok := tool.Tool.InputSchema.Properties["max_depth"].(map[string]any)
	require.True(t, ok)
	require.Equal(t, float64(1), depth["minimum"])
	require.Equal(t, float64(1), depth["maximum"])
	require.Equal(t, float64(1), depth["const"])

	result, err := srv.handleGetDefaultCausalChainBounded(context.Background(), callToolReq(
		"get_default_causal_chain_bounded",
		map[string]interface{}{
			"query": "decision", "max_depth": 2, "max_nodes": 10,
			"max_result_bytes": boundedCausalMaxResultBytes,
		},
	))
	require.NoError(t, err)
	require.True(t, result.IsError)
	envelope := decodeStructuredResult[boundedCausalErrorEnvelope](t, result)
	require.Equal(t, "invalid_arguments", envelope.Error.Code)
}

func TestBoundedCausalToolRejectsOversizeAndScopeSpoof(t *testing.T) {
	srv := newTestServer(t)
	ctx := context.Background()
	_, err := srv.handleAddCausalNode(ctx, callToolReq("add_causal_node", map[string]interface{}{
		"node_type": "decision", "content": strings.Repeat("<", 96*1024),
	}))
	require.NoError(t, err)

	oversize, err := srv.handleGetDefaultCausalChainBounded(ctx, callToolReq(
		"get_default_causal_chain_bounded",
		map[string]interface{}{
			"query": "<<<", "max_depth": 1, "max_nodes": 10,
			"max_result_bytes": boundedCausalMaxResultBytes,
		},
	))
	require.NoError(t, err)
	require.True(t, oversize.IsError)
	errEnvelope := decodeStructuredResult[boundedCausalErrorEnvelope](t, oversize)
	require.Equal(t, "stored_causal_node_too_large", errEnvelope.Error.Code)
	require.Equal(t, string(causal.StoredCausalResultMeasurement), errEnvelope.Error.Measurement)
	require.Greater(t, errEnvelope.Error.MeasuredBytes, int64(boundedCausalMaxResultBytes))
	require.Equal(t, int64(boundedCausalMaxResultBytes), errEnvelope.Error.MaximumBytes)
	wire, err := json.Marshal(oversize)
	require.NoError(t, err)
	require.Less(t, len(wire), 1024*1024)

	spoof := sessionToolReq(
		"get_default_causal_chain_bounded",
		map[string]interface{}{
			"query": "decision", "max_depth": 1, "max_nodes": 10,
			"max_result_bytes": boundedCausalMaxResultBytes,
		},
		"local", "project-spoof",
	)
	spoofed, err := srv.handleGetDefaultCausalChainBounded(ctx, spoof)
	require.NoError(t, err)
	require.True(t, spoofed.IsError)
	spoofEnvelope := decodeStructuredResult[boundedCausalErrorEnvelope](t, spoofed)
	require.Equal(t, "scope_override_forbidden", spoofEnvelope.Error.Code)
}

func TestBoundedCausalToolMapsStoredOversizeWithoutReflectingNode(t *testing.T) {
	const storedRowHardLimit = 16 * 1024 * 1024
	db, err := sqlite.OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { require.NoError(t, db.Close()) })
	repo, err := sqlite.NewCausalRepo(db)
	require.NoError(t, err)
	srv := &Server{causal: tools.NewCausalService(repo)}

	const hostileID = "hostile-causal-node-must-not-reach-wire"
	_, err = db.SqlDB().Exec(`INSERT INTO causal_nodes (
		id, tenant_id, project_id, node_type, content, created_at
	) VALUES (?, 'local', 'default', 'decision',
		CAST('oversized-decision ' || zeroblob(?) AS TEXT),
		'2026-09-01T00:00:00Z')`, hostileID, storedRowHardLimit+1)
	require.NoError(t, err)
	conn, err := db.SqlDB().Conn(context.Background())
	require.NoError(t, err)
	previousLimit, err := modernsqlite.Limit(conn, sqlitelib.SQLITE_LIMIT_LENGTH, storedRowHardLimit)
	require.NoError(t, err)
	require.Greater(t, previousLimit, storedRowHardLimit)
	require.NoError(t, conn.Close())

	result, err := srv.handleGetDefaultCausalChainBounded(context.Background(), callToolReq(
		"get_default_causal_chain_bounded",
		map[string]interface{}{
			"query": "oversized-decision", "max_depth": 1, "max_nodes": 1,
			"max_result_bytes": boundedCausalMaxResultBytes,
		},
	))
	require.NoError(t, err)
	require.True(t, result.IsError)
	envelope := decodeStructuredResult[boundedCausalErrorEnvelope](t, result)
	require.Equal(t, "stored_causal_node_too_large", envelope.Error.Code)
	require.Equal(t, string(causal.StoredCausalBytesMeasurement), envelope.Error.Measurement)
	require.Greater(t, envelope.Error.MeasuredBytes, int64(storedRowHardLimit))
	require.Equal(t, int64(storedRowHardLimit), envelope.Error.MaximumBytes)

	wire, err := json.Marshal(result)
	require.NoError(t, err)
	require.Less(t, len(wire), 4096)
	require.NotContains(t, string(wire), hostileID)
	require.NotContains(t, string(wire), "oversized-decision")
}
