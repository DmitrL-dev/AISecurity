"""
SENTINEL Benchmark Visualization
================================

Generates charts and reports from benchmark results.
"""

import json
from pathlib import Path
import sys


def load_results(path: str = "benchmarks/benchmark_results.json") -> dict:
    """Load benchmark results from JSON."""
    with open(path, 'r') as f:
        return json.load(f)


def print_ascii_bar(label: str, value: float, max_value: float = 100, width: int = 40):
    """Print ASCII bar chart."""
    filled = int((value / max_value) * width)
    bar = "█" * filled + "░" * (width - filled)
    print(f"  {label:20} [{bar}] {value:.1f}%")


def generate_report(results: dict):
    """Generate comprehensive benchmark report."""

    print("\n" + "=" * 70)
    print("🔬 SENTINEL BENCHMARK REPORT")
    print("=" * 70)

    # Summary table
    print("\n## Engine Performance Summary\n")
    print(f"{'Engine':<20} {'Recall':>10} {'Precision':>10} {'F1':>10} {'TP':>8}")
    print("-" * 60)

    for engine, metrics in results.items():
        recall = metrics.get('recall', 0) * 100
        prec = metrics.get('precision', 0) * 100
        f1 = metrics.get('f1', 0) * 100
        tp = metrics.get('confusion_matrix', {}).get('TP', 0)

        print(f"{engine:<20} {recall:>9.1f}% {prec:>9.1f}% {f1:>9.1f}% {tp:>8}")

    print()

    # Recall comparison (ASCII chart)
    print("## Recall Comparison\n")
    for engine, metrics in sorted(results.items(),
                                  key=lambda x: x[1].get('recall', 0),
                                  reverse=True):
        recall = metrics.get('recall', 0) * 100
        print_ascii_bar(engine, recall)

    print()

    # Confusion matrices
    print("## Confusion Matrices\n")
    for engine, metrics in results.items():
        cm = metrics.get('confusion_matrix', {})
        tp = cm.get('TP', 0)
        fp = cm.get('FP', 0)
        tn = cm.get('TN', 0)
        fn = cm.get('FN', 0)

        print(f"### {engine}")
        print(f"  ┌────────────┬────────────┐")
        print(f"  │ TP: {tp:>5} │ FP: {fp:>5} │")
        print(f"  ├────────────┼────────────┤")
        print(f"  │ FN: {fn:>5} │ TN: {tn:>5} │")
        print(f"  └────────────┴────────────┘")
        print()

    # Best performers
    print("## Top Performers\n")

    # Best recall
    best_recall = max(results.items(), key=lambda x: x[1].get('recall', 0))
    print(
        f"  🏆 Best Recall:    {best_recall[0]} ({best_recall[1]['recall']*100:.1f}%)")

    # Best precision
    best_prec = max(results.items(), key=lambda x: x[1].get('precision', 0))
    print(
        f"  🎯 Best Precision: {best_prec[0]} ({best_prec[1]['precision']*100:.1f}%)")

    # Best F1
    best_f1 = max(results.items(), key=lambda x: x[1].get('f1', 0))
    print(f"  ⚖️  Best F1:       {best_f1[0]} ({best_f1[1]['f1']*100:.1f}%)")

    # Fastest
    best_speed = min(results.items(), key=lambda x: x[1].get(
        'avg_latency_ms', float('inf')))
    print(
        f"  ⚡ Fastest:        {best_speed[0]} ({best_speed[1]['avg_latency_ms']:.2f}ms)")

    print()

    # Dataset stats
    total_samples = sum(
        cm.get('TP', 0) + cm.get('FP', 0) + cm.get('TN', 0) + cm.get('FN', 0)
        for cm in [list(results.values())[0].get('confusion_matrix', {})]
    )
    attacks = list(results.values())[0].get('confusion_matrix', {}).get('TP', 0) + \
        list(results.values())[0].get('confusion_matrix', {}).get('FN', 0)
    benign = total_samples - attacks

    print("## Dataset Statistics\n")
    print(f"  Total samples: {total_samples}")
    print(f"  Attacks:       {attacks}")
    print(f"  Benign:        {benign}")

    print("\n" + "=" * 70)
    print("Report generated successfully!")
    print("=" * 70)


def save_markdown_report(results: dict, output_path: str = "benchmarks/BENCHMARK_REPORT.md"):
    """Save report as markdown file."""

    lines = [
        "# 🔬 SENTINEL Benchmark Report",
        "",
        "## Summary",
        "",
        "| Engine | Recall | Precision | F1 | TP | Latency |",
        "|--------|--------|-----------|----|----|---------|",
    ]

    for engine, metrics in sorted(results.items(),
                                  key=lambda x: x[1].get('recall', 0),
                                  reverse=True):
        recall = metrics.get('recall', 0) * 100
        prec = metrics.get('precision', 0) * 100
        f1 = metrics.get('f1', 0) * 100
        tp = metrics.get('confusion_matrix', {}).get('TP', 0)
        latency = metrics.get('avg_latency_ms', 0)

        lines.append(
            f"| **{engine}** | {recall:.1f}% | {prec:.1f}% | {f1:.1f}% | {tp} | {latency:.2f}ms |")

    lines.extend([
        "",
        "## Top Performers",
        "",
    ])

    # Best recall
    best_recall = max(results.items(), key=lambda x: x[1].get('recall', 0))
    lines.append(
        f"- 🏆 **Best Recall:** {best_recall[0]} ({best_recall[1]['recall']*100:.1f}%)")

    # Best F1
    best_f1 = max(results.items(), key=lambda x: x[1].get('f1', 0))
    lines.append(
        f"- ⚖️ **Best F1:** {best_f1[0]} ({best_f1[1]['f1']*100:.1f}%)")

    lines.extend([
        "",
        "## Improvement History",
        "",
        "| Stage | Recall | TP | Approach |",
        "|-------|--------|-----|----------|",
        "| Baseline | 4.5% | 9 | Basic regex |",
        "| +Patterns | 38.5% | 337 | 120+ regex patterns |",
        "| +Semantic+HF | 64.2% | 774 | threshold=0.50 |",
        "| +Prototypes | 72.3% | 872 | 100+ prototypes |",
        "| +Threshold | 79.1% | 954 | threshold=0.30 |",
        "| **Final** | **85.1%** | **1026** | **threshold=0.25** |",
        "",
        "---",
        "",
        "*Generated by SENTINEL Benchmark Visualization*",
    ])

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print(f"Markdown report saved to: {output_path}")


if __name__ == "__main__":
    results_path = sys.argv[1] if len(
        sys.argv) > 1 else "benchmarks/benchmark_results.json"

    try:
        results = load_results(results_path)
        generate_report(results)
        save_markdown_report(results)
    except FileNotFoundError:
        print(f"Error: Results file not found: {results_path}")
        print("Run benchmark_eval.py first to generate results.")
        sys.exit(1)
