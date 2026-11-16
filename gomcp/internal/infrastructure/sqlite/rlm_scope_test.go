package sqlite

import (
	"context"
	"testing"

	"github.com/syntrex/gomcp/internal/domain/causal"
	"github.com/syntrex/gomcp/internal/domain/crystal"
	"github.com/syntrex/gomcp/internal/domain/memory"
	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
	"github.com/syntrex/gomcp/internal/domain/session"
)

func scopedCtx(tenantID, projectID string) context.Context {
	return rlmscope.WithScope(context.Background(), rlmscope.New(tenantID, projectID))
}

func TestRLMScope_FactsAreTenantAndProjectIsolated(t *testing.T) {
	db, err := OpenMemory()
	if err != nil {
		t.Fatalf("open db: %v", err)
	}
	defer db.Close()

	repo, err := NewFactRepo(db)
	if err != nil {
		t.Fatalf("repo: %v", err)
	}

	ctxA := scopedCtx("tenant-a", "project-alpha")
	ctxB := scopedCtx("tenant-b", "project-alpha")
	ctxA2 := scopedCtx("tenant-a", "project-beta")

	fA := memory.NewFact("alpha secret", memory.LevelProject, "scope", "")
	fB := memory.NewFact("bravo secret", memory.LevelProject, "scope", "")
	fA2 := memory.NewFact("beta project secret", memory.LevelProject, "scope", "")
	if err := repo.Add(ctxA, fA); err != nil {
		t.Fatalf("add A: %v", err)
	}
	if err := repo.Add(ctxB, fB); err != nil {
		t.Fatalf("add B: %v", err)
	}
	if err := repo.Add(ctxA2, fA2); err != nil {
		t.Fatalf("add A2: %v", err)
	}

	got, err := repo.ListByLevel(ctxA, memory.LevelProject)
	if err != nil {
		t.Fatalf("list A: %v", err)
	}
	if len(got) != 1 || got[0].Content != "alpha secret" {
		t.Fatalf("tenant/project A list leaked or missed facts: %#v", got)
	}
	if _, err := repo.Get(ctxA, fB.ID); err == nil {
		t.Fatal("tenant A must not read tenant B fact by ID")
	}
	search, err := repo.Search(ctxA, "secret", 10)
	if err != nil {
		t.Fatalf("search A: %v", err)
	}
	if len(search) != 1 || search[0].ID != fA.ID {
		t.Fatalf("tenant/project A search leaked facts: %#v", search)
	}
	stats, err := repo.Stats(ctxA)
	if err != nil {
		t.Fatalf("stats A: %v", err)
	}
	if stats.TotalFacts != 1 {
		t.Fatalf("stats must be scoped, got total=%d", stats.TotalFacts)
	}
}

func TestRLMScope_SessionsAllowSameIDAcrossProjects(t *testing.T) {
	db, err := OpenMemory()
	if err != nil {
		t.Fatalf("open db: %v", err)
	}
	defer db.Close()

	repo, err := NewStateRepo(db)
	if err != nil {
		t.Fatalf("repo: %v", err)
	}

	ctxA := scopedCtx("tenant-a", "project-alpha")
	ctxB := scopedCtx("tenant-a", "project-beta")
	stateA := session.NewCognitiveStateVector("same-session")
	stateA.SetGoal("alpha goal", 0.1)
	stateB := session.NewCognitiveStateVector("same-session")
	stateB.SetGoal("beta goal", 0.2)

	if err := repo.Save(ctxA, stateA, stateA.Checksum()); err != nil {
		t.Fatalf("save A: %v", err)
	}
	if err := repo.Save(ctxB, stateB, stateB.Checksum()); err != nil {
		t.Fatalf("save B: %v", err)
	}

	gotA, _, err := repo.Load(ctxA, "same-session", nil)
	if err != nil {
		t.Fatalf("load A: %v", err)
	}
	gotB, _, err := repo.Load(ctxB, "same-session", nil)
	if err != nil {
		t.Fatalf("load B: %v", err)
	}
	if gotA.PrimaryGoal == nil || gotB.PrimaryGoal == nil ||
		gotA.PrimaryGoal.Description != "alpha goal" || gotB.PrimaryGoal.Description != "beta goal" {
		t.Fatalf("session state crossed projects: A=%#v B=%#v", gotA.PrimaryGoal, gotB.PrimaryGoal)
	}
}

func TestRLMScope_ConversationLogIsScoped(t *testing.T) {
	db, err := OpenMemory()
	if err != nil {
		t.Fatalf("open db: %v", err)
	}
	defer db.Close()

	repo, err := NewConversationLogRepo(db)
	if err != nil {
		t.Fatalf("repo: %v", err)
	}

	ctxA := scopedCtx("tenant-a", "project-alpha")
	ctxB := scopedCtx("tenant-b", "project-alpha")
	if err := repo.Record(ctxA, ConversationEntry{SessionID: "s", Role: "user", Content: "alpha", MsgIndex: 0}); err != nil {
		t.Fatalf("record A: %v", err)
	}
	if err := repo.Record(ctxB, ConversationEntry{SessionID: "s", Role: "user", Content: "bravo", MsgIndex: 0}); err != nil {
		t.Fatalf("record B: %v", err)
	}

	aRows, err := repo.GetSession(ctxA, "s")
	if err != nil {
		t.Fatalf("get A: %v", err)
	}
	bRows, err := repo.GetSession(ctxB, "s")
	if err != nil {
		t.Fatalf("get B: %v", err)
	}
	if len(aRows) != 1 || aRows[0].Content != "alpha" || len(bRows) != 1 || bRows[0].Content != "bravo" {
		t.Fatalf("conversation rows crossed scope: A=%#v B=%#v", aRows, bRows)
	}
	if err := repo.MarkDistilled(ctxA, []int64{aRows[0].ID}); err != nil {
		t.Fatalf("mark A: %v", err)
	}
	undB, err := repo.GetUndistilled(ctxB, 10)
	if err != nil {
		t.Fatalf("undistilled B: %v", err)
	}
	if len(undB) != 1 || undB[0].Content != "bravo" {
		t.Fatalf("marking A must not affect B: %#v", undB)
	}
}

func TestRLMScope_CrystalsAllowSamePathAcrossProjects(t *testing.T) {
	db, err := OpenMemory()
	if err != nil {
		t.Fatalf("open db: %v", err)
	}
	defer db.Close()

	repo, err := NewCrystalRepo(db)
	if err != nil {
		t.Fatalf("repo: %v", err)
	}

	ctxA := scopedCtx("tenant-a", "project-alpha")
	ctxB := scopedCtx("tenant-a", "project-beta")
	if err := repo.Upsert(ctxA, &crystal.Crystal{Path: "src/main.go", Name: "alpha-main"}); err != nil {
		t.Fatalf("upsert A: %v", err)
	}
	if err := repo.Upsert(ctxB, &crystal.Crystal{Path: "src/main.go", Name: "beta-main"}); err != nil {
		t.Fatalf("upsert B: %v", err)
	}

	gotA, err := repo.Get(ctxA, "src/main.go")
	if err != nil {
		t.Fatalf("get A: %v", err)
	}
	gotB, err := repo.Get(ctxB, "src/main.go")
	if err != nil {
		t.Fatalf("get B: %v", err)
	}
	if gotA.Name != "alpha-main" || gotB.Name != "beta-main" {
		t.Fatalf("crystal path crossed projects: A=%q B=%q", gotA.Name, gotB.Name)
	}
}

func TestRLMScope_CausalChainsAreScoped(t *testing.T) {
	db, err := OpenMemory()
	if err != nil {
		t.Fatalf("open db: %v", err)
	}
	defer db.Close()

	repo, err := NewCausalRepo(db)
	if err != nil {
		t.Fatalf("repo: %v", err)
	}

	ctxA := scopedCtx("tenant-a", "project-alpha")
	ctxB := scopedCtx("tenant-b", "project-alpha")
	nodeA := causal.NewNode(causal.NodeDecision, "ship alpha decision")
	nodeB := causal.NewNode(causal.NodeDecision, "ship bravo decision")
	if err := repo.AddNode(ctxA, nodeA); err != nil {
		t.Fatalf("add A: %v", err)
	}
	if err := repo.AddNode(ctxB, nodeB); err != nil {
		t.Fatalf("add B: %v", err)
	}
	if err := repo.AddEdge(ctxA, causal.NewEdge(nodeA.ID, nodeB.ID, causal.EdgeCauses)); err == nil {
		t.Fatal("tenant A must not create a causal edge to tenant B node")
	}

	chain, err := repo.GetChain(ctxA, "ship", 1)
	if err != nil {
		t.Fatalf("chain A: %v", err)
	}
	if chain.Decision == nil || chain.Decision.ID != nodeA.ID {
		t.Fatalf("causal chain must stay in tenant A, got %#v", chain.Decision)
	}
	stats, err := repo.Stats(ctxA)
	if err != nil {
		t.Fatalf("stats A: %v", err)
	}
	if stats.TotalNodes != 1 {
		t.Fatalf("causal stats must be scoped, got %d", stats.TotalNodes)
	}
}
