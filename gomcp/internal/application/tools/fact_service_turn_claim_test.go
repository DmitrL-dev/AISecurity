package tools

import (
	"strings"
	"testing"

	"github.com/stretchr/testify/require"

	"github.com/syntrex/gomcp/internal/domain/memory"
)

const (
	boundedClaimTestTurnID = "turn_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
	boundedClaimRequestRef = "session-turn-request-v1:sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
)

func TestCompletedSessionTurnClaimFactIDIsBounded(t *testing.T) {
	for _, tc := range []struct {
		name    string
		factID  string
		wantErr bool
	}{
		{name: "one byte", factID: "f"},
		{name: "256 bytes", factID: strings.Repeat("f", 256)},
		{name: "empty", factID: "", wantErr: true},
		{name: "257 bytes", factID: strings.Repeat("f", 257), wantErr: true},
	} {
		t.Run(tc.name, func(t *testing.T) {
			claim := &memory.SessionTurnClaim{
				Version:         1,
				TurnID:          boundedClaimTestTurnID,
				RequestRef:      boundedClaimRequestRef,
				State:           memory.SessionTurnCompleted,
				Generation:      1,
				CompletedFactID: tc.factID,
			}
			err := validateSessionTurnClaim(claim, boundedClaimTestTurnID, boundedClaimRequestRef)
			if tc.wantErr {
				require.ErrorIs(t, err, memory.ErrSessionTurnClaimIntegrity)
				return
			}
			require.NoError(t, err)
		})
	}
}
