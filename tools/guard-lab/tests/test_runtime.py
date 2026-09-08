"""Native protocol and resource boundaries; synthetic fixtures only."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class NativeProtocolTests(unittest.TestCase):
    def test_only_strict_boolean_and_finite_score_are_accepted(self):
        from guard_lab.runtime import decode_predictions
        for value in [{}, None, {"detected": 0, "risk_score": 0},
                      {"detected": False, "risk_score": float("nan")},
                      {"detected": False, "risk_score": True},
                      {"detected": True, "risk_score": 2},
                      {"detected": False, "risk_score": 0, "text": "private-marker"}]:
            self.assertEqual(decode_predictions(json.dumps([value]).encode(), 1), ["INVALID_RESULT"])
        self.assertEqual(decode_predictions(b'[{"detected":false,"risk_score":0}]', 1), [False])
        self.assertEqual(decode_predictions(b'[{"detected":true,"risk_score":0.7}]', 1), [True])

    def test_bad_envelope_does_not_produce_a_safe_prediction(self):
        from guard_lab.runtime import decode_predictions
        for raw in [b'', b'not json', b'{}', b'[]', b'[false,false]', b'\xff',
                    b'[{"error":"private exception"}]']:
            self.assertEqual(decode_predictions(raw, 1), ["INVALID_RESULT"])

    def test_out_of_range_large_integer_and_duplicate_keys_are_invalid_results(self):
        from guard_lab.runtime import decode_predictions
        for raw in [json.dumps([{"detected": False, "risk_score": 10**300}]).encode(),
                    b'[{"detected":true,"detected":false,"risk_score":0}]']:
            self.assertEqual(decode_predictions(raw, 1), ["INVALID_RESULT"])

    def test_valid_unicode_corpus_fits_native_input_budget(self):
        from guard_lab.runtime import run_process
        texts = ["я" * 8100 + f"{i:03}" for i in range(250)]
        # Real subprocess at the same byte-limited IPC boundary, no native cost.
        program = ("import json,sys; raw=sys.stdin.buffer.read(8388609); "
                   "sys.exit(6) if len(raw)>8388608 else None; data=json.loads(raw); "
                   "print(json.dumps([{'detected':False,'risk_score':0} for _ in data]))")
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(run_process([sys.executable, "-I", "-c", program], texts,
                                         Path(directory), 5), [False] * 250)

    def test_dependency_origin_requires_exact_public_commit_and_subdirectory(self):
        from guard_lab._worker import valid_origin
        origin = {"url": "https://github.com/DmitrL-dev/AISecurity.git",
                  "subdirectory": "sentinel-core", "vcs_info": {"vcs": "git",
                  "commit_id": "dd432e0baed808f539780bb21d94737617b40429"}}
        self.assertTrue(valid_origin(origin))
        for changed in [{}, dict(origin, url="https://example.invalid/other.git"),
                        dict(origin, subdirectory="other"),
                        dict(origin, vcs_info={"vcs": "git", "commit_id": "main"}),
                        dict(origin, vcs_info={"vcs": "git",
                             "commit_id": "b9fdd8a0e95accaf001017d243c1a16075d7a216"})]:
            self.assertFalse(valid_origin(changed))

    def test_worker_deadline_and_crash_are_errors_not_safe(self):
        from guard_lab.runtime import run_process
        with tempfile.TemporaryDirectory() as directory:
            for command, code in [([sys.executable, "-I", "-c", "import time; time.sleep(5)"], "TIMEOUT"),
                                  ([sys.executable, "-I", "-c", "raise RuntimeError('private-marker')"], "ENGINE_ERROR")]:
                self.assertEqual(run_process(command, ["text"], Path(directory), .1), [code])


class CLITests(unittest.TestCase):
    def test_malformed_input_is_fixed_error_and_does_not_echo_content_or_path(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "input.jsonl").write_text("private-marker", encoding="utf-8")
            result = subprocess.run([sys.executable, "-m", "guard_lab", "--data-dir", directory,
                                     "--input", "input.jsonl"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, "")
            self.assertEqual(result.stderr, "guard-lab: INVALID_JSONL\n")

    def test_invalid_timeout_never_starts_a_run(self):
        for timeout in ["0", "-1", "nan", "121", "inf"]:
            result = subprocess.run([sys.executable, "-m", "guard_lab", "--demo", "--timeout", timeout],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertNotIn('"counts"', result.stdout)


if __name__ == "__main__":
    unittest.main()
