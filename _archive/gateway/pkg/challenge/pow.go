// Package challenge provides Proof-of-Work challenge mechanisms
// to protect the Gateway from abuse and AI crawlers.
// Based on concepts from Anubis (github.com/TecharoHQ/anubis)
package challenge

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"math/rand"
	"strings"
	"sync"
	"time"
)

// Challenge represents a PoW challenge for a client
type Challenge struct {
	ID         string    `json:"id"`
	Nonce      string    `json:"nonce"`
	Difficulty int       `json:"difficulty"`
	Algorithm  string    `json:"algorithm"`
	CreatedAt  time.Time `json:"created_at"`
	ExpiresAt  time.Time `json:"expires_at"`
}

// Solution represents a client's solution to a challenge
type Solution struct {
	ChallengeID string `json:"challenge_id"`
	Nonce       string `json:"nonce"`
	Answer      string `json:"answer"`
}

// VerifyResult contains the result of challenge verification
type VerifyResult struct {
	Valid    bool   `json:"valid"`
	Message  string `json:"message"`
	Duration time.Duration
}

// Config for the PoW engine
type Config struct {
	// DefaultDifficulty is the number of leading zeros required (1-16)
	DefaultDifficulty int `yaml:"default_difficulty"`
	// ChallengeTTL is how long a challenge remains valid
	ChallengeTTL time.Duration `yaml:"challenge_ttl"`
	// Algorithm: "fast" (SHA256) or "slow" (intentionally wasteful)
	Algorithm string `yaml:"algorithm"`
	// MaxPendingChallenges per IP
	MaxPendingChallenges int `yaml:"max_pending_challenges"`
}

// DefaultConfig returns sensible defaults
func DefaultConfig() Config {
	return Config{
		DefaultDifficulty:    4,
		ChallengeTTL:         5 * time.Minute,
		Algorithm:            "fast",
		MaxPendingChallenges: 10,
	}
}

// Engine manages PoW challenges
type Engine struct {
	config     Config
	challenges sync.Map // map[string]*Challenge
	mu         sync.RWMutex
}

// NewEngine creates a new PoW challenge engine
func NewEngine(config Config) *Engine {
	if config.DefaultDifficulty < 1 {
		config.DefaultDifficulty = 4
	}
	if config.DefaultDifficulty > 16 {
		config.DefaultDifficulty = 16
	}
	if config.ChallengeTTL == 0 {
		config.ChallengeTTL = 5 * time.Minute
	}
	
	e := &Engine{
		config: config,
	}
	
	// Start cleanup goroutine
	go e.cleanupExpired()
	
	return e
}

// GenerateChallenge creates a new challenge for a client
func (e *Engine) GenerateChallenge(clientID string, difficulty int) *Challenge {
	if difficulty <= 0 {
		difficulty = e.config.DefaultDifficulty
	}
	if difficulty > 16 {
		difficulty = 16
	}
	
	now := time.Now()
	challenge := &Challenge{
		ID:         generateChallengeID(),
		Nonce:      generateNonce(),
		Difficulty: difficulty,
		Algorithm:  e.config.Algorithm,
		CreatedAt:  now,
		ExpiresAt:  now.Add(e.config.ChallengeTTL),
	}
	
	e.challenges.Store(challenge.ID, challenge)
	
	return challenge
}

// VerifySolution checks if a solution is valid
func (e *Engine) VerifySolution(solution *Solution) *VerifyResult {
	start := time.Now()
	
	// Retrieve challenge
	val, ok := e.challenges.Load(solution.ChallengeID)
	if !ok {
		return &VerifyResult{
			Valid:    false,
			Message:  "challenge not found or expired",
			Duration: time.Since(start),
		}
	}
	
	challenge := val.(*Challenge)
	
	// Check expiration
	if time.Now().After(challenge.ExpiresAt) {
		e.challenges.Delete(solution.ChallengeID)
		return &VerifyResult{
			Valid:    false,
			Message:  "challenge expired",
			Duration: time.Since(start),
		}
	}
	
	// Verify the PoW
	valid := verifyPoW(challenge.Nonce, solution.Answer, challenge.Difficulty)
	
	if valid {
		// Remove used challenge (one-time use)
		e.challenges.Delete(solution.ChallengeID)
	}
	
	return &VerifyResult{
		Valid:    valid,
		Message:  getMessage(valid),
		Duration: time.Since(start),
	}
}

// GetChallenge retrieves a challenge by ID
func (e *Engine) GetChallenge(id string) (*Challenge, bool) {
	val, ok := e.challenges.Load(id)
	if !ok {
		return nil, false
	}
	return val.(*Challenge), true
}

// Stats returns current engine statistics
func (e *Engine) Stats() map[string]interface{} {
	count := 0
	e.challenges.Range(func(_, _ interface{}) bool {
		count++
		return true
	})
	
	return map[string]interface{}{
		"pending_challenges":   count,
		"default_difficulty":   e.config.DefaultDifficulty,
		"algorithm":            e.config.Algorithm,
		"challenge_ttl_seconds": e.config.ChallengeTTL.Seconds(),
	}
}

// cleanupExpired removes expired challenges periodically
func (e *Engine) cleanupExpired() {
	ticker := time.NewTicker(1 * time.Minute)
	defer ticker.Stop()
	
	for range ticker.C {
		now := time.Now()
		e.challenges.Range(func(key, value interface{}) bool {
			challenge := value.(*Challenge)
			if now.After(challenge.ExpiresAt) {
				e.challenges.Delete(key)
			}
			return true
		})
	}
}

// verifyPoW checks if the answer produces a hash with required leading zeros
func verifyPoW(nonce, answer string, difficulty int) bool {
	// Concatenate nonce and answer
	data := nonce + answer
	
	// Compute SHA256 hash
	hash := sha256.Sum256([]byte(data))
	hashHex := hex.EncodeToString(hash[:])
	
	// Check for required number of leading zeros
	prefix := strings.Repeat("0", difficulty)
	return strings.HasPrefix(hashHex, prefix)
}

// generateChallengeID creates a unique challenge identifier
func generateChallengeID() string {
	return fmt.Sprintf("pow_%d_%s", time.Now().UnixNano(), randomHex(8))
}

// generateNonce creates a random nonce for the challenge
func generateNonce() string {
	return randomHex(32)
}

// randomHex generates a random hex string of specified length
func randomHex(length int) string {
	bytes := make([]byte, length/2+1)
	rand.Read(bytes)
	return hex.EncodeToString(bytes)[:length]
}

// getMessage returns a human-readable message
func getMessage(valid bool) string {
	if valid {
		return "proof of work verified successfully"
	}
	return "invalid proof of work"
}

// SolveChallenge solves a PoW challenge (for testing/client use)
// Returns the answer and number of iterations
func SolveChallenge(nonce string, difficulty int) (string, int) {
	iterations := 0
	for {
		iterations++
		answer := fmt.Sprintf("%d", iterations)
		
		data := nonce + answer
		hash := sha256.Sum256([]byte(data))
		hashHex := hex.EncodeToString(hash[:])
		
		prefix := strings.Repeat("0", difficulty)
		if strings.HasPrefix(hashHex, prefix) {
			return answer, iterations
		}
	}
}
