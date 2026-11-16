package orchestrator

import (
	"crypto/rand"
	"fmt"
)

// GenID generates a collision-safe unique ID with the given prefix, using
// crypto/rand (8 hex bytes) so concurrent captures never collide. Mirrors the
// soc package's internal genID.
func GenID(prefix string) string {
	b := make([]byte, 8)
	_, _ = rand.Read(b)
	return fmt.Sprintf("%s-%x", prefix, b)
}
