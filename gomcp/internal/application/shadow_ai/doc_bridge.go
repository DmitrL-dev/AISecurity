package shadow_ai

import (
	"crypto/sha256"
	"fmt"
	"regexp"
	"strings"
	"sync"
	"time"
)

// --- Document Review Bridge ---
// Controlled gateway for AI access: scans documents for secrets and PII,
// supports content redaction, and routes through the approval workflow.

// DocReviewStatus tracks the lifecycle of a document review.
type DocReviewStatus string

const (
	DocReviewPending   DocReviewStatus = "pending"
	DocReviewScanning  DocReviewStatus = "scanning"
	DocReviewClean     DocReviewStatus = "clean"
	DocReviewRedacted  DocReviewStatus = "redacted"
	DocReviewBlocked   DocReviewStatus = "blocked"
	DocReviewApproved  DocReviewStatus = "approved"
)

// ScanResult contains the results of scanning a document.
type ScanResult struct {
	DocumentID  string        `json:"document_id"`
	Status      DocReviewStatus `json:"status"`
	PIIFound    []PIIMatch    `json:"pii_found,omitempty"`
	SecretsFound []SecretMatch `json:"secrets_found,omitempty"`
	DataClass   DataClassification `json:"data_classification"`
	ContentHash string        `json:"content_hash"`
	ScannedAt   time.Time     `json:"scanned_at"`
	SizeBytes   int           `json:"size_bytes"`
}

// PIIMatch represents a detected PII pattern in content.
type PIIMatch struct {
	Type     string `json:"type"`      // "email", "phone", "ssn", "credit_card", "passport"
	Location int    `json:"location"`  // Character offset
	Length   int    `json:"length"`
	Masked   string `json:"masked"`    // Redacted value, e.g., "j***@example.com"
}

// SecretMatch represents a detected secret/API key in content.
type SecretMatch struct {
	Type     string `json:"type"`      // "api_key", "password", "token", "private_key"
	Location int    `json:"location"`
	Length   int    `json:"length"`
	Provider string `json:"provider"`  // "OpenAI", "AWS", "GitHub", etc.
}

// DocBridge manages document scanning, redaction, and review workflow.
type DocBridge struct {
	mu             sync.RWMutex
	reviews        map[string]*ScanResult
	piiPatterns    []*piiPattern
	secretPats     []secretPattern // Cached compiled patterns
	signatures     *AISignatureDB  // Reused across scans
	maxDocSize     int             // bytes
}

type piiPattern struct {
	name    string
	regex   *regexp.Regexp
	maskFn  func(string) string
}

// NewDocBridge creates a new Document Review Bridge.
func NewDocBridge() *DocBridge {
	return &DocBridge{
		reviews:    make(map[string]*ScanResult),
		piiPatterns: defaultPIIPatterns(),
		secretPats:  secretPatterns(),
		signatures:  NewAISignatureDB(),
		maxDocSize:  10 * 1024 * 1024, // 10 MB
	}
}

// ScanDocument scans content for PII and secrets, classifies data, returns result.
func (db *DocBridge) ScanDocument(docID, content, userID string) *ScanResult {
	result := &ScanResult{
		DocumentID: docID,
		Status:     DocReviewScanning,
		ScannedAt:  time.Now(),
		SizeBytes:  len(content),
	}

	// Content hash for dedup.
	h := sha256.Sum256([]byte(content))
	result.ContentHash = fmt.Sprintf("%x", h[:])

	// Size check.
	if len(content) > db.maxDocSize {
		result.Status = DocReviewBlocked
		result.DataClass = DataCritical
		db.store(result)
		return result
	}

	// Scan for PII.
	result.PIIFound = db.scanPII(content)

	// Scan for secrets (reuse cached signature DB).
	if keyType := db.signatures.ScanForAPIKeys(content); keyType != "" {
		result.SecretsFound = append(result.SecretsFound, SecretMatch{
			Type:     "api_key",
			Provider: keyType,
		})
	}

	// Scan for additional secret patterns.
	result.SecretsFound = append(result.SecretsFound, db.scanSecrets(content)...)

	// Classify data based on findings.
	result.DataClass = db.classifyData(result)

	// Set status based on findings.
	if db.signatures.ScanForInjection(content) {
		result.Status = DocReviewBlocked
		result.DataClass = DataCritical
	} else if len(result.SecretsFound) > 0 {
		result.Status = DocReviewBlocked
	} else if len(result.PIIFound) > 0 {
		result.Status = DocReviewRedacted
	} else {
		result.Status = DocReviewClean
	}

	db.store(result)
	return result
}

// RedactContent replaces PII and secrets in content with masked values.
func (db *DocBridge) RedactContent(content string) string {
	for _, p := range db.piiPatterns {
		content = p.regex.ReplaceAllStringFunc(content, p.maskFn)
	}

	// Redact common secret patterns (cached).
	for _, sp := range db.secretPats {
		content = sp.regex.ReplaceAllString(content, sp.replacement)
	}

	return content
}

// GetReview returns a scan result by document ID.
func (db *DocBridge) GetReview(docID string) (*ScanResult, bool) {
	db.mu.RLock()
	defer db.mu.RUnlock()
	r, ok := db.reviews[docID]
	if !ok {
		return nil, false
	}
	cp := *r
	return &cp, true
}

// RecentReviews returns the N most recent reviews.
func (db *DocBridge) RecentReviews(limit int) []ScanResult {
	db.mu.RLock()
	defer db.mu.RUnlock()

	results := make([]ScanResult, 0, len(db.reviews))
	for _, r := range db.reviews {
		results = append(results, *r)
	}

	// Sort by time desc (simple bubble for bounded set).
	for i := 0; i < len(results); i++ {
		for j := i + 1; j < len(results); j++ {
			if results[j].ScannedAt.After(results[i].ScannedAt) {
				results[i], results[j] = results[j], results[i]
			}
		}
	}

	if len(results) > limit {
		results = results[:limit]
	}
	return results
}

// Stats returns aggregate document review statistics.
func (db *DocBridge) Stats() map[string]int {
	db.mu.RLock()
	defer db.mu.RUnlock()

	stats := map[string]int{
		"total":    len(db.reviews),
		"clean":    0,
		"redacted": 0,
		"blocked":  0,
	}
	for _, r := range db.reviews {
		switch r.Status {
		case DocReviewClean:
			stats["clean"]++
		case DocReviewRedacted:
			stats["redacted"]++
		case DocReviewBlocked:
			stats["blocked"]++
		}
	}
	return stats
}

func (db *DocBridge) store(result *ScanResult) {
	db.mu.Lock()
	defer db.mu.Unlock()
	db.reviews[result.DocumentID] = result
}

// scanPII runs all PII patterns against content.
func (db *DocBridge) scanPII(content string) []PIIMatch {
	var matches []PIIMatch
	for _, p := range db.piiPatterns {
		locs := p.regex.FindAllStringIndex(content, -1)
		for _, loc := range locs {
			matched := content[loc[0]:loc[1]]
			matches = append(matches, PIIMatch{
				Type:     p.name,
				Location: loc[0],
				Length:   loc[1] - loc[0],
				Masked:   p.maskFn(matched),
			})
		}
	}
	return matches
}

// scanSecrets scans for common secret patterns beyond AI API keys.
func (db *DocBridge) scanSecrets(content string) []SecretMatch {
	var matches []SecretMatch
	for _, sp := range db.secretPats {
		locs := sp.regex.FindAllStringIndex(content, -1)
		for _, loc := range locs {
			matches = append(matches, SecretMatch{
				Type:     sp.secretType,
				Location: loc[0],
				Length:   loc[1] - loc[0],
				Provider: sp.provider,
			})
		}
	}
	return matches
}

// classifyData determines the data classification level based on scan results.
func (db *DocBridge) classifyData(result *ScanResult) DataClassification {
	if len(result.SecretsFound) > 0 {
		return DataCritical
	}

	hasSensitivePII := false
	for _, pii := range result.PIIFound {
		switch pii.Type {
		case "ssn", "credit_card", "passport":
			return DataCritical
		case "email", "phone":
			hasSensitivePII = true
		}
	}

	if hasSensitivePII {
		return DataConfidential
	}

	if result.SizeBytes > 1024*1024 { // >1MB
		return DataInternal
	}

	return DataPublic
}

// --- PII Patterns ---

func defaultPIIPatterns() []*piiPattern {
	return []*piiPattern{
		{
			name:  "email",
			regex: regexp.MustCompile(`[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}`),
			maskFn: func(s string) string {
				parts := strings.SplitN(s, "@", 2)
				if len(parts) != 2 {
					return "***@***"
				}
				if len(parts[0]) <= 1 {
					return "*@" + parts[1]
				}
				return string(parts[0][0]) + "***@" + parts[1]
			},
		},
		{
			name:  "phone",
			regex: regexp.MustCompile(`\+?[1-9]\d{0,2}[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2,4}`),
			maskFn: func(s string) string {
				if len(s) < 4 {
					return "***"
				}
				return s[:2] + strings.Repeat("*", len(s)-4) + s[len(s)-2:]
			},
		},
		{
			name:  "ssn",
			regex: regexp.MustCompile(`\b\d{3}-\d{2}-\d{4}\b`),
			maskFn: func(_ string) string {
				return "***-**-****"
			},
		},
		{
			name:  "credit_card",
			regex: regexp.MustCompile(`\b(?:\d{4}[\s\-]?){3}\d{4}\b`),
			maskFn: func(s string) string {
				clean := strings.ReplaceAll(strings.ReplaceAll(s, "-", ""), " ", "")
				if len(clean) < 4 {
					return "****"
				}
				return strings.Repeat("*", len(clean)-4) + clean[len(clean)-4:]
			},
		},
		{
			name:  "passport",
			regex: regexp.MustCompile(`\b[A-Z]{1,2}\d{6,9}\b`),
			maskFn: func(s string) string {
				if len(s) <= 2 {
					return "**"
				}
				return s[:2] + strings.Repeat("*", len(s)-2)
			},
		},
	}
}

type secretPattern struct {
	secretType  string
	provider    string
	regex       *regexp.Regexp
	replacement string
}

func secretPatterns() []secretPattern {
	return []secretPattern{
		{secretType: "aws_key", provider: "AWS", regex: regexp.MustCompile(`AKIA[0-9A-Z]{16}`), replacement: "[AWS_KEY_REDACTED]"},
		{secretType: "github_token", provider: "GitHub", regex: regexp.MustCompile(`ghp_[a-zA-Z0-9]{36}`), replacement: "[GITHUB_TOKEN_REDACTED]"},
		{secretType: "github_token", provider: "GitHub", regex: regexp.MustCompile(`github_pat_[a-zA-Z0-9_]{82}`), replacement: "[GITHUB_PAT_REDACTED]"},
		{secretType: "slack_token", provider: "Slack", regex: regexp.MustCompile(`xoxb-[0-9]{10,13}-[0-9]{10,13}-[a-zA-Z0-9]{24}`), replacement: "[SLACK_TOKEN_REDACTED]"},
		{secretType: "private_key", provider: "Generic", regex: regexp.MustCompile(`-----BEGIN (?:RSA |EC |DSA )?PRIVATE KEY-----`), replacement: "[PRIVATE_KEY_REDACTED]"},
		{secretType: "password", provider: "Generic", regex: regexp.MustCompile(`(?i)password\s*[=:]\s*['"]?[^\s'"]{8,}`), replacement: "[PASSWORD_REDACTED]"},
		{secretType: "connection_string", provider: "Database", regex: regexp.MustCompile(`(?i)(?:mysql|postgres|mongodb)://[^\s]+`), replacement: "[DB_CONN_REDACTED]"},
	}
}
