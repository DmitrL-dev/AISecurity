package takeover

import (
	"context"
	"fmt"
	"net"
	"net/url"
	"strings"
	"time"

	"github.com/sentinel-community/strike-force/internal/domain/entity"
)

type Module struct {
	fingerprints map[string]string
}

func NewModule() *Module {
	return &Module{
		// CNAME suffix -> Service Name
		fingerprints: map[string]string{
			"s3.amazonaws.com":  "Amazon S3",
			"herokuapp.com":     "Heroku",
			"github.io":         "GitHub Pages",
			"azurewebsites.net": "Azure",
			"cloudapp.net":      "Azure",
			"readme.io":         "Readme.io",
			"pantheon.io":       "Pantheon",
			"tumblr.com":        "Tumblr",
			"wordpress.com":     "WordPress",
			"teamwork.com":      "Teamwork",
			"helpjuice.com":     "Helpjuice",
			"helpscoutdocs.com": "HelpScout",
			"ghost.io":          "Ghost",
			"cargo.site":        "Cargo",
			"usertrust.com":     "UserTrust",
			"surge.sh":          "Surge.sh",
			"bitbucket.io":      "Bitbucket",
			"netlify.com":       "Netlify",
			"zendesk.com":       "Zendesk",
			"fastly.net":        "Fastly",
			"myshopify.com":     "Shopify",
		},
	}
}

func (m *Module) Name() string {
	return "subdomain_takeover"
}

func (m *Module) Execute(ctx context.Context, target entity.Target) ([]entity.Result, error) {
	results := []entity.Result{}

	// 1. Parse Hostname
	u, err := url.Parse(target.URL)
	if err != nil {
		return nil, fmt.Errorf("failed to parse URL: %w", err)
	}
	host := u.Hostname()

	// 2. Perform DNS CNAME Lookup
	cname, err := net.LookupCNAME(host)
	if err != nil {
		// DNS errors are common, just log/ignore for scanning
		return results, nil
	}

	// net.LookupCNAME passes back fully qualified name (e.g., "target.com.")
	cname = strings.TrimSuffix(cname, ".")

	// 3. Match against fingerprints
	for signature, service := range m.fingerprints {
		if strings.Contains(cname, signature) {
			// Found potential takeover!
			// Now checks body for confirmation (Hybrid check)
			confidence := "Potential"
			details := fmt.Sprintf("CNAME points to %s (%s)", service, cname)

			// Simple body checks to increase confidence
			if strings.Contains(target.Body, "NoSuchBucket") ||
				strings.Contains(target.Body, "There is nothing here") ||
				strings.Contains(target.Body, "Site not found") {
				confidence = "High"
				details += " + Body Signature Match"
			}

			results = append(results, entity.Result{
				TargetID:    target.ID,
				PayloadID:   "takeover_" + service,
				Success:     true,
				Response:    details,
				Technique:   "DNS_CNAME",
				Environment: confidence, // Mapping Confidence to Environment field for now
				Timestamp:   time.Now(),
				StatusCode:  200, // Logical success
			})
			break // Found primary provider
		}
	}

	return results, nil
}
