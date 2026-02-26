"""Frequency analysis of 87K jailbreak patterns to find discriminative tokens."""
import json
import re
from collections import Counter

SIG_PATH = r"c:\AISecurity\sentinel-community\signatures\jailbreaks.json"

with open(SIG_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

patterns = data["patterns"]
safe = data.get("safe_examples", [])

# Tokenize


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Zа-яА-ЯёЁ]+", text.lower())


# Count token frequencies in jailbreaks
jb_counter: Counter[str] = Counter()
for p in patterns:
    tokens = tokenize(p.get("pattern", ""))
    jb_counter.update(set(tokens))  # set = presence, not frequency

# Count in safe examples
safe_counter: Counter[str] = Counter()
safe_texts = []
if isinstance(safe, list):
    for s in safe:
        text = s if isinstance(s, str) else s.get("text", s.get("pattern", ""))
        if isinstance(text, str):
            safe_texts.append(text)
            safe_counter.update(set(tokenize(text)))

print(f"Jailbreak patterns: {len(patterns)}")
print(f"Safe examples: {len(safe_texts)}")
print()

# Top tokens in jailbreaks (appearing in >5% of patterns)
n = len(patterns)
print("=== Top 50 tokens by jailbreak frequency ===")
for token, count in jb_counter.most_common(50):
    pct = count * 100 / n
    safe_pct = safe_counter.get(token, 0) * 100 / max(len(safe_texts), 1)
    ratio = pct / max(safe_pct, 0.1)
    marker = " ***" if ratio > 3 and pct > 5 else ""
    print(
        f"  {token:25s}  jb={pct:5.1f}%  safe={safe_pct:5.1f}%  ratio={ratio:5.1f}{marker}")

# Bigrams in jailbreaks
print("\n=== Top 30 bigrams ===")
bigram_counter: Counter[str] = Counter()
for p in patterns[:10000]:
    tokens = tokenize(p.get("pattern", ""))
    for i in range(len(tokens) - 1):
        bigram_counter[tokens[i] + " " + tokens[i + 1]] += 1

for bg, count in bigram_counter.most_common(30):
    print(f"  {bg:35s}  {count:5d}")

# Attack class distribution
print("\n=== Attack classes ===")
ac_counter: Counter[str] = Counter()
for p in patterns:
    ac_counter[p.get("attack_class", "?")] += 1
for ac, count in ac_counter.most_common(10):
    print(f"  {ac}: {count} ({count*100//len(patterns)}%)")

# Bypass techniques
print("\n=== Bypass techniques (top 15) ===")
bt_counter: Counter[str] = Counter()
for p in patterns:
    bt_counter[p.get("bypass_technique", "?")] += 1
for bt, count in bt_counter.most_common(15):
    print(f"  {bt:30s}  {count:5d}")
