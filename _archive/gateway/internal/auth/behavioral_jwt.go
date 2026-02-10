package auth

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/base64"
	"encoding/json"
	"errors"
	"os"
	"strings"
	"time"

	"github.com/gofiber/fiber/v2"
)

// BehavioralClaims extends standard JWT with behavior hash
type BehavioralClaims struct {
	UserID        string  `json:"sub"`
	BehaviorHash  string  `json:"bh"`              // Hash of behavioral profile
	IssuedAt      int64   `json:"iat"`
	ExpiresAt     int64   `json:"exp"`
	AvgInterval   float64 `json:"avg_interval"`    // Avg seconds between requests
	AvgPromptLen  int     `json:"avg_prompt_len"`  // Avg prompt length
	TopicHash     string  `json:"topic_hash"`      // Hash of topic distribution
}

// BehavioralJWTConfig holds configuration
type BehavioralJWTConfig struct {
	Secret             string
	ExpirationHours    int
	BehaviorThreshold  float64 // Max allowed drift from profile
}

// DefaultConfig returns default configuration
func DefaultConfig() BehavioralJWTConfig {
	secret := os.Getenv("JWT_SECRET")
	if secret == "" {
		secret = "sentinel-dev-secret-change-in-production"
	}
	
	return BehavioralJWTConfig{
		Secret:            secret,
		ExpirationHours:   24,
		BehaviorThreshold: 0.3, // 30% drift allowed
	}
}

// GenerateToken creates a behavioral JWT
func GenerateToken(userID string, profile BehaviorProfile, config BehavioralJWTConfig) (string, error) {
	now := time.Now().Unix()
	
	claims := BehavioralClaims{
		UserID:       userID,
		BehaviorHash: computeBehaviorHash(profile),
		IssuedAt:     now,
		ExpiresAt:    now + int64(config.ExpirationHours*3600),
		AvgInterval:  profile.AvgInterval,
		AvgPromptLen: profile.AvgPromptLen,
		TopicHash:    profile.TopicHash,
	}
	
	// Header
	header := map[string]string{
		"alg": "HS256",
		"typ": "JWT",
	}
	headerJSON, _ := json.Marshal(header)
	headerB64 := base64.RawURLEncoding.EncodeToString(headerJSON)
	
	// Payload
	payloadJSON, _ := json.Marshal(claims)
	payloadB64 := base64.RawURLEncoding.EncodeToString(payloadJSON)
	
	// Signature
	signInput := headerB64 + "." + payloadB64
	mac := hmac.New(sha256.New, []byte(config.Secret))
	mac.Write([]byte(signInput))
	signature := base64.RawURLEncoding.EncodeToString(mac.Sum(nil))
	
	return signInput + "." + signature, nil
}

// ValidateToken validates JWT and checks behavior drift
func ValidateToken(tokenString string, currentProfile BehaviorProfile, config BehavioralJWTConfig) (*BehavioralClaims, error) {
	parts := strings.Split(tokenString, ".")
	if len(parts) != 3 {
		return nil, errors.New("invalid token format")
	}
	
	// Verify signature
	signInput := parts[0] + "." + parts[1]
	mac := hmac.New(sha256.New, []byte(config.Secret))
	mac.Write([]byte(signInput))
	expectedSig := base64.RawURLEncoding.EncodeToString(mac.Sum(nil))
	
	if !hmac.Equal([]byte(parts[2]), []byte(expectedSig)) {
		return nil, errors.New("invalid signature")
	}
	
	// Decode claims
	payloadJSON, err := base64.RawURLEncoding.DecodeString(parts[1])
	if err != nil {
		return nil, errors.New("invalid payload encoding")
	}
	
	var claims BehavioralClaims
	if err := json.Unmarshal(payloadJSON, &claims); err != nil {
		return nil, errors.New("invalid payload format")
	}
	
	// Check expiration
	if time.Now().Unix() > claims.ExpiresAt {
		return nil, errors.New("token expired")
	}
	
	// Check behavior drift
	currentHash := computeBehaviorHash(currentProfile)
	drift := computeDrift(claims, currentProfile)
	
	if drift > config.BehaviorThreshold {
		return nil, errors.New("behavior drift exceeded threshold")
	}
	
	// Additional check: hash mismatch with high confidence
	if currentHash != claims.BehaviorHash && drift > config.BehaviorThreshold/2 {
		return nil, errors.New("behavioral profile changed significantly")
	}
	
	return &claims, nil
}

// BehaviorProfile represents user's behavioral signature
type BehaviorProfile struct {
	AvgInterval  float64 // Avg seconds between requests
	AvgPromptLen int     // Avg prompt length
	TopicHash    string  // Hash of typical topics
	RequestCount int     // Total requests in window
}

// computeBehaviorHash creates a hash of behavioral features
func computeBehaviorHash(profile BehaviorProfile) string {
	data := []byte(strings.Join([]string{
		string(rune(int(profile.AvgInterval * 10))),      // Quantize interval
		string(rune(profile.AvgPromptLen / 10)),          // Quantize prompt len
		profile.TopicHash,
	}, ":"))
	
	hash := sha256.Sum256(data)
	return base64.RawURLEncoding.EncodeToString(hash[:8]) // Truncated hash
}

// computeDrift calculates behavioral drift between token and current
func computeDrift(claims BehavioralClaims, current BehaviorProfile) float64 {
	// Normalize features to [0,1] range
	intervalDrift := abs(claims.AvgInterval-current.AvgInterval) / max(claims.AvgInterval, 1)
	lengthDrift := abs(float64(claims.AvgPromptLen-current.AvgPromptLen)) / max(float64(claims.AvgPromptLen), 1)
	
	// Topic drift: 0 if same, 1 if different
	var topicDrift float64 = 0
	if claims.TopicHash != current.TopicHash {
		topicDrift = 0.5 // Partial weight for topic change
	}
	
	// Weighted average
	return (intervalDrift*0.3 + lengthDrift*0.3 + topicDrift*0.4)
}

func abs(x float64) float64 {
	if x < 0 {
		return -x
	}
	return x
}

func max(a, b float64) float64 {
	if a > b {
		return a
	}
	return b
}

// Middleware returns Fiber middleware for behavioral JWT auth
func Middleware(config BehavioralJWTConfig) fiber.Handler {
	return func(c *fiber.Ctx) error {
		// Skip auth for health check
		if c.Path() == "/health" {
			return c.Next()
		}
		
		// Get token from header
		authHeader := c.Get("Authorization")
		if authHeader == "" {
			return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
				"error": "Missing Authorization header",
			})
		}
		
		// Extract Bearer token
		tokenString := strings.TrimPrefix(authHeader, "Bearer ")
		if tokenString == authHeader {
			return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
				"error": "Invalid Authorization format",
			})
		}
		
		// Get current behavior profile from request context
		// This would be populated by Brain's behavioral analysis
		currentProfile := extractCurrentProfile(c)
		
		// Validate token
		claims, err := ValidateToken(tokenString, currentProfile, config)
		if err != nil {
			return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
				"error":  "Token validation failed",
				"reason": err.Error(),
			})
		}
		
		// Store claims in context for downstream handlers
		c.Locals("user_id", claims.UserID)
		c.Locals("claims", claims)
		
		return c.Next()
	}
}

// extractCurrentProfile extracts behavioral features from current request
func extractCurrentProfile(c *fiber.Ctx) BehaviorProfile {
	body := c.Body()
	promptLen := len(body)
	
	// Get user ID from header or use IP
	userID := c.Get("X-User-ID")
	if userID == "" {
		userID = c.IP()
	}
	
	// Try to get stored profile from Redis (if available)
	// The profile key format is: "sentinel:profile:{userID}"
	// This is populated by Brain's behavioral analysis
	storedProfile := getStoredProfile(userID)
	if storedProfile != nil {
		// Update with current request length
		storedProfile.AvgPromptLen = (storedProfile.AvgPromptLen + promptLen) / 2
		storedProfile.RequestCount++
		return *storedProfile
	}
	
	// Fallback: return profile based on current request
	return BehaviorProfile{
		AvgInterval:  5.0,       // Default: 5 seconds between requests
		AvgPromptLen: promptLen,
		TopicHash:    "",        // Would come from Brain semantic analysis
		RequestCount: 1,
	}
}

// getStoredProfile attempts to retrieve behavioral profile
// In production, this queries Redis; here we provide a stub that can be extended
func getStoredProfile(userID string) *BehaviorProfile {
	// Redis integration point
	// redisAddr := os.Getenv("REDIS_URL")
	// if redisAddr == "" {
	//     return nil
	// }
	// client := redis.NewClient(...)
	// data := client.Get(ctx, "sentinel:profile:" + userID)
	// ...
	
	// For now, return nil to use fallback
	// This will be populated when Brain writes profiles to Redis
	_ = userID // avoid unused warning
	return nil
}
