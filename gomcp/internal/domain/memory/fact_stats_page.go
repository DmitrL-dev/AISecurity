package memory

import (
	"context"
	"errors"
)

const (
	FactStatsPageMaxDomains int64 = 10_000

	// encoding/json expands one stored domain byte to at most six wire bytes.
	// The 128-byte reserve covers the object keys, count, quotes and braces.
	FactStatsPageMaxSerializedDomainBytes      int64 = 16 * 1024 * 1024
	FactStatsPageStoredDomainHardMaxBytes      int64 = (FactStatsPageMaxSerializedDomainBytes - 128) / 6
	FactStatsPageStoredDomainScopeHardMaxBytes int64 = 32 * 1024 * 1024
	FactStatsPageMaxSerializedDomainScopeBytes int64 = 32 * 1024 * 1024
	FactStatsPageFrameRawBytes                       = 512 * 1024
	FactStatsPageMaxSegmentsPerPage                  = 2_048
	FactStatsPageMaxSnapshotSegments           int64 = FactStatsPageMaxDomains +
		(FactStatsPageMaxSerializedDomainScopeBytes / FactStatsPageFrameRawBytes)
	FactStatsPageMaxCalls                     = 69
	FactStatsPageSnapshotIDBytes              = 32
	FactStatsPageSnapshotTTLSeconds     int64 = 5 * 60
	FactStatsPageMaxActiveSnapshots     int64 = 2
	FactStatsPageMaxActiveSnapshotBytes       = FactStatsPageMaxActiveSnapshots *
		FactStatsPageMaxSerializedDomainScopeBytes
	FactStatsPageMaxActiveSnapshotSegments = FactStatsPageMaxActiveSnapshots *
		FactStatsPageMaxSnapshotSegments
)

// FixedFactStoreStats is the bounded portion of FactStoreStats. ByDomain is
// deliberately absent: exact stats paging streams immutable domain aggregates
// from a materialized snapshot.
type FixedFactStoreStats struct {
	TotalFacts     int               `json:"total_facts"`
	LiveFacts      int               `json:"live_facts"`
	ArchivedCount  int               `json:"archived_count"`
	ByLevel        map[HierLevel]int `json:"by_level"`
	ByOrigin       map[Origin]int    `json:"by_origin"`
	StaleCount     int               `json:"stale_count"`
	WithEmbeddings int               `json:"with_embeddings"`
	GeneCount      int               `json:"gene_count"`
	ColdCount      int               `json:"cold_count"`
	GenomeHash     string            `json:"genome_hash,omitempty"`
}

// FactStatsDomain is one logical by_domain entry. Snapshot creation serializes
// it once as canonical Go JSON and persists only bounded wire segments.
type FactStatsDomain struct {
	Domain string `json:"domain"`
	Count  int    `json:"count"`
}

// FactStatsDomainSegment is one immutable piece of one canonical domain entry.
// A page packs segments until either the 512 KiB raw budget or the 2,048
// segment work budget is exhausted.
type FactStatsDomainSegment struct {
	SegmentIndex int64
	Ordinal      int64
	SHA256       string
	TotalBytes   int
	StoredOffset int
	StoredBytes  int
	LocalOffset  int
	Offset       int
	Data         []byte
	SegmentFinal bool
	Final        bool
}

// FactStatsPagePosition is the signed continuation boundary. SnapshotID is an
// opaque random identity; the remaining fields pin the materialized snapshot
// and the exact next byte within its ordered segment stream.
type FactStatsPagePosition struct {
	SnapshotID       string
	ExpectedRows     int64
	ExpectedDomains  int64
	ExpectedSegments int64
	SerializedBytes  int64
	SegmentIndex     int64
	SegmentOffset    int
}

// FactStatsPage contains one bounded read from a materialized aggregate
// snapshot. Fixed is present only on the initial step.
type FactStatsPage struct {
	SnapshotID        string
	ExpectedRows      int64
	ExpectedDomains   int64
	ExpectedSegments  int64
	SerializedBytes   int64
	Fixed             *FixedFactStoreStats
	Segments          []FactStatsDomainSegment
	NextSegmentIndex  int64
	NextSegmentOffset int
	Done              bool
}

// FactStatsPageStoredOversize reports a metadata-only SQLite measurement made
// before any stored domain value is selected into Go memory.
type FactStatsPageStoredOversize struct {
	Measurement BoundedSearchStoredOversize
}

func (e *FactStatsPageStoredOversize) Error() string {
	return "stored fact stats data exceeds a hard limit"
}

type FactStatsPageResultOversizeKind string

const (
	FactStatsPageDomainResultOversizeKind FactStatsPageResultOversizeKind = "domain"
	FactStatsPageScopeResultOversizeKind  FactStatsPageResultOversizeKind = "scope"
)

// FactStatsPageResultOversize reports an exact canonical-JSON byte count. It
// carries no domain or fact content and is safe to map to a public 413.
type FactStatsPageResultOversize struct {
	Kind               FactStatsPageResultOversizeKind
	SerializedBytes    int64
	MaxSerializedBytes int64
}

func (e *FactStatsPageResultOversize) Error() string {
	return "serialized fact stats data exceeds a hard limit"
}

// FactStatsPageSnapshotBusy prevents a second initial walk from invalidating
// the immutable snapshot already owned by an in-flight walk for this scope.
type FactStatsPageSnapshotBusy struct{}

func (e *FactStatsPageSnapshotBusy) Error() string {
	return "fact stats snapshot is already active for this scope"
}

// FactStatsPageSnapshotCapacity reports only bounded aggregate metadata. No
// scope or snapshot identity is included in this public-safe typed error.
type FactStatsPageSnapshotCapacity struct {
	ActiveSnapshots       int64
	MaxActiveSnapshots    int64
	ActiveSerializedBytes int64
	MaxSerializedBytes    int64
	ActiveSegments        int64
	MaxActiveSegments     int64
}

func (e *FactStatsPageSnapshotCapacity) Error() string {
	return "fact stats snapshot capacity is exhausted"
}

// ExactFactStatsPageStore is additive so the legacy FactStore.Stats contract
// and all existing implementations remain unchanged.
type ExactFactStatsPageStore interface {
	FactStatsPage(ctx context.Context, position *FactStatsPagePosition) (*FactStatsPage, error)
}

// ErrFactStatsPageChanged means the opaque materialized snapshot no longer
// exists or does not match the signed continuation.
var ErrFactStatsPageChanged = errors.New("fact stats page snapshot changed")
