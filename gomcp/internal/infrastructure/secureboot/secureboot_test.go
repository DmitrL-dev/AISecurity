package secureboot

import (
	"crypto/ed25519"
	"encoding/hex"
	"os"
	"testing"
)

func TestNewVerifier(t *testing.T) {
	v := NewVerifier()
	stats := v.Stats()
	if stats.TotalVerifications != 0 {
		t.Errorf("total = %d, want 0", stats.TotalVerifications)
	}
}

func TestVerifyBinary_Unsigned(t *testing.T) {
	v := NewVerifier()

	// Verify self (test binary) — should fail without signature.
	exe, _ := os.Executable()
	result := v.VerifyBinary(exe)

	if result.Valid {
		t.Error("expected invalid for unsigned binary")
	}
	if result.BinaryHash == "" {
		t.Error("hash should be populated even for unsigned")
	}
}

func TestVerifyBinary_Signed(t *testing.T) {
	v := NewVerifier()

	// Generate key pair.
	pub, priv := GenerateKeyPair()

	v.AddTrustedKey(TrustedKey{
		ID:        "test-key-1",
		Algorithm: "ed25519",
		PublicKey: pub,
		PublicHex: hex.EncodeToString(pub),
		Purpose:   "binary_signing",
	})

	// Sign the test binary.
	exe, _ := os.Executable()
	hash, sig, err := SignBinary(exe, priv)
	if err != nil {
		t.Fatalf("SignBinary: %v", err)
	}

	// Register signature.
	v.RegisterSignature(hash, sig, "test-key-1")

	// Verify.
	result := v.VerifyBinary(exe)
	if !result.Valid {
		t.Errorf("expected valid, got error: %s", result.Error)
	}
	if !result.SignatureOK {
		t.Error("signature should be OK")
	}
	if result.TrustedKey != "test-key-1" {
		t.Errorf("trusted_key = %s, want test-key-1", result.TrustedKey)
	}
}

func TestVerifyBinary_WrongKey(t *testing.T) {
	v := NewVerifier()

	// Generate two different key pairs.
	pub1, _ := GenerateKeyPair()
	_, priv2 := GenerateKeyPair()

	v.AddTrustedKey(TrustedKey{
		ID:        "key-1",
		Algorithm: "ed25519",
		PublicKey: pub1, // Trust key 1
		PublicHex: hex.EncodeToString(pub1),
	})

	// Sign with key 2.
	exe, _ := os.Executable()
	hash, sig, _ := SignBinary(exe, priv2)
	v.RegisterSignature(hash, sig, "key-1") // Attribute to key-1

	// Verify — should fail because sig was made with key-2.
	result := v.VerifyBinary(exe)
	if result.Valid {
		t.Error("expected invalid for wrong key")
	}
}

func TestGenerateAttestation(t *testing.T) {
	v := NewVerifier()
	pub, priv := GenerateKeyPair()

	v.AddTrustedKey(TrustedKey{
		ID: "boot-key", Algorithm: "ed25519", PublicKey: pub,
		PublicHex: hex.EncodeToString(pub),
	})

	exe, _ := os.Executable()
	hash, sig, _ := SignBinary(exe, priv)
	v.RegisterSignature(hash, sig, "boot-key")

	attestation := v.GenerateAttestation("node-001", map[string]string{
		"soc-ingest": exe,
	})

	if !attestation.AllVerified {
		t.Error("expected all binaries verified")
	}
	if len(attestation.Binaries) != 1 {
		t.Errorf("binaries = %d, want 1", len(attestation.Binaries))
	}
	if attestation.NodeID != "node-001" {
		t.Errorf("node_id = %s, want node-001", attestation.NodeID)
	}
}

func TestExportAttestation(t *testing.T) {
	attestation := BootAttestation{
		NodeID:      "test",
		AllVerified: true,
		ChainValid:  true,
	}

	data, err := ExportAttestation(attestation)
	if err != nil {
		t.Fatalf("ExportAttestation: %v", err)
	}
	if len(data) == 0 {
		t.Error("exported data is empty")
	}
}

func TestSignBinary(t *testing.T) {
	_, priv := GenerateKeyPair()

	exe, _ := os.Executable()
	hash, sig, err := SignBinary(exe, priv)
	if err != nil {
		t.Fatalf("SignBinary: %v", err)
	}
	if len(hash) != 64 {
		t.Errorf("hash length = %d, want 64", len(hash))
	}
	if len(sig) == 0 {
		t.Error("signature is empty")
	}

	// Verify signature manually.
	pub := priv.Public().(ed25519.PublicKey)
	hashBytes, _ := hex.DecodeString(hash)
	sigBytes, _ := hex.DecodeString(sig)
	if !ed25519.Verify(pub, hashBytes, sigBytes) {
		t.Error("manual signature verification failed")
	}
}

func TestStats(t *testing.T) {
	v := NewVerifier()
	exe, _ := os.Executable()

	v.VerifyBinary(exe)
	v.VerifyBinary(exe)

	stats := v.Stats()
	if stats.TotalVerifications != 2 {
		t.Errorf("total = %d, want 2", stats.TotalVerifications)
	}
	if stats.Failed != 2 {
		t.Errorf("failed = %d, want 2 (unsigned)", stats.Failed)
	}
}
