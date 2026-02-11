#!/usr/bin/env python3
"""
ONNX Model Export via Optimum (More Stable)

Uses HuggingFace Optimum for reliable ONNX export.

Usage:
    python export_onnx_optimum.py
"""

import os
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_models_dir() -> Path:
    """Get or create models directory."""
    models_dir = Path.home() / ".sentinel" / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    return models_dir


def export_with_optimum(model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
    """Export using HuggingFace Optimum (official ONNX exporter)."""
    from optimum.onnxruntime import ORTModelForFeatureExtraction
    from transformers import AutoTokenizer

    output_dir = get_models_dir()

    logger.info(f"Exporting {model_name} to ONNX...")

    # Load and export in one step
    model = ORTModelForFeatureExtraction.from_pretrained(
        model_name,
        export=True,
    )

    # Save ONNX model
    model.save_pretrained(output_dir)

    # Save tokenizer
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    tokenizer.save_pretrained(output_dir)

    # Find the ONNX file
    onnx_files = list(output_dir.glob("*.onnx"))
    if onnx_files:
        onnx_path = onnx_files[0]
        logger.info(f"ONNX model saved: {onnx_path}")
        logger.info(f"Size: {onnx_path.stat().st_size / 1024 / 1024:.1f} MB")

        # Verify inference
        verify_model(output_dir)
        return onnx_path
    else:
        logger.error("No ONNX file found")
        return None


def verify_model(model_dir: Path):
    """Verify the exported model works."""
    import numpy as np
    import onnxruntime as ort
    from transformers import AutoTokenizer

    # Find ONNX file
    onnx_files = list(model_dir.glob("*.onnx"))
    if not onnx_files:
        logger.error("No ONNX file to verify")
        return False

    onnx_path = onnx_files[0]

    logger.info(f"Verifying: {onnx_path}")

    # Create session
    session = ort.InferenceSession(str(onnx_path))

    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(str(model_dir))

    # Test sentence
    test_sentence = "This is a security test for ONNX inference."

    # Tokenize
    inputs = tokenizer(
        test_sentence,
        return_tensors="np",
        padding=True,
        truncation=True,
        max_length=256,
    )

    # Run inference
    outputs = session.run(
        None,
        {
            "input_ids": inputs["input_ids"],
            "attention_mask": inputs["attention_mask"],
        },
    )

    # Check output shape
    last_hidden = outputs[0]
    logger.info(f"Output shape: {last_hidden.shape}")
    logger.info(f"Embedding dim: {last_hidden.shape[-1]}")

    # Mean pooling to get sentence embedding
    embedding = np.mean(last_hidden, axis=1)
    logger.info(f"Sentence embedding shape: {embedding.shape}")
    logger.info(f"Embedding norm: {np.linalg.norm(embedding):.4f}")

    logger.info("✓ ONNX verification passed!")
    return True


def main():
    """Export all models needed for SENTINEL Rust Core."""
    try:
        from optimum.onnxruntime import ORTModelForFeatureExtraction
    except ImportError:
        print("Installing optimum[onnxruntime]...")
        import subprocess

        subprocess.run(["pip", "install", "optimum[onnxruntime]", "-q"])
        from optimum.onnxruntime import ORTModelForFeatureExtraction

    output_dir = get_models_dir()
    logger.info(f"Output directory: {output_dir}")

    # Export model
    onnx_path = export_with_optimum()

    if onnx_path:
        print("\n" + "=" * 60)
        print("ONNX Export Complete")
        print("=" * 60)
        print(f"Model:   all-MiniLM-L6-v2")
        print(f"Path:    {output_dir}")
        print(f"ONNX:    {onnx_path.name}")
        print(f"Size:    {onnx_path.stat().st_size / 1024 / 1024:.1f} MB")
        print("=" * 60)


if __name__ == "__main__":
    main()
