# Weekly public CPU regressions

The **Public Core and Guard Lab Regressions** workflow replaces the nonfunctional
legacy AgenticRed wiring, with the owner's explicit agreement to change scope.
Its filename remains `agentic-red.yml` for workflow continuity. This is **not
AgenticRed, generative red-teaming, an HTTP gateway test or a benchmark score**.

Every Sunday at 03:00 UTC, on relevant pull requests, or by manual dispatch:

1. Initialize a receipt as `INCOMPLETE`, before dependency setup.
2. Exercise the gate's offline failure controls. Run the actual runner in a
   separate empty virtual environment: missing dependencies must produce exit 2
   and an `INCOMPLETE` receipt without fabricated coverage. Preserve that negative
   control separately as `missing-core.json`, then reinitialize the main receipt.
3. Install Guard Lab in a fresh Linux/Python 3.11 environment with Rust 1.88.0,
   one Cargo build worker and the documented bounded release profile. Install
   the exact native Git pin from `tools/guard-lab/requirements-core.txt`.
4. Verify the installed native distribution's actual Git origin and version.
5. Run all authored native cases from `sentinel-core/tests/test_public_core.py`
   (currently 48, minimum 48) and the Guard Lab suite with native tests enabled
   (currently 26, minimum 26). Zero tests, skips and expected failures cannot pass.
6. Upload the content-free JSON receipt even if a later step fails. Checkout or
   receipt-creation failure leaves a failed Actions job, not a fabricated report.

The target is the **installed release pin**, not an implicitly substituted HEAD
extension. Fixture and wrapper source comes from the checked-out revision. This
does not run all Rust unit tests, optional ML/CDN features, live external models
or a production service. It needs no API key, GPU or customer corpus. Dependency
installation uses public package/source registries; test inputs are authored
synthetic fixtures, including positive and negative detection expectations.

## Outcomes

- `PASSED` / exit 0: all required cases and tests executed successfully.
- `REGRESSION` / exit 1: completed assertions or expected decisions disagree.
  This is not an automatic finding of an exploitable security vulnerability.
- `INCOMPLETE` / exit 2: setup, dependency, execution, schema, coverage or test
  error prevents a complete result. A prior success is overwritten before a run.

If both a regression and an execution error occur, the overall status is
`INCOMPLETE`; available component counts remain in the receipt. Reports contain
counts, fixed reason codes, versions, source revision and fixture/runner digests,
not input text or exception details. They are provenance records, not attestations
against malicious test code or a compromised runner.

Actions check results and its normal notification settings report failures. The
workflow has only `contents: read`; it does not create or close issues, so it
cannot generate another weekly series of mislabeled vulnerability reports.

Reproduce after the documented Guard Lab installation, from the repository root:

```sh
python -m unittest discover -s .github/tests -p test_public_regressions.py -v
tools/guard-lab/.venv/bin/python .github/scripts/public_regressions.py
```

The original research integration is not restored or claimed. Its historical
coverage gap and the explicit replacement decision are tracked in issue #32.
