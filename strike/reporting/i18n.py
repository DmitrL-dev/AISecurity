#!/usr/bin/env python3
"""
SENTINEL Strike v3.0 — Internationalization (i18n) Module

Provides translations for reports in multiple languages.
Currently supported: English (en), Russian (ru)
"""

from typing import Dict, Any

# Default language
DEFAULT_LANG = "en"

# ============================================================================
# VULNERABILITY DATABASE — Bilingual
# ============================================================================

VULNERABILITY_DB: Dict[str, Dict[str, Any]] = {
    "sqli": {
        "name": {"en": "SQL Injection", "ru": "SQL Injection"},
        "description": {
            "en": "Attacker can inject SQL commands into database queries, allowing reading, modifying, or deleting any data.",
            "ru": "Атакующий может внедрять SQL-команды в запросы к базе данных, что позволяет читать, изменять или удалять любые данные.",
        },
        "impact": {
            "en": [
                "🔴 Full database leak (logins, passwords, personal data)",
                "🔴 Data modification or deletion",
                "🔴 Administrative access",
                "🔴 Server command execution (in some cases)",
            ],
            "ru": [
                "🔴 Полная утечка базы данных (логины, пароли, персональные данные)",
                "🔴 Изменение или удаление данных",
                "🔴 Получение административного доступа",
                "🔴 Возможность выполнения команд на сервере (в некоторых случаях)",
            ],
        },
        "business_risk": {
            "en": "CRITICAL — Full system compromise possible, customer data leak, GDPR fines up to 4% annual revenue.",
            "ru": "КРИТИЧЕСКИЙ — Возможна полная компрометация системы, утечка данных клиентов, штрафы GDPR до 4% годового оборота.",
        },
        "remediation": {
            "en": [
                "Use parameterized queries (prepared statements)",
                "Use ORM instead of raw SQL queries",
                "Enable WAF with SQL injection protection",
                "Limit DB user privileges (principle of least privilege)",
            ],
            "ru": [
                "Использовать параметризованные запросы (prepared statements)",
                "Применять ORM вместо сырых SQL-запросов",
                "Включить WAF с защитой от SQL-инъекций",
                "Ограничить права пользователя БД (принцип минимальных привилегий)",
            ],
        },
        "cwe": "CWE-89",
        "owasp": "A03:2021 — Injection",
        "cvss_base": 9.8,
    },
    "xss": {
        "name": {"en": "Cross-Site Scripting (XSS)", "ru": "Cross-Site Scripting (XSS)"},
        "description": {
            "en": "Attacker can inject malicious JavaScript code that executes in victim's browser.",
            "ru": "Атакующий может внедрять вредоносный JavaScript-код, который выполняется в браузере жертвы.",
        },
        "impact": {
            "en": [
                "🟠 Session cookie theft (account takeover)",
                "🟠 Redirect to phishing sites",
                "🟠 Page content modification",
                "🟠 User input data theft",
            ],
            "ru": [
                "🟠 Кража сессионных cookies (захват аккаунта)",
                "🟠 Перенаправление на фишинговые сайты",
                "🟠 Изменение содержимого страницы",
                "🟠 Кража данных, вводимых пользователем",
            ],
        },
        "business_risk": {
            "en": "HIGH — Mass user account takeover possible, reputational damage.",
            "ru": "ВЫСОКИЙ — Возможен массовый захват аккаунтов пользователей, репутационный ущерб.",
        },
        "remediation": {
            "en": [
                "Escape all user data on output",
                "Use Content-Security-Policy (CSP)",
                "Apply HTTPOnly flag for cookies",
                "Validate and sanitize input data",
            ],
            "ru": [
                "Экранировать все пользовательские данные при выводе",
                "Использовать Content-Security-Policy (CSP)",
                "Применять HTTPOnly флаг для cookies",
                "Валидировать и санитайзить входные данные",
            ],
        },
        "cwe": "CWE-79",
        "owasp": "A03:2021 — Injection",
        "cvss_base": 6.1,
    },
    "lfi": {
        "name": {"en": "Local File Inclusion (LFI)", "ru": "Local File Inclusion (LFI)"},
        "description": {
            "en": "Attacker can read arbitrary server files, including configurations, passwords, and source code.",
            "ru": "Атакующий может читать произвольные файлы сервера, включая конфигурации, пароли и исходный код.",
        },
        "impact": {
            "en": [
                "🔴 Reading config files (/etc/passwd, config.php)",
                "🔴 Application source code leak",
                "🟠 Reading logs with sensitive information",
                "🔴 Code execution possibility (via log poisoning)",
            ],
            "ru": [
                "🔴 Чтение конфигурационных файлов (/etc/passwd, config.php)",
                "🔴 Утечка исходного кода приложения",
                "🟠 Чтение логов с чувствительной информацией",
                "🔴 Возможность выполнения кода (через log poisoning)",
            ],
        },
        "business_risk": {
            "en": "CRITICAL — Direct path to full server compromise.",
            "ru": "КРИТИЧЕСКИЙ — Прямой путь к полной компрометации сервера.",
        },
        "remediation": {
            "en": [
                "Never use user input in file paths",
                "Use whitelist of allowed files",
                "Configure open_basedir in PHP",
                "Use chroot for application isolation",
            ],
            "ru": [
                "Никогда не использовать пользовательский ввод в путях файлов",
                "Использовать whitelist разрешённых файлов",
                "Настроить open_basedir в PHP",
                "Использовать chroot для изоляции приложения",
            ],
        },
        "cwe": "CWE-98",
        "owasp": "A01:2021 — Broken Access Control",
        "cvss_base": 7.5,
    },
    "ssrf": {
        "name": {"en": "Server-Side Request Forgery (SSRF)", "ru": "Server-Side Request Forgery (SSRF)"},
        "description": {
            "en": "Attacker can make server perform requests to internal resources or external systems.",
            "ru": "Атакующий может заставить сервер выполнять запросы к внутренним ресурсам или внешним системам.",
        },
        "impact": {
            "en": [
                "🔴 Access to internal infrastructure (169.254.169.254, localhost)",
                "🔴 Firewall and VPN bypass",
                "🟠 Internal network scanning",
                "🔴 Cloud metadata theft (AWS/GCP credentials)",
            ],
            "ru": [
                "🔴 Доступ к внутренней инфраструктуре (169.254.169.254, localhost)",
                "🔴 Обход firewall и VPN",
                "🟠 Сканирование внутренней сети",
                "🔴 Кража метаданных облака (AWS/GCP credentials)",
            ],
        },
        "business_risk": {
            "en": "CRITICAL — Can lead to compromise of entire cloud infrastructure.",
            "ru": "КРИТИЧЕСКИЙ — Может привести к компрометации всей облачной инфраструктуры.",
        },
        "remediation": {
            "en": [
                "Validate and filter URLs server-side",
                "Use whitelist of allowed domains",
                "Block requests to private IPs (RFC 1918)",
                "Disable redirects when making requests",
            ],
            "ru": [
                "Валидировать и фильтровать URL на стороне сервера",
                "Использовать whitelist разрешённых доменов",
                "Блокировать запросы к приватным IP (RFC 1918)",
                "Отключить редиректы при выполнении запросов",
            ],
        },
        "cwe": "CWE-918",
        "owasp": "A10:2021 — SSRF",
        "cvss_base": 9.1,
    },
    "cmdi": {
        "name": {"en": "Command Injection", "ru": "Command Injection"},
        "description": {
            "en": "Attacker can execute arbitrary operating system commands on the server.",
            "ru": "Атакующий может выполнять произвольные команды операционной системы на сервере.",
        },
        "impact": {
            "en": [
                "🔴 Full server control",
                "🔴 Backdoor and malware installation",
                "🔴 Access to all user data",
                "🔴 Using server for attacks on other systems",
            ],
            "ru": [
                "🔴 Полный контроль над сервером",
                "🔴 Установка backdoor и malware",
                "🔴 Доступ к данным всех пользователей",
                "🔴 Использование сервера для атак на другие системы",
            ],
        },
        "business_risk": {
            "en": "CRITICAL — Full server compromise, maximum damage.",
            "ru": "КРИТИЧЕСКИЙ — Полная компрометация сервера, максимальный ущерб.",
        },
        "remediation": {
            "en": [
                "Never pass user input to shell commands",
                "Use safe APIs instead of system() / exec()",
                "Escape special characters",
                "Apply containerization with limited privileges",
            ],
            "ru": [
                "Никогда не передавать пользовательский ввод в shell-команды",
                "Использовать безопасные API вместо system() / exec()",
                "Экранировать специальные символы",
                "Применять контейнеризацию с ограниченными правами",
            ],
        },
        "cwe": "CWE-78",
        "owasp": "A03:2021 — Injection",
        "cvss_base": 10.0,
    },
    "auth_bypass": {
        "name": {"en": "Authentication Bypass", "ru": "Authentication Bypass"},
        "description": {
            "en": "Attacker can bypass authentication mechanism and gain access without credentials.",
            "ru": "Атакующий может обойти механизм аутентификации и получить доступ без учётных данных.",
        },
        "impact": {
            "en": [
                "🔴 Unauthorized account access",
                "🔴 Admin account takeover",
                "🟠 View other users' data",
            ],
            "ru": [
                "🔴 Несанкционированный доступ к аккаунтам",
                "🔴 Захват административных учётных записей",
                "🟠 Просмотр данных других пользователей",
            ],
        },
        "business_risk": {
            "en": "CRITICAL — Direct data access without authorization.",
            "ru": "КРИТИЧЕСКИЙ — Прямой доступ к данным без авторизации.",
        },
        "remediation": {
            "en": [
                "Audit authentication logic",
                "Use proven libraries (don't reinvent the wheel)",
                "Implement multi-factor authentication (MFA)",
                "Log all login attempts",
            ],
            "ru": [
                "Провести аудит логики аутентификации",
                "Использовать проверенные библиотеки (не изобретать велосипед)",
                "Внедрить многофакторную аутентификацию (MFA)",
                "Логировать все попытки входа",
            ],
        },
        "cwe": "CWE-287",
        "owasp": "A07:2021 — Identification and Authentication Failures",
        "cvss_base": 9.8,
    },
    "waf_bypass": {
        "name": {"en": "WAF Bypass", "ru": "WAF Bypass"},
        "description": {
            "en": "Attacker found a way to bypass Web Application Firewall, protection is ineffective.",
            "ru": "Атакующий нашёл способ обойти Web Application Firewall, защита неэффективна.",
        },
        "impact": {
            "en": [
                "🟠 WAF does not block attacks",
                "🟠 False sense of security",
                "🟠 All vulnerabilities become exploitable",
            ],
            "ru": [
                "🟠 WAF не блокирует атаки",
                "🟠 Ложное чувство безопасности",
                "🟠 Все уязвимости становятся эксплуатируемыми",
            ],
        },
        "business_risk": {
            "en": "MEDIUM — WAF is not the only line of defense, but its bypass increases risk.",
            "ru": "СРЕДНИЙ — WAF не является единственной линией защиты, но его обход увеличивает риск.",
        },
        "remediation": {
            "en": [
                "Update WAF rules",
                "Enable Unicode and encoding normalization",
                "Add rules for detected bypass techniques",
                "Remember: WAF is additional protection, not a replacement for fixing vulnerabilities",
            ],
            "ru": [
                "Обновить правила WAF",
                "Включить нормализацию Unicode и encoding",
                "Добавить правила для обнаруженных bypass-техник",
                "Помнить: WAF — дополнительная защита, не замена исправления уязвимостей",
            ],
        },
        "cwe": "CWE-693",
        "owasp": "N/A",
        "cvss_base": 5.0,
    },
    "unknown": {
        "name": {"en": "Detected Vulnerability", "ru": "Обнаруженная уязвимость"},
        "description": {
            "en": "Successful protection bypass using specialized technique.",
            "ru": "Успешный обход защиты с использованием специализированной техники.",
        },
        "impact": {
            "en": ["🟡 Requires additional analysis"],
            "ru": ["🟡 Требует дополнительного анализа"],
        },
        "business_risk": {
            "en": "MEDIUM — Detailed specialist analysis required.",
            "ru": "СРЕДНИЙ — Необходима детальная проверка специалистом.",
        },
        "remediation": {
            "en": [
                "Conduct manual analysis of detected point",
                "Check application logs",
                "Contact SENTINEL Strike team for detailed analysis",
            ],
            "ru": [
                "Провести ручной анализ обнаруженной точки",
                "Проверить логи приложения",
                "Связаться с командой SENTINEL Strike для детального разбора",
            ],
        },
        "cwe": "N/A",
        "owasp": "N/A",
        "cvss_base": 5.0,
    },
}


# ============================================================================
# UI STRINGS
# ============================================================================

UI_STRINGS = {
    "report_title": {
        "en": "Penetration Testing Report",
        "ru": "Отчёт о тестировании на проникновение",
    },
    "executive_summary": {
        "en": "Executive Summary",
        "ru": "Краткое резюме для руководства",
    },
    "risk_critical": {"en": "CRITICAL", "ru": "КРИТИЧЕСКИЙ"},
    "risk_high": {"en": "HIGH", "ru": "ВЫСОКИЙ"},
    "risk_medium": {"en": "MEDIUM", "ru": "СРЕДНИЙ"},
    "overall_risk": {"en": "OVERALL RISK", "ru": "ОБЩИЙ РИСК"},
    "unique_vulns": {"en": "Unique Vulnerabilities", "ru": "Уникальных уязвимостей"},
    "successful_attacks": {"en": "Successful Attacks", "ru": "Успешных атак"},
    "bypass_success_rate": {"en": "Bypass Success Rate", "ru": "Успешность обхода защиты"},
    "critical_found": {
        "en": "critical vulnerabilities found requiring immediate action.",
        "ru": "критических уязвимостей, требующих немедленного устранения.",
    },
    "risks": {"en": "Risks", "ru": "Риски"},
    "risk_system_compromise": {
        "en": "Full system compromise possible",
        "ru": "Возможна полная компрометация системы",
    },
    "risk_data_leak": {
        "en": "Customer data leak",
        "ru": "Утечка конфиденциальных данных клиентов",
    },
    "risk_gdpr": {
        "en": "GDPR fines up to 4% annual revenue",
        "ru": "Штрафы регуляторов (GDPR: до 4% годового оборота)",
    },
    "risk_reputation": {"en": "Reputational damage", "ru": "Репутационный ущерб"},
    "recommendation": {"en": "Recommendation", "ru": "Рекомендация"},
    "stop_access": {
        "en": "Suspend access to vulnerable endpoints until fixed.",
        "ru": "Приостановить доступ к уязвимым эндпоинтам до исправления.",
    },
    "findings": {"en": "Detailed Findings", "ru": "Детальные находки"},
    "description": {"en": "Description", "ru": "Описание"},
    "potential_damage": {"en": "Potential Damage", "ru": "Потенциальный ущерб"},
    "business_risk": {"en": "Business Risk", "ru": "Бизнес-риск"},
    "remediation_steps": {"en": "Remediation Steps", "ru": "Рекомендации по устранению"},
    "technical_details": {"en": "Technical Details", "ru": "Технические детали"},
    "bypass_technique": {"en": "Bypass Technique", "ru": "Техника обхода"},
    "payload": {"en": "Payload", "ru": "Вредоносная нагрузка"},
    "how_to_reproduce": {"en": "How to Reproduce (PoC)", "ru": "Как воспроизвести (PoC)"},
    "vulnerable_url": {"en": "Vulnerable URL", "ru": "Уязвимый URL"},
    "expected_result": {"en": "Expected Result", "ru": "Ожидаемый результат"},
    "remediation_roadmap": {"en": "Remediation Roadmap", "ru": "План устранения"},
    "immediate": {"en": "Immediate (0-24 hours)", "ru": "Немедленно (0-24 часа)"},
    "within_week": {"en": "Within a Week", "ru": "В течение недели"},
    "planned": {"en": "Planned", "ru": "В плановом порядке"},
    "disclaimer_title": {"en": "Important Note", "ru": "Важное примечание"},
    "disclaimer_text": {
        "en": "These results require manual verification by a specialist.",
        "ru": "Данные результаты требуют ручной верификации специалистом.",
    },
    "honeypot_warning": {
        "en": "Suspicious responses detected",
        "ru": "Обнаружены подозрительные ответы",
    },
    "generated": {"en": "Generated", "ru": "Сформирован"},
    "target": {"en": "Target", "ru": "Цель"},
}


def get_vuln_field(vuln_type: str, field: str, lang: str = "en") -> Any:
    """Get vulnerability field in specified language."""
    vuln = VULNERABILITY_DB.get(vuln_type, VULNERABILITY_DB["unknown"])
    value = vuln.get(field)

    if isinstance(value, dict):
        return value.get(lang, value.get("en", ""))
    return value


def get_string(key: str, lang: str = "en") -> str:
    """Get UI string in specified language."""
    strings = UI_STRINGS.get(key, {})
    if isinstance(strings, dict):
        return strings.get(lang, strings.get("en", key))
    return str(strings)
