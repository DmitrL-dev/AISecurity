package oracle

import (
	"fmt"
	"regexp"
	"strings"

	"github.com/syntrex/gomcp/internal/domain/entropy"
)

// SecretScanResult holds the result of scanning content for secrets.
type SecretScanResult struct {
	HasSecrets   bool     `json:"has_secrets"`
	Detections   []string `json:"detections,omitempty"`
	MaxEntropy   float64  `json:"max_entropy"`
	LineCount    int      `json:"line_count"`
	ScannerRules int      `json:"scanner_rules"`
}

// Common secret patterns (regex).
var secretPatterns = []*regexp.Regexp{
	regexp.MustCompile(`(?i)(api[_-]?key|apikey)\s*[:=]\s*['"]?([a-zA-Z0-9_\-]{20,})['"]?`),
	regexp.MustCompile(`(?i)(secret|token|password|passwd|pwd)\s*[:=]\s*['"]?([^\s'"]{8,})['"]?`),
	regexp.MustCompile(`(?i)(bearer|authorization)\s+[a-zA-Z0-9_\-.]{20,}`),
	regexp.MustCompile(`(?i)-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----`),
	regexp.MustCompile(`(?i)(aws_access_key_id|aws_secret_access_key)\s*=\s*[A-Za-z0-9/+=]{16,}`),
	regexp.MustCompile(`ghp_[a-zA-Z0-9]{36}`),                       // GitHub PAT
	regexp.MustCompile(`sk-[a-zA-Z0-9]{32,}`),                       // OpenAI key
	regexp.MustCompile(`(?i)(mongodb|postgres|mysql)://[^\s]{10,}`), // DB connection strings
}

const (
	// Lines with entropy above this threshold are suspicious.
	lineEntropyThreshold = 4.5

	// Minimum line length to check (short lines can have high entropy naturally).
	minLineLength = 20
)

// ScanForSecrets checks content for high-entropy strings and known secret patterns.
// Returns a result indicating whether secrets were detected.
func ScanForSecrets(content string) *SecretScanResult {
	result := &SecretScanResult{
		ScannerRules: len(secretPatterns),
	}

	lines := strings.Split(content, "\n")
	result.LineCount = len(lines)

	// Pass 1: Pattern matching.
	for _, pattern := range secretPatterns {
		if matches := pattern.FindStringSubmatch(content); len(matches) > 0 {
			result.HasSecrets = true
			match := matches[0]
			if len(match) > 30 {
				match = match[:15] + "***REDACTED***"
			}
			result.Detections = append(result.Detections, "PATTERN: "+match)
		}
	}

	// Pass 2: Entropy-based detection on individual lines.
	for i, line := range lines {
		line = strings.TrimSpace(line)
		if len(line) < minLineLength {
			continue
		}

		// Skip comments.
		if strings.HasPrefix(line, "//") || strings.HasPrefix(line, "#") ||
			strings.HasPrefix(line, "*") || strings.HasPrefix(line, "/*") {
			continue
		}

		ent := entropy.ShannonEntropy(line)
		if ent > result.MaxEntropy {
			result.MaxEntropy = ent
		}

		if ent > lineEntropyThreshold {
			result.HasSecrets = true
			// SEC (pre-launch audit 18.06): NEVER echo the secret. Show only a short
			// fixed prefix + length regardless of line length — the old >40 gate left
			// short high-entropy secrets logged whole, and longer ones leaked 20 chars.
			prefix := line
			if len(prefix) > 4 {
				prefix = prefix[:4]
			}
			result.Detections = append(result.Detections,
				fmt.Sprintf("ENTROPY: line %d (%.2f bits/char, len=%d, prefix=%q ***REDACTED***)", i+1, ent, len(line), prefix))
		}
	}

	return result
}
