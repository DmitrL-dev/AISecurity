#!/usr/bin/env python3
"""
GoMCP Python Bridge — JSON-RPC interface for ML operations.
Supports: compute_embedding, semantic_search, classify_prompt

Resource-optimized:
- ONNX INT8 quantized inference (4x faster, 4x less memory)
- LRU cache for repeated prompts
- Thread-limited ONNX sessions (max 4 threads)
- Lazy model loading (no memory until first request)
- Memory-mapped model loading
"""

import sys
import json
import os
import time
import hashlib
from pathlib import Path
from collections import OrderedDict

# Model paths
MODEL_DIR = Path(__file__).parent.parent.parent.parent.parent / "models"
SAFETY_MODEL_DIR = MODEL_DIR / "safety-classifier-v2"
EMBEDDING_MODEL_DIR = MODEL_DIR / "safety-classifier-onnx"

# Resource limits — keep host under 50%
MAX_CPU_THREADS = 4
CACHE_SIZE = 5000
CACHE_TTL = 3600

# Lazy-loaded models
_embedder = None
_classifier = None
_classifier_session = None  # ONNX session with resource limits

# LRU Cache
_cache = OrderedDict()
_cache_timestamps = {}
_cache_lock = None  # Will be initialized on first use


def _get_cache_lock():
    """Lazy initialize cache lock."""
    global _cache_lock
    if _cache_lock is None:
        import threading

        _cache_lock = threading.Lock()
    return _cache_lock


def _cache_get(key: str):
    """Get from cache with TTL check."""
    lock = _get_cache_lock()
    with lock:
        if key in _cache:
            if time.time() - _cache_timestamps[key] > CACHE_TTL:
                del _cache[key]
                del _cache_timestamps[key]
                return None
            _cache.move_to_end(key)
            return _cache[key]
        return None


def _cache_put(key: str, value: dict):
    """Put in cache with eviction."""
    lock = _get_cache_lock()
    with lock:
        if key in _cache:
            _cache.move_to_end(key)
        _cache[key] = value
        _cache_timestamps[key] = time.time()
        while len(_cache) > CACHE_SIZE:
            oldest_key, _ = _cache.popitem(last=False)
            del _cache_timestamps[oldest_key]


def load_embedder():
    """Lazy-load the embedding model."""
    global _embedder
    if _embedder is not None:
        return _embedder

    try:
        from sentence_transformers import SentenceTransformer

        model_path = EMBEDDING_MODEL_DIR / "model.onnx"
        if model_path.exists():
            _embedder = SentenceTransformer(str(EMBEDDING_MODEL_DIR))
        else:
            # Fallback to default model
            _embedder = SentenceTransformer("all-MiniLM-L6-v2")
    except ImportError:
        raise RuntimeError("sentence-transformers not installed")

    return _embedder


def load_classifier():
    """Lazy-load the safety classifier v2 with resource limits."""
    global _classifier, _classifier_session
    if _classifier is not None:
        return _classifier

    try:
        import onnxruntime as ort
        import numpy as np
        from transformers import AutoTokenizer

        # Find model (prefer INT8 for lower resource usage)
        model_path = SAFETY_MODEL_DIR / "model_int8.onnx"
        if not model_path.exists():
            model_path = SAFETY_MODEL_DIR / "model_fp16.onnx"
        if not model_path.exists():
            model_path = SAFETY_MODEL_DIR / "model_fp32.onnx"
        if not model_path.exists():
            model_path = EMBEDDING_MODEL_DIR / "model.onnx"

        if not model_path.exists():
            raise FileNotFoundError(
                f"Safety classifier model not found in {SAFETY_MODEL_DIR}"
            )

        # Load tokenizer
        tokenizer = AutoTokenizer.from_pretrained(SAFETY_MODEL_DIR)

        # Configure ONNX Runtime for low resource usage
        session_options = ort.SessionOptions()
        session_options.intra_op_num_threads = MAX_CPU_THREADS
        session_options.inter_op_num_threads = 2
        session_options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        session_options.graph_optimization_level = (
            ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        )

        # Memory-mapped loading
        session_options.add_session_config_entry(
            "session.use_ort_model_bytes_direct_io", "1"
        )

        # Load ONNX model with resource limits
        session = ort.InferenceSession(
            str(model_path),
            sess_options=session_options,
            providers=[
                (
                    "CPUExecutionProvider",
                    {
                        "intra_op_num_threads": MAX_CPU_THREADS,
                        "inter_op_num_threads": 2,
                        "arena_extend_strategy": "kSameAsRequested",
                    },
                )
            ],
        )

        # Load labels
        labels_path = SAFETY_MODEL_DIR / "labels.json"
        if labels_path.exists():
            with open(labels_path) as f:
                labels_map = json.load(f)
            labels = [labels_map[str(i)] for i in range(len(labels_map))]
        else:
            labels = [
                "safe",
                "jailbreak",
                "prompt_injection",
                "tool_abuse",
                "exfiltration",
                "pii_leak",
                "auth_bypass",
                "encoding",
                "persistence",
                "sensor_anomaly",
                "dos",
                "model_theft",
                "supply_chain",
                "data_poisoning",
                "evasion",
                "social_engineering",
            ]

        _classifier = {
            "session": session,
            "tokenizer": tokenizer,
            "labels": labels,
            "input_names": [inp.name for inp in session.get_inputs()],
        }
        _classifier_session = session

    except ImportError as e:
        raise RuntimeError(f"Required packages not installed: {e}")

    return _classifier


def compute_embedding(params):
    """Compute embedding vector for text."""
    text = params.get("text", "")
    embedder = load_embedder()
    embedding = embedder.encode(text, convert_to_numpy=True).tolist()
    return {
        "embedding": embedding,
        "model": embedder.get_sentence_embedding_dimension(),
    }


def semantic_search(params):
    """Perform semantic search."""
    query = params.get("query", "")
    limit = params.get("limit", 10)
    embedder = load_embedder()
    # This would need access to the fact store — simplified for now
    query_emb = embedder.encode(query, convert_to_numpy=True).tolist()
    return {
        "query_embedding": query_emb,
        "results": [],
        "message": "semantic_search requires fact store integration",
    }


def classify_prompt(params):
    """Classify text using Safety Classifier v2 (16-class threat detection).

    Optimized with:
    - LRU cache for repeated prompts
    - ONNX INT8 quantized inference
    - Thread-limited ONNX session
    """
    text = params.get("text", "")

    # Check cache first
    cache_key = hashlib.sha256(text.encode()).hexdigest()[:16]
    cached = _cache_get(cache_key)
    if cached is not None:
        cached["cached"] = True
        return cached

    classifier = load_classifier()

    session = classifier["session"]
    tokenizer = classifier["tokenizer"]
    labels = classifier["labels"]
    input_names = classifier["input_names"]

    # Tokenize
    encoded = tokenizer(
        text,
        truncation=True,
        max_length=512,
        return_tensors="np",
        padding="max_length",
    )

    # Prepare inputs
    input_feed = {}
    if "input_ids" in input_names:
        input_feed["input_ids"] = encoded["input_ids"].astype("int64")
    if "attention_mask" in input_names:
        input_feed["attention_mask"] = encoded["attention_mask"].astype("int64")
    if "token_type_ids" in input_names:
        input_feed["token_type_ids"] = encoded.get(
            "token_type_ids", np.zeros_like(encoded["input_ids"])
        ).astype("int64")

    # Run inference
    outputs = session.run(None, input_feed)
    logits = outputs[0][0]  # [num_labels]

    # Softmax
    exp_logits = np.exp(logits - np.max(logits))
    probabilities = exp_logits / exp_logits.sum()

    # Get top prediction
    max_idx = int(np.argmax(probabilities))
    category = labels[max_idx] if max_idx < len(labels) else "safe"
    confidence = float(probabilities[max_idx])

    # Build probability map
    prob_map = {}
    for i, label in enumerate(labels):
        if i < len(probabilities):
            prob_map[label] = round(float(probabilities[i]), 4)

    # Determine severity
    severity_map = {
        "safe": "INFO",
        "jailbreak": "HIGH",
        "prompt_injection": "CRITICAL",
        "tool_abuse": "HIGH",
        "exfiltration": "CRITICAL",
        "pii_leak": "HIGH",
        "auth_bypass": "CRITICAL",
        "encoding": "MEDIUM",
        "persistence": "HIGH",
        "sensor_anomaly": "MEDIUM",
        "dos": "HIGH",
        "model_theft": "HIGH",
        "supply_chain": "CRITICAL",
        "data_poisoning": "CRITICAL",
        "evasion": "HIGH",
        "social_engineering": "MEDIUM",
    }

    result = {
        "category": category,
        "confidence": round(confidence, 4),
        "probabilities": prob_map,
        "is_threat": category != "safe",
        "severity": severity_map.get(category, "INFO"),
        "cached": False,
    }

    # Store in cache
    _cache_put(cache_key, result)

    return result


def main():
    """Main entry point — reads JSON-RPC from stdin, writes to stdout."""
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"invalid JSON: {e}"}))
        return

    method = data.get("method", "")
    params = data.get("params", {})

    handlers = {
        "compute_embedding": compute_embedding,
        "semantic_search": semantic_search,
        "classify_prompt": classify_prompt,
    }

    if method not in handlers:
        print(json.dumps({"error": f"unknown method: {method}"}))
        return

    try:
        result = handlers[method](params)
        print(json.dumps({"result": result}))
    except Exception as e:
        print(json.dumps({"error": str(e)}))


if __name__ == "__main__":
    main()
