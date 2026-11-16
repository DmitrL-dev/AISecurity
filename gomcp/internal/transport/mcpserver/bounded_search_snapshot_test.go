package mcpserver

import (
	"runtime"
	"strings"
	"testing"
	"time"

	"github.com/stretchr/testify/require"

	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
)

func TestBoundedSearchSnapshotCacheRejectsCapacityWithoutEviction(t *testing.T) {
	fixedNow := time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC)
	cache := boundedSearchSnapshotCache{now: func() time.Time { return fixedNow }}
	owner := &Server{}
	results := []boundedSearchCursorFact{{
		FactID: "fact-a", SHA256: strings.Repeat("a", 64), SerializedSize: 1,
	}}
	var first *boundedSearchSnapshot
	for index := 0; index < boundedSearchMaxActiveSnapshots; index++ {
		snapshot, err := cache.register(
			owner, rlmscope.New("tenant-a", "project-a"), strings.Repeat("b", 64),
			"keyword", 20, 1024*1024, results,
		)
		require.NoError(t, err)
		if index == 0 {
			first = snapshot
		}
	}
	_, err := cache.register(
		owner, rlmscope.New("tenant-a", "project-a"), strings.Repeat("b", 64),
		"keyword", 20, 1024*1024, results,
	)
	var capacity *boundedSearchSnapshotCapacityError
	require.ErrorAs(t, err, &capacity)
	require.Same(t, first, cache.snapshots[first.id],
		"capacity rejection must not evict an active snapshot")
}

func TestBoundedSearchAdmissionReservesWorstCasePayloadAndManifest(t *testing.T) {
	fixedNow := time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC)
	cache := boundedSearchSnapshotCache{now: func() time.Time { return fixedNow }}
	owner := &Server{}
	first, err := cache.reserve(
		owner, rlmscope.New("tenant-a", "project-a"), strings.Repeat("a", 64),
		"keyword", 100, factPageMaxFactBytes,
	)
	require.NoError(t, err)
	second, err := cache.reserve(
		owner, rlmscope.New("tenant-a", "project-b"), strings.Repeat("b", 64),
		"keyword", 100, factPageMaxFactBytes,
	)
	require.NoError(t, err)
	_, err = cache.reserve(
		owner, rlmscope.New("tenant-a", "project-c"), strings.Repeat("c", 64),
		"keyword", 100, factPageMaxFactBytes,
	)
	var capacity *boundedSearchSnapshotCapacityError
	require.ErrorAs(t, err, &capacity)
	require.Equal(t, boundedSearchMaxInFlightStarts, cache.initializing)
	require.Equal(t, boundedSearchMaxCachedPayloadBytes, cache.payloadBytes)
	require.Positive(t, cache.manifestBytes)

	cache.close(first)
	cache.close(second)
	require.Zero(t, cache.initializing)
	require.Zero(t, cache.payloadBytes)
	require.Zero(t, cache.manifestBytes)
}

func TestBoundedSearchSnapshotLookupDoesNotHoldCacheMutexWhileSnapshotWaits(t *testing.T) {
	fixedNow := time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC)
	cache := boundedSearchSnapshotCache{now: func() time.Time { return fixedNow }}
	owner := &Server{}
	scope := rlmscope.New("tenant-a", "project-a")
	querySHA := strings.Repeat("b", 64)
	results := []boundedSearchCursorFact{{
		FactID: "fact-a", SHA256: strings.Repeat("a", 64), SerializedSize: 1,
	}}
	snapshot, err := cache.register(owner, scope, querySHA, "keyword", 20, 1024*1024, results)
	require.NoError(t, err)
	cursor := boundedSearchCursor{
		Version: boundedSearchProtocolVersion, SnapshotID: snapshot.id,
		MemoryScope: factPageScope(scope), QuerySHA256: querySHA, Mode: "keyword",
		Limit: 20, MaxFactBytes: 1024 * 1024, ExpiresAtUnix: snapshot.expiresAtUnix,
	}

	snapshot.mu.Lock()
	waiterStarted := make(chan struct{})
	waiterDone := make(chan error, 1)
	go func() {
		close(waiterStarted)
		locked, lockErr := cache.lock(owner, cursor)
		if lockErr == nil {
			locked.mu.Unlock()
		}
		waiterDone <- lockErr
	}()
	<-waiterStarted
	probeDeadline := time.Now().Add(100 * time.Millisecond)
	for time.Now().Before(probeDeadline) {
		if !cache.mu.TryLock() {
			break
		}
		cache.mu.Unlock()
		runtime.Gosched()
	}

	registrationDone := make(chan error, 1)
	go func() {
		_, registerErr := cache.register(
			owner, rlmscope.New("tenant-a", "project-b"), querySHA,
			"keyword", 20, 1024*1024, results,
		)
		registrationDone <- registerErr
	}()
	var registrationBlocked bool
	select {
	case registerErr := <-registrationDone:
		require.NoError(t, registerErr)
	case <-time.After(250 * time.Millisecond):
		registrationBlocked = true
	}
	snapshot.mu.Unlock()
	require.NoError(t, <-waiterDone)
	if registrationBlocked {
		require.NoError(t, <-registrationDone)
		t.Fatal("cache-wide admission waited behind one snapshot mutex")
	}
}

func TestBoundedSearchExpiryKeepsBusyPayloadChargedUntilItCanBeRetired(t *testing.T) {
	fixedNow := time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC)
	cache := boundedSearchSnapshotCache{now: func() time.Time { return fixedNow }}
	owner := &Server{}
	scope := rlmscope.New("tenant-a", "project-a")
	results := []boundedSearchCursorFact{{
		FactID: "fact-a", SHA256: strings.Repeat("a", 64), SerializedSize: 1024,
	}}
	snapshot, err := cache.register(
		owner, scope, strings.Repeat("b", 64), "keyword", 20, 1024*1024, results,
	)
	require.NoError(t, err)

	snapshot.mu.Lock()
	require.NoError(t, cache.reservePayloadLocked(snapshot, 1024))
	require.EqualValues(t, 1024, cache.payloadBytes)
	fixedNow = fixedNow.Add(time.Duration(boundedSearchSnapshotTTLSeconds+1) * time.Second)
	cache.cleanupExpired(fixedNow.Unix())
	require.EqualValues(t, 1024, cache.payloadBytes,
		"an in-flight materialization must stay charged while it owns the snapshot")
	require.Same(t, snapshot, cache.snapshots[snapshot.id])
	snapshot.mu.Unlock()

	cache.cleanupExpired(fixedNow.Unix())
	require.Zero(t, cache.payloadBytes)
	require.NotContains(t, cache.snapshots, snapshot.id)
}
