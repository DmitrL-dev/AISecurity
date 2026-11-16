package sqlite

import (
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"sync"
	"time"

	"github.com/syntrex/gomcp/internal/domain/memory"
	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
)

const (
	factPageManifestFixedOverhead int64 = 4 * 1024
	factPageManifestItemOverhead  int64 = 128
	factPageCallRetrySlack        int64 = 8
)

type factPageManifestItem struct {
	createdAt string
	id        string
	sequence  int64
}

type factPageCachedPayload struct {
	ordinal    int64
	key        memory.FactPageKey
	digest     string
	serialized []byte
}

type factPageSnapshot struct {
	mu sync.Mutex

	closed        bool
	id            string
	scope         rlmscope.Scope
	level         memory.HierLevel
	maxFactBytes  int
	highWater     int64
	expectedCount int64
	expiresAtUnix int64
	maxCalls      int64
	callsUsed     int64
	manifestBytes int64
	manifest      []factPageManifestItem
	payload       *factPageCachedPayload
}

type factPageSnapshotCache struct {
	mu sync.Mutex

	snapshots     map[string]*factPageSnapshot
	manifestBytes int64
	now           func() time.Time
}

func newFactPageSnapshotID() (string, error) {
	random := make([]byte, memory.FactPageSnapshotIDBytes)
	if _, err := rand.Read(random); err != nil {
		return "", fmt.Errorf("generate fact page snapshot identity: %w", err)
	}
	return hex.EncodeToString(random), nil
}

func validFactPageSnapshotID(value string) bool {
	if len(value) != memory.FactPageSnapshotIDBytes*2 {
		return false
	}
	decoded, err := hex.DecodeString(value)
	return err == nil && len(decoded) == memory.FactPageSnapshotIDBytes &&
		value == hex.EncodeToString(decoded)
}

func factPageManifestSize(items []factPageManifestItem) int64 {
	total := factPageManifestFixedOverhead
	for _, item := range items {
		total += factPageManifestItemOverhead + int64(len(item.id)+len(item.createdAt))
	}
	return total
}

func factPageSnapshotMaxCalls(rowCount, totalStoredBytes int64) int64 {
	// One call emits the first frame of every row. The second term is a
	// conservative bound on all additional frames after sixfold JSON escaping
	// and the fixed per-fact serialization reserve. The same finite eight-call
	// retry slack used by the Rust gateway permits ambiguous-response retries.
	worstSerializedBytes := 6*totalStoredBytes + rowCount*64*1024
	extraFrameBytes := worstSerializedBytes - rowCount
	if extraFrameBytes < 0 {
		extraFrameBytes = 0
	}
	extraFrames := extraFrameBytes / memory.FactPageFrameRawBytes
	return rowCount + extraFrames + factPageCallRetrySlack
}

func (c *factPageSnapshotCache) currentTimeLocked() time.Time {
	if c.now == nil {
		return time.Now()
	}
	return c.now()
}

func wipeFactPageSnapshotLocked(snapshot *factPageSnapshot) {
	if snapshot.payload != nil {
		for index := range snapshot.payload.serialized {
			snapshot.payload.serialized[index] = 0
		}
		snapshot.payload.serialized = nil
		snapshot.payload = nil
	}
	snapshot.manifest = nil
	snapshot.closed = true
}

func (c *factPageSnapshotCache) cleanupExpiredLocked(nowUnix int64) {
	for snapshotID, snapshot := range c.snapshots {
		if snapshot.expiresAtUnix > nowUnix {
			continue
		}
		snapshot.mu.Lock()
		wipeFactPageSnapshotLocked(snapshot)
		snapshot.mu.Unlock()
		delete(c.snapshots, snapshotID)
		c.manifestBytes -= snapshot.manifestBytes
	}
	if c.manifestBytes < 0 {
		c.manifestBytes = 0
	}
}

func (c *factPageSnapshotCache) register(
	sc rlmscope.Scope,
	level memory.HierLevel,
	maxFactBytes int,
	highWater, expectedCount, totalStoredBytes int64,
	manifest []factPageManifestItem,
) (*factPageSnapshot, error) {
	snapshotID, err := newFactPageSnapshotID()
	if err != nil {
		return nil, err
	}
	manifestBytes := factPageManifestSize(manifest)
	maxCalls := factPageSnapshotMaxCalls(expectedCount, totalStoredBytes)
	if maxCalls < expectedCount || maxCalls <= 0 {
		return nil, fmt.Errorf("invalid fact page call budget")
	}

	c.mu.Lock()
	defer c.mu.Unlock()
	if c.snapshots == nil {
		c.snapshots = make(map[string]*factPageSnapshot)
	}
	now := c.currentTimeLocked()
	c.cleanupExpiredLocked(now.Unix())
	projectedBytes := c.manifestBytes + manifestBytes
	if len(c.snapshots) >= memory.FactPageMaxActiveSnapshots ||
		projectedBytes > memory.FactPageMaxManifestBytes {
		return nil, &memory.FactPageSnapshotCapacityError{
			ActiveSnapshots:    len(c.snapshots) + 1,
			MaxActiveSnapshots: memory.FactPageMaxActiveSnapshots,
			ManifestBytes:      projectedBytes,
			MaxManifestBytes:   memory.FactPageMaxManifestBytes,
		}
	}
	snapshot := &factPageSnapshot{
		id:            snapshotID,
		scope:         sc,
		level:         level,
		maxFactBytes:  maxFactBytes,
		highWater:     highWater,
		expectedCount: expectedCount,
		expiresAtUnix: now.Unix() + memory.FactPageSnapshotTTLSeconds,
		maxCalls:      maxCalls,
		manifestBytes: manifestBytes,
		manifest:      manifest,
	}
	c.snapshots[snapshotID] = snapshot
	c.manifestBytes = projectedBytes
	return snapshot, nil
}

func (snapshot *factPageSnapshot) key(ordinal int64) (memory.FactPageKey, error) {
	if ordinal < 0 || ordinal >= int64(len(snapshot.manifest)) {
		return memory.FactPageKey{}, memory.ErrFactPageChanged
	}
	item := snapshot.manifest[ordinal]
	return memory.FactPageKey{
		CreatedAt:     item.createdAt,
		ID:            item.id,
		SnapshotID:    snapshot.id,
		Sequence:      item.sequence,
		Ordinal:       ordinal,
		ExpiresAtUnix: snapshot.expiresAtUnix,
		MaxCalls:      snapshot.maxCalls,
	}, nil
}

func (c *factPageSnapshotCache) lock(
	sc rlmscope.Scope,
	level memory.HierLevel,
	maxFactBytes int,
	highWater, expectedCount int64,
	key memory.FactPageKey,
) (*factPageSnapshot, error) {
	c.mu.Lock()
	if c.snapshots == nil {
		c.mu.Unlock()
		return nil, memory.ErrFactPageExpired
	}
	nowUnix := c.currentTimeLocked().Unix()
	c.cleanupExpiredLocked(nowUnix)
	snapshot := c.snapshots[key.SnapshotID]
	if snapshot == nil {
		c.mu.Unlock()
		return nil, memory.ErrFactPageExpired
	}
	snapshot.mu.Lock()
	c.mu.Unlock()

	if snapshot.closed || snapshot.expiresAtUnix <= nowUnix {
		snapshot.mu.Unlock()
		return nil, memory.ErrFactPageExpired
	}
	if snapshot.scope != sc || snapshot.level != level || snapshot.maxFactBytes != maxFactBytes ||
		snapshot.highWater != highWater || snapshot.expectedCount != expectedCount ||
		key.ExpiresAtUnix != snapshot.expiresAtUnix || key.MaxCalls != snapshot.maxCalls {
		snapshot.mu.Unlock()
		return nil, memory.ErrFactPageChanged
	}
	expectedKey, err := snapshot.key(key.Ordinal)
	if err != nil || expectedKey != key {
		snapshot.mu.Unlock()
		return nil, memory.ErrFactPageChanged
	}
	if snapshot.callsUsed >= snapshot.maxCalls {
		snapshot.mu.Unlock()
		return nil, memory.ErrFactPageExpired
	}
	snapshot.callsUsed++
	return snapshot, nil
}

func (c *factPageSnapshotCache) release(
	sc rlmscope.Scope,
	level memory.HierLevel,
	key memory.FactPageKey,
) error {
	c.mu.Lock()
	defer c.mu.Unlock()
	if c.snapshots == nil {
		return memory.ErrFactPageExpired
	}
	c.cleanupExpiredLocked(c.currentTimeLocked().Unix())
	snapshot := c.snapshots[key.SnapshotID]
	if snapshot == nil {
		return memory.ErrFactPageExpired
	}
	snapshot.mu.Lock()
	defer snapshot.mu.Unlock()
	if snapshot.scope != sc || snapshot.level != level ||
		key.ExpiresAtUnix != snapshot.expiresAtUnix || key.MaxCalls != snapshot.maxCalls {
		return memory.ErrFactPageChanged
	}
	wipeFactPageSnapshotLocked(snapshot)
	delete(c.snapshots, key.SnapshotID)
	c.manifestBytes -= snapshot.manifestBytes
	if c.manifestBytes < 0 {
		c.manifestBytes = 0
	}
	return nil
}

func cacheFactPagePayloadLocked(
	snapshot *factPageSnapshot,
	key memory.FactPageKey,
	serialized []byte,
) *factPageCachedPayload {
	if snapshot.payload != nil {
		for index := range snapshot.payload.serialized {
			snapshot.payload.serialized[index] = 0
		}
	}
	digest := sha256.Sum256(serialized)
	snapshot.payload = &factPageCachedPayload{
		ordinal:    key.Ordinal,
		key:        key,
		digest:     hex.EncodeToString(digest[:]),
		serialized: serialized,
	}
	return snapshot.payload
}

func factPageFrameLocked(
	payload *factPageCachedPayload,
	offset int,
) (*memory.FactPageRecord, error) {
	if payload == nil || offset < 0 || offset >= len(payload.serialized) {
		return nil, memory.ErrFactPageChanged
	}
	end := offset + memory.FactPageFrameRawBytes
	if end > len(payload.serialized) {
		end = len(payload.serialized)
	}
	data := append([]byte(nil), payload.serialized[offset:end]...)
	return &memory.FactPageRecord{
		Key:        payload.key,
		FactID:     payload.key.ID,
		SHA256:     payload.digest,
		TotalBytes: len(payload.serialized),
		Offset:     offset,
		Data:       data,
		Final:      end == len(payload.serialized),
	}, nil
}
