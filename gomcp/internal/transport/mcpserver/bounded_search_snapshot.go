package mcpserver

import (
	"crypto/rand"
	"encoding/hex"
	"fmt"
	"sync"
	"time"

	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
)

const (
	boundedSearchSnapshotIDBytes             = 32
	boundedSearchSnapshotTTLSeconds    int64 = 5 * 60
	boundedSearchMaxActiveSnapshots          = 128
	boundedSearchMaxInFlightStarts           = 2
	boundedSearchMaxManifestBytes      int64 = 8 * 1024 * 1024
	boundedSearchMaxCachedPayloadBytes int64 = 2 * int64(factPageMaxFactBytes)
	boundedSearchManifestBaseBytes     int64 = 4 * 1024
	boundedSearchManifestEntryBytes    int64 = 128
	boundedSearchMaxFactIdentityBytes        = 256
	boundedSearchDigestTextBytes             = 64
)

type boundedSearchCachedPayload struct {
	resultIndex int
	serialized  []byte
}

type boundedSearchSnapshot struct {
	mu sync.Mutex

	closed         bool
	initialized    bool
	id             string
	owner          *Server
	scope          rlmscope.Scope
	querySHA256    string
	mode           string
	limit          int
	maxFactBytes   int
	expiresAtUnix  int64
	results        []boundedSearchCursorFact
	payload        *boundedSearchCachedPayload
	expectedResult int
	expectedOffset int
	expectedCall   int
	maxCalls       int
	callsUsed      int
	maxBytes       int64
	bytesEmitted   int64

	// Protected only by boundedSearchSnapshotCache.mu. Cache-wide accounting
	// can therefore detach an expired entry without waiting on snapshot.mu.
	cacheManifestBytes int64
	cachePayloadBytes  int64
	cacheInitializing  bool
}

type boundedSearchSnapshotCache struct {
	mu sync.Mutex

	snapshots     map[string]*boundedSearchSnapshot
	manifestBytes int64
	payloadBytes  int64
	initializing  int
	now           func() time.Time
}

type boundedSearchSnapshotCapacityError struct{}

func (*boundedSearchSnapshotCapacityError) Error() string {
	return "bounded search snapshot capacity exhausted"
}

type boundedSearchSnapshotExpiredError struct{}

func (*boundedSearchSnapshotExpiredError) Error() string {
	return "bounded search snapshot expired"
}

type boundedSearchSnapshotCursorError struct{}

func (*boundedSearchSnapshotCursorError) Error() string {
	return "bounded search cursor does not match its snapshot"
}

type boundedSearchSnapshotWorkError struct{}

func (*boundedSearchSnapshotWorkError) Error() string {
	return "bounded search snapshot exhausted its work budget"
}

var processBoundedSearchSnapshots boundedSearchSnapshotCache

func newBoundedSearchSnapshotID() (string, error) {
	random := make([]byte, boundedSearchSnapshotIDBytes)
	if _, err := rand.Read(random); err != nil {
		return "", fmt.Errorf("generate bounded search snapshot identity: %w", err)
	}
	return hex.EncodeToString(random), nil
}

func validBoundedSearchSnapshotID(value string) bool {
	if len(value) != boundedSearchSnapshotIDBytes*2 {
		return false
	}
	decoded, err := hex.DecodeString(value)
	return err == nil && len(decoded) == boundedSearchSnapshotIDBytes &&
		value == hex.EncodeToString(decoded)
}

func boundedSearchManifestSize(results []boundedSearchCursorFact) int64 {
	total := boundedSearchManifestBaseBytes
	for _, result := range results {
		total += boundedSearchManifestEntryBytes + int64(len(result.FactID)+len(result.SHA256))
	}
	return total
}

func boundedSearchReservedManifestSize(limit int) int64 {
	return boundedSearchManifestBaseBytes + int64(limit)*(boundedSearchManifestEntryBytes+boundedSearchMaxFactIdentityBytes+boundedSearchDigestTextBytes)
}

func boundedSearchBudgets(results []boundedSearchCursorFact) (int, int64, error) {
	maxCalls := 0
	var maxBytes int64
	for _, result := range results {
		if result.SerializedSize <= 0 {
			return 0, 0, fmt.Errorf("bounded search result has no serialized payload")
		}
		maxCalls += (result.SerializedSize + factPageFrameRawBytes - 1) / factPageFrameRawBytes
		maxBytes += int64(result.SerializedSize)
	}
	if maxCalls <= 0 || maxBytes <= 0 {
		return 0, 0, fmt.Errorf("bounded search result budget is empty")
	}
	return maxCalls, maxBytes, nil
}

func (c *boundedSearchSnapshotCache) currentTimeLocked() time.Time {
	if c.now != nil {
		return c.now()
	}
	return time.Now()
}

// detachLocked releases cache-wide charges without acquiring snapshot.mu.
func (c *boundedSearchSnapshotCache) detachLocked(snapshot *boundedSearchSnapshot) bool {
	if snapshot == nil || c.snapshots[snapshot.id] != snapshot {
		return false
	}
	delete(c.snapshots, snapshot.id)
	c.manifestBytes -= snapshot.cacheManifestBytes
	c.payloadBytes -= snapshot.cachePayloadBytes
	if snapshot.cacheInitializing {
		c.initializing--
	}
	snapshot.cacheManifestBytes = 0
	snapshot.cachePayloadBytes = 0
	snapshot.cacheInitializing = false
	if c.manifestBytes < 0 {
		c.manifestBytes = 0
	}
	if c.payloadBytes < 0 {
		c.payloadBytes = 0
	}
	if c.initializing < 0 {
		c.initializing = 0
	}
	return true
}

func (c *boundedSearchSnapshotCache) expiredCandidatesLocked(nowUnix int64) []*boundedSearchSnapshot {
	candidates := make([]*boundedSearchSnapshot, 0)
	for _, snapshot := range c.snapshots {
		if snapshot.expiresAtUnix <= nowUnix {
			candidates = append(candidates, snapshot)
		}
	}
	return candidates
}

func wipeBoundedSearchSnapshotLocked(snapshot *boundedSearchSnapshot) {
	if snapshot.payload != nil {
		for index := range snapshot.payload.serialized {
			snapshot.payload.serialized[index] = 0
		}
		snapshot.payload.serialized = nil
		snapshot.payload = nil
	}
	snapshot.results = nil
	snapshot.closed = true
}

func (c *boundedSearchSnapshotCache) retireExpired(
	candidates []*boundedSearchSnapshot,
	nowUnix int64,
) {
	for _, snapshot := range candidates {
		// A busy materialization stays charged until it releases snapshot.mu.
		// TryLock keeps cache admission independent of any one slow snapshot.
		if !snapshot.mu.TryLock() {
			continue
		}
		c.mu.Lock()
		detached := snapshot.expiresAtUnix <= nowUnix && c.detachLocked(snapshot)
		c.mu.Unlock()
		if detached {
			wipeBoundedSearchSnapshotLocked(snapshot)
		}
		snapshot.mu.Unlock()
	}
}

func (c *boundedSearchSnapshotCache) cleanupExpired(nowUnix int64) {
	c.mu.Lock()
	candidates := c.expiredCandidatesLocked(nowUnix)
	c.mu.Unlock()
	c.retireExpired(candidates, nowUnix)
}

// reserve charges worst-case manifest and payload memory before SQLite or JSON
// materialization. No more than two initial searches may execute concurrently.
func (c *boundedSearchSnapshotCache) reserve(
	owner *Server,
	sc rlmscope.Scope,
	querySHA256, mode string,
	limit, maxFactBytes int,
) (*boundedSearchSnapshot, error) {
	if owner == nil || limit < 1 || limit > 100 ||
		maxFactBytes < 1 || maxFactBytes > factPageMaxFactBytes {
		return nil, fmt.Errorf("invalid bounded search admission bounds")
	}
	manifestReservation := boundedSearchReservedManifestSize(limit)
	payloadReservation := int64(maxFactBytes)
	if manifestReservation > boundedSearchMaxManifestBytes ||
		payloadReservation > boundedSearchMaxCachedPayloadBytes {
		return nil, &boundedSearchSnapshotCapacityError{}
	}
	snapshotID, err := newBoundedSearchSnapshotID()
	if err != nil {
		return nil, err
	}

	c.mu.Lock()
	if c.snapshots == nil {
		c.snapshots = make(map[string]*boundedSearchSnapshot)
	}
	now := c.currentTimeLocked()
	candidates := c.expiredCandidatesLocked(now.Unix())
	c.mu.Unlock()
	c.retireExpired(candidates, now.Unix())

	c.mu.Lock()
	now = c.currentTimeLocked()
	if len(c.snapshots) >= boundedSearchMaxActiveSnapshots ||
		c.initializing >= boundedSearchMaxInFlightStarts ||
		c.manifestBytes+manifestReservation > boundedSearchMaxManifestBytes ||
		c.payloadBytes+payloadReservation > boundedSearchMaxCachedPayloadBytes {
		c.mu.Unlock()
		return nil, &boundedSearchSnapshotCapacityError{}
	}
	snapshot := &boundedSearchSnapshot{
		id:                 snapshotID,
		owner:              owner,
		scope:              sc,
		querySHA256:        querySHA256,
		mode:               mode,
		limit:              limit,
		maxFactBytes:       maxFactBytes,
		expiresAtUnix:      now.Unix() + boundedSearchSnapshotTTLSeconds,
		cacheManifestBytes: manifestReservation,
		cachePayloadBytes:  payloadReservation,
		cacheInitializing:  true,
	}
	c.snapshots[snapshotID] = snapshot
	c.manifestBytes += manifestReservation
	c.payloadBytes += payloadReservation
	c.initializing++
	c.mu.Unlock()
	return snapshot, nil
}

// activate replaces conservative reservations with exact retained charges.
func (c *boundedSearchSnapshotCache) activate(
	snapshot *boundedSearchSnapshot,
	results []boundedSearchCursorFact,
	firstPayload []byte,
) error {
	if snapshot == nil || len(results) == 0 || len(results) > snapshot.limit {
		return fmt.Errorf("invalid bounded search activation manifest")
	}
	maxCalls, maxBytes, err := boundedSearchBudgets(results)
	if err != nil {
		return err
	}
	actualManifestBytes := boundedSearchManifestSize(results)
	retainFirstPayload := len(firstPayload) > factPageFrameRawBytes
	if len(firstPayload) > 0 && len(firstPayload) != results[0].SerializedSize {
		return fmt.Errorf("bounded search first payload size does not match manifest")
	}
	retainedPayloadBytes := int64(0)
	if retainFirstPayload {
		retainedPayloadBytes = int64(len(firstPayload))
	}

	snapshot.mu.Lock()
	defer snapshot.mu.Unlock()
	if snapshot.closed || snapshot.initialized {
		return &boundedSearchSnapshotExpiredError{}
	}
	c.mu.Lock()
	nowUnix := c.currentTimeLocked().Unix()
	if c.snapshots[snapshot.id] != snapshot || !snapshot.cacheInitializing ||
		snapshot.expiresAtUnix <= nowUnix {
		c.mu.Unlock()
		return &boundedSearchSnapshotExpiredError{}
	}
	projectedManifestBytes := c.manifestBytes - snapshot.cacheManifestBytes + actualManifestBytes
	projectedPayloadBytes := c.payloadBytes - snapshot.cachePayloadBytes + retainedPayloadBytes
	if actualManifestBytes > snapshot.cacheManifestBytes ||
		projectedManifestBytes > boundedSearchMaxManifestBytes ||
		projectedPayloadBytes > boundedSearchMaxCachedPayloadBytes {
		c.mu.Unlock()
		return &boundedSearchSnapshotCapacityError{}
	}
	c.manifestBytes = projectedManifestBytes
	c.payloadBytes = projectedPayloadBytes
	c.initializing--
	snapshot.cacheManifestBytes = actualManifestBytes
	snapshot.cachePayloadBytes = retainedPayloadBytes
	snapshot.cacheInitializing = false
	c.mu.Unlock()

	snapshot.results = append([]boundedSearchCursorFact(nil), results...)
	snapshot.maxCalls = maxCalls
	snapshot.maxBytes = maxBytes
	snapshot.initialized = true
	if retainFirstPayload {
		snapshot.payload = &boundedSearchCachedPayload{resultIndex: 0, serialized: firstPayload}
	}
	return nil
}

// register is a completed-snapshot convenience for cache-level tests.
func (c *boundedSearchSnapshotCache) register(
	owner *Server,
	sc rlmscope.Scope,
	querySHA256, mode string,
	limit, maxFactBytes int,
	results []boundedSearchCursorFact,
) (*boundedSearchSnapshot, error) {
	snapshot, err := c.reserve(owner, sc, querySHA256, mode, limit, maxFactBytes)
	if err != nil {
		return nil, err
	}
	if err := c.activate(snapshot, results, nil); err != nil {
		c.close(snapshot)
		return nil, err
	}
	return snapshot, nil
}

// lock finishes cache lookup before waiting for snapshot.mu.
func (c *boundedSearchSnapshotCache) lock(
	owner *Server,
	cursor boundedSearchCursor,
) (*boundedSearchSnapshot, error) {
	c.mu.Lock()
	if c.snapshots == nil {
		c.mu.Unlock()
		return nil, &boundedSearchSnapshotExpiredError{}
	}
	nowUnix := c.currentTimeLocked().Unix()
	candidates := c.expiredCandidatesLocked(nowUnix)
	c.mu.Unlock()
	c.retireExpired(candidates, nowUnix)

	c.mu.Lock()
	snapshot := c.snapshots[cursor.SnapshotID]
	c.mu.Unlock()
	if snapshot == nil {
		return nil, &boundedSearchSnapshotExpiredError{}
	}

	snapshot.mu.Lock()
	c.mu.Lock()
	attached := c.snapshots[snapshot.id] == snapshot
	nowUnix = c.currentTimeLocked().Unix()
	if attached && (snapshot.closed || !snapshot.initialized || snapshot.expiresAtUnix <= nowUnix) {
		c.detachLocked(snapshot)
		attached = false
	}
	c.mu.Unlock()
	if !attached || snapshot.closed || !snapshot.initialized || snapshot.expiresAtUnix <= nowUnix {
		wipeBoundedSearchSnapshotLocked(snapshot)
		snapshot.mu.Unlock()
		return nil, &boundedSearchSnapshotExpiredError{}
	}
	if snapshot.owner != owner || factPageScope(snapshot.scope) != cursor.MemoryScope ||
		snapshot.querySHA256 != cursor.QuerySHA256 || snapshot.mode != cursor.Mode ||
		snapshot.limit != cursor.Limit || snapshot.maxFactBytes != cursor.MaxFactBytes ||
		snapshot.expiresAtUnix != cursor.ExpiresAtUnix ||
		snapshot.expectedResult != cursor.ResultIndex ||
		snapshot.expectedOffset != cursor.IntraFactOffset ||
		snapshot.expectedCall != cursor.CallIndex {
		snapshot.mu.Unlock()
		return nil, &boundedSearchSnapshotCursorError{}
	}
	if snapshot.callsUsed >= snapshot.maxCalls || snapshot.bytesEmitted >= snapshot.maxBytes {
		snapshot.mu.Unlock()
		return nil, &boundedSearchSnapshotWorkError{}
	}
	return snapshot, nil
}

// reservePayloadLocked charges one exact current fact before materializing it.
// The caller holds snapshot.mu; cache.mu is never held while waiting for it.
func (c *boundedSearchSnapshotCache) reservePayloadLocked(
	snapshot *boundedSearchSnapshot,
	payloadBytes int64,
) error {
	if payloadBytes <= 0 || payloadBytes > int64(snapshot.maxFactBytes) || snapshot.payload != nil {
		return &boundedSearchSnapshotWorkError{}
	}
	c.mu.Lock()
	defer c.mu.Unlock()
	if c.snapshots[snapshot.id] != snapshot || snapshot.cachePayloadBytes != 0 ||
		snapshot.expiresAtUnix <= c.currentTimeLocked().Unix() {
		return &boundedSearchSnapshotExpiredError{}
	}
	if c.payloadBytes+payloadBytes > boundedSearchMaxCachedPayloadBytes {
		return &boundedSearchSnapshotCapacityError{}
	}
	c.payloadBytes += payloadBytes
	snapshot.cachePayloadBytes = payloadBytes
	return nil
}

// releasePayloadLocked wipes and uncharges the current fact atomically with
// respect to this snapshot. The caller holds snapshot.mu.
func (c *boundedSearchSnapshotCache) releasePayloadLocked(snapshot *boundedSearchSnapshot) {
	if snapshot.payload != nil {
		for index := range snapshot.payload.serialized {
			snapshot.payload.serialized[index] = 0
		}
		snapshot.payload.serialized = nil
		snapshot.payload = nil
	}
	c.mu.Lock()
	if c.snapshots[snapshot.id] == snapshot {
		c.payloadBytes -= snapshot.cachePayloadBytes
		if c.payloadBytes < 0 {
			c.payloadBytes = 0
		}
	}
	snapshot.cachePayloadBytes = 0
	c.mu.Unlock()
}

func (c *boundedSearchSnapshotCache) close(snapshot *boundedSearchSnapshot) {
	if snapshot == nil {
		return
	}
	snapshot.mu.Lock()
	wipeBoundedSearchSnapshotLocked(snapshot)
	snapshot.mu.Unlock()
	c.mu.Lock()
	c.detachLocked(snapshot)
	c.mu.Unlock()
}
