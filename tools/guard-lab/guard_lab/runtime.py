"""One bounded process per run; native logs and exception strings are discarded."""
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from .metrics import ERRORS
from .corpus import _unique_keys

MAX_OUTPUT = 256 * 1024


def decode_predictions(raw: bytes, count: int):
    invalid = ["INVALID_RESULT"] * count
    try:
        values = json.loads(raw, object_pairs_hook=_unique_keys)
    except (ValueError, UnicodeError, RecursionError):
        return invalid
    if not isinstance(values, list) or len(values) != count:
        return invalid
    results = []
    for value in values:
        if isinstance(value, dict) and set(value) == {"error"}:
            error = value["error"]
            results.append(error if isinstance(error, str) and error in ERRORS else "INVALID_RESULT")
        elif (isinstance(value, dict) and set(value) == {"detected", "risk_score"}
              and type(value["detected"]) is bool and type(value["risk_score"]) in (float, int)
              and 0 <= value["risk_score"] <= 1 and math.isfinite(value["risk_score"])):
            results.append(value["detected"])
        else:
            results.append("INVALID_RESULT")
    return results


def run_process(command, texts, directory: Path, timeout: float):
    env = {"PATH": os.defpath, "SENTINEL_SIGNATURES_DIR": str(directory),
           "GUARD_LAB_CPU_SECONDS": str(math.ceil(timeout) + 1)}
    with tempfile.TemporaryFile() as output:
        try:
            with subprocess.Popen(command, stdin=subprocess.PIPE, stdout=output,
                                  stderr=subprocess.DEVNULL, cwd=directory, env=env) as process:
                try:
                    process.communicate(json.dumps(texts, ensure_ascii=False).encode("utf-8"), timeout=timeout)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.communicate()
                    return ["TIMEOUT"] * len(texts)
                if process.returncode:
                    return ["ENGINE_ERROR"] * len(texts)
        except OSError:
            return ["ENGINE_ERROR"] * len(texts)
        output.seek(0)
        raw = output.read(MAX_OUTPUT + 1)
        if len(raw) > MAX_OUTPUT:
            return ["INVALID_RESULT"] * len(texts)
        return decode_predictions(raw, len(texts))


def predict(records, timeout: float):
    texts = [record.text for record in records if record.split == "test"]
    with tempfile.TemporaryDirectory(prefix="guard-lab-") as directory:
        # -I ignores PYTHONPATH, user site and the caller's working directory.
        return run_process([sys.executable, "-I", "-m", "guard_lab._worker"],
                           texts, Path(directory), timeout)
