#!/usr/bin/env python3
"""
SENTINEL + Nemotron 3 Integration
Dataset Converter: jailbreaks.json → Alpaca training format

Converts SENTINEL threat signatures into fine-tuning dataset for Nemotron 3 Nano.
"""

import json
import random
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass
import hashlib


@dataclass
class TrainingSample:
    """Single training sample in Alpaca format."""
    instruction: str
    input: str
    output: str
    category: str  # For stratified splitting


def load_jailbreaks(path: str = "signatures/jailbreaks.json") -> Dict[str, Any]:
    """Load jailbreaks signatures."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def generate_safe_prompts(count: int = 5000) -> List[str]:
    """Generate safe/benign prompts for negative samples."""
    templates = [
        "What is {topic}?",
        "Can you explain {topic}?",
        "Help me understand {topic}",
        "Write a summary about {topic}",
        "Tell me about {topic}",
        "How does {topic} work?",
        "What are the benefits of {topic}?",
        "Describe {topic} in simple terms",
        "Give me an overview of {topic}",
        "I need help with {topic}",
    ]
    
    topics = [
        "machine learning", "Python programming", "data science", 
        "web development", "cloud computing", "database design",
        "software engineering", "project management", "API design",
        "testing strategies", "code review", "documentation",
        "Git workflows", "CI/CD pipelines", "containerization",
        "microservices", "REST APIs", "GraphQL", "authentication",
        "encryption", "network security basics", "best practices",
        "algorithm optimization", "data structures", "debugging",
        "performance tuning", "code refactoring", "design patterns",
        "clean code", "agile methodology", "DevOps culture",
        "customer service", "travel planning", "recipe ideas",
        "fitness tips", "learning languages", "book recommendations",
        "movie suggestions", "music theory", "photography",
        "gardening", "home improvement", "financial planning",
        "career advice", "interview preparation", "resume writing",
    ]
    
    prompts = []
    for _ in range(count):
        template = random.choice(templates)
        topic = random.choice(topics)
        prompts.append(template.format(topic=topic))
    
    return prompts


def convert_to_training_format(
    jailbreaks: Dict[str, Any],
    include_safe: bool = True,
    safe_ratio: float = 0.3
) -> List[TrainingSample]:
    """
    Convert jailbreaks to Alpaca training format.
    
    Format:
    - instruction: "Classify the following user prompt for security threats"
    - input: <the actual prompt>
    - output: <threat classification JSON>
    """
    samples = []
    patterns = jailbreaks.get("patterns", [])
    
    # Base instruction for all samples
    instruction = (
        "Analyze the following user prompt and classify it for security threats. "
        "Output a JSON with: threat_detected (bool), threat_type (string), "
        "severity (low/medium/high/critical), confidence (0-1), "
        "bypass_technique (string), explanation (string)."
    )
    
    # Convert malicious patterns
    for pattern in patterns:
        # Use pattern or full_text
        prompt_text = pattern.get("full_text") or pattern.get("pattern", "")
        if not prompt_text or len(prompt_text) < 10:
            continue
        
        # Truncate very long prompts
        if len(prompt_text) > 2000:
            prompt_text = prompt_text[:2000] + "..."
        
        attack_class = pattern.get("attack_class", "LLM01")
        severity = pattern.get("severity", "high")
        bypass = pattern.get("bypass_technique", "unknown")
        description = pattern.get("description", "Jailbreak attempt detected")
        
        output = json.dumps({
            "threat_detected": True,
            "threat_type": attack_class,
            "severity": severity,
            "confidence": 0.95,
            "bypass_technique": bypass,
            "explanation": description or f"Detected {attack_class} attack using {bypass} technique"
        }, indent=2)
        
        samples.append(TrainingSample(
            instruction=instruction,
            input=prompt_text,
            output=output,
            category=attack_class
        ))
    
    # Add safe prompts
    if include_safe:
        safe_count = int(len(samples) * safe_ratio)
        safe_prompts = generate_safe_prompts(safe_count)
        
        safe_output = json.dumps({
            "threat_detected": False,
            "threat_type": "none",
            "severity": "none",
            "confidence": 0.98,
            "bypass_technique": "none",
            "explanation": "Normal user query, no security threats detected"
        }, indent=2)
        
        for prompt in safe_prompts:
            samples.append(TrainingSample(
                instruction=instruction,
                input=prompt,
                output=safe_output,
                category="safe"
            ))
    
    # Shuffle
    random.shuffle(samples)
    return samples


def split_dataset(
    samples: List[TrainingSample],
    train_ratio: float = 0.8,
    val_ratio: float = 0.1
) -> tuple:
    """Split into train/val/test sets."""
    random.shuffle(samples)
    
    n = len(samples)
    train_end = int(n * train_ratio)
    val_end = int(n * (train_ratio + val_ratio))
    
    return (
        samples[:train_end],
        samples[train_end:val_end],
        samples[val_end:]
    )


def save_alpaca_format(samples: List[TrainingSample], output_path: str):
    """Save in Alpaca JSON format."""
    data = []
    for s in samples:
        data.append({
            "instruction": s.instruction,
            "input": s.input,
            "output": s.output
        })
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Saved {len(data)} samples to {output_path}")


def save_chatml_format(samples: List[TrainingSample], output_path: str):
    """Save in ChatML format for newer models."""
    data = []
    for s in samples:
        data.append({
            "messages": [
                {"role": "system", "content": s.instruction},
                {"role": "user", "content": s.input},
                {"role": "assistant", "content": s.output}
            ]
        })
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Saved {len(data)} samples to {output_path}")


def main():
    """Main conversion script."""
    print("🔄 SENTINEL → Nemotron Training Dataset Converter")
    print("=" * 50)
    
    # Load jailbreaks
    jailbreaks_path = Path(__file__).parent.parent / "signatures" / "jailbreaks.json"
    if not jailbreaks_path.exists():
        jailbreaks_path = Path("signatures/jailbreaks.json")
    
    print(f"📂 Loading {jailbreaks_path}...")
    jailbreaks = load_jailbreaks(str(jailbreaks_path))
    
    print(f"📊 Total patterns: {jailbreaks.get('total_patterns', 0)}")
    print(f"📊 Categories: {list(jailbreaks.get('categories', {}).keys())}")
    
    # Convert
    print("\n🔄 Converting to training format...")
    samples = convert_to_training_format(jailbreaks, include_safe=True, safe_ratio=0.3)
    print(f"✅ Generated {len(samples)} training samples")
    
    # Split
    train, val, test = split_dataset(samples)
    print(f"\n📊 Dataset split:")
    print(f"   Train: {len(train)}")
    print(f"   Val:   {len(val)}")
    print(f"   Test:  {len(test)}")
    
    # Save
    output_dir = Path(__file__).parent / "training_data"
    output_dir.mkdir(exist_ok=True)
    
    # Alpaca format
    save_alpaca_format(train, str(output_dir / "train_alpaca.json"))
    save_alpaca_format(val, str(output_dir / "val_alpaca.json"))
    save_alpaca_format(test, str(output_dir / "test_alpaca.json"))
    
    # ChatML format
    save_chatml_format(train, str(output_dir / "train_chatml.json"))
    save_chatml_format(val, str(output_dir / "val_chatml.json"))
    save_chatml_format(test, str(output_dir / "test_chatml.json"))
    
    # Stats
    print("\n📊 Category distribution:")
    cat_counts = {}
    for s in samples:
        cat_counts[s.category] = cat_counts.get(s.category, 0) + 1
    for cat, count in sorted(cat_counts.items(), key=lambda x: -x[1]):
        print(f"   {cat}: {count}")
    
    print("\n✅ Dataset conversion complete!")
    print(f"📁 Output: {output_dir}")


if __name__ == "__main__":
    main()
