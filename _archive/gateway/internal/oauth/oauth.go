package oauth

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"os"
	"strings"
	"sync"
	"time"

	"github.com/gofiber/fiber/v2"
)

// Provider represents an OAuth/OIDC provider configuration
type Provider struct {
	Name         string `json:"name"`
	Issuer       string `json:"issuer"`
	ClientID     string `json:"client_id"`
	ClientSecret string `json:"client_secret"`
	AuthURL      string `json:"auth_url"`
	TokenURL     string `json:"token_url"`
	UserInfoURL  string `json:"userinfo_url"`
	Scopes       string `json:"scopes"`
}

// OIDCClaims represents standard OIDC claims
type OIDCClaims struct {
	Sub           string `json:"sub"`
	Email         string `json:"email"`
	EmailVerified bool   `json:"email_verified"`
	Name          string `json:"name"`
	Picture       string `json:"picture"`
	Iss           string `json:"iss"`
	Aud           string `json:"aud"`
	Exp           int64  `json:"exp"`
	Iat           int64  `json:"iat"`
}

// Config for OAuth/OIDC middleware
type Config struct {
	Enabled       bool
	Providers     []Provider
	DefaultScopes []string
	CookieName    string
	SessionTTL    time.Duration
}

// DefaultConfig returns default OAuth config
func DefaultConfig() Config {
	return Config{
		Enabled:       false,
		DefaultScopes: []string{"openid", "email", "profile"},
		CookieName:    "sentinel_session",
		SessionTTL:    24 * time.Hour,
	}
}

// ConfigFromEnv loads config from environment
func ConfigFromEnv() Config {
	cfg := DefaultConfig()
	
	if os.Getenv("OAUTH_ENABLED") == "true" {
		cfg.Enabled = true
	}
	
	// Load providers from env
	// OAUTH_GOOGLE_CLIENT_ID, OAUTH_GOOGLE_CLIENT_SECRET, etc.
	providers := []struct {
		name        string
		issuer      string
		authURL     string
		tokenURL    string
		userInfoURL string
	}{
		{
			name:        "google",
			issuer:      "https://accounts.google.com",
			authURL:     "https://accounts.google.com/o/oauth2/v2/auth",
			tokenURL:    "https://oauth2.googleapis.com/token",
			userInfoURL: "https://openidconnect.googleapis.com/v1/userinfo",
		},
		{
			name:        "microsoft",
			issuer:      "https://login.microsoftonline.com/common/v2.0",
			authURL:     "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
			tokenURL:    "https://login.microsoftonline.com/common/oauth2/v2.0/token",
			userInfoURL: "https://graph.microsoft.com/oidc/userinfo",
		},
		{
			name:        "github",
			issuer:      "https://github.com",
			authURL:     "https://github.com/login/oauth/authorize",
			tokenURL:    "https://github.com/login/oauth/access_token",
			userInfoURL: "https://api.github.com/user",
		},
	}
	
	for _, p := range providers {
		envPrefix := "OAUTH_" + strings.ToUpper(p.name) + "_"
		clientID := os.Getenv(envPrefix + "CLIENT_ID")
		clientSecret := os.Getenv(envPrefix + "CLIENT_SECRET")
		
		if clientID != "" && clientSecret != "" {
			cfg.Providers = append(cfg.Providers, Provider{
				Name:         p.name,
				Issuer:       p.issuer,
				ClientID:     clientID,
				ClientSecret: clientSecret,
				AuthURL:      p.authURL,
				TokenURL:     p.tokenURL,
				UserInfoURL:  p.userInfoURL,
				Scopes:       "openid email profile",
			})
		}
	}
	
	return cfg
}

// Session store
type sessionStore struct {
	sessions map[string]*OIDCClaims
	mu       sync.RWMutex
}

var store = &sessionStore{
	sessions: make(map[string]*OIDCClaims),
}

// NewMiddleware creates OAuth/OIDC middleware
func NewMiddleware(cfg Config) fiber.Handler {
	return func(c *fiber.Ctx) error {
		if !cfg.Enabled {
			return c.Next()
		}
		
		// Skip auth endpoints
		path := c.Path()
		if strings.HasPrefix(path, "/oauth/") || 
		   strings.HasPrefix(path, "/health") ||
		   strings.HasPrefix(path, "/api/v1/auth/login") {
			return c.Next()
		}
		
		// Check session cookie
		sessionID := c.Cookies(cfg.CookieName)
		if sessionID == "" {
			return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
				"error": "Authentication required",
				"oauth_providers": getProviderNames(cfg.Providers),
			})
		}
		
		// Validate session
		store.mu.RLock()
		claims, ok := store.sessions[sessionID]
		store.mu.RUnlock()
		
		if !ok {
			return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
				"error": "Session expired",
			})
		}
		
		// Check expiration
		if time.Now().Unix() > claims.Exp {
			store.mu.Lock()
			delete(store.sessions, sessionID)
			store.mu.Unlock()
			return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
				"error": "Token expired",
			})
		}
		
		// Set user context
		c.Locals("user", claims)
		c.Locals("user_id", claims.Sub)
		c.Locals("email", claims.Email)
		
		return c.Next()
	}
}

// AuthRoutes sets up OAuth routes
func AuthRoutes(app *fiber.App, cfg Config) {
	oauth := app.Group("/oauth")
	
	// List providers
	oauth.Get("/providers", func(c *fiber.Ctx) error {
		providers := make([]fiber.Map, len(cfg.Providers))
		for i, p := range cfg.Providers {
			providers[i] = fiber.Map{
				"name":     p.Name,
				"auth_url": p.AuthURL,
			}
		}
		return c.JSON(fiber.Map{"providers": providers})
	})
	
	// Initiate OAuth flow
	oauth.Get("/authorize/:provider", func(c *fiber.Ctx) error {
		providerName := c.Params("provider")
		provider := findProvider(cfg.Providers, providerName)
		if provider == nil {
			return c.Status(fiber.StatusNotFound).JSON(fiber.Map{
				"error": "Provider not found",
			})
		}
		
		redirectURI := c.BaseURL() + "/oauth/callback/" + providerName
		state := generateState()
		
		authURL := provider.AuthURL +
			"?client_id=" + provider.ClientID +
			"&redirect_uri=" + redirectURI +
			"&response_type=code" +
			"&scope=" + provider.Scopes +
			"&state=" + state
		
		return c.Redirect(authURL)
	})
	
	// OAuth callback
	oauth.Get("/callback/:provider", func(c *fiber.Ctx) error {
		providerName := c.Params("provider")
		code := c.Query("code")
		
		if code == "" {
			return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
				"error": "Missing authorization code",
			})
		}
		
		provider := findProvider(cfg.Providers, providerName)
		if provider == nil {
			return c.Status(fiber.StatusNotFound).JSON(fiber.Map{
				"error": "Provider not found",
			})
		}
		
		// Exchange code for token
		claims, err := exchangeCodeForClaims(provider, code, c.BaseURL())
		if err != nil {
			return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
				"error": "Token exchange failed: " + err.Error(),
			})
		}
		
		// Create session
		sessionID := generateState()
		store.mu.Lock()
		store.sessions[sessionID] = claims
		store.mu.Unlock()
		
		// Set cookie
		c.Cookie(&fiber.Cookie{
			Name:     cfg.CookieName,
			Value:    sessionID,
			Expires:  time.Now().Add(cfg.SessionTTL),
			HTTPOnly: true,
			Secure:   true,
			SameSite: "Lax",
		})
		
		return c.JSON(fiber.Map{
			"message": "Authentication successful",
			"user": fiber.Map{
				"email": claims.Email,
				"name":  claims.Name,
			},
		})
	})
	
	// Logout
	oauth.Post("/logout", func(c *fiber.Ctx) error {
		sessionID := c.Cookies(cfg.CookieName)
		if sessionID != "" {
			store.mu.Lock()
			delete(store.sessions, sessionID)
			store.mu.Unlock()
		}
		
		c.Cookie(&fiber.Cookie{
			Name:    cfg.CookieName,
			Value:   "",
			Expires: time.Now().Add(-time.Hour),
		})
		
		return c.JSON(fiber.Map{"message": "Logged out"})
	})
}

// Helper functions
func findProvider(providers []Provider, name string) *Provider {
	for _, p := range providers {
		if p.Name == name {
			return &p
		}
	}
	return nil
}

func getProviderNames(providers []Provider) []string {
	names := make([]string, len(providers))
	for i, p := range providers {
		names[i] = p.Name
	}
	return names
}

func generateState() string {
	// In production, use crypto/rand
	return "state_" + time.Now().Format("20060102150405")
}

func exchangeCodeForClaims(provider *Provider, code, baseURL string) (*OIDCClaims, error) {
	redirectURI := baseURL + "/oauth/callback/" + provider.Name
	
	// Step 1: Exchange code for token
	tokenReq, err := http.NewRequest("POST", provider.TokenURL, strings.NewReader(
		"grant_type=authorization_code"+
		"&code="+code+
		"&redirect_uri="+redirectURI+
		"&client_id="+provider.ClientID+
		"&client_secret="+provider.ClientSecret,
	))
	if err != nil {
		return nil, err
	}
	
	tokenReq.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	tokenReq.Header.Set("Accept", "application/json")
	
	client := &http.Client{Timeout: 10 * time.Second}
	tokenResp, err := client.Do(tokenReq)
	if err != nil {
		return nil, err
	}
	defer tokenResp.Body.Close()
	
	if tokenResp.StatusCode != http.StatusOK {
		return nil, errors.New("token exchange failed: " + tokenResp.Status)
	}
	
	var tokenData struct {
		AccessToken  string `json:"access_token"`
		TokenType    string `json:"token_type"`
		ExpiresIn    int64  `json:"expires_in"`
		RefreshToken string `json:"refresh_token"`
		IDToken      string `json:"id_token"`
	}
	
	if err := json.NewDecoder(tokenResp.Body).Decode(&tokenData); err != nil {
		return nil, err
	}
	
	if tokenData.AccessToken == "" {
		return nil, errors.New("no access token in response")
	}
	
	// Step 2: Get user info
	userReq, err := http.NewRequestWithContext(context.Background(), "GET", provider.UserInfoURL, nil)
	if err != nil {
		return nil, err
	}
	
	userReq.Header.Set("Authorization", "Bearer "+tokenData.AccessToken)
	userReq.Header.Set("Accept", "application/json")
	
	userResp, err := client.Do(userReq)
	if err != nil {
		return nil, err
	}
	defer userResp.Body.Close()
	
	if userResp.StatusCode != http.StatusOK {
		return nil, errors.New("userinfo request failed: " + userResp.Status)
	}
	
	// Step 3: Parse claims
	var claims OIDCClaims
	if err := json.NewDecoder(userResp.Body).Decode(&claims); err != nil {
		return nil, err
	}
	
	// Set expiration if not provided
	if claims.Exp == 0 {
		claims.Exp = time.Now().Add(time.Duration(tokenData.ExpiresIn) * time.Second).Unix()
		if tokenData.ExpiresIn == 0 {
			claims.Exp = time.Now().Add(1 * time.Hour).Unix()
		}
	}
	
	claims.Iss = provider.Issuer
	
	return &claims, nil
}

