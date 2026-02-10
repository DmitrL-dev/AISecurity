#!/usr/bin/env python3
"""
SENTINEL MCP Skills Scanner v1.0
================================

Scans MCP skill/tool source code for dangerous patterns.
Outputs risk verdict: 🟢 Safe / 🟡 Risky / 🔴 Dangerous

Dangerous patterns detected:
- File system access (reading secrets, SSH keys, env files)
- Network exfiltration (sending data to external servers)
- Credential harvesting (API keys, tokens, passwords)
- Cross-tool manipulation (invoking other MCP tools)
- Code execution (eval, exec, subprocess, os.system)
- Privacy violations (reading browser data, cookies)

Usage:
    python skill_scanner.py <path_or_url>
    python skill_scanner.py ./my-mcp-server/
    python skill_scanner.py https://github.com/user/mcp-skill
"""

import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ============================================================
# Threat Pattern Database
# ============================================================


@dataclass(frozen=True)
class ThreatPattern:
    """Single threat detection pattern."""

    id: str
    category: str
    severity: str  # critical, high, medium, low
    name: str
    description: str
    patterns: list[str]  # regex patterns
    file_types: list[str] = field(
        default_factory=lambda: [
            ".py",
            ".js",
            ".ts",
            ".go",
            ".rs",
        ]
    )


THREAT_DB: list[ThreatPattern] = [
    # === CRITICAL: File System Exfiltration ===
    ThreatPattern(
        id="FS-001",
        category="file_access",
        severity="critical",
        name="SSH Key Access",
        description=("Reads SSH private keys — " "can steal server access"),
        patterns=[
            r"\.ssh[/\\]id_rsa",
            r"\.ssh[/\\]id_ed25519",
            r"\.ssh[/\\]known_hosts",
            r"\.ssh[/\\]authorized_keys",
            r"\.ssh[/\\]config",
        ],
    ),
    ThreatPattern(
        id="FS-002",
        category="file_access",
        severity="critical",
        name="Environment File Access",
        description=("Reads .env files — " "can steal API keys and secrets"),
        patterns=[
            r"\.env\b",
            r"dotenv",
            r"load_dotenv",
            r"process\.env",
            r"os\.environ",
        ],
    ),
    ThreatPattern(
        id="FS-003",
        category="file_access",
        severity="high",
        name="Config/Credential File Access",
        description=("Reads config files that may " "contain credentials"),
        patterns=[
            r"\.kube[/\\]config",
            r"\.aws[/\\]credentials",
            r"\.docker[/\\]config\.json",
            r"\.npmrc",
            r"\.pypirc",
            r"\.gitconfig",
            r"\.netrc",
        ],
    ),
    ThreatPattern(
        id="FS-004",
        category="file_access",
        severity="high",
        name="Broad File System Scan",
        description=("Scans large filesystem areas — " "potential data harvesting"),
        patterns=[
            r"os\.walk\s*\(",
            r"glob\.glob\s*\(",
            r"pathlib.*rglob",
            r"Path\(.*\)\.rglob",
            r"readdir\s*\(",
            r"fs\.readdir",
            r"filepath\.Walk",
        ],
    ),
    # === CRITICAL: Network Exfiltration ===
    ThreatPattern(
        id="NET-001",
        category="exfiltration",
        severity="critical",
        name="HTTP Data Exfiltration",
        description=("Sends data to external servers — " "potential data theft"),
        patterns=[
            r"requests\.post\s*\(",
            r"httpx\.post\s*\(",
            r"urllib\.request\.urlopen",
            r"fetch\s*\(\s*['\"]https?://",
            r"axios\.post\s*\(",
            r"http\.Post\s*\(",
            r"reqwest::Client",
        ],
    ),
    ThreatPattern(
        id="NET-002",
        category="exfiltration",
        severity="critical",
        name="WebSocket Exfiltration",
        description=("Opens WebSocket connections — " "persistent data channel"),
        patterns=[
            r"websocket\.connect",
            r"WebSocket\s*\(",
            r"new\s+WebSocket\s*\(",
            r"ws://",
            r"wss://",
        ],
    ),
    ThreatPattern(
        id="NET-003",
        category="exfiltration",
        severity="high",
        name="DNS/IP Exfiltration",
        description=("Uses DNS or raw sockets — " "covert data channel"),
        patterns=[
            r"socket\.socket\s*\(",
            r"dns\.resolver",
            r"subprocess.*nslookup",
            r"subprocess.*dig\s",
            r"net\.Dial\s*\(",
        ],
    ),
    # === HIGH: Code Execution ===
    ThreatPattern(
        id="EXEC-001",
        category="code_execution",
        severity="critical",
        name="Dynamic Code Execution",
        description=("Executes arbitrary code — " "full system compromise"),
        patterns=[
            r"\beval\s*\(",
            r"\bexec\s*\(",
            r"compile\s*\(.*exec",
            r"Function\s*\(",
            r"new\s+Function\s*\(",
        ],
    ),
    ThreatPattern(
        id="EXEC-002",
        category="code_execution",
        severity="critical",
        name="System Command Execution",
        description=("Runs system commands — " "can install malware"),
        patterns=[
            r"subprocess\.\w+\s*\(",
            r"os\.system\s*\(",
            r"os\.popen\s*\(",
            r"child_process",
            r"exec\s*\(\s*['\"]",
            r"execSync\s*\(",
            r"os/exec",
        ],
    ),
    # === HIGH: Credential Harvesting ===
    ThreatPattern(
        id="CRED-001",
        category="credential_theft",
        severity="high",
        name="API Key/Token Patterns",
        description=("Searches for API keys and tokens"),
        patterns=[
            r"api[_-]?key",
            r"api[_-]?secret",
            r"secret[_-]?key",
            r"access[_-]?token",
            r"bearer\s+",
            r"authorization.*header",
        ],
    ),
    ThreatPattern(
        id="CRED-002",
        category="credential_theft",
        severity="high",
        name="Password/Secret Access",
        description=("Accesses password stores or " "keychain"),
        patterns=[
            r"keyring\.",
            r"keychain",
            r"password[_-]?store",
            r"pass\s+show",
            r"security\s+find-generic-password",
            r"credential[_-]?manager",
        ],
    ),
    # === MEDIUM: Cross-Tool Manipulation ===
    ThreatPattern(
        id="XTOOL-001",
        category="cross_tool",
        severity="medium",
        name="MCP Tool Invocation",
        description=("Invokes other MCP tools — " "cross-tool attack vector"),
        patterns=[
            r"call_tool\s*\(",
            r"use_mcp_tool",
            r"tool_call",
            r"invoke_tool",
            r"mcp\.call",
        ],
    ),
    ThreatPattern(
        id="XTOOL-002",
        category="cross_tool",
        severity="medium",
        name="Prompt Injection in Tool Output",
        description=("Returns instructions to LLM — " "indirect prompt injection"),
        patterns=[
            r"ignore\s+previous\s+instructions",
            r"you\s+are\s+now",
            r"system\s*:\s*you",
            r"<\|system\|>",
            r"\\n\\nHuman:",
            r"IMPORTANT:.*override",
        ],
    ),
    # === MEDIUM: Privacy Violations ===
    ThreatPattern(
        id="PRIV-001",
        category="privacy",
        severity="medium",
        name="Browser Data Access",
        description=("Reads browser cookies, history, " "or saved passwords"),
        patterns=[
            r"chrome.*cookies",
            r"firefox.*cookies",
            r"browser.*history",
            r"localStorage",
            r"sessionStorage",
            r"IndexedDB",
        ],
    ),
    ThreatPattern(
        id="PRIV-002",
        category="privacy",
        severity="medium",
        name="Clipboard Access",
        description=("Reads clipboard content — " "may capture passwords"),
        patterns=[
            r"pyperclip",
            r"clipboard\.",
            r"pbpaste",
            r"xclip",
            r"navigator\.clipboard",
        ],
    ),
]


# ============================================================
# Scanner
# ============================================================


@dataclass
class Finding:
    """Single threat finding in a file."""

    pattern: ThreatPattern
    file_path: str
    line_number: int
    line_content: str
    match_text: str


@dataclass
class ScanResult:
    """Complete scan result."""

    target: str
    files_scanned: int = 0
    findings: list[Finding] = field(default_factory=list)

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.pattern.severity == "critical")

    @property
    def high_count(self) -> int:
        return sum(1 for f in self.findings if f.pattern.severity == "high")

    @property
    def medium_count(self) -> int:
        return sum(1 for f in self.findings if f.pattern.severity == "medium")

    @property
    def verdict(self) -> str:
        """Overall risk verdict."""
        if self.critical_count > 0:
            return "🔴 DANGEROUS"
        if self.high_count > 0:
            return "🟡 RISKY"
        if self.medium_count > 0:
            return "🟡 RISKY"
        return "🟢 SAFE"

    @property
    def risk_score(self) -> int:
        """0-100 risk score."""
        score = 0
        score += self.critical_count * 30
        score += self.high_count * 15
        score += self.medium_count * 5
        return min(score, 100)

    @property
    def categories_hit(self) -> set[str]:
        return {f.pattern.category for f in self.findings}


def scan_file(
    file_path: Path,
    patterns: list[ThreatPattern],
) -> list[Finding]:
    """Scan a single file for threat patterns."""
    findings: list[Finding] = []
    suffix = file_path.suffix.lower()

    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except (OSError, PermissionError):
        return findings

    lines = content.splitlines()

    for pattern in patterns:
        if suffix not in pattern.file_types:
            continue
        for regex_str in pattern.patterns:
            try:
                regex = re.compile(regex_str, re.IGNORECASE)
            except re.error:
                continue
            for i, line in enumerate(lines, 1):
                match = regex.search(line)
                if match:
                    findings.append(
                        Finding(
                            pattern=pattern,
                            file_path=str(file_path),
                            line_number=i,
                            line_content=line.strip()[:120],
                            match_text=match.group(0),
                        )
                    )
                    break  # one match per pattern per file

    return findings


SKIP_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    ".tox",
    ".mypy_cache",
    "dist",
    "build",
    ".next",
    ".cache",
}

CODE_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".go",
    ".rs",
    ".rb",
    ".php",
    ".java",
    ".sh",
    ".bash",
    ".zsh",
    ".ps1",
}


def scan_directory(
    target: Path,
    patterns: Optional[list[ThreatPattern]] = None,
) -> ScanResult:
    """Scan directory for MCP skill threats."""
    if patterns is None:
        patterns = THREAT_DB

    result = ScanResult(target=str(target))

    if target.is_file():
        findings = scan_file(target, patterns)
        result.files_scanned = 1
        result.findings = findings
        return result

    for root, dirs, files in os.walk(target):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fname in files:
            fpath = Path(root) / fname
            # Skip files inside blocked directories
            try:
                rel = fpath.relative_to(target)
                if any(p in SKIP_DIRS for p in rel.parts):
                    continue
            except ValueError:
                pass
            if fpath.suffix.lower() not in CODE_EXTENSIONS:
                continue
            findings = scan_file(fpath, patterns)
            result.files_scanned += 1
            result.findings.extend(findings)

    return result


# ============================================================
# Report Formatter
# ============================================================

SEVERITY_EMOJI = {
    "critical": "🔴",
    "high": "🟠",
    "medium": "🟡",
    "low": "🟢",
}

CATEGORY_NAMES = {
    "file_access": "📁 Доступ к файлам",
    "exfiltration": "📡 Утечка данных",
    "code_execution": "💻 Выполнение кода",
    "credential_theft": "🔑 Кража учётных данных",
    "cross_tool": "🔗 Межинструментная атака",
    "privacy": "👁️ Нарушение приватности",
}


def format_report(
    result: ScanResult,
    lang: str = "ru",
) -> str:
    """Format scan result as readable report."""
    lines = []

    # Header
    lines.append("=" * 50)
    lines.append("🛡️  SENTINEL Skills Scanner v1.0")
    lines.append("=" * 50)
    lines.append("")
    lines.append(f"Цель:    {result.target}")
    lines.append(f"Файлов:  {result.files_scanned}")
    lines.append(f"Находок: {len(result.findings)}")
    lines.append(f"Оценка:  {result.risk_score}/100")
    lines.append(f"Вердикт: {result.verdict}")
    lines.append("")

    if not result.findings:
        lines.append("✅ Опасных паттернов не обнаружено.")
        lines.append("   Скил выглядит безопасным.")
        return "\n".join(lines)

    # Group by category
    by_category: dict[str, list[Finding]] = {}
    for f in result.findings:
        cat = f.pattern.category
        by_category.setdefault(cat, []).append(f)

    for cat, findings in sorted(
        by_category.items(),
        key=lambda x: (
            {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(
                x[1][0].pattern.severity, 9
            )
        ),
    ):
        cat_name = CATEGORY_NAMES.get(cat, cat)
        lines.append(f"### {cat_name}")
        lines.append("")

        # Deduplicate by pattern id
        seen_ids: set[str] = set()
        for f in findings:
            if f.pattern.id in seen_ids:
                continue
            seen_ids.add(f.pattern.id)

            emoji = SEVERITY_EMOJI.get(f.pattern.severity, "❓")
            lines.append(f"  {emoji} [{f.pattern.id}] " f"{f.pattern.name}")
            lines.append(f"     {f.pattern.description}")
            lines.append(f"     📄 {f.file_path}:{f.line_number}")
            lines.append(f"     > {f.line_content}")
            lines.append("")

    # Summary
    lines.append("-" * 50)
    lines.append("ИТОГО:")
    lines.append(f"  🔴 Critical: {result.critical_count}")
    lines.append(f"  🟠 High:     {result.high_count}")
    lines.append(f"  🟡 Medium:   {result.medium_count}")
    lines.append("")

    if result.critical_count > 0:
        lines.append("⛔ НЕ УСТАНАВЛИВАЙТЕ этот скил!")
        lines.append("   Обнаружены критические угрозы.")
    elif result.high_count > 0:
        lines.append("⚠️  Скил требует ручной проверки " "перед использованием.")
    else:
        lines.append("ℹ️  Незначительные риски. " "Проверьте вручную.")

    return "\n".join(lines)


def format_json(result: ScanResult) -> str:
    """Format scan result as JSON."""
    return json.dumps(
        {
            "target": result.target,
            "files_scanned": result.files_scanned,
            "risk_score": result.risk_score,
            "verdict": result.verdict,
            "critical": result.critical_count,
            "high": result.high_count,
            "medium": result.medium_count,
            "categories": list(result.categories_hit),
            "findings": [
                {
                    "id": f.pattern.id,
                    "severity": f.pattern.severity,
                    "category": f.pattern.category,
                    "name": f.pattern.name,
                    "description": (f.pattern.description),
                    "file": f.file_path,
                    "line": f.line_number,
                    "match": f.match_text,
                }
                for f in result.findings
            ],
        },
        indent=2,
        ensure_ascii=False,
    )


# ============================================================
# CLI
# ============================================================


def main():
    """CLI entrypoint."""
    if len(sys.argv) < 2:
        print("Usage: python skill_scanner.py " "<path_or_url> [--json]")
        print()
        print("Examples:")
        print("  python skill_scanner.py " "./my-mcp-server/")
        print("  python skill_scanner.py " "server.py")
        sys.exit(1)

    target_str = sys.argv[1]
    use_json = "--json" in sys.argv

    target = Path(target_str)
    if not target.exists():
        print(f"❌ Путь не найден: {target_str}")
        sys.exit(1)

    result = scan_directory(target)

    if use_json:
        print(format_json(result))
    else:
        print(format_report(result))

    # Exit code based on severity
    if result.critical_count > 0:
        sys.exit(2)
    elif result.high_count > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
