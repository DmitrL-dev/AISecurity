# Guard Lab: local input evaluation

Approved scope: a small, standalone evaluation tool for the already-public
AISecurity engine, not a new protection service or detector release.

## Contract

- Linux x86-64, Python 3.11, no runtime API, GPU, telemetry or account.
- `EngineRegistry.analyze_patterns` from public commit
  `b9fdd8a0e95accaf001017d243c1a16075d7a216`, default Cargo features only.
  This endpoint runs eight pattern engines, not the entire legacy engine list.
- A bounded UTF-8 JSONL file contains `text`, `label` (`benign`/`attack`), and
  `split` (`test`/`calibration`). Only test rows are evaluated. Calibration rows
  are overlap checks, not threshold fitting. The native boolean is the decision.
- Reject normalized duplicates, conflicting duplicates and cross-split overlap.
  This is exact normalized deduplication, not semantic independence detection.
- The native binding runs in a fresh resource-limited subprocess. A private empty
  signature directory overrides legacy ambient signature discovery. No text goes
  in process arguments, errors, reports or telemetry. This is not an OS sandbox
  against a malicious installed extension.
- Results use generated row numbers, aggregate TP/TN/FP/FN and separate execution
  errors. Never turn a crash, missing dependency or malformed response into safe.
- Dataset limits: 4 MiB, 1,000 records, 16 KiB UTF-8 per text; wall time at most
  120 seconds. File access is restricted to a regular, non-symlink basename in a
  directory selected by the caller. Reports go to stdout, not an implicit file.

## Release boundary

New code is written specifically for this public tool. No private source files,
detectors, policies, datasets, keys, models or predictions are copied. Fixtures
are newly authored synthetic demonstrations, not blind benchmark evidence.
The engine remains an external pinned dependency. Existing repository licenses
and third-party notices are not replaced. The new package carries Apache-2.0.

The review allowlist is `tools/guard-lab/**`, this spec and its plan, plus focused
README/QUICKSTART entry-point edits and a package-only `.gitignore` exception.
No unrelated legacy installer rewrite,
workflow execution, production change, history rewrite or public announcement.

## Acceptance

Observe failing tests before implementation; exercise the CLI, actual native
binding and clean install on a VPS. Check package/archive file membership and
secrets before GitHub publication. Record exact source, environment, commands
and limits. If native installation fails, publish no installability claim.
Historical credential issue #19 remains a separate unresolved investigation;
a clean new diff does not establish that the repository history is clean.
