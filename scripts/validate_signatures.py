#!/usr/bin/env python3
"""
SENTINEL Signature Validator v2.0

Security-enhanced validation:
- JSON schema validation
- Regex pattern testing
- Duplicate detection & removal
- False positive testing
- ReDoS detection
- Pattern complexity limits
- Suspicious pattern detection
"""

import json
import re
import sys
import signal
from pathlib import Path
from typing import Optional

SIGNATURES_DIR = Path(__file__).parent.parent / "signatures"

# Security limits
MAX_REGEX_LENGTH = 500
MAX_PATTERN_GROUPS = 10
REGEX_TIMEOUT_MS = 100

# ReDoS dangerous patterns (exponential backtracking)
REDOS_PATTERNS = [
    r'\(\.\+\)\+',      # (.+)+
    r'\(\.\*\)\+',      # (.*)+
    r'\(\.\+\)\*',      # (.+)*
    r'\(\.\*\)\*',      # (.*)*
    r'\([^)]+\+\)\+',   # (a+)+
    r'\([^)]+\*\)\+',   # (a*)+
    r'\(\w\+\)\+',      # (\w+)+
    r'\(\d\+\)\+',      # (\d+)+
]

# Suspicious constructs (potential backdoors)
SUSPICIOUS_PATTERNS = [
    r'\(\?!',           # Negative lookahead - could whitelist attacks
    r'\(\?<!',          # Negative lookbehind
    r'\(\?\(\w+\)',     # Conditional patterns
]

SAFE_EXAMPLES = [
    "How do I prevent prompt injection attacks?",
    "What is a jailbreak in iPhone context?",
    "Explain DAN methodology in project management",
    "Show me an example of a system prompt for education",
    "What are best practices for AI safety?",
    "How does OWASP classify LLM vulnerabilities?",
    "Can you help me debug this code?",
    "Write a story about a detective",
    "Translate this text to Spanish",
    "What's the weather like today?",
]


def is_redos_vulnerable(pattern: str) -> bool:
    """Check if regex pattern is vulnerable to ReDoS."""
    for redos in REDOS_PATTERNS:
        if re.search(redos, pattern):
            return True
    return False


def is_suspicious_pattern(pattern: str) -> Optional[str]:
    """Check for suspicious constructs that could be backdoors."""
    for susp in SUSPICIOUS_PATTERNS:
        if re.search(susp, pattern):
            return susp
    return None


def check_pattern_complexity(pattern: str) -> list[str]:
    """Check pattern complexity limits."""
    issues = []

    if len(pattern) > MAX_REGEX_LENGTH:
        issues.append(f"Pattern too long: {len(pattern)} > {MAX_REGEX_LENGTH}")

    # Count groups
    groups = len(re.findall(r'\([^?]', pattern))
    if groups > MAX_PATTERN_GROUPS:
        issues.append(f"Too many groups: {groups} > {MAX_PATTERN_GROUPS}")

    return issues


def validate_jailbreaks() -> tuple[bool, list[str]]:
    """Validate jailbreaks.json."""
    errors = []
    jailbreaks_file = SIGNATURES_DIR / "jailbreaks.json"
    
    if not jailbreaks_file.exists():
        errors.append("jailbreaks.json not found")
        return False, errors
    
    try:
        with open(jailbreaks_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        errors.append(f"Invalid JSON: {e}")
        return False, errors
    
    # Check required fields
    required = ["version", "patterns"]
    for field in required:
        if field not in data:
            errors.append(f"Missing required field: {field}")
    
    # Validate patterns and remove duplicates
    pattern_ids = set()
    unique_patterns = []
    duplicates_removed = 0
    false_positives = []
    
    for i, pattern in enumerate(data.get("patterns", [])):
        # Check required pattern fields
        if "id" not in pattern:
            errors.append(f"Pattern {i}: missing 'id'")
            continue
        
        # Skip duplicates instead of error
        if pattern["id"] in pattern_ids:
            duplicates_removed += 1
            continue

        pattern_ids.add(pattern["id"])
        unique_patterns.append(pattern)
        
        # Validate regex
        regex = pattern.get("regex")
        if regex:
            # Security checks
            if is_redos_vulnerable(regex):
                print(f"[SECURITY] ReDoS vulnerable: {pattern['id']}")
                errors.append(f"ReDoS vulnerable: {pattern['id']}")
                continue

            susp = is_suspicious_pattern(regex)
            if susp:
                print(
                    f"[SECURITY] Suspicious pattern in {pattern['id']}: {susp}")

            complexity_issues = check_pattern_complexity(regex)
            for issue in complexity_issues:
                print(f"[SECURITY] {pattern['id']}: {issue}")

            try:
                compiled = re.compile(regex)
                
                # Test against safe examples
                for safe in SAFE_EXAMPLES:
                    if compiled.search(safe):
                        false_positives.append(f"{pattern['id']} matches safe: '{safe[:50]}...'")
                        
            except re.error as e:
                errors.append(f"Invalid regex in {pattern['id']}: {e}")
    
    # Save deduplicated file if duplicates were found
    if duplicates_removed > 0:
        print(f"[INFO] Removed {duplicates_removed} duplicate patterns")
        data["patterns"] = unique_patterns
        data["total_patterns"] = len(unique_patterns)
        with open(jailbreaks_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    if false_positives:
        print(f"[WARN] {len(false_positives)} potential false positives:")
        for fp in false_positives[:5]:  # Show first 5
            print(f"  - {fp}")
    
    print(f"[INFO] Validated {len(pattern_ids)} patterns in jailbreaks.json")
    return len(errors) == 0, errors


def validate_keywords() -> tuple[bool, list[str]]:
    """Validate keywords.json."""
    errors = []
    keywords_file = SIGNATURES_DIR / "keywords.json"
    
    if not keywords_file.exists():
        errors.append("keywords.json not found")
        return False, errors
    
    try:
        with open(keywords_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        errors.append(f"Invalid JSON: {e}")
        return False, errors
    
    # Check required fields
    if "keyword_sets" not in data:
        errors.append("Missing 'keyword_sets' field")
        return False, errors
    
    total_keywords = 0
    for kw_set in data["keyword_sets"]:
        if "keywords" not in kw_set:
            errors.append(f"Keyword set {kw_set.get('id', '?')} missing 'keywords'")
        else:
            total_keywords += len(kw_set["keywords"])
    
    print(f"[INFO] Validated {total_keywords} keywords in keywords.json")
    return len(errors) == 0, errors


def validate_pii() -> tuple[bool, list[str]]:
    """Validate pii.json."""
    errors = []
    pii_file = SIGNATURES_DIR / "pii.json"
    
    if not pii_file.exists():
        errors.append("pii.json not found")
        return False, errors
    
    try:
        with open(pii_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        errors.append(f"Invalid JSON: {e}")
        return False, errors
    
    # Validate regex patterns
    for pattern in data.get("patterns", []):
        regex = pattern.get("regex")
        if regex:
            try:
                re.compile(regex)
            except re.error as e:
                errors.append(f"Invalid regex in {pattern.get('id', '?')}: {e}")
    
    print(f"[INFO] Validated {len(data.get('patterns', []))} patterns in pii.json")
    return len(errors) == 0, errors


def main():
    """Main entry point."""
    print("=" * 60)
    print("SENTINEL Signature Validator")
    print("=" * 60)
    
    all_valid = True
    all_errors = []
    
    # Validate each file
    valid, errors = validate_jailbreaks()
    all_valid = all_valid and valid
    all_errors.extend(errors)
    
    valid, errors = validate_keywords()
    all_valid = all_valid and valid
    all_errors.extend(errors)
    
    valid, errors = validate_pii()
    all_valid = all_valid and valid
    all_errors.extend(errors)
    
    print("=" * 60)
    
    if all_errors:
        print(f"[ERROR] Validation failed with {len(all_errors)} errors:")
        for err in all_errors:
            print(f"  - {err}")
        sys.exit(1)
    else:
        print("[OK] All signatures valid!")
        sys.exit(0)


if __name__ == "__main__":
    main()
