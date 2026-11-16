package oracle

import (
	"context"
	"crypto/aes"
	"crypto/cipher"
	"crypto/rand"
	"crypto/sha256"
	"fmt"
	"io"
	"regexp"
	"strings"

	"github.com/syntrex/gomcp/internal/domain/crystal"
	"github.com/syntrex/gomcp/internal/domain/memory"
)

// ThreatFinding represents a single finding from the threat model scanner.
type ThreatFinding struct {
	Category  string `json:"category"` // SECRET, WEAK_CONFIG, LOGIC_HOLE, HARDCODED
	Severity  string `json:"severity"` // CRITICAL, HIGH, MEDIUM, LOW
	FilePath  string `json:"file_path"`
	Line      int    `json:"line,omitempty"`
	Primitive string `json:"primitive,omitempty"`
	Detail    string `json:"detail"`
}

// ThreatReport is the result of synthesize_threat_model.
type ThreatReport struct {
	Findings        []ThreatFinding `json:"findings"`
	CrystalsScanned int             `json:"crystals_scanned"`
	FactsCorrelated int             `json:"facts_correlated"`
	Encrypted       bool            `json:"encrypted"`
}

// Threat detection patterns (beyond secret_scanner).
var threatPatterns = []struct {
	pattern  *regexp.Regexp
	category string
	severity string
	detail   string
}{
	{regexp.MustCompile(`(?i)TODO\s*:?\s*(hack|fix|security|vuln|bypass)`), "LOGIC_HOLE", "MEDIUM", "Security TODO left in code"},
	{regexp.MustCompile(`(?i)(disable|skip|bypass)\s*(auth|ssl|tls|verify|validation|certificate)`), "WEAK_CONFIG", "HIGH", "Security mechanism disabled"},
	{regexp.MustCompile(`(?i)http://[^\s"']+`), "WEAK_CONFIG", "MEDIUM", "Plain HTTP URL (no TLS)"},
	{regexp.MustCompile(`(?i)(0\.0\.0\.0|localhost|127\.0\.0\.1):\d+`), "WEAK_CONFIG", "LOW", "Hardcoded local address"},
	{regexp.MustCompile(`(?i)password\s*=\s*["'][^"']{1,30}["']`), "HARDCODED", "CRITICAL", "Hardcoded password"},
	{regexp.MustCompile(`(?i)(exec|eval|system)\s*\(`), "LOGIC_HOLE", "HIGH", "Dynamic code execution"},
	{regexp.MustCompile(`(?i)chmod\s+0?777`), "WEAK_CONFIG", "HIGH", "World-writable permissions"},
	{regexp.MustCompile(`(?i)(unsafe|nosec|nolint:\s*security)`), "LOGIC_HOLE", "MEDIUM", "Security lint suppressed"},
	{regexp.MustCompile(`(?i)cors.*(\*|AllowAll|allow_all)`), "WEAK_CONFIG", "HIGH", "CORS wildcard enabled"},
	{regexp.MustCompile(`(?i)debug\s*[:=]\s*(true|1|on|yes)`), "WEAK_CONFIG", "MEDIUM", "Debug mode enabled in config"},
	// Shadow AI — unauthorized external AI usage (§C³ Shadow Guard)
	{regexp.MustCompile(`(?i)(api\.openai\.com|api\.anthropic\.com|api\.deepseek\.com|api\.mistral\.ai|api\.groq\.com|api\.cohere\.com)`), "SHADOW_AI", "HIGH", "External AI API endpoint detected"},
	{regexp.MustCompile(`(?i)(sk-[a-zA-Z0-9]{20,}|ANTHROPIC_API_KEY|DEEPSEEK_API_KEY|OPENAI_API_KEY|GROQ_API_KEY)`), "SHADOW_AI", "CRITICAL", "AI provider API key detected"},
	{regexp.MustCompile(`(?i)(ollama|localhost:11434|127\.0\.0\.1:11434|0\.0\.0\.0:11434)`), "SHADOW_AI", "HIGH", "Local Ollama runtime detected"},
	{regexp.MustCompile(`(?i)(moltbot|langchain|autogen|crewai)\b.*\.(run|execute|invoke|call)`), "SHADOW_AI", "MEDIUM", "AI agent framework invocation detected"},
}

// SynthesizeThreatModel scans Code Crystals for architectural vulnerabilities.
// Only available in ZERO-G mode. Results are returned as structured findings.
func SynthesizeThreatModel(ctx context.Context, crystalStore crystal.CrystalStore, factStore memory.FactStore) (*ThreatReport, error) {
	report := &ThreatReport{}

	// Scan all crystals.
	crystals, err := crystalStore.List(ctx, "*", 500)
	if err != nil {
		return nil, fmt.Errorf("list crystals: %w", err)
	}
	report.CrystalsScanned = len(crystals)

	for _, c := range crystals {
		// Scan primitive values for threat patterns.
		for _, p := range c.Primitives {
			content := p.Value
			for _, tp := range threatPatterns {
				if tp.pattern.MatchString(content) {
					report.Findings = append(report.Findings, ThreatFinding{
						Category:  tp.category,
						Severity:  tp.severity,
						FilePath:  c.Path,
						Line:      p.SourceLine,
						Primitive: p.Name,
						Detail:    tp.detail,
					})
				}
			}

			// Also run secret scanner on primitive values.
			scanResult := ScanForSecrets(content)
			if scanResult.HasSecrets {
				for _, det := range scanResult.Detections {
					report.Findings = append(report.Findings, ThreatFinding{
						Category:  "SECRET",
						Severity:  "CRITICAL",
						FilePath:  c.Path,
						Line:      p.SourceLine,
						Primitive: p.Name,
						Detail:    det,
					})
				}
			}
		}
	}

	// Correlate with L1-L2 facts for architectural context.
	if factStore != nil {
		l1facts, _ := factStore.ListByLevel(ctx, memory.LevelDomain)
		l2facts, _ := factStore.ListByLevel(ctx, memory.LevelModule)
		report.FactsCorrelated = len(l1facts) + len(l2facts)

		// Cross-reference: findings in files mentioned by facts.
		factPaths := make(map[string]bool)
		for _, f := range l1facts {
			if f.CodeRef != "" {
				parts := strings.SplitN(f.CodeRef, ":", 2)
				factPaths[parts[0]] = true
			}
		}
		for _, f := range l2facts {
			if f.CodeRef != "" {
				parts := strings.SplitN(f.CodeRef, ":", 2)
				factPaths[parts[0]] = true
			}
		}

		// Boost severity of findings in documented files.
		for i := range report.Findings {
			if factPaths[report.Findings[i].FilePath] {
				report.Findings[i].Detail += " [IN_DOCUMENTED_MODULE]"
			}
		}
	}

	return report, nil
}

// EncryptReport encrypts report data using a key derived from genome hash + mode.
// Key = SHA-256(genomeHash + "ZERO-G"). Without valid genome + active mode, decryption is impossible.
func EncryptReport(data []byte, genomeHash string) ([]byte, error) {
	key := deriveKey(genomeHash)
	block, err := aes.NewCipher(key)
	if err != nil {
		return nil, fmt.Errorf("aes cipher: %w", err)
	}

	aesGCM, err := cipher.NewGCM(block)
	if err != nil {
		return nil, fmt.Errorf("gcm: %w", err)
	}

	nonce := make([]byte, aesGCM.NonceSize())
	if _, err := io.ReadFull(rand.Reader, nonce); err != nil {
		return nil, fmt.Errorf("nonce: %w", err)
	}

	return aesGCM.Seal(nonce, nonce, data, nil), nil
}

// DecryptReport decrypts data encrypted by EncryptReport.
func DecryptReport(ciphertext []byte, genomeHash string) ([]byte, error) {
	key := deriveKey(genomeHash)
	block, err := aes.NewCipher(key)
	if err != nil {
		return nil, fmt.Errorf("aes cipher: %w", err)
	}

	aesGCM, err := cipher.NewGCM(block)
	if err != nil {
		return nil, fmt.Errorf("gcm: %w", err)
	}

	nonceSize := aesGCM.NonceSize()
	if len(ciphertext) < nonceSize {
		return nil, fmt.Errorf("ciphertext too short")
	}

	nonce, ciphertext := ciphertext[:nonceSize], ciphertext[nonceSize:]
	return aesGCM.Open(nil, nonce, ciphertext, nil)
}

func deriveKey(genomeHash string) []byte {
	h := sha256.Sum256([]byte(genomeHash + "ZERO-G"))
	return h[:]
}
