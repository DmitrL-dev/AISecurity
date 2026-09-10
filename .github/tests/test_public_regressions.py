"""Offline failure controls for the weekly public regression gate."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "public_regressions", ROOT / ".github/scripts/public_regressions.py")
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)


def core_report():
    rows = [{"case": f"case-{i}", "expected": i % 2 == 0,
             "detected": i % 2 == 0} for i in range(48)]
    return {"core_version": "2.0.1", "synthetic_regression_suite": True,
            "passed": 48, "total": 48, "rows": rows}


class ProcessOutcomeTests(unittest.TestCase):
    def test_actual_unittest_assertion_failure_is_regression(self):
        def failure():
            raise AssertionError("synthetic failure control")
        suite = unittest.TestSuite(
            [unittest.FunctionTestCase(lambda: None) for _ in range(25)]
            + [unittest.FunctionTestCase(failure)])
        result = suite.run(unittest.TestResult())
        self.assertEqual(result.testsRun, 26)
        self.assertEqual(gate.summarize_suite(result)["status"], "REGRESSION")

    def test_main_exit_codes_match_receipts(self):
        for status, code in (("PASSED", 0), ("REGRESSION", 1), ("INCOMPLETE", 2)):
            with tempfile.TemporaryDirectory() as directory:
                with patch.object(gate, "REPORT", Path(directory) / "report.json"):
                    with patch.object(gate, "run_checks", return_value={"status": status}):
                        self.assertEqual(gate.main([]), code)
                    self.assertEqual(json.loads(gate.REPORT.read_text())["status"], status)

    def test_missing_git_does_not_leave_stale_success(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(gate, "REPORT", Path(directory) / "report.json"):
                gate.REPORT.write_text('{"status":"PASSED"}')
                with patch.object(gate.subprocess, "run", side_effect=FileNotFoundError):
                    with patch.object(gate, "run_checks", return_value={"status": "PASSED"}):
                        self.assertEqual(gate.main([]), 2)
                self.assertEqual(json.loads(gate.REPORT.read_text())["status"], "INCOMPLETE")


class CoreReportTests(unittest.TestCase):
    def check(self, report):
        return gate.summarize_core(report, [f"case-{i}" for i in range(48)])

    def test_complete_report_passes(self):
        self.assertEqual(self.check(core_report())["status"], "PASSED")

    def test_missing_or_empty_results_are_incomplete(self):
        for value in ({}, None, [], {"rows": []}):
            with self.subTest(value=value):
                self.assertEqual(self.check(value)["status"], "INCOMPLETE")

    def test_deny_all_and_allow_all_are_regressions(self):
        for decision in (True, False):
            report = core_report()
            for row in report["rows"]:
                row["detected"] = decision
            report["passed"] = 24
            self.assertEqual(self.check(report)["status"], "REGRESSION")

    def test_execution_error_is_not_a_detector_regression(self):
        report = core_report()
        report["rows"][0] = {"case": "case-0", "expected": True,
                             "error": "ENGINE_ERROR"}
        report["passed"] = 47
        self.assertEqual(self.check(report)["status"], "INCOMPLETE")

    def test_corrupt_counts_rows_and_version_are_incomplete(self):
        mutations = [
            lambda r: r.update(passed=49),
            lambda r: r.update(total=0),
            lambda r: r.update(core_version="2.0.0"),
            lambda r: r.update(synthetic_regression_suite=False),
            lambda r: r["rows"].pop(),
            lambda r: r["rows"][1].update(case="case-0"),
            lambda r: r["rows"][0].update(detected=1),
            lambda r: r["rows"][0].update(expected=1),
            lambda r: r.update(passed=True),
        ]
        for mutate in mutations:
            report = core_report()
            mutate(report)
            self.assertEqual(self.check(report)["status"], "INCOMPLETE")


class SuiteTests(unittest.TestCase):
    def result(self):
        result = unittest.TestResult()
        result.testsRun = 26
        return result

    def test_complete_suite_passes(self):
        self.assertEqual(gate.summarize_suite(self.result())["status"], "PASSED")

    def test_failed_assertion_is_regression(self):
        result = self.result()
        result.failures.append((None, "private diagnostic must not be emitted"))
        summary = gate.summarize_suite(result)
        self.assertEqual(summary["status"], "REGRESSION")
        self.assertNotIn("private diagnostic", json.dumps(summary))

    def test_incomplete_suite_cannot_pass(self):
        for field in ("errors", "skipped", "expectedFailures"):
            result = self.result()
            getattr(result, field).append((None, "detail"))
            self.assertEqual(gate.summarize_suite(result)["status"], "INCOMPLETE")
        for count in (0, 25):
            result = self.result()
            result.testsRun = count
            self.assertEqual(gate.summarize_suite(result)["status"], "INCOMPLETE")

    def test_unexpected_success_is_not_silently_accepted(self):
        result = self.result()
        result.unexpectedSuccesses.append(None)
        self.assertEqual(gate.summarize_suite(result)["status"], "REGRESSION")


class ReceiptTests(unittest.TestCase):
    def test_initial_receipt_cannot_claim_a_run(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(gate, "REPORT", Path(directory) / "report.json"):
                self.assertEqual(gate.main(["--initialize"]), 0)
                report = json.loads(gate.REPORT.read_text())
                self.assertEqual(report["status"], "INCOMPLETE")
                self.assertEqual(report["reason"], "SETUP_NOT_COMPLETED")

    def test_exception_overwrites_previous_success_with_incomplete(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(gate, "REPORT", Path(directory) / "report.json"):
                gate.REPORT.write_text('{"status":"PASSED"}')
                with patch.object(gate, "run_checks", side_effect=ImportError("do not leak")):
                    self.assertEqual(gate.main([]), 2)
                report = json.loads(gate.REPORT.read_text())
                self.assertEqual(report["status"], "INCOMPLETE")
                self.assertNotIn("do not leak", json.dumps(report))

    def test_workflow_is_read_only_and_no_longer_claims_agenticred(self):
        workflow = (ROOT / ".github/workflows/agentic-red.yml").read_text()
        self.assertIn("name: Public Core and Guard Lab Regressions", workflow)
        self.assertIn("contents: read", workflow)
        self.assertIn("persist-credentials: false", workflow)
        self.assertIn("if: always()", workflow)
        for obsolete in ("pip install agenticred", "issues.create", "services:",
                         "continue-on-error: true", "secrets.", "pull_request_target"):
            self.assertNotIn(obsolete, workflow)


if __name__ == "__main__":
    unittest.main()
