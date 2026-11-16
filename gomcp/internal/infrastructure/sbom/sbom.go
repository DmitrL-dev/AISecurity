// Package sbom implements SEC-010 SBOM + Release Signing.
//
// Generates SPDX Software Bill of Materials and provides
// binary signing using Ed25519 (with Sigstore Cosign integration point).
//
// Usage:
//
//	gen := sbom.NewGenerator("SENTINEL AI SOC", "2.1.0")
//	gen.AddDependency("golang.org/x/crypto", "v0.21.0", "BSD-3-Clause")
//	spdx, _ := gen.GenerateSPDX()
package sbom

import (
	"crypto/ed25519"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"time"
)

// SPDXDocument is an SPDX 2.3 SBOM document.
type SPDXDocument struct {
	SPDXVersion    string        `json:"spdxVersion"`
	DataLicense    string        `json:"dataLicense"`
	SPDXID         string        `json:"SPDXID"`
	DocumentName   string        `json:"name"`
	Namespace      string        `json:"documentNamespace"`
	CreationInfo   CreationInfo  `json:"creationInfo"`
	Packages       []Package     `json:"packages"`
	Relationships  []Relationship `json:"relationships,omitempty"`
}

// CreationInfo describes when and how the SBOM was created.
type CreationInfo struct {
	Created  string   `json:"created"`
	Creators []string `json:"creators"`
	Comment  string   `json:"comment,omitempty"`
}

// Package is an SPDX package entry.
type Package struct {
	SPDXID       string `json:"SPDXID"`
	Name         string `json:"name"`
	Version      string `json:"versionInfo"`
	Supplier     string `json:"supplier,omitempty"`
	License      string `json:"licenseConcluded"`
	DownloadURL  string `json:"downloadLocation"`
	Checksum     string `json:"checksum,omitempty"` // SHA256:hex
}

// Relationship links packages.
type Relationship struct {
	Element string `json:"spdxElementId"`
	Type    string `json:"relationshipType"`
	Related string `json:"relatedSpdxElement"`
}

// ReleaseSignature is a signed release record.
type ReleaseSignature struct {
	Binary    string `json:"binary"`
	Version   string `json:"version"`
	Hash      string `json:"hash"`       // SHA-256
	Signature string `json:"signature"`   // Ed25519 hex
	KeyID     string `json:"key_id"`
	SignedAt  string `json:"signed_at"`
}

// Generator produces SBOM documents.
type Generator struct {
	productName string
	version     string
	packages    []Package
}

// NewGenerator creates an SBOM generator.
func NewGenerator(productName, version string) *Generator {
	return &Generator{
		productName: productName,
		version:     version,
	}
}

// AddDependency adds a dependency to the SBOM.
func (g *Generator) AddDependency(name, version, license string) {
	g.packages = append(g.packages, Package{
		SPDXID:      fmt.Sprintf("SPDXRef-%s", sanitizeID(name)),
		Name:        name,
		Version:     version,
		License:     license,
		DownloadURL: fmt.Sprintf("https://pkg.go.dev/%s@%s", name, version),
	})
}

// GenerateSPDX creates an SPDX 2.3 JSON document.
func (g *Generator) GenerateSPDX() (*SPDXDocument, error) {
	doc := &SPDXDocument{
		SPDXVersion: "SPDX-2.3",
		DataLicense: "CC0-1.0",
		SPDXID:      "SPDXRef-DOCUMENT",
		DocumentName: fmt.Sprintf("%s-%s", g.productName, g.version),
		Namespace:    fmt.Sprintf("https://sentinel.spectorn.ai/spdx/%s/%s", g.productName, g.version),
		CreationInfo: CreationInfo{
			Created:  time.Now().UTC().Format(time.RFC3339),
			Creators: []string{"Tool: sentinel-sbom-gen", "Organization: Syntrex"},
		},
		Packages: append([]Package{{
			SPDXID:      "SPDXRef-Product",
			Name:        g.productName,
			Version:     g.version,
			License:     "Proprietary",
			DownloadURL: "https://github.com/syntrex/gomcp",
		}}, g.packages...),
	}

	// Add relationships.
	for _, pkg := range g.packages {
		doc.Relationships = append(doc.Relationships, Relationship{
			Element: "SPDXRef-Product",
			Type:    "DEPENDS_ON",
			Related: pkg.SPDXID,
		})
	}

	return doc, nil
}

// ExportJSON serializes the SBOM to JSON.
func ExportJSON(doc *SPDXDocument) ([]byte, error) {
	return json.MarshalIndent(doc, "", "  ")
}

// SignRelease signs a binary for release verification.
func SignRelease(binaryPath, version string, privateKey ed25519.PrivateKey, keyID string) (*ReleaseSignature, error) {
	hash, err := hashFile(binaryPath)
	if err != nil {
		return nil, fmt.Errorf("sbom: hash %s: %w", binaryPath, err)
	}

	hashBytes, _ := hex.DecodeString(hash)
	sig := ed25519.Sign(privateKey, hashBytes)

	return &ReleaseSignature{
		Binary:    binaryPath,
		Version:   version,
		Hash:      hash,
		Signature: hex.EncodeToString(sig),
		KeyID:     keyID,
		SignedAt:  time.Now().UTC().Format(time.RFC3339),
	}, nil
}

// VerifyRelease verifies a signed release.
func VerifyRelease(sig *ReleaseSignature, publicKey ed25519.PublicKey) bool {
	hashBytes, err := hex.DecodeString(sig.Hash)
	if err != nil {
		return false
	}
	sigBytes, err := hex.DecodeString(sig.Signature)
	if err != nil {
		return false
	}
	return ed25519.Verify(publicKey, hashBytes, sigBytes)
}

// --- Helpers ---

func sanitizeID(name string) string {
	result := make([]byte, 0, len(name))
	for _, c := range name {
		if (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') || c == '-' {
			result = append(result, byte(c))
		} else {
			result = append(result, '-')
		}
	}
	return string(result)
}

func hashFile(path string) (string, error) {
	f, err := os.Open(path)
	if err != nil {
		return "", err
	}
	defer f.Close()
	h := sha256.New()
	if _, err := io.Copy(h, f); err != nil {
		return "", err
	}
	return hex.EncodeToString(h.Sum(nil)), nil
}
