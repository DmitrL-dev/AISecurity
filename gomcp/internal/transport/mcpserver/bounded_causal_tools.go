package mcpserver

import (
	"context"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"errors"
	"strings"

	"github.com/mark3labs/mcp-go/mcp"

	"github.com/syntrex/gomcp/internal/application/tools"
	"github.com/syntrex/gomcp/internal/domain/causal"
	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
)

const boundedCausalMaxResultBytes = tools.CausalChainMaxResultBytes

func boundedCausalDirectNeighbourDepth(schema map[string]any) {
	schema["const"] = float64(tools.CausalChainMaxDepth)
}

type boundedCausalFrame struct {
	SHA256     string `json:"sha256"`
	TotalBytes int    `json:"total_bytes"`
	DataBase64 string `json:"data_base64"`
}

type boundedCausalPayload struct {
	Version            int                `json:"version"`
	Encoding           string             `json:"encoding"`
	FrameRawLimitBytes int                `json:"frame_raw_limit_bytes"`
	MaxResultBytes     int                `json:"max_result_bytes"`
	Frame              boundedCausalFrame `json:"frame"`
}

type boundedCausalEnvelope struct {
	MemoryScope factPageMemoryScope  `json:"memory_scope"`
	Result      boundedCausalPayload `json:"result"`
}

type boundedCausalError struct {
	Code           string `json:"code"`
	Message        string `json:"message"`
	ActualBytes    int    `json:"actual_bytes,omitempty"`
	MaxResultBytes int    `json:"max_result_bytes,omitempty"`
	MaxNodes       int    `json:"max_nodes,omitempty"`
	Measurement    string `json:"measurement,omitempty"`
	MeasuredBytes  int64  `json:"measured_bytes,omitempty"`
	MaximumBytes   int64  `json:"maximum_bytes,omitempty"`
}

type boundedCausalErrorEnvelope struct {
	MemoryScope *factPageMemoryScope `json:"memory_scope,omitempty"`
	Error       boundedCausalError   `json:"error"`
}

func (s *Server) registerBoundedCausalTools() {
	s.mcp.AddTool(
		mcp.NewTool("get_default_causal_chain_bounded",
			mcp.WithDescription("Read a repository-bounded causal chain from local/default as one base64 JSON frame. Scope overrides are rejected."),
			mcp.WithString("query", mcp.Description("Decision search query"), mcp.Required()),
			mcp.WithNumber("max_depth", mcp.Description("Direct-neighbour depth (must be 1)"), mcp.Min(tools.CausalChainMaxDepth), mcp.Max(tools.CausalChainMaxDepth), boundedCausalDirectNeighbourDepth, mcp.MultipleOf(1), mcp.Required()),
			mcp.WithNumber("max_nodes", mcp.Description("Maximum returned nodes (1-100)"), mcp.Min(1), mcp.Max(tools.CausalChainMaxNodes), mcp.MultipleOf(1), mcp.Required()),
			mcp.WithNumber("max_result_bytes", mcp.Description("Maximum serialized result bytes (1-524288)"), mcp.Min(1), mcp.Max(boundedCausalMaxResultBytes), mcp.MultipleOf(1), mcp.Required()),
		),
		s.handleGetDefaultCausalChainBounded,
	)
}

func boundedCausalErrorResult(
	sc *rlmscope.Scope,
	code, message string,
	actualBytes, maxResultBytes, maxNodes int,
) *mcp.CallToolResult {
	var marker *factPageMemoryScope
	if sc != nil {
		value := factPageScope(*sc)
		marker = &value
	}
	return structuredFactPageResult(boundedCausalErrorEnvelope{
		MemoryScope: marker,
		Error: boundedCausalError{
			Code: code, Message: message, ActualBytes: actualBytes,
			MaxResultBytes: maxResultBytes, MaxNodes: maxNodes,
		},
	}, true)
}

func boundedCausalStoredOversizeResult(
	sc rlmscope.Scope,
	oversized *causal.StoredCausalOversizeError,
	maxNodes int,
) *mcp.CallToolResult {
	code := "stored_causal_data_too_large"
	message := "stored causal data exceeds a hard limit"
	if oversized.Kind == causal.StoredCausalNodeOversizeKind {
		code = "stored_causal_node_too_large"
		message = "stored causal node exceeds the hard byte limit"
	} else if oversized.Kind == causal.StoredCausalScopeOversizeKind {
		code = "stored_causal_scope_too_large"
		message = "stored causal scope exceeds the hard byte limit"
	}
	marker := factPageScope(sc)
	return structuredFactPageResult(boundedCausalErrorEnvelope{
		MemoryScope: &marker,
		Error: boundedCausalError{
			Code: code, Message: message, MaxNodes: maxNodes,
			Measurement:   string(oversized.Measurement),
			MeasuredBytes: oversized.Measured,
			MaximumBytes:  oversized.Maximum,
		},
	}, true)
}

func (s *Server) handleGetDefaultCausalChainBounded(
	ctx context.Context,
	req mcp.CallToolRequest,
) (*mcp.CallToolResult, error) {
	sc := rlmscope.Default()
	if requestHasFactPageScopeOverride(req) {
		return boundedCausalErrorResult(&sc, "scope_override_forbidden", "default causal lookup does not accept scope overrides", 0, 0, 0), nil
	}
	defaultCtx, sc, err := s.defaultScopeContext(ctx)
	if err != nil {
		return boundedCausalErrorResult(&sc, "scope_override_forbidden", err.Error(), 0, 0, 0), nil
	}
	arguments := req.GetArguments()
	for name := range arguments {
		switch name {
		case "query", "max_depth", "max_nodes", "max_result_bytes":
		default:
			return boundedCausalErrorResult(&sc, "invalid_arguments", "request contains an unknown argument", 0, 0, 0), nil
		}
	}
	query, ok := arguments["query"].(string)
	if !ok || query == "" || query != strings.TrimSpace(query) || len(query) > 4096 {
		return boundedCausalErrorResult(&sc, "invalid_arguments", "query must be a non-empty string of at most 4096 bytes without surrounding whitespace", 0, 0, 0), nil
	}
	maxDepth, err := exactIntegerArgument(arguments, "max_depth")
	if err != nil || maxDepth != tools.CausalChainMaxDepth {
		return boundedCausalErrorResult(&sc, "invalid_arguments", "max_depth must be the integer 1", 0, 0, 0), nil
	}
	maxNodes, err := exactIntegerArgument(arguments, "max_nodes")
	if err != nil || maxNodes < 1 || maxNodes > tools.CausalChainMaxNodes {
		return boundedCausalErrorResult(&sc, "invalid_arguments", "max_nodes must be an integer from 1 through 100", 0, 0, 0), nil
	}
	maxResultBytes, err := exactIntegerArgument(arguments, "max_result_bytes")
	if err != nil || maxResultBytes < 1 || maxResultBytes > boundedCausalMaxResultBytes {
		return boundedCausalErrorResult(&sc, "invalid_arguments", "max_result_bytes must be an integer from 1 through 524288", 0, 0, 0), nil
	}
	chain, err := s.causal.GetChainBounded(
		defaultCtx, query, maxDepth, maxNodes, maxResultBytes,
	)
	if err != nil {
		if errors.Is(err, causal.ErrCausalChainTooLarge) {
			return boundedCausalErrorResult(&sc, "causal_chain_too_large", "causal chain exceeds max_nodes", 0, 0, maxNodes), nil
		}
		var storedOversize *causal.StoredCausalOversizeError
		if errors.As(err, &storedOversize) {
			return boundedCausalStoredOversizeResult(sc, storedOversize, maxNodes), nil
		}
		return boundedCausalErrorResult(&sc, "causal_unavailable", "bounded causal lookup is unavailable", 0, 0, maxNodes), nil
	}
	serialized, err := json.Marshal(map[string]any{
		"chain":   chain,
		"mermaid": chain.ToMermaid(),
	})
	if err != nil {
		return boundedCausalErrorResult(&sc, "causal_encoding_failed", "causal chain could not be encoded", 0, maxResultBytes, maxNodes), nil
	}
	if len(serialized) > maxResultBytes {
		return boundedCausalErrorResult(&sc, "causal_result_too_large", "serialized causal result exceeds max_result_bytes", len(serialized), maxResultBytes, maxNodes), nil
	}
	digest := sha256.Sum256(serialized)
	return structuredFactPageResult(boundedCausalEnvelope{
		MemoryScope: factPageScope(sc),
		Result: boundedCausalPayload{
			Version:            1,
			Encoding:           "base64-json",
			FrameRawLimitBytes: boundedCausalMaxResultBytes,
			MaxResultBytes:     maxResultBytes,
			Frame: boundedCausalFrame{
				SHA256:     hex.EncodeToString(digest[:]),
				TotalBytes: len(serialized),
				DataBase64: base64.StdEncoding.EncodeToString(serialized),
			},
		},
	}, false), nil
}
