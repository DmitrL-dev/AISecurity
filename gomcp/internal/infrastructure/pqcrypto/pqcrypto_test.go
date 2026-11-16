package pqcrypto

import (
	"testing"
)

func TestNewHybridSigner(t *testing.T) {
	signer, err := NewHybridSigner(SchemeHybrid)
	if err != nil {
		t.Fatalf("NewHybridSigner: %v", err)
	}
	if signer.PublicKeyHex() == "" {
		t.Error("public key empty")
	}
}

func TestSignAndVerify(t *testing.T) {
	signer, err := NewHybridSigner(SchemeHybrid)
	if err != nil {
		t.Fatalf("NewHybridSigner: %v", err)
	}

	data := []byte("decision: allow event EVT-001")
	sig, err := signer.Sign(data)
	if err != nil {
		t.Fatalf("Sign: %v", err)
	}

	if sig.ClassicalSig == "" {
		t.Error("classical sig empty")
	}
	if sig.PQSig == "" {
		t.Error("PQ sig empty")
	}
	if sig.Scheme != SchemeHybrid {
		t.Errorf("scheme = %s, want hybrid", sig.Scheme)
	}

	if !signer.Verify(data, sig) {
		t.Error("verification failed for valid signature")
	}
}

func TestVerify_TamperedData(t *testing.T) {
	signer, _ := NewHybridSigner(SchemeHybrid)

	data := []byte("original data")
	sig, _ := signer.Sign(data)

	tamperedData := []byte("tampered data")
	if signer.Verify(tamperedData, sig) {
		t.Error("should fail for tampered data")
	}
}

func TestVerify_TamperedSig(t *testing.T) {
	signer, _ := NewHybridSigner(SchemeHybrid)

	data := []byte("test data")
	sig, _ := signer.Sign(data)

	sig.PQSig = "0000000000000000000000000000000000000000000000000000000000000000"
	if signer.Verify(data, sig) {
		t.Error("should fail for tampered PQ sig")
	}
}

func TestStats(t *testing.T) {
	signer, _ := NewHybridSigner(SchemeHybrid)

	signer.Sign([]byte("a"))
	signer.Sign([]byte("b"))
	sig, _ := signer.Sign([]byte("c"))
	signer.Verify([]byte("c"), sig)

	stats := signer.Stats()
	if stats.TotalSigns != 3 {
		t.Errorf("signs = %d, want 3", stats.TotalSigns)
	}
	if stats.TotalVerifies != 1 {
		t.Errorf("verifies = %d, want 1", stats.TotalVerifies)
	}
}
