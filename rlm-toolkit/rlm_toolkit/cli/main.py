"""
CLI Main
========

Main CLI entry point using argparse.
"""

from __future__ import annotations

import argparse
import sys
from typing import Optional, List


def create_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="rlm",
        description="RLM-Toolkit: Recursive Language Model execution framework",
        epilog="Examples:\n"
               "  rlm run --model ollama:llama4 --context file.txt --query 'Summarize'\n"
               "  rlm eval --benchmark oolong --model openai:gpt-5.2\n"
               "  rlm trace --run-id abc123",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        "--version", "-v",
        action="version",
        version="%(prog)s 0.1.0",
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Run command
    run_parser = subparsers.add_parser(
        "run",
        help="Run RLM on context with query",
    )
    run_parser.add_argument(
        "--model", "-m",
        required=True,
        help="Model to use (format: provider:model, e.g., ollama:llama4)",
    )
    run_parser.add_argument(
        "--context", "-c",
        required=True,
        help="Context file path or '-' for stdin",
    )
    run_parser.add_argument(
        "--query", "-q",
        required=True,
        help="Query to run on context",
    )
    run_parser.add_argument(
        "--max-iterations",
        type=int,
        default=50,
        help="Maximum REPL iterations (default: 50)",
    )
    run_parser.add_argument(
        "--max-cost",
        type=float,
        default=10.0,
        help="Maximum cost in USD (default: 10.0)",
    )
    run_parser.add_argument(
        "--output", "-o",
        help="Output file (default: stdout)",
    )
    run_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    
    # Eval command
    eval_parser = subparsers.add_parser(
        "eval",
        help="Evaluate model on benchmark",
    )
    eval_parser.add_argument(
        "--benchmark", "-b",
        required=True,
        choices=["oolong", "circle", "custom"],
        help="Benchmark to run",
    )
    eval_parser.add_argument(
        "--model", "-m",
        required=True,
        help="Model to evaluate",
    )
    eval_parser.add_argument(
        "--output", "-o",
        help="Results output file",
    )
    
    # Trace command
    trace_parser = subparsers.add_parser(
        "trace",
        help="View execution trace",
    )
    trace_parser.add_argument(
        "--run-id",
        required=True,
        help="Run ID to trace",
    )
    trace_parser.add_argument(
        "--format",
        choices=["text", "json", "html"],
        default="text",
        help="Output format",
    )
    
    # Interactive REPL command
    repl_parser = subparsers.add_parser(
        "repl",
        help="Start interactive REPL",
    )
    repl_parser.add_argument(
        "--model", "-m",
        default="ollama:llama4",
        help="Model to use (default: ollama:llama4)",
    )
    
    return parser


def app(args: Optional[List[str]] = None) -> int:
    """Main CLI application.
    
    Args:
        args: Command line arguments (uses sys.argv if None)
    
    Returns:
        Exit code
    """
    from rlm_toolkit.cli.commands import run_command, eval_command, trace_command, repl_command
    
    parser = create_parser()
    parsed = parser.parse_args(args)
    
    if parsed.command is None:
        parser.print_help()
        return 0
    
    try:
        if parsed.command == "run":
            return run_command(parsed)
        elif parsed.command == "eval":
            return eval_command(parsed)
        elif parsed.command == "trace":
            return trace_command(parsed)
        elif parsed.command == "repl":
            return repl_command(parsed)
        else:
            parser.print_help()
            return 1
    except KeyboardInterrupt:
        print("\nInterrupted.")
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if parsed.verbose:
            import traceback
            traceback.print_exc()
        return 1


def main():
    """CLI entry point."""
    sys.exit(app())


if __name__ == "__main__":
    main()
