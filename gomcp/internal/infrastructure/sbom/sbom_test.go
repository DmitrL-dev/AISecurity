package sbom

import (
	"crypto/ed25519"
	"encoding/json"
	"os"
	"testing"
)

func TestNewGenerator(t *testing.T) {
	g := NewGenerator("SENTINEL", "2.1.0")
	if g.productName != "SENTINEL" {
		t.Errorf("product = %s", g.productName)
	}
}

func TestGenerateSPDX(t *testing.T) {
	g := NewGenerator("SENTINEL AI SOC", "2.1.0")
	g.AddDependency("golang.org/x/crypto", "v0.21.0", "BSD-3-Clause")
	g.AddDependency("gopkg.in/yaml.v3", "v3.0.1", "Apache-2.0")

	doc, err := g.GenerateSPDX()
	if err != nil {
		t.Fatalf("GenerateSPDX: %v", err)
	}

	if doc.SPDXVersion != "SPDX-2.3" {
		t.Errorf("version = %s", doc.SPDXVersion)
	}
	// Product + 2 deps = 3 packages.
	if len(doc.Packages) != 3 {
		t.Errorf("packages = %d, want 3", len(doc.Packages))
	}
	if len(doc.Relationships) != 2 {
		t.Errorf("relationships = %d, want 2", len(doc.Relationships))
	}
}

func TestExportJSON(t *testing.T) {
	g := NewGenerator("test", "1.0.0")
	g.AddDependency("dep1", "v1.0.0", "MIT")
	doc, _ := g.GenerateSPDX()

	data, err := ExportJSON(doc)
	if err != nil {
		t.Fatalf("ExportJSON: %v", err)
	}

	var parsed SPDXDocument
	if err := json.Unmarshal(data, &parsed); err != nil {
		t.Fatalf("parse JSON: %v", err)
	}
	if parsed.DocumentName != "test-1.0.0" {
		t.Errorf("name = %s", parsed.DocumentName)
	}
}

func TestSignAndVerifyRelease(t *testing.T) {
	pub, priv, _ := ed25519.GenerateKey(nil)

	exe, _ := os.Executable()
	sig, err := SignRelease(exe, "2.1.0", priv, "release-key-1")
	if err != nil {
		t.Fatalf("SignRelease: %v", err)
	}

	if sig.Version != "2.1.0" {
		t.Errorf("version = %s", sig.Version)
	}
	if sig.Hash == "" || sig.Signature == "" {
		t.Error("hash/signature empty")
	}

	if !VerifyRelease(sig, pub) {
		t.Error("verification failed for valid signature")
	}

	// Tamper with hash.
	sig.Hash = "0000000000000000000000000000000000000000000000000000000000000000"
	if VerifyRelease(sig, pub) {
		t.Error("verification should fail for tampered hash")
	}
}
