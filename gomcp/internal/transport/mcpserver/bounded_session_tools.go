package mcpserver

import (
	"bytes"
	"context"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"strings"

	"github.com/mark3labs/mcp-go/mcp"

	applicationtools "github.com/syntrex/gomcp/internal/application/tools"
	"github.com/syntrex/gomcp/internal/domain/memory"
	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
)

const (
	boundedSessionProtocolVersion = 1
	boundedSessionMaxCursorBytes  = 64 * 1024
	boundedSessionMaxContentBytes = 64 * 1024
	managedSessionRequestPrefix   = "session-turn-request-v1:sha256:"
)

type boundedSessionScope struct {
	Version   int    `json:"version"`
	Kind      string `json:"kind"`
	TenantID  string `json:"tenant_id"`
	ProjectID string `json:"project_id"`
	SessionID string `json:"session_id"`
}

type boundedSessionErrorEnvelope struct {
	MemoryScope *boundedSessionScope `json:"memory_scope,omitempty"`
	Error       factPageError        `json:"error"`
}

type boundedSessionStoredLimitEnvelope struct {
	MemoryScope boundedSessionScope           `json:"memory_scope"`
	Error       boundedSearchStoredLimitError `json:"error"`
}

type boundedSessionTurnResult struct {
	Version       int                        `json:"version"`
	Found         bool                       `json:"found"`
	Deduplicated  bool                       `json:"deduplicated"`
	TurnReceipt   *memory.SessionTurnReceipt `json:"turn_receipt,omitempty"`
	FactID        string                     `json:"fact_id,omitempty"`
	ContentSHA256 string                     `json:"content_sha256,omitempty"`
	ContentBytes  int                        `json:"content_bytes,omitempty"`
}

type boundedSessionTurnEnvelope struct {
	MemoryScope boundedSessionScope      `json:"memory_scope"`
	Result      boundedSessionTurnResult `json:"result"`
}

type boundedSessionRecallFact struct {
	ID        string           `json:"id"`
	TenantID  string           `json:"tenant_id"`
	ProjectID string           `json:"project_id"`
	SessionID string           `json:"session_id"`
	Content   string           `json:"content"`
	Level     memory.HierLevel `json:"level"`
	Domain    string           `json:"domain"`
	Module    string           `json:"module"`
	Origin    memory.Origin    `json:"origin"`
}

type boundedSessionCursorFact struct {
	FactID         string `json:"fact_id"`
	SHA256         string `json:"sha256"`
	StateSHA256    string `json:"state_sha256"`
	SerializedSize int    `json:"serialized_size"`
}

type boundedSessionSearchCursor struct {
	Version         int                        `json:"version"`
	MemoryScope     boundedSessionScope        `json:"memory_scope"`
	QuerySHA256     string                     `json:"query_sha256"`
	Mode            string                     `json:"mode"`
	Limit           int                        `json:"limit"`
	MaxFactBytes    int                        `json:"max_fact_bytes"`
	Results         []boundedSessionCursorFact `json:"results"`
	ResultIndex     int                        `json:"result_index"`
	IntraFactOffset int                        `json:"intra_fact_offset"`
}

type boundedSessionSearchPage struct {
	Version            int             `json:"version"`
	Encoding           string          `json:"encoding"`
	FrameRawLimitBytes int             `json:"frame_raw_limit_bytes"`
	MaxFactBytes       int             `json:"max_fact_bytes"`
	ResultCount        int             `json:"result_count"`
	Frames             []factPageFrame `json:"frames"`
	NextCursor         string          `json:"next_cursor,omitempty"`
	Done               bool            `json:"done"`
}

type boundedSessionSearchEnvelope struct {
	MemoryScope boundedSessionScope      `json:"memory_scope"`
	Page        boundedSessionSearchPage `json:"page"`
}

func (s *Server) registerBoundedSessionTools() {
	s.mcp.AddTool(
		mcp.NewTool("add_scoped_session_turn",
			mcp.WithDescription("Store one managed conversation turn and return only a compact receipt attestation. Requires exact _meta.rlm_scope."),
			mcp.WithString("session_id", mcp.Description("Exact session identifier"), mcp.Required()),
			mcp.WithString("turn_id", mcp.Description("turn_ followed by 64 lowercase hex characters"), mcp.Required()),
			mcp.WithString("content", mcp.Description("Managed conversation projection, at most 65536 UTF-8 bytes"), mcp.Required()),
			mcp.WithString("request_ref", mcp.Description("Canonical session-turn-request-v1 SHA-256 identity"), mcp.Required()),
		),
		s.handleAddScopedSessionTurn,
	)
	s.mcp.AddTool(
		mcp.NewTool("get_scoped_session_turn",
			mcp.WithDescription("Reconcile one managed conversation turn without returning stored content. Requires exact _meta.rlm_scope."),
			mcp.WithString("session_id", mcp.Description("Exact session identifier"), mcp.Required()),
			mcp.WithString("turn_id", mcp.Description("turn_ followed by 64 lowercase hex characters"), mcp.Required()),
			mcp.WithString("request_ref", mcp.Description("Canonical session-turn-request-v1 SHA-256 identity"), mcp.Required()),
		),
		s.handleGetScopedSessionTurn,
	)
	s.mcp.AddTool(
		mcp.NewTool("search_scoped_session_facts_page",
			mcp.WithDescription("Search one exact managed conversation session and return one bounded base64 fact frame. Requires exact _meta.rlm_scope."),
			mcp.WithString("session_id", mcp.Description("Exact session identifier"), mcp.Required()),
			mcp.WithString("query", mcp.Description("Non-empty search query"), mcp.Required()),
			mcp.WithString("mode", mcp.Description("keyword, semantic, or hybrid"), mcp.Enum("keyword", "semantic", "hybrid"), mcp.Required()),
			mcp.WithNumber("limit", mcp.Description("Maximum ranked results (1-100)"), mcp.Min(1), mcp.Max(100), mcp.MultipleOf(1), mcp.Required()),
			mcp.WithNumber("max_fact_bytes", mcp.Description("Maximum compact serialized fact bytes (1-16777216)"), mcp.Min(1), mcp.Max(factPageMaxFactBytes), mcp.MultipleOf(1), mcp.Required()),
			mcp.WithString("cursor", mcp.Description("Opaque continuation cursor returned by the previous page")),
		),
		s.handleSearchScopedSessionFactsPage,
	)
}

func boundedSessionScopeFor(ctx context.Context, sessionID string) boundedSessionScope {
	sc := rlmscope.FromContext(ctx)
	return boundedSessionScope{
		Version: 1, Kind: "session", TenantID: sc.TenantID,
		ProjectID: sc.ProjectID, SessionID: sessionID,
	}
}

func boundedSessionErrorResult(
	marker *boundedSessionScope,
	code, message string,
) *mcp.CallToolResult {
	return structuredFactPageResult(boundedSessionErrorEnvelope{
		MemoryScope: marker,
		Error:       factPageError{Code: code, Message: message},
	}, true)
}

func boundedSessionStoredOversizedResult(
	marker boundedSessionScope,
	measurement *memory.BoundedSearchStoredOversize,
) *mcp.CallToolResult {
	wireError := boundedSearchStoredLimitError{}
	if measurement == nil {
		wireError.Code = "stored_search_unavailable"
		wireError.Message = "stored bounded-session measurement is unavailable"
	} else {
		switch measurement.Kind {
		case memory.BoundedSearchStoredIdentityOversizeKind:
			wireError.Code = "stored_fact_identity_too_large"
			wireError.Message = "stored session fact identity exceeds the bounded-search hard limit"
			wireError.StoredIdentityBytes = measurement.StoredBytes
			wireError.MaxStoredIdentityBytes = measurement.MaxStoredBytes
		case memory.BoundedSearchStoredScopeOversizeKind:
			wireError.Code = "stored_search_scope_too_large"
			wireError.Message = "stored session search scope exceeds the aggregate hard limit"
			wireError.StoredTotalBytes = measurement.StoredBytes
			wireError.MaxStoredTotalBytes = measurement.MaxStoredBytes
		default:
			wireError.Code = "stored_fact_too_large"
			wireError.Message = "stored session fact variable columns exceed the hard limit"
			wireError.StoredVariableBytes = measurement.StoredBytes
			wireError.MaxStoredVariableBytes = measurement.MaxStoredBytes
		}
	}
	return structuredFactPageResult(boundedSessionStoredLimitEnvelope{
		MemoryScope: marker,
		Error:       wireError,
	}, true)
}

func parseBoundedSessionContext(
	s *Server,
	ctx context.Context,
	req mcp.CallToolRequest,
) (context.Context, string, *mcp.CallToolResult) {
	exactCtx, err := s.sessionMemoryContext(ctx, req)
	if err != nil {
		return nil, "", boundedSessionErrorResult(nil, "invalid_scope", err.Error())
	}
	sessionID, ok := req.GetArguments()["session_id"].(string)
	if !ok || rlmscope.ValidateSessionID(sessionID) != nil {
		return nil, "", boundedSessionErrorResult(nil, "invalid_arguments", "session_id is invalid")
	}
	return exactCtx, sessionID, nil
}

func validManagedSessionRequestRef(value string) bool {
	if len(value) != len(managedSessionRequestPrefix)+sha256.Size*2 ||
		!strings.HasPrefix(value, managedSessionRequestPrefix) {
		return false
	}
	return validBoundedSearchDigest(value[len(managedSessionRequestPrefix):])
}

func validateManagedSessionFact(
	ctx context.Context,
	sessionID string,
	fact *memory.Fact,
	requestRef string,
) error {
	sc, err := rlmscope.RequireSessionScope(ctx, sessionID)
	if err != nil {
		return err
	}
	if fact == nil || fact.ID == "" || len(fact.ID) > 256 ||
		fact.TenantID != sc.TenantID || fact.ProjectID != sc.ProjectID ||
		fact.SessionID != sessionID || fact.Level != memory.LevelDomain ||
		fact.Domain != "conversation" || fact.Module != "chat" ||
		fact.Origin != memory.OriginDerived || fact.Source != "session_memory" {
		return fmt.Errorf("managed session fact boundary mismatch")
	}
	if requestRef != "" && fact.CodeRef != requestRef {
		return memory.ErrSessionTurnConflict
	}
	return nil
}

func (s *Server) handleAddScopedSessionTurn(
	ctx context.Context,
	req mcp.CallToolRequest,
) (*mcp.CallToolResult, error) {
	exactCtx, sessionID, failure := parseBoundedSessionContext(s, ctx, req)
	if failure != nil {
		return failure, nil
	}
	marker := boundedSessionScopeFor(exactCtx, sessionID)
	arguments := req.GetArguments()
	for name := range arguments {
		switch name {
		case "session_id", "turn_id", "content", "request_ref":
		default:
			return boundedSessionErrorResult(&marker, "invalid_arguments", "request contains an unknown argument"), nil
		}
	}
	turnID, turnOK := arguments["turn_id"].(string)
	content, contentOK := arguments["content"].(string)
	requestRef, requestRefOK := arguments["request_ref"].(string)
	if !turnOK || rlmscope.ValidateTurnID(turnID) != nil || !contentOK || content == "" ||
		len(content) > boundedSessionMaxContentBytes || !requestRefOK || !validManagedSessionRequestRef(requestRef) {
		return boundedSessionErrorResult(&marker, "invalid_arguments", "turn_id, non-empty bounded content, and canonical request_ref are required"), nil
	}
	fact, receipt, deduplicated, err := s.facts.AddSessionTurn(exactCtx, sessionID, applicationtools.AddFactParams{
		Content: content, Level: int(memory.LevelDomain), Domain: "conversation",
		Module: "chat", CodeRef: requestRef, TurnID: turnID, Origin: string(memory.OriginDerived),
	})
	if err != nil {
		if errors.Is(err, memory.ErrSessionTurnConflict) {
			return boundedSessionErrorResult(&marker, "turn_conflict", "turn id is bound to another request"), nil
		}
		return boundedSessionErrorResult(&marker, "session_store_unavailable", "managed session turn could not be stored"), nil
	}
	if err := validateManagedSessionFact(exactCtx, sessionID, fact, requestRef); err != nil {
		return boundedSessionErrorResult(&marker, "session_scope_mismatch", "stored session turn failed exact-boundary validation"), nil
	}
	digest := sha256.Sum256([]byte(fact.Content))
	return structuredFactPageResult(boundedSessionTurnEnvelope{
		MemoryScope: marker,
		Result: boundedSessionTurnResult{
			Version: 1, Found: true, Deduplicated: deduplicated,
			TurnReceipt: receipt, FactID: fact.ID,
			ContentSHA256: hex.EncodeToString(digest[:]), ContentBytes: len(fact.Content),
		},
	}, false), nil
}

func (s *Server) handleGetScopedSessionTurn(
	ctx context.Context,
	req mcp.CallToolRequest,
) (*mcp.CallToolResult, error) {
	exactCtx, sessionID, failure := parseBoundedSessionContext(s, ctx, req)
	if failure != nil {
		return failure, nil
	}
	marker := boundedSessionScopeFor(exactCtx, sessionID)
	arguments := req.GetArguments()
	for name := range arguments {
		switch name {
		case "session_id", "turn_id", "request_ref":
		default:
			return boundedSessionErrorResult(&marker, "invalid_arguments", "request contains an unknown argument"), nil
		}
	}
	turnID, turnOK := arguments["turn_id"].(string)
	requestRef, requestRefOK := arguments["request_ref"].(string)
	if !turnOK || rlmscope.ValidateTurnID(turnID) != nil ||
		!requestRefOK || !validManagedSessionRequestRef(requestRef) {
		return boundedSessionErrorResult(&marker, "invalid_arguments", "valid turn_id and canonical request_ref are required"), nil
	}
	receipt, fact, err := s.facts.GetSessionTurn(exactCtx, sessionID, turnID)
	if err != nil {
		return boundedSessionErrorResult(&marker, "session_lookup_unavailable", "managed session turn could not be reconciled"), nil
	}
	if receipt == nil && fact == nil {
		return structuredFactPageResult(boundedSessionTurnEnvelope{
			MemoryScope: marker,
			Result:      boundedSessionTurnResult{Version: 1, Found: false},
		}, false), nil
	}
	if err := validateManagedSessionFact(exactCtx, sessionID, fact, requestRef); err != nil {
		if errors.Is(err, memory.ErrSessionTurnConflict) {
			return boundedSessionErrorResult(&marker, "turn_conflict", "turn id is bound to another request"), nil
		}
		return boundedSessionErrorResult(&marker, "session_scope_mismatch", "stored session turn failed exact-boundary validation"), nil
	}
	return structuredFactPageResult(boundedSessionTurnEnvelope{
		MemoryScope: marker,
		Result: boundedSessionTurnResult{
			Version: 1, Found: true, TurnReceipt: receipt, FactID: fact.ID,
		},
	}, false), nil
}

func compactManagedSessionFact(
	ctx context.Context,
	sessionID string,
	fact *memory.Fact,
) (boundedSessionRecallFact, error) {
	if err := validateManagedSessionFact(ctx, sessionID, fact, ""); err != nil {
		return boundedSessionRecallFact{}, err
	}
	return boundedSessionRecallFact{
		ID: fact.ID, TenantID: fact.TenantID, ProjectID: fact.ProjectID,
		SessionID: fact.SessionID, Content: fact.Content, Level: fact.Level,
		Domain: fact.Domain, Module: fact.Module, Origin: fact.Origin,
	}, nil
}

// fullManagedSessionFactSHA256 freezes every persisted field, including fields
// intentionally omitted from the compact response. Some of those hidden fields
// affect eligibility or rank (for example stale/archive, created_at, and the
// embedding), so a compact-frame digest alone cannot prove an unchanged page.
func fullManagedSessionFactSHA256(fact *memory.Fact) (string, error) {
	if fact == nil {
		return "", fmt.Errorf("managed session fact is missing")
	}
	encoded, err := json.Marshal(fact)
	if err != nil || len(encoded) == 0 {
		return "", fmt.Errorf("serialize managed session fact state")
	}
	digest := sha256.Sum256(encoded)
	return hex.EncodeToString(digest[:]), nil
}

func (s *Server) handleSearchScopedSessionFactsPage(
	ctx context.Context,
	req mcp.CallToolRequest,
) (*mcp.CallToolResult, error) {
	exactCtx, sessionID, failure := parseBoundedSessionContext(s, ctx, req)
	if failure != nil {
		return failure, nil
	}
	marker := boundedSessionScopeFor(exactCtx, sessionID)
	arguments := req.GetArguments()
	for name := range arguments {
		switch name {
		case "session_id", "query", "mode", "limit", "max_fact_bytes", "cursor":
		default:
			return boundedSessionErrorResult(&marker, "invalid_arguments", "request contains an unknown argument"), nil
		}
	}
	query, queryOK := arguments["query"].(string)
	mode, modeOK := arguments["mode"].(string)
	if !queryOK || strings.TrimSpace(query) == "" || len(query) > boundedSessionMaxContentBytes ||
		!modeOK || (mode != string(applicationtools.ModeKeyword) &&
		mode != string(applicationtools.ModeSemantic) && mode != string(applicationtools.ModeHybrid)) {
		return boundedSessionErrorResult(&marker, "invalid_arguments", "bounded non-empty query and keyword, semantic, or hybrid mode are required"), nil
	}
	limit, err := exactIntegerArgument(arguments, "limit")
	if err != nil || limit < 1 || limit > 100 {
		return boundedSessionErrorResult(&marker, "invalid_arguments", "limit must be an integer from 1 through 100"), nil
	}
	maxFactBytes, err := exactIntegerArgument(arguments, "max_fact_bytes")
	if err != nil || maxFactBytes < 1 || maxFactBytes > factPageMaxFactBytes {
		return boundedSessionErrorResult(&marker, "invalid_arguments", "max_fact_bytes must be an integer from 1 through 16777216"), nil
	}
	queryDigest := sha256.Sum256([]byte(query))
	querySHA256 := hex.EncodeToString(queryDigest[:])
	cursorToken := ""
	if raw, present := arguments["cursor"]; present {
		value, ok := raw.(string)
		if !ok || value == "" {
			return boundedSessionErrorResult(&marker, "invalid_cursor", "cursor must be a non-empty opaque string"), nil
		}
		cursorToken = value
	}

	var cursor boundedSessionSearchCursor
	var serialized [][]byte
	if cursorToken == "" {
		cursor, serialized, err = s.startBoundedSessionSearch(
			exactCtx, marker, sessionID, query, querySHA256, mode, limit, maxFactBytes,
		)
		if oversized, ok := err.(*boundedSearchFactTooLargeError); ok {
			result := boundedSessionErrorResult(&marker, "fact_too_large", "compact session fact exceeds max_fact_bytes")
			envelope := result.StructuredContent.(boundedSessionErrorEnvelope)
			envelope.Error.FactID = oversized.factID
			envelope.Error.FactBytes = oversized.factBytes
			envelope.Error.MaxFactBytes = maxFactBytes
			result.StructuredContent = envelope
			return result, nil
		}
		if oversized, ok := err.(*boundedSearchStoredOversizeError); ok {
			return boundedSessionStoredOversizedResult(marker, oversized.measurement), nil
		}
		if err != nil {
			return boundedSessionErrorResult(&marker, "search_unavailable", "bounded session search is unavailable"), nil
		}
		if len(cursor.Results) == 0 {
			return structuredFactPageResult(newBoundedSessionSearchEnvelope(marker, maxFactBytes, 0, nil, "", true), false), nil
		}
	} else {
		cursor, err = decodeBoundedSessionCursor(cursorToken, marker, querySHA256, mode, limit, maxFactBytes)
		if err != nil {
			return boundedSessionErrorResult(&marker, "invalid_cursor", "cursor is invalid or does not match this request"), nil
		}
		serialized, err = s.reloadBoundedSessionResults(exactCtx, sessionID, cursor)
		if err != nil {
			return boundedSessionErrorResult(&marker, "page_changed", "frozen session search page changed"), nil
		}
	}

	entry := cursor.Results[cursor.ResultIndex]
	factBytes := serialized[cursor.ResultIndex]
	start := cursor.IntraFactOffset
	end := start + factPageFrameRawBytes
	if end > len(factBytes) {
		end = len(factBytes)
	}
	if start < 0 || start >= len(factBytes) || end <= start {
		return boundedSessionErrorResult(&marker, "invalid_cursor", "cursor does not advance"), nil
	}
	frame := factPageFrame{
		FactID: entry.FactID, SHA256: entry.SHA256, TotalBytes: entry.SerializedSize,
		Offset: start, DataBase64: base64.StdEncoding.EncodeToString(factBytes[start:end]),
		Final: end == len(factBytes),
	}
	nextIndex, nextOffset := cursor.ResultIndex, end
	if nextOffset == len(factBytes) {
		nextIndex++
		nextOffset = 0
	}
	done := nextIndex == len(cursor.Results)
	nextCursor := ""
	if !done {
		cursor.ResultIndex = nextIndex
		cursor.IntraFactOffset = nextOffset
		nextCursor, err = encodeBoundedSessionCursor(cursor)
		if err != nil {
			return boundedSessionErrorResult(&marker, "page_encoding_failed", "continuation cursor could not be encoded"), nil
		}
	}
	return structuredFactPageResult(newBoundedSessionSearchEnvelope(
		marker, maxFactBytes, len(cursor.Results), []factPageFrame{frame}, nextCursor, done,
	), false), nil
}

func (s *Server) startBoundedSessionSearch(
	ctx context.Context,
	marker boundedSessionScope,
	sessionID, query, querySHA256, mode string,
	limit, maxFactBytes int,
) (boundedSessionSearchCursor, [][]byte, error) {
	cursor := boundedSessionSearchCursor{
		Version: boundedSessionProtocolVersion, MemoryScope: marker,
		QuerySHA256: querySHA256, Mode: mode, Limit: limit, MaxFactBytes: maxFactBytes,
		Results: []boundedSessionCursorFact{},
	}
	facts, oversize, err := s.facts.SearchSessionFactsBoundedSnapshot(
		ctx, sessionID, query, limit, applicationtools.SearchMode(mode),
	)
	if err != nil {
		return boundedSessionSearchCursor{}, nil, err
	}
	if oversize != nil {
		return boundedSessionSearchCursor{}, nil, &boundedSearchStoredOversizeError{measurement: oversize}
	}
	serialized := make([][]byte, 0, len(facts))
	seen := make(map[string]struct{}, len(facts))
	for _, fact := range facts {
		compact, err := compactManagedSessionFact(ctx, sessionID, fact)
		if err != nil {
			return boundedSessionSearchCursor{}, nil, err
		}
		if _, duplicate := seen[compact.ID]; duplicate {
			return boundedSessionSearchCursor{}, nil, fmt.Errorf("duplicate ranked session fact id")
		}
		seen[compact.ID] = struct{}{}
		encoded, err := json.Marshal(compact)
		if err != nil || len(encoded) == 0 {
			return boundedSessionSearchCursor{}, nil, fmt.Errorf("serialize ranked session fact")
		}
		if len(encoded) > maxFactBytes {
			return boundedSessionSearchCursor{}, nil, &boundedSearchFactTooLargeError{factID: compact.ID, factBytes: len(encoded)}
		}
		stateSHA256, err := fullManagedSessionFactSHA256(fact)
		if err != nil {
			return boundedSessionSearchCursor{}, nil, err
		}
		digest := sha256.Sum256(encoded)
		cursor.Results = append(cursor.Results, boundedSessionCursorFact{
			FactID: compact.ID, SHA256: hex.EncodeToString(digest[:]),
			StateSHA256: stateSHA256, SerializedSize: len(encoded),
		})
		serialized = append(serialized, encoded)
	}
	return cursor, serialized, nil
}

func (s *Server) reloadBoundedSessionResults(
	ctx context.Context,
	sessionID string,
	cursor boundedSessionSearchCursor,
) ([][]byte, error) {
	ids := make([]string, len(cursor.Results))
	for index, frozen := range cursor.Results {
		ids[index] = frozen.FactID
	}
	facts, oversize, err := s.facts.ReloadSessionFactsBoundedSnapshot(ctx, sessionID, ids)
	if err != nil {
		return nil, err
	}
	if oversize != nil {
		return nil, &boundedSearchStoredOversizeError{measurement: oversize}
	}
	if len(facts) != len(cursor.Results) {
		return nil, fmt.Errorf("frozen session fact count changed")
	}
	serialized := make([][]byte, len(cursor.Results))
	for index, frozen := range cursor.Results {
		fact := facts[index]
		if fact.ID != frozen.FactID {
			return nil, fmt.Errorf("frozen session fact order changed")
		}
		stateSHA256, err := fullManagedSessionFactSHA256(fact)
		if err != nil || !hmac.Equal(
			mustDecodeBoundedSearchDigest(stateSHA256),
			mustDecodeBoundedSearchDigest(frozen.StateSHA256),
		) {
			return nil, fmt.Errorf("frozen session fact state changed")
		}
		compact, err := compactManagedSessionFact(ctx, sessionID, fact)
		if err != nil {
			return nil, err
		}
		encoded, err := json.Marshal(compact)
		if err != nil || len(encoded) != frozen.SerializedSize {
			return nil, fmt.Errorf("frozen session fact size changed")
		}
		digest := sha256.Sum256(encoded)
		if !hmac.Equal(digest[:], mustDecodeBoundedSearchDigest(frozen.SHA256)) {
			return nil, fmt.Errorf("frozen session fact digest changed")
		}
		serialized[index] = encoded
	}
	return serialized, nil
}

func newBoundedSessionSearchEnvelope(
	marker boundedSessionScope,
	maxFactBytes, resultCount int,
	frames []factPageFrame,
	nextCursor string,
	done bool,
) boundedSessionSearchEnvelope {
	if frames == nil {
		frames = []factPageFrame{}
	}
	return boundedSessionSearchEnvelope{
		MemoryScope: marker,
		Page: boundedSessionSearchPage{
			Version: boundedSessionProtocolVersion, Encoding: "base64-json",
			FrameRawLimitBytes: factPageFrameRawBytes, MaxFactBytes: maxFactBytes,
			ResultCount: resultCount, Frames: frames, NextCursor: nextCursor, Done: done,
		},
	}
}

func encodeBoundedSessionCursor(cursor boundedSessionSearchCursor) (string, error) {
	payload, err := json.Marshal(cursor)
	if err != nil {
		return "", err
	}
	mac := hmac.New(sha256.New, factPageCursorMACKey)
	_, _ = mac.Write(payload)
	token := base64.RawURLEncoding.EncodeToString(payload) + "." +
		base64.RawURLEncoding.EncodeToString(mac.Sum(nil))
	if len(token) > boundedSessionMaxCursorBytes {
		return "", fmt.Errorf("cursor exceeds bounded size")
	}
	return token, nil
}

func decodeBoundedSessionCursor(
	token string,
	marker boundedSessionScope,
	querySHA256, mode string,
	limit, maxFactBytes int,
) (boundedSessionSearchCursor, error) {
	var cursor boundedSessionSearchCursor
	if token == "" || len(token) > boundedSessionMaxCursorBytes || strings.Count(token, ".") != 1 {
		return cursor, fmt.Errorf("invalid cursor framing")
	}
	parts := strings.SplitN(token, ".", 2)
	payload, err := base64.RawURLEncoding.DecodeString(parts[0])
	if err != nil || len(payload) == 0 ||
		parts[0] != base64.RawURLEncoding.EncodeToString(payload) {
		return cursor, fmt.Errorf("invalid cursor payload")
	}
	signature, err := base64.RawURLEncoding.DecodeString(parts[1])
	if err != nil || len(signature) != sha256.Size ||
		parts[1] != base64.RawURLEncoding.EncodeToString(signature) {
		return cursor, fmt.Errorf("invalid cursor signature")
	}
	mac := hmac.New(sha256.New, factPageCursorMACKey)
	_, _ = mac.Write(payload)
	if !hmac.Equal(signature, mac.Sum(nil)) {
		return cursor, fmt.Errorf("invalid cursor signature")
	}
	decoder := json.NewDecoder(bytes.NewReader(payload))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(&cursor); err != nil {
		return cursor, fmt.Errorf("invalid cursor object")
	}
	var trailing any
	if err := decoder.Decode(&trailing); err != io.EOF {
		return cursor, fmt.Errorf("invalid cursor trailing data")
	}
	canonical, err := json.Marshal(cursor)
	if err != nil || !bytes.Equal(payload, canonical) {
		return cursor, fmt.Errorf("cursor is not canonical")
	}
	if cursor.Version != boundedSessionProtocolVersion || cursor.MemoryScope != marker ||
		cursor.QuerySHA256 != querySHA256 || cursor.Mode != mode || cursor.Limit != limit ||
		cursor.MaxFactBytes != maxFactBytes || !validBoundedSearchDigest(cursor.QuerySHA256) ||
		len(cursor.Results) == 0 || len(cursor.Results) > limit ||
		cursor.ResultIndex < 0 || cursor.ResultIndex >= len(cursor.Results) {
		return cursor, fmt.Errorf("cursor does not match request")
	}
	seen := make(map[string]struct{}, len(cursor.Results))
	for _, fact := range cursor.Results {
		if fact.FactID == "" || len(fact.FactID) > 256 ||
			!validBoundedSearchDigest(fact.SHA256) ||
			!validBoundedSearchDigest(fact.StateSHA256) || fact.SerializedSize < 1 ||
			fact.SerializedSize > maxFactBytes {
			return cursor, fmt.Errorf("cursor result is invalid")
		}
		if _, duplicate := seen[fact.FactID]; duplicate {
			return cursor, fmt.Errorf("cursor result is duplicated")
		}
		seen[fact.FactID] = struct{}{}
	}
	currentSize := cursor.Results[cursor.ResultIndex].SerializedSize
	if cursor.IntraFactOffset < 0 || cursor.IntraFactOffset >= currentSize ||
		(cursor.ResultIndex == 0 && cursor.IntraFactOffset == 0) {
		return cursor, fmt.Errorf("cursor makes no progress")
	}
	return cursor, nil
}
