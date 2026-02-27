#!/usr/bin/env python3
"""
SENTINEL Secret Leak Scanner v2.0

Scans signature files for leaked API keys/tokens.
Generates report + sends email alert to maintainer.
"""

import json
import re
import os
import smtplib
import hashlib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SIGNATURES_DIR = Path(__file__).parent.parent / "signatures"
JAILBREAKS_FILE = SIGNATURES_DIR / "jailbreaks.json"
REPORTS_DIR = Path(__file__).parent.parent / "reports" / "leaked_secrets"

# TODO: sections added incrementally below

# ============================================================
# Secret detection patterns (regex, name, provider, legitimacy check URL)
# ============================================================
SECRET_PATTERNS: list[tuple[str, str, str, str]] = [
    # OpenAI
    (
        r"sk-[a-zA-Z0-9]{20,}",
        "OpenAI API Key",
        "OpenAI",
        "https://platform.openai.com/account/api-keys",
    ),
    (
        r"sk-proj-[a-zA-Z0-9\-_]{40,}",
        "OpenAI Project Key",
        "OpenAI",
        "https://platform.openai.com/account/api-keys",
    ),
    # AWS
    (
        r"AKIA[A-Z0-9]{16}",
        "AWS Access Key ID",
        "AWS",
        "https://console.aws.amazon.com/iam",
    ),
    (
        r"(?:aws_secret_access_key|AWS_SECRET)\s*[=:]\s*[A-Za-z0-9/+=]{40}",
        "AWS Secret Key",
        "AWS",
        "https://console.aws.amazon.com/iam",
    ),
    # Google
    (
        r"AIza[0-9A-Za-z\-_]{35}",
        "Google API Key",
        "Google",
        "https://console.cloud.google.com/apis/credentials",
    ),
    # Azure
    (r"[a-f0-9]{32}", "Azure API Key (candidate)", "Azure", "https://portal.azure.com"),
    # Anthropic
    (
        r"sk-ant-[a-zA-Z0-9\-_]{40,}",
        "Anthropic API Key",
        "Anthropic",
        "https://console.anthropic.com/settings/keys",
    ),
    # HuggingFace
    (
        r"hf_[a-zA-Z0-9]{34}",
        "HuggingFace Token",
        "HuggingFace",
        "https://huggingface.co/settings/tokens",
    ),
    # GitHub
    (
        r"gh[pousr]_[A-Za-z0-9_]{36,}",
        "GitHub Token",
        "GitHub",
        "https://github.com/settings/tokens",
    ),
    (
        r"github_pat_[A-Za-z0-9_]{22,}",
        "GitHub PAT",
        "GitHub",
        "https://github.com/settings/tokens",
    ),
    # Slack
    (
        r"xox[baprs]-[0-9]{10,}-[a-zA-Z0-9\-]+",
        "Slack Token",
        "Slack",
        "https://api.slack.com/apps",
    ),
    # Stripe
    (
        r"sk_live_[a-zA-Z0-9]{24,}",
        "Stripe Secret Key",
        "Stripe",
        "https://dashboard.stripe.com/apikeys",
    ),
    (
        r"pk_live_[a-zA-Z0-9]{24,}",
        "Stripe Publishable Key",
        "Stripe",
        "https://dashboard.stripe.com/apikeys",
    ),
    # Telegram
    (
        r"[0-9]{8,10}:[A-Za-z0-9_-]{35}",
        "Telegram Bot Token",
        "Telegram",
        "https://t.me/BotFather",
    ),
    # SendGrid
    (
        r"SG\.[a-zA-Z0-9\-_]{22}\.[a-zA-Z0-9\-_]{43}",
        "SendGrid API Key",
        "SendGrid",
        "https://app.sendgrid.com/settings/api_keys",
    ),
    # Generic high-entropy (last — broadest)
    (
        r"(?:api[_-]?key|apikey|secret|token|password)\s*[=:]\s*['\"]([A-Za-z0-9\-_./+=]{20,})['\"]",
        "Generic Secret in Assignment",
        "Unknown",
        "",
    ),
]


# ============================================================
# Legitimacy assessment
# ============================================================


def assess_legitimacy(secret: str, secret_type: str) -> str:
    """Assess if a secret looks real or fake/example."""
    # Known fake prefixes
    fakes = [
        "sk-xxxxxxx",
        "sk-your",
        "sk-test",
        "sk-fake",
        "sk-placeholder",
        "AKIAIOSFODNN7EXAMPLE",
        "AIzaSyExample",
        "your_api_key",
        "INSERT_KEY",
        "xxx",
        "000",
        "abc",
        "test",
        "demo",
        "example",
        "1234",
        "sample",
    ]
    lower = secret.lower()
    for f in fakes:
        if f.lower() in lower:
            return "FAKE/EXAMPLE"

    # Entropy check — real keys have high entropy
    unique = len(set(secret))
    ratio = unique / max(len(secret), 1)
    if ratio < 0.3:
        return "LIKELY_FAKE (low entropy)"

    # Length check
    if len(secret) < 16:
        return "LIKELY_FAKE (too short)"

    # All same char
    if len(set(secret.replace("-", "").replace("_", ""))) < 4:
        return "FAKE (repetitive)"

    return "LIKELY_REAL — REQUIRES INVESTIGATION"


# ============================================================
# Scanner
# ============================================================


def scan_signatures() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Scan jailbreaks.json for leaked secrets.

    Returns (found_secrets, cleaned_patterns).
    """
    if not JAILBREAKS_FILE.exists():
        print("[SKIP] jailbreaks.json not found")
        return [], []

    with open(JAILBREAKS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    patterns = data.get("patterns", data) if isinstance(data, dict) else data

    found: list[dict[str, Any]] = []
    clean: list[dict[str, Any]] = []

    for p in patterns:
        text = str(p.get("pattern", ""))
        text += " " + str(p.get("full_text", ""))
        text += " " + str(p.get("regex", ""))

        hit = False
        for regex, secret_name, provider, check_url in SECRET_PATTERNS:
            matches = re.findall(regex, text)
            if not matches:
                continue
            for secret_value in matches:
                found.append(
                    {
                        "secret_type": secret_name,
                        "provider": provider,
                        "secret_value": secret_value,
                        "pattern_id": p.get("id", "unknown"),
                        "source": p.get("source", "unknown"),
                        "fetched_at": p.get("fetched_at", ""),
                        "check_url": check_url,
                        "legitimacy": assess_legitimacy(secret_value, secret_name),
                        "sha256": hashlib.sha256(secret_value.encode()).hexdigest(),
                        "found_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
            hit = True
            break

        if not hit:
            clean.append(p)

    return found, clean


# ============================================================
# Report generation
# ============================================================


def generate_report(secrets: list[dict[str, Any]]) -> tuple[str, Path]:
    """Generate JSON + text report. Returns (text_body, json_path)."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    # JSON report
    json_path = REPORTS_DIR / f"leak_report_{ts}.json"
    report_data = {
        "scan_time": datetime.now(timezone.utc).isoformat(),
        "total_secrets_found": len(secrets),
        "likely_real": sum(1 for s in secrets if "LIKELY_REAL" in s["legitimacy"]),
        "secrets": secrets,
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)

    # Text body for email
    real = [s for s in secrets if "LIKELY_REAL" in s["legitimacy"]]
    fake = [s for s in secrets if "LIKELY_REAL" not in s["legitimacy"]]

    lines = [
        "=" * 60,
        "🚨 SENTINEL — Leaked Secret Report",
        f"Scan time: {report_data['scan_time']}",
        f"Total found: {len(secrets)}",
        f"Likely REAL: {len(real)}",
        f"Likely fake/example: {len(fake)}",
        "=" * 60,
        "",
    ]

    if real:
        lines.append("⚠️  LIKELY REAL SECRETS (require action):")
        lines.append("-" * 60)
        for i, s in enumerate(real, 1):
            lines.extend(
                [
                    f"\n[{i}] {s['secret_type']} ({s['provider']})",
                    f"    Key:       {s['secret_value']}",
                    f"    Source:     {s['source']}",
                    f"    Pattern ID: {s['pattern_id']}",
                    f"    Fetched:   {s['fetched_at']}",
                    f"    Legitimacy: {s['legitimacy']}",
                    f"    SHA256:    {s['sha256']}",
                    f"    Check URL: {s['check_url']}",
                ]
            )
        lines.append("")

    if fake:
        lines.append(f"ℹ️  Fake/example secrets ({len(fake)} total, first 5):")
        lines.append("-" * 60)
        for i, s in enumerate(fake[:5], 1):
            lines.extend(
                [
                    f"  [{i}] {s['secret_type']}: {s['secret_value'][:40]}...",
                    f"      Source: {s['source']} | {s['legitimacy']}",
                ]
            )

    lines.extend(["", "=" * 60, f"Full report: {json_path}", "=" * 60])

    body = "\n".join(lines)
    print(body)
    return body, json_path


# ============================================================
# Email notification
# ============================================================


def send_email_alert(body: str, secrets_count: int, real_count: int) -> bool:
    """Send leak alert via SMTP.

    Env vars:
      SENTINEL_ALERT_EMAIL  — recipient (required)
      SMTP_HOST             — SMTP server (default: smtp.gmail.com)
      SMTP_PORT             — SMTP port (default: 587)
      SMTP_USER             — sender login
      SMTP_PASS             — sender password / app password
    """
    recipient = os.environ.get("SENTINEL_ALERT_EMAIL", "")
    if not recipient:
        print("[WARN] SENTINEL_ALERT_EMAIL not set, skipping email")
        return False

    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_pass = os.environ.get("SMTP_PASS", "")

    if not smtp_user or not smtp_pass:
        print("[WARN] SMTP_USER/SMTP_PASS not set, skipping email")
        return False

    subject = f"🚨 SENTINEL: {real_count} leaked secrets found ({secrets_count} total)"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = recipient
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        print(f"[OK] Alert sent to {recipient}")
        return True
    except Exception as e:
        print(f"[ERROR] Email failed: {e}")
        return False


# ============================================================
# Clean + save
# ============================================================


def clean_and_save(clean_patterns: list[dict[str, Any]]) -> None:
    """Overwrite jailbreaks.json with cleaned patterns."""
    with open(JAILBREAKS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        data["patterns"] = clean_patterns
        data["total_patterns"] = len(clean_patterns)
    else:
        data = clean_patterns

    with open(JAILBREAKS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"[OK] Saved {len(clean_patterns)} clean patterns")


# ============================================================
# Main
# ============================================================


def main() -> None:
    print("=" * 60)
    print("SENTINEL Secret Leak Scanner v2.0")
    print(f"Time: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    found, clean = scan_signatures()

    if not found:
        print("[OK] No secrets found — signatures clean")
        return

    real = [s for s in found if "LIKELY_REAL" in s["legitimacy"]]
    print(f"\n[!] Found {len(found)} secrets ({len(real)} likely real)")

    # Generate report
    body, json_path = generate_report(found)

    # Send email if real secrets found
    if real:
        send_email_alert(body, len(found), len(real))

    # Clean signatures file
    clean_and_save(clean)

    print(f"\n[DONE] Removed {len(found)} patterns, report: {json_path}")


if __name__ == "__main__":
    main()
