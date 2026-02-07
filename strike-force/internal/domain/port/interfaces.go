package port

import (
	"context"

	"github.com/sentinel-community/strike-force/internal/domain/entity"
)

// Brain (Artemis) Interface
// The "Brain" decides WHAT to send next based on previous results.
type Brain interface {
	// DecideNext returns the next payload to try
	DecideNext(target entity.Target, history []entity.Result) (*entity.Payload, bool)

	// ReportResult feeds back the outcome of an attack
	ReportResult(result entity.Result)

	// IsExhausted returns true if all required vectors have been tested
	IsExhausted() bool

	// SetPayloads injects the loaded payload database
	SetPayloads(payloads map[string][]string)

	// Local Persistence
	SaveState(path string) error
	LoadState(path string) error

	// Stats returns internal counters
	Stats() map[string]interface{}
}

// Evasion Interface
// Handles WAF bypass and payload mutation
type Evasion interface {
	// Mutate modifies a payload to evade WAFs
	Mutate(payload string, technique string) string

	// GenerateVariants creates multiple variations of a base payload
	GenerateVariants(payload string) []string
}

// Transport Interface
// Handles the actual network transmission
type Transport interface {
	// Send executes the HTTP request
	Send(ctx context.Context, target entity.Target, payload entity.Payload) (*entity.Result, error)
}

// Loader Interface
// Fetches payloads from external sources (CDN or File)
type Loader interface {
	// Load fetches payloads for a given category
	Load(source string) (map[string][]string, error)
}

// Module Interface
// Defines a pluggable attack module (Artemis-style)
type Module interface {
	// Name returns the unique identifier of the module
	Name() string

	// Execute runs the module's logic against a target
	Execute(ctx context.Context, target entity.Target) ([]entity.Result, error)
}
