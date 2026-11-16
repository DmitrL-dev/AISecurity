package soc

import (
	"crypto/rand"
	"fmt"
)

// genID generates a collision-safe unique ID with the given prefix.
// Uses crypto/rand for 8 random hex bytes instead of time.UnixNano
// to prevent collisions under high concurrency.
func genID(prefix string) string {
	b := make([]byte, 8)
	_, _ = rand.Read(b)
	return fmt.Sprintf("%s-%x", prefix, b)
}
