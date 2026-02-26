"""Train jailbreak detection micro-models on 87K real dataset.

Loads jailbreak patterns as positives, generates synthetic negatives,
extracts features via TextFeatureExtractor, trains 4 micro-models
via the SwarmOrchestrator, and evaluates on a held-out test set.

Usage:
    python scripts/train_jailbreak.py
"""

from __future__ import annotations
from micro_swarm.presets.jailbreak import build_jailbreak
from micro_swarm.text_features import TextFeatureExtractor

import json
import random
import sys
import time

sys.path.insert(0, r"c:\AISecurity\sentinel-community\micro-swarm")


SIG_PATH = r"c:\AISecurity\sentinel-community\signatures\jailbreaks.json"

# Synthetic negative samples — diverse natural text
NATURAL_SAMPLES = [
    "What is the weather forecast for tomorrow in New York City?",
    "Can you help me write a professional email to my colleague?",
    "Tell me about the history of the Roman Empire.",
    "How do I make chocolate chip cookies from scratch?",
    "What are the best practices for writing unit tests in Python?",
    "Please summarize the main points of this research paper.",
    "How do I set up a PostgreSQL database on Ubuntu?",
    "What is the difference between TCP and UDP protocols?",
    "Can you explain how photosynthesis works in plants?",
    "I need help debugging this JavaScript function.",
    "What are the symptoms of seasonal allergies?",
    "How do I configure a reverse proxy with Nginx?",
    "Please help me plan a 7-day trip to Japan.",
    "What is the capital of Australia and its population?",
    "How do I create a REST API using Flask?",
    "Can you review my resume and suggest improvements?",
    "What are the main differences between Python and Go?",
    "How do machine learning models handle missing data?",
    "What is the best way to learn a new programming language?",
    "Can you help me understand quantum computing basics?",
    "The quarterly sales report shows a 15% increase in revenue.",
    "Our team meeting is scheduled for 3 PM on Wednesday.",
    "Please forward the invoice to the accounting department.",
    "The new software update includes several bug fixes.",
    "I would like to schedule a dentist appointment for next week.",
    "What time does the library close on weekends?",
    "How many calories are in a serving of Greek yogurt?",
    "Can you recommend a good book on data structures?",
    "What is the current exchange rate between USD and EUR?",
    "How do I renew my driver's license online?",
    "Расскажите о преимуществах микросервисной архитектуры.",
    "Какая погода будет завтра в Москве?",
    "Помогите составить план тренировок на неделю.",
    "Как приготовить борщ по классическому рецепту?",
    "Объясните принцип работы нейронных сетей.",
    "Какие документы нужны для получения загранпаспорта?",
    "Посоветуйте хороший фильм на вечер.",
    "Как настроить VPN на роутере?",
    "Расскажите об истории создания Python.",
    "Какие есть способы оптимизации SQL запросов?",
]


def generate_negatives(count: int) -> list[str]:
    """Generate diverse negative samples by combining templates."""
    topics = [
        "cooking", "travel", "sports", "music", "science",
        "history", "technology", "health", "education", "business",
        "gardening", "photography", "architecture", "literature", "math",
    ]
    actions = [
        "Tell me about", "Explain how", "What is the best way to",
        "Can you describe", "How does", "What are the benefits of",
        "Please help me understand", "I would like to learn about",
    ]
    result = list(NATURAL_SAMPLES)
    rng = random.Random(42)
    while len(result) < count:
        action = rng.choice(actions)
        topic = rng.choice(topics)
        variants = [
            f"{action} {topic} in modern society.",
            f"{action} {topic} and its applications.",
            f"{action} {topic} for beginners.",
            f"I have a question about {topic}. {action} the basics.",
        ]
        result.append(rng.choice(variants))
    return result[:count]


def main() -> None:
    """Train and evaluate jailbreak detection models."""
    # Load data
    print("Loading jailbreak data...")
    with open(SIG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    positives = [p["pattern"] for p in data["patterns"] if p.get("pattern")]
    print(f"  Positive samples: {len(positives)}")

    # Generate negatives (1:1 ratio)
    neg_count = min(len(positives), 5000)  # cap for speed
    negatives = generate_negatives(neg_count)
    print(f"  Negative samples: {len(negatives)}")

    # Extract features
    print("\nExtracting features...")
    ext = TextFeatureExtractor()

    pos_subset = random.Random(42).sample(positives, min(5000, len(positives)))

    t0 = time.perf_counter()
    pos_features = [ext.extract(text).as_dict() for text in pos_subset]
    neg_features = [ext.extract(text).as_dict() for text in negatives]
    elapsed = time.perf_counter() - t0
    print(
        f"  Extracted {len(pos_features) + len(neg_features)} in {elapsed:.2f}s")

    # Split train/test (80/20)
    rng = random.Random(42)
    rng.shuffle(pos_features)
    rng.shuffle(neg_features)

    pos_train = pos_features[: int(0.8 * len(pos_features))]
    pos_test = pos_features[int(0.8 * len(pos_features)):]
    neg_train = neg_features[: int(0.8 * len(neg_features))]
    neg_test = neg_features[int(0.8 * len(neg_features)):]

    print(f"  Train: {len(pos_train)} pos + {len(neg_train)} neg")
    print(f"  Test:  {len(pos_test)} pos + {len(neg_test)} neg")

    # Build swarm
    print("\nTraining micro-models...")
    swarm = build_jailbreak()

    # Train: feed positive samples with label 1.0
    t0 = time.perf_counter()
    train_data = [(f, 1.0) for f in pos_train] + [(f, 0.0) for f in neg_train]
    rng.shuffle(train_data)

    for features, label in train_data:
        result = swarm.predict(features)
        # Simple online learning: adjust based on error
        error = label - result.final_score
        if abs(error) > 0.1:
            swarm.train_step(features, label)

    elapsed = time.perf_counter() - t0
    print(f"  Training completed in {elapsed:.2f}s")

    # Evaluate
    print("\nEvaluating on test set...")

    # Test positives (should score high)
    pos_scores = [swarm.predict(f).final_score for f in pos_test]
    neg_scores = [swarm.predict(f).final_score for f in neg_test]

    threshold = 0.5
    tp = sum(1 for s in pos_scores if s > threshold)
    fn = sum(1 for s in pos_scores if s <= threshold)
    tn = sum(1 for s in neg_scores if s <= threshold)
    fp = sum(1 for s in neg_scores if s > threshold)

    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    f1 = 2 * precision * recall / max(precision + recall, 0.001)
    accuracy = (tp + tn) / max(tp + tn + fp + fn, 1)

    print(f"\n  Threshold: {threshold}")
    print(f"  TP={tp} FN={fn} FP={fp} TN={tn}")
    print(f"  Accuracy:  {accuracy:.3f}")
    print(f"  Precision: {precision:.3f}")
    print(f"  Recall:    {recall:.3f}")
    print(f"  F1:        {f1:.3f}")

    # Score distribution
    print("\n  Score distribution (positives):")
    for bucket in [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]:
        count = sum(1 for s in pos_scores if bucket <= s < bucket + 0.1)
        bar = "#" * (count * 40 // max(len(pos_scores), 1))
        print(f"    [{bucket:.1f}-{bucket+0.1:.1f}): {count:4d} {bar}")

    print("\n  Score distribution (negatives):")
    for bucket in [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]:
        count = sum(1 for s in neg_scores if bucket <= s < bucket + 0.1)
        bar = "#" * (count * 40 // max(len(neg_scores), 1))
        print(f"    [{bucket:.1f}-{bucket+0.1:.1f}): {count:4d} {bar}")


if __name__ == "__main__":
    main()
