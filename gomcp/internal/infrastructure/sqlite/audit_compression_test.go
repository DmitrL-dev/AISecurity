package sqlite

import (
	"context"
	"fmt"
	"github.com/syntrex/gomcp/internal/domain/memory"
	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
	"testing"
	"time"
)

func TestAuditCompressionRollsBackArchivesAndSummaryOnSQLFault(t *testing.T) {
	for _, fault := range []string{"archive", "summary"} {
		t.Run(fault, func(t *testing.T) {
			repo := newTestFactRepo(t)
			ctx, cancel := context.WithTimeout(rlmscope.WithScope(context.Background(), rlmscope.New("tenant-a", "compression")), 3*time.Second)
			defer cancel()
			var facts []*memory.Fact
			for _, content := range []string{"compression original first", "compression original second"} {
				fact := memory.NewFact(content, memory.LevelDomain, "audit", "")
				fact.Origin = memory.OriginExternal
				if err := repo.Add(ctx, fact); err != nil {
					t.Fatal(err)
				}
				facts = append(facts, fact)
			}
			trigger := `CREATE TEMP TRIGGER synthetic_compression_fault BEFORE INSERT ON hierarchical_facts WHEN NEW.source='consolidation' BEGIN SELECT RAISE(ABORT,'synthetic summary fault'); END`
			if fault == "archive" {
				trigger = fmt.Sprintf(`CREATE TEMP TRIGGER synthetic_compression_fault BEFORE UPDATE OF is_archived ON hierarchical_facts WHEN OLD.id='%s' AND NEW.is_archived=1 BEGIN SELECT RAISE(ABORT,'synthetic archive fault'); END`, facts[1].ID)
			}
			if _, err := repo.db.Exec(trigger); err != nil {
				t.Fatal(err)
			}
			id, err := repo.CompressFacts(ctx, []string{facts[0].ID, facts[1].ID}, "synthetic summary")
			if err == nil || id != "" {
				t.Fatal("injected SQL failure reported successful compression")
			}
			for _, fact := range facts {
				stored, err := repo.Get(ctx, fact.ID)
				if err != nil || stored.IsArchived {
					t.Fatal("failed compression left an archived/missing original")
				}
			}
			var summaries int
			if err := repo.db.QueryRow(`SELECT COUNT(*) FROM hierarchical_facts WHERE source='consolidation'`).Scan(&summaries); err != nil || summaries != 0 {
				t.Fatal("failed compression left a summary")
			}
		})
	}
}

func TestAuditCompressionPreservesScopeGenesTrustAndSummaryDedup(t *testing.T) {
	repo := newTestFactRepo(t)
	ctx := rlmscope.WithScope(context.Background(), rlmscope.New("tenant-a", "compression"))
	first := memory.NewFact("first original", memory.LevelDomain, "audit", "")
	first.Origin = memory.OriginUser
	second := memory.NewFact("second original", memory.LevelDomain, "audit", "")
	second.Origin = memory.OriginExternal
	gene := memory.NewGene("synthetic immutable gene", "audit")
	for _, fact := range []*memory.Fact{first, second, gene} {
		if err := repo.Add(ctx, fact); err != nil {
			t.Fatal(err)
		}
	}
	foreign := memory.NewFact("foreign original", memory.LevelDomain, "audit", "")
	other := rlmscope.WithScope(context.Background(), rlmscope.New("tenant-b", "compression"))
	if err := repo.Add(other, foreign); err != nil {
		t.Fatal(err)
	}
	// The existing byte-identical summary remains the dedup survivor. Its lower
	// external trust cannot be promoted by a derived consolidation.
	survivor := memory.NewFact("synthetic summary", memory.LevelDomain, "audit", "")
	survivor.Origin = memory.OriginExternal
	if err := repo.Add(ctx, survivor); err != nil {
		t.Fatal(err)
	}
	id, err := repo.CompressFacts(ctx, []string{first.ID, second.ID, first.ID, gene.ID, foreign.ID}, "synthetic summary")
	if err != nil {
		t.Fatal(err)
	}
	if id != survivor.ID {
		t.Fatal("compression bypassed existing summary dedup")
	}
	summary, err := repo.Get(ctx, id)
	if err != nil || summary.Origin != memory.OriginExternal || summary.IsArchived {
		t.Fatal("compression promoted trust or archived its summary")
	}
	for _, fact := range []*memory.Fact{first, second} {
		got, err := repo.Get(ctx, fact.ID)
		if err != nil || !got.IsArchived {
			t.Fatal("successful compression did not archive its inputs")
		}
	}
	got, err := repo.Get(ctx, gene.ID)
	if err != nil || got.IsArchived {
		t.Fatal("compression archived immutable gene")
	}
	got, err = repo.Get(other, foreign.ID)
	if err != nil || got.IsArchived {
		t.Fatal("compression crossed tenant scope")
	}
}
