package memory

import (
	"context"
	"errors"
)

var exactProtocolToolNames = [...]string{
	"store_project_fact_exact",
	"add_session_fact",
	"get_session_turn",
	"search_session_facts",
	"inspect_current_project",
	"project_fact_stats",
	"list_default_facts_page",
	"list_project_facts_page",
	"search_default_facts_page",
	"search_project_facts_page",
	"default_fact_stats_page",
	"project_fact_stats_page",
	"add_scoped_session_turn",
	"get_scoped_session_turn",
	"search_scoped_session_facts_page",
	"acquire_scoped_session_turn_claim",
	"begin_scoped_session_turn_execution",
	"get_default_causal_chain_bounded",
}

// ProjectExactFactStore is the additive persistence boundary for the exact
// project write tool. It deliberately does not change FactStore: older writers
// retain their legacy fold semantics, while the exact tool can promise that a
// successful response was loaded from the committed SQLite row rather than
// echoing a caller-owned handle.
type ProjectExactFactStore interface {
	StoreProjectFactExact(ctx context.Context, fact *Fact) (stored *Fact, created bool, err error)
}

// ExactProtocolToolNames returns the rollback-safe MCP tools whose arguments
// and responses must never pass through legacy interaction logging or context
// injection. The returned slice is a copy so callers cannot mutate policy.
func ExactProtocolToolNames() []string {
	names := make([]string, len(exactProtocolToolNames))
	copy(names, exactProtocolToolNames[:])
	return names
}

// IsExactProtocolTool reports whether toolName is governed by the exact-memory
// protocol boundary.
func IsExactProtocolTool(toolName string) bool {
	for _, name := range exactProtocolToolNames {
		if toolName == name {
			return true
		}
	}
	return false
}

// FactStore defines the interface for hierarchical fact persistence.
type FactStore interface {
	// CRUD
	Add(ctx context.Context, fact *Fact) error
	Get(ctx context.Context, id string) (*Fact, error)
	Update(ctx context.Context, fact *Fact) error
	Delete(ctx context.Context, id string) error

	// Queries
	ListByDomain(ctx context.Context, domain string, includeStale bool) ([]*Fact, error)
	ListByLevel(ctx context.Context, level HierLevel) ([]*Fact, error)
	ListDomains(ctx context.Context) ([]string, error)
	GetStale(ctx context.Context, includeArchived bool) ([]*Fact, error)
	Search(ctx context.Context, query string, limit int) ([]*Fact, error)

	// SearchByVector ranks facts by cosine similarity to queryVec.
	// Skips facts without an embedding. Returns up to limit results
	// ordered by descending similarity. Empty queryVec returns nil.
	SearchByVector(ctx context.Context, queryVec []float64, limit int) ([]*Fact, error)

	// Genome Layer
	ListGenes(ctx context.Context) ([]*Fact, error)

	// TTL
	GetExpired(ctx context.Context) ([]*Fact, error)
	RefreshTTL(ctx context.Context, id string) error

	// v3.3 Context GC
	TouchFact(ctx context.Context, id string) error                                            // Increment hit_count + update last_accessed_at
	GetColdFacts(ctx context.Context, limit int) ([]*Fact, error)                              // hit_count=0, created >30 days ago
	CompressFacts(ctx context.Context, ids []string, summary string) (newID string, err error) // Archive originals, create summary

	// Stats
	Stats(ctx context.Context) (*FactStoreStats, error)
}

// FactPageKey is the signed, content-free position of one immutable export
// manifest item. CreatedAt is the raw stored SQLite TEXT value; Sequence pins
// the payload version maintained by fact_export_sequence. SnapshotID, Ordinal,
// expiry and call budget are internal opaque-cursor fields, never public page
// fields.
type FactPageKey struct {
	CreatedAt     string `json:"created_at"`
	ID            string `json:"id"`
	SnapshotID    string `json:"snapshot_id"`
	Sequence      int64  `json:"sequence"`
	Ordinal       int64  `json:"ordinal"`
	ExpiresAtUnix int64  `json:"expires_at_unix"`
	MaxCalls      int64  `json:"max_calls"`
}

// FactPageRecord is one detached bounded frame cut from canonical JSON that
// was serialized once after an exact row preflight. Data never aliases the
// snapshot cache and is capped at FactPageFrameRawBytes.
type FactPageRecord struct {
	Key        FactPageKey
	FactID     string
	SHA256     string
	TotalBytes int
	Offset     int
	Data       []byte
	Final      bool
}

// FactPage is one bounded keyset step. Snapshot is an immutable AUTOINCREMENT
// export-sequence high-water mark, so rows inserted after the first request
// cannot appear in a later page even if a foreign writer backdates created_at
// or SQLite reuses a deleted table rowid.
type FactPage struct {
	Snapshot      int64
	ExpectedCount int64
	Key           FactPageKey
	Fact          *Fact
	Record        *FactPageRecord
	HasMore       bool
}

// ExactFactPageStore is deliberately additive instead of growing FactStore.
// The legacy list_facts path keeps its interface and behavior byte-for-byte;
// only stores that explicitly implement this boundary can serve
// list_facts_page. maxFactBytes is part of the signed cursor contract and must
// be applied to both the initial list step and every record reload.
type ExactFactPageStore interface {
	ListByLevelPage(
		ctx context.Context,
		level HierLevel,
		maxFactBytes int,
		snapshot int64,
		expectedCount int64,
		after *FactPageKey,
	) (*FactPage, error)
	GetByLevelPageKey(
		ctx context.Context,
		level HierLevel,
		maxFactBytes int,
		snapshot int64,
		expectedCount int64,
		key FactPageKey,
		offset int,
	) (*FactPageRecord, error)
	ReleaseFactPage(
		ctx context.Context,
		level HierLevel,
		key FactPageKey,
	) error
}

// SessionFactStore is the fail-closed persistence surface for conversation
// memory. Implementations must require an explicit tenant/project scope in ctx
// and apply an exact, non-empty session_id predicate to every operation.
//
// It is deliberately separate from FactStore: the legacy fact tools keep their
// project-wide contract, while callers that promise session isolation cannot
// accidentally fall back to a broader query.
type SessionFactStore interface {
	AddForSession(ctx context.Context, sessionID string, fact *Fact) error
	// AddTurnForSession stores one logical conversation turn exactly once.
	// A valid versioned request identity in CodeRef controls conflict/dedup;
	// otherwise the complete fact payload retains the legacy identity semantics.
	// Every successful dedup returns the original row and deduplicated=true.
	AddTurnForSession(ctx context.Context, sessionID, turnID string, fact *Fact) (*SessionTurnReceipt, bool, error)
	GetTurnForSession(ctx context.Context, sessionID, turnID string) (*SessionTurnReceipt, *Fact, error)
	ListForSession(ctx context.Context, sessionID string, includeStale bool) ([]*Fact, error)
	SearchForSession(ctx context.Context, sessionID, query string, limit int) ([]*Fact, error)
	SearchByVectorForSession(ctx context.Context, sessionID string, queryVec []float64, limit int) ([]*Fact, error)
}

// SessionTurnReceipt is the durable acknowledgement for one exact-session
// turn write. PayloadSHA256 binds the operation id to the stored semantics;
// it is not derived from, and does not reveal, the caller's idempotency token.
type SessionTurnReceipt struct {
	Version       int    `json:"version"`
	TurnID        string `json:"turn_id"`
	FactID        string `json:"fact_id"`
	PayloadSHA256 string `json:"payload_sha256"`
}

var (
	// ErrFactNotFound distinguishes a missing scoped fact from storage failure.
	ErrFactNotFound             = errors.New("fact not found")
	ErrExactFactConflict        = errors.New("live fact with the legacy identity has different exact fields")
	ErrExactFactIntegrity       = errors.New("exact project fact integrity violation")
	ErrExactFactProjectArchived = errors.New("exact project fact store is unavailable while the project is archived")
	ErrSessionTurnConflict      = errors.New("session turn id already committed with different payload")
	ErrSessionTurnIntegrity     = errors.New("session turn receipt integrity violation")
	ErrFactPageChanged          = errors.New("fact page snapshot changed")
	ErrFactPageExpired          = errors.New("fact page snapshot expired")
)

// HotCache defines the interface for in-memory L0 fact cache.
type HotCache interface {
	GetL0Facts(ctx context.Context) ([]*Fact, error)
	InvalidateFact(ctx context.Context, id string) error
	WarmUp(ctx context.Context, facts []*Fact) error
	Close() error
}
