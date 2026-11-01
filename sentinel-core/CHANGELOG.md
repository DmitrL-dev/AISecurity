# Public core maintenance

> **Frozen legacy snapshot.** 2.0.1 is the final entry; no further releases are planned.

## 2.0.1 — 2026-09-09

This updates the public detector code, not just its evaluation wrapper. It is
not an export of the current commercial Spectorn engine or rule collection.

### Detection fixes

- Input-handling and precision fixes in the public pattern core.

### Reproducibility and boundaries

- The Python distribution takes its version from Cargo; previously the wheel
  advertised `0.1.0` while the native binding returned `2.0.0`.
- `Cargo.lock` records the dependency resolution used for the maintenance tests.
  This does not pin the OS, compiler, build frontend or a bit-identical binary.
- `tests/public_core_regressions.rs` tests decoding and precision directly.
  `tests/test_public_core.py` checks the installed native binding on 48 authored
  synthetic cases and verifies that wheel/native versions agree. It is a
  regression suite, not an independent benchmark or a general accuracy claim.

The API, eight-engine `analyze_patterns` composition, signatures loader and
decision aggregation are unchanged. No model weights, private corpus, current
commercial policy or new hosted service is included.

Match offsets are not guaranteed to map back to the original input; do not use them
to redact it. Pattern matches alone do not establish intent or authorize tool execution.

Reference: [Maturin version metadata](https://www.maturin.rs/metadata#dynamic-metadata).
