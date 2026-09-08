# Public core maintenance

## 2.0.1 — 2026-09-09

This updates the public detector code, not just its evaluation wrapper. It is
not an export of the current commercial Spectorn engine or rule collection.

### Detection fixes

- Percent decoding now assembles UTF-8 bytes correctly, including Cyrillic,
  CJK and emoji. Malformed escape syntax no longer consumes a subsequent escape.
- Base64 accepts readable UTF-8, preserves identifier fragments and replaces
  each original token once. Its scan view tolerates excess padding and unused
  nonzero bits so it does not miss text accepted by permissive decoders.
- Numeric HTML entities decode valid Unicode scalars. Decoded fullwidth and
  zero-width text passes through the existing canonicalization again.
- Ordinary model-identity and capability questions are no longer independent
  injection findings. This removes four discovery-only patterns, not the
  surrounding scan: mixed requests still reach extraction and override rules.

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

Normalization is a derived scan view: one HTML, percent and base64 pass, followed
by Unicode canonicalization. It is not a recursive decoder or a replacement for
an application's parser. Invalid percent-decoded UTF-8 uses replacement
characters; non-text base64 and impossible data lengths remain opaque. Match
offsets are not a guaranteed mapping back to the original pre-normalized text. Do not use them for
redaction of the original input. Pattern matches alone do not establish intent
or authorize tool execution.

References: [percent-encoded octets](https://www.rfc-editor.org/rfc/rfc3986#section-2.1),
[base64 canonical encoding](https://www.rfc-editor.org/rfc/rfc4648#section-3.5),
[Maturin version metadata](https://www.maturin.rs/metadata#dynamic-metadata).
