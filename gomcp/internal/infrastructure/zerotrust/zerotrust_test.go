package zerotrust

import (
	"testing"
)

func TestNewIdentity(t *testing.T) {
	id, err := NewIdentity("soc-ingest", SPIFFEIngest)
	if err != nil {
		t.Fatalf("NewIdentity: %v", err)
	}

	if id.SPIFFEID() != SPIFFEIngest {
		t.Errorf("spiffe_id = %s, want %s", id.SPIFFEID(), SPIFFEIngest)
	}

	stats := id.Stats()
	if stats.CertRotations != 1 {
		t.Errorf("cert_rotations = %d, want 1", stats.CertRotations)
	}
}

func TestCertPEM(t *testing.T) {
	id, err := NewIdentity("soc-ingest", SPIFFEIngest)
	if err != nil {
		t.Fatalf("NewIdentity: %v", err)
	}

	pem := id.CertPEM()
	if len(pem) == 0 {
		t.Error("CertPEM is empty")
	}
}

func TestServerTLSConfig(t *testing.T) {
	id, err := NewIdentity("soc-ingest", SPIFFEIngest)
	if err != nil {
		t.Fatalf("NewIdentity: %v", err)
	}

	cfg := id.ServerTLSConfig()
	if cfg.MinVersion != 0x0304 { // TLS 1.3
		t.Errorf("min version = %x, want 0x0304 (TLS 1.3)", cfg.MinVersion)
	}
	if cfg.ClientAuth != 4 { // RequireAndVerifyClientCert
		t.Errorf("client_auth = %d, want 4", cfg.ClientAuth)
	}
	if cfg.ClientCAs == nil {
		t.Error("ClientCAs should not be nil")
	}
}

func TestClientTLSConfig(t *testing.T) {
	id, err := NewIdentity("soc-correlate", SPIFFECorrelate)
	if err != nil {
		t.Fatalf("NewIdentity: %v", err)
	}

	cfg := id.ClientTLSConfig()
	if cfg.MinVersion != 0x0304 {
		t.Errorf("min version = %x, want TLS 1.3", cfg.MinVersion)
	}
	if cfg.RootCAs == nil {
		t.Error("RootCAs should not be nil")
	}
}

func TestCertRotation(t *testing.T) {
	id, err := NewIdentity("soc-respond", SPIFFERespond)
	if err != nil {
		t.Fatalf("NewIdentity: %v", err)
	}

	pem1 := string(id.CertPEM())

	if err := id.RotateCert(); err != nil {
		t.Fatalf("RotateCert: %v", err)
	}

	pem2 := string(id.CertPEM())
	if pem1 == pem2 {
		t.Error("cert should change after rotation")
	}

	stats := id.Stats()
	if stats.CertRotations != 2 {
		t.Errorf("rotations = %d, want 2", stats.CertRotations)
	}
}

func TestAuthzPolicy(t *testing.T) {
	// Check ingest accepts immune, shield, sidecar, dashboard.
	allowed := AuthzPolicy[SPIFFEIngest]
	if len(allowed) != 4 {
		t.Errorf("ingest allowed_callers = %d, want 4", len(allowed))
	}

	// Correlate only accepts ingest.
	allowed = AuthzPolicy[SPIFFECorrelate]
	if len(allowed) != 1 || allowed[0] != SPIFFEIngest {
		t.Errorf("correlate allowed = %v, want [ingest]", allowed)
	}

	// Respond only accepts correlate.
	allowed = AuthzPolicy[SPIFFERespond]
	if len(allowed) != 1 || allowed[0] != SPIFFECorrelate {
		t.Errorf("respond allowed = %v, want [correlate]", allowed)
	}
}
