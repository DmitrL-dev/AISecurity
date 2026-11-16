package orchestrator

import (
	"context"
	"errors"
	"strings"
	"testing"
	"time"

	"github.com/syntrex/gomcp/internal/domain/memory"
	"github.com/syntrex/gomcp/internal/infrastructure/sqlite"
)

var errAuditHygiene = errors.New("synthetic hygiene failure")

type auditHygieneStore struct {
	memory.FactStore
	expired, watchdog, stale []*memory.Fact
	failWrite, failRead      string
}

func (s *auditHygieneStore) GetExpired(context.Context) ([]*memory.Fact, error) {
	if s.failRead == "expired" {
		return nil, errAuditHygiene
	}
	return s.expired, nil
}
func (s *auditHygieneStore) GetStale(context.Context, bool) ([]*memory.Fact, error) {
	if s.failRead == "stale" {
		return nil, errAuditHygiene
	}
	return s.stale, nil
}
func (s *auditHygieneStore) ListByLevel(context.Context, memory.HierLevel) ([]*memory.Fact, error) {
	if s.failRead == "watchdog" {
		return nil, errAuditHygiene
	}
	return s.watchdog, nil
}
func (s *auditHygieneStore) Update(ctx context.Context, f *memory.Fact) error {
	if s.failWrite == f.ID {
		return errAuditHygiene
	}
	return s.FactStore.Update(ctx, f)
}
func (s *auditHygieneStore) Delete(ctx context.Context, id string) error {
	if s.failWrite == id {
		return errAuditHygiene
	}
	return s.FactStore.Delete(ctx, id)
}

type auditHygieneCache struct {
	ids  []string
	fail bool
}

func (c *auditHygieneCache) GetL0Facts(context.Context) ([]*memory.Fact, error) { return nil, nil }
func (c *auditHygieneCache) WarmUp(context.Context, []*memory.Fact) error       { return nil }
func (c *auditHygieneCache) Close() error                                       { return nil }
func (c *auditHygieneCache) InvalidateFact(_ context.Context, id string) error {
	c.ids = append(c.ids, id)
	if c.fail {
		return errAuditHygiene
	}
	return nil
}

func TestAuditHygieneCountsPersistedWritesPreservesCandidatesAndReportsFaults(t *testing.T) {
	for _, failure := range []string{"", "expire", "watchdog", "archive", "read-expired", "read-watchdog", "read-stale", "cache"} {
		t.Run(failure, func(t *testing.T) {
			db, err := sqlite.OpenMemory()
			if err != nil {
				t.Fatal(err)
			}
			defer db.Close()
			repo, err := sqlite.NewFactRepo(db)
			if err != nil {
				t.Fatal(err)
			}
			ctx := context.Background()
			facts := map[string]*memory.Fact{}
			for _, name := range []string{"expire", "watchdog", "archive"} {
				f := memory.NewFact("synthetic hygiene "+name, memory.LevelProject, "audit", "")
				f.CreatedAt = time.Now().Add(-48 * time.Hour)
				f.UpdatedAt = f.CreatedAt
				if name == "watchdog" {
					f.Domain = "recovery"
					f.Source = "watchdog"
				}
				if name == "archive" {
					f.IsStale = true
				}
				if err := repo.Add(ctx, f); err != nil {
					t.Fatal(err)
				}
				facts[name] = f
			}
			store := &auditHygieneStore{FactStore: repo, expired: []*memory.Fact{facts["expire"]}, watchdog: []*memory.Fact{facts["watchdog"]}, stale: []*memory.Fact{facts["archive"]}}
			if f := facts[failure]; f != nil {
				store.failWrite = f.ID
			}
			if strings.HasPrefix(failure, "read-") {
				store.failRead = strings.TrimPrefix(failure, "read-")
			}
			cache := &auditHygieneCache{fail: failure == "cache"}
			result := HeartbeatResult{}
			expired, archived := New(DefaultConfig(), nil, store).WithCache(cache).memoryHygiene(ctx, &result)
			wantE, wantA := 1, 2
			switch failure {
			case "expire":
				wantE = 0
			case "watchdog", "archive", "read-watchdog", "read-stale":
				wantA = 1
			case "read-expired":
				wantE = 0
				wantA = 0
			}
			if expired != wantE || archived != wantA || len(cache.ids) != wantE+wantA {
				t.Fatalf("wrong successful write/cache counts: %d/%d/%d want %d/%d", expired, archived, len(cache.ids), wantE, wantA)
			}
			if (len(result.Errors) > 0) != (failure != "") {
				t.Fatalf("incorrect error reporting: %v", result.Errors)
			}
			if facts["expire"].IsStale || facts["archive"].IsArchived {
				t.Fatal("hygiene mutated shared candidate pointers")
			}
			if store.failWrite != "" {
				got, err := repo.Get(ctx, store.failWrite)
				if err != nil {
					t.Fatal("failed write lost original")
				}
				if got.IsArchived || failure == "expire" && got.IsStale {
					t.Fatal("failed write changed original flags")
				}
			}
		})
	}
}
