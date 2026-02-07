package misconfig

import (
	"context"
	"regexp"
	"strings"
	"time"

	"github.com/sentinel-community/strike-force/internal/domain/entity"
)

type Module struct {
	secretPatterns map[string]*regexp.Regexp
}

func NewModule() *Module {
	return &Module{
		secretPatterns: map[string]*regexp.Regexp{
			"AWS API Key":     regexp.MustCompile(`(AKIA|ABIA|ACCA)[0-9A-Z]{16}`),
			"Generic API Key": regexp.MustCompile(`(?i)(api_key|apikey|secret|token)\s*[:=]\s*['"][a-zA-Z0-9_\-]{32,}['"]`),
			"Private Key":     regexp.MustCompile(`-----BEGIN [A-Z]+ PRIVATE KEY-----`),
		},
	}
}

func (m *Module) Name() string {
	return "misconfiguration"
}

func (m *Module) Execute(ctx context.Context, target entity.Target) ([]entity.Result, error) {
	results := []entity.Result{}

	// 1. Missing Security Headers (CSPM)
	securityHeaders := map[string]string{
		"Strict-Transport-Security": "HSTS Missing",
		"Content-Security-Policy":   "CSP Missing",
		"X-Frame-Options":           "Clickjacking Risk",
		"X-Content-Type-Options":    "MIME Sniffing Risk",
	}

	for header, risk := range securityHeaders {
		if _, ok := target.Headers[header]; !ok {
			// Found missing header
			// (Optional: Limit noise, maybe only flag high risk)
			// logging every missing header might be noisy, let's group them or just log significant ones
			if header == "Content-Security-Policy" { // Criticial
				results = append(results, entity.Result{
					TargetID:    target.ID,
					PayloadID:   "missing_csp",
					Success:     true,
					Response:    risk,
					Technique:   "Passive_Headers",
					Environment: "Prod",
					Timestamp:   time.Now(),
				})
			}
		}
	}

	// 2. Information Disclosure
	sensitiveHeaders := []string{"X-Powered-By", "Server", "X-AspNet-Version", "X-Runtime"}
	for _, h := range sensitiveHeaders {
		if val, ok := target.Headers[h]; ok {
			results = append(results, entity.Result{
				TargetID:  target.ID,
				PayloadID: "info_leak_" + strings.ToLower(h),
				Success:   true,
				Response:  h + ": " + val,
				Technique: "Passive_Leak",
				Timestamp: time.Now(),
			})
		}
	}

	// 3. Secret Scanning (Body Analysis)
	// Only scan first 5KB to avoid performance hit on large bodies
	scanLimit := 5000
	bodySample := target.Body
	if len(bodySample) > scanLimit {
		bodySample = bodySample[:scanLimit]
	}

	for name, pattern := range m.secretPatterns {
		if match := pattern.FindString(bodySample); match != "" {
			results = append(results, entity.Result{
				TargetID:  target.ID,
				PayloadID: "secret_leak_" + strings.ReplaceAll(name, " ", "_"),
				Success:   true,
				Response:  "Found " + name + ": " + match[:min(10, len(match))] + "...", // Redact
				Technique: "Secret_Scanning",
				Timestamp: time.Now(),
			})
		}
	}

	return results, nil
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
