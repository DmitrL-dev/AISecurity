package memory

import "context"

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

	// TTL
	GetExpired(ctx context.Context) ([]*Fact, error)
	RefreshTTL(ctx context.Context, id string) error

	// Stats
	Stats(ctx context.Context) (*FactStoreStats, error)
}

// HotCache defines the interface for in-memory L0 fact cache.
type HotCache interface {
	GetL0Facts(ctx context.Context) ([]*Fact, error)
	InvalidateFact(ctx context.Context, id string) error
	WarmUp(ctx context.Context, facts []*Fact) error
	Close() error
}
