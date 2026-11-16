// Package zerotrust implements SEC-008 Zero-Trust Internal Networking.
//
// Provides mTLS with SPIFFE identity for all internal SOC communication:
//   - Certificate generation and rotation (24h default)
//   - SPIFFE workload identity (spiffe://sentinel.syntrex.io/soc/*)
//   - TLS 1.3 only with strong cipher suites
//   - Client certificate validation (mutual TLS)
//   - Connection authorization based on SPIFFE ID allowlists
//
// Usage:
//
//	zt := zerotrust.New("soc-ingest", spiffeID)
//	tlsConfig := zt.ServerTLSConfig()
//	// or
//	tlsConfig := zt.ClientTLSConfig(targetSPIFFEID)
package zerotrust

import (
	"crypto/ecdsa"
	"crypto/elliptic"
	"crypto/rand"
	"crypto/tls"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/pem"
	"fmt"
	"log/slog"
	"math/big"
	"net/url"
	"sync"
	"time"
)

const (
	// DefaultCertLifetime is the certificate rotation period.
	DefaultCertLifetime = 24 * time.Hour

	// TrustDomain is the SPIFFE trust domain.
	TrustDomain = "sentinel.syntrex.pro"
)

// SPIFFEID is a SPIFFE workload identity.
type SPIFFEID string

// Well-known SPIFFE IDs for SOC components.
const (
	SPIFFEIngest    SPIFFEID = "spiffe://sentinel.syntrex.pro/soc/ingest"
	SPIFFECorrelate SPIFFEID = "spiffe://sentinel.syntrex.pro/soc/correlate"
	SPIFFERespond   SPIFFEID = "spiffe://sentinel.syntrex.pro/soc/respond"
	SPIFFEImmune    SPIFFEID = "spiffe://sentinel.syntrex.pro/sensor/immune"
	SPIFFESidecar   SPIFFEID = "spiffe://sentinel.syntrex.pro/sensor/sidecar"
	SPIFFEShield    SPIFFEID = "spiffe://sentinel.syntrex.pro/sensor/shield"
	SPIFFEDashboard SPIFFEID = "spiffe://sentinel.syntrex.pro/dashboard"
)

// AuthzPolicy defines which SPIFFE IDs can connect to a service.
var AuthzPolicy = map[SPIFFEID][]SPIFFEID{
	SPIFFEIngest:    {SPIFFEImmune, SPIFFEShield, SPIFFESidecar, SPIFFEDashboard},
	SPIFFECorrelate: {SPIFFEIngest},
	SPIFFERespond:   {SPIFFECorrelate},
}

// Identity holds a service's mTLS identity.
type Identity struct {
	mu          sync.RWMutex
	spiffeID    SPIFFEID
	serviceName string
	cert        *tls.Certificate
	caCert      *x509.Certificate
	caKey       *ecdsa.PrivateKey
	caPool      *x509.CertPool
	allowedCallers []SPIFFEID
	logger      *slog.Logger
	stats       IdentityStats
}

// IdentityStats tracks mTLS metrics.
type IdentityStats struct {
	mu                sync.Mutex
	CertRotations     int64     `json:"cert_rotations"`
	ConnectionsAccepted int64   `json:"connections_accepted"`
	ConnectionsDenied   int64   `json:"connections_denied"`
	LastRotation      time.Time `json:"last_rotation"`
	CertExpiry        time.Time `json:"cert_expiry"`
	StartedAt         time.Time `json:"started_at"`
}

// NewIdentity creates a new zero-trust mTLS identity.
func NewIdentity(serviceName string, spiffeID SPIFFEID) (*Identity, error) {
	logger := slog.Default().With("component", "sec-008-zerotrust", "service", serviceName)

	// Generate CA for this trust domain (in production: use SPIRE).
	caKey, err := ecdsa.GenerateKey(elliptic.P256(), rand.Reader)
	if err != nil {
		return nil, fmt.Errorf("zerotrust: generate CA key: %w", err)
	}

	caTemplate := &x509.Certificate{
		SerialNumber: big.NewInt(1),
		Subject: pkix.Name{
			Organization: []string{"SENTINEL AI SOC"},
			CommonName:   "SENTINEL Trust CA",
		},
		NotBefore:             time.Now(),
		NotAfter:              time.Now().Add(365 * 24 * time.Hour),
		IsCA:                  true,
		KeyUsage:              x509.KeyUsageCertSign | x509.KeyUsageCRLSign,
		BasicConstraintsValid: true,
	}

	caCertDER, err := x509.CreateCertificate(rand.Reader, caTemplate, caTemplate, &caKey.PublicKey, caKey)
	if err != nil {
		return nil, fmt.Errorf("zerotrust: create CA cert: %w", err)
	}

	caCert, err := x509.ParseCertificate(caCertDER)
	if err != nil {
		return nil, fmt.Errorf("zerotrust: parse CA cert: %w", err)
	}

	caPool := x509.NewCertPool()
	caPool.AddCert(caCert)

	// Lookup authorization policy.
	allowed := AuthzPolicy[spiffeID]

	identity := &Identity{
		spiffeID:       spiffeID,
		serviceName:    serviceName,
		caCert:         caCert,
		caKey:          caKey,
		caPool:         caPool,
		allowedCallers: allowed,
		logger:         logger,
		stats: IdentityStats{
			StartedAt: time.Now(),
		},
	}

	// Generate initial workload certificate.
	if err := identity.rotateCert(); err != nil {
		return nil, fmt.Errorf("zerotrust: initial cert: %w", err)
	}

	logger.Info("zero-trust identity initialized",
		"spiffe_id", spiffeID,
		"allowed_callers", len(allowed),
		"cert_expiry", identity.stats.CertExpiry,
	)

	return identity, nil
}

// ServerTLSConfig returns a TLS config for accepting mTLS connections.
func (id *Identity) ServerTLSConfig() *tls.Config {
	return &tls.Config{
		GetCertificate: func(*tls.ClientHelloInfo) (*tls.Certificate, error) {
			id.mu.RLock()
			defer id.mu.RUnlock()
			return id.cert, nil
		},
		ClientAuth: tls.RequireAndVerifyClientCert,
		ClientCAs:  id.caPool,
		MinVersion: tls.VersionTLS13,
		CipherSuites: []uint16{
			tls.TLS_AES_256_GCM_SHA384,
			tls.TLS_CHACHA20_POLY1305_SHA256,
		},
		VerifyPeerCertificate: id.verifyPeerCert,
	}
}

// ClientTLSConfig returns a TLS config for connecting to a peer.
func (id *Identity) ClientTLSConfig() *tls.Config {
	return &tls.Config{
		GetClientCertificate: func(*tls.CertificateRequestInfo) (*tls.Certificate, error) {
			id.mu.RLock()
			defer id.mu.RUnlock()
			return id.cert, nil
		},
		RootCAs:    id.caPool,
		MinVersion: tls.VersionTLS13,
	}
}

// RotateCert generates a new workload certificate.
func (id *Identity) RotateCert() error {
	return id.rotateCert()
}

// SPIFFEID returns the identity's SPIFFE ID.
func (id *Identity) SPIFFEID() SPIFFEID {
	return id.spiffeID
}

// CertPEM returns the current certificate in PEM format.
func (id *Identity) CertPEM() []byte {
	id.mu.RLock()
	defer id.mu.RUnlock()
	if id.cert == nil || len(id.cert.Certificate) == 0 {
		return nil
	}
	return pem.EncodeToMemory(&pem.Block{
		Type:  "CERTIFICATE",
		Bytes: id.cert.Certificate[0],
	})
}

// Stats returns identity metrics.
func (id *Identity) Stats() IdentityStats {
	id.stats.mu.Lock()
	defer id.stats.mu.Unlock()
	return IdentityStats{
		CertRotations:      id.stats.CertRotations,
		ConnectionsAccepted: id.stats.ConnectionsAccepted,
		ConnectionsDenied:   id.stats.ConnectionsDenied,
		LastRotation:        id.stats.LastRotation,
		CertExpiry:          id.stats.CertExpiry,
		StartedAt:           id.stats.StartedAt,
	}
}

// --- Internal ---

func (id *Identity) rotateCert() error {
	key, err := ecdsa.GenerateKey(elliptic.P256(), rand.Reader)
	if err != nil {
		return fmt.Errorf("generate key: %w", err)
	}

	spiffeURL, _ := url.Parse(string(id.spiffeID))

	template := &x509.Certificate{
		SerialNumber: big.NewInt(time.Now().UnixNano()),
		Subject: pkix.Name{
			Organization: []string{"SENTINEL AI SOC"},
			CommonName:   id.serviceName,
		},
		URIs:      []*url.URL{spiffeURL},
		NotBefore: time.Now(),
		NotAfter:  time.Now().Add(DefaultCertLifetime),
		KeyUsage:  x509.KeyUsageDigitalSignature | x509.KeyUsageKeyEncipherment,
		ExtKeyUsage: []x509.ExtKeyUsage{
			x509.ExtKeyUsageServerAuth,
			x509.ExtKeyUsageClientAuth,
		},
	}

	certDER, err := x509.CreateCertificate(rand.Reader, template, id.caCert, &key.PublicKey, id.caKey)
	if err != nil {
		return fmt.Errorf("create cert: %w", err)
	}

	cert := &tls.Certificate{
		Certificate: [][]byte{certDER},
		PrivateKey:  key,
	}

	id.mu.Lock()
	id.cert = cert
	id.mu.Unlock()

	id.stats.mu.Lock()
	id.stats.CertRotations++
	id.stats.LastRotation = time.Now()
	id.stats.CertExpiry = template.NotAfter
	id.stats.mu.Unlock()

	id.logger.Info("certificate rotated",
		"expiry", template.NotAfter,
		"rotations", id.stats.CertRotations,
	)

	return nil
}

func (id *Identity) verifyPeerCert(rawCerts [][]byte, _ [][]*x509.Certificate) error {
	if len(rawCerts) == 0 {
		id.stats.mu.Lock()
		id.stats.ConnectionsDenied++
		id.stats.mu.Unlock()
		return fmt.Errorf("no client certificate")
	}

	cert, err := x509.ParseCertificate(rawCerts[0])
	if err != nil {
		id.stats.mu.Lock()
		id.stats.ConnectionsDenied++
		id.stats.mu.Unlock()
		return fmt.Errorf("invalid client certificate: %w", err)
	}

	// Check SPIFFE ID in URI SAN.
	for _, uri := range cert.URIs {
		callerID := SPIFFEID(uri.String())
		for _, allowed := range id.allowedCallers {
			if callerID == allowed {
				id.stats.mu.Lock()
				id.stats.ConnectionsAccepted++
				id.stats.mu.Unlock()
				return nil
			}
		}
	}

	id.stats.mu.Lock()
	id.stats.ConnectionsDenied++
	id.stats.mu.Unlock()

	return fmt.Errorf("SPIFFE ID not authorized")
}
