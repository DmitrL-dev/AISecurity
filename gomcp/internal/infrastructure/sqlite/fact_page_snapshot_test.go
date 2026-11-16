package sqlite

import (
	"errors"
	"strings"
	"testing"
	"time"

	"github.com/stretchr/testify/require"

	"github.com/syntrex/gomcp/internal/domain/memory"
	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
)

func testFactPageManifest(count int, id, createdAt string) []factPageManifestItem {
	manifest := make([]factPageManifestItem, count)
	for index := range manifest {
		manifest[index] = factPageManifestItem{
			id:        id,
			createdAt: createdAt,
			sequence:  int64(index + 1),
		}
	}
	return manifest
}

func TestFactPageSnapshotCacheRejectsCapacityWithoutEvictingActive(t *testing.T) {
	fixedNow := time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC)
	cache := factPageSnapshotCache{now: func() time.Time { return fixedNow }}
	manifest := testFactPageManifest(1, "fact-a", fixedNow.Format(time.RFC3339Nano))

	first, err := cache.register(
		rlmscope.New("tenant-a", "project-a"), memory.LevelProject,
		1024*1024, 1, 1, 128, manifest,
	)
	require.NoError(t, err)
	_, err = cache.register(
		rlmscope.New("tenant-a", "project-b"), memory.LevelProject,
		1024*1024, 2, 1, 128, manifest,
	)
	require.NoError(t, err)
	_, err = cache.register(
		rlmscope.New("tenant-a", "project-c"), memory.LevelProject,
		1024*1024, 3, 1, 128, manifest,
	)
	var capacity *memory.FactPageSnapshotCapacityError
	require.ErrorAs(t, err, &capacity)
	require.Equal(t, 3, capacity.ActiveSnapshots)
	require.Equal(t, memory.FactPageMaxActiveSnapshots, capacity.MaxActiveSnapshots)

	key, err := first.key(0)
	require.NoError(t, err)
	locked, err := cache.lock(
		first.scope, first.level, first.maxFactBytes,
		first.highWater, first.expectedCount, key,
	)
	require.NoError(t, err, "capacity rejection must not evict an active snapshot")
	locked.mu.Unlock()
}

func TestFactPageSnapshotCacheEnforcesAggregateManifestBytes(t *testing.T) {
	fixedNow := time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC)
	cache := factPageSnapshotCache{now: func() time.Time { return fixedNow }}
	manifest := testFactPageManifest(
		9_000, strings.Repeat("i", 256), strings.Repeat("2", 128),
	)
	require.Less(t, factPageManifestSize(manifest), memory.FactPageMaxManifestBytes)

	first, err := cache.register(
		rlmscope.New("tenant-a", "project-a"), memory.LevelProject,
		memory.FactPageMaxSerializedBytes, 9_000, 9_000, 4*1024*1024, manifest,
	)
	require.NoError(t, err)
	_, err = cache.register(
		rlmscope.New("tenant-a", "project-b"), memory.LevelProject,
		memory.FactPageMaxSerializedBytes, 18_000, 9_000, 4*1024*1024, manifest,
	)
	var capacity *memory.FactPageSnapshotCapacityError
	require.ErrorAs(t, err, &capacity)
	require.Equal(t, 2, capacity.ActiveSnapshots)
	require.Greater(t, capacity.ManifestBytes, memory.FactPageMaxManifestBytes)

	key, err := first.key(0)
	require.NoError(t, err)
	locked, err := cache.lock(
		first.scope, first.level, first.maxFactBytes,
		first.highWater, first.expectedCount, key,
	)
	require.NoError(t, err)
	locked.mu.Unlock()
}

func TestFactPageSnapshotCacheExpiresAndNeverRestartsMissingSnapshot(t *testing.T) {
	now := time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC)
	cache := factPageSnapshotCache{now: func() time.Time { return now }}
	scope := rlmscope.New("tenant-a", "project-a")
	snapshot, err := cache.register(
		scope, memory.LevelProject, 1024*1024, 1, 1, 128,
		testFactPageManifest(1, "fact-a", now.Format(time.RFC3339Nano)),
	)
	require.NoError(t, err)
	key, err := snapshot.key(0)
	require.NoError(t, err)

	now = now.Add(time.Duration(memory.FactPageSnapshotTTLSeconds+1) * time.Second)
	_, err = cache.lock(scope, memory.LevelProject, 1024*1024, 1, 1, key)
	require.ErrorIs(t, err, memory.ErrFactPageExpired)
	require.Empty(t, cache.snapshots, "expired snapshots must be removed, never restarted")

	missing := key
	missing.SnapshotID = strings.Repeat("a", memory.FactPageSnapshotIDBytes*2)
	_, err = cache.lock(scope, memory.LevelProject, 1024*1024, 1, 1, missing)
	require.ErrorIs(t, err, memory.ErrFactPageExpired)
}

func TestFactPageSnapshotCachePinsFiniteCallsAndWipesReleasedPayload(t *testing.T) {
	fixedNow := time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC)
	cache := factPageSnapshotCache{now: func() time.Time { return fixedNow }}
	scope := rlmscope.New("tenant-a", "project-a")
	snapshot, err := cache.register(
		scope, memory.LevelProject, 1024*1024, 1, 1, 1,
		testFactPageManifest(1, "fact-a", fixedNow.Format(time.RFC3339Nano)),
	)
	require.NoError(t, err)
	key, err := snapshot.key(0)
	require.NoError(t, err)
	require.EqualValues(t, 9, key.MaxCalls,
		"one bounded one-frame row gets one base call plus finite retry slack")

	locked, err := cache.lock(scope, memory.LevelProject, 1024*1024, 1, 1, key)
	require.NoError(t, err)
	serialized := []byte("canonical payload")
	cacheFactPagePayloadLocked(locked, key, serialized)
	locked.mu.Unlock()

	for call := int64(1); call < key.MaxCalls; call++ {
		locked, err = cache.lock(scope, memory.LevelProject, 1024*1024, 1, 1, key)
		require.NoError(t, err)
		locked.mu.Unlock()
	}
	_, err = cache.lock(scope, memory.LevelProject, 1024*1024, 1, 1, key)
	require.True(t, errors.Is(err, memory.ErrFactPageExpired), err)
	require.NoError(t, cache.release(scope, memory.LevelProject, key))
	for _, value := range serialized {
		require.Zero(t, value, "released canonical payload must be wiped")
	}
	require.Empty(t, cache.snapshots)
}
