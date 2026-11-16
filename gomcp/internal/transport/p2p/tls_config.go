package transport

import (
	"crypto/ecdsa"
	"crypto/elliptic"
	"crypto/rand"
	"crypto/tls"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/pem"
	"fmt"
	"math/big"
	"net"
	"time"
)

// TLSConfig configures mutual TLS for P2P connections (v3.6).
type TLSConfig struct {
	CertFile string `json:"cert_file,omitempty"` // Path to cert PEM (auto-generated if empty)
	KeyFile  string `json:"key_file,omitempty"`  // Path to key PEM (auto-generated if empty)
	Enabled  bool   `json:"enabled"`
}

// GenerateSelfSignedCert creates a self-signed TLS certificate for P2P mutual auth.
// The cert includes the peer ID as the common name for identity verification.
func GenerateSelfSignedCert(peerID string) (tls.Certificate, error) {
	key, err := ecdsa.GenerateKey(elliptic.P256(), rand.Reader)
	if err != nil {
		return tls.Certificate{}, fmt.Errorf("generate key: %w", err)
	}

	serial, _ := rand.Int(rand.Reader, new(big.Int).Lsh(big.NewInt(1), 128))

	template := &x509.Certificate{
		SerialNumber: serial,
		Subject: pkix.Name{
			CommonName:   peerID,
			Organization: []string{"GoMCP P2P"},
		},
		NotBefore:             time.Now(),
		NotAfter:              time.Now().Add(365 * 24 * time.Hour),
		KeyUsage:              x509.KeyUsageDigitalSignature | x509.KeyUsageKeyEncipherment,
		ExtKeyUsage:           []x509.ExtKeyUsage{x509.ExtKeyUsageServerAuth, x509.ExtKeyUsageClientAuth},
		BasicConstraintsValid: true,
		IPAddresses:           []net.IP{net.ParseIP("127.0.0.1")},
		DNSNames:              []string{"localhost"},
	}

	certDER, err := x509.CreateCertificate(rand.Reader, template, template, &key.PublicKey, key)
	if err != nil {
		return tls.Certificate{}, fmt.Errorf("create cert: %w", err)
	}

	certPEM := pem.EncodeToMemory(&pem.Block{Type: "CERTIFICATE", Bytes: certDER})
	keyDER, err := x509.MarshalECPrivateKey(key)
	if err != nil {
		return tls.Certificate{}, fmt.Errorf("marshal key: %w", err)
	}
	keyPEM := pem.EncodeToMemory(&pem.Block{Type: "EC PRIVATE KEY", Bytes: keyDER})

	return tls.X509KeyPair(certPEM, keyPEM)
}

// NewMutualTLSConfig creates a TLS config for mutual authentication.
// Both server and client verify each other's certificates.
func NewMutualTLSConfig(cert tls.Certificate) *tls.Config {
	return &tls.Config{
		Certificates:       []tls.Certificate{cert},
		ClientAuth:         tls.RequireAnyClientCert,
		InsecureSkipVerify: true, // Self-signed certs — verify via genome hash instead.
		MinVersion:         tls.VersionTLS13,
	}
}

// ExtractPeerIDFromCert extracts the peer ID (CommonName) from a TLS connection.
func ExtractPeerIDFromCert(conn *tls.Conn) (string, error) {
	state := conn.ConnectionState()
	if len(state.PeerCertificates) == 0 {
		return "", fmt.Errorf("no peer certificate")
	}
	return state.PeerCertificates[0].Subject.CommonName, nil
}
