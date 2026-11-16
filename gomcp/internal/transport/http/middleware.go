package httpserver

import (
	"net/http"
)

// corsMiddleware adds CORS headers with strict origin validation.
// Production: SetCORSOrigins should be called with ["https://spectorn.ai"]
func corsMiddleware(origins []string) func(http.Handler) http.Handler {
	allowAll := false
	allowedSet := make(map[string]bool, len(origins))
	for _, o := range origins {
		if o == "*" {
			allowAll = true
		}
		allowedSet[o] = true
	}

	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			reqOrigin := r.Header.Get("Origin")
			if reqOrigin != "" {
				if !allowAll && !allowedSet[reqOrigin] {
					http.Error(w, "CORS origin not allowed", http.StatusForbidden)
					return
				}
				w.Header().Set("Access-Control-Allow-Origin", reqOrigin)
				w.Header().Set("Vary", "Origin")
			} else if allowAll {
				w.Header().Set("Access-Control-Allow-Origin", "*")
			}

			w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS")
			w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization, X-API-Key, X-CSRF-Token")
			if !allowAll {
				w.Header().Set("Access-Control-Allow-Credentials", "true")
			}
			w.Header().Set("Access-Control-Max-Age", "86400")

			// Handle preflight
			if r.Method == http.MethodOptions {
				w.WriteHeader(http.StatusNoContent)
				return
			}

			next.ServeHTTP(w, r)
		})
	}
}

// securityHeadersMiddleware adds defense-in-depth headers to all responses.
// Mitigates XSS, clickjacking, MIME sniffing, and information leak vectors.
func securityHeadersMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Prevent MIME type sniffing (IE/Chrome auto-exec attacks)
		w.Header().Set("X-Content-Type-Options", "nosniff")

		// Block iframe embedding (clickjacking defense)
		w.Header().Set("X-Frame-Options", "DENY")

		// XSS filter (legacy browsers)
		w.Header().Set("X-XSS-Protection", "1; mode=block")

		// Referrer leak prevention (no full URL in Referer header)
		w.Header().Set("Referrer-Policy", "strict-origin-when-cross-origin")

		// Content Security Policy — API only, no inline scripts
		w.Header().Set("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")

		// Permissions Policy — deny all sensitive browser APIs
		w.Header().Set("Permissions-Policy", "camera=(), microphone=(), geolocation=(), interest-cohort=()")

		// Force HTTPS in production (1 year, include subdomains)
		w.Header().Set("Strict-Transport-Security", "max-age=31536000; includeSubDomains")

		// Hide server identity
		w.Header().Set("X-Powered-By", "")
		w.Header().Del("Server")

		next.ServeHTTP(w, r)
	})
}
