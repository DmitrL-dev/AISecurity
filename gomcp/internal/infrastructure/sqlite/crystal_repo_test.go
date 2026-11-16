package sqlite

import (
	"context"
	"testing"

	"github.com/syntrex/gomcp/internal/domain/crystal"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func newTestCrystalRepo(t *testing.T) *CrystalRepo {
	t.Helper()
	db, err := OpenMemory()
	require.NoError(t, err)
	t.Cleanup(func() { db.Close() })

	repo, err := NewCrystalRepo(db)
	require.NoError(t, err)
	return repo
}

func makeCrystal(path, name string) *crystal.Crystal {
	return &crystal.Crystal{
		Path:            path,
		Name:            name,
		TokenCount:      150,
		ContentHash:     "hash123",
		PrimitivesCount: 2,
		Primitives: []crystal.Primitive{
			{PType: "function", Name: "main", Value: "func main()", SourceLine: 1, Confidence: 1.0},
			{PType: "function", Name: "init", Value: "func init()", SourceLine: 5, Confidence: 0.9},
		},
		IndexedAt:   1700000000.0,
		SourceMtime: 1699999000.0,
		SourceHash:  "src_hash",
	}
}

func TestCrystalRepo_Upsert_Get(t *testing.T) {
	repo := newTestCrystalRepo(t)
	ctx := context.Background()

	c := makeCrystal("cmd/main.go", "main.go")
	require.NoError(t, repo.Upsert(ctx, c))

	got, err := repo.Get(ctx, "cmd/main.go")
	require.NoError(t, err)
	require.NotNil(t, got)

	assert.Equal(t, "cmd/main.go", got.Path)
	assert.Equal(t, "main.go", got.Name)
	assert.Equal(t, 150, got.TokenCount)
	assert.Equal(t, 2, got.PrimitivesCount)
	assert.Len(t, got.Primitives, 2)
	assert.Equal(t, "function", got.Primitives[0].PType)
}

func TestCrystalRepo_Upsert_Overwrite(t *testing.T) {
	repo := newTestCrystalRepo(t)
	ctx := context.Background()

	c := makeCrystal("main.go", "main.go")
	require.NoError(t, repo.Upsert(ctx, c))

	c.TokenCount = 300
	c.PrimitivesCount = 5
	require.NoError(t, repo.Upsert(ctx, c))

	got, err := repo.Get(ctx, "main.go")
	require.NoError(t, err)
	assert.Equal(t, 300, got.TokenCount)
	assert.Equal(t, 5, got.PrimitivesCount)
}

func TestCrystalRepo_Get_NotFound(t *testing.T) {
	repo := newTestCrystalRepo(t)
	ctx := context.Background()

	got, err := repo.Get(ctx, "nonexistent.go")
	assert.Error(t, err)
	assert.Nil(t, got)
}

func TestCrystalRepo_Delete(t *testing.T) {
	repo := newTestCrystalRepo(t)
	ctx := context.Background()

	c := makeCrystal("delete_me.go", "delete_me.go")
	require.NoError(t, repo.Upsert(ctx, c))
	require.NoError(t, repo.Delete(ctx, "delete_me.go"))

	got, err := repo.Get(ctx, "delete_me.go")
	assert.Error(t, err)
	assert.Nil(t, got)
}

func TestCrystalRepo_List(t *testing.T) {
	repo := newTestCrystalRepo(t)
	ctx := context.Background()

	for _, p := range []string{"cmd/main.go", "internal/foo.go", "internal/bar.go", "README.md"} {
		require.NoError(t, repo.Upsert(ctx, makeCrystal(p, p)))
	}

	// List all
	all, err := repo.List(ctx, "", 100)
	require.NoError(t, err)
	assert.Len(t, all, 4)

	// List with pattern
	internal, err := repo.List(ctx, "internal%", 100)
	require.NoError(t, err)
	assert.Len(t, internal, 2)
}

func TestCrystalRepo_Search(t *testing.T) {
	repo := newTestCrystalRepo(t)
	ctx := context.Background()

	c1 := makeCrystal("server.go", "server.go")
	c1.Primitives = []crystal.Primitive{
		{PType: "function", Name: "handleRequest", Value: "func handleRequest()", SourceLine: 10, Confidence: 1.0},
	}
	c2 := makeCrystal("client.go", "client.go")
	c2.Primitives = []crystal.Primitive{
		{PType: "function", Name: "sendRequest", Value: "func sendRequest()", SourceLine: 5, Confidence: 1.0},
	}
	c3 := makeCrystal("utils.go", "utils.go")
	c3.Primitives = []crystal.Primitive{
		{PType: "function", Name: "helper", Value: "func helper()", SourceLine: 1, Confidence: 1.0},
	}

	for _, c := range []*crystal.Crystal{c1, c2, c3} {
		require.NoError(t, repo.Upsert(ctx, c))
	}

	results, err := repo.Search(ctx, "Request", 10)
	require.NoError(t, err)
	assert.Len(t, results, 2)
}

func TestCrystalRepo_Stats(t *testing.T) {
	repo := newTestCrystalRepo(t)
	ctx := context.Background()

	c1 := makeCrystal("main.go", "main.go")
	c1.TokenCount = 100
	c2 := makeCrystal("server.py", "server.py")
	c2.TokenCount = 200
	c2.PrimitivesCount = 5

	require.NoError(t, repo.Upsert(ctx, c1))
	require.NoError(t, repo.Upsert(ctx, c2))

	stats, err := repo.Stats(ctx)
	require.NoError(t, err)
	assert.Equal(t, 2, stats.TotalCrystals)
	assert.Equal(t, 300, stats.TotalTokens)
}
