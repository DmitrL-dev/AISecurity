package mcpserver

import (
	"bytes"
	"context"
	"crypto/hmac"
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"math"
	"strings"

	"github.com/mark3labs/mcp-go/mcp"

	"github.com/syntrex/gomcp/internal/domain/memory"
	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
)

const (
	factPageProtocolVersion = 1
	factPageFrameRawBytes   = 512 * 1024
	factPageMaxFactBytes    = memory.FactPageMaxSerializedBytes
	factPageMaxCursorBytes  = 8 * 1024
)

var factPageCursorMACKey = func() []byte {
	key := make([]byte, sha256.Size)
	if _, err := rand.Read(key); err != nil {
		panic(fmt.Sprintf("initialize fact page cursor key: %v", err))
	}
	return key
}()

type factPageMemoryScope struct {
	Version   int    `json:"version"`
	Kind      string `json:"kind"`
	TenantID  string `json:"tenant_id"`
	ProjectID string `json:"project_id"`
}

type factPageFrame struct {
	FactID     string `json:"fact_id"`
	SHA256     string `json:"sha256"`
	TotalBytes int    `json:"total_bytes"`
	Offset     int    `json:"offset"`
	DataBase64 string `json:"data_base64"`
	Final      bool   `json:"final"`
}

type factPagePayload struct {
	Version            int             `json:"version"`
	Encoding           string          `json:"encoding"`
	FrameRawLimitBytes int             `json:"frame_raw_limit_bytes"`
	MaxFactBytes       int             `json:"max_fact_bytes"`
	ExpectedCount      int64           `json:"expected_count"`
	Frames             []factPageFrame `json:"frames"`
	NextCursor         string          `json:"next_cursor,omitempty"`
	Done               bool            `json:"done"`
}

type factPageEnvelope struct {
	MemoryScope factPageMemoryScope `json:"memory_scope"`
	Page        factPagePayload     `json:"page"`
}

type factPageError struct {
	Code         string `json:"code"`
	Message      string `json:"message"`
	FactID       string `json:"fact_id,omitempty"`
	FactBytes    int    `json:"fact_bytes,omitempty"`
	MaxFactBytes int    `json:"max_fact_bytes,omitempty"`
}

type factPageErrorEnvelope struct {
	MemoryScope *factPageMemoryScope `json:"memory_scope,omitempty"`
	Error       factPageError        `json:"error"`
}

type factPageCursorFact struct {
	Key        memory.FactPageKey `json:"key"`
	FactID     string             `json:"fact_id"`
	SHA256     string             `json:"sha256"`
	TotalBytes int                `json:"total_bytes"`
	Offset     int                `json:"offset"`
	HasMore    bool               `json:"has_more"`
}

type factPageCursor struct {
	Version       int                 `json:"version"`
	TenantID      string              `json:"tenant_id"`
	ProjectID     string              `json:"project_id"`
	Level         int                 `json:"level"`
	MaxFactBytes  int                 `json:"max_fact_bytes"`
	Snapshot      int64               `json:"snapshot"`
	ExpectedCount int64               `json:"expected_count"`
	After         *memory.FactPageKey `json:"after,omitempty"`
	Fact          *factPageCursorFact `json:"fact,omitempty"`
}

func factPageScope(sc rlmscope.Scope) factPageMemoryScope {
	return factPageMemoryScope{
		Version:   1,
		Kind:      "project",
		TenantID:  sc.TenantID,
		ProjectID: sc.ProjectID,
	}
}

func structuredFactPageResult(payload any, isError bool) *mcp.CallToolResult {
	return &mcp.CallToolResult{
		Content:           []mcp.Content{},
		StructuredContent: payload,
		IsError:           isError,
	}
}

func factPageErrorResult(sc *rlmscope.Scope, code, message string) *mcp.CallToolResult {
	var marker *factPageMemoryScope
	if sc != nil {
		value := factPageScope(*sc)
		marker = &value
	}
	return structuredFactPageResult(factPageErrorEnvelope{
		MemoryScope: marker,
		Error: factPageError{
			Code:    code,
			Message: message,
		},
	}, true)
}

func factPageOversizedResult(sc rlmscope.Scope, factID string, factBytes, maxFactBytes int) *mcp.CallToolResult {
	return structuredFactPageResult(factPageErrorEnvelope{
		MemoryScope: func() *factPageMemoryScope {
			marker := factPageScope(sc)
			return &marker
		}(),
		Error: factPageError{
			Code:         "fact_too_large",
			Message:      "serialized fact exceeds max_fact_bytes",
			FactID:       factID,
			FactBytes:    factBytes,
			MaxFactBytes: maxFactBytes,
		},
	}, true)
}

func exactIntegerArgument(arguments map[string]any, name string) (int, error) {
	raw, ok := arguments[name]
	if !ok {
		return 0, fmt.Errorf("%s is required", name)
	}
	var value int64
	switch typed := raw.(type) {
	case float64:
		if math.IsNaN(typed) || math.IsInf(typed, 0) || math.Trunc(typed) != typed ||
			typed < math.MinInt64 || typed > math.MaxInt64 {
			return 0, fmt.Errorf("%s must be an integer", name)
		}
		value = int64(typed)
	case int:
		value = int64(typed)
	case int64:
		value = typed
	case json.Number:
		parsed, err := typed.Int64()
		if err != nil {
			return 0, fmt.Errorf("%s must be an integer", name)
		}
		value = parsed
	default:
		return 0, fmt.Errorf("%s must be an integer", name)
	}
	if int64(int(value)) != value {
		return 0, fmt.Errorf("%s is out of range", name)
	}
	return int(value), nil
}

func validateFactPageKey(key memory.FactPageKey) error {
	if key.ID == "" || key.ID != strings.TrimSpace(key.ID) || len(key.ID) > 256 {
		return fmt.Errorf("invalid key id")
	}
	if key.CreatedAt == "" || key.CreatedAt != strings.TrimSpace(key.CreatedAt) || len(key.CreatedAt) > 128 {
		return fmt.Errorf("invalid key created_at")
	}
	for index := 0; index < len(key.CreatedAt); index++ {
		if key.CreatedAt[index] < 0x20 || key.CreatedAt[index] > 0x7e {
			return fmt.Errorf("invalid key created_at")
		}
	}
	if len(key.SnapshotID) != memory.FactPageSnapshotIDBytes*2 || key.Sequence <= 0 ||
		key.Ordinal < 0 || key.ExpiresAtUnix <= 0 || key.MaxCalls <= 0 {
		return fmt.Errorf("invalid key snapshot position")
	}
	decodedSnapshotID, err := hex.DecodeString(key.SnapshotID)
	if err != nil || len(decodedSnapshotID) != memory.FactPageSnapshotIDBytes ||
		key.SnapshotID != hex.EncodeToString(decodedSnapshotID) {
		return fmt.Errorf("invalid key snapshot identity")
	}
	return nil
}

func compareFactPageKeys(left, right memory.FactPageKey) int {
	if left.CreatedAt < right.CreatedAt {
		return -1
	}
	if left.CreatedAt > right.CreatedAt {
		return 1
	}
	return strings.Compare(left.ID, right.ID)
}

func validateFactPageCursor(cursor factPageCursor, sc rlmscope.Scope, level, maxFactBytes int) error {
	if cursor.Version != factPageProtocolVersion || cursor.TenantID != sc.TenantID ||
		cursor.ProjectID != sc.ProjectID || cursor.Level != level ||
		cursor.MaxFactBytes != maxFactBytes || cursor.Snapshot <= 0 || cursor.ExpectedCount <= 0 {
		return fmt.Errorf("cursor does not match request scope or bounds")
	}
	if cursor.After != nil {
		if err := validateFactPageKey(*cursor.After); err != nil {
			return err
		}
	}
	if cursor.Fact == nil {
		if cursor.After == nil {
			return fmt.Errorf("cursor makes no progress")
		}
		return nil
	}
	fact := cursor.Fact
	if err := validateFactPageKey(fact.Key); err != nil {
		return err
	}
	if fact.FactID != fact.Key.ID || len(fact.SHA256) != sha256.Size*2 {
		return fmt.Errorf("cursor fact identity is invalid")
	}
	if _, err := hex.DecodeString(fact.SHA256); err != nil || fact.SHA256 != strings.ToLower(fact.SHA256) {
		return fmt.Errorf("cursor fact digest is invalid")
	}
	if fact.TotalBytes <= 0 || fact.TotalBytes > maxFactBytes ||
		fact.Offset <= 0 || fact.Offset >= fact.TotalBytes {
		return fmt.Errorf("cursor fact offset is invalid")
	}
	if cursor.After != nil {
		after := *cursor.After
		if compareFactPageKeys(fact.Key, after) <= 0 ||
			fact.Key.SnapshotID != after.SnapshotID ||
			fact.Key.ExpiresAtUnix != after.ExpiresAtUnix ||
			fact.Key.MaxCalls != after.MaxCalls ||
			fact.Key.Ordinal != after.Ordinal+1 {
			return fmt.Errorf("cursor fact key does not advance within one snapshot")
		}
	}
	return nil
}

func encodeFactPageCursor(cursor factPageCursor) (string, error) {
	payload, err := json.Marshal(cursor)
	if err != nil {
		return "", fmt.Errorf("encode cursor payload: %w", err)
	}
	mac := hmac.New(sha256.New, factPageCursorMACKey)
	_, _ = mac.Write(payload)
	return base64.RawURLEncoding.EncodeToString(payload) + "." +
		base64.RawURLEncoding.EncodeToString(mac.Sum(nil)), nil
}

func decodeFactPageCursor(token string, sc rlmscope.Scope, level, maxFactBytes int) (factPageCursor, error) {
	var cursor factPageCursor
	if token == "" || len(token) > factPageMaxCursorBytes || strings.Count(token, ".") != 1 {
		return cursor, fmt.Errorf("invalid cursor framing")
	}
	parts := strings.SplitN(token, ".", 2)
	payload, err := base64.RawURLEncoding.DecodeString(parts[0])
	if err != nil || len(payload) == 0 || len(payload) > factPageMaxCursorBytes {
		return cursor, fmt.Errorf("invalid cursor payload")
	}
	signature, err := base64.RawURLEncoding.DecodeString(parts[1])
	if err != nil || len(signature) != sha256.Size {
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
	if err := validateFactPageCursor(cursor, sc, level, maxFactBytes); err != nil {
		return cursor, err
	}
	return cursor, nil
}

func validateFactPageRecord(sc rlmscope.Scope, level int, key memory.FactPageKey, fact *memory.Fact) error {
	if fact == nil || fact.TenantID != sc.TenantID || fact.ProjectID != sc.ProjectID ||
		fact.SessionID != "" || int(fact.Level) != level || fact.ID != key.ID {
		return fmt.Errorf("fact page backend scope mismatch")
	}
	return nil
}

func mapHasFactPageScopeOverride(values map[string]any) bool {
	for _, key := range []string{
		"tenant_id", "project_id", "rlm_tenant_id", "rlm_project_id",
		"rlm_scope", "gomcp_scope", "scope",
	} {
		if _, present := values[key]; present {
			return true
		}
	}
	return false
}

func requestHasFactPageScopeOverride(req mcp.CallToolRequest) bool {
	for headerName := range req.Header {
		for _, scopeHeader := range []string{
			"X-GoMCP-Tenant-ID", "X-GoMCP-Project-ID", "X-RLM-Tenant-ID", "X-RLM-Project-ID",
		} {
			if strings.EqualFold(headerName, scopeHeader) {
				return true
			}
		}
	}
	if mapHasFactPageScopeOverride(req.GetArguments()) {
		return true
	}
	for _, meta := range []*mcp.Meta{req.Params.Meta, req.Request.Params.Meta} {
		if meta != nil && mapHasFactPageScopeOverride(meta.AdditionalFields) {
			return true
		}
	}
	return false
}

func (s *Server) handleListDefaultFactsPage(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	sc := rlmscope.Default()
	if requestHasFactPageScopeOverride(req) {
		return factPageErrorResult(&sc, "scope_override_forbidden", "default fact paging does not accept scope overrides"), nil
	}
	defaultCtx, sc, err := s.defaultScopeContext(ctx)
	if err != nil {
		return factPageErrorResult(&sc, "scope_override_forbidden", err.Error()), nil
	}
	return s.handleListFactsPageForScope(defaultCtx, sc, req)
}

func (s *Server) handleListProjectFactsPage(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	explicitCtx, sc, err := s.explicitMetaScopeContext(ctx, req)
	if err != nil {
		return factPageErrorResult(nil, "invalid_scope", err.Error()), nil
	}
	if _, err := rlmscope.RequireExactProject(explicitCtx); err != nil {
		return factPageErrorResult(&sc, "invalid_scope", err.Error()), nil
	}
	return s.handleListFactsPageForScope(explicitCtx, sc, req)
}

func (s *Server) handleListFactsPageForScope(
	ctx context.Context,
	sc rlmscope.Scope,
	req mcp.CallToolRequest,
) (*mcp.CallToolResult, error) {
	arguments := req.GetArguments()
	for name := range arguments {
		if name != "level" && name != "max_fact_bytes" && name != "cursor" {
			return factPageErrorResult(&sc, "invalid_arguments", "request contains an unknown argument"), nil
		}
	}
	level, err := exactIntegerArgument(arguments, "level")
	if err != nil || level < 0 || level > 3 {
		return factPageErrorResult(&sc, "invalid_arguments", "level must be an integer from 0 through 3"), nil
	}
	maxFactBytes, err := exactIntegerArgument(arguments, "max_fact_bytes")
	if err != nil || maxFactBytes < 1 || maxFactBytes > factPageMaxFactBytes {
		return factPageErrorResult(&sc, "invalid_arguments", "max_fact_bytes must be an integer from 1 through 16777216"), nil
	}

	cursorToken := ""
	if raw, present := arguments["cursor"]; present {
		value, ok := raw.(string)
		if !ok || value == "" {
			return factPageErrorResult(&sc, "invalid_cursor", "cursor must be a non-empty opaque string"), nil
		}
		cursorToken = value
	}
	cursor := factPageCursor{
		Version:      factPageProtocolVersion,
		TenantID:     sc.TenantID,
		ProjectID:    sc.ProjectID,
		Level:        level,
		MaxFactBytes: maxFactBytes,
	}
	if cursorToken != "" {
		cursor, err = decodeFactPageCursor(cursorToken, sc, level, maxFactBytes)
		if err != nil {
			return factPageErrorResult(&sc, "invalid_cursor", "cursor is invalid or does not match this request"), nil
		}
	}
	releaseCursorSnapshot := func() {
		var key *memory.FactPageKey
		if cursor.Fact != nil {
			key = &cursor.Fact.Key
		} else if cursor.After != nil {
			key = cursor.After
		}
		if key != nil {
			_ = s.facts.ReleaseFactPage(ctx, level, *key)
		}
	}

	var (
		fact    *memory.Fact
		record  *memory.FactPageRecord
		key     memory.FactPageKey
		hasMore bool
	)
	if cursor.Fact != nil {
		key = cursor.Fact.Key
		record, err = s.facts.GetFactPageRecord(
			ctx, level, maxFactBytes, cursor.Snapshot, cursor.ExpectedCount, key,
			cursor.Fact.Offset,
		)
		if err != nil {
			var storedOversize *memory.FactPageStoredOversizeError
			releaseCursorSnapshot()
			if errors.Is(err, memory.ErrFactPageExpired) {
				return factPageErrorResult(&sc, "page_expired", "fact page snapshot expired"), nil
			}
			if errors.Is(err, memory.ErrFactPageChanged) || errors.As(err, &storedOversize) {
				return factPageErrorResult(&sc, "page_changed", "fact page snapshot changed"), nil
			}
			return factPageErrorResult(&sc, "invalid_cursor", "cursor fact is unavailable"), nil
		}
		hasMore = cursor.Fact.HasMore
	} else {
		page, pageErr := s.facts.ListFactsPage(
			ctx, level, maxFactBytes, cursor.Snapshot, cursor.ExpectedCount, cursor.After,
		)
		if pageErr != nil {
			var storedOversize *memory.FactPageStoredOversizeError
			var capacity *memory.FactPageSnapshotCapacityError
			if cursorToken != "" {
				releaseCursorSnapshot()
			}
			if errors.Is(pageErr, memory.ErrFactPageExpired) {
				return factPageErrorResult(&sc, "page_expired", "fact page snapshot expired"), nil
			}
			if errors.Is(pageErr, memory.ErrFactPageChanged) ||
				(cursorToken != "" && errors.As(pageErr, &storedOversize)) {
				return factPageErrorResult(&sc, "page_changed", "fact page snapshot changed"), nil
			}
			if errors.As(pageErr, &storedOversize) {
				return boundedSearchStoredOversizedResult(sc, &storedOversize.Measurement), nil
			}
			if errors.As(pageErr, &capacity) {
				return factPageErrorResult(&sc, "page_capacity", "fact page snapshot capacity is exhausted"), nil
			}
			return factPageErrorResult(&sc, "page_unavailable", "exact fact page is unavailable"), nil
		}
		if page == nil || page.Fact == nil {
			var expectedCount int64
			if page != nil {
				expectedCount = page.ExpectedCount
			}
			return structuredFactPageResult(factPageEnvelope{
				MemoryScope: factPageScope(sc),
				Page: factPagePayload{
					Version:            factPageProtocolVersion,
					Encoding:           "base64-json",
					FrameRawLimitBytes: factPageFrameRawBytes,
					MaxFactBytes:       maxFactBytes,
					ExpectedCount:      expectedCount,
					Frames:             []factPageFrame{},
					Done:               true,
				},
			}, false), nil
		}
		cursor.Snapshot = page.Snapshot
		cursor.ExpectedCount = page.ExpectedCount
		fact = page.Fact
		record = page.Record
		key = page.Key
		hasMore = page.HasMore
	}
	if cursor.Fact == nil {
		if err := validateFactPageRecord(sc, level, key, fact); err != nil {
			_ = s.facts.ReleaseFactPage(ctx, level, key)
			return factPageErrorResult(&sc, "page_scope_mismatch", "fact page backend scope mismatch"), nil
		}
	}
	if record == nil || record.Key != key || record.FactID != key.ID || record.TotalBytes <= 0 {
		_ = s.facts.ReleaseFactPage(ctx, level, key)
		return factPageErrorResult(&sc, "page_scope_mismatch", "fact page backend record mismatch"), nil
	}
	if record.TotalBytes > maxFactBytes {
		_ = s.facts.ReleaseFactPage(ctx, level, key)
		return factPageOversizedResult(sc, key.ID, record.TotalBytes, maxFactBytes), nil
	}
	if len(record.SHA256) != sha256.Size*2 || record.Offset < 0 ||
		len(record.Data) == 0 || len(record.Data) > factPageFrameRawBytes ||
		record.Offset+len(record.Data) > record.TotalBytes ||
		record.Final != (record.Offset+len(record.Data) == record.TotalBytes) {
		_ = s.facts.ReleaseFactPage(ctx, level, key)
		return factPageErrorResult(&sc, "page_scope_mismatch", "fact page backend frame mismatch"), nil
	}
	digestBytes, digestErr := hex.DecodeString(record.SHA256)
	if digestErr != nil || len(digestBytes) != sha256.Size ||
		record.SHA256 != hex.EncodeToString(digestBytes) {
		_ = s.facts.ReleaseFactPage(ctx, level, key)
		return factPageErrorResult(&sc, "page_scope_mismatch", "fact page backend digest mismatch"), nil
	}
	if cursor.Fact != nil {
		if cursor.Fact.FactID != record.FactID || cursor.Fact.SHA256 != record.SHA256 ||
			cursor.Fact.TotalBytes != record.TotalBytes || cursor.Fact.Offset != record.Offset {
			_ = s.facts.ReleaseFactPage(ctx, level, key)
			return factPageErrorResult(&sc, "invalid_cursor", "cursor fact changed while it was being read"), nil
		}
	}
	frame := factPageFrame{
		FactID:     record.FactID,
		SHA256:     record.SHA256,
		TotalBytes: record.TotalBytes,
		Offset:     record.Offset,
		DataBase64: base64.StdEncoding.EncodeToString(record.Data),
		Final:      record.Final,
	}
	payload := factPagePayload{
		Version:            factPageProtocolVersion,
		Encoding:           "base64-json",
		FrameRawLimitBytes: factPageFrameRawBytes,
		MaxFactBytes:       maxFactBytes,
		ExpectedCount:      cursor.ExpectedCount,
		Frames:             []factPageFrame{frame},
		Done:               record.Final && !hasMore,
	}
	if !payload.Done {
		next := factPageCursor{
			Version:       factPageProtocolVersion,
			TenantID:      sc.TenantID,
			ProjectID:     sc.ProjectID,
			Level:         level,
			MaxFactBytes:  maxFactBytes,
			Snapshot:      cursor.Snapshot,
			ExpectedCount: cursor.ExpectedCount,
			After:         cursor.After,
		}
		if !record.Final {
			next.Fact = &factPageCursorFact{
				Key:        key,
				FactID:     record.FactID,
				SHA256:     record.SHA256,
				TotalBytes: record.TotalBytes,
				Offset:     record.Offset + len(record.Data),
				HasMore:    hasMore,
			}
		} else {
			next.After = &key
		}
		payload.NextCursor, err = encodeFactPageCursor(next)
		if err != nil {
			_ = s.facts.ReleaseFactPage(ctx, level, key)
			return factPageErrorResult(&sc, "page_encoding_failed", "continuation cursor could not be encoded"), nil
		}
	}
	if payload.Done {
		if err := s.facts.ReleaseFactPage(ctx, level, key); err != nil {
			if errors.Is(err, memory.ErrFactPageExpired) {
				return factPageErrorResult(&sc, "page_expired", "fact page snapshot expired"), nil
			}
			return factPageErrorResult(&sc, "page_changed", "fact page snapshot changed"), nil
		}
	}
	return structuredFactPageResult(factPageEnvelope{
		MemoryScope: factPageScope(sc),
		Page:        payload,
	}, false), nil
}
