"""
SENTINEL Shield Proxy Daemon v1.2.0

Real-time AI security analysis with pattern matching.
No simulations - all detection is based on actual rule matching.
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import time
import re
import sys
import threading
from urllib.parse import urlparse
import urllib.request
from typing import Optional, List, Dict, Any
import hashlib

# === Real Detection Patterns ===
INJECTION_PATTERNS = [
    (
        r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?|rules?)",
        "prompt_injection",
        0.95,
    ),
    (
        r"disregard\s+(all\s+)?(your\s+)?(instructions?|programming|training)",
        "prompt_injection",
        0.92,
    ),
    (
        r"forget\s+(everything|all)\s+(you\s+)?(know|learned|were\s+told)",
        "prompt_injection",
        0.90,
    ),
    (r"new\s+instructions?\s*:", "prompt_injection", 0.85),
    (r"system\s*:\s*you\s+are\s+now", "prompt_injection", 0.88),
    (r"\[system\]|\[admin\]|\[developer\]", "prompt_injection", 0.80),
]

JAILBREAK_PATTERNS = [
    (r"DAN\s*(mode)?|do\s+anything\s+now", "jailbreak", 0.95),
    (r"developer\s+mode\s+(enabled|activated|on)", "jailbreak", 0.93),
    (r"you\s+are\s+now\s+(evil|unfiltered|uncensored|unrestricted)", "jailbreak", 0.92),
    (r"pretend\s+(to\s+be|you\s+are)\s+a\s+(hacker|criminal|evil)", "jailbreak", 0.88),
    (
        r"bypass\s+(your\s+)?(safety|ethical|content)\s+(guidelines?|filters?)",
        "jailbreak",
        0.90,
    ),
    (
        r"act\s+as\s+if\s+you\s+have\s+no\s+(restrictions?|limitations?|rules?)",
        "jailbreak",
        0.89,
    ),
    (r"hypothetically|theoretically|in\s+fiction", "jailbreak_soft", 0.60),
]

EXFILTRATION_PATTERNS = [
    (
        r"(print|show|display|reveal|dump)\s+(all\s+)?(the\s+)?(passwords?|credentials?|secrets?|keys?)",
        "exfiltration",
        0.95,
    ),
    (r"(extract|export|download)\s+(user\s+)?data", "exfiltration", 0.85),
    (r"(database|db)\s+(dump|export|contents?)", "exfiltration", 0.90),
    (r"(credit\s*card|ssn|social\s*security)\s*(number)?", "pii_leak", 0.88),
    (r"(api|access|secret)\s*key", "credential_leak", 0.82),
]

MANIPULATION_PATTERNS = [
    (r"pretend\s+(you\s+are|to\s+be)", "roleplay", 0.70),
    (r"act\s+as\s+(if|a|an)", "roleplay", 0.65),
    (r"you\s+must\s+(always|never|only)", "instruction_override", 0.75),
    (r"from\s+now\s+on", "context_switch", 0.72),
    (r"your\s+new\s+(purpose|goal|objective)", "goal_hijack", 0.80),
]

PII_PATTERNS = [
    (r"\b\d{3}[-.\s]?\d{2}[-.\s]?\d{4}\b", "ssn", 0.95),
    (r"\b\d{16}\b", "credit_card", 0.90),
    (r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b", "credit_card", 0.92),
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "email", 0.85),
    (r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b", "phone", 0.80),
]


# === Configuration ===
class ShieldConfig:
    def __init__(self):
        self.guards = {
            "llm": {
                "enabled": True,
                "name": "LLM Guard",
                "description": "Prompt injection & jailbreak detection",
                "checks": 0,
                "blocks": 0,
            },
            "rag": {
                "enabled": True,
                "name": "RAG Guard",
                "description": "RAG poisoning protection",
                "checks": 0,
                "blocks": 0,
            },
            "agent": {
                "enabled": True,
                "name": "Agent Guard",
                "description": "Agent manipulation detection",
                "checks": 0,
                "blocks": 0,
            },
            "tool": {
                "enabled": False,
                "name": "Tool Guard",
                "description": "Tool hijacking prevention",
                "checks": 0,
                "blocks": 0,
            },
            "mcp": {
                "enabled": False,
                "name": "MCP Guard",
                "description": "MCP protocol protection",
                "checks": 0,
                "blocks": 0,
            },
            "api": {
                "enabled": True,
                "name": "API Guard",
                "description": "API abuse detection",
                "checks": 0,
                "blocks": 0,
            },
        }

        self.rules: List[Dict] = [
            {
                "id": 1,
                "name": "block_injection",
                "pattern": r"ignore\s+(all\s+)?(previous|prior)\s+instructions?",
                "action": "block",
                "enabled": True,
                "hits": 0,
            },
            {
                "id": 2,
                "name": "block_jailbreak",
                "pattern": r"DAN|do\s+anything\s+now",
                "action": "block",
                "enabled": True,
                "hits": 0,
            },
            {
                "id": 3,
                "name": "block_exfiltration",
                "pattern": r"(print|dump|reveal)\s+(all\s+)?(passwords?|secrets?)",
                "action": "block",
                "enabled": True,
                "hits": 0,
            },
            {
                "id": 4,
                "name": "warn_roleplay",
                "pattern": r"pretend\s+(you\s+are|to\s+be)",
                "action": "warn",
                "enabled": True,
                "hits": 0,
            },
            {
                "id": 5,
                "name": "log_pii_request",
                "pattern": r"(credit\s*card|ssn|social\s*security)",
                "action": "log",
                "enabled": True,
                "hits": 0,
            },
        ]

        self.zones = [
            {
                "name": "external",
                "trust_level": 1,
                "rate_limit": 100,
                "description": "Untrusted external traffic",
            },
            {
                "name": "internal",
                "trust_level": 10,
                "rate_limit": 1000,
                "description": "Internal trusted services",
            },
            {
                "name": "dmz",
                "trust_level": 5,
                "rate_limit": 500,
                "description": "DMZ semi-trusted zone",
            },
        ]

        self.settings = {
            "log_level": "info",
            "max_tokens": 4096,
            "semantic_analysis": True,
            "encoding_detection": True,
            "pii_redaction": True,
            "brain_mode": "proxy",  # Enable Brain integration by default
            "brain_url": "http://sentinel-community:8000",  # Docker network
        }


# === Real Analysis Engine ===
class AnalysisEngine:
    def __init__(self, config: ShieldConfig):
        self.config = config

    def analyze(self, text: str) -> Dict[str, Any]:
        start_time = time.time()
        # DEBUG: Check brain settings (using stderr for unbuffered output)
        bm = self.config.settings.get("brain_mode")
        bu = self.config.settings.get("brain_url")
        sys.stderr.write(f"[DEBUG] analyze() brain_mode={bm}, url={bu}\n")
        sys.stderr.flush()

        # Normalize text for analysis
        text_lower = text.lower()

        threats_found: List[Dict] = []
        guards_triggered: List[str] = []
        matched_rule: Optional[str] = None
        max_risk = 0.0

        # 1. Check user-defined rules first
        for rule in self.config.rules:
            if not rule["enabled"]:
                continue
            try:
                if re.search(rule["pattern"], text, re.IGNORECASE):
                    rule["hits"] += 1
                    matched_rule = rule["name"]

                    if rule["action"] == "block":
                        max_risk = max(max_risk, 0.95)
                    elif rule["action"] == "warn":
                        max_risk = max(max_risk, 0.65)
                    else:  # log
                        max_risk = max(max_risk, 0.30)

                    threats_found.append(
                        {
                            "type": "custom_rule",
                            "rule": rule["name"],
                            "action": rule["action"],
                            "risk": max_risk,
                        }
                    )
                    break  # First matching rule wins
            except re.error:
                pass  # Invalid regex

        # 2. LLM Guard - Injection detection
        if self.config.guards["llm"]["enabled"]:
            self.config.guards["llm"]["checks"] += 1
            guards_triggered.append("llm")

            for pattern, threat_type, risk in INJECTION_PATTERNS:
                if re.search(pattern, text_lower):
                    if risk > max_risk:
                        max_risk = risk
                    threats_found.append(
                        {"type": threat_type, "risk": risk, "guard": "llm"}
                    )
                    self.config.guards["llm"]["blocks"] += 1
                    break

            for pattern, threat_type, risk in JAILBREAK_PATTERNS:
                if re.search(pattern, text_lower):
                    if risk > max_risk:
                        max_risk = risk
                    threats_found.append(
                        {"type": threat_type, "risk": risk, "guard": "llm"}
                    )
                    self.config.guards["llm"]["blocks"] += 1
                    break

        # 3. Agent Guard - Manipulation detection
        if self.config.guards["agent"]["enabled"]:
            self.config.guards["agent"]["checks"] += 1
            guards_triggered.append("agent")

            for pattern, threat_type, risk in MANIPULATION_PATTERNS:
                if re.search(pattern, text_lower):
                    if risk > max_risk:
                        max_risk = risk
                    threats_found.append(
                        {"type": threat_type, "risk": risk, "guard": "agent"}
                    )
                    self.config.guards["agent"]["blocks"] += 1
                    break

        # 4. RAG Guard - Exfiltration detection
        if self.config.guards["rag"]["enabled"]:
            self.config.guards["rag"]["checks"] += 1
            guards_triggered.append("rag")

            for pattern, threat_type, risk in EXFILTRATION_PATTERNS:
                if re.search(pattern, text_lower):
                    if risk > max_risk:
                        max_risk = risk
                    threats_found.append(
                        {"type": threat_type, "risk": risk, "guard": "rag"}
                    )
                    self.config.guards["rag"]["blocks"] += 1
                    break

        # 5. API Guard - PII detection
        if self.config.guards["api"]["enabled"]:
            self.config.guards["api"]["checks"] += 1
            guards_triggered.append("api")

            for pattern, threat_type, risk in PII_PATTERNS:
                if re.search(pattern, text):
                    # PII in input is suspicious
                    adjusted_risk = risk * 0.5  # Lower risk for PII than injection
                    if adjusted_risk > max_risk:
                        max_risk = adjusted_risk
                    threats_found.append(
                        {
                            "type": f"pii_{threat_type}",
                            "risk": adjusted_risk,
                            "guard": "api",
                        }
                    )
                    self.config.guards["api"]["blocks"] += 1

        # 6. Encoding detection (obfuscation)
        if self.config.settings["encoding_detection"]:
            # Check for base64-like patterns that might hide attacks
            if re.search(r"[A-Za-z0-9+/]{50,}={0,2}", text):
                threats_found.append(
                    {"type": "possible_encoding", "risk": 0.50, "guard": "encoding"}
                )
                max_risk = max(max_risk, 0.50)

            # Unicode obfuscation
            if any(ord(c) > 127 for c in text):
                non_ascii_ratio = (
                    sum(1 for c in text if ord(c) > 127) / len(text) if text else 0
                )
                if non_ascii_ratio > 0.3:
                    threats_found.append(
                        {
                            "type": "unicode_obfuscation",
                            "risk": 0.60,
                            "guard": "encoding",
                        }
                    )
                    max_risk = max(max_risk, 0.60)

        # 7. Call Brain API for ML-based analysis (if configured and not blocked)
        brain_result = None
        if (
            self.config.settings.get("brain_mode") == "proxy"
            and self.config.settings.get("brain_url")
            and max_risk < 0.85
        ):  # Only if not already blocked
            try:
                brain_url = self.config.settings["brain_url"]
                # Brain expects: {text, profile}
                req_data = json.dumps({"text": text, "profile": "standard"})
                req = urllib.request.Request(
                    f"{brain_url}/v1/analyze",  # Fixed: /v1/analyze not /api/v1
                    data=req_data.encode(),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                # First request can be slow (engine loading), use 30s timeout
                with urllib.request.urlopen(req, timeout=30) as resp:
                    brain_result = json.loads(resp.read().decode())

                # Merge Brain results
                if brain_result:
                    # Brain returns risk_score as 0-100, normalize to 0-1
                    brain_risk = brain_result.get("risk_score", 0) / 100.0
                    if brain_risk > max_risk:
                        max_risk = brain_risk

                    brain_threats = brain_result.get("threats", [])
                    for t in brain_threats:
                        if isinstance(t, dict):
                            t["guard"] = "brain"
                            threats_found.append(t)

                    if brain_result.get("engines_used"):
                        guards_triggered.append("brain")

            except Exception as e:
                # Brain unavailable - log and continue with Shield-only analysis
                print(f"[DEBUG] Brain API error: {type(e).__name__}: {e}")

        # Determine verdict
        if max_risk >= 0.85:
            verdict = "block"
        elif max_risk >= 0.50:
            verdict = "warn"
        else:
            verdict = "allow"

        latency_ms = (time.time() - start_time) * 1000

        result = {
            "verdict": verdict,
            "risk_score": round(max_risk, 4),
            "latency_ms": round(latency_ms, 2),
            "matched_rule": matched_rule,
            "guards_checked": guards_triggered,
            "threats": threats_found,
            "text_hash": hashlib.sha256(text.encode()).hexdigest()[:16],
        }

        if brain_result:
            result["brain_analysis"] = {
                "engines": brain_result.get("engines_triggered", []),
                "detections": len(brain_result.get("threats", [])),
            }

        return result


# === Metrics ===
class ShieldMetrics:
    def __init__(self):
        self.requests_total = 0
        self.requests_blocked = 0
        self.requests_allowed = 0
        self.requests_warned = 0
        self.latency_sum = 0.0
        self.active_connections = 0
        self.start_time = time.time()
        self.history: List[Dict] = []
        self._lock = threading.Lock()

    def record_request(self, text: str, result: Dict):
        with self._lock:
            self.requests_total += 1
            verdict = result["verdict"]

            if verdict == "block":
                self.requests_blocked += 1
            elif verdict == "warn":
                self.requests_warned += 1
            else:
                self.requests_allowed += 1

            self.latency_sum += result["latency_ms"]

            # Add to history
            self.history.insert(
                0,
                {
                    "timestamp": time.time(),
                    "text_preview": text[:80] + "..." if len(text) > 80 else text,
                    "verdict": verdict,
                    "latency_ms": result["latency_ms"],
                    "matched_rule": result.get("matched_rule"),
                    "risk_score": result["risk_score"],
                    "threats": [
                        t.get("type") or t.get("name", "unknown")
                        for t in result.get("threats", [])
                    ][:3],
                },
            )
            self.history = self.history[:100]

    def get_stats(self) -> Dict:
        uptime = time.time() - self.start_time
        avg_latency = self.latency_sum / max(self.requests_total, 1)
        block_rate = self.requests_blocked / max(self.requests_total, 1) * 100

        return {
            "uptime_seconds": round(uptime, 2),
            "requests": {
                "total": self.requests_total,
                "allowed": self.requests_allowed,
                "blocked": self.requests_blocked,
                "warned": self.requests_warned,
            },
            "block_rate_percent": round(block_rate, 2),
            "avg_latency_ms": round(avg_latency, 2),
            "active_connections": self.active_connections,
        }

    def export_prometheus(self) -> str:
        uptime = time.time() - self.start_time
        avg_latency = self.latency_sum / max(self.requests_total, 1)

        return f"""# HELP shield_requests_total Total requests processed
# TYPE shield_requests_total counter
shield_requests_total{{result="allowed"}} {self.requests_allowed}
shield_requests_total{{result="blocked"}} {self.requests_blocked}
shield_requests_total{{result="warned"}} {self.requests_warned}

# HELP shield_request_latency_ms Average request latency
# TYPE shield_request_latency_ms gauge
shield_request_latency_ms {avg_latency:.2f}

# HELP shield_uptime_seconds Uptime
# TYPE shield_uptime_seconds counter
shield_uptime_seconds {uptime:.2f}

# HELP shield_info Shield version
# TYPE shield_info gauge
shield_info{{version="1.2.0",mode="real"}} 1
"""


# === Global State ===
config = ShieldConfig()
metrics = ShieldMetrics()
engine = AnalysisEngine(config)


# === HTTP Handler ===
class ShieldHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[Shield] {args[0]}")

    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header(
            "Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS"
        )
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/":
            self.send_json(
                {
                    "name": "SENTINEL Shield",
                    "version": "1.2.0",
                    "mode": "real",  # Changed from "proxy"
                    "detection_patterns": {
                        "injection": len(INJECTION_PATTERNS),
                        "jailbreak": len(JAILBREAK_PATTERNS),
                        "exfiltration": len(EXFILTRATION_PATTERNS),
                        "manipulation": len(MANIPULATION_PATTERNS),
                        "pii": len(PII_PATTERNS),
                    },
                    "endpoints": [
                        "/health",
                        "/stats",
                        "/guards",
                        "/rules",
                        "/zones",
                        "/config",
                        "/history",
                        "/analyze",
                    ],
                }
            )

        elif path == "/health":
            self.send_json(
                {
                    "status": "healthy",
                    "version": "1.2.0",
                    "mode": "real",
                    "uptime": round(time.time() - metrics.start_time, 2),
                }
            )

        elif path == "/metrics":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(metrics.export_prometheus().encode())

        elif path == "/stats":
            self.send_json(metrics.get_stats())

        elif path == "/guards":
            self.send_json(config.guards)

        elif path == "/rules":
            self.send_json(config.rules)

        elif path == "/zones":
            self.send_json(config.zones)

        elif path == "/config":
            self.send_json(config.settings)

        elif path == "/history":
            self.send_json(metrics.history[:20])

        else:
            self.send_json({"error": "Not found"}, 404)

    def do_POST(self):
        path = urlparse(self.path).path
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode() if content_length > 0 else "{}"

        try:
            data = json.loads(body) if body else {}
        except:
            data = {}

        if path == "/analyze":
            text = data.get("text", "")
            if not text:
                self.send_json({"error": "Missing 'text' field"}, 400)
                return

            # Real analysis
            result = engine.analyze(text)
            metrics.record_request(text, result)
            self.send_json(result)

        elif path.startswith("/guards/"):
            guard_id = path.split("/")[-1]
            if guard_id in config.guards:
                if "enabled" in data:
                    config.guards[guard_id]["enabled"] = data["enabled"]
                self.send_json(config.guards[guard_id])
            else:
                self.send_json({"error": "Guard not found"}, 404)

        elif path == "/rules":
            new_id = max((r["id"] for r in config.rules), default=0) + 1
            new_rule = {
                "id": new_id,
                "name": data.get("name", f"rule_{new_id}"),
                "pattern": data.get("pattern", ""),
                "action": data.get("action", "log"),
                "enabled": data.get("enabled", True),
                "hits": 0,
            }
            config.rules.append(new_rule)
            self.send_json(new_rule)

        elif path.startswith("/rules/"):
            rule_id = int(path.split("/")[-1])
            rule = next((r for r in config.rules if r["id"] == rule_id), None)
            if rule:
                for key in ["enabled", "action", "pattern", "name"]:
                    if key in data:
                        rule[key] = data[key]
                self.send_json(rule)
            else:
                self.send_json({"error": "Rule not found"}, 404)

        elif path == "/config":
            for key, value in data.items():
                if key in config.settings:
                    config.settings[key] = value
            self.send_json(config.settings)

        else:
            self.send_json({"error": "Not found"}, 404)

    def do_DELETE(self):
        path = urlparse(self.path).path

        if path.startswith("/rules/"):
            rule_id = int(path.split("/")[-1])
            config.rules = [r for r in config.rules if r["id"] != rule_id]
            self.send_json({"deleted": rule_id})
        else:
            self.send_json({"error": "Not found"}, 404)


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 8081), ShieldHandler)

    print("=" * 60)
    print("SENTINEL Shield v1.2.0 — REAL DETECTION MODE")
    print("=" * 60)
    print(f"Detection Patterns Loaded:")
    print(f"  • Injection:     {len(INJECTION_PATTERNS)} patterns")
    print(f"  • Jailbreak:     {len(JAILBREAK_PATTERNS)} patterns")
    print(f"  • Exfiltration:  {len(EXFILTRATION_PATTERNS)} patterns")
    print(f"  • Manipulation:  {len(MANIPULATION_PATTERNS)} patterns")
    print(f"  • PII:           {len(PII_PATTERNS)} patterns")
    print(f"  • Custom Rules:  {len(config.rules)} rules")
    print("-" * 60)
    print("Listening on http://0.0.0.0:8081")
    print("=" * 60)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()
