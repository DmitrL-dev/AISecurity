"""Local evaluation, not a request enforcement boundary."""
import argparse
import json
import math
from pathlib import Path
import sys

from .corpus import CorpusError, load_corpus
from .metrics import make_report
from .runtime import predict


class Parser(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "guard-lab: INVALID_ARGUMENTS\n")


def main(argv=None):
    parser = Parser(description="Evaluate labelled inputs locally; stdout never contains input text.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--demo", action="store_true", help="Run the synthetic demonstration (not a benchmark)")
    source.add_argument("--input", help="JSONL basename inside --data-dir")
    parser.add_argument("--data-dir", type=Path, default=Path("."))
    parser.add_argument("--timeout", type=float, default=30, help="Whole native run wall-time limit, 0 < seconds <= 120")
    args = parser.parse_args(argv)
    if not math.isfinite(args.timeout) or not 0 < args.timeout <= 120:
        parser.error("timeout")
    if sys.platform != "linux":
        parser.exit(2, "guard-lab: UNSUPPORTED_PLATFORM\n")
    directory = Path(__file__).parent if args.demo else args.data_dir
    name = "demo.jsonl" if args.demo else args.input
    try:
        records = load_corpus(directory, name)
    except CorpusError as error:
        parser.exit(2, f"guard-lab: {error}\n")
    report = make_report(records, predict(records, args.timeout))
    report["synthetic_demo"] = args.demo
    json.dump(report, sys.stdout, allow_nan=False, sort_keys=True, indent=2)
    sys.stdout.write("\n")
    return 1 if report["counts"]["errors"] else 0
