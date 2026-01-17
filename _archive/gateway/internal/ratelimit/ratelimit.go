package ratelimit

import (
	"context"
	"fmt"
	"log"
	"os"
	"strconv"
	"time"

	"github.com/gofiber/fiber/v2"
	"github.com/redis/go-redis/v9"
)

// Config for rate limiter
type Config struct {
	// Max requests per window
	Max int
	// Window duration
	Window time.Duration
	// Key generator function (default: IP-based)
	KeyGenerator func(*fiber.Ctx) string
	// Redis client
	Redis *redis.Client
}

// DefaultConfig returns default rate limiter config
func DefaultConfig() Config {
	redisAddr := os.Getenv("REDIS_URL")
	if redisAddr == "" {
		redisAddr = "redis:6379"
	}
	
	// Parse redis URL (redis://host:port format)
	if len(redisAddr) > 8 && redisAddr[:8] == "redis://" {
		redisAddr = redisAddr[8:]
	}
	
	rdb := redis.NewClient(&redis.Options{
		Addr: redisAddr,
	})
	
	return Config{
		Max:    100, // 100 requests
		Window: time.Minute, // per minute
		KeyGenerator: func(c *fiber.Ctx) string {
			return c.IP()
		},
		Redis: rdb,
	}
}

// UserKeyGenerator creates a per-user key generator that uses JWT user_id
// Falls back to IP if no user is authenticated
func UserKeyGenerator(c *fiber.Ctx) string {
	// Try to get user from context (set by auth middleware)
	if user := c.Locals("user"); user != nil {
		return fmt.Sprintf("user:%v", user)
	}
	// Try to get from X-User-ID header (if set by gateway)
	if userID := c.Get("X-User-ID"); userID != "" {
		return fmt.Sprintf("user:%s", userID)
	}
	// Fallback to IP
	return fmt.Sprintf("ip:%s", c.IP())
}

// PerUserConfig returns config with per-user rate limiting
func PerUserConfig() Config {
	cfg := DefaultConfig()
	cfg.KeyGenerator = UserKeyGenerator
	cfg.Max = 60  // 60 requests per minute per user (stricter)
	return cfg
}


// New creates a rate limiter middleware
func New(config ...Config) fiber.Handler {
	cfg := DefaultConfig()
	if len(config) > 0 {
		cfg = config[0]
		if cfg.Redis == nil {
			cfg.Redis = DefaultConfig().Redis
		}
		if cfg.KeyGenerator == nil {
			cfg.KeyGenerator = DefaultConfig().KeyGenerator
		}
		if cfg.Max == 0 {
			cfg.Max = 100
		}
		if cfg.Window == 0 {
			cfg.Window = time.Minute
		}
	}

	return func(c *fiber.Ctx) error {
		key := fmt.Sprintf("ratelimit:%s", cfg.KeyGenerator(c))
		ctx := context.Background()

		// Increment counter
		count, err := cfg.Redis.Incr(ctx, key).Result()
		if err != nil {
			log.Printf("Rate limiter Redis error: %v", err)
			// Fail open - allow request if Redis fails
			return c.Next()
		}

		// Set expiry on first request
		if count == 1 {
			cfg.Redis.Expire(ctx, key, cfg.Window)
		}

		// Get TTL for headers
		ttl, _ := cfg.Redis.TTL(ctx, key).Result()

		// Set rate limit headers
		c.Set("X-RateLimit-Limit", strconv.Itoa(cfg.Max))
		c.Set("X-RateLimit-Remaining", strconv.Itoa(max(0, cfg.Max-int(count))))
		c.Set("X-RateLimit-Reset", strconv.FormatInt(time.Now().Add(ttl).Unix(), 10))

		// Check if limit exceeded
		if int(count) > cfg.Max {
			log.Printf("Rate limit exceeded for %s: %d/%d", cfg.KeyGenerator(c), count, cfg.Max)
			return c.Status(fiber.StatusTooManyRequests).JSON(fiber.Map{
				"error":   "Rate limit exceeded",
				"message": fmt.Sprintf("Too many requests. Limit: %d per %s", cfg.Max, cfg.Window),
				"retry_after": ttl.Seconds(),
			})
		}

		return c.Next()
	}
}
