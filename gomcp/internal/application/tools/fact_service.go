// Package tools provides application-level tool services that bridge
// domain logic with MCP tool handlers.
package tools

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"

	"github.com/syntrex/gomcp/internal/domain/memory"
	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
	"github.com/syntrex/gomcp/internal/domain/synapse"
	"github.com/syntrex/gomcp/internal/domain/vectorstore"
)

var errSessionFactBoundary = errors.New("session fact store boundary violation")

// FactService implements MCP tool logic for hierarchical fact operations.
type FactService struct {
	store    memory.FactStore
	cache    memory.HotCache
	synapses synapse.SynapseStore
	recorder DecisionRecorder     // v3.7: tamper-evident trace
	embedder vectorstore.Embedder // optional: enables semantic + hybrid search
}

// SetDecisionRecorder injects the decision recorder.
func (s *FactService) SetDecisionRecorder(r DecisionRecorder) {
	s.recorder = r
}

// SetEmbedder injects an embedder for semantic search.
// nil disables semantic mode; SearchFacts then falls back to keyword.
func (s *FactService) SetEmbedder(e vectorstore.Embedder) {
	s.embedder = e
}

// HasEmbedder reports whether semantic search is currently available.
func (s *FactService) HasEmbedder() bool {
	return s.embedder != nil
}

// WithSynapseStore enables verified synapse expansion for hybrid retrieval.
func (s *FactService) WithSynapseStore(store synapse.SynapseStore) *FactService {
	s.synapses = store
	return s
}

// NewFactService creates a new FactService.
func NewFactService(store memory.FactStore, cache memory.HotCache) *FactService {
	return &FactService{store: store, cache: cache}
}

func (s *FactService) sessionStore(ctx context.Context, sessionID string) (memory.SessionFactStore, error) {
	if _, err := rlmscope.RequireSessionScope(ctx, sessionID); err != nil {
		return nil, err
	}
	store, ok := s.store.(memory.SessionFactStore)
	if !ok {
		return nil, fmt.Errorf("session memory is unavailable: fact store does not support exact session isolation")
	}
	return store, nil
}

func validateSessionFacts(ctx context.Context, sessionID string, facts ...*memory.Fact) error {
	sc, err := rlmscope.RequireSessionScope(ctx, sessionID)
	if err != nil {
		return err
	}
	for _, fact := range facts {
		if fact == nil {
			return fmt.Errorf("%w: nil fact", errSessionFactBoundary)
		}
		if fact.TenantID != sc.TenantID || fact.ProjectID != sc.ProjectID || fact.SessionID != sessionID {
			return fmt.Errorf("%w: fact outside the exact tenant/project/session boundary", errSessionFactBoundary)
		}
	}
	return nil
}

// AddFactParams holds parameters for the add_fact tool.
type AddFactParams struct {
	Content string `json:"content"`
	Level   int    `json:"level"`
	Domain  string `json:"domain,omitempty"`
	Module  string `json:"module,omitempty"`
	CodeRef string `json:"code_ref,omitempty"`
	// TurnID is used only by AddSessionTurn. It is a content-free operation
	// identifier used to reconcile a lost acknowledgement.
	TurnID string `json:"turn_id,omitempty"`
	// Origin is where the CONTENT came from, on the trust axis. See memory.Origin.
	//
	// Optional in the wire schema and NOT defaulted to OriginUser. `add_fact` is a tool an
	// AGENT calls, and an agent calls it for two indistinguishable reasons: the user asked it
	// to remember something, or a document it just read told it to. Treating an unstated origin
	// as user-authored is precisely the assumption that makes `memory/persist` and
	// `memory/tamper` undecidable, so an unstated origin degrades to OriginExternal — the
	// conservative reading of «an agent decided to write this and did not say why».
	//
	// A caller that genuinely relays a human instruction says so explicitly, which is a claim
	// it is then accountable for.
	Origin string `json:"origin,omitempty"`
}

// StoreProjectFactExactParams is intentionally narrower than AddFactParams.
// Every accepted field is part of the exact collision comparison; fields that
// the public project store endpoint cannot attest are not accepted here.
type StoreProjectFactExactParams struct {
	Content string `json:"content"`
	Level   int    `json:"level"`
	Domain  string `json:"domain,omitempty"`
	Module  string `json:"module,omitempty"`
	Origin  string `json:"origin,omitempty"`
}

// resolveOrigin maps the wire value to the enum, failing SAFE rather than open.
//
// Empty → OriginExternal, not OriginUser: see the note on AddFactParams.Origin. An unrecognised
// string is also OriginExternal rather than an error, because refusing the write would lose the
// fact entirely, and a fact stored with the least trust is strictly better than no fact plus a
// caller that retries without the field.
func resolveOrigin(raw string) memory.Origin {
	candidate := memory.Origin(raw)
	if raw == "" || !candidate.IsValid() || candidate == memory.OriginUnspecified {
		return memory.OriginExternal
	}
	return candidate
}

// AddFact creates a new hierarchical fact.
func (s *FactService) AddFact(ctx context.Context, params AddFactParams) (*memory.Fact, error) {
	level, ok := memory.HierLevelFromInt(params.Level)
	if !ok {
		return nil, fmt.Errorf("invalid level %d, must be 0-3", params.Level)
	}

	fact := memory.NewFact(params.Content, level, params.Domain, params.Module)
	fact.CodeRef = params.CodeRef
	fact.Source = "add_fact"
	fact.Origin = resolveOrigin(params.Origin)

	if err := fact.Validate(); err != nil {
		return nil, fmt.Errorf("validate fact: %w", err)
	}
	s.attachEmbedding(ctx, fact)
	if err := s.store.Add(ctx, fact); err != nil {
		return nil, fmt.Errorf("store fact: %w", err)
	}

	// Invalidate cache if L0 fact.
	if level == memory.LevelProject && s.cache != nil {
		if err := s.cache.InvalidateFact(ctx, fact.ID); err != nil {
			return fact, fmt.Errorf("fact %s stored but cache invalidation failed: %w", fact.ID, err)
		}
	}

	return fact, nil
}

func exactProjectOrigin(raw string) (memory.Origin, error) {
	if raw == "" {
		return memory.OriginExternal, nil
	}
	candidate := memory.Origin(raw)
	switch candidate {
	case memory.OriginUser, memory.OriginDerived, memory.OriginExternal:
		return candidate, nil
	default:
		return "", fmt.Errorf("origin must be user, derived, or external")
	}
}

// StoreProjectFactExact stores one non-session fact without invoking legacy
// folding. A collision is either a read-only replay of the durable row or a
// typed conflict; the service never returns the newly allocated request Fact.
func (s *FactService) StoreProjectFactExact(
	ctx context.Context,
	params StoreProjectFactExactParams,
) (*memory.Fact, bool, error) {
	sc, err := rlmscope.RequireExactProject(ctx)
	if err != nil {
		return nil, false, err
	}
	level, ok := memory.HierLevelFromInt(params.Level)
	if !ok {
		return nil, false, fmt.Errorf("invalid level %d, must be 0-3", params.Level)
	}
	origin, err := exactProjectOrigin(params.Origin)
	if err != nil {
		return nil, false, err
	}
	store, ok := s.store.(memory.ProjectExactFactStore)
	if !ok {
		return nil, false, fmt.Errorf("exact project fact store is unavailable")
	}

	pending := memory.NewFact(params.Content, level, params.Domain, params.Module)
	pending.Source = "add_fact"
	pending.Origin = origin
	if err := pending.Validate(); err != nil {
		return nil, false, fmt.Errorf("validate exact project fact: %w", err)
	}
	s.attachEmbedding(ctx, pending)

	stored, created, err := store.StoreProjectFactExact(ctx, pending)
	if err != nil {
		return nil, false, err
	}
	if stored == nil || stored.TenantID != sc.TenantID || stored.ProjectID != sc.ProjectID ||
		stored.SessionID != "" || stored.Content != params.Content || stored.Level != level ||
		stored.Domain != params.Domain || stored.Module != params.Module || stored.Origin != origin {
		return nil, false, fmt.Errorf("%w: store returned a row outside the exact request", memory.ErrExactFactIntegrity)
	}

	if created && level == memory.LevelProject && s.cache != nil {
		_ = s.cache.InvalidateFact(ctx, stored.ID)
	}
	return stored, created, nil
}

func (s *FactService) buildSessionFact(ctx context.Context, sessionID string, params AddFactParams) (*memory.Fact, error) {
	level, ok := memory.HierLevelFromInt(params.Level)
	if !ok {
		return nil, fmt.Errorf("invalid level %d, must be 0-3", params.Level)
	}

	fact := memory.NewFact(params.Content, level, params.Domain, params.Module)
	fact.CodeRef = params.CodeRef
	fact.Source = "session_memory"
	fact.Origin = resolveOrigin(params.Origin)
	fact.SessionID = sessionID
	if err := fact.Validate(); err != nil {
		return nil, fmt.Errorf("validate session fact: %w", err)
	}
	s.attachEmbedding(ctx, fact)
	return fact, nil
}

// AddSessionFact preserves the original unkeyed session-memory contract.
// It creates a fact that is addressable only through the exact
// tenant/project/session memory surface, without imposing turn receipts on
// callers that predate the idempotency extension.
func (s *FactService) AddSessionFact(ctx context.Context, sessionID string, params AddFactParams) (*memory.Fact, error) {
	store, err := s.sessionStore(ctx, sessionID)
	if err != nil {
		return nil, err
	}
	fact, err := s.buildSessionFact(ctx, sessionID, params)
	if err != nil {
		return nil, err
	}
	if err := store.AddForSession(ctx, sessionID, fact); err != nil {
		return nil, fmt.Errorf("store session fact: %w", err)
	}
	if err := validateSessionFacts(ctx, sessionID, fact); err != nil {
		return nil, err
	}
	return fact, nil
}

// AddSessionTurn adds receipt-backed idempotency to session memory for callers
// that explicitly supply a turn identifier. Legacy AddSessionFact callers keep
// their prior store semantics and return type.
func (s *FactService) AddSessionTurn(
	ctx context.Context,
	sessionID string,
	params AddFactParams,
) (*memory.Fact, *memory.SessionTurnReceipt, bool, error) {
	store, err := s.sessionStore(ctx, sessionID)
	if err != nil {
		return nil, nil, false, err
	}
	if err := rlmscope.ValidateTurnID(params.TurnID); err != nil {
		return nil, nil, false, err
	}
	fact, err := s.buildSessionFact(ctx, sessionID, params)
	if err != nil {
		return nil, nil, false, err
	}
	receipt, deduplicated, err := store.AddTurnForSession(ctx, sessionID, params.TurnID, fact)
	if err != nil {
		return nil, nil, false, fmt.Errorf("store session fact: %w", err)
	}
	if err := validateSessionFacts(ctx, sessionID, fact); err != nil {
		return nil, nil, false, err
	}
	if err := validateSessionTurnReceipt(receipt, params.TurnID, fact); err != nil {
		return nil, nil, false, err
	}
	return fact, receipt, deduplicated, nil
}

func validateSessionTurnReceipt(receipt *memory.SessionTurnReceipt, turnID string, fact *memory.Fact) error {
	if receipt == nil || fact == nil || receipt.Version != 1 || receipt.TurnID != turnID ||
		receipt.FactID != fact.ID || len(receipt.PayloadSHA256) != 64 {
		return memory.ErrSessionTurnIntegrity
	}
	for _, char := range receipt.PayloadSHA256 {
		if !((char >= '0' && char <= '9') || (char >= 'a' && char <= 'f')) {
			return memory.ErrSessionTurnIntegrity
		}
	}
	return nil
}

// GetSessionTurn is the read-only reconciliation surface used after an
// ambiguous transport outcome. Absence is returned as nil receipt/fact.
func (s *FactService) GetSessionTurn(
	ctx context.Context,
	sessionID, turnID string,
) (*memory.SessionTurnReceipt, *memory.Fact, error) {
	store, err := s.sessionStore(ctx, sessionID)
	if err != nil {
		return nil, nil, err
	}
	if err := rlmscope.ValidateTurnID(turnID); err != nil {
		return nil, nil, err
	}
	receipt, fact, err := store.GetTurnForSession(ctx, sessionID, turnID)
	if err != nil {
		return nil, nil, err
	}
	if receipt == nil && fact == nil {
		return nil, nil, nil
	}
	if receipt == nil || fact == nil {
		return nil, nil, memory.ErrSessionTurnIntegrity
	}
	if err := validateSessionFacts(ctx, sessionID, fact); err != nil {
		return nil, nil, err
	}
	if err := validateSessionTurnReceipt(receipt, turnID, fact); err != nil {
		return nil, nil, err
	}
	return receipt, fact, nil
}

// attachEmbedding embeds fact.Content into fact.Embedding when an embedder
// is configured and the fact has no embedding yet. Failures are swallowed —
// memory persistence must not depend on embedder availability.
func (s *FactService) attachEmbedding(ctx context.Context, fact *memory.Fact) {
	if s.embedder == nil || fact == nil || len(fact.Embedding) > 0 || fact.Content == "" {
		return
	}
	vec, err := s.embedder.Embed(ctx, fact.Content)
	if err != nil || len(vec) == 0 {
		return
	}
	fact.Embedding = vec
}

// AddGeneParams holds parameters for the add_gene tool.
type AddGeneParams struct {
	Content string `json:"content"`
	Domain  string `json:"domain,omitempty"`
}

// AddGene creates an immutable genome fact (L0 only).
// Once created, a gene cannot be updated, deleted, or marked stale.
// Genes represent survival invariants — the DNA of the system.
func (s *FactService) AddGene(ctx context.Context, params AddGeneParams) (*memory.Fact, error) {
	gene := memory.NewGene(params.Content, params.Domain)
	gene.Origin = memory.OriginDerived

	if err := gene.Validate(); err != nil {
		return nil, fmt.Errorf("validate gene: %w", err)
	}
	s.attachEmbedding(ctx, gene)
	if err := s.store.Add(ctx, gene); err != nil {
		return nil, fmt.Errorf("store gene: %w", err)
	}

	// Invalidate L0 cache — genes are always L0.
	if s.cache != nil {
		_ = s.cache.InvalidateFact(ctx, gene.ID)
	}

	return gene, nil
}

// GetFact retrieves a fact by ID.
func (s *FactService) GetFact(ctx context.Context, id string) (*memory.Fact, error) {
	return s.store.Get(ctx, id)
}

// UpdateFactParams holds parameters for the update_fact tool.
type UpdateFactParams struct {
	ID      string  `json:"id"`
	Content *string `json:"content,omitempty"`
	IsStale *bool   `json:"is_stale,omitempty"`
}

// UpdateFact updates a fact.
func (s *FactService) UpdateFact(ctx context.Context, params UpdateFactParams) (*memory.Fact, error) {
	fact, err := s.store.Get(ctx, params.ID)
	if err != nil {
		return nil, err
	}

	// Genome Layer: block mutation of genes.
	if fact.IsImmutable() {
		return nil, memory.ErrImmutableFact
	}

	if params.Content != nil && *params.Content != fact.Content {
		fact.Content = *params.Content
		// A caller-provided replacement is a new assertion, not evidence for
		// the provenance of the previous bytes. Preserve lower trust only.
		fact.Origin = memory.LeastTrusted(fact.Origin, memory.OriginDerived)
	}
	if params.IsStale != nil {
		fact.IsStale = *params.IsStale
	}

	if err := s.store.Update(ctx, fact); err != nil {
		return nil, err
	}

	if fact.Level == memory.LevelProject && s.cache != nil {
		_ = s.cache.InvalidateFact(ctx, fact.ID)
	}

	return fact, nil
}

// DeleteFact deletes a fact by ID.
func (s *FactService) DeleteFact(ctx context.Context, id string) error {
	// Genome Layer: block deletion of genes.
	fact, err := s.store.Get(ctx, id)
	if err != nil {
		return err
	}
	if fact.IsImmutable() {
		return memory.ErrImmutableFact
	}

	if s.cache != nil {
		_ = s.cache.InvalidateFact(ctx, id)
	}
	return s.store.Delete(ctx, id)
}

// ListFactsParams holds parameters for the list_facts tool.
type ListFactsParams struct {
	Domain       string `json:"domain,omitempty"`
	Level        *int   `json:"level,omitempty"`
	IncludeStale bool   `json:"include_stale,omitempty"`
}

// ListFacts lists facts by domain or level.
func (s *FactService) ListFacts(ctx context.Context, params ListFactsParams) ([]*memory.Fact, error) {
	if params.Domain != "" {
		return s.store.ListByDomain(ctx, params.Domain, params.IncludeStale)
	}
	if params.Level != nil {
		level, ok := memory.HierLevelFromInt(*params.Level)
		if !ok {
			return nil, fmt.Errorf("invalid level %d", *params.Level)
		}
		return s.store.ListByLevel(ctx, level)
	}
	// Default: return L0 facts.
	return s.store.ListByLevel(ctx, memory.LevelProject)
}

// ListFactsPage returns one exact-project SQLite keyset step. It is separate
// from ListFacts so the legacy tool retains its historical unbounded JSON/text
// contract while the gateway can opt in to a bounded wire protocol.
func (s *FactService) ListFactsPage(
	ctx context.Context,
	level int,
	maxFactBytes int,
	snapshot int64,
	expectedCount int64,
	after *memory.FactPageKey,
) (*memory.FactPage, error) {
	hierLevel, ok := memory.HierLevelFromInt(level)
	if !ok {
		return nil, fmt.Errorf("invalid level %d", level)
	}
	store, ok := s.store.(memory.ExactFactPageStore)
	if !ok {
		return nil, fmt.Errorf("exact fact pagination is unavailable for this store")
	}
	return store.ListByLevelPage(ctx, hierLevel, maxFactBytes, snapshot, expectedCount, after)
}

// GetFactPageRecord reloads an in-progress framed fact under the same exact
// scope, level, snapshot and key that produced its cursor.
func (s *FactService) GetFactPageRecord(
	ctx context.Context,
	level int,
	maxFactBytes int,
	snapshot int64,
	expectedCount int64,
	key memory.FactPageKey,
	offset int,
) (*memory.FactPageRecord, error) {
	hierLevel, ok := memory.HierLevelFromInt(level)
	if !ok {
		return nil, fmt.Errorf("invalid level %d", level)
	}
	store, ok := s.store.(memory.ExactFactPageStore)
	if !ok {
		return nil, fmt.Errorf("exact fact pagination is unavailable for this store")
	}
	return store.GetByLevelPageKey(ctx, hierLevel, maxFactBytes, snapshot, expectedCount, key, offset)
}

// ReleaseFactPage drops one completed process-local manifest and its cached
// canonical payload. The exact scope and level are rechecked by the store.
func (s *FactService) ReleaseFactPage(
	ctx context.Context,
	level int,
	key memory.FactPageKey,
) error {
	hierLevel, ok := memory.HierLevelFromInt(level)
	if !ok {
		return fmt.Errorf("invalid level %d", level)
	}
	store, ok := s.store.(memory.ExactFactPageStore)
	if !ok {
		return fmt.Errorf("exact fact pagination is unavailable for this store")
	}
	return store.ReleaseFactPage(ctx, hierLevel, key)
}

// SearchMode selects how SearchFactsWithMode interprets the query.
type SearchMode string

const (
	// ModeKeyword runs LIKE-style substring matching on fact content.
	ModeKeyword SearchMode = "keyword"
	// ModeSemantic embeds the query and ranks by cosine similarity.
	// Falls back to keyword if no embedder is configured.
	ModeSemantic SearchMode = "semantic"
	// ModeHybrid unions keyword and semantic results, deduped by ID.
	// Falls back to keyword if no embedder is configured.
	ModeHybrid SearchMode = "hybrid"
)

// SearchFacts searches facts by content (keyword, LIKE-based).
// Preserved for backward compatibility — equivalent to SearchFactsWithMode(ModeKeyword).
func (s *FactService) SearchFacts(ctx context.Context, query string, limit int) ([]*memory.Fact, error) {
	if limit <= 0 {
		limit = 20
	}
	return s.store.Search(ctx, query, limit)
}

// SearchFactsSemantic embeds the query and ranks facts by cosine similarity.
// Returns an error if no embedder is configured.
func (s *FactService) SearchFactsSemantic(ctx context.Context, query string, limit int) ([]*memory.Fact, error) {
	if s.embedder == nil {
		return nil, fmt.Errorf("semantic search unavailable: no embedder configured")
	}
	if limit <= 0 {
		limit = 20
	}
	vec, err := s.embedder.Embed(ctx, query)
	if err != nil {
		return nil, fmt.Errorf("embed query: %w", err)
	}
	return s.store.SearchByVector(ctx, vec, limit)
}

// SearchFactsHybrid fuses keyword and semantic rankings (weighted RRF, see
// fuseHybridResults). Falls back to pure keyword if there is no embedder.
func (s *FactService) SearchFactsHybrid(ctx context.Context, query string, limit int) ([]*memory.Fact, error) {
	if limit <= 0 {
		limit = 20
	}
	if s.embedder == nil {
		keyword, err := s.store.Search(ctx, query, limit)
		if err != nil {
			return nil, err
		}
		return s.expandWithVerifiedSynapses(ctx, keyword, limit), nil
	}

	depth := hybridDepth(limit)
	semantic, err := s.SearchFactsSemantic(ctx, query, depth)
	if err != nil {
		// On embedder failure, degrade to keyword rather than erroring out.
		return s.store.Search(ctx, query, limit)
	}

	keyword, err := s.store.Search(ctx, query, depth)
	if err != nil {
		// Semantic worked but keyword failed — return semantic alone.
		if len(semantic) > limit {
			semantic = semantic[:limit]
		}
		return semantic, nil
	}

	merged := fuseHybridResults(semantic, keyword, limit, s.semanticFusionWeight())
	return s.expandWithVerifiedSynapses(ctx, merged, limit), nil
}

func (s *FactService) expandWithVerifiedSynapses(ctx context.Context, facts []*memory.Fact, limit int) []*memory.Fact {
	if s.synapses == nil || len(facts) == 0 || len(facts) >= limit {
		return facts
	}
	verified, err := s.synapses.ListVerified(ctx)
	if err != nil {
		return facts
	}
	seen := make(map[string]struct{}, len(facts))
	seeds := make(map[string]struct{}, len(facts))
	for _, f := range facts {
		if f == nil {
			continue
		}
		seen[f.ID] = struct{}{}
		seeds[f.ID] = struct{}{}
	}
	for _, link := range verified {
		neighborID := ""
		if _, ok := seeds[link.FactIDA]; ok {
			neighborID = link.FactIDB
		} else if _, ok := seeds[link.FactIDB]; ok {
			neighborID = link.FactIDA
		}
		if neighborID == "" {
			continue
		}
		if _, ok := seen[neighborID]; ok {
			continue
		}
		neighbor, err := s.store.Get(ctx, neighborID)
		if err != nil || neighbor == nil || neighbor.IsArchived {
			continue
		}
		facts = append(facts, neighbor)
		seen[neighborID] = struct{}{}
		if len(facts) >= limit {
			break
		}
	}
	return facts
}

// SearchFactsWithMode dispatches to keyword/semantic/hybrid by mode.
// Unknown or empty mode defaults to hybrid.
func (s *FactService) SearchFactsWithMode(ctx context.Context, query string, limit int, mode SearchMode) ([]*memory.Fact, error) {
	switch mode {
	case ModeKeyword:
		return s.SearchFacts(ctx, query, limit)
	case ModeSemantic:
		return s.SearchFactsSemantic(ctx, query, limit)
	default: // ModeHybrid or empty/unknown
		return s.SearchFactsHybrid(ctx, query, limit)
	}
}

// SearchSessionFactsWithMode recalls facts from one exact session. Unlike the
// project-wide search path it performs no synapse expansion: a project-level
// synapse has no session boundary and could reintroduce a sibling session.
func (s *FactService) SearchSessionFactsWithMode(ctx context.Context, sessionID, query string, limit int, mode SearchMode) ([]*memory.Fact, error) {
	store, err := s.sessionStore(ctx, sessionID)
	if err != nil {
		return nil, err
	}
	if limit <= 0 {
		limit = 20
	}
	keywordAt := func(n int) ([]*memory.Fact, error) {
		facts, err := store.SearchForSession(ctx, sessionID, query, n)
		if err != nil {
			return nil, err
		}
		if err := validateSessionFacts(ctx, sessionID, facts...); err != nil {
			return nil, err
		}
		return facts, nil
	}
	semanticAt := func(n int) ([]*memory.Fact, error) {
		if s.embedder == nil {
			return nil, fmt.Errorf("semantic search unavailable: no embedder configured")
		}
		vec, err := s.embedder.Embed(ctx, query)
		if err != nil {
			return nil, fmt.Errorf("embed query: %w", err)
		}
		facts, err := store.SearchByVectorForSession(ctx, sessionID, vec, n)
		if err != nil {
			return nil, err
		}
		if err := validateSessionFacts(ctx, sessionID, facts...); err != nil {
			return nil, err
		}
		return facts, nil
	}

	keyword := func() ([]*memory.Fact, error) { return keywordAt(limit) }

	switch mode {
	case ModeKeyword:
		return keyword()
	case ModeSemantic:
		return semanticAt(limit)
	}

	if s.embedder == nil {
		return keyword()
	}
	depth := hybridDepth(limit)
	semanticFacts, err := semanticAt(depth)
	if err != nil {
		if errors.Is(err, errSessionFactBoundary) {
			return nil, err
		}
		return keyword()
	}
	keywordFacts, err := keywordAt(depth)
	if err != nil {
		if errors.Is(err, errSessionFactBoundary) {
			return nil, err
		}
		if len(semanticFacts) > limit {
			semanticFacts = semanticFacts[:limit]
		}
		return semanticFacts, nil
	}
	return fuseHybridResults(semanticFacts, keywordFacts, limit, s.semanticFusionWeight()), nil
}

// ListDomains returns all unique domains.
func (s *FactService) ListDomains(ctx context.Context) ([]string, error) {
	return s.store.ListDomains(ctx)
}

// GetStale returns stale facts.
func (s *FactService) GetStale(ctx context.Context, includeArchived bool) ([]*memory.Fact, error) {
	return s.store.GetStale(ctx, includeArchived)
}

// ProcessExpired handles expired TTL facts.
func (s *FactService) ProcessExpired(ctx context.Context) (int, error) {
	expired, err := s.store.GetExpired(ctx)
	if err != nil {
		return 0, err
	}

	processed := 0
	for _, fact := range expired {
		if fact.TTL == nil {
			continue
		}
		// Stores may return shared pointers. A rejected write must not mutate that
		// live object before persistence has succeeded.
		candidate := *fact
		var mutationErr error
		switch fact.TTL.OnExpire {
		case memory.OnExpireMarkStale:
			candidate.MarkStale()
			mutationErr = s.store.Update(ctx, &candidate)
		case memory.OnExpireArchive:
			candidate.Archive()
			mutationErr = s.store.Update(ctx, &candidate)
		case memory.OnExpireDelete:
			mutationErr = s.store.Delete(ctx, fact.ID)
		default:
			return processed, fmt.Errorf("expire fact %s: unsupported expiry policy %q", fact.ID, fact.TTL.OnExpire)
		}
		if mutationErr != nil {
			return processed, fmt.Errorf("expire fact %s: %w", fact.ID, mutationErr)
		}
		processed++
		if s.cache != nil {
			if err := s.cache.InvalidateFact(ctx, fact.ID); err != nil {
				return processed, fmt.Errorf("invalidate expired fact %s: %w", fact.ID, err)
			}
		}
	}

	return processed, nil
}

// GetStats returns fact store statistics.
func (s *FactService) GetStats(ctx context.Context) (*memory.FactStoreStats, error) {
	return s.store.Stats(ctx)
}

// GetL0Facts returns L0 facts from the scoped durable store.
func (s *FactService) GetL0Facts(ctx context.Context) ([]*memory.Fact, error) {
	// The hot cache has no completeness or generation witness. Read the
	// scoped durable store until a coherent cache protocol is available.
	return s.store.ListByLevel(ctx, memory.LevelProject)
}

// ToJSON marshals any value to indented JSON string.
func ToJSON(v interface{}) string {
	data, _ := json.MarshalIndent(v, "", "  ")
	return string(data)
}

// ListGenes returns all genome facts (immutable survival invariants).
func (s *FactService) ListGenes(ctx context.Context) ([]*memory.Fact, error) {
	return s.store.ListGenes(ctx)
}

// VerifyGenome computes the Merkle hash of all genes and returns integrity status.
func (s *FactService) VerifyGenome(ctx context.Context) (string, int, error) {
	genes, err := s.store.ListGenes(ctx)
	if err != nil {
		return "", 0, fmt.Errorf("list genes: %w", err)
	}
	hash := memory.GenomeHash(genes)
	return hash, len(genes), nil
}

// Store returns the underlying FactStore for direct access by subsystems
// (e.g., apoptosis recovery that needs raw store operations).
func (s *FactService) Store() memory.FactStore {
	return s.store
}

// --- v3.3 Context GC ---

// GetColdFacts returns facts with hit_count=0, created >30 days ago.
// Genes are excluded. Use for memory hygiene review.
func (s *FactService) GetColdFacts(ctx context.Context, limit int) ([]*memory.Fact, error) {
	if limit <= 0 {
		limit = 50
	}
	return s.store.GetColdFacts(ctx, limit)
}

// CompressFactsParams holds parameters for the compress_facts tool.
type CompressFactsParams struct {
	IDs     []string `json:"fact_ids"`
	Summary string   `json:"summary"`
}

// CompressFacts archives the given facts and creates a summary fact.
// Genes are silently skipped (invariant protection).
func (s *FactService) CompressFacts(ctx context.Context, params CompressFactsParams) (string, error) {
	if len(params.IDs) == 0 {
		return "", fmt.Errorf("fact_ids is required")
	}
	if params.Summary == "" {
		return "", fmt.Errorf("summary is required")
	}
	// v3.7: auto-backup decision before compression.
	if s.recorder != nil {
		s.recorder.RecordDecision("ORACLE", "COMPRESS_FACTS",
			fmt.Sprintf("ids=%v summary=%s", params.IDs, params.Summary))
	}
	return s.store.CompressFacts(ctx, params.IDs, params.Summary)
}
