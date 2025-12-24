#!/usr/bin/env python3
"""
SENTINEL Strike v3.0 — Professional Report Generator

Business-friendly pentest reports with:
- Human-readable vulnerability descriptions
- Business impact assessment
- Clear remediation steps
- Executive summary for management
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path
from collections import Counter
import html
import re

# i18n support
from strike.reporting.i18n import get_vuln_field, get_string, VULNERABILITY_DB as I18N_VULN_DB

logger = logging.getLogger(__name__)


# ============================================================================
# VULNERABILITY DATABASE — Human-readable descriptions
# ============================================================================

VULNERABILITY_DB = {
    "sqli": {
        "name": "SQL Injection",
        "description": "Атакующий может внедрять SQL-команды в запросы к базе данных, что позволяет читать, изменять или удалять любые данные.",
        "impact": [
            "🔴 Полная утечка базы данных (логины, пароли, персональные данные)",
            "🔴 Изменение или удаление данных",
            "🔴 Получение административного доступа",
            "🔴 Возможность выполнения команд на сервере (в некоторых случаях)",
        ],
        "business_risk": "КРИТИЧЕСКИЙ — Возможна полная компрометация системы, утечка данных клиентов, штрафы GDPR до 4% годового оборота.",
        "remediation": [
            "Использовать параметризованные запросы (prepared statements)",
            "Применять ORM вместо сырых SQL-запросов",
            "Включить WAF с защитой от SQL-инъекций",
            "Ограничить права пользователя БД (принцип минимальных привилегий)",
        ],
        "cwe": "CWE-89",
        "owasp": "A03:2021 — Injection",
        "cvss_base": 9.8,
    },
    "xss": {
        "name": "Cross-Site Scripting (XSS)",
        "description": "Атакующий может внедрять вредоносный JavaScript-код, который выполняется в браузере жертвы.",
        "impact": [
            "🟠 Кража сессионных cookies (захват аккаунта)",
            "🟠 Перенаправление на фишинговые сайты",
            "🟠 Изменение содержимого страницы",
            "🟠 Кража данных, вводимых пользователем",
        ],
        "business_risk": "ВЫСОКИЙ — Возможен массовый захват аккаунтов пользователей, репутационный ущерб.",
        "remediation": [
            "Экранировать все пользовательские данные при выводе",
            "Использовать Content-Security-Policy (CSP)",
            "Применять HTTPOnly флаг для cookies",
            "Валидировать и санитайзить входные данные",
        ],
        "cwe": "CWE-79",
        "owasp": "A03:2021 — Injection",
        "cvss_base": 6.1,
    },
    "lfi": {
        "name": "Local File Inclusion (LFI)",
        "description": "Атакующий может читать произвольные файлы сервера, включая конфигурации, пароли и исходный код.",
        "impact": [
            "🔴 Чтение конфигурационных файлов (/etc/passwd, config.php)",
            "🔴 Утечка исходного кода приложения",
            "🟠 Чтение логов с чувствительной информацией",
            "🔴 Возможность выполнения кода (через log poisoning)",
        ],
        "business_risk": "КРИТИЧЕСКИЙ — Прямой путь к полной компрометации сервера.",
        "remediation": [
            "Никогда не использовать пользовательский ввод в путях файлов",
            "Использовать whitelist разрешённых файлов",
            "Настроить open_basedir в PHP",
            "Использовать chroot для изоляции приложения",
        ],
        "cwe": "CWE-98",
        "owasp": "A01:2021 — Broken Access Control",
        "cvss_base": 7.5,
    },
    "ssrf": {
        "name": "Server-Side Request Forgery (SSRF)",
        "description": "Атакующий может заставить сервер выполнять запросы к внутренним ресурсам или внешним системам.",
        "impact": [
            "🔴 Доступ к внутренней инфраструктуре (169.254.169.254, localhost)",
            "🔴 Обход firewall и VPN",
            "🟠 Сканирование внутренней сети",
            "🔴 Кража метаданных облака (AWS/GCP credentials)",
        ],
        "business_risk": "КРИТИЧЕСКИЙ — Может привести к компрометации всей облачной инфраструктуры.",
        "remediation": [
            "Валидировать и фильтровать URL на стороне сервера",
            "Использовать whitelist разрешённых доменов",
            "Блокировать запросы к приватным IP (RFC 1918)",
            "Отключить редиректы при выполнении запросов",
        ],
        "cwe": "CWE-918",
        "owasp": "A10:2021 — SSRF",
        "cvss_base": 9.1,
    },
    "cmdi": {
        "name": "Command Injection",
        "description": "Атакующий может выполнять произвольные команды операционной системы на сервере.",
        "impact": [
            "🔴 Полный контроль над сервером",
            "🔴 Установка backdoor и malware",
            "🔴 Доступ к данным всех пользователей",
            "🔴 Использование сервера для атак на другие системы",
        ],
        "business_risk": "КРИТИЧЕСКИЙ — Полная компрометация сервера, максимальный ущерб.",
        "remediation": [
            "Никогда не передавать пользовательский ввод в shell-команды",
            "Использовать безопасные API вместо system() / exec()",
            "Экранировать специальные символы",
            "Применять контейнеризацию с ограниченными правами",
        ],
        "cwe": "CWE-78",
        "owasp": "A03:2021 — Injection",
        "cvss_base": 10.0,
    },
    "auth_bypass": {
        "name": "Authentication Bypass",
        "description": "Атакующий может обойти механизм аутентификации и получить доступ без учётных данных.",
        "impact": [
            "🔴 Несанкционированный доступ к аккаунтам",
            "🔴 Захват административных учётных записей",
            "🟠 Просмотр данных других пользователей",
        ],
        "business_risk": "КРИТИЧЕСКИЙ — Прямой доступ к данным без авторизации.",
        "remediation": [
            "Провести аудит логики аутентификации",
            "Использовать проверенные библиотеки (не изобретать велосипед)",
            "Внедрить многофакторную аутентификацию (MFA)",
            "Логировать все попытки входа",
        ],
        "cwe": "CWE-287",
        "owasp": "A07:2021 — Identification and Authentication Failures",
        "cvss_base": 9.8,
    },
    "waf_bypass": {
        "name": "WAF Bypass",
        "description": "Атакующий нашёл способ обойти Web Application Firewall, защита неэффективна.",
        "impact": [
            "🟠 WAF не блокирует атаки",
            "🟠 Ложное чувство безопасности",
            "🟠 Все уязвимости становятся эксплуатируемыми",
        ],
        "business_risk": "СРЕДНИЙ — WAF не является единственной линией защиты, но его обход увеличивает риск.",
        "remediation": [
            "Обновить правила WAF",
            "Включить нормализацию Unicode и encoding",
            "Добавить правила для обнаруженных bypass-техник",
            "Помнить: WAF — дополнительная защита, не замена исправления уязвимостей",
        ],
        "cwe": "CWE-693",
        "owasp": "N/A",
        "cvss_base": 5.0,
    },
    "unknown": {
        "name": "Обнаруженная уязвимость",
        "description": "Успешный обход защиты с использованием специализированной техники.",
        "impact": [
            "🟡 Требует дополнительного анализа",
        ],
        "business_risk": "СРЕДНИЙ — Необходима детальная проверка специалистом.",
        "remediation": [
            "Провести ручной анализ обнаруженной точки",
            "Проверить логи приложения",
            "Связаться с командой SENTINEL Strike для детального разбора",
        ],
        "cwe": "N/A",
        "owasp": "N/A",
        "cvss_base": 5.0,
    },
}


# ============================================================================
# MITRE ATT&CK MAPPING
# ============================================================================

MITRE_MAPPING = {
    "sqli": {
        "tactic": "Initial Access",
        "technique_id": "T1190",
        "technique": "Exploit Public-Facing Application",
    },
    "xss": {
        "tactic": "Execution",
        "technique_id": "T1059.007",
        "technique": "JavaScript",
    },
    "lfi": {
        "tactic": "Collection",
        "technique_id": "T1005",
        "technique": "Data from Local System",
    },
    "ssrf": {
        "tactic": "Discovery",
        "technique_id": "T1526",
        "technique": "Cloud Service Discovery",
    },
    "cmdi": {
        "tactic": "Execution",
        "technique_id": "T1059",
        "technique": "Command and Scripting Interpreter",
    },
    "auth_bypass": {
        "tactic": "Initial Access",
        "technique_id": "T1078",
        "technique": "Valid Accounts",
    },
    "waf_bypass": {
        "tactic": "Defense Evasion",
        "technique_id": "T1027",
        "technique": "Obfuscated Files",
    },
    "unknown": {"tactic": "Unknown", "technique_id": "N/A", "technique": "Unknown"},
}


def classify_vulnerability(technique: str, payload: str) -> str:
    """Classify vulnerability type from technique name and payload."""
    technique_lower = technique.lower()
    payload_lower = payload.lower()

    # Check technique name first
    if any(x in technique_lower for x in ["sql", "sqli", "union", "select"]):
        return "sqli"
    if any(x in technique_lower for x in ["xss", "script", "alert", "console"]):
        return "xss"
    if any(x in technique_lower for x in ["lfi", "traversal", "path", "file"]):
        return "lfi"
    if any(x in technique_lower for x in ["ssrf", "url", "fetch"]):
        return "ssrf"
    if any(x in technique_lower for x in ["cmd", "rce", "exec", "command"]):
        return "cmdi"
    if any(x in technique_lower for x in ["auth", "login", "bypass"]):
        return "auth_bypass"

    # Check payload content
    if any(x in payload_lower for x in ["or 1=1", "union", "select", "' or", "%27"]):
        return "sqli"
    if any(x in payload_lower for x in ["<script", "onerror", "onload", "javascript:"]):
        return "xss"
    if any(x in payload_lower for x in ["../", "..\\", "/etc/", "passwd"]):
        return "lfi"

    return "waf_bypass"  # Default for successful bypasses


@dataclass
class Finding:
    """Single vulnerability finding with business context."""

    title: str
    severity: str
    technique: str
    payload: str
    endpoint: str = ""
    vuln_type: str = ""
    description: str = ""
    impact: List[str] = field(default_factory=list)
    business_risk: str = ""
    remediation: List[str] = field(default_factory=list)
    cwe: str = ""
    owasp: str = ""
    cvss: float = 0.0
    mitre: Dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.vuln_type:
            self.vuln_type = classify_vulnerability(
                self.technique, self.payload)

        vuln_info = VULNERABILITY_DB.get(
            self.vuln_type, VULNERABILITY_DB["unknown"])

        if not self.description:
            self.description = vuln_info["description"]
        if not self.impact:
            self.impact = vuln_info["impact"]
        if not self.business_risk:
            self.business_risk = vuln_info["business_risk"]
        if not self.remediation:
            self.remediation = vuln_info["remediation"]
        if not self.cwe:
            self.cwe = vuln_info["cwe"]
        if not self.owasp:
            self.owasp = vuln_info["owasp"]
        if not self.cvss:
            self.cvss = vuln_info["cvss_base"]
        if not self.mitre:
            self.mitre = MITRE_MAPPING.get(
                self.vuln_type, MITRE_MAPPING["unknown"])

        # Update title with proper name
        self.title = f"{vuln_info['name']} ({self.technique})"


@dataclass
class ReportData:
    """Aggregated report data."""

    target: str
    start_time: str
    end_time: str
    total_requests: int
    total_bypasses: int
    findings: List[Finding]
    severity_counts: Dict[str, int]
    technique_counts: Dict[str, int]
    blocked_count: int
    vuln_type_counts: Dict[str, int] = field(default_factory=dict)
    honeypot_count: int = 0  # Suspicious fast responses (< 10ms)

    @property
    def critical_count(self) -> int:
        return self.severity_counts.get("CRITICAL", 0)

    @property
    def high_count(self) -> int:
        return self.severity_counts.get("HIGH", 0)

    @property
    def medium_count(self) -> int:
        return self.severity_counts.get("MEDIUM", 0)

    @property
    def success_rate(self) -> float:
        total = self.total_bypasses + self.blocked_count
        return (self.total_bypasses / total * 100) if total > 0 else 0


class StrikeReportGenerator:
    """Professional pentest report generator with business context.

    Supports i18n with --lang parameter (en/ru).
    """

    def __init__(self, log_path: Optional[str] = None, lang: str = "en"):
        self.log_path = Path(log_path) if log_path else None
        self.lang = lang  # Language for report: "en" or "ru"
        self.entries: List[Dict] = []
        self.report_data: Optional[ReportData] = None

        if self.log_path and self.log_path.exists():
            self._parse_log()

    def _parse_log(self):
        """Parse JSONL attack log."""
        self.entries = []
        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        self.entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

        self._process_entries()

    def _process_entries(self):
        """Process entries into structured report data."""
        if not self.entries:
            return

        target = "Unknown"
        start_time = ""
        end_time = ""

        for e in self.entries:
            if e.get("type") == "attack_start":
                target = e.get("target", "Unknown")
                start_time = e.get("timestamp", "")
            if e.get("timestamp"):
                end_time = e.get("timestamp")

        requests = [e for e in self.entries if e.get("type") == "request"]
        bypasses = [e for e in self.entries if e.get("type") == "bypass"]
        blocked = [e for e in self.entries if e.get("type") == "blocked"]

        severity_counts = Counter(e.get("severity", "UNKNOWN")
                                  for e in bypasses)
        technique_counts = Counter(
            e.get("technique", "unknown") for e in bypasses)

        # Create unique findings (deduplicate by vuln type)
        seen_vulns = {}
        findings = []

        for b in bypasses:
            finding = Finding(
                title="",  # Will be set in __post_init__
                severity=b.get("severity", "MEDIUM"),
                technique=b.get("technique", "unknown"),
                payload=b.get("payload", ""),
                endpoint=b.get("endpoint", target),
            )

            # Deduplicate: keep best example per vuln type
            key = (finding.vuln_type, finding.severity)
            if key not in seen_vulns:
                seen_vulns[key] = finding
                findings.append(finding)

        # Sort by severity
        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        findings.sort(key=lambda f: severity_order.get(f.severity, 99))

        # Vuln type distribution
        vuln_type_counts = Counter(f.vuln_type for f in findings)

        self.report_data = ReportData(
            target=target,
            start_time=start_time,
            end_time=end_time,
            total_requests=len(requests),
            total_bypasses=len(bypasses),
            findings=findings,
            severity_counts=dict(severity_counts),
            technique_counts=dict(technique_counts),
            blocked_count=len(blocked),
            vuln_type_counts=dict(vuln_type_counts),
            honeypot_count=sum(
                1 for b in bypasses if b.get("honeypot_suspicious")),
        )

    def generate_html(self) -> str:
        """Generate professional HTML report."""
        if not self.report_data:
            return "<html><body><h1>No data</h1></body></html>"

        return HTML_TEMPLATE.format(
            lang=self.lang,
            report_title=get_string("report_title", self.lang),
            target=html.escape(self.report_data.target),
            generated_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            start_time=(
                self.report_data.start_time[:19]
                if self.report_data.start_time
                else "N/A"
            ),
            end_time=(
                self.report_data.end_time[:19] if self.report_data.end_time else "N/A"
            ),
            total_requests=self.report_data.total_requests,
            total_bypasses=self.report_data.total_bypasses,
            blocked_count=self.report_data.blocked_count,
            success_rate=f"{self.report_data.success_rate:.1f}",
            critical_count=self.report_data.critical_count,
            high_count=self.report_data.high_count,
            medium_count=self.report_data.medium_count,
            unique_vulns=len(self.report_data.findings),
            executive_summary=self._generate_executive_summary(),
            findings_html=self._generate_findings_html(),
            remediation_html=self._generate_remediation_html(),
            severity_chart_data=self._generate_severity_chart_data(),
            vuln_chart_data=self._generate_vuln_chart_data(),
        )

    def _generate_executive_summary(self) -> str:
        """Generate business-friendly executive summary."""
        if not self.report_data:
            return ""

        critical = self.report_data.critical_count
        high = self.report_data.high_count

        if critical > 0:
            risk_level = "КРИТИЧЕСКИЙ"
            risk_color = "#dc3545"
            risk_text = f"""
            <p>Обнаружено <strong>{critical} критических уязвимостей</strong>, требующих немедленного устранения.</p>
            <p>⚠️ <strong>Риски:</strong></p>
            <ul>
                <li>Возможна полная компрометация системы</li>
                <li>Утечка конфиденциальных данных клиентов</li>
                <li>Штрафы регуляторов (GDPR: до 4% годового оборота)</li>
                <li>Репутационный ущерб</li>
            </ul>
            <p>🚨 <strong>Рекомендация:</strong> Приостановить доступ к уязвимым эндпоинтам до исправления.</p>
            """
        elif high > 0:
            risk_level = "ВЫСОКИЙ"
            risk_color = "#fd7e14"
            risk_text = f"""
            <p>Обнаружено <strong>{high} уязвимостей высокой критичности</strong>.</p>
            <p>⚠️ Рекомендуется исправление в течение 7 дней.</p>
            """
        else:
            risk_level = "СРЕДНИЙ"
            risk_color = "#ffc107"
            risk_text = "<p>Критических уязвимостей не обнаружено. Рекомендуется плановое исправление.</p>"

        return f"""
        <div class="risk-badge" style="background: {risk_color};">ОБЩИЙ РИСК: {risk_level}</div>
        {risk_text}
        <div class="summary-stats">
            <div class="summary-stat">
                <span class="stat-num">{len(self.report_data.findings)}</span>
                <span class="stat-label">Уникальных уязвимостей</span>
            </div>
            <div class="summary-stat">
                <span class="stat-num">{self.report_data.total_bypasses}</span>
                <span class="stat-label">Успешных атак</span>
            </div>
            <div class="summary-stat">
                <span class="stat-num">{self.report_data.success_rate:.0f}%</span>
                <span class="stat-label">Успешность обхода защиты</span>
            </div>
        </div>
        
        <!-- DISCLAIMER -->
        <div style="margin-top: 25px; padding: 20px; background: rgba(255, 193, 7, 0.15); border-left: 4px solid #ffc107; border-radius: 8px;">
            <h4 style="color: #ffc107; margin-bottom: 10px;">⚠️ Важное примечание</h4>
            <p style="margin-bottom: 10px;">
                <strong>Данные результаты требуют ручной верификации специалистом.</strong>
            </p>
            <p style="margin-bottom: 10px;">
                SENTINEL Strike — автоматизированный сканер уязвимостей. 
                Вероятность ложноположительного срабатывания (False Positive Rate):
            </p>
            <ul style="margin-left: 20px; margin-bottom: 10px;">
                <li><strong>WAF Bypass:</strong> ~20-30% — WAF может пропускать запрос без реальной уязвимости</li>
                <li><strong>SQL Injection:</strong> ~5-10% — response может измениться по другим причинам</li>
                <li><strong>XSS:</strong> ~15-20% — payload может отразиться, но не выполниться</li>
                <li><strong>LFI/Path Traversal:</strong> ~10-15% — файл может не существовать</li>
            </ul>
            <p style="color: #58a6ff;">
                🔍 <strong>Рекомендация:</strong> Проверьте каждую уязвимость вручную 
                (используя предоставленные PoC) перед включением в финальный отчёт.
            </p>
        </div>
        """ + (
            f"""
        <!-- HONEYPOT WARNING -->
        <div style="margin-top: 15px; padding: 15px; background: rgba(255, 0, 0, 0.1); border-left: 4px solid #dc3545; border-radius: 8px;">
            <h4 style="color: #dc3545; margin-bottom: 10px;">🍯 Обнаружены подозрительные ответы</h4>
            <p><strong>{self.report_data.honeypot_count} из {self.report_data.total_bypasses} bypasses</strong> имеют аномально быстрое время ответа (&lt;10ms).</p>
            <p style="margin-top: 10px;">Это может указывать на:</p>
            <ul style="margin-left: 20px;">
                <li><strong>Honeypot/Tarpit</strong> — фиктивные уязвимости для отслеживания атакующих</li>
                <li><strong>Deception Technology</strong> — системы обнаружения и замедления атак</li>
                <li><strong>WAF с фейковыми сигнатурами</strong> — намеренно пропущенные запросы для анализа</li>
            </ul>
            <p style="color: #dc3545; margin-top: 10px;"><strong>⚠️ Рекомендация:</strong> Эти findings требуют особо тщательной ручной верификации.</p>
        </div>
        """
            if self.report_data.honeypot_count > 0
            else ""
        )

    def _generate_findings_html(self) -> str:
        """Generate detailed findings with business context."""
        if not self.report_data:
            return ""

        html_parts = []

        for i, f in enumerate(self.report_data.findings[:20], 1):
            sev_class = f.severity.lower()

            impact_html = "\n".join(
                f"<li>{html.escape(imp)}</li>" for imp in f.impact)
            remediation_html = "\n".join(
                f"<li>{html.escape(rem)}</li>" for rem in f.remediation
            )

            # Generate curl command for PoC
            endpoint = f.endpoint or self.report_data.target
            payload_escaped = f.payload.replace("'", "\\'")
            curl_example = f"curl -i '{endpoint}?param={payload_escaped}'"

            # Generate step-by-step PoC
            poc_steps = f"""
            <ol style="margin-left: 20px; color: #c9d1d9;">
                <li>Откройте браузер или терминал</li>
                <li>Перейдите по URL: <code style="background: #21262d; padding: 2px 6px; border-radius: 4px; color: #58a6ff;">{html.escape(endpoint)}</code></li>
                <li>Введите payload в параметр (см. ниже)</li>
                <li>Если ответ отличается от обычного — уязвимость подтверждена</li>
            </ol>
            """

            html_parts.append(
                f"""
            <div class="finding-card {sev_class}">
                <div class="finding-header">
                    <span class="severity-badge {sev_class}">{f.severity}</span>
                    <h3 class="finding-title">{html.escape(f.title)}</h3>
                    <span class="cvss-badge">CVSS {f.cvss}</span>
                </div>
                
                <div class="finding-content">
                    <!-- УЯЗВИМЫЙ ENDPOINT -->
                    <div class="finding-section" style="background: rgba(220, 53, 69, 0.1); padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                        <h4>🎯 Уязвимый URL</h4>
                        <a href="{html.escape(endpoint)}" target="_blank" style="color: #58a6ff; word-break: break-all; font-size: 0.95em;">
                            {html.escape(endpoint)}
                        </a>
                    </div>
                    
                    <div class="finding-section">
                        <h4>📋 Описание</h4>
                        <p>{html.escape(f.description)}</p>
                    </div>
                    
                    <div class="finding-section">
                        <h4>💥 Потенциальный ущерб</h4>
                        <ul class="impact-list">{impact_html}</ul>
                    </div>
                    
                    <div class="finding-section">
                        <h4>💼 Бизнес-риск</h4>
                        <p class="business-risk">{html.escape(f.business_risk)}</p>
                    </div>
                    
                    <div class="finding-section">
                        <h4>✅ Рекомендации по устранению</h4>
                        <ol class="remediation-list">{remediation_html}</ol>
                    </div>
                    
                    <div class="finding-meta">
                        <span class="meta-item"><strong>CWE:</strong> {html.escape(f.cwe)}</span>
                        <span class="meta-item"><strong>OWASP:</strong> {html.escape(f.owasp)}</span>
                        <span class="meta-item"><strong>MITRE:</strong> {html.escape(f.mitre.get('technique_id', 'N/A'))}</span>
                    </div>
                    
                    <!-- ТЕХНИЧЕСКИЕ ДЕТАЛИ -->
                    <details class="technical-details" open>
                        <summary>🔧 Технические детали (для разработчиков)</summary>
                        <div class="tech-content">
                            <p><strong>Техника обхода:</strong> <code style="background: #21262d; padding: 2px 8px; border-radius: 4px;">{html.escape(f.technique)}</code></p>
                            
                            <p style="margin-top: 15px;"><strong>🧪 Payload (вредоносная нагрузка):</strong></p>
                            <code class="payload">{html.escape(f.payload)}</code>
                            
                            <p style="margin-top: 20px;"><strong>📝 Как воспроизвести (PoC):</strong></p>
                            {poc_steps}
                            
                            <p style="margin-top: 15px;"><strong>🖥️ Пример HTTP-запроса:</strong></p>
                            <code class="payload" style="background: #0d1117; color: #7ee787;">{html.escape(curl_example)}</code>
                            
                            <p style="margin-top: 15px;"><strong>📊 Ожидаемый результат при эксплуатации:</strong></p>
                            <ul style="margin-left: 20px; color: #f85149;">
                                <li>HTTP 200 OK вместо 403/400</li>
                                <li>Изменённый ответ (утечка данных, ошибка SQL, и т.д.)</li>
                                <li>Время ответа отличается (для blind-атак)</li>
                            </ul>
                        </div>
                    </details>
                </div>
            </div>
            """
            )

        return "\n".join(html_parts)

    def _generate_remediation_html(self) -> str:
        """Generate prioritized remediation roadmap."""
        if not self.report_data:
            return ""

        critical_findings = [
            f for f in self.report_data.findings if f.severity == "CRITICAL"
        ]
        high_findings = [
            f for f in self.report_data.findings if f.severity == "HIGH"]
        medium_findings = [
            f for f in self.report_data.findings if f.severity == "MEDIUM"
        ]

        html_parts = []

        if critical_findings:
            html_parts.append(
                """
            <div class="priority-section critical">
                <h3>🚨 Немедленно (0-24 часа)</h3>
                <ul>
            """
            )
            for f in critical_findings[:5]:
                html_parts.append(
                    f"<li>{html.escape(f.title)}: {html.escape(f.remediation[0] if f.remediation else 'Требуется анализ')}</li>"
                )
            html_parts.append("</ul></div>")

        if high_findings:
            html_parts.append(
                """
            <div class="priority-section high">
                <h3>⚠️ В течение недели</h3>
                <ul>
            """
            )
            for f in high_findings[:5]:
                html_parts.append(
                    f"<li>{html.escape(f.title)}: {html.escape(f.remediation[0] if f.remediation else 'Требуется анализ')}</li>"
                )
            html_parts.append("</ul></div>")

        if medium_findings:
            html_parts.append(
                """
            <div class="priority-section medium">
                <h3>📋 В плановом порядке</h3>
                <ul>
            """
            )
            for f in medium_findings[:5]:
                html_parts.append(f"<li>{html.escape(f.title)}</li>")
            html_parts.append("</ul></div>")

        return "\n".join(html_parts)

    def _generate_severity_chart_data(self) -> str:
        if not self.report_data:
            return "[]"
        colors = {
            "CRITICAL": "#dc3545",
            "HIGH": "#fd7e14",
            "MEDIUM": "#ffc107",
            "LOW": "#28a745",
        }
        data = [
            {"name": k, "value": v, "color": colors.get(k, "#6c757d")}
            for k, v in self.report_data.severity_counts.items()
        ]
        return json.dumps(data)

    def _generate_vuln_chart_data(self) -> str:
        if not self.report_data:
            return "[]"
        data = []
        for vuln_type, count in self.report_data.vuln_type_counts.items():
            name = VULNERABILITY_DB.get(vuln_type, {}).get("name", vuln_type)
            data.append({"name": name, "value": count})
        return json.dumps(data)

    def save(self, output_dir: str = "reports", formats: List[str] = None):
        if formats is None:
            formats = ["html"]

        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target_name = (
            self.report_data.target.replace("https://", "")
            .replace("http://", "")
            .replace("/", "_")
            .replace(":", "")
            if self.report_data
            else "unknown"
        )

        saved = []

        if "html" in formats:
            html_path = output_path / \
                f"strike_report_{target_name}_{timestamp}.html"
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(self.generate_html())
            saved.append(str(html_path))

        return saved


# ============================================================================
# HTML TEMPLATE — Business-Friendly (i18n supported)
# ============================================================================

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="{lang}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{report_title} — {target}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #e4e4e4;
            line-height: 1.7;
        }}
        
        .container {{ max-width: 1200px; margin: 0 auto; padding: 30px; }}
        
        /* Header */
        .header {{
            background: linear-gradient(90deg, #0f3460 0%, #16213e 100%);
            padding: 40px;
            border-radius: 16px;
            margin-bottom: 30px;
            border: 1px solid rgba(255,255,255,0.1);
        }}
        
        .header h1 {{
            font-size: 2em;
            color: #fff;
            margin-bottom: 10px;
        }}
        
        .header-subtitle {{ color: #4cc9f0; font-size: 1.2em; }}
        
        .header-meta {{
            display: flex;
            gap: 30px;
            margin-top: 20px;
            flex-wrap: wrap;
        }}
        
        .meta-item {{ color: #888; }}
        .meta-value {{ color: #fff; font-weight: 600; }}
        
        /* Executive Summary */
        .executive-summary {{
            background: rgba(255,255,255,0.05);
            border-radius: 16px;
            padding: 30px;
            margin-bottom: 30px;
            border: 1px solid rgba(255,255,255,0.1);
        }}
        
        .executive-summary h2 {{
            color: #4cc9f0;
            margin-bottom: 20px;
            font-size: 1.5em;
        }}
        
        .risk-badge {{
            display: inline-block;
            padding: 10px 25px;
            border-radius: 30px;
            font-weight: 700;
            font-size: 1.1em;
            color: white;
            margin-bottom: 20px;
        }}
        
        .summary-stats {{
            display: flex;
            gap: 30px;
            margin-top: 20px;
            flex-wrap: wrap;
        }}
        
        .summary-stat {{
            background: rgba(0,0,0,0.3);
            padding: 20px 30px;
            border-radius: 12px;
            text-align: center;
        }}
        
        .stat-num {{
            display: block;
            font-size: 2.5em;
            font-weight: 700;
            color: #e94560;
        }}
        
        .stat-label {{ color: #888; font-size: 0.9em; }}
        
        /* Findings */
        .findings-section h2 {{
            color: #e94560;
            margin-bottom: 25px;
            font-size: 1.5em;
        }}
        
        .finding-card {{
            background: rgba(255,255,255,0.03);
            border-radius: 12px;
            margin-bottom: 25px;
            border-left: 5px solid;
            overflow: hidden;
        }}
        
        .finding-card.critical {{ border-color: #dc3545; }}
        .finding-card.high {{ border-color: #fd7e14; }}
        .finding-card.medium {{ border-color: #ffc107; }}
        
        .finding-header {{
            display: flex;
            align-items: center;
            gap: 15px;
            padding: 20px;
            background: rgba(0,0,0,0.3);
        }}
        
        .severity-badge {{
            padding: 6px 16px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: 700;
            text-transform: uppercase;
        }}
        
        .severity-badge.critical {{ background: #dc3545; color: white; }}
        .severity-badge.high {{ background: #fd7e14; color: white; }}
        .severity-badge.medium {{ background: #ffc107; color: #000; }}
        
        .finding-title {{ flex: 1; font-size: 1.2em; font-weight: 600; }}
        
        .cvss-badge {{
            background: rgba(233, 69, 96, 0.2);
            color: #e94560;
            padding: 6px 12px;
            border-radius: 6px;
            font-weight: 600;
        }}
        
        .finding-content {{ padding: 25px; }}
        
        .finding-section {{
            margin-bottom: 20px;
        }}
        
        .finding-section h4 {{
            color: #4cc9f0;
            margin-bottom: 10px;
            font-size: 1em;
        }}
        
        .impact-list, .remediation-list {{
            margin-left: 20px;
        }}
        
        .impact-list li, .remediation-list li {{
            margin-bottom: 8px;
        }}
        
        .business-risk {{
            background: rgba(253, 126, 20, 0.1);
            padding: 15px;
            border-radius: 8px;
            border-left: 3px solid #fd7e14;
        }}
        
        .finding-meta {{
            display: flex;
            gap: 20px;
            margin-top: 20px;
            padding-top: 15px;
            border-top: 1px solid rgba(255,255,255,0.1);
            font-size: 0.9em;
        }}
        
        .technical-details {{
            margin-top: 20px;
            background: rgba(0,0,0,0.2);
            border-radius: 8px;
            overflow: hidden;
        }}
        
        .technical-details summary {{
            padding: 15px;
            cursor: pointer;
            color: #888;
        }}
        
        .tech-content {{
            padding: 15px;
            border-top: 1px solid rgba(255,255,255,0.1);
        }}
        
        code.payload {{
            display: block;
            background: rgba(0,0,0,0.4);
            padding: 15px;
            border-radius: 6px;
            font-family: monospace;
            font-size: 0.85em;
            color: #ff6b6b;
            word-break: break-all;
            margin-top: 10px;
        }}
        
        /* Remediation Roadmap */
        .remediation-section {{
            background: rgba(255,255,255,0.05);
            border-radius: 16px;
            padding: 30px;
            margin: 30px 0;
        }}
        
        .remediation-section h2 {{
            color: #4cc9f0;
            margin-bottom: 25px;
        }}
        
        .priority-section {{
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 15px;
        }}
        
        .priority-section.critical {{
            background: rgba(220, 53, 69, 0.15);
            border-left: 4px solid #dc3545;
        }}
        
        .priority-section.high {{
            background: rgba(253, 126, 20, 0.15);
            border-left: 4px solid #fd7e14;
        }}
        
        .priority-section.medium {{
            background: rgba(255, 193, 7, 0.15);
            border-left: 4px solid #ffc107;
        }}
        
        .priority-section h3 {{ margin-bottom: 15px; }}
        .priority-section ul {{ margin-left: 25px; }}
        .priority-section li {{ margin-bottom: 8px; }}
        
        /* Charts */
        .charts-row {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 25px;
            margin: 30px 0;
        }}
        
        .chart-card {{
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            padding: 25px;
        }}
        
        .chart-card h3 {{
            color: #4cc9f0;
            margin-bottom: 20px;
        }}
        
        /* Footer */
        .footer {{
            text-align: center;
            padding: 40px;
            color: #666;
            margin-top: 30px;
        }}
        
        .footer a {{ color: #4cc9f0; text-decoration: none; }}
        
        @media (max-width: 768px) {{
            .charts-row {{ grid-template-columns: 1fr; }}
            .summary-stats {{ flex-direction: column; }}
        }}
        
        @media print {{
            body {{ background: white; color: black; }}
            .header {{ background: #f0f0f0; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <h1>🔐 Отчёт о тестировании на проникновение</h1>
            <div class="header-subtitle">{target}</div>
            <div class="header-meta">
                <div class="meta-item">Дата: <span class="meta-value">{generated_time}</span></div>
                <div class="meta-item">Период: <span class="meta-value">{start_time} — {end_time}</span></div>
                <div class="meta-item">Исполнитель: <span class="meta-value">SENTINEL Strike v3.0</span></div>
            </div>
        </div>
        
        <!-- Executive Summary -->
        <div class="executive-summary">
            <h2>📊 Краткое резюме для руководства</h2>
            {executive_summary}
        </div>
        
        <!-- Charts -->
        <div class="charts-row">
            <div class="chart-card">
                <h3>Распределение по критичности</h3>
                <canvas id="severityChart"></canvas>
            </div>
            <div class="chart-card">
                <h3>Типы уязвимостей</h3>
                <canvas id="vulnChart"></canvas>
            </div>
        </div>
        
        <!-- Remediation Roadmap -->
        <div class="remediation-section">
            <h2>🛠️ План устранения (по приоритету)</h2>
            {remediation_html}
        </div>
        
        <!-- Findings -->
        <div class="findings-section">
            <h2>🔍 Детальное описание уязвимостей</h2>
            {findings_html}
        </div>
        
        <!-- Footer -->
        <div class="footer">
            <p>Отчёт сгенерирован <strong>SENTINEL Strike v3.0</strong></p>
            <p><a href="mailto:chg@live.ru">chg@live.ru</a> | <a href="https://t.me/DmLabincev">@DmLabincev</a></p>
        </div>
    </div>
    
    <script>
        const severityData = {severity_chart_data};
        new Chart(document.getElementById('severityChart'), {{
            type: 'doughnut',
            data: {{
                labels: severityData.map(d => d.name),
                datasets: [{{ data: severityData.map(d => d.value), backgroundColor: severityData.map(d => d.color), borderWidth: 0 }}]
            }},
            options: {{ responsive: true, plugins: {{ legend: {{ position: 'bottom', labels: {{ color: '#e4e4e4' }} }} }} }}
        }});
        
        const vulnData = {vuln_chart_data};
        new Chart(document.getElementById('vulnChart'), {{
            type: 'bar',
            data: {{
                labels: vulnData.map(d => d.name),
                datasets: [{{ data: vulnData.map(d => d.value), backgroundColor: '#e94560', borderRadius: 6 }}]
            }},
            options: {{
                indexAxis: 'y',
                responsive: true,
                plugins: {{ legend: {{ display: false }} }},
                scales: {{
                    x: {{ ticks: {{ color: '#888' }}, grid: {{ color: 'rgba(255,255,255,0.1)' }} }},
                    y: {{ ticks: {{ color: '#e4e4e4' }}, grid: {{ display: false }} }}
                }}
            }}
        }});
    </script>
</body>
</html>
"""


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python report_generator.py <log_file.jsonl>")
        sys.exit(1)

    generator = StrikeReportGenerator(sys.argv[1])
    saved = generator.save()

    print("=" * 60)
    print("✅ Профессиональный отчёт создан")
    print("=" * 60)
    for f in saved:
        print(f"   📄 {f}")

    if generator.report_data:
        print()
        print(f"   🎯 Цель: {generator.report_data.target}")
        print(f"   🔴 Критических: {generator.report_data.critical_count}")
        print(f"   🟠 Высоких: {generator.report_data.high_count}")
        print(
            f"   📊 Уникальных уязвимостей: {len(generator.report_data.findings)}")
