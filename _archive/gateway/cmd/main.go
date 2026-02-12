package main

import (
	"crypto/tls"
	"log"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/gofiber/fiber/v2"
	"github.com/gofiber/fiber/v2/middleware/logger"
	"sentinel-gateway/internal/auth"
	"sentinel-gateway/internal/brain"
	"sentinel-gateway/internal/proxy"
	"sentinel-gateway/internal/ratelimit"
	"sentinel-gateway/pkg/challenge"
)

func main() {
	// Initialize Fiber app
	app := fiber.New(fiber.Config{
		AppName: "Sentinel Gateway v2.0",
	})

	// Middleware: Logger
	app.Use(logger.New())

	// Middleware: Rate Limiter (Redis Token Bucket)
	app.Use(ratelimit.New(ratelimit.Config{
		Max:    100,              // 100 requests per minute
		Window: time.Minute,
	}))

	// Middleware: PoW Challenge (Anubis-style bot protection)
	powMiddleware := challenge.NewFiberMiddleware(challenge.FiberConfig{
		DefaultDifficulty: 4,
		TokenTTL:          1 * time.Hour,
		ChallengeTTL:      5 * time.Minute,
		ProtectedPaths:    []string{"/v1/"},
		ExemptPaths:       []string{"/health", "/metrics", "/.sentinel/", "/auth/", "/dashboard", "/chat"},
		Rules: []challenge.Rule{
			{Name: "googlebot", UserAgentRegex: "googlebot", Action: challenge.ActionAllow},
			{Name: "bingbot", UserAgentRegex: "bingbot", Action: challenge.ActionAllow},
			{Name: "generic-bot", UserAgentRegex: "bot", Action: challenge.ActionChallenge, Difficulty: 8},
			{Name: "crawler", UserAgentRegex: "crawler", Action: challenge.ActionChallenge, Difficulty: 8},
			{Name: "ai-scrapers", UserAgentRegex: "openai", Action: challenge.ActionChallenge, Difficulty: 12},
			{Name: "anthropic", UserAgentRegex: "anthropic", Action: challenge.ActionChallenge, Difficulty: 12},
		},
		Skip: func(c *fiber.Ctx) bool {
			// Skip if challenge protection is disabled
			return os.Getenv("CHALLENGE_ENABLED") == "false"
		},
	})
	app.Use(powMiddleware.Handler())

	// Challenge stats endpoint
	app.Get("/.sentinel/challenge/stats", func(c *fiber.Ctx) error {
		return c.JSON(powMiddleware.Stats())
	})

	// Initialize Brain Client with TLS
	brainAddr := os.Getenv("SENTINEL_BRAIN_URL")
	if brainAddr == "" {
		brainAddr = "localhost:50051"
	}
	
	// Load TLS configuration
	tlsConfig := brain.LoadTLSConfigFromEnv()
	var tlsCreds *tls.Config
	if tlsConfig.Enabled {
		var err error
		tlsCreds, err = tlsConfig.CreateTLSCredentials()
		if err != nil {
			log.Fatalf("Failed to load TLS credentials: %v", err)
		}
	}
	
	brainClient, err := brain.NewClient(brainAddr, tlsCreds)
	if err != nil {
		log.Fatalf("Failed to connect to Brain: %v", err)
	}
	defer brainClient.Close()

	// Auth configuration
	authConfig := auth.DefaultConfig()

	// Public routes (no auth required)
	app.Get("/health", func(c *fiber.Ctx) error {
		return c.JSON(fiber.Map{"status": "ok"})
	})
	
	// Auth routes
	app.Post("/auth/login", auth.LoginHandler(authConfig))
	
	// Protected routes (auth required)
	protected := app.Group("/v1")
	
	// Check if auth is enabled
	if os.Getenv("AUTH_ENABLED") != "false" {
		protected.Use(auth.Middleware(authConfig))
	}
	
	protected.Post("/chat/completions", proxy.NewHandler(brainClient))
	protected.Post("/auth/refresh", auth.RefreshHandler(authConfig))

	// Static files for Dashboard UI
	app.Static("/", "./dashboard", fiber.Static{
		Index: "chat.html",
	})
	
	// Explicit routes for dashboard pages
	app.Get("/chat", func(c *fiber.Ctx) error {
		return c.SendFile("./dashboard/chat.html")
	})
	
	app.Get("/dashboard", func(c *fiber.Ctx) error {
		return c.SendFile("./dashboard/index.html")
	})

	// Graceful Shutdown
	go func() {
		if err := app.Listen(":8080"); err != nil {
			log.Panic(err)
		}
	}()

	log.Println("Sentinel Gateway v2.0 started on :8080")
	log.Printf("Auth enabled: %v", os.Getenv("AUTH_ENABLED") != "false")

	c := make(chan os.Signal, 1)
	signal.Notify(c, os.Interrupt, syscall.SIGTERM)
	<-c

	log.Println("Shutting down Sentinel Gateway...")
	_ = app.Shutdown()
}
