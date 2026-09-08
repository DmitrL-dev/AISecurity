"""Exercise audit target selection and failure propagation without network calls."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / ".github/scripts/audit-python-dependencies.sh"


class DependencyAuditTests(unittest.TestCase):
    def run_audit(self, failure=0):
        self.assertTrue(SCRIPT.is_file(), "dependency audit runner is missing")
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            # Only the network-facing auditor is substituted. The shell runner,
            # argument handling and exit propagation are the production code.
            auditor = temp / "audit python"
            auditor.write_text(
                "#!/usr/bin/env python3\n"
                "import json, os, pathlib, sys\n"
                "log = pathlib.Path(os.environ['AUDIT_TEST_LOG'])\n"
                "calls = json.loads(log.read_text()) if log.exists() else []\n"
                "calls.append(sys.argv[1:])\n"
                "log.write_text(json.dumps(calls))\n"
                "status = int(os.environ['AUDIT_TEST_EXIT'])\n"
                "if status == 3:\n"
                "    status = 1 if '--strict' in sys.argv else 0\n"
                "sys.exit(status)\n",
                encoding="utf-8")
            auditor.chmod(0o700)
            log = temp / "calls.json"
            reports = temp / "reports with spaces"
            result = subprocess.run(
                ["sh", str(SCRIPT), str(auditor), str(reports)],
                cwd=temp, text=True, capture_output=True, timeout=10,
                env={**os.environ, "AUDIT_TEST_LOG": str(log),
                     "AUDIT_TEST_EXIT": str(failure)})
            calls = json.loads(log.read_text()) if log.exists() else []
            return result, calls, str(reports)

    def test_audits_tools_runtime_packages_and_build_inputs(self):
        result, calls, reports = self.run_audit()
        self.assertEqual(result.returncode, 0, result.stderr)
        targets = [
            (["--local"], "tools.json"),
            ([str(ROOT)], "runtime.json"),
            ([str(ROOT / "tools/guard-lab")], "guard-lab.json"),
            (["-r", str(ROOT / "tools/guard-lab/build-constraints.txt")],
             "guard-lab-build.json"),
        ]
        self.assertEqual(calls, [
            ["-m", "pip_audit", "--strict", *target, "--format", "json", "--output",
             str(Path(reports) / filename)]
            for target, filename in targets
        ])

    def test_vulnerabilities_fail_job_but_keep_collecting_other_reports(self):
        result, calls, _ = self.run_audit(failure=1)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(len(calls), 4)

    def test_auditor_operational_error_is_not_a_clean_scan(self):
        result, calls, _ = self.run_audit(failure=2)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(len(calls), 4)

    def test_skipped_dependency_is_not_a_complete_audit(self):
        # pip-audit 2.10.1 accepts incomplete coverage unless strict is requested.
        result, calls, _ = self.run_audit(failure=3)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(len(calls), 4)


if __name__ == "__main__":
    unittest.main()
