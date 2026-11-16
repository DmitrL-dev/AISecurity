package tools

import (
	"context"
	"errors"
	"github.com/syntrex/gomcp/internal/domain/memory"
	"testing"
	"time"
)

var errAuditExpiry = errors.New("synthetic expiry storage failure")

type auditExpiryStore struct {
	memory.FactStore
	expired           []*memory.Fact
	mutations, failAt int
}

func (s *auditExpiryStore) GetExpired(context.Context) ([]*memory.Fact, error) { return s.expired, nil }
func (s *auditExpiryStore) Update(ctx context.Context, fact *memory.Fact) error {
	s.mutations++
	if s.mutations == s.failAt {
		return errAuditExpiry
	}
	return s.FactStore.Update(ctx, fact)
}
func (s *auditExpiryStore) Delete(ctx context.Context, id string) error {
	s.mutations++
	if s.mutations == s.failAt {
		return errAuditExpiry
	}
	return s.FactStore.Delete(ctx, id)
}

type auditExpiryCache struct {
	invalidated []string
	fail        bool
}

func (c *auditExpiryCache) GetL0Facts(context.Context) ([]*memory.Fact, error) { return nil, nil }
func (c *auditExpiryCache) InvalidateFact(_ context.Context, id string) error {
	c.invalidated = append(c.invalidated, id)
	if c.fail {
		return errAuditExpiry
	}
	return nil
}
func (c *auditExpiryCache) WarmUp(context.Context, []*memory.Fact) error { return nil }
func (c *auditExpiryCache) Close() error                                 { return nil }

func TestAuditExpiryPropagatesFaultsCountsOnlyCommittedMutationsAndInvalidatesCache(t *testing.T) {
	for _, policy := range []string{memory.OnExpireMarkStale, memory.OnExpireArchive, memory.OnExpireDelete} {
		for _, failAt := range []int{1, 2, 0} {
			base := newTestFactService(t)
			ctx := context.Background()
			var expired []*memory.Fact
			for _, content := range []string{"synthetic expiry first", "synthetic expiry second"} {
				fact := memory.NewFact(content, memory.LevelProject, "audit", "")
				fact.TTL = &memory.TTLConfig{TTLSeconds: 1, OnExpire: policy}
				fact.CreatedAt = time.Now().Add(-time.Hour)
				fact.ValidFrom = fact.CreatedAt
				if err := base.Store().Add(ctx, fact); err != nil {
					t.Fatal(err)
				}
				expired = append(expired, fact)
			}
			store := &auditExpiryStore{FactStore: base.Store(), expired: expired, failAt: failAt}
			cache := &auditExpiryCache{}
			processed, err := NewFactService(store, cache).ProcessExpired(ctx)
			expected := 2
			if failAt > 0 {
				expected = failAt - 1
				if !errors.Is(err, errAuditExpiry) {
					t.Fatalf("policy %s did not propagate failure: %v", policy, err)
				}
			} else if err != nil {
				t.Fatal(err)
			}
			if processed != expected || len(cache.invalidated) != expected {
				t.Fatalf("policy %s counted/invalidate failed mutation: processed=%d cache=%d want=%d", policy, processed, len(cache.invalidated), expected)
			}
			if failAt > 0 {
				failed := expired[failAt-1]
				if failed.IsStale || failed.IsArchived {
					t.Fatal("failed write mutated shared input pointer")
				}
				stored, err := base.Store().Get(ctx, failed.ID)
				if err != nil || stored.IsStale || stored.IsArchived {
					t.Fatal("failed mutation changed persisted row")
				}
			}
		}
	}
}
func TestAuditExpiryRejectsUnknownPolicyAndReportsCacheFailure(t *testing.T) {
	for _, unknown := range []bool{true, false} {
		base := newTestFactService(t)
		ctx := context.Background()
		fact := memory.NewFact("synthetic invalidation fixture", memory.LevelProject, "audit", "")
		if err := base.Store().Add(ctx, fact); err != nil {
			t.Fatal(err)
		}
		policy := memory.OnExpireMarkStale
		if unknown {
			policy = "unknown"
		}
		fact.TTL = &memory.TTLConfig{TTLSeconds: 1, OnExpire: policy}
		store := &auditExpiryStore{FactStore: base.Store(), expired: []*memory.Fact{fact}}
		cache := &auditExpiryCache{fail: true}
		processed, err := NewFactService(store, cache).ProcessExpired(ctx)
		if err == nil {
			t.Fatal("invalid policy/cache failure reported success")
		}
		if unknown {
			if processed != 0 || store.mutations != 0 {
				t.Fatal("unknown expiry policy counted as mutation")
			}
		} else if processed != 1 || !errors.Is(err, errAuditExpiry) {
			t.Fatal("cache failure lost committed-mutation count or cause")
		}
	}
}

func TestAuditAddFactReportsPersistedWriteAndCacheFailure(t *testing.T) {
	base := newTestFactService(t)
	cache := &auditExpiryCache{fail: true}
	service := NewFactService(base.Store(), cache)
	fact, err := service.AddFact(context.Background(), AddFactParams{Content: "synthetic committed fact cache fault", Level: 0})
	if fact == nil || !errors.Is(err, errAuditExpiry) {
		t.Fatalf("persisted write/cache failure not reported: fact=%v err=%v", fact != nil, err)
	}
	stored, readErr := base.Store().Get(context.Background(), fact.ID)
	if readErr != nil || stored.Content != fact.Content || len(cache.invalidated) != 1 {
		t.Fatal("partial cache failure obscured persisted fact")
	}
}
