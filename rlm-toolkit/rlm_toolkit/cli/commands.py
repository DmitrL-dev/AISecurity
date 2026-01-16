"""
CLI Commands
=============

Implementation of CLI commands.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import argparse


def parse_model(model_spec: str) -> tuple[str, str]:
    """Parse model specification.
    
    Format: provider:model (e.g., ollama:llama4, openai:gpt-5.2)
    
    Returns:
        (provider, model) tuple
    """
    if ":" not in model_spec:
        # Default to ollama
        return ("ollama", model_spec)
    
    parts = model_spec.split(":", 1)
    return (parts[0].lower(), parts[1])


def get_provider(provider_name: str, model: str):
    """Get LLM provider instance."""
    if provider_name == "ollama":
        from rlm_toolkit.providers.ollama import OllamaProvider
        return OllamaProvider(model)
    elif provider_name == "openai":
        from rlm_toolkit.providers.openai import OpenAIProvider
        return OpenAIProvider(model)
    elif provider_name == "anthropic":
        from rlm_toolkit.providers.anthropic import AnthropicProvider
        return AnthropicProvider(model)
    elif provider_name == "google":
        from rlm_toolkit.providers.google import GeminiProvider
        return GeminiProvider(model)
    else:
        raise ValueError(f"Unknown provider: {provider_name}")


def run_command(args: "argparse.Namespace") -> int:
    """Execute run command."""
    from rlm_toolkit.core.engine import RLM, RLMConfig
    
    # Parse model
    provider_name, model = parse_model(args.model)
    
    # Read context
    if args.context == "-":
        context = sys.stdin.read()
    else:
        context_path = Path(args.context)
        if not context_path.exists():
            print(f"Error: Context file not found: {args.context}", file=sys.stderr)
            return 1
        context = context_path.read_text(encoding="utf-8")
    
    # Create provider and RLM
    root_provider = get_provider(provider_name, model)
    
    config = RLMConfig(
        max_iterations=args.max_iterations,
        max_cost=args.max_cost,
    )
    
    rlm = RLM(root=root_provider, config=config)
    
    # Run
    print(f"Running RLM with {provider_name}:{model}...", file=sys.stderr)
    print(f"Context: {len(context):,} chars", file=sys.stderr)
    print(f"Query: {args.query}", file=sys.stderr)
    print("-" * 40, file=sys.stderr)
    
    result = rlm.run(context, args.query)
    
    # Format output
    if args.format == "json":
        output = json.dumps({
            "answer": result.answer,
            "status": result.status,
            "iterations": result.iterations,
            "total_cost": result.total_cost,
            "execution_time": result.execution_time,
        }, indent=2)
    else:
        output = result.answer or "(no answer)"
    
    # Write output
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"Output written to: {args.output}", file=sys.stderr)
    else:
        print(output)
    
    # Summary
    print("-" * 40, file=sys.stderr)
    print(f"Status: {result.status}", file=sys.stderr)
    print(f"Iterations: {result.iterations}", file=sys.stderr)
    print(f"Cost: ${result.total_cost:.4f}", file=sys.stderr)
    print(f"Time: {result.execution_time:.2f}s", file=sys.stderr)
    
    return 0 if result.status == "success" else 1


def eval_command(args: "argparse.Namespace") -> int:
    """Execute eval command."""
    print(f"Evaluating {args.model} on {args.benchmark} benchmark...")
    print("(Benchmark evaluation not yet implemented)")
    
    # TODO: Implement benchmark evaluation
    # - Load benchmark dataset
    # - Run RLM on each example
    # - Calculate metrics
    # - Report results
    
    return 0


def trace_command(args: "argparse.Namespace") -> int:
    """Execute trace command."""
    print(f"Fetching trace for run: {args.run_id}")
    print("(Trace viewing not yet implemented)")
    
    # TODO: Implement trace viewing
    # - Load trace from storage
    # - Format based on args.format
    # - Display
    
    return 0


def repl_command(args: "argparse.Namespace") -> int:
    """Start interactive REPL."""
    from rlm_toolkit.core.repl import SecureREPL
    
    print("RLM-Toolkit Interactive REPL")
    print(f"Model: {args.model}")
    print("Type 'exit' or Ctrl+C to quit")
    print("-" * 40)
    
    repl = SecureREPL()
    namespace = {}
    
    while True:
        try:
            code = input(">>> ")
            
            if code.strip().lower() in ("exit", "quit"):
                print("Goodbye!")
                break
            
            if not code.strip():
                continue
            
            # Handle multi-line input
            if code.rstrip().endswith(":"):
                lines = [code]
                while True:
                    line = input("... ")
                    if not line.strip():
                        break
                    lines.append(line)
                code = "\n".join(lines)
            
            # Execute
            try:
                output = repl.execute(code, namespace)
                if output:
                    print(output.rstrip())
            except Exception as e:
                print(f"Error: {e}")
        
        except EOFError:
            print("\nGoodbye!")
            break
    
    return 0
