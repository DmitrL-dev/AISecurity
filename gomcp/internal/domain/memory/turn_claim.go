package memory

import (
	"context"
	"errors"
	"fmt"
	"strings"
)

const (
	SessionTurnRequestRefPrefix        = "session-turn-request-v1:sha256:"
	SessionTurnClaimTokenPrefix        = "claim_"
	SessionTurnCompletedFactIDMaxBytes = 256
)

// SessionTurnClaimState is the durable provider-dispatch state for one scoped
// chat turn. CLAIMED may be taken over after its lease; every later state is
// deliberately non-stealable.
type SessionTurnClaimState string

const (
	SessionTurnClaimed   SessionTurnClaimState = "CLAIMED"
	SessionTurnExecuting SessionTurnClaimState = "EXECUTING"
	SessionTurnCompleted SessionTurnClaimState = "COMPLETED"
	SessionTurnUncertain SessionTurnClaimState = "UNCERTAIN"
)

func (state SessionTurnClaimState) IsValid() bool {
	switch state {
	case SessionTurnClaimed, SessionTurnExecuting, SessionTurnCompleted, SessionTurnUncertain:
		return true
	default:
		return false
	}
}

// SessionTurnClaim is the content-free acknowledgement returned to the
// gateway. Owned is computed for the caller's token and is never persisted;
// another claimant's token is not exposed on the wire.
type SessionTurnClaim struct {
	Version                 int                   `json:"version"`
	TurnID                  string                `json:"turn_id"`
	RequestRef              string                `json:"request_ref"`
	State                   SessionTurnClaimState `json:"state"`
	Owned                   bool                  `json:"owned"`
	Generation              int64                 `json:"generation"`
	LeaseUntilUnix          int64                 `json:"lease_until_unix,omitempty"`
	ExecutionStartedUnix    int64                 `json:"execution_started_unix,omitempty"`
	UncertaintyDeadlineUnix int64                 `json:"uncertainty_deadline_unix,omitempty"`
	CompletedFactID         string                `json:"completed_fact_id,omitempty"`
}

// SessionTurnClaimStore is additive to SessionFactStore so legacy memory
// callers keep their contract. Implementations must serialize these operations
// across processes and must reconcile a valid receipt as COMPLETED before
// permitting a new provider execution.
type SessionTurnClaimStore interface {
	AcquireSessionTurnClaim(
		ctx context.Context,
		sessionID, turnID, requestRef, ownerToken string,
	) (*SessionTurnClaim, error)
	BeginSessionTurnExecution(
		ctx context.Context,
		sessionID, turnID, requestRef, ownerToken string,
	) (*SessionTurnClaim, error)
}

var (
	ErrSessionTurnClaimIntegrity = errors.New("session turn claim integrity violation")
	ErrSessionTurnClaimNotFound  = errors.New("session turn claim not found")
)

func ValidateSessionTurnRequestRef(requestRef string) error {
	if !validPrefixedLowerHex(requestRef, SessionTurnRequestRefPrefix, 64) {
		return fmt.Errorf("request_ref must be %s followed by 64 lowercase hex characters", SessionTurnRequestRefPrefix)
	}
	return nil
}

func ValidateSessionTurnClaimToken(ownerToken string) error {
	if !validPrefixedLowerHex(ownerToken, SessionTurnClaimTokenPrefix, 64) {
		return fmt.Errorf("owner_token must be claim_ followed by 64 lowercase hex characters")
	}
	return nil
}

// ValidateSessionTurnCompletedFactID keeps the durable claim acknowledgement
// within the same byte bound as exact fact and cursor identities. The error is
// value-free so a corrupt stored identifier is never reflected to callers.
func ValidateSessionTurnCompletedFactID(factID string) error {
	if factID == "" || len(factID) > SessionTurnCompletedFactIDMaxBytes {
		return fmt.Errorf("completed_fact_id must contain 1 through 256 bytes")
	}
	return nil
}

func validPrefixedLowerHex(value, prefix string, hexLength int) bool {
	if len(value) != len(prefix)+hexLength || !strings.HasPrefix(value, prefix) {
		return false
	}
	for index := len(prefix); index < len(value); index++ {
		char := value[index]
		if !((char >= '0' && char <= '9') || (char >= 'a' && char <= 'f')) {
			return false
		}
	}
	return true
}
