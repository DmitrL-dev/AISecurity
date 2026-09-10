"""Content-free receipts for the maintained, CPU-only public regression suite."""
import hashlib
import importlib.metadata
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / ".public-regression-reports/result.json"


def summarize_core(report, expected_ids):
    invalid = {"status": "INCOMPLETE", "reason": "INVALID_CORE_REPORT"}
    if (not isinstance(report, dict) or len(expected_ids) < 48
            or len(set(expected_ids)) != len(expected_ids)
            or report.get("core_version") != "2.0.1"
            or report.get("synthetic_regression_suite") is not True
            or type(report.get("total")) is not int
            or type(report.get("passed")) is not int
            or report["total"] != len(expected_ids)
            or not isinstance(report.get("rows"), list)
            or len(report["rows"]) != len(expected_ids)):
        return invalid
    passed = errors = 0
    for row, expected_id in zip(report["rows"], expected_ids):
        if (not isinstance(row, dict) or row.get("case") != expected_id
                or type(row.get("expected")) is not bool):
            return invalid
        if set(row) == {"case", "expected", "error"} and row["error"] == "ENGINE_ERROR":
            errors += 1
        elif set(row) == {"case", "expected", "detected"} and type(row["detected"]) is bool:
            passed += row["detected"] is row["expected"]
        else:
            return invalid
    if report["passed"] != passed:
        return invalid
    status = "INCOMPLETE" if errors else (
        "PASSED" if passed == len(expected_ids) else "REGRESSION")
    return {"status": status, "total": len(expected_ids),
            "executed": len(expected_ids) - errors, "passed": passed, "errors": errors}


def summarize_suite(result):
    counts = {"tests": result.testsRun, "failures": len(result.failures),
              "errors": len(result.errors), "skipped": len(result.skipped),
              "expected_failures": len(result.expectedFailures),
              "unexpected_successes": len(result.unexpectedSuccesses)}
    if (counts["tests"] < 26 or counts["errors"] or counts["skipped"]
            or counts["expected_failures"]):
        status = "INCOMPLETE"
    elif counts["failures"] or counts["unexpected_successes"]:
        status = "REGRESSION"
    else:
        status = "PASSED"
    return {"status": status, **counts}


def run_checks():
    # Fail before scoring if the actual installation is not the documented pin.
    from guard_lab.metrics import PUBLIC_COMMIT
    from guard_lab._worker import valid_origin
    from sentinel_core import version
    dist = importlib.metadata.distribution("sentinel-core")
    origin = json.loads(dist.read_text("direct_url.json") or "null")
    if not valid_origin(origin) or dist.version != version() or version() != "2.0.1":
        return {"status": "INCOMPLETE", "reason": "ENGINE_ORIGIN_MISMATCH"}

    path = ROOT / "sentinel-core/tests/test_public_core.py"
    spec = importlib.util.spec_from_file_location("weekly_core_cases", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    expected_ids = [name for name, _, _ in module.cases()]
    core = summarize_core(module.evaluate(), expected_ids)

    os.environ["GUARD_LAB_NATIVE_TESTS"] = "1"
    suite = unittest.TestLoader().discover(str(ROOT / "tools/guard-lab/tests"))
    # Never persist tracebacks, assertion values, test input or exception text.
    result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
    lab = summarize_suite(result)
    statuses = (core["status"], lab["status"])
    status = ("INCOMPLETE" if "INCOMPLETE" in statuses else
              "REGRESSION" if "REGRESSION" in statuses else "PASSED")
    return {"status": status, "core": core, "guard_lab": lab,
            "core_version": version(), "core_commit": PUBLIC_COMMIT,
            "guard_lab_version": importlib.metadata.version("aisecurity-guard-lab"),
            "fixture_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "origin_verified": True}


def write_report(result):
    revision = "unknown"
    try:
        source = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                capture_output=True, text=True, timeout=10)
        if source.returncode == 0 and re.fullmatch(r"[0-9a-f]{40}", source.stdout.strip()):
            revision = source.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    if revision == "unknown":
        result = {"status": "INCOMPLETE", "reason": "SOURCE_REVISION_UNAVAILABLE"}
    report = {"schema_version": 1, "scope": "public-core-and-guard-lab-regressions",
              "source_revision": revision, "python_version": sys.version.split()[0],
              "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "synthetic_only": True, **result}
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    temporary = REPORT.with_suffix(".tmp")
    temporary.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(temporary, REPORT)
    print(json.dumps(report, allow_nan=False))
    return report["status"]


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv == ["--initialize"]:
        write_report({"status": "INCOMPLETE", "reason": "SETUP_NOT_COMPLETED"})
        return 0
    if argv:
        raise SystemExit("Use no arguments or --initialize")
    # Replace a prior receipt first: termination must not leave stale success.
    write_report({"status": "INCOMPLETE", "reason": "EXECUTION_NOT_COMPLETED"})
    try:
        result = run_checks()
    except Exception:
        result = {"status": "INCOMPLETE", "reason": "RUNNER_ERROR"}
    status = write_report(result)
    return {"PASSED": 0, "REGRESSION": 1, "INCOMPLETE": 2}[status]


if __name__ == "__main__":
    raise SystemExit(main())
