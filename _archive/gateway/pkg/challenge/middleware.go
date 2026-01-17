// Package challenge provides HTTP middleware for PoW challenges
package challenge

import (
	"encoding/json"
	"net/http"
	"strings"
	"sync"
	"time"
)

// Action defines what to do with a request
type Action string

const (
	ActionAllow     Action = "ALLOW"
	ActionDeny      Action = "DENY"
	ActionChallenge Action = "CHALLENGE"
)

// Rule defines a matching rule for requests
type Rule struct {
	Name            string   `yaml:"name"`
	UserAgentRegex  string   `yaml:"user_agent_regex,omitempty"`
	RemoteAddresses []string `yaml:"remote_addresses,omitempty"`
	PathPrefix      string   `yaml:"path_prefix,omitempty"`
	Action          Action   `yaml:"action"`
	Difficulty      int      `yaml:"difficulty,omitempty"`
}

// TokenStore manages verified client tokens
type TokenStore struct {
	tokens sync.Map // map[token]expiry
	ttl    time.Duration
}

// NewTokenStore creates a token store with specified TTL
func NewTokenStore(ttl time.Duration) *TokenStore {
	if ttl == 0 {
		ttl = 1 * time.Hour
	}
	ts := &TokenStore{ttl: ttl}
	go ts.cleanup()
	return ts
}

// Add stores a verified token
func (ts *TokenStore) Add(token string) {
	ts.tokens.Store(token, time.Now().Add(ts.ttl))
}

// IsValid checks if a token is valid
func (ts *TokenStore) IsValid(token string) bool {
	val, ok := ts.tokens.Load(token)
	if !ok {
		return false
	}
	expiry := val.(time.Time)
	if time.Now().After(expiry) {
		ts.tokens.Delete(token)
		return false
	}
	return true
}

// cleanup removes expired tokens
func (ts *TokenStore) cleanup() {
	ticker := time.NewTicker(5 * time.Minute)
	defer ticker.Stop()
	
	for range ticker.C {
		now := time.Now()
		ts.tokens.Range(func(key, value interface{}) bool {
			if now.After(value.(time.Time)) {
				ts.tokens.Delete(key)
			}
			return true
		})
	}
}

// Middleware provides HTTP middleware for PoW challenges
type Middleware struct {
	engine     *Engine
	tokenStore *TokenStore
	rules      []Rule
}

// MiddlewareConfig configures the challenge middleware
type MiddlewareConfig struct {
	Engine     *Engine
	TokenStore *TokenStore
	Rules      []Rule
}

// NewMiddleware creates a new challenge middleware
func NewMiddleware(config MiddlewareConfig) *Middleware {
	if config.Engine == nil {
		config.Engine = NewEngine(DefaultConfig())
	}
	if config.TokenStore == nil {
		config.TokenStore = NewTokenStore(1 * time.Hour)
	}
	
	return &Middleware{
		engine:     config.Engine,
		tokenStore: config.TokenStore,
		rules:      config.Rules,
	}
}

// Handler wraps an HTTP handler with PoW challenge protection
func (m *Middleware) Handler(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Check for existing valid token
		token := r.Header.Get("X-Challenge-Token")
		if token != "" && m.tokenStore.IsValid(token) {
			// Client has valid token, pass through
			w.Header().Set("X-Anubis-Status", "PASS")
			next.ServeHTTP(w, r)
			return
		}
		
		// Check if client is submitting a solution
		if r.Method == http.MethodPost && r.URL.Path == "/.sentinel/challenge/verify" {
			m.handleVerify(w, r)
			return
		}
		
		// Check if client needs a challenge
		if r.URL.Path == "/.sentinel/challenge/new" {
			m.handleNewChallenge(w, r)
			return
		}
		
		// Evaluate rules
		action := m.evaluateRules(r)
		
		switch action {
		case ActionAllow:
			w.Header().Set("X-Anubis-Status", "PASS")
			w.Header().Set("X-Anubis-Action", string(ActionAllow))
			next.ServeHTTP(w, r)
			
		case ActionDeny:
			w.Header().Set("X-Anubis-Status", "DENIED")
			w.Header().Set("X-Anubis-Action", string(ActionDeny))
			http.Error(w, "Access denied", http.StatusForbidden)
			
		case ActionChallenge:
			w.Header().Set("X-Anubis-Status", "CHALLENGE")
			w.Header().Set("X-Anubis-Action", string(ActionChallenge))
			m.sendChallengeRequired(w, r)
		}
	})
}

// evaluateRules determines the action for a request
func (m *Middleware) evaluateRules(r *http.Request) Action {
	userAgent := r.UserAgent()
	
	for _, rule := range m.rules {
		// Check user agent
		if rule.UserAgentRegex != "" {
			if strings.Contains(strings.ToLower(userAgent), strings.ToLower(rule.UserAgentRegex)) {
				return rule.Action
			}
		}
		
		// Check path prefix
		if rule.PathPrefix != "" {
			if strings.HasPrefix(r.URL.Path, rule.PathPrefix) {
				return rule.Action
			}
		}
	}
	
	// Default: allow
	return ActionAllow
}

// handleNewChallenge creates and returns a new challenge
func (m *Middleware) handleNewChallenge(w http.ResponseWriter, r *http.Request) {
	clientID := r.RemoteAddr
	difficulty := m.getDifficultyForRequest(r)
	
	challenge := m.engine.GenerateChallenge(clientID, difficulty)
	
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"challenge_id": challenge.ID,
		"nonce":        challenge.Nonce,
		"difficulty":   challenge.Difficulty,
		"algorithm":    challenge.Algorithm,
		"expires_at":   challenge.ExpiresAt.Unix(),
		"instructions": "Find an answer such that SHA256(nonce + answer) starts with N zeros, where N = difficulty",
	})
}

// handleVerify verifies a solution and issues a token
func (m *Middleware) handleVerify(w http.ResponseWriter, r *http.Request) {
	var solution Solution
	if err := json.NewDecoder(r.Body).Decode(&solution); err != nil {
		http.Error(w, "invalid request body", http.StatusBadRequest)
		return
	}
	
	result := m.engine.VerifySolution(&solution)
	
	response := map[string]interface{}{
		"valid":      result.Valid,
		"message":    result.Message,
		"duration_ms": result.Duration.Milliseconds(),
	}
	
	if result.Valid {
		// Issue a token
		token := generateChallengeID() // Reuse ID generator for tokens
		m.tokenStore.Add(token)
		response["token"] = token
		response["token_ttl_seconds"] = int(m.tokenStore.ttl.Seconds())
	}
	
	w.Header().Set("Content-Type", "application/json")
	if !result.Valid {
		w.WriteHeader(http.StatusUnauthorized)
	}
	json.NewEncoder(w).Encode(response)
}

// sendChallengeRequired tells client they need to complete a challenge
func (m *Middleware) sendChallengeRequired(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusUnauthorized)
	
	json.NewEncoder(w).Encode(map[string]interface{}{
		"error":         "challenge_required",
		"message":       "Proof of work challenge required",
		"challenge_url": "/.sentinel/challenge/new",
		"verify_url":    "/.sentinel/challenge/verify",
	})
}

// getDifficultyForRequest determines difficulty based on request suspicious signals
func (m *Middleware) getDifficultyForRequest(r *http.Request) int {
	difficulty := 4 // Base difficulty
	
	// Increase difficulty for suspicious patterns
	userAgent := strings.ToLower(r.UserAgent())
	
	// Known bot patterns get higher difficulty
	if strings.Contains(userAgent, "bot") ||
		strings.Contains(userAgent, "crawler") ||
		strings.Contains(userAgent, "spider") {
		difficulty += 4
	}
	
	// Empty user agent
	if userAgent == "" {
		difficulty += 2
	}
	
	// Cap at 16
	if difficulty > 16 {
		difficulty = 16
	}
	
	return difficulty
}

// Stats returns middleware statistics
func (m *Middleware) Stats() map[string]interface{} {
	engineStats := m.engine.Stats()
	
	tokenCount := 0
	m.tokenStore.tokens.Range(func(_, _ interface{}) bool {
		tokenCount++
		return true
	})
	
	engineStats["active_tokens"] = tokenCount
	engineStats["rules_count"] = len(m.rules)
	
	return engineStats
}
