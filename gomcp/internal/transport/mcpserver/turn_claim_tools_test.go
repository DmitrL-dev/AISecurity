package mcpserver

import (
	"context"
	"encoding/json"
	"strings"
	"testing"

	"github.com/stretchr/testify/require"

	applicationtools "github.com/syntrex/gomcp/internal/application/tools"
	"github.com/syntrex/gomcp/internal/domain/memory"
	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
	"github.com/syntrex/gomcp/internal/infrastructure/sqlite"
)

const (
	claimToolRequestRefA = "session-turn-request-v1:sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
	claimToolRequestRefB = "session-turn-request-v1:sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
	claimToolOwnerA      = "claim_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
	claimToolOwnerB      = "claim_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
)

type oversizedCompletedClaimStore struct {
	*sqlite.FactRepo
	claim *memory.SessionTurnClaim
}

func (s *oversizedCompletedClaimStore) AcquireSessionTurnClaim(
	context.Context,
	string,
	string,
	string,
	string,
) (*memory.SessionTurnClaim, error) {
	return s.claim, nil
}

func claimToolRequest(name, requestRef, ownerToken string) map[string]interface{} {
	return map[string]interface{}{
		"session_id":  "session-one",
		"turn_id":     testTurnID,
		"request_ref": requestRef,
		"owner_token": ownerToken,
	}
}

func decodeClaimToolEnvelope(t *testing.T, result any) sessionTurnClaimEnvelope {
	t.Helper()
	encoded, err := json.Marshal(result)
	require.NoError(t, err)
	var envelope sessionTurnClaimEnvelope
	require.NoError(t, json.Unmarshal(encoded, &envelope))
	return envelope
}

func TestSessionTurnClaimToolsAreExactStructuredOnlyTools(t *testing.T) {
	srv, _ := newProjectTestServer(t, rlmscope.New("tenant-a", "project-alpha"))
	for _, name := range []string{
		"acquire_scoped_session_turn_claim",
		"begin_scoped_session_turn_execution",
	} {
		tool := srv.mcp.GetTool(name)
		require.NotNil(t, tool, name)
		require.NotNil(t, tool.Handler, name)
		require.ElementsMatch(t,
			[]string{"session_id", "turn_id", "request_ref", "owner_token"},
			tool.Tool.InputSchema.Required,
		)
		require.ElementsMatch(t,
			[]string{"session_id", "turn_id", "request_ref", "owner_token"},
			mapKeys(tool.Tool.InputSchema.Properties),
		)
		require.True(t, memory.IsExactProtocolTool(name), name)
	}
}

func TestSessionTurnClaimToolsEnforceOwnershipAndRequestBinding(t *testing.T) {
	srv, _ := newProjectTestServer(t, rlmscope.New("tenant-a", "project-alpha"))
	ctx := context.Background()

	acquired, err := srv.handleAcquireScopedSessionTurnClaim(
		ctx,
		sessionToolReq(
			"acquire_scoped_session_turn_claim",
			claimToolRequest("acquire_scoped_session_turn_claim", claimToolRequestRefA, claimToolOwnerA),
			"tenant-a",
			"project-alpha",
		),
	)
	require.NoError(t, err)
	require.False(t, acquired.IsError)
	require.Empty(t, acquired.Content)
	require.NotNil(t, acquired.StructuredContent)
	first := decodeClaimToolEnvelope(t, acquired.StructuredContent)
	require.Equal(t, boundedSessionScope{
		Version: 1, Kind: "session", TenantID: "tenant-a",
		ProjectID: "project-alpha", SessionID: "session-one",
	}, first.MemoryScope)
	require.NotNil(t, first.Claim)
	require.Equal(t, memory.SessionTurnClaimed, first.Claim.State)
	require.Equal(t, claimToolRequestRefA, first.Claim.RequestRef)
	require.True(t, first.Claim.Owned)

	busy, err := srv.handleAcquireScopedSessionTurnClaim(
		ctx,
		sessionToolReq(
			"acquire_scoped_session_turn_claim",
			claimToolRequest("acquire_scoped_session_turn_claim", claimToolRequestRefA, claimToolOwnerB),
			"tenant-a",
			"project-alpha",
		),
	)
	require.NoError(t, err)
	require.False(t, busy.IsError)
	busyEnvelope := decodeClaimToolEnvelope(t, busy.StructuredContent)
	require.Equal(t, memory.SessionTurnClaimed, busyEnvelope.Claim.State)
	require.False(t, busyEnvelope.Claim.Owned)

	wrongBegin, err := srv.handleBeginScopedSessionTurnExecution(
		ctx,
		sessionToolReq(
			"begin_scoped_session_turn_execution",
			claimToolRequest("begin_scoped_session_turn_execution", claimToolRequestRefA, claimToolOwnerB),
			"tenant-a",
			"project-alpha",
		),
	)
	require.NoError(t, err)
	require.False(t, wrongBegin.IsError)
	wrongEnvelope := decodeClaimToolEnvelope(t, wrongBegin.StructuredContent)
	require.Equal(t, memory.SessionTurnClaimed, wrongEnvelope.Claim.State)
	require.False(t, wrongEnvelope.Claim.Owned)

	executing, err := srv.handleBeginScopedSessionTurnExecution(
		ctx,
		sessionToolReq(
			"begin_scoped_session_turn_execution",
			claimToolRequest("begin_scoped_session_turn_execution", claimToolRequestRefA, claimToolOwnerA),
			"tenant-a",
			"project-alpha",
		),
	)
	require.NoError(t, err)
	require.False(t, executing.IsError)
	executingEnvelope := decodeClaimToolEnvelope(t, executing.StructuredContent)
	require.Equal(t, memory.SessionTurnExecuting, executingEnvelope.Claim.State)
	require.True(t, executingEnvelope.Claim.Owned)

	conflict, err := srv.handleAcquireScopedSessionTurnClaim(
		ctx,
		sessionToolReq(
			"acquire_scoped_session_turn_claim",
			claimToolRequest("acquire_scoped_session_turn_claim", claimToolRequestRefB, claimToolOwnerB),
			"tenant-a",
			"project-alpha",
		),
	)
	require.NoError(t, err)
	require.True(t, conflict.IsError)
	conflictWire, err := json.Marshal(conflict.StructuredContent)
	require.NoError(t, err)
	var conflictEnvelope boundedSessionErrorEnvelope
	require.NoError(t, json.Unmarshal(conflictWire, &conflictEnvelope))
	require.Equal(t, "turn_conflict", conflictEnvelope.Error.Code)
}

func TestSessionTurnClaimToolsRejectScopeAndUnknownArgumentsBeforeStore(t *testing.T) {
	srv, _ := newProjectTestServer(t, rlmscope.New("tenant-a", "project-alpha"))

	missingScope, err := srv.handleAcquireScopedSessionTurnClaim(
		context.Background(),
		callToolReq(
			"acquire_scoped_session_turn_claim",
			claimToolRequest("acquire_scoped_session_turn_claim", claimToolRequestRefA, claimToolOwnerA),
		),
	)
	require.NoError(t, err)
	require.True(t, missingScope.IsError)

	arguments := claimToolRequest("acquire_scoped_session_turn_claim", claimToolRequestRefA, claimToolOwnerA)
	arguments["tenant_id"] = "other"
	unknown, err := srv.handleAcquireScopedSessionTurnClaim(
		context.Background(),
		sessionToolReq(
			"acquire_scoped_session_turn_claim", arguments, "tenant-a", "project-alpha",
		),
	)
	require.NoError(t, err)
	require.True(t, unknown.IsError)
	encoded, err := json.Marshal(unknown.StructuredContent)
	require.NoError(t, err)
	var envelope boundedSessionErrorEnvelope
	require.NoError(t, json.Unmarshal(encoded, &envelope))
	require.Equal(t, "invalid_arguments", envelope.Error.Code)
}

func TestSessionTurnClaimToolsDoNotReflectOversizedUnknownArgumentNames(t *testing.T) {
	srv, _ := newProjectTestServer(t, rlmscope.New("tenant-a", "project-alpha"))
	arguments := claimToolRequest(
		"acquire_scoped_session_turn_claim",
		claimToolRequestRefA,
		claimToolOwnerA,
	)
	arguments[strings.Repeat("unknown", 20_000)] = true

	result, err := srv.handleAcquireScopedSessionTurnClaim(
		context.Background(),
		sessionToolReq(
			"acquire_scoped_session_turn_claim",
			arguments,
			"tenant-a",
			"project-alpha",
		),
	)
	require.NoError(t, err)
	require.True(t, result.IsError)
	encoded, err := json.Marshal(result)
	require.NoError(t, err)
	require.Less(t, len(encoded), 4096, "unknown argument names must not be reflected into responses")
}

func TestSessionTurnClaimToolsRejectOversizedCompletedFactIDWithoutReflection(t *testing.T) {
	oversizedID := strings.Repeat("f", 257)
	srv, repo, _ := newBoundedSessionRepoServer(t, rlmscope.New("tenant-a", "project-alpha"))
	store := &oversizedCompletedClaimStore{
		FactRepo: repo,
		claim: &memory.SessionTurnClaim{
			Version: 1, TurnID: testTurnID, RequestRef: claimToolRequestRefA,
			State: memory.SessionTurnCompleted, Generation: 1, CompletedFactID: oversizedID,
		},
	}
	srv.facts = applicationtools.NewFactService(store, nil)

	result, err := srv.handleAcquireScopedSessionTurnClaim(
		context.Background(),
		sessionToolReq(
			"acquire_scoped_session_turn_claim",
			claimToolRequest("acquire_scoped_session_turn_claim", claimToolRequestRefA, claimToolOwnerB),
			"tenant-a",
			"project-alpha",
		),
	)
	require.NoError(t, err)
	requireBoundedSessionErrorCode(t, result, "claim_integrity")
	encoded, err := json.Marshal(result)
	require.NoError(t, err)
	require.Less(t, len(encoded), 4096)
	require.NotContains(t, string(encoded), oversizedID)
}
