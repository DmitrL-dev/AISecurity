package tools

import (
	"context"
	"fmt"

	"github.com/syntrex/gomcp/internal/domain/memory"
	rlmscope "github.com/syntrex/gomcp/internal/domain/scope"
)

func (s *FactService) sessionTurnClaimStore(
	ctx context.Context,
	sessionID string,
) (memory.SessionTurnClaimStore, error) {
	if _, err := rlmscope.RequireSessionScope(ctx, sessionID); err != nil {
		return nil, err
	}
	store, ok := s.store.(memory.SessionTurnClaimStore)
	if !ok {
		return nil, fmt.Errorf("session turn claims are unavailable: fact store does not support durable dispatch claims")
	}
	return store, nil
}

func validateSessionTurnClaim(
	claim *memory.SessionTurnClaim,
	turnID, requestRef string,
) error {
	if claim == nil || claim.Version != 1 || claim.TurnID != turnID ||
		claim.RequestRef != requestRef ||
		!claim.State.IsValid() || claim.Generation < 1 {
		return memory.ErrSessionTurnClaimIntegrity
	}
	switch claim.State {
	case memory.SessionTurnClaimed:
		if claim.LeaseUntilUnix <= 0 || claim.ExecutionStartedUnix != 0 ||
			claim.UncertaintyDeadlineUnix != 0 || claim.CompletedFactID != "" {
			return memory.ErrSessionTurnClaimIntegrity
		}
	case memory.SessionTurnExecuting:
		if claim.LeaseUntilUnix != 0 || claim.ExecutionStartedUnix <= 0 ||
			claim.UncertaintyDeadlineUnix < claim.ExecutionStartedUnix ||
			claim.CompletedFactID != "" {
			return memory.ErrSessionTurnClaimIntegrity
		}
	case memory.SessionTurnUncertain:
		if claim.Owned || claim.LeaseUntilUnix != 0 || claim.ExecutionStartedUnix <= 0 ||
			claim.UncertaintyDeadlineUnix < claim.ExecutionStartedUnix ||
			claim.CompletedFactID != "" {
			return memory.ErrSessionTurnClaimIntegrity
		}
	case memory.SessionTurnCompleted:
		validExecutionPair := (claim.ExecutionStartedUnix == 0 && claim.UncertaintyDeadlineUnix == 0) ||
			(claim.ExecutionStartedUnix > 0 && claim.UncertaintyDeadlineUnix >= claim.ExecutionStartedUnix)
		if claim.Owned || claim.LeaseUntilUnix != 0 || !validExecutionPair ||
			memory.ValidateSessionTurnCompletedFactID(claim.CompletedFactID) != nil {
			return memory.ErrSessionTurnClaimIntegrity
		}
	}
	return nil
}

func (s *FactService) AcquireSessionTurnClaim(
	ctx context.Context,
	sessionID, turnID, requestRef, ownerToken string,
) (*memory.SessionTurnClaim, error) {
	store, err := s.sessionTurnClaimStore(ctx, sessionID)
	if err != nil {
		return nil, err
	}
	if err := rlmscope.ValidateTurnID(turnID); err != nil {
		return nil, err
	}
	if err := memory.ValidateSessionTurnRequestRef(requestRef); err != nil {
		return nil, err
	}
	if err := memory.ValidateSessionTurnClaimToken(ownerToken); err != nil {
		return nil, err
	}
	claim, err := store.AcquireSessionTurnClaim(ctx, sessionID, turnID, requestRef, ownerToken)
	if err != nil {
		return nil, fmt.Errorf("acquire session turn claim: %w", err)
	}
	if err := validateSessionTurnClaim(claim, turnID, requestRef); err != nil {
		return nil, err
	}
	return claim, nil
}

func (s *FactService) BeginSessionTurnExecution(
	ctx context.Context,
	sessionID, turnID, requestRef, ownerToken string,
) (*memory.SessionTurnClaim, error) {
	store, err := s.sessionTurnClaimStore(ctx, sessionID)
	if err != nil {
		return nil, err
	}
	if err := rlmscope.ValidateTurnID(turnID); err != nil {
		return nil, err
	}
	if err := memory.ValidateSessionTurnRequestRef(requestRef); err != nil {
		return nil, err
	}
	if err := memory.ValidateSessionTurnClaimToken(ownerToken); err != nil {
		return nil, err
	}
	claim, err := store.BeginSessionTurnExecution(ctx, sessionID, turnID, requestRef, ownerToken)
	if err != nil {
		return nil, fmt.Errorf("begin session turn execution: %w", err)
	}
	if err := validateSessionTurnClaim(claim, turnID, requestRef); err != nil {
		return nil, err
	}
	return claim, nil
}
