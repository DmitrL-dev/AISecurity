package sqlite

import (
	"testing"
	"time"

	"github.com/syntrex/gomcp/internal/domain/orchestrator"
)

func setupOrchRepo(t *testing.T) *OrchestratorRepo {
	t.Helper()
	db, err := OpenMemory()
	if err != nil {
		t.Fatalf("open memory db: %v", err)
	}
	t.Cleanup(func() { db.Close() })
	repo, err := NewOrchestratorRepo(db)
	if err != nil {
		t.Fatalf("new orchestrator repo: %v", err)
	}
	return repo
}

func sampleAt(tenant, hash string, ts time.Time, blocked bool) orchestrator.Sample {
	return orchestrator.Sample{
		ID:         orchestrator.GenID("orch"),
		TenantID:   tenant,
		Timestamp:  ts,
		PromptHash: hash,
		EngineScores: map[string]float64{
			"prompt_injection": 0.95,
		},
		Aggregate: orchestrator.AggregateFeatures{
			Risk:             0.95,
			CoreConfidence:   0.95,
			EnginesTriggered: 1,
			CoreBlocked:      blocked,
		},
		VectorComplete: false,
		VectorSchema:   orchestrator.VectorSchema,
		Blocked:        blocked,
		Risk:           0.95,
		ThreatType:     "prompt_injection",
		ModelVersion:   "sentinel-core/1.0",
		Label:          orchestrator.LabelUnlabeled,
	}
}

func TestOrchInsertAndRoundTrip(t *testing.T) {
	repo := setupOrchRepo(t)
	s := sampleAt("tenant-a", "abc123", time.Now(), true)
	if err := repo.Insert(s); err != nil {
		t.Fatalf("insert: %v", err)
	}

	total, labeled, err := repo.CountSamples("tenant-a")
	if err != nil {
		t.Fatalf("count: %v", err)
	}
	if total != 1 || labeled != 0 {
		t.Fatalf("want total=1 labeled=0, got total=%d labeled=%d", total, labeled)
	}

	// Export including unlabeled to read the row back and verify fields round-trip.
	got, err := repo.ExportLabeled("tenant-a", 10, false)
	if err != nil {
		t.Fatalf("export: %v", err)
	}
	if len(got) != 1 {
		t.Fatalf("want 1 row, got %d", len(got))
	}
	r := got[0]
	if r.PromptHash != "abc123" || r.ThreatType != "prompt_injection" || !r.Blocked {
		t.Errorf("round-trip mismatch: %+v", r)
	}
	if r.EngineScores["prompt_injection"] != 0.95 {
		t.Errorf("engine scores not round-tripped: %v", r.EngineScores)
	}
	if r.Aggregate.Risk != 0.95 || r.Aggregate.EnginesTriggered != 1 {
		t.Errorf("aggregate not round-tripped: %+v", r.Aggregate)
	}
	if r.VectorSchema != orchestrator.VectorSchema {
		t.Errorf("vector schema not round-tripped: %q", r.VectorSchema)
	}
}

func TestOrchAttachLabel_TimeWindowJoin(t *testing.T) {
	repo := setupOrchRepo(t)
	base := time.Now()

	inWindow := sampleAt("tenant-a", "in", base, true)
	beforeWindow := sampleAt("tenant-a", "before", base.Add(-2*time.Hour), true)
	afterWindow := sampleAt("tenant-a", "after", base.Add(2*time.Hour), true)
	for _, s := range []orchestrator.Sample{inWindow, beforeWindow, afterWindow} {
		if err := repo.Insert(s); err != nil {
			t.Fatalf("insert: %v", err)
		}
	}

	// Attach label over a 1-hour window centered on base.
	from := base.Add(-30 * time.Minute)
	to := base.Add(30 * time.Minute)
	n, err := repo.AttachLabel("tenant-a", from, to, orchestrator.LabelBenign, "incident:FALSE_POSITIVE")
	if err != nil {
		t.Fatalf("attach: %v", err)
	}
	if n != 1 {
		t.Fatalf("expected exactly 1 row labeled (only the in-window sample), got %d", n)
	}

	labeled, err := repo.ExportLabeled("tenant-a", 10, true)
	if err != nil {
		t.Fatalf("export: %v", err)
	}
	if len(labeled) != 1 || labeled[0].PromptHash != "in" {
		t.Fatalf("only the in-window sample should be labeled, got %+v", labeled)
	}
	if labeled[0].Label != orchestrator.LabelBenign || labeled[0].LabelSource != "incident:FALSE_POSITIVE" {
		t.Errorf("label/source mismatch: %+v", labeled[0])
	}
	if labeled[0].LabeledAt == nil {
		t.Error("labeled_at should be set")
	}
}

func TestOrchAttachLabel_DoesNotOverwriteExisting(t *testing.T) {
	repo := setupOrchRepo(t)
	base := time.Now()
	s := sampleAt("tenant-a", "h", base, true)
	if err := repo.Insert(s); err != nil {
		t.Fatalf("insert: %v", err)
	}
	from, to := base.Add(-time.Hour), base.Add(time.Hour)

	// First disposition: malicious.
	if _, err := repo.AttachLabel("tenant-a", from, to, orchestrator.LabelMalicious, "incident:RESOLVED"); err != nil {
		t.Fatalf("attach 1: %v", err)
	}
	// Second disposition in the same window: must NOT relabel an already-labeled row.
	n, err := repo.AttachLabel("tenant-a", from, to, orchestrator.LabelBenign, "incident:FALSE_POSITIVE")
	if err != nil {
		t.Fatalf("attach 2: %v", err)
	}
	if n != 0 {
		t.Errorf("already-labeled row must not be overwritten, but %d rows updated", n)
	}
	labeled, _ := repo.ExportLabeled("tenant-a", 10, true)
	if len(labeled) != 1 || labeled[0].Label != orchestrator.LabelMalicious {
		t.Errorf("label should remain malicious, got %+v", labeled)
	}
}

func TestOrchTenantIsolation(t *testing.T) {
	repo := setupOrchRepo(t)
	now := time.Now()
	if err := repo.Insert(sampleAt("tenant-a", "a", now, true)); err != nil {
		t.Fatal(err)
	}
	if err := repo.Insert(sampleAt("tenant-b", "b", now, true)); err != nil {
		t.Fatal(err)
	}

	// Label-attach for tenant-a must NOT touch tenant-b's row.
	from, to := now.Add(-time.Hour), now.Add(time.Hour)
	n, err := repo.AttachLabel("tenant-a", from, to, orchestrator.LabelMalicious, "incident:RESOLVED")
	if err != nil {
		t.Fatalf("attach: %v", err)
	}
	if n != 1 {
		t.Fatalf("only tenant-a's row should be labeled, got %d", n)
	}

	// Export is tenant-scoped: tenant-a sees only its own row.
	aRows, _ := repo.ExportLabeled("tenant-a", 10, false)
	if len(aRows) != 1 || aRows[0].TenantID != "tenant-a" {
		t.Errorf("tenant-a export leaked or missing: %+v", aRows)
	}
	bRows, _ := repo.ExportLabeled("tenant-b", 10, false)
	if len(bRows) != 1 || bRows[0].TenantID != "tenant-b" {
		t.Errorf("tenant-b export wrong: %+v", bRows)
	}
	// tenant-b's row stayed unlabeled.
	if bRows[0].Label != orchestrator.LabelUnlabeled {
		t.Errorf("tenant-b row must remain unlabeled (cross-tenant leak), got %q", bRows[0].Label)
	}
}

func TestOrchEmptyTenantRefused(t *testing.T) {
	repo := setupOrchRepo(t)
	now := time.Now()
	if _, err := repo.AttachLabel("", now.Add(-time.Hour), now, orchestrator.LabelBenign, "x"); err == nil {
		t.Error("AttachLabel with empty tenant must be refused")
	}
	if _, err := repo.ExportLabeled("", 10, true); err == nil {
		t.Error("ExportLabeled with empty tenant must be refused")
	}
	if _, err := repo.DeleteByTenant(""); err == nil {
		t.Error("DeleteByTenant with empty tenant must be refused")
	}
}

func TestOrchInvalidLabelRefused(t *testing.T) {
	repo := setupOrchRepo(t)
	now := time.Now()
	if _, err := repo.AttachLabel("tenant-a", now.Add(-time.Hour), now, orchestrator.Label("garbage"), "x"); err == nil {
		t.Error("AttachLabel with invalid label must be refused")
	}
	if _, err := repo.AttachLabel("tenant-a", now.Add(-time.Hour), now, orchestrator.LabelUnlabeled, "x"); err == nil {
		t.Error("AttachLabel with empty label must be refused (it would un-label nothing meaningfully)")
	}
}

func TestOrchPurgeExpired(t *testing.T) {
	repo := setupOrchRepo(t)
	old := sampleAt("tenant-a", "old", time.Now().AddDate(0, 0, -100), true)
	fresh := sampleAt("tenant-a", "fresh", time.Now(), true)
	if err := repo.Insert(old); err != nil {
		t.Fatal(err)
	}
	if err := repo.Insert(fresh); err != nil {
		t.Fatal(err)
	}
	n, err := repo.PurgeExpired(90)
	if err != nil {
		t.Fatalf("purge: %v", err)
	}
	if n != 1 {
		t.Fatalf("expected 1 expired sample purged, got %d", n)
	}
	total, _, _ := repo.CountSamples("tenant-a")
	if total != 1 {
		t.Errorf("expected 1 fresh sample remaining, got %d", total)
	}
}

func TestOrchDeleteByTenant(t *testing.T) {
	repo := setupOrchRepo(t)
	now := time.Now()
	_ = repo.Insert(sampleAt("tenant-a", "a1", now, true))
	_ = repo.Insert(sampleAt("tenant-a", "a2", now, false))
	_ = repo.Insert(sampleAt("tenant-b", "b1", now, true))

	n, err := repo.DeleteByTenant("tenant-a")
	if err != nil {
		t.Fatalf("delete: %v", err)
	}
	if n != 2 {
		t.Fatalf("expected 2 tenant-a rows deleted, got %d", n)
	}
	aTotal, _, _ := repo.CountSamples("tenant-a")
	bTotal, _, _ := repo.CountSamples("tenant-b")
	if aTotal != 0 {
		t.Errorf("tenant-a should be empty, got %d", aTotal)
	}
	if bTotal != 1 {
		t.Errorf("tenant-b must be untouched, got %d", bTotal)
	}
}

// TestOrchPrivacyNoRawPromptColumn asserts the schema stores NO raw prompt — only
// a hash. This is the privacy invariant: the table must not have a column capable
// of holding prompt text (prompt/payload/text/content/input).
func TestOrchPrivacyNoRawPromptColumn(t *testing.T) {
	repo := setupOrchRepo(t)
	rows, err := repo.db.Query(`PRAGMA table_info(orchestrator_samples)`)
	if err != nil {
		t.Fatalf("pragma: %v", err)
	}
	defer rows.Close()
	forbidden := map[string]bool{
		"prompt": true, "payload": true, "text": true, "content": true,
		"input": true, "raw_prompt": true, "body": true,
	}
	var cols []string
	for rows.Next() {
		var cid int
		var name, ctype string
		var notnull, pk int
		var dflt any
		if err := rows.Scan(&cid, &name, &ctype, &notnull, &dflt, &pk); err != nil {
			t.Fatalf("scan: %v", err)
		}
		cols = append(cols, name)
		if forbidden[name] {
			t.Errorf("orchestrator_samples has a forbidden raw-content column %q — privacy invariant is metadata-only", name)
		}
	}
	// Sanity: the hash column must exist.
	hasHash := false
	for _, c := range cols {
		if c == "prompt_hash" {
			hasHash = true
		}
	}
	if !hasHash {
		t.Error("prompt_hash column missing")
	}
}
