#!/usr/bin/env python3
"""
ONNX Model Export for SENTINEL Rust Core

Exports SentenceTransformer models to ONNX format for use with
ort crate in Rust.

Usage:
    python export_onnx_models.py

Output:
    ~/.sentinel/models/
        all-MiniLM-L6-v2.onnx
        tokenizer.json
"""

import os
import json
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_models_dir() -> Path:
    """Get or create models directory."""
    models_dir = Path.home() / ".sentinel" / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    return models_dir


def export_sentence_transformer(
    model_name: str = "all-MiniLM-L6-v2",
    output_dir: Path = None,
) -> Path:
    """
    Export SentenceTransformer to ONNX format.

    Args:
        model_name: HuggingFace model name
        output_dir: Output directory (default: ~/.sentinel/models/)

    Returns:
        Path to exported ONNX model
    """
    from sentence_transformers import SentenceTransformer
    import torch

    output_dir = output_dir or get_models_dir()
    onnx_path = output_dir / f"{model_name.replace('/', '_')}.onnx"

    if onnx_path.exists():
        logger.info(f"ONNX model already exists: {onnx_path}")
        return onnx_path

    logger.info(f"Loading SentenceTransformer: {model_name}")
    model = SentenceTransformer(model_name)

    # Get the transformer model and tokenizer
    transformer = model[0].auto_model
    tokenizer = model.tokenizer

    # Save tokenizer config for Rust (uses tokenizers crate)
    tokenizer_path = output_dir / "tokenizer.json"
    if hasattr(tokenizer, "save_pretrained"):
        tokenizer.save_pretrained(str(output_dir))
        logger.info(f"Tokenizer saved to: {output_dir}")

    # Create dummy inputs for export
    dummy_text = "This is a sample text for ONNX export"
    tokens = tokenizer(
        dummy_text,
        padding=True,
        truncation=True,
        max_length=256,
        return_tensors="pt",
    )

    logger.info(f"Exporting to ONNX: {onnx_path}")

    # Export to ONNX
    torch.onnx.export(
        transformer,
        (tokens["input_ids"], tokens["attention_mask"]),
        str(onnx_path),
        input_names=["input_ids", "attention_mask"],
        output_names=["last_hidden_state"],
        dynamic_axes={
            "input_ids": {0: "batch", 1: "sequence"},
            "attention_mask": {0: "batch", 1: "sequence"},
            "last_hidden_state": {0: "batch", 1: "sequence"},
        },
        opset_version=14,
        do_constant_folding=True,
    )

    logger.info(f"ONNX model exported: {onnx_path}")
    logger.info(f"Model size: {onnx_path.stat().st_size / 1024 / 1024:.1f} MB")

    # Verify the model
    verify_onnx_model(onnx_path)

    return onnx_path


def verify_onnx_model(onnx_path: Path) -> bool:
    """Verify ONNX model loads correctly."""
    import onnx
    import onnxruntime as ort

    logger.info("Verifying ONNX model...")

    # Load and check model
    model = onnx.load(str(onnx_path))
    onnx.checker.check_model(model)
    logger.info("ONNX model validated ✓")

    # Test inference
    session = ort.InferenceSession(str(onnx_path))

    # Get input shapes
    inputs = {inp.name: inp.shape for inp in session.get_inputs()}
    outputs = {out.name: out.shape for out in session.get_outputs()}

    logger.info(f"Inputs: {inputs}")
    logger.info(f"Outputs: {outputs}")

    # Test run
    import numpy as np

    dummy_input_ids = np.array([[101, 2023, 2003, 1037, 3231, 102]], dtype=np.int64)
    dummy_attention = np.ones_like(dummy_input_ids)

    result = session.run(
        None, {"input_ids": dummy_input_ids, "attention_mask": dummy_attention}
    )

    logger.info(f"Output shape: {result[0].shape}")
    logger.info("ONNX inference test passed ✓")

    return True


def export_model_card(model_name: str, onnx_path: Path) -> None:
    """Save model metadata for Rust loader."""
    output_dir = onnx_path.parent
    card_path = output_dir / "model_card.json"

    card = {
        "model_name": model_name,
        "onnx_file": onnx_path.name,
        "embedding_dim": 384,  # all-MiniLM-L6-v2 dimension
        "max_sequence_length": 256,
        "exported_at": __import__("datetime").datetime.now().isoformat(),
        "onnx_opset": 14,
    }

    with open(card_path, "w") as f:
        json.dump(card, f, indent=2)

    logger.info(f"Model card saved: {card_path}")


def main():
    """Export all models needed for SENTINEL Rust Core."""
    models_dir = get_models_dir()
    logger.info(f"Models directory: {models_dir}")

    # Primary embedding model
    model_name = "all-MiniLM-L6-v2"
    onnx_path = export_sentence_transformer(model_name)
    export_model_card(model_name, onnx_path)

    print("\n" + "=" * 60)
    print("ONNX Export Complete")
    print("=" * 60)
    print(f"Model: {model_name}")
    print(f"ONNX:  {onnx_path}")
    print(f"Size:  {onnx_path.stat().st_size / 1024 / 1024:.1f} MB")
    print("=" * 60)
    print("\nRust integration:")
    print("  1. Add 'ml' feature to sentinel-core")
    print("  2. Load model via: Session::with_model(onnx_bytes)")
    print("  3. Use tokenizers crate for tokenization")


if __name__ == "__main__":
    main()
