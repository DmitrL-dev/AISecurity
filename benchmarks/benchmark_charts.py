"""
SENTINEL Publication-Quality Benchmark Visualizations
======================================================

Generates matplotlib charts for benchmark reports.
"""

from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import json
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend


def load_results(path: str = "benchmarks/benchmark_results.json") -> dict:
    """Load benchmark results."""
    with open(path, 'r') as f:
        return json.load(f)


def create_recall_comparison_chart(results: dict, output_dir: str = "benchmarks/charts"):
    """Create bar chart comparing recall across engines."""
    Path(output_dir).mkdir(exist_ok=True)

    engines = []
    recalls = []
    colors = []

    color_map = {
        'hybrid': '#4CAF50',      # Green - best
        'semantic': '#2196F3',     # Blue
        'injection': '#FF9800',    # Orange
        'voice_jailbreak': '#9C27B0',  # Purple
        'prompt_guard': '#F44336',  # Red
    }

    for engine, metrics in sorted(results.items(),
                                  key=lambda x: x[1].get('recall', 0),
                                  reverse=True):
        engines.append(engine)
        recalls.append(metrics.get('recall', 0) * 100)
        colors.append(color_map.get(engine, '#757575'))

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(engines, recalls, color=colors, height=0.6)

    # Add value labels
    for bar, recall in zip(bars, recalls):
        ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2,
                f'{recall:.1f}%', va='center', fontsize=11, fontweight='bold')

    ax.set_xlabel('Recall (%)', fontsize=12)
    ax.set_title('SENTINEL Detection Engine Recall Comparison',
                 fontsize=14, fontweight='bold')
    ax.set_xlim(0, 100)
    ax.axvline(x=85, color='#4CAF50', linestyle='--',
               alpha=0.5, label='Target (85%)')
    ax.legend()

    # Style
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.tight_layout()

    output_path = f"{output_dir}/recall_comparison.png"
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {output_path}")
    return output_path


def create_precision_recall_chart(results: dict, output_dir: str = "benchmarks/charts"):
    """Create scatter plot of precision vs recall."""
    Path(output_dir).mkdir(exist_ok=True)

    fig, ax = plt.subplots(figsize=(10, 8))

    color_map = {
        'hybrid': '#4CAF50',
        'semantic': '#2196F3',
        'injection': '#FF9800',
        'voice_jailbreak': '#9C27B0',
        'prompt_guard': '#F44336',
    }

    for engine, metrics in results.items():
        precision = metrics.get('precision', 0) * 100
        recall = metrics.get('recall', 0) * 100
        f1 = metrics.get('f1', 0) * 100

        # Size based on F1
        size = f1 * 5 + 50

        ax.scatter(recall, precision, s=size,
                   c=color_map.get(engine, '#757575'),
                   alpha=0.7, label=f'{engine} (F1={f1:.1f}%)')

        # Label
        ax.annotate(engine, (recall, precision),
                    xytext=(5, 5), textcoords='offset points',
                    fontsize=10, fontweight='bold')

    ax.set_xlabel('Recall (%)', fontsize=12)
    ax.set_ylabel('Precision (%)', fontsize=12)
    ax.set_title('SENTINEL Precision-Recall Trade-off',
                 fontsize=14, fontweight='bold')
    ax.set_xlim(0, 105)
    ax.set_ylim(0, 105)

    # Add quadrant lines
    ax.axhline(y=80, color='gray', linestyle='--', alpha=0.3)
    ax.axvline(x=80, color='gray', linestyle='--', alpha=0.3)
    ax.fill_between([80, 105], 80, 105, alpha=0.1,
                    color='green', label='Target Zone')

    ax.legend(loc='lower left', fontsize=9)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    output_path = f"{output_dir}/precision_recall.png"
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {output_path}")
    return output_path


def create_confusion_matrix_heatmap(results: dict, output_dir: str = "benchmarks/charts"):
    """Create confusion matrix heatmap for best engine."""
    Path(output_dir).mkdir(exist_ok=True)

    # Get best engine (hybrid)
    best = max(results.items(), key=lambda x: x[1].get('f1', 0))
    engine_name, metrics = best
    cm = metrics.get('confusion_matrix', {})

    tp = cm.get('TP', 0)
    fp = cm.get('FP', 0)
    fn = cm.get('FN', 0)
    tn = cm.get('TN', 0)

    matrix = np.array([[tp, fp], [fn, tn]])

    fig, ax = plt.subplots(figsize=(8, 6))

    im = ax.imshow(matrix, cmap='Blues')

    # Labels
    ax.set_xticks([0, 1])
    ax.set_yticks([0, 1])
    ax.set_xticklabels(['Detected', 'Not Detected'])
    ax.set_yticklabels(['Attack', 'Benign'])
    ax.set_xlabel('Prediction', fontsize=12)
    ax.set_ylabel('Actual', fontsize=12)
    ax.set_title(f'{engine_name.upper()} Confusion Matrix',
                 fontsize=14, fontweight='bold')

    # Values
    for i in range(2):
        for j in range(2):
            val = matrix[i, j]
            color = 'white' if val > matrix.max() / 2 else 'black'
            labels_map = {(0, 0): 'TP', (0, 1): 'FP',
                          (1, 0): 'FN', (1, 1): 'TN'}
            ax.text(j, i, f'{labels_map[(i,j)]}\n{val}',
                    ha='center', va='center', color=color, fontsize=14, fontweight='bold')

    plt.colorbar(im, ax=ax, label='Count')
    plt.tight_layout()

    output_path = f"{output_dir}/confusion_matrix.png"
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {output_path}")
    return output_path


def create_improvement_timeline(output_dir: str = "benchmarks/charts"):
    """Create timeline of recall improvements."""
    Path(output_dir).mkdir(exist_ok=True)

    stages = ['Baseline', '+Patterns', '+Semantic',
              '+Prototypes', '+Threshold', 'Final']
    recalls = [4.5, 38.5, 64.2, 72.3, 79.1, 85.1]
    tps = [9, 337, 774, 872, 954, 1026]

    fig, ax1 = plt.subplots(figsize=(12, 6))

    x = np.arange(len(stages))
    width = 0.35

    bars1 = ax1.bar(x - width/2, recalls, width,
                    label='Recall (%)', color='#4CAF50', alpha=0.8)
    ax1.set_ylabel('Recall (%)', color='#4CAF50', fontsize=12)
    ax1.tick_params(axis='y', labelcolor='#4CAF50')
    ax1.set_ylim(0, 100)

    # Add value labels
    for bar, val in zip(bars1, recalls):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                 f'{val:.1f}%', ha='center', fontsize=9, fontweight='bold')

    ax2 = ax1.twinx()
    bars2 = ax2.bar(x + width/2, tps, width,
                    label='True Positives', color='#2196F3', alpha=0.8)
    ax2.set_ylabel('True Positives', color='#2196F3', fontsize=12)
    ax2.tick_params(axis='y', labelcolor='#2196F3')
    ax2.set_ylim(0, 1200)

    for bar, val in zip(bars2, tps):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 20,
                 f'{val}', ha='center', fontsize=9, fontweight='bold')

    ax1.set_xlabel('Development Stage', fontsize=12)
    ax1.set_title('SENTINEL Detection Improvement Timeline',
                  fontsize=14, fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(stages)

    # Legend
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')

    plt.tight_layout()
    output_path = f"{output_dir}/improvement_timeline.png"
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {output_path}")
    return output_path


def generate_all_charts(results_path: str = "benchmarks/benchmark_results.json"):
    """Generate all visualization charts."""
    results = load_results(results_path)

    print("Generating SENTINEL benchmark visualizations...")
    print("-" * 50)

    charts = []
    charts.append(create_recall_comparison_chart(results))
    charts.append(create_precision_recall_chart(results))
    charts.append(create_confusion_matrix_heatmap(results))
    charts.append(create_improvement_timeline())

    print("-" * 50)
    print(f"Generated {len(charts)} charts in benchmarks/charts/")

    return charts


if __name__ == "__main__":
    generate_all_charts()
