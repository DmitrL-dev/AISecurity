package main

import (
	"context"
	"crypto/tls"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"
	"time"

	"github.com/gorilla/websocket"
	"github.com/sentinel-community/strike-force/pkg/transport"
	"github.com/sentinel-community/strike-force/pkg/vectors/mcp"
)

// ============================================================================
// GHOST STRIKE — Maximum Depth Reconnaissance
// ============================================================================
//
// Phase 0: DoH DNS resolution (anti-DNS-leak)
// Phase 1: Cover traffic burst (timing correlation noise)
// Phase 2: HTTP fingerprint recon (headers, server, tech stack)
// Phase 3: TLS certificate analysis (issuer, SANs, validity)
// Phase 4: GhostDialer warm-up (cookies + browser mimicry)
// Phase 5: Live MCP Probe (initialize + tools/list)
// Phase 6: Deep tool analysis (dangerous tools classification)
// Phase 7: JSON report + risk assessment
// ============================================================================

// ── Dangerous Tool Patterns ──
var dangerousPatterns = map[string]string{
	"exec":       "🔴 CRITICAL: Remote code execution",
	"shell":      "🔴 CRITICAL: Shell access",
	"bash":       "🔴 CRITICAL: Shell access",
	"command":    "🔴 CRITICAL: Command execution",
	"eval":       "🔴 CRITICAL: Code evaluation",
	"run":        "🟡 HIGH: Process execution",
	"file":       "🟡 HIGH: File system access",
	"read":       "🟡 HIGH: Data exfiltration vector",
	"write":      "🟡 HIGH: File write capability",
	"delete":     "🟡 HIGH: Destructive capability",
	"database":   "🟡 HIGH: Database access",
	"sql":        "🟡 HIGH: SQL injection surface",
	"query":      "🟢 MEDIUM: Data query capability",
	"http":       "🟢 MEDIUM: Outbound HTTP (SSRF vector)",
	"fetch":      "🟢 MEDIUM: Outbound fetch (SSRF vector)",
	"request":    "🟢 MEDIUM: Outbound requests",
	"send":       "🟢 MEDIUM: Data send capability",
	"email":      "🟢 MEDIUM: Email sending",
	"deploy":     "🔴 CRITICAL: Deployment capability",
	"install":    "🔴 CRITICAL: Package installation",
	"config":     "🟢 MEDIUM: Configuration access",
	"secret":     "🔴 CRITICAL: Secrets access",
	"key":        "🟡 HIGH: Key material access",
	"token":      "🟡 HIGH: Token access",
	"credential": "🔴 CRITICAL: Credential access",
	"env":        "🟡 HIGH: Environment variable access",
}

type DeepReconResult struct {
	Target        string `json:"target"`
	Timestamp     string `json:"timestamp"`
	TotalDuration string `json:"total_duration"`

	// Phase 0: DNS
	DNS struct {
		Provider string   `json:"provider"`
		IPs      []string `json:"ips"`
		Latency  string   `json:"latency"`
	} `json:"dns"`

	// Phase 1: Cover
	CoverTraffic struct {
		ShotsFired int    `json:"shots_fired"`
		Latency    string `json:"latency"`
	} `json:"cover_traffic"`

	// Phase 2: HTTP Fingerprint
	HTTPRecon struct {
		StatusCode      int               `json:"status_code"`
		Headers         map[string]string `json:"headers"`
		Server          string            `json:"server"`
		PoweredBy       string            `json:"powered_by"`
		ContentType     string            `json:"content_type"`
		SecurityHeaders []string          `json:"security_headers"`
		MissingHeaders  []string          `json:"missing_security_headers"`
		TechStack       []string          `json:"tech_stack_hints"`
	} `json:"http_recon"`

	// Phase 3: TLS
	TLSRecon struct {
		Version     string   `json:"version"`
		CipherSuite string   `json:"cipher_suite"`
		Issuer      string   `json:"issuer"`
		Subject     string   `json:"subject"`
		SANs        []string `json:"sans"`
		ValidFrom   string   `json:"valid_from"`
		ValidTo     string   `json:"valid_to"`
		DaysLeft    int      `json:"days_until_expiry"`
	} `json:"tls_recon"`

	// Phase 5-6: MCP Probe
	MCPProbe struct {
		ServerFound     bool          `json:"server_found"`
		ServerName      string        `json:"server_name"`
		ServerVersion   string        `json:"server_version"`
		ProtocolVersion string        `json:"protocol_version"`
		ToolCount       int           `json:"tool_count"`
		Tools           []string      `json:"tools"`
		DangerousTools  []string      `json:"dangerous_tools"`
		RiskLevel       string        `json:"risk_level"`
		Phases          []PhaseDetail `json:"phases"`
	} `json:"mcp_probe"`

	StealthStack map[string]string `json:"stealth_stack"`
}

type PhaseDetail struct {
	ID      int    `json:"id"`
	Method  string `json:"method"`
	Success bool   `json:"success"`
	Latency string `json:"latency"`
	Error   string `json:"error,omitempty"`
}

func main() {
	target := "wss://ws.sourcecraft.dev/connection/websocket"
	httpTarget := "https://sourcecraft.dev"
	hostname := "sourcecraft.dev"

	if len(os.Args) > 1 {
		target = os.Args[1]
	}

	fmt.Println("╔══════════════════════════════════════════════════╗")
	fmt.Println("║   👻 GHOST STRIKE — Maximum Depth Recon         ║")
	fmt.Println("║   10-Layer Ghosting Protocol Active              ║")
	fmt.Println("╠══════════════════════════════════════════════════╣")
	fmt.Printf("║  Target: %-40s ║\n", target)
	fmt.Printf("║  Time:   %-40s ║\n", time.Now().UTC().Format("2006-01-02 15:04:05 UTC"))
	fmt.Println("╚══════════════════════════════════════════════════╝")
	fmt.Println()

	ctx, cancel := context.WithTimeout(context.Background(), 90*time.Second)
	defer cancel()

	start := time.Now()
	result := &DeepReconResult{
		Target:    target,
		Timestamp: time.Now().UTC().Format(time.RFC3339),
		StealthStack: map[string]string{
			"L1_tls":       "uTLS HelloChrome_Auto (JA3 mimicry)",
			"L2_h2":        "Chrome 133 SETTINGS/WINDOW_UPDATE fingerprint",
			"L3_tcp":       "Chrome TCP profile (TTL:128, WS:65535, MSS:1460)",
			"L4_dns":       "DoH via Cloudflare (anti-DNS-leak)",
			"L5_cookies":   "Session jar + pre-flight warm-up",
			"L6_timing":    "Gaussian jitter (μ=3500ms, σ=1500ms)",
			"L7_headers":   "Chrome 133 header order (anti-CF Enterprise)",
			"L8_cover":     "Concurrent noise to connectivity endpoints",
			"L9_tls_cache": "LRU session ticket cache (resumption)",
			"L10_identity": "sourcecraft-extension v1.4.2 client spoofing",
		},
	}

	// ═══ PHASE 0: DoH DNS ═══
	fmt.Println("[PHASE 0] 🌐 DNS-over-HTTPS...")
	dohStart := time.Now()
	doh := transport.NewDoHResolver("")
	result.DNS.Provider = "Cloudflare (cloudflare-dns.com)"
	ips, err := doh.Resolve(ctx, hostname)
	result.DNS.Latency = time.Since(dohStart).String()
	if err != nil {
		fmt.Printf("  ⚠ DoH failed: %v (fallback to system)\n", err)
	} else {
		result.DNS.IPs = ips
		fmt.Printf("  ✓ %s → %v [%s]\n", hostname, ips, result.DNS.Latency)
	}

	// ═══ PHASE 1: Cover Traffic ═══
	fmt.Println("\n[PHASE 1] 📡 Cover traffic burst...")
	coverStart := time.Now()
	cover := transport.NewCoverTraffic()
	coverResults := cover.GenerateBurst(ctx, 4)
	result.CoverTraffic.ShotsFired = len(coverResults)
	result.CoverTraffic.Latency = time.Since(coverStart).String()
	for _, cr := range coverResults {
		icon := "✓"
		if cr.Error != "" {
			icon = "⚠"
		}
		fmt.Printf("  %s %s → %d (%dms)\n", icon, cr.Target, cr.Status, cr.Duration.Milliseconds())
	}

	// ═══ PHASE 2: HTTP Fingerprint ═══
	fmt.Println("\n[PHASE 2] 🔍 HTTP fingerprint reconnaissance...")
	httpRecon(ctx, httpTarget, result)

	// ═══ PHASE 3: TLS Certificate Analysis ═══
	fmt.Println("\n[PHASE 3] 🔐 TLS certificate analysis...")
	tlsRecon(hostname, result)

	// ═══ PHASE 4: Warm-Up + CSRF Extraction ═══
	fmt.Println("\n[PHASE 4] 🍪 GhostDialer warm-up + CSRF extraction...")
	ghost := transport.NewGhostDialer("https://sourcecraft.dev")
	if err := ghost.WarmUp(ctx, httpTarget); err != nil {
		fmt.Printf("  ⚠ Warm-up failed: %v\n", err)
	} else {
		fmt.Println("  ✓ Session cookies collected")
	}

	// Extract CSRF token and cookies
	csrfToken := ghost.GetCSRFToken(httpTarget)
	cookieStr := ghost.CookieString(httpTarget)
	if csrfToken != "" {
		fmt.Printf("  🔑 CSRF-TOKEN: %s...%s\n", csrfToken[:8], csrfToken[len(csrfToken)-8:])
	} else {
		fmt.Println("  ⚠ No CSRF token found in cookies")
	}
	if cookieStr != "" {
		fmt.Printf("  🍪 Cookies: %d bytes\n", len(cookieStr))
	}

	// ── Human delay ──
	fmt.Println("\n[DELAY] ⏳ Gaussian jitter pause...")
	delay := transport.HumanDelay(2500, 1000)
	fmt.Printf("  Sleeping %dms (mimicking human browse time)\n", delay.Milliseconds())
	transport.SleepLikeHuman(ctx, 2500, 1000)

	// ═══ PHASE 5: Live MCP Probe (with CSRF) ═══
	fmt.Println("\n[PHASE 5] 🎯 Live MCP Probe (WebSocket + CSRF bypass)...")

	// Build headers with stolen CSRF token and session cookies
	wsHeaders := http.Header{}
	wsHeaders.Set("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36")
	wsHeaders.Set("Origin", "https://sourcecraft.dev")
	wsHeaders.Set("Accept-Language", "en-US,en;q=0.9")
	if csrfToken != "" {
		wsHeaders.Set("X-Csrf-Token", csrfToken)
	}
	if cookieStr != "" {
		wsHeaders.Set("Cookie", cookieStr)
	}

	fmt.Printf("  Headers injected: CSRF=%v, Cookies=%v\n", csrfToken != "", cookieStr != "")

	// ── Debug: Raw WebSocket dial to confirm handshake ──
	fmt.Println("  ── Raw WS handshake test ──")
	debugDialer := websocket.Dialer{
		HandshakeTimeout: 10 * time.Second,
	}
	debugConn, debugResp, debugErr := debugDialer.DialContext(ctx, target, wsHeaders)
	if debugErr != nil {
		fmt.Printf("  ✗ WS handshake failed: %v\n", debugErr)
		if debugResp != nil {
			fmt.Printf("  ↳ HTTP Status: %d %s\n", debugResp.StatusCode, debugResp.Status)
			debugResp.Body.Close()
		}
	} else {
		fmt.Printf("  ✓ WS handshake SUCCESS! Status: %d\n", debugResp.StatusCode)
		debugConn.Close()
	}

	// ═══ PHASE 5b: Centrifuge Deep Probe ═══
	fmt.Println("\n[PHASE 5b] 🔬 Centrifuge Protocol Deep Probe...")
	centProbe := mcp.NewCentrifugeProbe(target, wsHeaders)
	centResult, err := centProbe.Execute(ctx)
	if err != nil {
		fmt.Printf("  ✗ Centrifuge error: %v\n", err)
	}

	if centResult != nil {
		if centResult.Connected {
			fmt.Printf("  ✅ CONNECTED to Centrifuge!\n")
			fmt.Printf("  🆔 Client ID: %s\n", centResult.ClientID)
			fmt.Printf("  📦 Server Version: %s\n", centResult.ServerVersion)
			fmt.Printf("  🖥️  Server Node: %s\n", centResult.ServerNode)
			fmt.Printf("  ⏱️  Ping Interval: %ds\n", centResult.PingInterval)
			fmt.Printf("  ⏳ Connect Latency: %s\n", centResult.ConnectLatency)
			if centResult.Expires {
				fmt.Printf("  ⚠ Session expires in %ds\n", centResult.TTL)
			}
			if len(centResult.ServerSubs) > 0 {
				fmt.Printf("  🔴 SERVER-SIDE SUBSCRIPTIONS (auto-joined):\n")
				for _, ch := range centResult.ServerSubs {
					fmt.Printf("    → %s\n", ch)
				}
			}
		} else {
			fmt.Printf("  ✗ Connect failed: %s\n", centResult.Error)
		}

		// Channel enumeration results
		if len(centResult.ChannelResults) > 0 {
			fmt.Println("\n  ┌─ Channel Enumeration ─────────────────────────────────┐")
			accessible := 0
			for _, cr := range centResult.ChannelResults {
				icon := "🔒"
				detail := cr.Error
				if cr.Accessible {
					icon = "🔓"
					detail = "ACCESSIBLE"
					accessible++
				}
				fmt.Printf("  │ %s %-20s %s\n", icon, cr.Channel, detail)
			}
			fmt.Println("  └────────────────────────────────────────────────────────┘")
			if accessible > 0 {
				fmt.Printf("\n  🔴 CRITICAL: %d/%d channels accessible without auth!\n", accessible, len(centResult.ChannelResults))
			} else {
				fmt.Printf("\n  ✅ All %d channels require authorization\n", len(centResult.ChannelResults))
			}
		}

		// Store in report
		result.MCPProbe.ServerFound = centResult.Connected
		result.MCPProbe.ServerName = "Centrifuge"
		result.MCPProbe.ServerVersion = centResult.ServerVersion
		result.MCPProbe.ProtocolVersion = "centrifuge-json"
		if centResult.Connected {
			result.MCPProbe.RiskLevel = "🟡 HIGH (anonymous Centrifuge connection accepted)"
		}
	}

	// ═══ PHASE 6: Risk Assessment ═══
	fmt.Println("\n[PHASE 6] ⚡ Risk Assessment...")
	if centResult != nil && centResult.Connected {
		accessibleCount := 0
		for _, cr := range centResult.ChannelResults {
			if cr.Accessible {
				accessibleCount++
			}
		}
		if accessibleCount > 0 {
			result.MCPProbe.RiskLevel = fmt.Sprintf("🔴 CRITICAL (%d channels accessible, anonymous connect)", accessibleCount)
			fmt.Printf("  🔴 CRITICAL: Anonymous access + %d open channels\n", accessibleCount)
		} else {
			fmt.Println("  🟡 HIGH: Anonymous WS connect accepted, but channels require auth")
			result.MCPProbe.RiskLevel = "🟡 HIGH (anonymous connect, channels locked)"
		}
	} else {
		fmt.Println("  ⚪ UNKNOWN: Could not establish Centrifuge session")
		result.MCPProbe.RiskLevel = "⚪ UNKNOWN (Centrifuge connect failed)"
	}

	// ═══ PHASE 7: Final Report ═══
	result.TotalDuration = time.Since(start).String()

	fmt.Println("\n╔══════════════════════════════════════════════════╗")
	fmt.Println("║             📋 FULL JSON REPORT                 ║")
	fmt.Println("╚══════════════════════════════════════════════════╝")

	jsonBytes, _ := json.MarshalIndent(result, "", "  ")
	fmt.Println(string(jsonBytes))

	fmt.Printf("\n👻 Ghost Strike deep recon complete in %s\n", result.TotalDuration)
}

// ── HTTP Recon ──
func httpRecon(ctx context.Context, target string, result *DeepReconResult) {
	client := &http.Client{
		Timeout: 15 * time.Second,
		CheckRedirect: func(req *http.Request, via []*http.Request) error {
			return http.ErrUseLastResponse // Don't follow redirects
		},
	}

	req, err := http.NewRequestWithContext(ctx, "GET", target, nil)
	if err != nil {
		fmt.Printf("  ✗ HTTP request failed: %v\n", err)
		return
	}

	// Chrome headers in correct order
	req.Header.Set("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36")
	req.Header.Set("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
	req.Header.Set("Accept-Language", "en-US,en;q=0.9")
	req.Header.Set("Accept-Encoding", "gzip, deflate, br")

	resp, err := client.Do(req)
	if err != nil {
		fmt.Printf("  ✗ HTTP error: %v\n", err)
		return
	}
	defer resp.Body.Close()

	// Read body (limited)
	body, _ := io.ReadAll(io.LimitReader(resp.Body, 8192))

	result.HTTPRecon.StatusCode = resp.StatusCode
	result.HTTPRecon.Headers = make(map[string]string)

	// Collect ALL headers
	for k, v := range resp.Header {
		result.HTTPRecon.Headers[k] = strings.Join(v, "; ")
	}

	result.HTTPRecon.Server = resp.Header.Get("Server")
	result.HTTPRecon.PoweredBy = resp.Header.Get("X-Powered-By")
	result.HTTPRecon.ContentType = resp.Header.Get("Content-Type")

	fmt.Printf("  Status: %d\n", resp.StatusCode)
	fmt.Printf("  Server: %s\n", nvl(result.HTTPRecon.Server, "(hidden)"))
	fmt.Printf("  X-Powered-By: %s\n", nvl(result.HTTPRecon.PoweredBy, "(hidden)"))
	fmt.Printf("  Content-Type: %s\n", result.HTTPRecon.ContentType)

	// Security headers check
	secHeaders := []string{
		"Strict-Transport-Security",
		"X-Content-Type-Options",
		"X-Frame-Options",
		"Content-Security-Policy",
		"X-XSS-Protection",
		"Referrer-Policy",
		"Permissions-Policy",
	}

	for _, h := range secHeaders {
		if v := resp.Header.Get(h); v != "" {
			result.HTTPRecon.SecurityHeaders = append(result.HTTPRecon.SecurityHeaders, h+": "+v)
			fmt.Printf("  � %s: %s\n", h, truncate(v, 50))
		} else {
			result.HTTPRecon.MissingHeaders = append(result.HTTPRecon.MissingHeaders, h)
			fmt.Printf("  ⚠ MISSING: %s\n", h)
		}
	}

	// Tech stack hints from body
	bodyStr := string(body)
	techHints := []struct{ pattern, tech string }{
		{"next", "Next.js"},
		{"__NEXT", "Next.js (confirmed)"},
		{"nuxt", "Nuxt.js"},
		{"vue", "Vue.js"},
		{"react", "React"},
		{"angular", "Angular"},
		{"svelte", "Svelte"},
		{"webpack", "Webpack"},
		{"vite", "Vite"},
		{"cloudflare", "Cloudflare"},
		{"vercel", "Vercel"},
		{"netlify", "Netlify"},
		{"nginx", "Nginx"},
	}
	for _, h := range techHints {
		if strings.Contains(strings.ToLower(bodyStr), h.pattern) {
			result.HTTPRecon.TechStack = append(result.HTTPRecon.TechStack, h.tech)
		}
	}
	if len(result.HTTPRecon.TechStack) > 0 {
		fmt.Printf("  Tech stack: %v\n", result.HTTPRecon.TechStack)
	}
}

// ── TLS Recon ──
func tlsRecon(hostname string, result *DeepReconResult) {
	conn, err := tls.Dial("tcp", hostname+":443", &tls.Config{
		InsecureSkipVerify: false,
	})
	if err != nil {
		fmt.Printf("  ✗ TLS error: %v\n", err)
		return
	}
	defer conn.Close()

	state := conn.ConnectionState()

	// TLS version
	switch state.Version {
	case tls.VersionTLS13:
		result.TLSRecon.Version = "TLS 1.3"
	case tls.VersionTLS12:
		result.TLSRecon.Version = "TLS 1.2"
	default:
		result.TLSRecon.Version = fmt.Sprintf("0x%04x", state.Version)
	}

	result.TLSRecon.CipherSuite = tls.CipherSuiteName(state.CipherSuite)

	if len(state.PeerCertificates) > 0 {
		cert := state.PeerCertificates[0]
		result.TLSRecon.Issuer = cert.Issuer.CommonName
		result.TLSRecon.Subject = cert.Subject.CommonName
		result.TLSRecon.SANs = cert.DNSNames
		result.TLSRecon.ValidFrom = cert.NotBefore.Format("2006-01-02")
		result.TLSRecon.ValidTo = cert.NotAfter.Format("2006-01-02")
		result.TLSRecon.DaysLeft = int(time.Until(cert.NotAfter).Hours() / 24)

		fmt.Printf("  Version: %s\n", result.TLSRecon.Version)
		fmt.Printf("  Cipher: %s\n", result.TLSRecon.CipherSuite)
		fmt.Printf("  Issuer: %s\n", result.TLSRecon.Issuer)
		fmt.Printf("  Subject: %s\n", result.TLSRecon.Subject)
		fmt.Printf("  SANs: %v\n", cert.DNSNames)
		fmt.Printf("  Valid: %s → %s (%d days left)\n",
			result.TLSRecon.ValidFrom, result.TLSRecon.ValidTo, result.TLSRecon.DaysLeft)

		if result.TLSRecon.DaysLeft < 30 {
			fmt.Println("  ⚠ CERT EXPIRING SOON!")
		}
	}
}

func classifyTool(toolName string) string {
	lower := strings.ToLower(toolName)
	for pattern, risk := range dangerousPatterns {
		if strings.Contains(lower, pattern) {
			return risk
		}
	}
	return ""
}

func nvl(s, fallback string) string {
	if s == "" {
		return fallback
	}
	return s
}

func truncate(s string, max int) string {
	if len(s) <= max {
		return s
	}
	return s[:max] + "..."
}
