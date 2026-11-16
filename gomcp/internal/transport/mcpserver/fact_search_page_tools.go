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
	"unicode"
	"unicode/utf8"

	"github.com/mark3labs/mcp-go/mcp"

	applicationtools "github.com/syntrex/gomcp/internal/application/tools"
	"github.com/syntrex/gomcp/internal/domain/memory"
	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
)

const (
	boundedSearchProtocolVersion = 1
	boundedSearchMaxCursorBytes  = 64 * 1024
	boundedSearchMaxQueryBytes   = 64 * 1024
	boundedSearchMaxQueryTerms   = 64
	boundedSearchMaxTermBytes    = 4 * 1024
)

type boundedSearchQueryLimitError struct {
	distinctTerms   int
	maxTerms        int
	normalizedBytes int
	maxBytes        int
}

func (e *boundedSearchQueryLimitError) Error() string {
	return "bounded search query exceeds the work limit"
}

type boundedSearchCursorFact struct {
	FactID         string `json:"fact_id"`
	SHA256         string `json:"sha256"`
	SerializedSize int    `json:"serialized_size"`
}

type boundedSearchCursor struct {
	Version         int                 `json:"version"`
	SnapshotID      string              `json:"snapshot_id"`
	MemoryScope     factPageMemoryScope `json:"memory_scope"`
	QuerySHA256     string              `json:"query_sha256"`
	Mode            string              `json:"mode"`
	Limit           int                 `json:"limit"`
	MaxFactBytes    int                 `json:"max_fact_bytes"`
	ExpiresAtUnix   int64               `json:"expires_at_unix"`
	ResultIndex     int                 `json:"result_index"`
	IntraFactOffset int                 `json:"intra_fact_offset"`
	CallIndex       int                 `json:"call_index"`
}

type boundedSearchPage struct {
	Version            int             `json:"version"`
	Encoding           string          `json:"encoding"`
	FrameRawLimitBytes int             `json:"frame_raw_limit_bytes"`
	MaxFactBytes       int             `json:"max_fact_bytes"`
	ResultCount        int             `json:"result_count"`
	Frames             []factPageFrame `json:"frames"`
	NextCursor         string          `json:"next_cursor,omitempty"`
	Done               bool            `json:"done"`
}

type boundedSearchEnvelope struct {
	MemoryScope factPageMemoryScope `json:"memory_scope"`
	Page        boundedSearchPage   `json:"page"`
}

// registerBoundedSearchTools is intentionally additive. The caller wires it
// alongside the legacy fact tools; search_facts and its text response are not
// changed by this protocol.
func (s *Server) registerBoundedSearchTools() {
	s.mcp.AddTool(
		mcp.NewTool("search_default_facts_page",
			mcp.WithDescription("Search local/default non-session facts in bounded base rank order, returning one base64 frame. Hybrid mode excludes legacy synapse expansion. Scope headers, arguments, and _meta overrides are rejected."),
			mcp.WithString("query", mcp.Description("Non-empty search query"), mcp.Required()),
			mcp.WithString("mode", mcp.Description("Search mode: keyword, semantic, or hybrid"), mcp.Enum("keyword", "semantic", "hybrid"), mcp.Required()),
			mcp.WithNumber("limit", mcp.Description("Maximum ranked results (1-100)"), mcp.Min(1), mcp.Max(100), mcp.MultipleOf(1), mcp.Required()),
			mcp.WithNumber("max_fact_bytes", mcp.Description("Maximum serialized bytes accepted for one fact (1-16777216)"), mcp.Min(1), mcp.Max(factPageMaxFactBytes), mcp.MultipleOf(1), mcp.Required()),
			mcp.WithString("cursor", mcp.Description("Opaque continuation cursor returned by the previous page")),
		),
		s.handleSearchDefaultFactsPage,
	)

	s.mcp.AddTool(
		mcp.NewTool("search_project_facts_page",
			mcp.WithDescription("Search one exact non-default project's non-session facts in bounded base rank order, returning one base64 frame. Hybrid mode excludes legacy synapse expansion. Requires explicit _meta.rlm_scope."),
			mcp.WithString("query", mcp.Description("Non-empty search query"), mcp.Required()),
			mcp.WithString("mode", mcp.Description("Search mode: keyword, semantic, or hybrid"), mcp.Enum("keyword", "semantic", "hybrid"), mcp.Required()),
			mcp.WithNumber("limit", mcp.Description("Maximum ranked results (1-100)"), mcp.Min(1), mcp.Max(100), mcp.MultipleOf(1), mcp.Required()),
			mcp.WithNumber("max_fact_bytes", mcp.Description("Maximum serialized bytes accepted for one fact (1-16777216)"), mcp.Min(1), mcp.Max(factPageMaxFactBytes), mcp.MultipleOf(1), mcp.Required()),
			mcp.WithString("cursor", mcp.Description("Opaque continuation cursor returned by the previous page")),
		),
		s.handleSearchProjectFactsPage,
	)
}

func (s *Server) handleSearchDefaultFactsPage(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	sc := rlmscope.Default()
	if requestHasFactPageScopeOverride(req) {
		return factPageErrorResult(&sc, "scope_override_forbidden", "default fact search does not accept scope overrides"), nil
	}
	defaultCtx, sc, err := s.defaultScopeContext(ctx)
	if err != nil {
		return factPageErrorResult(&sc, "scope_override_forbidden", err.Error()), nil
	}
	return s.handleSearchFactsPageForScope(defaultCtx, sc, req)
}

func (s *Server) handleSearchProjectFactsPage(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	explicitCtx, sc, err := s.explicitMetaScopeContext(ctx, req)
	if err != nil {
		return factPageErrorResult(nil, "invalid_scope", err.Error()), nil
	}
	if _, err := rlmscope.RequireExactProject(explicitCtx); err != nil {
		return factPageErrorResult(&sc, "invalid_scope", err.Error()), nil
	}
	return s.handleSearchFactsPageForScope(explicitCtx, sc, req)
}

func (s *Server) handleSearchFactsPageForScope(
	ctx context.Context,
	sc rlmscope.Scope,
	req mcp.CallToolRequest,
) (*mcp.CallToolResult, error) {
	arguments := req.GetArguments()
	for name := range arguments {
		switch name {
		case "query", "mode", "limit", "max_fact_bytes", "cursor":
		default:
			return factPageErrorResult(&sc, "invalid_arguments", "request contains an unknown argument"), nil
		}
	}

	query, ok := arguments["query"].(string)
	if !ok || strings.TrimSpace(query) == "" {
		return factPageErrorResult(&sc, "invalid_arguments", "query must be a non-empty string"), nil
	}
	if len(query) > boundedSearchMaxQueryBytes {
		return factPageErrorResult(&sc, "invalid_arguments", "query must not exceed 65536 UTF-8 bytes"), nil
	}
	mode, ok := arguments["mode"].(string)
	if !ok || (mode != string(applicationtools.ModeKeyword) &&
		mode != string(applicationtools.ModeSemantic) && mode != string(applicationtools.ModeHybrid)) {
		return factPageErrorResult(&sc, "invalid_arguments", "mode must be keyword, semantic, or hybrid"), nil
	}
	if mode != string(applicationtools.ModeSemantic) {
		if err := validateBoundedSearchQueryWork(query); err != nil {
			return factPageErrorResult(&sc, "query_work_limit_exceeded", "query exceeds the bounded-search work limit"), nil
		}
	}
	limit, err := exactIntegerArgument(arguments, "limit")
	if err != nil || limit < 1 || limit > 100 {
		return factPageErrorResult(&sc, "invalid_arguments", "limit must be an integer from 1 through 100"), nil
	}
	maxFactBytes, err := exactIntegerArgument(arguments, "max_fact_bytes")
	if err != nil || maxFactBytes < 1 || maxFactBytes > factPageMaxFactBytes {
		return factPageErrorResult(&sc, "invalid_arguments", "max_fact_bytes must be an integer from 1 through 16777216"), nil
	}

	queryDigest := sha256.Sum256([]byte(query))
	querySHA256 := hex.EncodeToString(queryDigest[:])
	cursorToken := ""
	if raw, present := arguments["cursor"]; present {
		value, ok := raw.(string)
		if !ok || value == "" {
			return factPageErrorResult(&sc, "invalid_cursor", "cursor must be a non-empty opaque string"), nil
		}
		cursorToken = value
	}

	var (
		cursor           boundedSearchCursor
		currentFactBytes []byte
	)
	if cursorToken == "" {
		cursor, currentFactBytes, err = s.startBoundedSearch(ctx, sc, query, querySHA256, mode, limit, maxFactBytes)
		if oversized, ok := err.(*boundedSearchFactTooLargeError); ok {
			return factPageOversizedResult(sc, oversized.factID, oversized.factBytes, maxFactBytes), nil
		}
		if oversized, ok := err.(*boundedSearchStoredOversizeError); ok {
			return boundedSearchStoredOversizedResult(sc, oversized.measurement), nil
		}
		var capacity *boundedSearchSnapshotCapacityError
		if errors.As(err, &capacity) {
			return factPageErrorResult(&sc, "search_capacity", "bounded search snapshot capacity is exhausted"), nil
		}
		if err != nil {
			return factPageErrorResult(&sc, "search_unavailable", "bounded fact search is unavailable"), nil
		}
		if cursor.SnapshotID == "" {
			return structuredFactPageResult(newBoundedSearchEnvelope(sc, maxFactBytes, 0, nil, "", true), false), nil
		}
	} else {
		cursor, err = decodeBoundedSearchCursor(cursorToken, sc, querySHA256, mode, limit, maxFactBytes)
		if err != nil {
			return factPageErrorResult(&sc, "invalid_cursor", "cursor is invalid or does not match this request"), nil
		}
	}

	frame, nextCursor, done, resultCount, err := s.emitBoundedSearchFrame(ctx, sc, cursor, currentFactBytes)
	if err != nil {
		var expired *boundedSearchSnapshotExpiredError
		var invalid *boundedSearchSnapshotCursorError
		var changed *boundedSearchPageChangedError
		var work *boundedSearchSnapshotWorkError
		var capacity *boundedSearchSnapshotCapacityError
		switch {
		case errors.As(err, &expired):
			return factPageErrorResult(&sc, "page_expired", "bounded search snapshot expired"), nil
		case errors.As(err, &invalid):
			return factPageErrorResult(&sc, "invalid_cursor", "cursor is invalid or does not match this request"), nil
		case errors.As(err, &changed):
			return factPageErrorResult(&sc, "page_changed", "frozen search page changed"), nil
		case errors.As(err, &work):
			return factPageErrorResult(&sc, "search_work_limit_exceeded", "bounded search snapshot exhausted its work budget"), nil
		case errors.As(err, &capacity):
			return factPageErrorResult(&sc, "search_capacity", "bounded search snapshot capacity is exhausted"), nil
		default:
			return factPageErrorResult(&sc, "page_encoding_failed", "continuation cursor could not be encoded"), nil
		}
	}

	return structuredFactPageResult(newBoundedSearchEnvelope(
		sc, maxFactBytes, resultCount, []factPageFrame{frame}, nextCursor, done,
	), false), nil
}

type boundedSearchPageChangedError struct{}

func (*boundedSearchPageChangedError) Error() string {
	return "frozen bounded search result changed"
}

func validateBoundedSearchQueryWork(query string) error {
	fields := strings.FieldsFunc(strings.ToLower(query), func(r rune) bool {
		return !unicode.IsLetter(r) && !unicode.IsDigit(r)
	})
	seen := make(map[string]struct{}, len(fields))
	distinctTerms := 0
	normalizedBytes := 0
	for _, field := range fields {
		if utf8.RuneCountInString(field) < 3 {
			continue
		}
		if _, duplicate := seen[field]; duplicate {
			continue
		}
		seen[field] = struct{}{}
		distinctTerms++
		normalizedBytes += len(field)
		if distinctTerms > boundedSearchMaxQueryTerms || normalizedBytes > boundedSearchMaxTermBytes {
			return &boundedSearchQueryLimitError{
				distinctTerms: distinctTerms, maxTerms: boundedSearchMaxQueryTerms,
				normalizedBytes: normalizedBytes, maxBytes: boundedSearchMaxTermBytes,
			}
		}
	}
	return nil
}

type boundedSearchFactTooLargeError struct {
	factID    string
	factBytes int
}

func (e *boundedSearchFactTooLargeError) Error() string {
	return "serialized fact exceeds max_fact_bytes"
}

type boundedSearchStoredOversizeError struct {
	measurement *memory.BoundedSearchStoredOversize
}

func (e *boundedSearchStoredOversizeError) Error() string {
	return "stored data exceeds a bounded search hard limit"
}

type boundedSearchStoredLimitError struct {
	Code                   string `json:"code"`
	Message                string `json:"message"`
	StoredIdentityBytes    int64  `json:"stored_identity_bytes,omitempty"`
	MaxStoredIdentityBytes int64  `json:"max_stored_identity_bytes,omitempty"`
	StoredVariableBytes    int64  `json:"stored_variable_bytes,omitempty"`
	MaxStoredVariableBytes int64  `json:"max_stored_variable_bytes,omitempty"`
	StoredTotalBytes       int64  `json:"stored_total_bytes,omitempty"`
	MaxStoredTotalBytes    int64  `json:"max_stored_total_bytes,omitempty"`
	StoredRows             int64  `json:"stored_rows,omitempty"`
	MaxStoredRows          int64  `json:"max_stored_rows,omitempty"`
}

type boundedSearchStoredLimitEnvelope struct {
	MemoryScope factPageMemoryScope           `json:"memory_scope"`
	Error       boundedSearchStoredLimitError `json:"error"`
}

func boundedSearchStoredOversizedResult(
	sc rlmscope.Scope,
	measurement *memory.BoundedSearchStoredOversize,
) *mcp.CallToolResult {
	marker := factPageScope(sc)
	wireError := boundedSearchStoredLimitError{}
	if measurement == nil {
		wireError.Code = "stored_search_unavailable"
		wireError.Message = "stored bounded-search measurement is unavailable"
	} else {
		switch measurement.Kind {
		case memory.BoundedSearchStoredIdentityOversizeKind:
			wireError.Code = "stored_fact_identity_too_large"
			wireError.Message = "stored fact identity exceeds the bounded-search hard limit"
			wireError.StoredIdentityBytes = measurement.StoredBytes
			wireError.MaxStoredIdentityBytes = measurement.MaxStoredBytes
		case memory.BoundedSearchStoredScopeOversizeKind:
			wireError.Code = "stored_search_scope_too_large"
			wireError.Message = "stored search scope exceeds the bounded-search aggregate hard limit"
			wireError.StoredTotalBytes = measurement.StoredBytes
			wireError.MaxStoredTotalBytes = measurement.MaxStoredBytes
		case memory.BoundedSearchStoredRowCountOversizeKind:
			wireError.Code = "stored_search_scope_too_large"
			wireError.Message = "stored search scope row count exceeds the hard limit"
			wireError.StoredRows = measurement.StoredRows
			wireError.MaxStoredRows = measurement.MaxStoredRows
		default:
			wireError.Code = "stored_fact_too_large"
			wireError.Message = "stored fact variable columns exceed the bounded-search hard limit"
			wireError.StoredVariableBytes = measurement.StoredBytes
			wireError.MaxStoredVariableBytes = measurement.MaxStoredBytes
		}
	}
	return structuredFactPageResult(boundedSearchStoredLimitEnvelope{
		MemoryScope: marker,
		Error:       wireError,
	}, true)
}

func (s *Server) startBoundedSearch(
	ctx context.Context,
	sc rlmscope.Scope,
	query, querySHA256, mode string,
	limit, maxFactBytes int,
) (boundedSearchCursor, []byte, error) {
	cursor := boundedSearchCursor{
		Version:      boundedSearchProtocolVersion,
		MemoryScope:  factPageScope(sc),
		QuerySHA256:  querySHA256,
		Mode:         mode,
		Limit:        limit,
		MaxFactBytes: maxFactBytes,
	}
	snapshot, err := processBoundedSearchSnapshots.reserve(
		s, sc, querySHA256, mode, limit, maxFactBytes,
	)
	if err != nil {
		return boundedSearchCursor{}, nil, err
	}
	keepSnapshot := false
	defer func() {
		if !keepSnapshot {
			processBoundedSearchSnapshots.close(snapshot)
		}
	}()

	facts, oversize, err := s.facts.SearchFactsBoundedSnapshot(ctx, query, limit, applicationtools.SearchMode(mode))
	if err != nil {
		return boundedSearchCursor{}, nil, err
	}
	if oversize != nil {
		return boundedSearchCursor{}, nil, &boundedSearchStoredOversizeError{measurement: oversize}
	}
	var currentFactBytes []byte
	results := make([]boundedSearchCursorFact, 0, len(facts))
	seen := make(map[string]struct{}, len(facts))
	for _, fact := range facts {
		if err := validateBoundedSearchFact(sc, fact); err != nil {
			return boundedSearchCursor{}, nil, err
		}
		if _, duplicate := seen[fact.ID]; duplicate {
			return boundedSearchCursor{}, nil, fmt.Errorf("duplicate ranked fact id")
		}
		seen[fact.ID] = struct{}{}
		encoded, err := json.Marshal(fact)
		if err != nil || len(encoded) == 0 {
			return boundedSearchCursor{}, nil, fmt.Errorf("serialize ranked fact")
		}
		if len(encoded) > maxFactBytes {
			return boundedSearchCursor{}, nil, &boundedSearchFactTooLargeError{factID: fact.ID, factBytes: len(encoded)}
		}
		digest := sha256.Sum256(encoded)
		if len(results) == 0 {
			currentFactBytes = encoded
		}
		results = append(results, boundedSearchCursorFact{
			FactID:         fact.ID,
			SHA256:         hex.EncodeToString(digest[:]),
			SerializedSize: len(encoded),
		})
	}
	if len(results) == 0 {
		return cursor, nil, nil
	}
	if err := processBoundedSearchSnapshots.activate(snapshot, results, currentFactBytes); err != nil {
		return boundedSearchCursor{}, nil, err
	}
	keepSnapshot = true
	cursor.SnapshotID = snapshot.id
	cursor.ExpiresAtUnix = snapshot.expiresAtUnix
	return cursor, currentFactBytes, nil
}

func (s *Server) reloadBoundedSearchResult(
	ctx context.Context,
	sc rlmscope.Scope,
	frozen boundedSearchCursorFact,
) ([]byte, error) {
	facts, oversize, err := s.facts.ReloadFactsBoundedSnapshot(ctx, []string{frozen.FactID})
	if err != nil {
		return nil, err
	}
	if oversize != nil {
		return nil, &boundedSearchStoredOversizeError{measurement: oversize}
	}
	if len(facts) != 1 {
		return nil, fmt.Errorf("frozen fact is unavailable")
	}
	fact := facts[0]
	if validateBoundedSearchFact(sc, fact) != nil || fact.ID != frozen.FactID {
		return nil, fmt.Errorf("reload frozen fact")
	}
	encoded, err := json.Marshal(fact)
	if err != nil || len(encoded) != frozen.SerializedSize {
		return nil, fmt.Errorf("frozen fact size changed")
	}
	digest := sha256.Sum256(encoded)
	if !hmac.Equal(digest[:], mustDecodeBoundedSearchDigest(frozen.SHA256)) {
		return nil, fmt.Errorf("frozen fact digest changed")
	}
	return encoded, nil
}

func (s *Server) emitBoundedSearchFrame(
	ctx context.Context,
	sc rlmscope.Scope,
	cursor boundedSearchCursor,
	currentFactBytes []byte,
) (factPageFrame, string, bool, int, error) {
	snapshot, err := processBoundedSearchSnapshots.lock(s, cursor)
	if err != nil {
		return factPageFrame{}, "", false, 0, err
	}
	resultCount := len(snapshot.results)
	entry := snapshot.results[cursor.ResultIndex]
	if snapshot.payload != nil {
		if snapshot.payload.resultIndex != cursor.ResultIndex ||
			len(snapshot.payload.serialized) != entry.SerializedSize {
			wipeBoundedSearchSnapshotLocked(snapshot)
			snapshot.mu.Unlock()
			processBoundedSearchSnapshots.close(snapshot)
			return factPageFrame{}, "", false, 0, &boundedSearchPageChangedError{}
		}
		currentFactBytes = snapshot.payload.serialized
	} else if currentFactBytes == nil {
		if err := processBoundedSearchSnapshots.reservePayloadLocked(snapshot, int64(entry.SerializedSize)); err != nil {
			snapshot.mu.Unlock()
			return factPageFrame{}, "", false, 0, err
		}
		currentFactBytes, err = s.reloadBoundedSearchResult(ctx, sc, entry)
		if err == nil {
			snapshot.payload = &boundedSearchCachedPayload{
				resultIndex: cursor.ResultIndex,
				serialized:  currentFactBytes,
			}
		}
	}
	if err != nil || len(currentFactBytes) != entry.SerializedSize {
		wipeBoundedSearchSnapshotLocked(snapshot)
		snapshot.mu.Unlock()
		processBoundedSearchSnapshots.close(snapshot)
		return factPageFrame{}, "", false, 0, &boundedSearchPageChangedError{}
	}
	start := cursor.IntraFactOffset
	end := start + factPageFrameRawBytes
	if end > len(currentFactBytes) {
		end = len(currentFactBytes)
	}
	if start < 0 || start >= len(currentFactBytes) || end <= start ||
		snapshot.bytesEmitted+int64(end-start) > snapshot.maxBytes {
		snapshot.mu.Unlock()
		return factPageFrame{}, "", false, 0, &boundedSearchSnapshotWorkError{}
	}
	frame := factPageFrame{
		FactID: entry.FactID, SHA256: entry.SHA256, TotalBytes: entry.SerializedSize,
		Offset: start, DataBase64: base64.StdEncoding.EncodeToString(currentFactBytes[start:end]),
		Final: end == len(currentFactBytes),
	}
	nextIndex, nextOffset := cursor.ResultIndex, end
	if nextOffset == len(currentFactBytes) {
		nextIndex++
		nextOffset = 0
	}
	done := nextIndex == resultCount
	nextCursor := ""
	nextCall := cursor.CallIndex + 1
	if !done {
		next := cursor
		next.ResultIndex = nextIndex
		next.IntraFactOffset = nextOffset
		next.CallIndex = nextCall
		nextCursor, err = encodeBoundedSearchCursor(next)
		if err != nil {
			snapshot.mu.Unlock()
			return factPageFrame{}, "", false, 0, err
		}
	}
	snapshot.callsUsed++
	snapshot.bytesEmitted += int64(end - start)
	snapshot.expectedResult = nextIndex
	snapshot.expectedOffset = nextOffset
	snapshot.expectedCall = nextCall
	if frame.Final && snapshot.payload != nil && snapshot.payload.resultIndex == cursor.ResultIndex {
		processBoundedSearchSnapshots.releasePayloadLocked(snapshot)
	}
	if done {
		wipeBoundedSearchSnapshotLocked(snapshot)
	}
	snapshot.mu.Unlock()
	if done {
		processBoundedSearchSnapshots.close(snapshot)
	}
	return frame, nextCursor, done, resultCount, nil
}

func validateBoundedSearchFact(sc rlmscope.Scope, fact *memory.Fact) error {
	if fact == nil || fact.ID == "" || len(fact.ID) > 256 || fact.TenantID != sc.TenantID ||
		fact.ProjectID != sc.ProjectID || fact.SessionID != "" {
		return fmt.Errorf("ranked fact is outside the exact project boundary")
	}
	return nil
}

func mustDecodeBoundedSearchDigest(value string) []byte {
	decoded, _ := hex.DecodeString(value)
	return decoded
}

func newBoundedSearchEnvelope(
	sc rlmscope.Scope,
	maxFactBytes, resultCount int,
	frames []factPageFrame,
	nextCursor string,
	done bool,
) boundedSearchEnvelope {
	if frames == nil {
		frames = []factPageFrame{}
	}
	return boundedSearchEnvelope{
		MemoryScope: factPageScope(sc),
		Page: boundedSearchPage{
			Version:            boundedSearchProtocolVersion,
			Encoding:           "base64-json",
			FrameRawLimitBytes: factPageFrameRawBytes,
			MaxFactBytes:       maxFactBytes,
			ResultCount:        resultCount,
			Frames:             frames,
			NextCursor:         nextCursor,
			Done:               done,
		},
	}
}

func encodeBoundedSearchCursor(cursor boundedSearchCursor) (string, error) {
	// The MAC key is intentionally process-local. A cursor from another
	// process (including one issued before restart) is invalid, so callers
	// must restart the search from its first page instead of resuming against
	// a different frozen in-memory trust boundary.
	payload, err := json.Marshal(cursor)
	if err != nil {
		return "", fmt.Errorf("encode cursor payload: %w", err)
	}
	mac := hmac.New(sha256.New, factPageCursorMACKey)
	_, _ = mac.Write(payload)
	token := base64.RawURLEncoding.EncodeToString(payload) + "." +
		base64.RawURLEncoding.EncodeToString(mac.Sum(nil))
	if len(token) > boundedSearchMaxCursorBytes {
		return "", fmt.Errorf("cursor exceeds %d bytes", boundedSearchMaxCursorBytes)
	}
	return token, nil
}

func decodeBoundedSearchCursor(
	token string,
	sc rlmscope.Scope,
	querySHA256, mode string,
	limit, maxFactBytes int,
) (boundedSearchCursor, error) {
	var cursor boundedSearchCursor
	if token == "" || len(token) > boundedSearchMaxCursorBytes || strings.Count(token, ".") != 1 {
		return cursor, fmt.Errorf("invalid cursor framing")
	}
	parts := strings.SplitN(token, ".", 2)
	payload, err := base64.RawURLEncoding.DecodeString(parts[0])
	if err != nil || len(payload) == 0 || parts[0] != base64.RawURLEncoding.EncodeToString(payload) {
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
	if err := validateBoundedSearchCursor(cursor, sc, querySHA256, mode, limit, maxFactBytes); err != nil {
		return cursor, err
	}
	return cursor, nil
}

func validateBoundedSearchCursor(
	cursor boundedSearchCursor,
	sc rlmscope.Scope,
	querySHA256, mode string,
	limit, maxFactBytes int,
) error {
	if cursor.Version != boundedSearchProtocolVersion || cursor.MemoryScope != factPageScope(sc) ||
		cursor.QuerySHA256 != querySHA256 || cursor.Mode != mode || cursor.Limit != limit ||
		cursor.MaxFactBytes != maxFactBytes {
		return fmt.Errorf("cursor does not match request scope or bounds")
	}
	if !validBoundedSearchDigest(cursor.QuerySHA256) {
		return fmt.Errorf("cursor query digest is invalid")
	}
	if !validBoundedSearchSnapshotID(cursor.SnapshotID) || cursor.ExpiresAtUnix <= 0 ||
		cursor.ResultIndex < 0 || cursor.ResultIndex >= cursor.Limit || cursor.CallIndex < 1 {
		return fmt.Errorf("cursor result position is invalid")
	}
	if cursor.IntraFactOffset < 0 || cursor.IntraFactOffset >= cursor.MaxFactBytes {
		return fmt.Errorf("cursor makes no progress")
	}
	return nil
}

func validBoundedSearchDigest(value string) bool {
	if len(value) != sha256.Size*2 || value != strings.ToLower(value) {
		return false
	}
	decoded, err := hex.DecodeString(value)
	return err == nil && len(decoded) == sha256.Size
}
