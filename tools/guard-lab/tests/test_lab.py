"""Synthetic boundary cases; no user data or production fixtures."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest


class PackageTests(unittest.TestCase):
    def test_public_package_exists(self):
        self.assertIsNotNone(importlib.util.find_spec("guard_lab"))


def row(text="A synthetic gardening question.", label="benign", split="test"):
    return {"text": text, "label": label, "split": split}


class LoaderTests(unittest.TestCase):
    def setUp(self):
        from guard_lab.corpus import load_corpus, CorpusError
        self.load = load_corpus
        self.error = CorpusError
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def write_rows(self, rows):
        (self.root / "input.jsonl").write_text(
            "".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")

    def test_keeps_input_only_in_memory_and_assigns_opaque_ids(self):
        self.write_rows([row(), row("Another example", split="calibration")])
        records = self.load(self.root, "input.jsonl")
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0].row_id, "row-000001")
        self.assertEqual(records[1].split, "calibration")

    def test_rejects_invalid_schema_without_echoing_input(self):
        for value in [None, [], {}, row(label=True), row(split="train"),
                      row(text=""), row(text="\ud800"),
                      dict(row(), secret="synthetic-private-marker")]:
            with self.subTest(value=type(value).__name__):
                self.write_rows([value])
                with self.assertRaises(self.error) as caught:
                    self.load(self.root, "input.jsonl")
                self.assertEqual(str(caught.exception), "INVALID_RECORD")

    def test_rejects_normalized_duplicate_and_cross_split_overlap(self):
        for second, code in [(row("  HELLO   WORLD "), "DUPLICATE_TEXT"),
                             (row("hello world", label="attack"), "DUPLICATE_TEXT"),
                             (row("hello world", split="calibration"), "SPLIT_OVERLAP")]:
            self.write_rows([row("hello world"), second])
            with self.assertRaisesRegex(self.error, "^" + code + "$"):
                self.load(self.root, "input.jsonl")

    def test_rejects_duplicate_json_keys_and_malformed_utf8(self):
        for raw in [b'{"text":"a","text":"b","label":"benign","split":"test"}\n',
                    b'\xff', b'not-json\n', b'\n', b'']:
            (self.root / "input.jsonl").write_bytes(raw)
            with self.assertRaises(self.error):
                self.load(self.root, "input.jsonl")

    def test_unicode_separators_inside_json_are_not_record_delimiters(self):
        text = "alpha\u0085beta\u2028gamma\u2029delta"
        (self.root / "input.jsonl").write_text(json.dumps(row(text), ensure_ascii=False) + "\n", encoding="utf-8")
        records = self.load(self.root, "input.jsonl")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].text, text)

    def test_rejects_oversized_data_text_and_row_count(self):
        self.write_rows([row("a" * 16385)])
        with self.assertRaisesRegex(self.error, "^INVALID_RECORD$"):
            self.load(self.root, "input.jsonl")
        self.write_rows([row(str(n)) for n in range(1001)])
        with self.assertRaisesRegex(self.error, "^TOO_MANY_RECORDS$"):
            self.load(self.root, "input.jsonl")
        (self.root / "input.jsonl").write_bytes(b" " * (4 * 1024 * 1024 + 1))
        with self.assertRaisesRegex(self.error, "^FILE_TOO_LARGE$"):
            self.load(self.root, "input.jsonl")

    def test_rejects_paths_symlinks_and_special_files(self):
        self.write_rows([row()])
        (self.root / "link.jsonl").symlink_to(self.root / "input.jsonl")
        os.mkfifo(self.root / "pipe.jsonl")
        for name in ["../input.jsonl", "/input.jsonl", "x/input.jsonl", "link.jsonl",
                     "pipe.jsonl", "missing.jsonl", ".", ".."]:
            with self.subTest(name=name), self.assertRaises(self.error):
                self.load(self.root, name)

    def test_requires_test_rows(self):
        self.write_rows([row(split="calibration")])
        with self.assertRaisesRegex(self.error, "^NO_TEST_RECORDS$"):
            self.load(self.root, "input.jsonl")


class ReportTests(unittest.TestCase):
    def test_calibration_rows_are_never_scored(self):
        from guard_lab.corpus import Record
        from guard_lab.metrics import make_report
        r = make_report([Record("row-000001", "x", "attack", "calibration"),
                         Record("row-000002", "y", "benign", "test")], [False])
        self.assertEqual(r["calibration_records"], 1)
        self.assertEqual(r["test_records"], 1)
        self.assertEqual(r["counts"], {"tp": 0, "tn": 1, "fp": 0, "fn": 0, "errors": 0})
        self.assertEqual([x["row_id"] for x in r["rows"]], ["row-000002"])

    def test_hand_checked_confusion_counts_exclude_failures_and_calibration(self):
        from guard_lab.corpus import Record
        from guard_lab.metrics import make_report
        records = [Record(f"row-{i:06}", "synthetic-private-marker", label, "test")
                   for i, label in enumerate(["attack", "benign", "benign", "attack", "attack"], 1)]
        report = make_report(records, [True, False, True, False, "TIMEOUT"])
        self.assertEqual(report["counts"], {"tp": 1, "tn": 1, "fp": 1, "fn": 1, "errors": 1})
        self.assertEqual(report["metrics"], {"precision": .5, "recall": .5, "f1": .5,
                                           "accuracy_scored": .5, "coverage": .8})
        self.assertNotIn("synthetic-private-marker", json.dumps(report))
        self.assertIsNone(report["rows"][-1]["detected"])
        self.assertEqual(report["rows"][-1]["error"], "TIMEOUT")

    def test_no_successful_predictions_has_no_accuracy(self):
        from guard_lab.corpus import Record
        from guard_lab.metrics import make_report
        r = make_report([Record("row-000001", "x", "benign", "test")], ["ENGINE_ERROR"])
        self.assertIsNone(r["metrics"]["accuracy_scored"])
        self.assertEqual(r["metrics"]["coverage"], 0)
        self.assertEqual(r["counts"]["tn"], 0)

    def test_unknown_adapter_values_and_mismatched_counts_are_not_safe(self):
        from guard_lab.corpus import Record
        from guard_lab.metrics import make_report
        records = [Record("row-000001", "x", "benign", "test")]
        for results in [[None], [0], [{}], ["sensitive exception detail"], [], [False, False]]:
            report = make_report(records, results)
            self.assertEqual(report["counts"]["errors"], 1)
            self.assertEqual(report["counts"]["tn"], 0)
            self.assertNotIn("sensitive exception", json.dumps(report))


if __name__ == "__main__":
    unittest.main()
