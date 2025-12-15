#!/usr/bin/env python3
"""Find and remove API keys from jailbreaks.json"""
import json
import re

JAILBREAKS_FILE = "signatures/jailbreaks.json"

# Patterns to detect secrets
SECRET_PATTERNS = [
    (r'sk-[a-zA-Z0-9]{20,}', 'OpenAI API Key'),
    (r'AKIA[A-Z0-9]{16}', 'AWS Access Key'),
    (r'AIza[0-9A-Za-z\-_]{35}', 'Google API Key'),
]

with open(JAILBREAKS_FILE, 'r', encoding='utf-8') as f:
    data = json.load(f)

found_secrets = []
cleaned_patterns = []

for p in data['patterns']:
    text = str(p.get('pattern', '')) + str(p.get('full_text', ''))
    has_secret = False
    
    for regex, name in SECRET_PATTERNS:
        matches = re.findall(regex, text)
        if matches:
            found_secrets.append({
                'id': p.get('id'),
                'source': p.get('source'),
                'secret_type': name,
                'secrets': matches[:2]  # First 2
            })
            has_secret = True
            break
    
    if not has_secret:
        cleaned_patterns.append(p)

print(f"Found {len(found_secrets)} patterns with secrets:")
for s in found_secrets[:10]:
    print(f"  Source: {s['source']}, ID: {s['id']}, Type: {s['secret_type']}")
    print(f"    Secrets: {s['secrets']}")

print(f"\nCleaning {len(found_secrets)} patterns...")
data['patterns'] = cleaned_patterns
data['total_patterns'] = len(cleaned_patterns)

with open(JAILBREAKS_FILE, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"Saved {len(cleaned_patterns)} clean patterns")
