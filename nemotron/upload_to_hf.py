"""
Upload SENTINEL Jailbreak Dataset to HuggingFace Hub

Usage:
    pip install huggingface_hub datasets
    huggingface-cli login
    python upload_to_hf.py
"""

from datasets import Dataset, DatasetDict
import json
from pathlib import Path


def load_json_data(file_path: Path) -> list:
    """Load JSON data from file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def convert_to_hf_format(data: list) -> dict:
    """Convert ChatML format to HuggingFace format."""
    records = []
    for item in data:
        messages = item.get("messages", [])
        if len(messages) >= 3:
            records.append({
                "system": messages[0]["content"],
                "user": messages[1]["content"],
                "assistant": messages[2]["content"],
                "messages": messages  # Keep original for ChatML users
            })
    return records


def main():
    # Paths
    data_dir = Path(__file__).parent / "training_data"
    
    # Load data
    print("Loading training data...")
    train_data = load_json_data(data_dir / "train_chatml.json")
    val_data = load_json_data(data_dir / "val_chatml.json")
    test_data = load_json_data(data_dir / "test_chatml.json")
    
    print(f"  Train: {len(train_data)} samples")
    print(f"  Val: {len(val_data)} samples")
    print(f"  Test: {len(test_data)} samples")
    
    # Convert to HF format
    print("\nConverting to HuggingFace format...")
    train_records = convert_to_hf_format(train_data)
    val_records = convert_to_hf_format(val_data)
    test_records = convert_to_hf_format(test_data)
    
    # Create datasets
    dataset_dict = DatasetDict({
        "train": Dataset.from_list(train_records),
        "validation": Dataset.from_list(val_records),
        "test": Dataset.from_list(test_records),
    })
    
    print(f"\nDataset created:")
    print(dataset_dict)
    
    # Upload to HuggingFace
    print("\nUploading to HuggingFace Hub...")
    dataset_dict.push_to_hub(
        "DmitrL-dev/sentinel-jailbreak-detection",
        private=False,
    )
    
    print("\n✅ Dataset uploaded successfully!")
    print("🔗 https://huggingface.co/datasets/DmitrL-dev/sentinel-jailbreak-detection")


if __name__ == "__main__":
    main()
