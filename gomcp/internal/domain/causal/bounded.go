package causal

import (
	"context"
	"errors"
)

const (
	BoundedCausalMaxDepth       = 1
	BoundedCausalMaxNodes       = 100
	BoundedCausalMaxResultBytes = 512 * 1024
)

// ErrCausalChainTooLarge reports that a bounded query found more nodes than
// the caller permitted. It is intentionally distinct from transport sizing:
// repositories must enforce the node limit before returning a chain.
var ErrCausalChainTooLarge = errors.New("causal chain exceeds max nodes")

type StoredCausalOversizeKind string
type StoredCausalMeasurementKind string

const (
	StoredCausalNodeOversizeKind  StoredCausalOversizeKind    = "row"
	StoredCausalScopeOversizeKind StoredCausalOversizeKind    = "scope"
	StoredCausalBytesMeasurement  StoredCausalMeasurementKind = "stored_bytes"
	StoredCausalResultMeasurement StoredCausalMeasurementKind = "estimated_result_bytes"
)

// StoredCausalOversizeError carries only metadata-derived byte counts. It must
// never contain a node ID, query, or content because the transport can return
// this error for hostile legacy rows.
type StoredCausalOversizeError struct {
	Kind        StoredCausalOversizeKind
	Measurement StoredCausalMeasurementKind
	Measured    int64
	Maximum     int64
}

func (e *StoredCausalOversizeError) Error() string {
	return "stored causal data exceeds a hard limit"
}

func (e *StoredCausalOversizeError) OversizeKind() string {
	return string(e.Kind)
}

func (e *StoredCausalOversizeError) OversizeMeasuredBytes() int64 {
	return e.Measured
}

func (e *StoredCausalOversizeError) OversizeMaximumBytes() int64 {
	return e.Maximum
}

// BoundedCausalStore is the additive persistence boundary used by the bounded
// wire tool. CausalStore remains unchanged so legacy get_causal_chain keeps its
// existing implementation and response contract.
type BoundedCausalStore interface {
	GetChainBounded(ctx context.Context, query string, maxDepth, maxNodes, maxResultBytes int) (*Chain, error)
}
