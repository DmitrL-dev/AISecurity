package identity

import (
	"sync"
	"time"
)

// Store manages AgentIdentity CRUD operations.
// Thread-safe for concurrent access from multiple goroutines.
type Store struct {
	mu     sync.RWMutex
	agents map[string]*AgentIdentity // agent_id → identity
}

// NewStore creates a new in-memory identity store.
func NewStore() *Store {
	return &Store{
		agents: make(map[string]*AgentIdentity),
	}
}

// Register adds a new agent identity to the store.
// Returns ErrAgentExists if the agent_id is already registered.
func (s *Store) Register(agent *AgentIdentity) error {
	if err := agent.Validate(); err != nil {
		return err
	}

	s.mu.Lock()
	defer s.mu.Unlock()

	if _, exists := s.agents[agent.AgentID]; exists {
		return ErrAgentExists
	}

	if agent.CreatedAt.IsZero() {
		agent.CreatedAt = time.Now()
	}
	agent.LastSeenAt = time.Now()
	s.agents[agent.AgentID] = agent
	return nil
}

// Get retrieves an agent identity by ID.
// Returns ErrAgentNotFound if the agent doesn't exist.
func (s *Store) Get(agentID string) (*AgentIdentity, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	agent, ok := s.agents[agentID]
	if !ok {
		return nil, ErrAgentNotFound
	}
	return agent, nil
}

// UpdateLastSeen updates the last_seen_at timestamp for an agent.
func (s *Store) UpdateLastSeen(agentID string) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	agent, ok := s.agents[agentID]
	if !ok {
		return ErrAgentNotFound
	}
	agent.LastSeenAt = time.Now()
	return nil
}

// Remove removes an agent identity from the store.
func (s *Store) Remove(agentID string) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	if _, ok := s.agents[agentID]; !ok {
		return ErrAgentNotFound
	}
	delete(s.agents, agentID)
	return nil
}

// List returns all registered agent identities.
func (s *Store) List() []*AgentIdentity {
	s.mu.RLock()
	defer s.mu.RUnlock()

	result := make([]*AgentIdentity, 0, len(s.agents))
	for _, agent := range s.agents {
		result = append(result, agent)
	}
	return result
}

// Count returns the number of registered agents.
func (s *Store) Count() int {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return len(s.agents)
}
