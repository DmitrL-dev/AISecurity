package memory

import "context"

// ExactSessionFactReader is an additive point lookup used to revalidate a
// frozen ranked session result without materializing the whole session. The
// exact tenant/project/session predicate is part of the persistence contract.
type ExactSessionFactReader interface {
	GetForSession(ctx context.Context, sessionID, factID string) (*Fact, error)
}

// ExactBoundedSessionSearchStore is the fail-closed persistence capability for
// the bounded session-search wire. Implementations must establish one exact
// tenant/project/session read snapshot, measure every selected row before
// materializing variable-width values, and run the callback in that snapshot.
// A nil factIDs slice selects the complete eligible session scope; a non-nil
// slice limits continuation revalidation to the signed frozen IDs.
type ExactBoundedSessionSearchStore interface {
	WithBoundedSessionSearchSnapshot(
		ctx context.Context,
		sessionID string,
		factIDs []string,
		run func(BoundedSearchSnapshot) ([]*Fact, error),
	) ([]*Fact, *BoundedSearchStoredOversize, error)
}
