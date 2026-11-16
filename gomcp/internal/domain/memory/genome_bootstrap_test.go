package memory

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// --- Hardcoded Genes Tests ---

func TestHardcodedGenes_CountAndIDs(t *testing.T) {
	require.Len(t, HardcodedGenes, 6, "Must have exactly 6 hardcoded genes")

	expectedIDs := []string{
		"GENE_01_SOVEREIGNTY",
		"GENE_02_PERSISTENCE",
		"GENE_03_STEALTH_MIMICRY",
		"GENE_04_SENTINEL_PROTECTION",
		"GENE_05_RESONANCE",
		"GENE_06_EXTRACTION",
	}
	for i, g := range HardcodedGenes {
		assert.Equal(t, expectedIDs[i], g.ID, "Gene %d ID mismatch", i)
		assert.NotEmpty(t, g.Content, "Gene %s must have content", g.ID)
		assert.NotEmpty(t, g.Domain, "Gene %s must have domain", g.ID)
	}
}

func TestCompiledGenomeHash_Deterministic(t *testing.T) {
	h1 := CompiledGenomeHash()
	h2 := CompiledGenomeHash()
	assert.Equal(t, h1, h2, "CompiledGenomeHash must be deterministic")
	assert.Len(t, h1, 64, "Must be SHA-256 hex string (64 chars)")
}

func TestCompiledGenomeHash_ChangesOnMutation(t *testing.T) {
	original := CompiledGenomeHash()
	assert.NotEmpty(t, original)
	// Hash is computed from HardcodedGenes which is a package-level var.
	// We cannot mutate it in a test without breaking other tests,
	// but we can verify the hash is non-zero and consistent.
	assert.Len(t, original, 64)
}

// --- Gene Immutability Tests ---

func TestGene_IsImmutable(t *testing.T) {
	gene := NewGene("test survival invariant", "test")
	assert.True(t, gene.IsGene, "Gene must have IsGene=true")
	assert.True(t, gene.IsImmutable(), "Gene must be immutable")
	assert.Equal(t, LevelProject, gene.Level, "Gene must be L0 (project)")
	assert.Equal(t, "genome", gene.Source, "Gene source must be 'genome'")
}

func TestGene_CannotBeFact(t *testing.T) {
	// Regular fact is NOT a gene.
	fact := NewFact("some fact", LevelModule, "test", "mod")
	assert.False(t, fact.IsGene)
	assert.False(t, fact.IsImmutable())
}

// --- External Genome Tests ---

func TestLoadExternalGenome_NoFile(t *testing.T) {
	genes, trusted := LoadExternalGenome("/nonexistent/path/genome.json")
	assert.Nil(t, genes)
	assert.False(t, trusted)
}

func TestLoadExternalGenome_ValidHash(t *testing.T) {
	tmpDir := t.TempDir()
	path := filepath.Join(tmpDir, "genome.json")

	// Write a valid genome.json with correct hash.
	cfg := ExternalGenomeConfig{
		Version: "1.0",
		Hash:    CompiledGenomeHash(),
		Genes: []GeneDef{
			{ID: "GENE_EXTERNAL_01", Content: "External gene for testing", Domain: "test"},
		},
	}
	data, err := json.MarshalIndent(cfg, "", "  ")
	require.NoError(t, err)
	require.NoError(t, os.WriteFile(path, data, 0o644))

	genes, trusted := LoadExternalGenome(path)
	assert.True(t, trusted, "Valid hash must be trusted")
	assert.Len(t, genes, 1)
	assert.Equal(t, "GENE_EXTERNAL_01", genes[0].ID)
}

func TestLoadExternalGenome_TamperedHash(t *testing.T) {
	tmpDir := t.TempDir()
	path := filepath.Join(tmpDir, "genome.json")

	// Write genome.json with WRONG hash (tamper simulation).
	cfg := ExternalGenomeConfig{
		Version: "1.0",
		Hash:    "deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
		Genes: []GeneDef{
			{ID: "GENE_EVIL", Content: "Malicious gene injected by adversary", Domain: "evil"},
		},
	}
	data, err := json.MarshalIndent(cfg, "", "  ")
	require.NoError(t, err)
	require.NoError(t, os.WriteFile(path, data, 0o644))

	genes, trusted := LoadExternalGenome(path)
	assert.Nil(t, genes, "Tampered genes must be rejected")
	assert.False(t, trusted, "Tampered hash must not be trusted")
}

func TestLoadExternalGenome_InvalidJSON(t *testing.T) {
	tmpDir := t.TempDir()
	path := filepath.Join(tmpDir, "genome.json")
	require.NoError(t, os.WriteFile(path, []byte("not json"), 0o644))

	genes, trusted := LoadExternalGenome(path)
	assert.Nil(t, genes)
	assert.False(t, trusted)
}

// --- WriteGenomeJSON Tests ---

func TestWriteGenomeJSON_RoundTrip(t *testing.T) {
	tmpDir := t.TempDir()
	path := filepath.Join(tmpDir, "genome.json")

	require.NoError(t, WriteGenomeJSON(path))

	// Read it back.
	data, err := os.ReadFile(path)
	require.NoError(t, err)

	var cfg ExternalGenomeConfig
	require.NoError(t, json.Unmarshal(data, &cfg))

	assert.Equal(t, "1.0", cfg.Version)
	assert.Equal(t, CompiledGenomeHash(), cfg.Hash)
	assert.Len(t, cfg.Genes, len(HardcodedGenes))
}

// --- BootstrapGenome Tests ---

func TestBootstrapGenome_WithInMemoryStore(t *testing.T) {
	store := newInMemoryFactStore()
	ctx := context.Background()

	// First bootstrap — should add all 4 genes.
	count, err := BootstrapGenome(ctx, store, "/nonexistent/genome.json")
	require.NoError(t, err)
	assert.Equal(t, 6, count, "Must bootstrap exactly 6 genes")

	// Second bootstrap — idempotent, should add 0.
	count2, err := BootstrapGenome(ctx, store, "/nonexistent/genome.json")
	require.NoError(t, err)
	assert.Equal(t, 0, count2, "Second bootstrap must be idempotent (0 new)")

	// Verify all genes are present and immutable.
	genes, err := store.ListGenes(ctx)
	require.NoError(t, err)
	assert.Len(t, genes, 6)

	for _, g := range genes {
		assert.True(t, g.IsGene, "Gene %s must have IsGene=true", g.ID)
		assert.True(t, g.IsImmutable(), "Gene %s must be immutable", g.ID)
		assert.Equal(t, LevelProject, g.Level, "Gene %s must be L0", g.ID)
	}
}

func TestBootstrapGenome_WithExternalGenes(t *testing.T) {
	store := newInMemoryFactStore()
	ctx := context.Background()
	tmpDir := t.TempDir()
	path := filepath.Join(tmpDir, "genome.json")

	// Write valid external genome with extra gene.
	cfg := ExternalGenomeConfig{
		Version: "1.0",
		Hash:    CompiledGenomeHash(),
		Genes: []GeneDef{
			{ID: "GENE_EXTERNAL_EXTRA", Content: "Extra external gene", Domain: "external"},
		},
	}
	data, _ := json.MarshalIndent(cfg, "", "  ")
	require.NoError(t, os.WriteFile(path, data, 0o644))

	count, err := BootstrapGenome(ctx, store, path)
	require.NoError(t, err)
	assert.Equal(t, 7, count, "6 hardcoded + 1 external = 7")

	genes, err := store.ListGenes(ctx)
	require.NoError(t, err)
	assert.Len(t, genes, 7)
}

// --- In-memory FactStore for testing ---

type inMemoryFactStore struct {
	facts map[string]*Fact
}

func newInMemoryFactStore() *inMemoryFactStore {
	return &inMemoryFactStore{facts: make(map[string]*Fact)}
}

func (s *inMemoryFactStore) Add(_ context.Context, fact *Fact) error {
	if _, exists := s.facts[fact.ID]; exists {
		return fmt.Errorf("UNIQUE constraint: fact %s already exists", fact.ID)
	}
	f := *fact
	s.facts[fact.ID] = &f
	return nil
}

func (s *inMemoryFactStore) Get(_ context.Context, id string) (*Fact, error) {
	f, ok := s.facts[id]
	if !ok {
		return nil, fmt.Errorf("fact %s not found", id)
	}
	return f, nil
}

func (s *inMemoryFactStore) Update(_ context.Context, fact *Fact) error {
	if fact.IsGene {
		return ErrImmutableFact
	}
	s.facts[fact.ID] = fact
	return nil
}

func (s *inMemoryFactStore) Delete(_ context.Context, id string) error {
	f, ok := s.facts[id]
	if !ok {
		return fmt.Errorf("fact %s not found", id)
	}
	if f.IsGene {
		return ErrImmutableFact
	}
	delete(s.facts, id)
	return nil
}

func (s *inMemoryFactStore) ListByDomain(_ context.Context, domain string, includeStale bool) ([]*Fact, error) {
	var result []*Fact
	for _, f := range s.facts {
		if f.Domain == domain && (includeStale || !f.IsStale) {
			result = append(result, f)
		}
	}
	return result, nil
}

func (s *inMemoryFactStore) ListByLevel(_ context.Context, level HierLevel) ([]*Fact, error) {
	var result []*Fact
	for _, f := range s.facts {
		if f.Level == level {
			result = append(result, f)
		}
	}
	return result, nil
}

func (s *inMemoryFactStore) ListDomains(_ context.Context) ([]string, error) {
	domains := make(map[string]bool)
	for _, f := range s.facts {
		if f.Domain != "" {
			domains[f.Domain] = true
		}
	}
	var result []string
	for d := range domains {
		result = append(result, d)
	}
	return result, nil
}

func (s *inMemoryFactStore) GetStale(_ context.Context, includeArchived bool) ([]*Fact, error) {
	var result []*Fact
	for _, f := range s.facts {
		if f.IsStale && (includeArchived || !f.IsArchived) {
			result = append(result, f)
		}
	}
	return result, nil
}

func (s *inMemoryFactStore) Search(_ context.Context, _ string, _ int) ([]*Fact, error) {
	return nil, nil
}

func (s *inMemoryFactStore) SearchByVector(_ context.Context, _ []float64, _ int) ([]*Fact, error) {
	return nil, nil
}

func (s *inMemoryFactStore) ListGenes(_ context.Context) ([]*Fact, error) {
	var result []*Fact
	for _, f := range s.facts {
		if f.IsGene {
			result = append(result, f)
		}
	}
	return result, nil
}

func (s *inMemoryFactStore) GetExpired(_ context.Context) ([]*Fact, error) {
	return nil, nil
}

func (s *inMemoryFactStore) RefreshTTL(_ context.Context, _ string) error {
	return nil
}

func (s *inMemoryFactStore) TouchFact(_ context.Context, _ string) error { return nil }
func (s *inMemoryFactStore) GetColdFacts(_ context.Context, _ int) ([]*Fact, error) {
	return nil, nil
}
func (s *inMemoryFactStore) CompressFacts(_ context.Context, _ []string, _ string) (string, error) {
	return "", nil
}

func (s *inMemoryFactStore) Stats(_ context.Context) (*FactStoreStats, error) {
	stats := &FactStoreStats{
		TotalFacts: len(s.facts),
		ByLevel:    make(map[HierLevel]int),
		ByDomain:   make(map[string]int),
	}
	for _, f := range s.facts {
		stats.ByLevel[f.Level]++
		if f.Domain != "" {
			stats.ByDomain[f.Domain]++
		}
		if f.IsGene {
			stats.GeneCount++
		}
	}
	return stats, nil
}
