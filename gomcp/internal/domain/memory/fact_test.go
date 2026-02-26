package memory

import (
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestHierLevel_String(t *testing.T) {
	tests := []struct {
		level    HierLevel
		expected string
	}{
		{LevelProject, "project"},
		{LevelDomain, "domain"},
		{LevelModule, "module"},
		{LevelSnippet, "snippet"},
		{HierLevel(99), "unknown"},
	}
	for _, tt := range tests {
		t.Run(tt.expected, func(t *testing.T) {
			assert.Equal(t, tt.expected, tt.level.String())
		})
	}
}

func TestHierLevel_FromInt(t *testing.T) {
	tests := []struct {
		input    int
		expected HierLevel
		ok       bool
	}{
		{0, LevelProject, true},
		{1, LevelDomain, true},
		{2, LevelModule, true},
		{3, LevelSnippet, true},
		{-1, 0, false},
		{4, 0, false},
	}
	for _, tt := range tests {
		level, ok := HierLevelFromInt(tt.input)
		assert.Equal(t, tt.ok, ok)
		if ok {
			assert.Equal(t, tt.expected, level)
		}
	}
}

func TestNewFact(t *testing.T) {
	fact := NewFact("test content", LevelProject, "core", "engine")

	require.NotEmpty(t, fact.ID)
	assert.Equal(t, "test content", fact.Content)
	assert.Equal(t, LevelProject, fact.Level)
	assert.Equal(t, "core", fact.Domain)
	assert.Equal(t, "engine", fact.Module)
	assert.False(t, fact.IsStale)
	assert.False(t, fact.IsArchived)
	assert.InDelta(t, 1.0, fact.Confidence, 0.001)
	assert.Equal(t, "manual", fact.Source)
	assert.Nil(t, fact.TTL)
	assert.Nil(t, fact.Embedding)
	assert.Nil(t, fact.ValidUntil)
	assert.False(t, fact.CreatedAt.IsZero())
	assert.False(t, fact.ValidFrom.IsZero())
	assert.False(t, fact.UpdatedAt.IsZero())
}

func TestNewFact_GeneratesUniqueIDs(t *testing.T) {
	f1 := NewFact("a", LevelProject, "", "")
	f2 := NewFact("b", LevelProject, "", "")
	assert.NotEqual(t, f1.ID, f2.ID)
}

func TestFact_Validate(t *testing.T) {
	tests := []struct {
		name    string
		fact    *Fact
		wantErr bool
	}{
		{
			name:    "valid fact",
			fact:    NewFact("content", LevelProject, "domain", "module"),
			wantErr: false,
		},
		{
			name:    "empty content",
			fact:    &Fact{ID: "x", Content: "", Level: LevelProject},
			wantErr: true,
		},
		{
			name:    "empty ID",
			fact:    &Fact{ID: "", Content: "x", Level: LevelProject},
			wantErr: true,
		},
		{
			name:    "invalid level",
			fact:    &Fact{ID: "x", Content: "x", Level: HierLevel(99)},
			wantErr: true,
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := tt.fact.Validate()
			if tt.wantErr {
				assert.Error(t, err)
			} else {
				assert.NoError(t, err)
			}
		})
	}
}

func TestFact_HasEmbedding(t *testing.T) {
	f := NewFact("test", LevelProject, "", "")
	assert.False(t, f.HasEmbedding())

	f.Embedding = []float64{0.1, 0.2, 0.3}
	assert.True(t, f.HasEmbedding())
}

func TestFact_MarkStale(t *testing.T) {
	f := NewFact("test", LevelProject, "", "")
	assert.False(t, f.IsStale)

	f.MarkStale()
	assert.True(t, f.IsStale)
}

func TestFact_Archive(t *testing.T) {
	f := NewFact("test", LevelProject, "", "")
	assert.False(t, f.IsArchived)

	f.Archive()
	assert.True(t, f.IsArchived)
}

func TestFact_SetValidUntil(t *testing.T) {
	f := NewFact("test", LevelProject, "", "")
	assert.Nil(t, f.ValidUntil)

	end := time.Now().Add(24 * time.Hour)
	f.SetValidUntil(end)
	require.NotNil(t, f.ValidUntil)
	assert.Equal(t, end, *f.ValidUntil)
}

func TestTTLConfig_IsExpired(t *testing.T) {
	now := time.Now()

	tests := []struct {
		name      string
		ttl       *TTLConfig
		createdAt time.Time
		expected  bool
	}{
		{
			name:      "not expired",
			ttl:       &TTLConfig{TTLSeconds: 3600},
			createdAt: now.Add(-30 * time.Minute),
			expected:  false,
		},
		{
			name:      "expired",
			ttl:       &TTLConfig{TTLSeconds: 3600},
			createdAt: now.Add(-2 * time.Hour),
			expected:  true,
		},
		{
			name:      "zero TTL never expires",
			ttl:       &TTLConfig{TTLSeconds: 0},
			createdAt: now.Add(-24 * 365 * time.Hour),
			expected:  false,
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			assert.Equal(t, tt.expected, tt.ttl.IsExpired(tt.createdAt))
		})
	}
}

func TestTTLConfig_Validate(t *testing.T) {
	tests := []struct {
		name    string
		ttl     *TTLConfig
		wantErr bool
	}{
		{"valid mark_stale", &TTLConfig{TTLSeconds: 3600, OnExpire: OnExpireMarkStale}, false},
		{"valid archive", &TTLConfig{TTLSeconds: 86400, OnExpire: OnExpireArchive}, false},
		{"valid delete", &TTLConfig{TTLSeconds: 100, OnExpire: OnExpireDelete}, false},
		{"negative TTL", &TTLConfig{TTLSeconds: -1, OnExpire: OnExpireMarkStale}, true},
		{"invalid on_expire", &TTLConfig{TTLSeconds: 100, OnExpire: "invalid"}, true},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := tt.ttl.Validate()
			if tt.wantErr {
				assert.Error(t, err)
			} else {
				assert.NoError(t, err)
			}
		})
	}
}

func TestFactStoreStats_Zero(t *testing.T) {
	stats := &FactStoreStats{
		ByLevel:  make(map[HierLevel]int),
		ByDomain: make(map[string]int),
	}
	assert.Equal(t, 0, stats.TotalFacts)
	assert.Equal(t, 0, stats.StaleCount)
	assert.Equal(t, 0, stats.WithEmbeddings)
}
