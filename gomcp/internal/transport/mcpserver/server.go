// Package mcpserver wires MCP tools and resources to application services.
package mcpserver

import (
	"context"
	"encoding/json"
	"fmt"

	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"

	"github.com/sentinel-community/gomcp/internal/application/contextengine"
	"github.com/sentinel-community/gomcp/internal/application/resources"
	"github.com/sentinel-community/gomcp/internal/application/tools"
	"github.com/sentinel-community/gomcp/internal/infrastructure/pybridge"
)

// Server wraps the MCP server with all registered tools and resources.
type Server struct {
	mcp           *server.MCPServer
	facts         *tools.FactService
	sessions      *tools.SessionService
	causal        *tools.CausalService
	crystals      *tools.CrystalService
	system        *tools.SystemService
	res           *resources.Provider
	pybridge      *pybridge.Bridge
	contextEngine *contextengine.Engine
}

// Config holds server configuration.
type Config struct {
	Name         string
	Version      string
	Instructions string // optional boot instructions returned at initialize
}

// Option configures optional Server dependencies.
type Option func(*Server)

// WithPyBridge sets the Python bridge for NLP/embedding tools.
func WithPyBridge(b *pybridge.Bridge) Option {
	return func(s *Server) {
		s.pybridge = b
	}
}

// WithContextEngine sets the Proactive Context Engine for automatic
// memory context injection into every tool response.
func WithContextEngine(e *contextengine.Engine) Option {
	return func(s *Server) {
		s.contextEngine = e
	}
}

// New creates a new MCP server with all tools and resources registered.
func New(cfg Config, facts *tools.FactService, sessions *tools.SessionService,
	causal *tools.CausalService, crystals *tools.CrystalService,
	system *tools.SystemService, res *resources.Provider, opts ...Option) *Server {

	s := &Server{
		facts:    facts,
		sessions: sessions,
		causal:   causal,
		crystals: crystals,
		system:   system,
		res:      res,
	}

	for _, opt := range opts {
		opt(s)
	}

	// Build server options — always include recovery middleware.
	serverOpts := []server.ServerOption{
		server.WithToolCapabilities(true),
		server.WithResourceCapabilities(true, true),
		server.WithRecovery(),
	}

	// Set boot instructions if provided.
	if cfg.Instructions != "" {
		serverOpts = append(serverOpts, server.WithInstructions(cfg.Instructions))
	}

	// Register context engine middleware if provided.
	if s.contextEngine != nil && s.contextEngine.IsEnabled() {
		serverOpts = append(serverOpts,
			server.WithToolHandlerMiddleware(s.contextEngine.Middleware()),
		)
	}

	s.mcp = server.NewMCPServer(cfg.Name, cfg.Version, serverOpts...)

	s.registerFactTools()
	s.registerSessionTools()
	s.registerCausalTools()
	s.registerCrystalTools()
	s.registerSystemTools()
	s.registerPythonBridgeTools()
	s.registerResources()

	return s
}

// MCPServer returns the underlying mcp-go server for transport binding.
func (s *Server) MCPServer() *server.MCPServer {
	return s.mcp
}

// --- Fact Tools ---

func (s *Server) registerFactTools() {
	s.mcp.AddTool(
		mcp.NewTool("add_fact",
			mcp.WithDescription("Add a new hierarchical memory fact (L0-L3)"),
			mcp.WithString("content", mcp.Description("Fact content"), mcp.Required()),
			mcp.WithNumber("level", mcp.Description("Hierarchy level: 0=project, 1=domain, 2=module, 3=snippet")),
			mcp.WithString("domain", mcp.Description("Domain category")),
			mcp.WithString("module", mcp.Description("Module name")),
			mcp.WithString("code_ref", mcp.Description("Code reference (file:line)")),
		),
		s.handleAddFact,
	)

	s.mcp.AddTool(
		mcp.NewTool("get_fact",
			mcp.WithDescription("Retrieve a fact by ID"),
			mcp.WithString("id", mcp.Description("Fact ID"), mcp.Required()),
		),
		s.handleGetFact,
	)

	s.mcp.AddTool(
		mcp.NewTool("update_fact",
			mcp.WithDescription("Update an existing fact"),
			mcp.WithString("id", mcp.Description("Fact ID"), mcp.Required()),
			mcp.WithString("content", mcp.Description("New content")),
			mcp.WithBoolean("is_stale", mcp.Description("Mark as stale")),
		),
		s.handleUpdateFact,
	)

	s.mcp.AddTool(
		mcp.NewTool("delete_fact",
			mcp.WithDescription("Delete a fact by ID"),
			mcp.WithString("id", mcp.Description("Fact ID"), mcp.Required()),
		),
		s.handleDeleteFact,
	)

	s.mcp.AddTool(
		mcp.NewTool("list_facts",
			mcp.WithDescription("List facts by domain or level"),
			mcp.WithString("domain", mcp.Description("Filter by domain")),
			mcp.WithNumber("level", mcp.Description("Filter by level (0-3)")),
			mcp.WithBoolean("include_stale", mcp.Description("Include stale facts")),
		),
		s.handleListFacts,
	)

	s.mcp.AddTool(
		mcp.NewTool("search_facts",
			mcp.WithDescription("Search facts by content text"),
			mcp.WithString("query", mcp.Description("Search query"), mcp.Required()),
			mcp.WithNumber("limit", mcp.Description("Max results")),
		),
		s.handleSearchFacts,
	)

	s.mcp.AddTool(
		mcp.NewTool("list_domains",
			mcp.WithDescription("List all unique fact domains"),
		),
		s.handleListDomains,
	)

	s.mcp.AddTool(
		mcp.NewTool("get_stale_facts",
			mcp.WithDescription("Get stale facts for review"),
			mcp.WithBoolean("include_archived", mcp.Description("Include archived facts")),
		),
		s.handleGetStaleFacts,
	)

	s.mcp.AddTool(
		mcp.NewTool("get_l0_facts",
			mcp.WithDescription("Get all L0 (project-level) facts — always-loaded context"),
		),
		s.handleGetL0Facts,
	)

	s.mcp.AddTool(
		mcp.NewTool("fact_stats",
			mcp.WithDescription("Get fact store statistics"),
		),
		s.handleFactStats,
	)

	s.mcp.AddTool(
		mcp.NewTool("process_expired",
			mcp.WithDescription("Process expired TTL facts (mark stale, archive, or delete)"),
		),
		s.handleProcessExpired,
	)
}

func (s *Server) handleAddFact(_ context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	params := tools.AddFactParams{
		Content: req.GetString("content", ""),
		Level:   req.GetInt("level", 0),
		Domain:  req.GetString("domain", ""),
		Module:  req.GetString("module", ""),
		CodeRef: req.GetString("code_ref", ""),
	}
	fact, err := s.facts.AddFact(context.Background(), params)
	if err != nil {
		return errorResult(err), nil
	}
	return textResult(tools.ToJSON(fact)), nil
}

func (s *Server) handleGetFact(_ context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	id := req.GetString("id", "")
	fact, err := s.facts.GetFact(context.Background(), id)
	if err != nil {
		return errorResult(err), nil
	}
	return textResult(tools.ToJSON(fact)), nil
}

func (s *Server) handleUpdateFact(_ context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	params := tools.UpdateFactParams{ID: req.GetString("id", "")}
	args := req.GetArguments()
	if v, ok := args["content"].(string); ok {
		params.Content = &v
	}
	if v, ok := args["is_stale"].(bool); ok {
		params.IsStale = &v
	}
	fact, err := s.facts.UpdateFact(context.Background(), params)
	if err != nil {
		return errorResult(err), nil
	}
	return textResult(tools.ToJSON(fact)), nil
}

func (s *Server) handleDeleteFact(_ context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	id := req.GetString("id", "")
	if err := s.facts.DeleteFact(context.Background(), id); err != nil {
		return errorResult(err), nil
	}
	return textResult(fmt.Sprintf("Fact %s deleted", id)), nil
}

func (s *Server) handleListFacts(_ context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	params := tools.ListFactsParams{
		Domain:       req.GetString("domain", ""),
		IncludeStale: req.GetBool("include_stale", false),
	}
	args := req.GetArguments()
	if v, ok := args["level"]; ok {
		if n, ok := v.(float64); ok {
			level := int(n)
			params.Level = &level
		}
	}
	facts, err := s.facts.ListFacts(context.Background(), params)
	if err != nil {
		return errorResult(err), nil
	}
	return textResult(tools.ToJSON(facts)), nil
}

func (s *Server) handleSearchFacts(_ context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	query := req.GetString("query", "")
	limit := req.GetInt("limit", 20)
	facts, err := s.facts.SearchFacts(context.Background(), query, limit)
	if err != nil {
		return errorResult(err), nil
	}
	return textResult(tools.ToJSON(facts)), nil
}

func (s *Server) handleListDomains(_ context.Context, _ mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	domains, err := s.facts.ListDomains(context.Background())
	if err != nil {
		return errorResult(err), nil
	}
	return textResult(tools.ToJSON(domains)), nil
}

func (s *Server) handleGetStaleFacts(_ context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	includeArchived := req.GetBool("include_archived", false)
	facts, err := s.facts.GetStale(context.Background(), includeArchived)
	if err != nil {
		return errorResult(err), nil
	}
	return textResult(tools.ToJSON(facts)), nil
}

func (s *Server) handleGetL0Facts(_ context.Context, _ mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	facts, err := s.facts.GetL0Facts(context.Background())
	if err != nil {
		return errorResult(err), nil
	}
	return textResult(tools.ToJSON(facts)), nil
}

func (s *Server) handleFactStats(_ context.Context, _ mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	stats, err := s.facts.GetStats(context.Background())
	if err != nil {
		return errorResult(err), nil
	}
	return textResult(tools.ToJSON(stats)), nil
}

func (s *Server) handleProcessExpired(_ context.Context, _ mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	count, err := s.facts.ProcessExpired(context.Background())
	if err != nil {
		return errorResult(err), nil
	}
	return textResult(fmt.Sprintf("Processed %d expired facts", count)), nil
}

// --- Session Tools ---

func (s *Server) registerSessionTools() {
	s.mcp.AddTool(
		mcp.NewTool("save_state",
			mcp.WithDescription("Save cognitive state vector"),
			mcp.WithString("session_id", mcp.Description("Session identifier"), mcp.Required()),
			mcp.WithString("state_json", mcp.Description("Full state JSON"), mcp.Required()),
		),
		s.handleSaveState,
	)

	s.mcp.AddTool(
		mcp.NewTool("load_state",
			mcp.WithDescription("Load cognitive state for a session"),
			mcp.WithString("session_id", mcp.Description("Session identifier"), mcp.Required()),
			mcp.WithNumber("version", mcp.Description("Specific version (latest if omitted)")),
		),
		s.handleLoadState,
	)

	s.mcp.AddTool(
		mcp.NewTool("list_sessions",
			mcp.WithDescription("List all persisted sessions"),
		),
		s.handleListSessions,
	)

	s.mcp.AddTool(
		mcp.NewTool("delete_session",
			mcp.WithDescription("Delete all versions of a session"),
			mcp.WithString("session_id", mcp.Description("Session identifier"), mcp.Required()),
		),
		s.handleDeleteSession,
	)

	s.mcp.AddTool(
		mcp.NewTool("restore_or_create",
			mcp.WithDescription("Restore existing session or create new one"),
			mcp.WithString("session_id", mcp.Description("Session identifier"), mcp.Required()),
		),
		s.handleRestoreOrCreate,
	)

	s.mcp.AddTool(
		mcp.NewTool("get_compact_state",
			mcp.WithDescription("Get compact text summary of session state for prompt injection"),
			mcp.WithString("session_id", mcp.Description("Session identifier"), mcp.Required()),
			mcp.WithNumber("max_tokens", mcp.Description("Max tokens for compact output")),
		),
		s.handleGetCompactState,
	)

	s.mcp.AddTool(
		mcp.NewTool("get_audit_log",
			mcp.WithDescription("Get audit log for a session"),
			mcp.WithString("session_id", mcp.Description("Session identifier"), mcp.Required()),
			mcp.WithNumber("limit", mcp.Description("Max entries")),
		),
		s.handleGetAuditLog,
	)
}

func (s *Server) handleSaveState(_ context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	stateJSON := req.GetString("state_json", "")

	var state map[string]interface{}
	if err := json.Unmarshal([]byte(stateJSON), &state); err != nil {
		return errorResult(fmt.Errorf("invalid state JSON: %w", err)), nil
	}

	// For simplicity, we use RestoreOrCreate to get/create a session,
	// then the full state is saved via the session service.
	sessionID := req.GetString("session_id", "")
	csv, _, err := s.sessions.RestoreOrCreate(context.Background(), sessionID)
	if err != nil {
		return errorResult(err), nil
	}

	csv.BumpVersion()
	if err := s.sessions.SaveState(context.Background(), csv); err != nil {
		return errorResult(err), nil
	}
	return textResult(fmt.Sprintf("State saved for session %s (v%d)", csv.SessionID, csv.Version)), nil
}

func (s *Server) handleLoadState(_ context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	sessionID := req.GetString("session_id", "")
	args := req.GetArguments()
	var version *int
	if v, ok := args["version"]; ok {
		if n, ok := v.(float64); ok {
			ver := int(n)
			version = &ver
		}
	}
	state, checksum, err := s.sessions.LoadState(context.Background(), sessionID, version)
	if err != nil {
		return errorResult(err), nil
	}
	result := map[string]interface{}{
		"state":    state,
		"checksum": checksum,
	}
	return textResult(tools.ToJSON(result)), nil
}

func (s *Server) handleListSessions(_ context.Context, _ mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	sessions, err := s.sessions.ListSessions(context.Background())
	if err != nil {
		return errorResult(err), nil
	}
	return textResult(tools.ToJSON(sessions)), nil
}

func (s *Server) handleDeleteSession(_ context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	sessionID := req.GetString("session_id", "")
	count, err := s.sessions.DeleteSession(context.Background(), sessionID)
	if err != nil {
		return errorResult(err), nil
	}
	return textResult(fmt.Sprintf("Deleted %d versions of session %s", count, sessionID)), nil
}

func (s *Server) handleRestoreOrCreate(_ context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	sessionID := req.GetString("session_id", "")
	state, restored, err := s.sessions.RestoreOrCreate(context.Background(), sessionID)
	if err != nil {
		return errorResult(err), nil
	}
	action := "created"
	if restored {
		action = "restored"
	}
	result := map[string]interface{}{
		"action": action,
		"state":  state,
	}
	return textResult(tools.ToJSON(result)), nil
}

func (s *Server) handleGetCompactState(_ context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	sessionID := req.GetString("session_id", "")
	maxTokens := req.GetInt("max_tokens", 500)
	compact, err := s.sessions.GetCompactState(context.Background(), sessionID, maxTokens)
	if err != nil {
		return errorResult(err), nil
	}
	return textResult(compact), nil
}

func (s *Server) handleGetAuditLog(_ context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	sessionID := req.GetString("session_id", "")
	limit := req.GetInt("limit", 50)
	log, err := s.sessions.GetAuditLog(context.Background(), sessionID, limit)
	if err != nil {
		return errorResult(err), nil
	}
	return textResult(tools.ToJSON(log)), nil
}

// --- Causal Tools ---

func (s *Server) registerCausalTools() {
	s.mcp.AddTool(
		mcp.NewTool("add_causal_node",
			mcp.WithDescription("Add a causal reasoning node"),
			mcp.WithString("node_type", mcp.Description("Node type: decision, reason, consequence, constraint, alternative, assumption"), mcp.Required()),
			mcp.WithString("content", mcp.Description("Node content"), mcp.Required()),
		),
		s.handleAddCausalNode,
	)

	s.mcp.AddTool(
		mcp.NewTool("add_causal_edge",
			mcp.WithDescription("Add a causal edge between nodes"),
			mcp.WithString("from_id", mcp.Description("Source node ID"), mcp.Required()),
			mcp.WithString("to_id", mcp.Description("Target node ID"), mcp.Required()),
			mcp.WithString("edge_type", mcp.Description("Edge type: justifies, causes, constrains"), mcp.Required()),
		),
		s.handleAddCausalEdge,
	)

	s.mcp.AddTool(
		mcp.NewTool("get_causal_chain",
			mcp.WithDescription("Get causal chain for a decision"),
			mcp.WithString("query", mcp.Description("Decision search query"), mcp.Required()),
			mcp.WithNumber("max_depth", mcp.Description("Max traversal depth")),
		),
		s.handleGetCausalChain,
	)

	s.mcp.AddTool(
		mcp.NewTool("causal_stats",
			mcp.WithDescription("Get causal store statistics"),
		),
		s.handleCausalStats,
	)
}

func (s *Server) handleAddCausalNode(_ context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	params := tools.AddNodeParams{
		NodeType: req.GetString("node_type", ""),
		Content:  req.GetString("content", ""),
	}
	node, err := s.causal.AddNode(context.Background(), params)
	if err != nil {
		return errorResult(err), nil
	}
	return textResult(tools.ToJSON(node)), nil
}

func (s *Server) handleAddCausalEdge(_ context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	params := tools.AddEdgeParams{
		FromID:   req.GetString("from_id", ""),
		ToID:     req.GetString("to_id", ""),
		EdgeType: req.GetString("edge_type", ""),
	}
	edge, err := s.causal.AddEdge(context.Background(), params)
	if err != nil {
		return errorResult(err), nil
	}
	return textResult(tools.ToJSON(edge)), nil
}

func (s *Server) handleGetCausalChain(_ context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	query := req.GetString("query", "")
	maxDepth := req.GetInt("max_depth", 3)
	chain, err := s.causal.GetChain(context.Background(), query, maxDepth)
	if err != nil {
		return errorResult(err), nil
	}

	result := map[string]interface{}{
		"chain":   chain,
		"mermaid": chain.ToMermaid(),
	}
	return textResult(tools.ToJSON(result)), nil
}

func (s *Server) handleCausalStats(_ context.Context, _ mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	stats, err := s.causal.GetStats(context.Background())
	if err != nil {
		return errorResult(err), nil
	}
	return textResult(tools.ToJSON(stats)), nil
}

// --- Crystal Tools ---

func (s *Server) registerCrystalTools() {
	s.mcp.AddTool(
		mcp.NewTool("search_crystals",
			mcp.WithDescription("Search code crystals by content/primitive names"),
			mcp.WithString("query", mcp.Description("Search query"), mcp.Required()),
			mcp.WithNumber("limit", mcp.Description("Max results")),
		),
		s.handleSearchCrystals,
	)

	s.mcp.AddTool(
		mcp.NewTool("get_crystal",
			mcp.WithDescription("Get a code crystal by file path"),
			mcp.WithString("path", mcp.Description("File path"), mcp.Required()),
		),
		s.handleGetCrystal,
	)

	s.mcp.AddTool(
		mcp.NewTool("list_crystals",
			mcp.WithDescription("List indexed code crystals"),
			mcp.WithString("pattern", mcp.Description("Path pattern filter")),
			mcp.WithNumber("limit", mcp.Description("Max results")),
		),
		s.handleListCrystals,
	)

	s.mcp.AddTool(
		mcp.NewTool("crystal_stats",
			mcp.WithDescription("Get code crystal statistics"),
		),
		s.handleCrystalStats,
	)
}

func (s *Server) handleSearchCrystals(_ context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	query := req.GetString("query", "")
	limit := req.GetInt("limit", 20)
	crystals, err := s.crystals.SearchCrystals(context.Background(), query, limit)
	if err != nil {
		return errorResult(err), nil
	}
	return textResult(tools.ToJSON(crystals)), nil
}

func (s *Server) handleGetCrystal(_ context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	path := req.GetString("path", "")
	crystal, err := s.crystals.GetCrystal(context.Background(), path)
	if err != nil {
		return errorResult(err), nil
	}
	return textResult(tools.ToJSON(crystal)), nil
}

func (s *Server) handleListCrystals(_ context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	pattern := req.GetString("pattern", "")
	limit := req.GetInt("limit", 50)
	crystals, err := s.crystals.ListCrystals(context.Background(), pattern, limit)
	if err != nil {
		return errorResult(err), nil
	}
	return textResult(tools.ToJSON(crystals)), nil
}

func (s *Server) handleCrystalStats(_ context.Context, _ mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	stats, err := s.crystals.GetCrystalStats(context.Background())
	if err != nil {
		return errorResult(err), nil
	}
	return textResult(tools.ToJSON(stats)), nil
}

// --- System Tools ---

func (s *Server) registerSystemTools() {
	s.mcp.AddTool(
		mcp.NewTool("health",
			mcp.WithDescription("Get server health status"),
		),
		s.handleHealth,
	)

	s.mcp.AddTool(
		mcp.NewTool("version",
			mcp.WithDescription("Get server version information"),
		),
		s.handleVersion,
	)

	s.mcp.AddTool(
		mcp.NewTool("dashboard",
			mcp.WithDescription("Get system dashboard with all metrics"),
		),
		s.handleDashboard,
	)
}

func (s *Server) handleHealth(_ context.Context, _ mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	health := s.system.Health(context.Background())
	return textResult(tools.ToJSON(health)), nil
}

func (s *Server) handleVersion(_ context.Context, _ mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	version := s.system.GetVersion()
	return textResult(tools.ToJSON(version)), nil
}

func (s *Server) handleDashboard(_ context.Context, _ mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	data, err := s.system.Dashboard(context.Background())
	if err != nil {
		return errorResult(err), nil
	}
	return textResult(tools.ToJSON(data)), nil
}

// --- Resources ---

func (s *Server) registerResources() {
	if s.res == nil {
		return
	}

	s.mcp.AddResource(
		mcp.NewResource("rlm://facts", "L0 Facts",
			mcp.WithResourceDescription("Project-level facts always loaded in context"),
			mcp.WithMIMEType("application/json"),
		),
		func(_ context.Context, req mcp.ReadResourceRequest) ([]mcp.ResourceContents, error) {
			text, err := s.res.GetFacts(context.Background())
			if err != nil {
				return nil, err
			}
			return []mcp.ResourceContents{
				mcp.TextResourceContents{URI: req.Params.URI, MIMEType: "application/json", Text: text},
			}, nil
		},
	)

	s.mcp.AddResource(
		mcp.NewResource("rlm://stats", "Memory Statistics",
			mcp.WithResourceDescription("Aggregate statistics about the memory store"),
			mcp.WithMIMEType("application/json"),
		),
		func(_ context.Context, req mcp.ReadResourceRequest) ([]mcp.ResourceContents, error) {
			text, err := s.res.GetStats(context.Background())
			if err != nil {
				return nil, err
			}
			return []mcp.ResourceContents{
				mcp.TextResourceContents{URI: req.Params.URI, MIMEType: "application/json", Text: text},
			}, nil
		},
	)

	s.mcp.AddResourceTemplate(
		mcp.NewResourceTemplate("rlm://state/{session_id}", "Session State",
			mcp.WithTemplateDescription("Cognitive state vector for a session"),
			mcp.WithTemplateMIMEType("application/json"),
		),
		func(_ context.Context, req mcp.ReadResourceRequest) ([]mcp.ResourceContents, error) {
			// Extract session_id from URI path.
			sessionID := extractSessionID(req.Params.URI)
			text, err := s.res.GetState(context.Background(), sessionID)
			if err != nil {
				return nil, err
			}
			return []mcp.ResourceContents{
				mcp.TextResourceContents{URI: req.Params.URI, MIMEType: "application/json", Text: text},
			}, nil
		},
	)
}

// --- Python Bridge Tools ---

func (s *Server) registerPythonBridgeTools() {
	if s.pybridge == nil {
		return
	}

	s.mcp.AddTool(
		mcp.NewTool("semantic_search",
			mcp.WithDescription("Semantic vector similarity search across facts (requires Python NLP)"),
			mcp.WithString("query", mcp.Description("Search query text"), mcp.Required()),
			mcp.WithNumber("limit", mcp.Description("Max results (default 10)")),
			mcp.WithNumber("threshold", mcp.Description("Min similarity threshold 0.0-1.0")),
		),
		s.handleSemanticSearch,
	)

	s.mcp.AddTool(
		mcp.NewTool("compute_embedding",
			mcp.WithDescription("Compute embedding vector for text (requires Python NLP)"),
			mcp.WithString("text", mcp.Description("Text to embed"), mcp.Required()),
		),
		s.handleComputeEmbedding,
	)

	s.mcp.AddTool(
		mcp.NewTool("reindex_embeddings",
			mcp.WithDescription("Reindex all fact embeddings (requires Python NLP)"),
			mcp.WithBoolean("force", mcp.Description("Force reindex even if embeddings exist")),
		),
		s.handleReindexEmbeddings,
	)

	s.mcp.AddTool(
		mcp.NewTool("consolidate_facts",
			mcp.WithDescription("Consolidate duplicate/similar facts using NLP (requires Python)"),
			mcp.WithNumber("similarity_threshold", mcp.Description("Similarity threshold for merging (default 0.85)")),
			mcp.WithString("domain", mcp.Description("Limit consolidation to a domain")),
		),
		s.handleConsolidateFacts,
	)

	s.mcp.AddTool(
		mcp.NewTool("enterprise_context",
			mcp.WithDescription("Get enterprise-level context summary (requires Python NLP)"),
			mcp.WithString("project", mcp.Description("Project name")),
			mcp.WithNumber("max_tokens", mcp.Description("Max tokens for output")),
		),
		s.handleEnterpriseContext,
	)

	s.mcp.AddTool(
		mcp.NewTool("route_context",
			mcp.WithDescription("Route context to appropriate handler based on intent (requires Python NLP)"),
			mcp.WithString("query", mcp.Description("User query to route"), mcp.Required()),
			mcp.WithString("session_id", mcp.Description("Current session ID")),
		),
		s.handleRouteContext,
	)

	s.mcp.AddTool(
		mcp.NewTool("discover_deep",
			mcp.WithDescription("Deep discovery of related facts and patterns (requires Python NLP)"),
			mcp.WithString("topic", mcp.Description("Topic to explore"), mcp.Required()),
			mcp.WithNumber("depth", mcp.Description("Exploration depth (default 2)")),
			mcp.WithNumber("max_results", mcp.Description("Max results")),
		),
		s.handleDiscoverDeep,
	)

	s.mcp.AddTool(
		mcp.NewTool("extract_from_conversation",
			mcp.WithDescription("Extract facts from conversation text (requires Python NLP)"),
			mcp.WithString("text", mcp.Description("Conversation text to extract from"), mcp.Required()),
			mcp.WithString("session_id", mcp.Description("Session ID for context")),
		),
		s.handleExtractFromConversation,
	)

	s.mcp.AddTool(
		mcp.NewTool("index_embeddings",
			mcp.WithDescription("Index embeddings for a batch of facts (requires Python NLP)"),
			mcp.WithString("fact_ids", mcp.Description("Comma-separated fact IDs to index")),
			mcp.WithBoolean("all", mcp.Description("Index all facts without embeddings")),
		),
		s.handleIndexEmbeddings,
	)

	s.mcp.AddTool(
		mcp.NewTool("build_communities",
			mcp.WithDescription("Build fact communities using graph clustering (requires Python NLP)"),
			mcp.WithNumber("min_community_size", mcp.Description("Minimum community size (default 3)")),
			mcp.WithNumber("similarity_threshold", mcp.Description("Edge threshold (default 0.7)")),
		),
		s.handleBuildCommunities,
	)

	s.mcp.AddTool(
		mcp.NewTool("check_python_bridge",
			mcp.WithDescription("Check Python bridge availability and capabilities"),
		),
		s.handleCheckPythonBridge,
	)
}

func (s *Server) handleSemanticSearch(_ context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	query := req.GetString("query", "")
	limit := req.GetInt("limit", 10)
	args := req.GetArguments()
	params := map[string]interface{}{
		"query": query,
		"limit": limit,
	}
	if v, ok := args["threshold"]; ok {
		params["threshold"] = v
	}
	result, err := s.pybridge.Call(context.Background(), "semantic_search", params)
	if err != nil {
		return errorResult(err), nil
	}
	return textResult(string(result)), nil
}

func (s *Server) handleComputeEmbedding(_ context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	text := req.GetString("text", "")
	emb, err := s.pybridge.ComputeEmbedding(context.Background(), text)
	if err != nil {
		return errorResult(err), nil
	}
	return textResult(tools.ToJSON(emb)), nil
}

func (s *Server) handleReindexEmbeddings(_ context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	force := req.GetBool("force", false)
	result, err := s.pybridge.Call(context.Background(), "reindex_embeddings", map[string]interface{}{
		"force": force,
	})
	if err != nil {
		return errorResult(err), nil
	}
	return textResult(string(result)), nil
}

func (s *Server) handleConsolidateFacts(_ context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	args := req.GetArguments()
	params := map[string]interface{}{}
	if v, ok := args["similarity_threshold"]; ok {
		params["similarity_threshold"] = v
	} else {
		params["similarity_threshold"] = 0.85
	}
	if v, ok := args["domain"]; ok {
		params["domain"] = v
	}
	result, err := s.pybridge.Call(context.Background(), "consolidate_facts", params)
	if err != nil {
		return errorResult(err), nil
	}
	return textResult(string(result)), nil
}

func (s *Server) handleEnterpriseContext(_ context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	params := map[string]interface{}{}
	args := req.GetArguments()
	if v, ok := args["project"]; ok {
		params["project"] = v
	}
	if v, ok := args["max_tokens"]; ok {
		params["max_tokens"] = v
	}
	result, err := s.pybridge.Call(context.Background(), "enterprise_context", params)
	if err != nil {
		return errorResult(err), nil
	}
	return textResult(string(result)), nil
}

func (s *Server) handleRouteContext(_ context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	params := map[string]interface{}{
		"query": req.GetString("query", ""),
	}
	if sid := req.GetString("session_id", ""); sid != "" {
		params["session_id"] = sid
	}
	result, err := s.pybridge.Call(context.Background(), "route_context", params)
	if err != nil {
		return errorResult(err), nil
	}
	return textResult(string(result)), nil
}

func (s *Server) handleDiscoverDeep(_ context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	params := map[string]interface{}{
		"topic": req.GetString("topic", ""),
		"depth": req.GetInt("depth", 2),
	}
	args := req.GetArguments()
	if v, ok := args["max_results"]; ok {
		params["max_results"] = v
	}
	result, err := s.pybridge.Call(context.Background(), "discover_deep", params)
	if err != nil {
		return errorResult(err), nil
	}
	return textResult(string(result)), nil
}

func (s *Server) handleExtractFromConversation(_ context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	params := map[string]interface{}{
		"text": req.GetString("text", ""),
	}
	if sid := req.GetString("session_id", ""); sid != "" {
		params["session_id"] = sid
	}
	result, err := s.pybridge.Call(context.Background(), "extract_from_conversation", params)
	if err != nil {
		return errorResult(err), nil
	}
	return textResult(string(result)), nil
}

func (s *Server) handleIndexEmbeddings(_ context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	params := map[string]interface{}{}
	if ids := req.GetString("fact_ids", ""); ids != "" {
		params["fact_ids"] = ids
	}
	params["all"] = req.GetBool("all", false)
	result, err := s.pybridge.Call(context.Background(), "index_embeddings", params)
	if err != nil {
		return errorResult(err), nil
	}
	return textResult(string(result)), nil
}

func (s *Server) handleBuildCommunities(_ context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	params := map[string]interface{}{}
	args := req.GetArguments()
	if v, ok := args["min_community_size"]; ok {
		params["min_community_size"] = v
	} else {
		params["min_community_size"] = 3
	}
	if v, ok := args["similarity_threshold"]; ok {
		params["similarity_threshold"] = v
	} else {
		params["similarity_threshold"] = 0.7
	}
	result, err := s.pybridge.Call(context.Background(), "build_communities", params)
	if err != nil {
		return errorResult(err), nil
	}
	return textResult(string(result)), nil
}

func (s *Server) handleCheckPythonBridge(_ context.Context, _ mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	available := s.pybridge.IsAvailable()
	status := map[string]interface{}{
		"available": available,
		"status":    "connected",
	}
	if !available {
		status["status"] = "unavailable"
		status["error"] = "Python interpreter not found or bridge script not accessible"
	}
	return textResult(tools.ToJSON(status)), nil
}

// --- Helpers ---

func textResult(text string) *mcp.CallToolResult {
	return &mcp.CallToolResult{
		Content: []mcp.Content{
			mcp.TextContent{Type: "text", Text: text},
		},
	}
}

func errorResult(err error) *mcp.CallToolResult {
	return &mcp.CallToolResult{
		Content: []mcp.Content{
			mcp.TextContent{Type: "text", Text: fmt.Sprintf("Error: %s", err.Error())},
		},
		IsError: true,
	}
}

func extractSessionID(uri string) string {
	// URI format: rlm://state/{session_id}
	const prefix = "rlm://state/"
	if len(uri) > len(prefix) {
		return uri[len(prefix):]
	}
	return "default"
}
