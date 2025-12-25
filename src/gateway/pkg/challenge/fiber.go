// Package challenge provides Fiber middleware adapter for PoW challenges
package challenge

import (
	"encoding/json"
	"strings"
	"time"

	"github.com/gofiber/fiber/v2"
)

// FiberMiddleware adapts PoW challenge system for Fiber framework
type FiberMiddleware struct {
	engine     *Engine
	tokenStore *TokenStore
	config     FiberConfig
}

// FiberConfig configures the Fiber middleware
type FiberConfig struct {
	// Skip determines if the middleware should be skipped
	Skip func(c *fiber.Ctx) bool
	// Rules for evaluating requests
	Rules []Rule
	// Difficulty settings
	DefaultDifficulty int
	// Token TTL after solving challenge
	TokenTTL time.Duration
	// Challenge TTL
	ChallengeTTL time.Duration
	// Protected paths (regex patterns)
	ProtectedPaths []string
	// Exempt paths (always allowed)
	ExemptPaths []string
}

// DefaultFiberConfig returns sensible defaults
func DefaultFiberConfig() FiberConfig {
	return FiberConfig{
		DefaultDifficulty: 4,
		TokenTTL:          1 * time.Hour,
		ChallengeTTL:      5 * time.Minute,
		ProtectedPaths:    []string{"/v1/", "/api/"},
		ExemptPaths:       []string{"/health", "/metrics", "/.sentinel/challenge/"},
		Rules: []Rule{
			{Name: "googlebot", UserAgentRegex: "Googlebot", Action: ActionAllow},
			{Name: "generic-bot", UserAgentRegex: "(?i:bot|crawler|spider)", Action: ActionChallenge, Difficulty: 8},
			{Name: "ai-scrapers", UserAgentRegex: "(?i:openai|anthropic|claude)", Action: ActionChallenge, Difficulty: 12},
		},
	}
}

// NewFiberMiddleware creates a new Fiber-compatible PoW middleware
func NewFiberMiddleware(config ...FiberConfig) *FiberMiddleware {
	cfg := DefaultFiberConfig()
	if len(config) > 0 {
		cfg = config[0]
	}

	engine := NewEngine(Config{
		DefaultDifficulty: cfg.DefaultDifficulty,
		ChallengeTTL:      cfg.ChallengeTTL,
		Algorithm:         "fast",
	})

	return &FiberMiddleware{
		engine:     engine,
		tokenStore: NewTokenStore(cfg.TokenTTL),
		config:     cfg,
	}
}

// Handler returns a Fiber middleware handler
func (m *FiberMiddleware) Handler() fiber.Handler {
	return func(c *fiber.Ctx) error {
		// Check skip function
		if m.config.Skip != nil && m.config.Skip(c) {
			return c.Next()
		}

		path := c.Path()

		// Check exempt paths
		for _, exempt := range m.config.ExemptPaths {
			if strings.HasPrefix(path, exempt) {
				return c.Next()
			}
		}

		// Handle challenge endpoints
		if path == "/.sentinel/challenge/new" {
			return m.handleNewChallenge(c)
		}
		if path == "/.sentinel/challenge/verify" && c.Method() == fiber.MethodPost {
			return m.handleVerify(c)
		}

		// Check if path needs protection
		needsProtection := false
		for _, protected := range m.config.ProtectedPaths {
			if strings.HasPrefix(path, protected) {
				needsProtection = true
				break
			}
		}

		if !needsProtection {
			return c.Next()
		}

		// Check for existing valid token
		token := c.Get("X-Challenge-Token")
		if token != "" && m.tokenStore.IsValid(token) {
			c.Set("X-Anubis-Status", "PASS")
			return c.Next()
		}

		// Evaluate rules
		action := m.evaluateRules(c)

		switch action {
		case ActionAllow:
			c.Set("X-Anubis-Status", "PASS")
			c.Set("X-Anubis-Action", string(ActionAllow))
			return c.Next()

		case ActionDeny:
			c.Set("X-Anubis-Status", "DENIED")
			c.Set("X-Anubis-Action", string(ActionDeny))
			return c.Status(fiber.StatusForbidden).JSON(fiber.Map{
				"error":   "access_denied",
				"message": "Access denied by security policy",
			})

		case ActionChallenge:
			c.Set("X-Anubis-Status", "CHALLENGE")
			c.Set("X-Anubis-Action", string(ActionChallenge))
			return m.sendChallengeRequired(c)
		}

		return c.Next()
	}
}

// evaluateRules checks request against configured rules
func (m *FiberMiddleware) evaluateRules(c *fiber.Ctx) Action {
	userAgent := strings.ToLower(c.Get("User-Agent"))

	for _, rule := range m.config.Rules {
		if rule.UserAgentRegex != "" {
			pattern := strings.ToLower(rule.UserAgentRegex)
			if strings.Contains(userAgent, pattern) ||
				(strings.Contains(pattern, "bot") && strings.Contains(userAgent, "bot")) {
				return rule.Action
			}
		}
	}

	return ActionAllow
}

// handleNewChallenge creates a new PoW challenge
func (m *FiberMiddleware) handleNewChallenge(c *fiber.Ctx) error {
	clientID := c.IP()
	difficulty := m.getDifficultyForRequest(c)

	challenge := m.engine.GenerateChallenge(clientID, difficulty)

	return c.JSON(fiber.Map{
		"challenge_id": challenge.ID,
		"nonce":        challenge.Nonce,
		"difficulty":   challenge.Difficulty,
		"algorithm":    challenge.Algorithm,
		"expires_at":   challenge.ExpiresAt.Unix(),
		"instructions": "Find an answer such that SHA256(nonce + answer) starts with N zeros, where N = difficulty",
	})
}

// handleVerify verifies a PoW solution
func (m *FiberMiddleware) handleVerify(c *fiber.Ctx) error {
	var solution Solution
	if err := json.Unmarshal(c.Body(), &solution); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "invalid_request",
			"message": "Invalid request body",
		})
	}

	result := m.engine.VerifySolution(&solution)

	response := fiber.Map{
		"valid":       result.Valid,
		"message":     result.Message,
		"duration_ms": result.Duration.Milliseconds(),
	}

	if result.Valid {
		token := generateChallengeID()
		m.tokenStore.Add(token)
		response["token"] = token
		response["token_ttl_seconds"] = int(m.config.TokenTTL.Seconds())
	}

	if !result.Valid {
		return c.Status(fiber.StatusUnauthorized).JSON(response)
	}

	return c.JSON(response)
}

// sendChallengeRequired returns challenge required response
func (m *FiberMiddleware) sendChallengeRequired(c *fiber.Ctx) error {
	return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
		"error":         "challenge_required",
		"message":       "Proof of work challenge required",
		"challenge_url": "/.sentinel/challenge/new",
		"verify_url":    "/.sentinel/challenge/verify",
	})
}

// getDifficultyForRequest adjusts difficulty based on signals
func (m *FiberMiddleware) getDifficultyForRequest(c *fiber.Ctx) int {
	difficulty := m.config.DefaultDifficulty
	userAgent := strings.ToLower(c.Get("User-Agent"))

	// Increase for bot patterns
	if strings.Contains(userAgent, "bot") ||
		strings.Contains(userAgent, "crawler") ||
		strings.Contains(userAgent, "spider") {
		difficulty += 4
	}

	// Increase for AI-related patterns
	if strings.Contains(userAgent, "openai") ||
		strings.Contains(userAgent, "anthropic") ||
		strings.Contains(userAgent, "claude") {
		difficulty += 6
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
func (m *FiberMiddleware) Stats() fiber.Map {
	engineStats := m.engine.Stats()

	tokenCount := 0
	m.tokenStore.tokens.Range(func(_, _ interface{}) bool {
		tokenCount++
		return true
	})

	return fiber.Map{
		"pending_challenges":    engineStats["pending_challenges"],
		"default_difficulty":    engineStats["default_difficulty"],
		"algorithm":             engineStats["algorithm"],
		"challenge_ttl_seconds": engineStats["challenge_ttl_seconds"],
		"active_tokens":         tokenCount,
		"rules_count":           len(m.config.Rules),
	}
}
