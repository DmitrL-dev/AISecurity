"""CLI for Micro-Model Swarm.

Commands:
    micro-swarm init --preset security
    micro-swarm train --data train.jsonl [--epochs 10]
    micro-swarm predict --input '{"entropy": 0.9, ...}'
    micro-swarm info
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path


def _cmd_init(args: argparse.Namespace) -> None:
    """Initialize a Swarm from a preset."""
    from micro_swarm.presets import load_preset, list_presets

    if args.preset not in list_presets():
        print(f"Error: unknown preset '{args.preset}'. "
              f"Available: {list_presets()}", file=sys.stderr)
        sys.exit(1)

    swarm = load_preset(args.preset)
    config = {
        "preset": args.preset,
        "domains": swarm.domain_names,
        "model_count": swarm.model_count,
    }

    config_path = Path("swarm_config.json")
    config_path.write_text(json.dumps(config, indent=2))
    print(f"✓ Initialized '{args.preset}' preset → {config_path}")
    print(f"  Domains: {swarm.domain_names}")
    print(f"  Models: {swarm.model_count}")


def _cmd_train(args: argparse.Namespace) -> None:
    """Train Swarm on data file."""
    from micro_swarm.presets import load_preset

    config_path = Path("swarm_config.json")
    if not config_path.exists():
        print("Error: no swarm_config.json found. Run 'micro-swarm init' first.",
              file=sys.stderr)
        sys.exit(1)

    config = json.loads(config_path.read_text())
    swarm = load_preset(config["preset"])

    data_path = Path(args.data)
    if not data_path.exists():
        print(f"Error: data file not found: {data_path}", file=sys.stderr)
        sys.exit(1)

    lines = data_path.read_text().strip().split("\n")
    epochs = args.epochs or 1

    print(f"Training on {len(lines)} samples × {epochs} epoch(s)...")
    start = time.time()

    for epoch in range(epochs):
        total_loss = 0.0
        for line in lines:
            sample = json.loads(line)
            target = sample.pop("_target", 0.5)
            losses = swarm.train_step(sample, target)
            total_loss += sum(losses.values()) / len(losses)

        avg_loss = total_loss / len(lines)
        print(f"  Epoch {epoch + 1}/{epochs}: avg_loss={avg_loss:.4f}")

    elapsed = time.time() - start
    print(f"✓ Training complete in {elapsed:.1f}s")


def _cmd_predict(args: argparse.Namespace) -> None:
    """Run prediction on input."""
    from micro_swarm.presets import load_preset

    config_path = Path("swarm_config.json")
    if not config_path.exists():
        print("Error: no swarm_config.json found. Run 'micro-swarm init' first.",
              file=sys.stderr)
        sys.exit(1)

    config = json.loads(config_path.read_text())
    swarm = load_preset(config["preset"])

    try:
        input_data = json.loads(args.input)
    except json.JSONDecodeError as e:
        print(f"Error: invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)

    result = swarm.predict(input_data)
    output = {
        "final_score": result.final_score,
        "domain_scores": {
            name: {"score": ds.score, "latency_ms": round(ds.latency_ms, 3)}
            for name, ds in result.domain_scores.items()
        },
        "meta_used": result.meta_used,
        "latency_ms": round(result.latency_ms, 3),
        "active_models": result.active_models,
    }
    print(json.dumps(output, indent=2))


def _cmd_info(args: argparse.Namespace) -> None:
    """Show Swarm info."""
    from micro_swarm.presets import load_preset, list_presets

    config_path = Path("swarm_config.json")
    if config_path.exists():
        config = json.loads(config_path.read_text())
        swarm = load_preset(config["preset"])
        total_params = sum(
            swarm._models[name].param_count for name in swarm.domain_names
        )
        total_mem = sum(
            swarm._models[name].memory_bytes for name in swarm.domain_names
        )
        print(f"Preset: {config['preset']}")
        print(f"Domains: {swarm.domain_names}")
        print(f"Models: {swarm.model_count}")
        print(f"Total params: {total_params:,}")
        print(f"Memory: {total_mem:,} bytes ({total_mem / 1024:.1f} KB)")
    else:
        print("No swarm_config.json found.")

    print(f"\nAvailable presets: {list_presets()}")


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="micro-swarm",
        description="Micro-Model Swarm: lightweight ML ensemble. "
                    "Pure Python, 0 deps, <1ms inference.",
    )
    subparsers = parser.add_subparsers(dest="command")

    # init
    init_p = subparsers.add_parser("init", help="Initialize Swarm from preset")
    init_p.add_argument("--preset", required=True,
                        help="Preset name (adtech, security, fraud, strike)")

    # train
    train_p = subparsers.add_parser("train", help="Train Swarm on data")
    train_p.add_argument("--data", required=True, help="Path to JSONL file")
    train_p.add_argument("--epochs", type=int, default=1,
                         help="Number of epochs")

    # predict
    pred_p = subparsers.add_parser("predict", help="Run prediction")
    pred_p.add_argument("--input", required=True, help="JSON input string")

    # info
    subparsers.add_parser("info", help="Show Swarm info")

    args = parser.parse_args()

    if args.command == "init":
        _cmd_init(args)
    elif args.command == "train":
        _cmd_train(args)
    elif args.command == "predict":
        _cmd_predict(args)
    elif args.command == "info":
        _cmd_info(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
