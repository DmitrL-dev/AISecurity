package crystal

import (
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestCrystal_Fields(t *testing.T) {
	c := &Crystal{
		Path:            "main.go",
		Name:            "main.go",
		TokenCount:      100,
		ContentHash:     "abc123",
		PrimitivesCount: 3,
		Primitives: []Primitive{
			{PType: "function", Name: "main", Value: "func main()", SourceLine: 1, Confidence: 1.0},
		},
		IndexedAt:      1700000000.0,
		SourceMtime:    1699999000.0,
		SourceHash:     "def456",
		HumanConfirmed: false,
	}

	assert.Equal(t, "main.go", c.Path)
	assert.Equal(t, 100, c.TokenCount)
	assert.Len(t, c.Primitives, 1)
	assert.Equal(t, "function", c.Primitives[0].PType)
	assert.False(t, c.HumanConfirmed)
}

func TestCrystalStats_Zero(t *testing.T) {
	stats := &CrystalStats{
		ByExtension: make(map[string]int),
	}
	assert.Equal(t, 0, stats.TotalCrystals)
	assert.Equal(t, 0, stats.TotalPrimitives)
	assert.Equal(t, 0, stats.TotalTokens)
}
