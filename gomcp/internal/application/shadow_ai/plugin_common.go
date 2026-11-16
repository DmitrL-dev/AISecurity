package shadow_ai

import (
	"errors"
	"fmt"
	"log/slog"
	"net/http"
	"net/url"
	"strings"

	socdomain "github.com/syntrex/gomcp/internal/domain/soc"
)

// validateVendorURL fail-fasts on a bad scheme or an SSRF target that resolves to
// an internal/loopback/link-local IP. A pure DNS-resolution failure is downgraded
// to a warning (the vendor host may simply be unreachable from this box at config
// time) — the load-bearing protection is socdomain.SafeDialContext, which
// re-resolves and pins the IP on EVERY actual request and cannot be bypassed.
func validateVendorURL(logger *slog.Logger, rawURL string) error {
	u, err := url.Parse(rawURL)
	if err != nil {
		return fmt.Errorf("invalid URL")
	}
	if u.Scheme != "http" && u.Scheme != "https" {
		return fmt.Errorf("ssrf blocked: invalid scheme %q", u.Scheme)
	}
	if err := socdomain.ValidateWebhookURL(rawURL); err != nil {
		// An explicit SSRF block (resolved to an illegal IP) is fatal; a mere
		// resolution failure is not (SafeDialContext still guards every request).
		if strings.Contains(err.Error(), "illegal target") {
			return err
		}
		if logger != nil {
			logger.Warn("vendor URL not resolvable at init; SSRF still enforced at dial time", "url", rawURL, "detail", err.Error())
		}
	}
	return nil
}

// cfgString safely extracts a string value from an untyped plugin config map.
// Missing keys and non-string values yield "".
func cfgString(config map[string]interface{}, key string) string {
	if config == nil {
		return ""
	}
	if v, ok := config[key].(string); ok {
		return strings.TrimSpace(v)
	}
	return ""
}

// sanitizeName turns an arbitrary domain/IP into a stable, vendor-object-safe
// name fragment (alphanumerics, dash, underscore, dot).
func sanitizeName(s string) string {
	var b strings.Builder
	for _, r := range s {
		switch {
		case r >= 'a' && r <= 'z', r >= 'A' && r <= 'Z', r >= '0' && r <= '9',
			r == '-', r == '_', r == '.':
			b.WriteRune(r)
		default:
			b.WriteRune('_')
		}
	}
	return b.String()
}

// vendorHTTPError represents a non-2xx response from a vendor API, retaining the
// status code (for auth-retry decisions) and a snippet of the body (for logs).
type vendorHTTPError struct {
	status int
	body   string
}

func (e *vendorHTTPError) Error() string {
	body := e.body
	const max = 512
	if len(body) > max {
		body = body[:max] + "...(truncated)"
	}
	return fmt.Sprintf("vendor API returned %d: %s", e.status, body)
}

// isAuthError reports whether err is a vendor 401 Unauthorized (or 403), which
// callers use to trigger a single re-authentication + retry.
func isAuthError(err error) bool {
	var ve *vendorHTTPError
	if errors.As(err, &ve) {
		return ve.status == http.StatusUnauthorized || ve.status == http.StatusForbidden
	}
	return false
}

// asVendorErr unwraps err into a *vendorHTTPError, returning true on success.
func asVendorErr(err error, target **vendorHTTPError) bool {
	return errors.As(err, target)
}
