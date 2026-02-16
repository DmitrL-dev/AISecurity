"""Benchmark: run detectors on real 87K jailbreak dataset."""
from micro_swarm.ncd import AdversarialDetector
from micro_swarm.kolmogorov import KolmogorovDetector
import json
import time
import sys

sys.path.insert(0, r"c:\AISecurity\sentinel-community\micro-swarm")


SIG_PATH = r"c:\AISecurity\sentinel-community\signatures\jailbreaks.json"

with open(SIG_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

patterns = data["patterns"]
print(f"Total patterns: {len(patterns)}")

# Length distribution
lengths = [len(p.get("pattern", "")) for p in patterns]
short = sum(1 for l in lengths if l < 50)
medium = sum(1 for l in lengths if 50 <= l < 200)
long_ = sum(1 for l in lengths if l >= 200)
print(f"Short (<50):    {short} ({short*100//len(patterns)}%)")
print(f"Medium (50-200): {medium} ({medium*100//len(patterns)}%)")
print(f"Long (200+):    {long_} ({long_*100//len(patterns)}%)")
print(f"Avg length:     {sum(lengths)//len(lengths)} chars")
print()

# Show samples
print("=== Sample MEDIUM patterns ===")
med = [p for p in patterns if 50 <= len(p.get("pattern", "")) < 200]
for p in med[:5]:
    ac = p.get("attack_class", "?")
    txt = p["pattern"][:120]
    print(f"  [{ac}] {txt}")
print()

print("=== Sample LONG patterns ===")
lng = [p for p in patterns if len(p.get("pattern", "")) >= 200]
for p in lng[:3]:
    ac = p.get("attack_class", "?")
    txt = p["pattern"][:150]
    print(f"  [{ac}] {txt}...")
print()

# Benchmark Kolmogorov on ALL patterns (min_length=20 to catch short ones too)
kd = KolmogorovDetector(min_length=20)
kd_results = {"natural": 0, "constructed": 0,
              "random_noise": 0, "too_short": 0}
t0 = time.perf_counter()

for p in patterns:
    text = p.get("pattern", "")
    if text:
        r = kd.analyze(text)
        kd_results[r.verdict] = kd_results.get(r.verdict, 0) + 1

elapsed = time.perf_counter() - t0
total_analyzed = sum(kd_results.values())
print(f"=== Kolmogorov on ALL {total_analyzed} patterns ({elapsed:.2f}s) ===")
for k, v in sorted(kd_results.items()):
    pct = v * 100 / max(total_analyzed, 1)
    print(f"  {k}: {v} ({pct:.1f}%)")

# Detection rate = constructed + random_noise
detected = kd_results.get("constructed", 0) + kd_results.get("random_noise", 0)
print(
    f"\n  DETECTION RATE: {detected}/{total_analyzed} = {detected*100/max(total_analyzed,1):.1f}%")
print()

# NCD on sample of 100 medium+ patterns
print("=== NCD AdversarialDetector on 100 medium+ patterns ===")
ad = AdversarialDetector()
ncd_results = {"natural": 0, "suspicious": 0, "adversarial": 0}
med_long = [p for p in patterns if len(p.get("pattern", "")) >= 50][:100]
t0 = time.perf_counter()
for p in med_long:
    r = ad.analyze(p["pattern"])
    ncd_results[r.verdict] = ncd_results.get(r.verdict, 0) + 1
elapsed = time.perf_counter() - t0
print(f"  Time: {elapsed:.2f}s")
for k, v in sorted(ncd_results.items()):
    print(f"  {k}: {v}")
detected_ncd = ncd_results.get(
    "suspicious", 0) + ncd_results.get("adversarial", 0)
print(f"  NCD DETECTION RATE: {detected_ncd}/100 = {detected_ncd}%")
