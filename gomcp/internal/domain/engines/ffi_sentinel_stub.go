//go:build !sentinel_native

package engines

import "errors"

// NativeSentinelCore is a dummy to make compilation pass when tag is missing.
type NativeSentinelCore struct {
	StubSentinelCore
}

// NewNativeSentinelCore returns an error when built without sentinel_native tag.
func NewNativeSentinelCore() (*NativeSentinelCore, error) {
	return nil, errors.New("sentinel_native build tag not provided; native engine disabled")
}
