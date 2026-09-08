"""Content-free evaluation reports. Execution failures are not decisions."""
from . import __version__

PUBLIC_COMMIT = "dd432e0baed808f539780bb21d94737617b40429"
ERRORS = frozenset({"TIMEOUT", "ENGINE_ERROR", "INVALID_RESULT", "DEPENDENCY_MISSING",
                    "ENGINE_ORIGIN_MISMATCH"})


def _ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def make_report(records, predictions):
    test_records = [record for record in records if record.split == "test"]
    if len(predictions) != len(test_records):
        predictions = ["INVALID_RESULT"] * len(test_records)
    counts = {"tp": 0, "tn": 0, "fp": 0, "fn": 0, "errors": 0}
    rows = []
    for record, prediction in zip(test_records, predictions):
        error = None
        if type(prediction) is bool:
            key = ("tp" if record.label == "attack" else "fp") if prediction else (
                "fn" if record.label == "attack" else "tn")
            counts[key] += 1
        else:
            error = prediction if isinstance(prediction, str) and prediction in ERRORS else "INVALID_RESULT"
            prediction = None
            counts["errors"] += 1
        rows.append({"row_id": record.row_id, "label": record.label,
                     "detected": prediction, "error": error})
    tp, tn, fp, fn = (counts[key] for key in ("tp", "tn", "fp", "fn"))
    scored = tp + tn + fp + fn
    return {"schema_version": 1, "tool_version": __version__, "mode": "local-input-evaluation",
            "engine": {"name": "sentinel-core", "endpoint": "EngineRegistry.analyze_patterns",
                       "expected_public_commit": PUBLIC_COMMIT, "runtime_signatures": "disabled"},
            "test_records": len(test_records), "calibration_records": len(records) - len(test_records),
            "counts": counts,
            "metrics": {"precision": _ratio(tp, tp + fp), "recall": _ratio(tp, tp + fn),
                        "f1": _ratio(2 * tp, 2 * tp + fp + fn),
                        "accuracy_scored": _ratio(tp + tn, scored),
                        "coverage": _ratio(scored, len(test_records))}, "rows": rows}
