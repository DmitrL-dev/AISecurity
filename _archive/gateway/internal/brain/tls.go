package brain

import (
	"crypto/tls"
	"crypto/x509"
	"fmt"
	"os"
)

// TLSConfig holds TLS configuration for gRPC client
type TLSConfig struct {
	Enabled  bool
	CertPath string
	KeyPath  string
	CAPath   string
}

// LoadTLSConfigFromEnv loads TLS configuration from environment variables
func LoadTLSConfigFromEnv() TLSConfig {
	enabled := os.Getenv("TLS_ENABLED") == "true"
	
	return TLSConfig{
		Enabled:  enabled,
		CertPath: getEnvOrDefault("TLS_CERT_PATH", "/certs/gateway.crt"),
		KeyPath:  getEnvOrDefault("TLS_KEY_PATH", "/certs/gateway.key"),
		CAPath:   getEnvOrDefault("TLS_CA_PATH", "/certs/ca.crt"),
	}
}

// CreateTLSCredentials creates TLS credentials for mTLS gRPC connection
func (c TLSConfig) CreateTLSCredentials() (*tls.Config, error) {
	if !c.Enabled {
		return nil, nil
	}

	// Load client certificate and key
	cert, err := tls.LoadX509KeyPair(c.CertPath, c.KeyPath)
	if err != nil {
		return nil, fmt.Errorf("failed to load client certificate: %w", err)
	}

	// Load CA certificate
	caCert, err := os.ReadFile(c.CAPath)
	if err != nil {
		return nil, fmt.Errorf("failed to load CA certificate: %w", err)
	}

	caCertPool := x509.NewCertPool()
	if !caCertPool.AppendCertsFromPEM(caCert) {
		return nil, fmt.Errorf("failed to parse CA certificate")
	}

	return &tls.Config{
		Certificates: []tls.Certificate{cert},
		RootCAs:      caCertPool,
		MinVersion:   tls.VersionTLS12,
	}, nil
}

func getEnvOrDefault(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}
