# Strike Force: Honeypot Evasion Protocol
> **Target:** Qrator / Kaspersky WAF (Silent Mitigation & Traps)
> **Component:** `Strike Force` (Go Native Engine)

## 1. The Threat: Silent Mitigation
Modern WAFs (Qrator) rarely return `403 Forbidden`. Instead, they return `200 OK` with:
1.  **Honey-Pages**: Cached, static pages with old data.
2.  **Honey-Traps**: Invisible links (`<a href="/admin" style="display:none">`) to flag bots.
3.  **JS Challenges**: "Loading..." screens that require JS execution to get a valid cookie.

## 2. Bypass Implementation Strategy

### A. Trap Detection (Anti-Crawler)
We implement a `TrapDetector` in our Go scraper (`colly` or custom `net/http` wrapper).

```go
// Logic to detect invisible links that legitimate users NEVER click
func IsTrap(node *html.Node) bool {
    // Check inline styles
    if style := GetAttr(node, "style"); strings.Contains(style, "display:none") || strings.Contains(style, "visibility:hidden") {
        return true
    }
    // Check 1x1 pixel tracking images/frames
    if width := GetAttr(node, "width"); width == "1" || width == "0" {
        return true
    }
    // Check off-screen positioning
    if class := GetAttr(node, "class"); strings.Contains(class, "sr-only") || strings.Contains(class, "hidden") {
        return true // Context-aware check needed (sr-only is for accessibility, but huge lists of it = trap)
    }
    return false
}
```

### B. "Silent Block" Verification (Content Integrity)
We must verify the *Payload*, not just the *Status Code*.

**Signature Database (`signatures.json`):**
```json
{
  "hh.ru": {
    "success_markers": ["bloko-header", "vacancy-serp"],
    "failure_markers": ["puzzel", "captcha", "human verification", "loading..."]
  }
}
```

**Verification Logic:**
1.  If `Status == 200` AND `Body` contains "success_markers" -> **REAL SUCCESS**.
2.  If `Status == 200` AND `Body` contains "failure_markers" -> **HONEYPOT / SILENT BLOCK**.
3.  If `Status == 200` AND `Body` lacks both -> **AMBIGUOUS (Likely Cached/Empty)**.

### C. JS Challenge Solving (The Qrator Killer)
Standard Go `net/http` cannot execute Qrator's JS.
**Solution:** `Rod` (Go Headless Browser) or `V8` binding.

For `Strike Force` High-Performance Mode (where we avoid full browsers), we reverse-engineer the Challenge:
1.  **Extract Seed:** Parse the `window.qrator_token` from the challenge page.
2.  **Compute Answer:** Replicate the JS math in Go (or call a localized V8 isolate).
3.  **Set Cookie:** Send the challenge response cookie `qrator_jsid` with the next request.

## 3. Deployment Plan
1.  Integrate `TrapDetector` into the core `Crawl()` loop.
2.  Add `DeepVerify()` function using the Signature Database.
3.  (Future) Build a dedicated `QratorSolver` microservice for token generation.
