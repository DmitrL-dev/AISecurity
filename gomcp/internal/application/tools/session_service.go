package tools

import (
	"context"
	"fmt"

	"github.com/syntrex/gomcp/internal/domain/session"
)

// SessionService implements MCP tool logic for cognitive state operations.
type SessionService struct {
	store session.StateStore
}

// NewSessionService creates a new SessionService.
func NewSessionService(store session.StateStore) *SessionService {
	return &SessionService{store: store}
}

// SaveStateParams holds parameters for the save_state tool.
type SaveStateParams struct {
	SessionID string  `json:"session_id"`
	GoalDesc  string  `json:"goal_description,omitempty"`
	Progress  float64 `json:"progress,omitempty"`
}

// SaveState saves a cognitive state vector.
func (s *SessionService) SaveState(ctx context.Context, state *session.CognitiveStateVector) error {
	checksum := state.Checksum()
	return s.store.Save(ctx, state, checksum)
}

// LoadState loads the latest (or specific version) of a session state.
func (s *SessionService) LoadState(ctx context.Context, sessionID string, version *int) (*session.CognitiveStateVector, string, error) {
	return s.store.Load(ctx, sessionID, version)
}

// ListSessions returns all persisted sessions.
func (s *SessionService) ListSessions(ctx context.Context) ([]session.SessionInfo, error) {
	return s.store.ListSessions(ctx)
}

// DeleteSession removes all versions of a session.
func (s *SessionService) DeleteSession(ctx context.Context, sessionID string) (int, error) {
	return s.store.DeleteSession(ctx, sessionID)
}

// GetAuditLog returns the audit log for a session.
func (s *SessionService) GetAuditLog(ctx context.Context, sessionID string, limit int) ([]session.AuditEntry, error) {
	return s.store.GetAuditLog(ctx, sessionID, limit)
}

// RestoreOrCreate loads an existing session or creates a new one.
func (s *SessionService) RestoreOrCreate(ctx context.Context, sessionID string) (*session.CognitiveStateVector, bool, error) {
	state, _, err := s.store.Load(ctx, sessionID, nil)
	if err == nil {
		return state, true, nil // restored
	}
	// Create new session.
	newState := session.NewCognitiveStateVector(sessionID)
	if err := s.SaveState(ctx, newState); err != nil {
		return nil, false, fmt.Errorf("save new session: %w", err)
	}
	return newState, false, nil // created
}

// GetCompactState returns a compact text representation of the current state.
func (s *SessionService) GetCompactState(ctx context.Context, sessionID string, maxTokens int) (string, error) {
	state, _, err := s.store.Load(ctx, sessionID, nil)
	if err != nil {
		return "", err
	}
	return state.ToCompactString(maxTokens), nil
}
