package auth

import (
	"os"

	"github.com/gofiber/fiber/v2"
)

// LoginRequest represents login credentials
type LoginRequest struct {
	UserID   string `json:"user_id"`
	Password string `json:"password"`
}

// LoginResponse contains the behavioral JWT
type LoginResponse struct {
	Token     string `json:"token"`
	ExpiresIn int    `json:"expires_in"`
	TokenType string `json:"token_type"`
}

// LoginHandler handles user authentication and issues behavioral JWT
func LoginHandler(config BehavioralJWTConfig) fiber.Handler {
	return func(c *fiber.Ctx) error {
		var req LoginRequest
		if err := c.BodyParser(&req); err != nil {
			return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
				"error": "Invalid request body",
			})
		}

		// Validate credentials
		// In production: check against database/LDAP/etc
		if !validateCredentials(req.UserID, req.Password) {
			return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
				"error": "Invalid credentials",
			})
		}

		// Get initial behavioral profile (new user = default profile)
		profile := getInitialProfile(req.UserID)

		// Generate behavioral JWT
		token, err := GenerateToken(req.UserID, profile, config)
		if err != nil {
			return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
				"error": "Failed to generate token",
			})
		}

		return c.JSON(LoginResponse{
			Token:     token,
			ExpiresIn: config.ExpirationHours * 3600,
			TokenType: "Bearer",
		})
	}
}

// validateCredentials checks user credentials
func validateCredentials(userID, password string) bool {
	// Demo mode: check against env variables
	demoUser := os.Getenv("DEMO_USER")
	demoPass := os.Getenv("DEMO_PASS")

	if demoUser == "" {
		demoUser = "admin"
	}
	if demoPass == "" {
		demoPass = "sentinel"
	}

	// In production: proper password hashing and DB lookup
	return userID == demoUser && password == demoPass
}

// getInitialProfile returns default behavioral profile for new session
func getInitialProfile(userID string) BehaviorProfile {
	// In production: query Redis for existing profile
	// redis.Get("profile:" + userID)

	return BehaviorProfile{
		AvgInterval:  5.0,   // 5 seconds between requests
		AvgPromptLen: 100,   // 100 chars average
		TopicHash:    "",    // No topic history yet
		RequestCount: 0,
	}
}

// RefreshHandler refreshes token with updated behavioral profile
func RefreshHandler(config BehavioralJWTConfig) fiber.Handler {
	return func(c *fiber.Ctx) error {
		// Get current claims from context (set by middleware)
		claims, ok := c.Locals("claims").(*BehavioralClaims)
		if !ok {
			return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
				"error": "No valid token in context",
			})
		}

		// Get updated profile from behavioral analysis
		currentProfile := extractCurrentProfile(c)

		// Generate new token with updated profile
		token, err := GenerateToken(claims.UserID, currentProfile, config)
		if err != nil {
			return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
				"error": "Failed to refresh token",
			})
		}

		return c.JSON(LoginResponse{
			Token:     token,
			ExpiresIn: config.ExpirationHours * 3600,
			TokenType: "Bearer",
		})
	}
}
