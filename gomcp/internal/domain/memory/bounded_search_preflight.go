package memory

import "context"

// BoundedSearchStoredOversize reports a database-side byte measurement made
// before any variable-width fact value is selected. StoredBytes is deliberately
// not an exact serialized Fact size.
type BoundedSearchStoredOversize struct {
	Kind           string
	StoredBytes    int64
	MaxStoredBytes int64
	StoredRows     int64
	MaxStoredRows  int64
}

const (
	BoundedSearchStoredIdentityOversizeKind = "identity"
	BoundedSearchStoredRowOversizeKind      = "row"
	BoundedSearchStoredScopeOversizeKind    = "scope"
	BoundedSearchStoredRowCountOversizeKind = "row_count"
)

// BoundedSearchSnapshot is valid only for the duration of the callback passed
// to ExactBoundedSearchStore.WithBoundedSearchSnapshot.
type BoundedSearchSnapshot interface {
	Search(ctx context.Context, query string, limit int) ([]*Fact, error)
	SearchByVector(ctx context.Context, queryVec []float64, limit int) ([]*Fact, error)
	Get(ctx context.Context, id string) (*Fact, error)
}

// ExactBoundedSearchStore is an additive, fail-closed capability for public
// bounded search. Implementations must establish one read snapshot, measure
// all selected rows before materializing any variable-width value, and run the
// callback in that same snapshot. A nil factIDs slice selects the whole exact
// non-session scope; a non-nil slice limits continuation checks to those frozen
// IDs so unrelated later inserts remain invisible.
type ExactBoundedSearchStore interface {
	WithBoundedSearchSnapshot(
		ctx context.Context,
		factIDs []string,
		run func(BoundedSearchSnapshot) ([]*Fact, error),
	) ([]*Fact, *BoundedSearchStoredOversize, error)
}
