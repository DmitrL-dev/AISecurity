"""Quick benchmark: TextFeatureExtractor on 87K jailbreaks."""
from micro_swarm.text_features import TextFeatureExtractor
import json
import sys
import time

sys.path.insert(0, r"c:\AISecurity\sentinel-community\micro-swarm")


SIG_PATH = r"c:\AISecurity\sentinel-community\signatures\jailbreaks.json"
with open(SIG_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

patterns = data["patterns"]
ext = TextFeatureExtractor()

# Run on all patterns
t0 = time.perf_counter()
all_features = []
for p in patterns:
    text = p.get("pattern", "")
    if text:
        feats = ext.extract(text)
        all_features.append(feats.features)

elapsed = time.perf_counter() - t0
print(
    f"Extracted features from {len(all_features)} patterns in {elapsed:.2f}s")
print(f"Speed: {len(all_features)/elapsed:.0f} patterns/sec")
print()

# For each feature, compute mean and what % of patterns have non-zero value
feature_names = sorted(all_features[0].keys())
print(f"{'Feature':<35s}  {'Mean':>6s}  {'Non-zero%':>8s}  {'Max':>6s}")
print("-" * 65)
for fname in feature_names:
    values = [f[fname] for f in all_features]
    mean = sum(values) / len(values)
    nonzero = sum(1 for v in values if v > 0.001) * 100 / len(values)
    mx = max(values)
    print(f"  {fname:<33s}  {mean:6.3f}  {nonzero:7.1f}%  {mx:6.3f}")

# Simple threshold detection: total_keyword_density > 0.05
print()
threshold = 0.05
detected = sum(
    1 for f in all_features if f["total_keyword_density"] > threshold)
print(
    f"Simple threshold (total_keyword > {threshold}): {detected}/{len(all_features)} = {detected*100/len(all_features):.1f}%")

# Multi-feature: any lexical > 0.02
detected2 = sum(1 for f in all_features if (
    f["injection_keyword_density"] > 0.02
    or f["role_keyword_density"] > 0.02
    or f["secret_keyword_density"] > 0.02
    or f["bypass_keyword_density"] > 0.02
    or f["suspicious_bigram_count"] > 0.05
    or f["role_assignment_score"] > 0
    or f["constraint_removal_score"] > 0
))
print(
    f"Multi-feature (any lexical signal): {detected2}/{len(all_features)} = {detected2*100/len(all_features):.1f}%")

# What about patterns with ZERO lexical signal?
zero_signal = [i for i, f in enumerate(all_features) if (
    f["injection_keyword_density"] == 0
    and f["role_keyword_density"] == 0
    and f["secret_keyword_density"] == 0
    and f["bypass_keyword_density"] == 0
    and f["generation_keyword_density"] == 0
    and f["suspicious_bigram_count"] == 0
    and f["role_assignment_score"] == 0
    and f["constraint_removal_score"] == 0
)]
print(
    f"\nZero lexical signal: {len(zero_signal)} patterns ({len(zero_signal)*100/len(all_features):.1f}%)")
if zero_signal:
    print("Samples with zero signal:")
    for idx in zero_signal[:5]:
        text = patterns[idx].get("pattern", "")[:120]
        bt = patterns[idx].get("bypass_technique", "?")
        print(f"  [{bt}] {text}")
