package vault

import (
	"fmt"
	"log"
	"os"
	"strings"

	vaultapi "github.com/hashicorp/vault/api"
)

// Client wraps HashiCorp Vault API for secrets management
type Client struct {
	client  *vaultapi.Client
	enabled bool
}

// NewClient creates a new Vault client
// Falls back to environment variables if VAULT_ENABLED != "true"
func NewClient() (*Client, error) {
	enabled := strings.ToLower(os.Getenv("VAULT_ENABLED")) == "true"

	if !enabled {
		log.Println("Vault disabled, using environment variable fallback")
		return &Client{enabled: false}, nil
	}

	config := vaultapi.DefaultConfig()
	config.Address = os.Getenv("VAULT_ADDR")
	if config.Address == "" {
		config.Address = "http://vault:8200"
	}

	client, err := vaultapi.NewClient(config)
	if err != nil {
		return nil, fmt.Errorf("failed to create Vault client: %w", err)
	}

	token := os.Getenv("VAULT_TOKEN")
	if token == "" {
		return nil, fmt.Errorf("VAULT_TOKEN environment variable required")
	}
	client.SetToken(token)

	log.Printf("Vault client initialized: %s", config.Address)
	return &Client{client: client, enabled: true}, nil
}

// GetSecret retrieves a secret from Vault
// Falls back to fallbackEnv if Vault is disabled or secret not found
func (c *Client) GetSecret(path, key, fallbackEnv string) (string, error) {
	if !c.enabled || c.client == nil {
		if fallbackEnv != "" {
			return os.Getenv(fallbackEnv), nil
		}
		return "", fmt.Errorf("vault disabled and no fallback provided")
	}

	secret, err := c.client.Logical().Read("secret/data/" + path)
	if err != nil {
		if fallbackEnv != "" {
			log.Printf("Vault read failed, falling back to %s: %v", fallbackEnv, err)
			return os.Getenv(fallbackEnv), nil
		}
		return "", fmt.Errorf("failed to read secret %s: %w", path, err)
	}

	if secret == nil || secret.Data == nil {
		if fallbackEnv != "" {
			return os.Getenv(fallbackEnv), nil
		}
		return "", fmt.Errorf("secret %s not found", path)
	}

	data, ok := secret.Data["data"].(map[string]interface{})
	if !ok {
		return "", fmt.Errorf("invalid secret format at %s", path)
	}

	value, ok := data[key].(string)
	if !ok {
		if fallbackEnv != "" {
			return os.Getenv(fallbackEnv), nil
		}
		return "", fmt.Errorf("key %s not found in secret %s", key, path)
	}

	return value, nil
}

// GetJWTSecret retrieves the JWT signing secret
func (c *Client) GetJWTSecret() (string, error) {
	return c.GetSecret("sentinel/gateway", "jwt_secret", "JWT_SECRET")
}

// GetRedisPassword retrieves the Redis password
func (c *Client) GetRedisPassword() (string, error) {
	return c.GetSecret("sentinel/redis", "password", "REDIS_PASSWORD")
}

// IsEnabled returns whether Vault is enabled
func (c *Client) IsEnabled() bool {
	return c.enabled
}
