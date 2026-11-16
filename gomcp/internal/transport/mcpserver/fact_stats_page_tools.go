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

	"github.com/syntrex/gomcp/internal/domain/memory"
	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
)

const factStatsPageProtocolVersion = 2

var factStatsPageCursorMACDomain = []byte("gomcp-fact-stats-page-v2\x00")

type factStatsDomainFrame struct {
	SegmentIndex int64  `json:"segment_index"`
	Ordinal      int64  `json:"ordinal"`
	SHA256       string `json:"sha256"`
	TotalBytes   int    `json:"total_bytes"`
	Offset       int    `json:"offset"`
	DataBase64   string `json:"data_base64"`
	SegmentFinal bool   `json:"segment_final"`
	Final        bool   `json:"final"`
}

type factStatsPagePayload struct {
	Version            int                         `json:"version"`
	Encoding           string                      `json:"encoding"`
	FrameRawLimitBytes int                         `json:"frame_raw_limit_bytes"`
	MaxSegmentsPerPage int                         `json:"max_segments_per_page"`
	MaxCalls           int                         `json:"max_calls"`
	CallIndex          int                         `json:"call_index"`
	SnapshotID         string                      `json:"snapshot_id"`
	ExpectedRows       int64                       `json:"expected_rows"`
	ExpectedCount      int64                       `json:"expected_count"`
	ExpectedSegments   int64                       `json:"expected_segments"`
	SerializedBytes    int64                       `json:"serialized_bytes"`
	FixedStats         *memory.FixedFactStoreStats `json:"fixed_stats,omitempty"`
	DomainFrames       []factStatsDomainFrame      `json:"domain_frames,omitempty"`
	NextCursor         string                      `json:"next_cursor,omitempty"`
	Done               bool                        `json:"done"`
}

type factStatsPageEnvelope struct {
	MemoryScope factPageMemoryScope  `json:"memory_scope"`
	Page        factStatsPagePayload `json:"page"`
}

type factStatsPageCursor struct {
	Version          int    `json:"version"`
	TenantID         string `json:"tenant_id"`
	ProjectID        string `json:"project_id"`
	SnapshotID       string `json:"snapshot_id"`
	ExpectedRows     int64  `json:"expected_rows"`
	ExpectedCount    int64  `json:"expected_count"`
	ExpectedSegments int64  `json:"expected_segments"`
	SerializedBytes  int64  `json:"serialized_bytes"`
	SegmentIndex     int64  `json:"segment_index"`
	SegmentOffset    int    `json:"segment_offset"`
	CallIndex        int    `json:"call_index"`
}

type factStatsResultLimitError struct {
	Code               string `json:"code"`
	Message            string `json:"message"`
	SerializedBytes    int64  `json:"serialized_bytes"`
	MaxSerializedBytes int64  `json:"max_serialized_bytes"`
}

type factStatsResultLimitEnvelope struct {
	MemoryScope factPageMemoryScope       `json:"memory_scope"`
	Error       factStatsResultLimitError `json:"error"`
}

func (s *Server) registerBoundedStatsTools() {
	s.mcp.AddTool(
		mcp.NewTool("default_fact_stats_page",
			mcp.WithDescription("Read bounded non-session fact statistics from local/default. Scope headers, arguments, and _meta overrides are rejected."),
			mcp.WithString("cursor", mcp.Description("Opaque continuation cursor returned by the previous page")),
		),
		s.handleDefaultFactStatsPage,
	)
	s.mcp.AddTool(
		mcp.NewTool("project_fact_stats_page",
			mcp.WithDescription("Read bounded non-session fact statistics from one exact non-default project. Requires explicit _meta.rlm_scope."),
			mcp.WithString("cursor", mcp.Description("Opaque continuation cursor returned by the previous page")),
		),
		s.handleProjectFactStatsPage,
	)
}

func encodeFactStatsPageCursor(cursor factStatsPageCursor) (string, error) {
	payload, err := json.Marshal(cursor)
	if err != nil {
		return "", fmt.Errorf("encode stats cursor payload: %w", err)
	}
	mac := hmac.New(sha256.New, factPageCursorMACKey)
	_, _ = mac.Write(factStatsPageCursorMACDomain)
	_, _ = mac.Write(payload)
	token := base64.RawURLEncoding.EncodeToString(payload) + "." +
		base64.RawURLEncoding.EncodeToString(mac.Sum(nil))
	if len(token) > factPageMaxCursorBytes {
		return "", fmt.Errorf("stats cursor exceeds maximum size")
	}
	return token, nil
}

func decodeFactStatsPageCursor(token string, sc rlmscope.Scope) (factStatsPageCursor, error) {
	var cursor factStatsPageCursor
	if token == "" || len(token) > factPageMaxCursorBytes || strings.Count(token, ".") != 1 {
		return cursor, fmt.Errorf("invalid stats cursor framing")
	}
	parts := strings.SplitN(token, ".", 2)
	payload, err := base64.RawURLEncoding.DecodeString(parts[0])
	if err != nil || len(payload) == 0 || len(payload) > factPageMaxCursorBytes {
		return cursor, fmt.Errorf("invalid stats cursor payload")
	}
	if base64.RawURLEncoding.EncodeToString(payload) != parts[0] {
		return cursor, fmt.Errorf("non-canonical stats cursor payload")
	}
	signature, err := base64.RawURLEncoding.DecodeString(parts[1])
	if err != nil || len(signature) != sha256.Size {
		return cursor, fmt.Errorf("invalid stats cursor signature")
	}
	if base64.RawURLEncoding.EncodeToString(signature) != parts[1] {
		return cursor, fmt.Errorf("non-canonical stats cursor signature")
	}
	mac := hmac.New(sha256.New, factPageCursorMACKey)
	_, _ = mac.Write(factStatsPageCursorMACDomain)
	_, _ = mac.Write(payload)
	if !hmac.Equal(signature, mac.Sum(nil)) {
		return cursor, fmt.Errorf("invalid stats cursor signature")
	}
	decoder := json.NewDecoder(bytes.NewReader(payload))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(&cursor); err != nil {
		return cursor, fmt.Errorf("invalid stats cursor object")
	}
	var trailing any
	if err := decoder.Decode(&trailing); err != io.EOF {
		return cursor, fmt.Errorf("invalid stats cursor trailing data")
	}
	canonical, err := json.Marshal(cursor)
	if err != nil || !bytes.Equal(payload, canonical) {
		return cursor, fmt.Errorf("non-canonical stats cursor object")
	}
	if err := validateFactStatsPageCursor(cursor, sc); err != nil {
		return cursor, err
	}
	return cursor, nil
}

func validateFactStatsPageCursor(cursor factStatsPageCursor, sc rlmscope.Scope) error {
	if cursor.Version != factStatsPageProtocolVersion || cursor.TenantID != sc.TenantID ||
		cursor.ProjectID != sc.ProjectID || !validFactStatsWireSnapshotID(cursor.SnapshotID) ||
		cursor.ExpectedRows <= 0 || cursor.ExpectedCount <= 0 ||
		cursor.ExpectedCount > cursor.ExpectedRows ||
		cursor.ExpectedCount > memory.FactStatsPageMaxDomains ||
		cursor.ExpectedSegments < cursor.ExpectedCount ||
		cursor.ExpectedSegments > memory.FactStatsPageMaxSnapshotSegments ||
		cursor.SerializedBytes <= 0 ||
		cursor.SerializedBytes > memory.FactStatsPageMaxSerializedDomainScopeBytes ||
		cursor.SegmentIndex < 0 || cursor.SegmentIndex >= cursor.ExpectedSegments ||
		cursor.SegmentOffset < 0 || cursor.SegmentOffset >= memory.FactStatsPageFrameRawBytes ||
		cursor.CallIndex < 1 || cursor.CallIndex >= memory.FactStatsPageMaxCalls {
		return fmt.Errorf("stats cursor does not match request scope or snapshot")
	}
	return nil
}

func validFactStatsWireSnapshotID(value string) bool {
	if len(value) != memory.FactStatsPageSnapshotIDBytes*2 {
		return false
	}
	decoded, err := hex.DecodeString(value)
	return err == nil && len(decoded) == memory.FactStatsPageSnapshotIDBytes &&
		value == hex.EncodeToString(decoded)
}

func validateFixedFactStats(stats *memory.FixedFactStoreStats) error {
	if stats == nil || stats.ByLevel == nil || stats.ByOrigin == nil {
		return fmt.Errorf("fixed fact stats are missing")
	}
	counts := map[string]int{
		"total_facts":     stats.TotalFacts,
		"live_facts":      stats.LiveFacts,
		"archived_count":  stats.ArchivedCount,
		"stale_count":     stats.StaleCount,
		"with_embeddings": stats.WithEmbeddings,
		"gene_count":      stats.GeneCount,
		"cold_count":      stats.ColdCount,
	}
	for name, count := range counts {
		if count < 0 {
			return fmt.Errorf("fixed fact stats %s must be nonnegative", name)
		}
		if name != "total_facts" && count > stats.TotalFacts {
			return fmt.Errorf("fixed fact stats %s exceeds total_facts", name)
		}
	}
	levelTotal := 0
	for level, count := range stats.ByLevel {
		if !level.IsValid() || count < 0 || count > stats.TotalFacts-levelTotal {
			return fmt.Errorf("fixed fact stats by_level is invalid")
		}
		levelTotal += count
	}
	if levelTotal != stats.TotalFacts {
		return fmt.Errorf("fixed fact stats by_level total must equal total_facts")
	}
	originTotal := 0
	for origin, count := range stats.ByOrigin {
		if !origin.IsValid() || count < 0 || count > stats.LiveFacts-originTotal {
			return fmt.Errorf("fixed fact stats by_origin is invalid")
		}
		originTotal += count
	}
	if originTotal != stats.LiveFacts {
		return fmt.Errorf("fixed fact stats by_origin total must equal live_facts")
	}
	if stats.GenomeHash != "" {
		if len(stats.GenomeHash) != sha256.Size*2 {
			return fmt.Errorf("fixed fact stats genome_hash is invalid")
		}
		if _, err := hex.DecodeString(stats.GenomeHash); err != nil || stats.GenomeHash != strings.ToLower(stats.GenomeHash) {
			return fmt.Errorf("fixed fact stats genome_hash is invalid")
		}
	}
	return nil
}

func factStatsResultOversizeResult(
	sc rlmscope.Scope,
	oversized *memory.FactStatsPageResultOversize,
) *mcp.CallToolResult {
	code := "stats_result_too_large"
	message := "serialized fact stats scope exceeds the hard result limit"
	if oversized.Kind == memory.FactStatsPageDomainResultOversizeKind {
		code = "stats_domain_result_too_large"
		message = "serialized fact stats domain exceeds the hard result limit"
	}
	return structuredFactPageResult(factStatsResultLimitEnvelope{
		MemoryScope: factPageScope(sc),
		Error: factStatsResultLimitError{
			Code:               code,
			Message:            message,
			SerializedBytes:    oversized.SerializedBytes,
			MaxSerializedBytes: oversized.MaxSerializedBytes,
		},
	}, true)
}

func (s *Server) handleDefaultFactStatsPage(
	ctx context.Context,
	req mcp.CallToolRequest,
) (*mcp.CallToolResult, error) {
	sc := rlmscope.Default()
	if requestHasFactPageScopeOverride(req) {
		return factPageErrorResult(&sc, "scope_override_forbidden", "default fact stats paging does not accept scope overrides"), nil
	}
	defaultCtx, sc, err := s.defaultScopeContext(ctx)
	if err != nil {
		return factPageErrorResult(&sc, "scope_override_forbidden", err.Error()), nil
	}
	return s.handleFactStatsPageForScope(defaultCtx, sc, req)
}

func (s *Server) handleProjectFactStatsPage(
	ctx context.Context,
	req mcp.CallToolRequest,
) (*mcp.CallToolResult, error) {
	explicitCtx, sc, err := s.explicitMetaScopeContext(ctx, req)
	if err != nil {
		return factPageErrorResult(nil, "invalid_scope", err.Error()), nil
	}
	if _, err := rlmscope.RequireExactProject(explicitCtx); err != nil {
		return factPageErrorResult(&sc, "invalid_scope", err.Error()), nil
	}
	return s.handleFactStatsPageForScope(explicitCtx, sc, req)
}

func (s *Server) handleFactStatsPageForScope(
	ctx context.Context,
	sc rlmscope.Scope,
	req mcp.CallToolRequest,
) (*mcp.CallToolResult, error) {
	arguments := req.GetArguments()
	for name := range arguments {
		if name != "cursor" {
			return factPageErrorResult(&sc, "invalid_arguments", "request contains an unknown argument"), nil
		}
	}

	var (
		cursorToken string
		cursor      factStatsPageCursor
		position    *memory.FactStatsPagePosition
	)
	if raw, present := arguments["cursor"]; present {
		value, ok := raw.(string)
		if !ok || value == "" {
			return factPageErrorResult(&sc, "invalid_cursor", "cursor must be a non-empty opaque string"), nil
		}
		cursorToken = value
	}
	if cursorToken != "" {
		var err error
		cursor, err = decodeFactStatsPageCursor(cursorToken, sc)
		if err != nil {
			return factPageErrorResult(&sc, "invalid_cursor", "cursor is invalid or does not match this request"), nil
		}
		position = &memory.FactStatsPagePosition{
			SnapshotID:       cursor.SnapshotID,
			ExpectedRows:     cursor.ExpectedRows,
			ExpectedDomains:  cursor.ExpectedCount,
			ExpectedSegments: cursor.ExpectedSegments,
			SerializedBytes:  cursor.SerializedBytes,
			SegmentIndex:     cursor.SegmentIndex,
			SegmentOffset:    cursor.SegmentOffset,
		}
	}

	page, err := s.facts.GetFactStatsPage(ctx, position)
	if err != nil {
		var storedOversize *memory.FactStatsPageStoredOversize
		if errors.As(err, &storedOversize) {
			return boundedSearchStoredOversizedResult(sc, &storedOversize.Measurement), nil
		}
		var resultOversize *memory.FactStatsPageResultOversize
		if errors.As(err, &resultOversize) {
			return factStatsResultOversizeResult(sc, resultOversize), nil
		}
		var snapshotBusy *memory.FactStatsPageSnapshotBusy
		if errors.As(err, &snapshotBusy) {
			return factPageErrorResult(&sc, "stats_snapshot_busy", "fact stats snapshot is already active for this scope"), nil
		}
		var snapshotCapacity *memory.FactStatsPageSnapshotCapacity
		if errors.As(err, &snapshotCapacity) {
			return factPageErrorResult(&sc, "stats_snapshot_capacity_exceeded", "fact stats snapshot capacity is exhausted"), nil
		}
		if errors.Is(err, memory.ErrFactStatsPageChanged) {
			return factPageErrorResult(&sc, "page_changed", "fact stats page snapshot changed"), nil
		}
		return factPageErrorResult(&sc, "page_unavailable", "exact fact stats page is unavailable"), nil
	}
	if page == nil {
		return factPageErrorResult(&sc, "page_scope_mismatch", "fact stats page backend returned invalid bounds"), nil
	}

	callIndex := 0
	if cursorToken == "" {
		if page.Fixed == nil || validateFixedFactStats(page.Fixed) != nil ||
			int64(page.Fixed.TotalFacts) != page.ExpectedRows {
			return factPageErrorResult(&sc, "page_scope_mismatch", "fact stats page backend returned invalid fixed counters"), nil
		}
	} else {
		callIndex = cursor.CallIndex
		if page.Fixed != nil || page.SnapshotID != cursor.SnapshotID ||
			page.ExpectedRows != cursor.ExpectedRows || page.ExpectedDomains != cursor.ExpectedCount ||
			page.ExpectedSegments != cursor.ExpectedSegments ||
			page.SerializedBytes != cursor.SerializedBytes {
			return factPageErrorResult(&sc, "page_scope_mismatch", "fact stats page backend changed cursor bounds"), nil
		}
	}

	payload := factStatsPagePayload{
		Version:            factStatsPageProtocolVersion,
		Encoding:           "base64-json-segments",
		FrameRawLimitBytes: memory.FactStatsPageFrameRawBytes,
		MaxSegmentsPerPage: memory.FactStatsPageMaxSegmentsPerPage,
		MaxCalls:           memory.FactStatsPageMaxCalls,
		CallIndex:          callIndex,
		SnapshotID:         page.SnapshotID,
		ExpectedRows:       page.ExpectedRows,
		ExpectedCount:      page.ExpectedDomains,
		ExpectedSegments:   page.ExpectedSegments,
		SerializedBytes:    page.SerializedBytes,
		FixedStats:         page.Fixed,
		Done:               page.Done,
	}
	if page.ExpectedDomains == 0 {
		if !page.Done || page.SnapshotID != "" || page.ExpectedSegments != 0 ||
			page.SerializedBytes != 0 || len(page.Segments) != 0 || cursorToken != "" {
			return factPageErrorResult(&sc, "page_scope_mismatch", "fact stats page backend returned an invalid empty snapshot"), nil
		}
		return structuredFactPageResult(factStatsPageEnvelope{
			MemoryScope: factPageScope(sc), Page: payload,
		}, false), nil
	}
	if !validFactStatsWireSnapshotID(page.SnapshotID) || page.ExpectedRows <= 0 ||
		page.ExpectedDomains > page.ExpectedRows || page.ExpectedDomains > memory.FactStatsPageMaxDomains ||
		page.ExpectedSegments < page.ExpectedDomains ||
		page.ExpectedSegments > memory.FactStatsPageMaxSnapshotSegments ||
		page.SerializedBytes <= 0 ||
		page.SerializedBytes > memory.FactStatsPageMaxSerializedDomainScopeBytes ||
		len(page.Segments) == 0 || len(page.Segments) > memory.FactStatsPageMaxSegmentsPerPage {
		return factPageErrorResult(&sc, "page_scope_mismatch", "fact stats page backend returned invalid snapshot bounds"), nil
	}

	expectedSegmentIndex := int64(0)
	expectedLocalOffset := 0
	if cursorToken != "" {
		expectedSegmentIndex = cursor.SegmentIndex
		expectedLocalOffset = cursor.SegmentOffset
	}
	rawBytes := 0
	var (
		previousOrdinal int64
		previousSHA256  string
		previousTotal   int
		previousEnd     int
		previousFinal   bool
		havePrevious    bool
	)
	for _, segment := range page.Segments {
		if segment.SegmentIndex != expectedSegmentIndex || segment.Ordinal < 0 ||
			segment.Ordinal >= page.ExpectedDomains || len(segment.SHA256) != sha256.Size*2 ||
			segment.SHA256 != strings.ToLower(segment.SHA256) {
			return factPageErrorResult(&sc, "page_scope_mismatch", "fact stats page backend returned invalid segment identity"), nil
		}
		if _, err := hex.DecodeString(segment.SHA256); err != nil ||
			segment.TotalBytes <= 0 || int64(segment.TotalBytes) > memory.FactStatsPageMaxSerializedDomainBytes ||
			segment.StoredOffset < 0 || segment.StoredOffset >= segment.TotalBytes ||
			segment.StoredBytes <= 0 || segment.StoredBytes > memory.FactStatsPageFrameRawBytes ||
			segment.StoredOffset+segment.StoredBytes > segment.TotalBytes ||
			segment.LocalOffset != expectedLocalOffset || segment.LocalOffset < 0 ||
			segment.LocalOffset >= segment.StoredBytes ||
			segment.Offset != segment.StoredOffset+segment.LocalOffset || len(segment.Data) == 0 ||
			len(segment.Data) > memory.FactStatsPageFrameRawBytes-rawBytes ||
			len(segment.Data) > segment.StoredBytes-segment.LocalOffset ||
			segment.Offset < 0 || segment.Offset+len(segment.Data) > segment.TotalBytes ||
			segment.SegmentFinal != (segment.LocalOffset+len(segment.Data) == segment.StoredBytes) ||
			segment.Final != (segment.Offset+len(segment.Data) == segment.TotalBytes) {
			return factPageErrorResult(&sc, "page_scope_mismatch", "fact stats page backend returned invalid segment bounds"), nil
		}
		if havePrevious {
			if segment.Ordinal == previousOrdinal {
				if segment.SHA256 != previousSHA256 || segment.TotalBytes != previousTotal ||
					segment.Offset != previousEnd {
					return factPageErrorResult(&sc, "page_scope_mismatch", "fact stats page backend broke domain continuity"), nil
				}
			} else if segment.Ordinal != previousOrdinal+1 || segment.Offset != 0 || !previousFinal {
				return factPageErrorResult(&sc, "page_scope_mismatch", "fact stats page backend broke ordinal continuity"), nil
			}
		}
		wireFrame := factStatsDomainFrame{
			SegmentIndex: segment.SegmentIndex,
			Ordinal:      segment.Ordinal,
			SHA256:       segment.SHA256,
			TotalBytes:   segment.TotalBytes,
			Offset:       segment.Offset,
			DataBase64:   base64.StdEncoding.EncodeToString(segment.Data),
			SegmentFinal: segment.SegmentFinal,
			Final:        segment.Final,
		}
		payload.DomainFrames = append(payload.DomainFrames, wireFrame)
		rawBytes += len(segment.Data)
		if !segment.SegmentFinal {
			expectedLocalOffset = segment.LocalOffset + len(segment.Data)
		} else {
			expectedSegmentIndex++
			expectedLocalOffset = 0
		}
		previousOrdinal = segment.Ordinal
		previousSHA256 = segment.SHA256
		previousTotal = segment.TotalBytes
		previousEnd = segment.Offset + len(segment.Data)
		previousFinal = segment.Final
		havePrevious = true
	}
	if rawBytes <= 0 || rawBytes > memory.FactStatsPageFrameRawBytes ||
		page.NextSegmentIndex != expectedSegmentIndex ||
		page.NextSegmentOffset != expectedLocalOffset ||
		page.NextSegmentIndex > page.ExpectedSegments || page.NextSegmentOffset < 0 ||
		page.NextSegmentOffset >= memory.FactStatsPageFrameRawBytes ||
		page.Done != (page.NextSegmentIndex == page.ExpectedSegments && page.NextSegmentOffset == 0) {
		return factPageErrorResult(&sc, "page_scope_mismatch", "fact stats page backend returned invalid continuation"), nil
	}
	if page.Done {
		if callIndex >= memory.FactStatsPageMaxCalls {
			return factPageErrorResult(&sc, "stats_work_limit_exceeded", "fact stats snapshot exceeded the hard call limit"), nil
		}
	} else {
		if callIndex+1 >= memory.FactStatsPageMaxCalls {
			return factPageErrorResult(&sc, "stats_work_limit_exceeded", "fact stats snapshot exceeded the hard call limit"), nil
		}
		next := factStatsPageCursor{
			Version:          factStatsPageProtocolVersion,
			TenantID:         sc.TenantID,
			ProjectID:        sc.ProjectID,
			SnapshotID:       page.SnapshotID,
			ExpectedRows:     page.ExpectedRows,
			ExpectedCount:    page.ExpectedDomains,
			ExpectedSegments: page.ExpectedSegments,
			SerializedBytes:  page.SerializedBytes,
			SegmentIndex:     page.NextSegmentIndex,
			SegmentOffset:    page.NextSegmentOffset,
			CallIndex:        callIndex + 1,
		}
		payload.NextCursor, err = encodeFactStatsPageCursor(next)
		if err != nil {
			return factPageErrorResult(&sc, "page_encoding_failed", "fact stats continuation cursor could not be encoded"), nil
		}
	}
	return structuredFactPageResult(factStatsPageEnvelope{
		MemoryScope: factPageScope(sc), Page: payload,
	}, false), nil
}
