package mcpserver

import (
	"context"
	"errors"

	"github.com/mark3labs/mcp-go/mcp"

	"github.com/syntrex/gomcp/internal/domain/memory"
	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
)

type sessionTurnClaimEnvelope struct {
	MemoryScope boundedSessionScope      `json:"memory_scope"`
	Claim       *memory.SessionTurnClaim `json:"claim"`
}

func (s *Server) registerSessionTurnClaimTools() {
	s.mcp.AddTool(
		mcp.NewTool("acquire_scoped_session_turn_claim",
			mcp.WithDescription("Acquire or inspect the durable provider-dispatch claim for one exact scoped turn. Requires exact _meta.rlm_scope."),
			mcp.WithString("session_id", mcp.Description("Exact session identifier"), mcp.Required()),
			mcp.WithString("turn_id", mcp.Description("turn_ followed by 64 lowercase hex characters"), mcp.Required()),
			mcp.WithString("request_ref", mcp.Description("Canonical session-turn-request-v1 SHA-256 identity"), mcp.Required()),
			mcp.WithString("owner_token", mcp.Description("Per-request claim_ token with 64 lowercase hex characters"), mcp.Required()),
		),
		s.handleAcquireScopedSessionTurnClaim,
	)
	s.mcp.AddTool(
		mcp.NewTool("begin_scoped_session_turn_execution",
			mcp.WithDescription("Atomically mark an owned scoped turn claim EXECUTING immediately before provider send. Requires exact _meta.rlm_scope."),
			mcp.WithString("session_id", mcp.Description("Exact session identifier"), mcp.Required()),
			mcp.WithString("turn_id", mcp.Description("turn_ followed by 64 lowercase hex characters"), mcp.Required()),
			mcp.WithString("request_ref", mcp.Description("Canonical session-turn-request-v1 SHA-256 identity"), mcp.Required()),
			mcp.WithString("owner_token", mcp.Description("Token returned as owner by claim acquisition"), mcp.Required()),
		),
		s.handleBeginScopedSessionTurnExecution,
	)
}

func parseSessionTurnClaimArguments(
	s *Server,
	ctx context.Context,
	req mcp.CallToolRequest,
) (context.Context, string, string, string, string, *boundedSessionScope, *mcp.CallToolResult) {
	exactCtx, sessionID, failure := parseBoundedSessionContext(s, ctx, req)
	if failure != nil {
		return nil, "", "", "", "", nil, failure
	}
	marker := boundedSessionScopeFor(exactCtx, sessionID)
	arguments := req.GetArguments()
	for name := range arguments {
		switch name {
		case "session_id", "turn_id", "request_ref", "owner_token":
		default:
			return nil, "", "", "", "", &marker,
				boundedSessionErrorResult(&marker, "invalid_arguments", "request contains an unknown argument")
		}
	}
	turnID, turnOK := arguments["turn_id"].(string)
	requestRef, requestOK := arguments["request_ref"].(string)
	ownerToken, ownerOK := arguments["owner_token"].(string)
	if !turnOK || rlmscope.ValidateTurnID(turnID) != nil ||
		!requestOK || memory.ValidateSessionTurnRequestRef(requestRef) != nil ||
		!ownerOK || memory.ValidateSessionTurnClaimToken(ownerToken) != nil {
		return nil, "", "", "", "", &marker,
			boundedSessionErrorResult(
				&marker,
				"invalid_arguments",
				"valid turn_id, canonical request_ref, and claim owner_token are required",
			)
	}
	return exactCtx, sessionID, turnID, requestRef, ownerToken, &marker, nil
}

func sessionTurnClaimErrorResult(
	marker *boundedSessionScope,
	err error,
) *mcp.CallToolResult {
	switch {
	case errors.Is(err, memory.ErrSessionTurnConflict):
		return boundedSessionErrorResult(marker, "turn_conflict", "turn id is bound to another request")
	case errors.Is(err, memory.ErrSessionTurnClaimIntegrity),
		errors.Is(err, memory.ErrSessionTurnIntegrity):
		return boundedSessionErrorResult(marker, "claim_integrity", "durable turn claim or receipt failed integrity validation")
	case errors.Is(err, memory.ErrSessionTurnClaimNotFound):
		return boundedSessionErrorResult(marker, "claim_missing", "durable turn claim does not exist")
	default:
		return boundedSessionErrorResult(marker, "claim_backend_unavailable", "durable turn claim backend is unavailable")
	}
}

func (s *Server) handleAcquireScopedSessionTurnClaim(
	ctx context.Context,
	req mcp.CallToolRequest,
) (*mcp.CallToolResult, error) {
	exactCtx, sessionID, turnID, requestRef, ownerToken, marker, failure :=
		parseSessionTurnClaimArguments(s, ctx, req)
	if failure != nil {
		return failure, nil
	}
	claim, err := s.facts.AcquireSessionTurnClaim(
		exactCtx, sessionID, turnID, requestRef, ownerToken,
	)
	if err != nil {
		return sessionTurnClaimErrorResult(marker, err), nil
	}
	return structuredFactPageResult(sessionTurnClaimEnvelope{
		MemoryScope: *marker,
		Claim:       claim,
	}, false), nil
}

func (s *Server) handleBeginScopedSessionTurnExecution(
	ctx context.Context,
	req mcp.CallToolRequest,
) (*mcp.CallToolResult, error) {
	exactCtx, sessionID, turnID, requestRef, ownerToken, marker, failure :=
		parseSessionTurnClaimArguments(s, ctx, req)
	if failure != nil {
		return failure, nil
	}
	claim, err := s.facts.BeginSessionTurnExecution(
		exactCtx, sessionID, turnID, requestRef, ownerToken,
	)
	if err != nil {
		return sessionTurnClaimErrorResult(marker, err), nil
	}
	return structuredFactPageResult(sessionTurnClaimEnvelope{
		MemoryScope: *marker,
		Claim:       claim,
	}, false), nil
}
