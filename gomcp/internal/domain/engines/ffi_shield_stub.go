//go:build !shield_native

package engines

import "errors"

// NativeShield is a dummy to make compilation pass when tag is missing.
type NativeShield struct {
	StubShield
}

// NewNativeShield returns an error when built without shield_native tag.
func NewNativeShield() (*NativeShield, error) {
	return nil, errors.New("shield_native build tag not provided; native engine disabled")
}
