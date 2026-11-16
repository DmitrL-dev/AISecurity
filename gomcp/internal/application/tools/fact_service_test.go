package tools

import (
	"context"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"github.com/syntrex/gomcp/internal/domain/memory"
	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
	"github.com/syntrex/gomcp/internal/infrastructure/sqlite"
)

func newTestFactService(t *testing.T) *FactService {
	t.Helper()
	db, err := sqlite.OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { db.Close() })

	repo, err := sqlite.NewFactRepo(db)
	require.NoError(t, err)

	return NewFactService(repo, nil)
}

func TestFactService_AddFact(t *testing.T) {
	svc := newTestFactService(t)
	ctx := context.Background()

	fact, err := svc.AddFact(ctx, AddFactParams{
		Content: "Go is fast",
		Level:   0,
		Domain:  "core",
		Module:  "engine",
		CodeRef: "main.go:42",
	})
	require.NoError(t, err)
	require.NotNil(t, fact)

	assert.Equal(t, "Go is fast", fact.Content)
	assert.Equal(t, memory.LevelProject, fact.Level)
	assert.Equal(t, "core", fact.Domain)
}

func TestFactService_AddFact_InvalidLevel(t *testing.T) {
	svc := newTestFactService(t)
	ctx := context.Background()

	_, err := svc.AddFact(ctx, AddFactParams{Content: "test", Level: 99})
	assert.Error(t, err)
}

func TestFactService_GetFact(t *testing.T) {
	svc := newTestFactService(t)
	ctx := context.Background()

	fact, err := svc.AddFact(ctx, AddFactParams{Content: "test", Level: 0})
	require.NoError(t, err)

	got, err := svc.GetFact(ctx, fact.ID)
	require.NoError(t, err)
	assert.Equal(t, fact.ID, got.ID)
}

func TestFactService_UpdateFact(t *testing.T) {
	svc := newTestFactService(t)
	ctx := context.Background()

	fact, err := svc.AddFact(ctx, AddFactParams{Content: "original", Level: 0})
	require.NoError(t, err)

	newContent := "updated"
	updated, err := svc.UpdateFact(ctx, UpdateFactParams{
		ID:      fact.ID,
		Content: &newContent,
	})
	require.NoError(t, err)
	assert.Equal(t, "updated", updated.Content)
}

func TestFactService_DeleteFact(t *testing.T) {
	svc := newTestFactService(t)
	ctx := context.Background()

	fact, err := svc.AddFact(ctx, AddFactParams{Content: "delete me", Level: 0})
	require.NoError(t, err)

	err = svc.DeleteFact(ctx, fact.ID)
	require.NoError(t, err)

	_, err = svc.GetFact(ctx, fact.ID)
	assert.Error(t, err)
}

func TestFactService_ListFacts_ByDomain(t *testing.T) {
	svc := newTestFactService(t)
	ctx := context.Background()

	_, _ = svc.AddFact(ctx, AddFactParams{Content: "f1", Level: 0, Domain: "backend"})
	_, _ = svc.AddFact(ctx, AddFactParams{Content: "f2", Level: 1, Domain: "backend"})
	_, _ = svc.AddFact(ctx, AddFactParams{Content: "f3", Level: 0, Domain: "frontend"})

	facts, err := svc.ListFacts(ctx, ListFactsParams{Domain: "backend"})
	require.NoError(t, err)
	assert.Len(t, facts, 2)
}

func TestFactService_SearchFacts(t *testing.T) {
	svc := newTestFactService(t)
	ctx := context.Background()

	_, _ = svc.AddFact(ctx, AddFactParams{Content: "Go concurrency", Level: 0})
	_, _ = svc.AddFact(ctx, AddFactParams{Content: "Python is slow", Level: 0})

	results, err := svc.SearchFacts(ctx, "Go", 10)
	require.NoError(t, err)
	assert.Len(t, results, 1)
}

func TestFactService_GetStats(t *testing.T) {
	svc := newTestFactService(t)
	ctx := context.Background()

	_, _ = svc.AddFact(ctx, AddFactParams{Content: "f1", Level: 0, Domain: "core"})
	_, _ = svc.AddFact(ctx, AddFactParams{Content: "f2", Level: 1, Domain: "core"})

	stats, err := svc.GetStats(ctx)
	require.NoError(t, err)
	assert.Equal(t, 2, stats.TotalFacts)
}

func TestFactServiceProcessExpiredCannotMutateSessionFacts(t *testing.T) {
	svc := newTestFactService(t)
	ctx := rlmscope.WithScope(context.Background(), rlmscope.New("local", "expiry-test"))

	legacy := memory.NewFact("expired legacy", memory.LevelProject, "ttl", "")
	legacy.TTL = &memory.TTLConfig{TTLSeconds: 1, OnExpire: memory.OnExpireDelete}
	legacy.CreatedAt = time.Now().Add(-2 * time.Hour)
	legacy.ValidFrom = legacy.CreatedAt
	require.NoError(t, svc.Store().Add(ctx, legacy))

	sessionStore, ok := svc.Store().(memory.SessionFactStore)
	require.True(t, ok)
	sessionFact := memory.NewFact("expired session", memory.LevelProject, "ttl", "")
	sessionFact.TTL = &memory.TTLConfig{TTLSeconds: 1, OnExpire: memory.OnExpireDelete}
	sessionFact.CreatedAt = time.Now().Add(-2 * time.Hour)
	sessionFact.ValidFrom = sessionFact.CreatedAt
	require.NoError(t, sessionStore.AddForSession(ctx, "session-one", sessionFact))

	processed, err := svc.ProcessExpired(ctx)
	require.NoError(t, err)
	require.Equal(t, 1, processed)

	_, err = svc.Store().Get(ctx, legacy.ID)
	require.Error(t, err)
	sessionFacts, err := sessionStore.ListForSession(ctx, "session-one", true)
	require.NoError(t, err)
	require.Len(t, sessionFacts, 1)
	require.Equal(t, sessionFact.ID, sessionFacts[0].ID)
}

func TestFactServiceRejectsSessionStoreBoundaryViolations(t *testing.T) {
	base := newTestFactService(t).Store()
	store := &boundaryViolatingSessionStore{FactStore: base, keywordViolation: true}
	svc := NewFactService(store, nil)
	ctx := rlmscope.WithScope(context.Background(), rlmscope.New("local", "project-alpha"))

	_, err := svc.AddSessionFact(ctx, "session-one", AddFactParams{
		Content: "must fail closed", Level: int(memory.LevelProject),
	})
	require.ErrorContains(t, err, "session fact store boundary violation")

	_, _, _, err = svc.AddSessionTurn(ctx, "session-one", AddFactParams{
		Content: "must fail closed", Level: int(memory.LevelProject),
		TurnID: "turn_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
	})
	require.ErrorContains(t, err, "session fact store boundary violation")

	_, err = svc.SearchSessionFactsWithMode(ctx, "session-one", "private", 20, ModeKeyword)
	require.ErrorContains(t, err, "session fact store boundary violation")

	svc.SetEmbedder(&stubEmbedder{dim: 2, embed: func(string) []float64 { return []float64{1, 0} }})
	_, err = svc.SearchSessionFactsWithMode(ctx, "session-one", "private", 20, ModeHybrid)
	require.ErrorContains(t, err, "session fact store boundary violation",
		"hybrid search must not swallow a keyword boundary error after semantic success")

	semanticStore := &boundaryViolatingSessionStore{FactStore: base, semanticViolation: true}
	semanticSvc := NewFactService(semanticStore, nil)
	semanticSvc.SetEmbedder(&stubEmbedder{dim: 2, embed: func(string) []float64 { return []float64{1, 0} }})
	_, err = semanticSvc.SearchSessionFactsWithMode(ctx, "session-one", "private", 20, ModeHybrid)
	require.ErrorContains(t, err, "session fact store boundary violation",
		"hybrid search must not fall back to keyword after a semantic boundary error")
}

func TestFactServiceAddSessionFactPreservesLegacyUnkeyedSemantics(t *testing.T) {
	const turnID = "turn_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
	svc := newTestFactService(t)
	ctx := rlmscope.WithScope(context.Background(), rlmscope.New("tenant-a", "project-legacy"))
	params := AddFactParams{
		Content: "legacy append marker", Level: int(memory.LevelDomain),
		Domain: "conversation", Module: "chat", Origin: string(memory.OriginDerived),
	}

	first, err := svc.AddSessionFact(ctx, "session-one", params)
	require.NoError(t, err)
	second, err := svc.AddSessionFact(ctx, "session-one", params)
	require.NoError(t, err)
	require.Equal(t, first.ID, second.ID, "legacy duplicate folding must remain unchanged")

	different, err := svc.AddSessionFact(ctx, "session-one", AddFactParams{
		Content: "different legacy marker", Level: int(memory.LevelDomain),
		Domain: "conversation", Module: "chat", Origin: string(memory.OriginDerived),
	})
	require.NoError(t, err)
	require.NotEqual(t, first.ID, different.ID)

	store, ok := svc.Store().(memory.SessionFactStore)
	require.True(t, ok)
	facts, err := store.ListForSession(ctx, "session-one", false)
	require.NoError(t, err)
	require.Len(t, facts, 2, "legacy writes remain unkeyed and use ordinary content folding")

	receipt, committed, err := svc.GetSessionTurn(ctx, "session-one", turnID)
	require.NoError(t, err)
	require.Nil(t, receipt)
	require.Nil(t, committed, "legacy writes must not fabricate turn receipts")
}

func TestFactServiceSessionTurnRequestRefDeduplicatesChangedBoundedContent(t *testing.T) {
	const (
		turnID      = "turn_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
		requestRefA = "session-turn-request-v1:sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
		requestRefB = "session-turn-request-v1:sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
	)
	svc := newTestFactService(t)
	ctx := rlmscope.WithScope(context.Background(), rlmscope.New("tenant-a", "project-request-ref"))

	first, receipt, deduplicated, err := svc.AddSessionTurn(ctx, "session-one", AddFactParams{
		Content: "bounded first assistant response", Level: int(memory.LevelDomain),
		Domain: "conversation", Module: "chat", CodeRef: requestRefA, TurnID: turnID,
		Origin: string(memory.OriginDerived),
	})
	require.NoError(t, err)
	require.False(t, deduplicated)

	retry, retryReceipt, deduplicated, err := svc.AddSessionTurn(ctx, "session-one", AddFactParams{
		Content: "same request, different bounded assistant response", Level: int(memory.LevelDomain),
		Domain: "conversation", Module: "chat", CodeRef: requestRefA, TurnID: turnID,
		Origin: string(memory.OriginDerived),
	})
	require.NoError(t, err)
	require.True(t, deduplicated)
	require.Equal(t, receipt, retryReceipt)
	require.Equal(t, first, retry, "service must return the originally committed fact")

	_, _, _, err = svc.AddSessionTurn(ctx, "session-one", AddFactParams{
		Content: "different request", Level: int(memory.LevelDomain),
		Domain: "conversation", Module: "chat", CodeRef: requestRefB, TurnID: turnID,
		Origin: string(memory.OriginDerived),
	})
	require.ErrorIs(t, err, memory.ErrSessionTurnConflict)
}

func TestFactService_GetL0Facts(t *testing.T) {
	svc := newTestFactService(t)
	ctx := context.Background()

	_, _ = svc.AddFact(ctx, AddFactParams{Content: "L0 fact", Level: 0})
	_, _ = svc.AddFact(ctx, AddFactParams{Content: "L1 fact", Level: 1})

	facts, err := svc.GetL0Facts(ctx)
	require.NoError(t, err)
	assert.Len(t, facts, 1)
	assert.Equal(t, "L0 fact", facts[0].Content)
}

func TestFactService_ListDomains(t *testing.T) {
	svc := newTestFactService(t)
	ctx := context.Background()

	_, _ = svc.AddFact(ctx, AddFactParams{Content: "f1", Level: 0, Domain: "backend"})
	_, _ = svc.AddFact(ctx, AddFactParams{Content: "f2", Level: 0, Domain: "frontend"})

	domains, err := svc.ListDomains(ctx)
	require.NoError(t, err)
	assert.Len(t, domains, 2)
}

func TestToJSON(t *testing.T) {
	result := ToJSON(map[string]string{"key": "value"})
	assert.Contains(t, result, "\"key\"")
	assert.Contains(t, result, "\"value\"")
}

type boundaryViolatingSessionStore struct {
	memory.FactStore
	keywordViolation  bool
	semanticViolation bool
}

func (s *boundaryViolatingSessionStore) AddForSession(_ context.Context, sessionID string, fact *memory.Fact) error {
	fact.TenantID = "local"
	fact.ProjectID = "project-other"
	fact.SessionID = sessionID
	return nil
}

func (s *boundaryViolatingSessionStore) AddTurnForSession(
	_ context.Context,
	sessionID, turnID string,
	fact *memory.Fact,
) (*memory.SessionTurnReceipt, bool, error) {
	err := s.AddForSession(context.Background(), sessionID, fact)
	return &memory.SessionTurnReceipt{
		Version: 1, TurnID: turnID, FactID: fact.ID,
		PayloadSHA256: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
	}, false, err
}

func (s *boundaryViolatingSessionStore) GetTurnForSession(
	context.Context, string, string,
) (*memory.SessionTurnReceipt, *memory.Fact, error) {
	return nil, nil, nil
}

func (s *boundaryViolatingSessionStore) ListForSession(context.Context, string, bool) ([]*memory.Fact, error) {
	return nil, nil
}

func (s *boundaryViolatingSessionStore) SearchForSession(_ context.Context, sessionID, _ string, _ int) ([]*memory.Fact, error) {
	if !s.keywordViolation {
		return []*memory.Fact{}, nil
	}
	fact := memory.NewFact("private sibling fact", memory.LevelProject, "session", "")
	fact.TenantID = "local"
	fact.ProjectID = "project-other"
	fact.SessionID = sessionID
	return []*memory.Fact{fact}, nil
}

func (s *boundaryViolatingSessionStore) SearchByVectorForSession(_ context.Context, sessionID string, _ []float64, _ int) ([]*memory.Fact, error) {
	if !s.semanticViolation {
		return []*memory.Fact{}, nil
	}
	fact := memory.NewFact("private sibling semantic fact", memory.LevelProject, "session", "")
	fact.TenantID = "local"
	fact.ProjectID = "project-other"
	fact.SessionID = sessionID
	return []*memory.Fact{fact}, nil
}

func TestAuditCallerGeneCannotClaimBuiltinOrigin(t *testing.T) {
	svc := newTestFactService(t)
	gene, err := svc.AddGene(context.Background(), AddGeneParams{Content: "synthetic caller assertion"})
	require.NoError(t, err)
	assert.Equal(t, memory.OriginDerived, gene.Origin)
}
func TestAuditReplacedContentDoesNotInheritBuiltinTrust(t *testing.T) {
	svc := newTestFactService(t)
	fact := memory.NewFact("original bytes", memory.LevelDomain, "audit", "")
	fact.Origin = memory.OriginBuiltin
	require.NoError(t, svc.Store().Add(context.Background(), fact))
	replacement := "new caller bytes"
	updated, err := svc.UpdateFact(context.Background(), UpdateFactParams{ID: fact.ID, Content: &replacement})
	require.NoError(t, err)
	assert.Equal(t, memory.OriginDerived, updated.Origin)
}
