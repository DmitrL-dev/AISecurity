package oracle

import (
	"context"
	"encoding/json"
	"testing"

	"github.com/syntrex/gomcp/internal/domain/crystal"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// --- Mock CrystalStore ---

type mockCrystalStore struct {
	crystals []*crystal.Crystal
}

func (m *mockCrystalStore) Upsert(_ context.Context, _ *crystal.Crystal) error { return nil }
func (m *mockCrystalStore) Get(_ context.Context, path string) (*crystal.Crystal, error) {
	for _, c := range m.crystals {
		if c.Path == path {
			return c, nil
		}
	}
	return nil, nil
}
func (m *mockCrystalStore) Delete(_ context.Context, _ string) error { return nil }
func (m *mockCrystalStore) List(_ context.Context, _ string, _ int) ([]*crystal.Crystal, error) {
	return m.crystals, nil
}
func (m *mockCrystalStore) Search(_ context.Context, _ string, _ int) ([]*crystal.Crystal, error) {
	return nil, nil
}
func (m *mockCrystalStore) Stats(_ context.Context) (*crystal.CrystalStats, error) {
	return &crystal.CrystalStats{TotalCrystals: len(m.crystals)}, nil
}

// --- Tests ---

func TestSynthesizeThreatModel_CleanCode(t *testing.T) {
	store := &mockCrystalStore{
		crystals: []*crystal.Crystal{
			{
				Path: "main.go",
				Name: "main.go",
				Primitives: []crystal.Primitive{
					{Name: "main", Value: "func main() { log.Println(\"starting\") }"},
				},
			},
		},
	}

	report, err := SynthesizeThreatModel(context.Background(), store, nil)
	require.NoError(t, err)
	assert.Equal(t, 1, report.CrystalsScanned)
	assert.Empty(t, report.Findings, "clean code should have no findings")
}

func TestSynthesizeThreatModel_HardcodedPassword(t *testing.T) {
	store := &mockCrystalStore{
		crystals: []*crystal.Crystal{
			{
				Path: "config.go",
				Name: "config.go",
				Primitives: []crystal.Primitive{
					{Name: "dbPassword", Value: `password = "supersecret123"`, SourceLine: 42},
				},
			},
		},
	}

	report, err := SynthesizeThreatModel(context.Background(), store, nil)
	require.NoError(t, err)
	require.NotEmpty(t, report.Findings)

	found := false
	for _, f := range report.Findings {
		if f.Category == "HARDCODED" && f.Severity == "CRITICAL" {
			found = true
			assert.Equal(t, "config.go", f.FilePath)
			assert.Equal(t, 42, f.Line)
		}
	}
	assert.True(t, found, "should detect hardcoded password")
}

func TestSynthesizeThreatModel_WeakConfig(t *testing.T) {
	store := &mockCrystalStore{
		crystals: []*crystal.Crystal{
			{
				Path: "server.go",
				Primitives: []crystal.Primitive{
					{Name: "init", Value: `skipSSLVerify = true; debug = true`},
				},
			},
		},
	}

	report, err := SynthesizeThreatModel(context.Background(), store, nil)
	require.NoError(t, err)

	categories := map[string]bool{}
	for _, f := range report.Findings {
		categories[f.Category] = true
	}
	assert.True(t, categories["WEAK_CONFIG"], "should detect weak config patterns")
}

func TestSynthesizeThreatModel_LogicHole(t *testing.T) {
	store := &mockCrystalStore{
		crystals: []*crystal.Crystal{
			{
				Path: "handler.go",
				Primitives: []crystal.Primitive{
					{Name: "processInput", Value: `// TODO: hack fix security bypass`},
				},
			},
		},
	}

	report, err := SynthesizeThreatModel(context.Background(), store, nil)
	require.NoError(t, err)

	found := false
	for _, f := range report.Findings {
		if f.Category == "LOGIC_HOLE" {
			found = true
		}
	}
	assert.True(t, found, "should detect security TODOs")
}

func TestSynthesizeThreatModel_SecretInCrystal(t *testing.T) {
	store := &mockCrystalStore{
		crystals: []*crystal.Crystal{
			{
				Path: "app.go",
				Primitives: []crystal.Primitive{
					{Name: "apiKey", Value: `api_key = "AKIAIOSFODNN7EXAMPLE123456789012345"`, SourceLine: 5},
				},
			},
		},
	}

	report, err := SynthesizeThreatModel(context.Background(), store, nil)
	require.NoError(t, err)

	hasSecret := false
	for _, f := range report.Findings {
		if f.Category == "SECRET" && f.Severity == "CRITICAL" {
			hasSecret = true
		}
	}
	assert.True(t, hasSecret, "should detect API keys via SecretScanner integration")
}

func TestSynthesizeThreatModel_EmptyCrystals(t *testing.T) {
	store := &mockCrystalStore{crystals: nil}

	report, err := SynthesizeThreatModel(context.Background(), store, nil)
	require.NoError(t, err)
	assert.Equal(t, 0, report.CrystalsScanned)
	assert.Empty(t, report.Findings)
}

func TestSynthesizeThreatModel_PatternCount(t *testing.T) {
	// Verify we have a meaningful number of threat patterns.
	assert.GreaterOrEqual(t, len(threatPatterns), 10, "should have at least 10 threat patterns")
}

// --- Encryption Tests ---

func TestEncryptDecrypt_Roundtrip(t *testing.T) {
	report := &ThreatReport{
		Findings: []ThreatFinding{
			{Category: "SECRET", Severity: "CRITICAL", FilePath: "test.go", Detail: "leaked key"},
		},
		CrystalsScanned: 5,
	}

	data, err := json.Marshal(report)
	require.NoError(t, err)

	genomeHash := "abc123deadbeef456789"

	encrypted, err := EncryptReport(data, genomeHash)
	require.NoError(t, err)
	assert.NotEqual(t, data, encrypted, "encrypted data should differ from plaintext")

	decrypted, err := DecryptReport(encrypted, genomeHash)
	require.NoError(t, err)

	var decoded ThreatReport
	require.NoError(t, json.Unmarshal(decrypted, &decoded))
	assert.Len(t, decoded.Findings, 1)
	assert.Equal(t, "SECRET", decoded.Findings[0].Category)
}

func TestEncryptDecrypt_WrongKey(t *testing.T) {
	data := []byte("sensitive threat report data")

	encrypted, err := EncryptReport(data, "correct-genome-hash")
	require.NoError(t, err)

	_, err = DecryptReport(encrypted, "wrong-genome-hash")
	assert.Error(t, err, "should fail with wrong genome hash")
}

func TestDeriveKey_Deterministic(t *testing.T) {
	k1 := deriveKey("test-hash")
	k2 := deriveKey("test-hash")
	assert.Equal(t, k1, k2, "same genome hash should derive same key")

	k3 := deriveKey("different-hash")
	assert.NotEqual(t, k1, k3, "different genome hashes should derive different keys")
}
