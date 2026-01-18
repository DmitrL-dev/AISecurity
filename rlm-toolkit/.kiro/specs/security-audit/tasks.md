# RLM-Toolkit Security Audit - Tasks

## Task List

### Phase 0: Preparation
- [ ] **T0.1**: Set up audit environment and tools
- [ ] **T0.2**: Review existing security tests in `tests/test_security.py`

---

### Phase 1: Static Analysis (P0)

- [ ] **T1.1**: Scan for dangerous patterns (exec, eval, subprocess, etc.)
  - Files: `rlm_toolkit/**/*.py`
  - Tool: grep + Bandit
  - AC: US-1

- [ ] **T1.2**: Verify SecureREPL blocked imports list completeness
  - File: `rlm_toolkit/core/repl.py`
  - Check: BLOCKED_IMPORTS covers all dangerous modules
  - AC: AC-1.3

- [ ] **T1.3**: Verify SecureREPL blocked builtins list completeness
  - File: `rlm_toolkit/core/repl.py`
  - Check: BLOCKED_BUILTINS covers all dangerous functions
  - AC: AC-1.4

- [ ] **T1.4**: Audit tools/__init__.py for unsafe patterns
  - Check: PythonREPL, ShellTool, CalculatorTool
  - AC: AC-1.1, AC-1.2

- [ ] **T1.5**: Run pip-audit / safety check for CVEs
  - File: `pyproject.toml`
  - AC: AC-2.2

---

### Phase 2: Dynamic Analysis (P1)

- [ ] **T2.1**: Run existing security tests
  - Command: `pytest tests/test_security.py -v`
  - Expected: All pass

- [ ] **T2.2**: Test sandbox escapes with fuzzing payloads
  - Payloads: base64 obfuscation, chr() tricks, __class__ chains
  - AC: AC-1.2

- [ ] **T2.3**: Test input validation on tools
  - File tools: path traversal (../../etc/passwd)
  - SQL tools: injection ('OR 1=1--)
  - Shell tools: command injection (;rm -rf /)
  - AC: AC-4.1, AC-4.2, AC-4.3, AC-4.4

- [ ] **T2.4**: Verify secrets are not logged
  - Set OPENAI_API_KEY, enable debug logging
  - Check: Key is masked in output
  - AC: AC-5.1, AC-5.2

---

### Phase 3: Antivirus Testing (P0)

- [ ] **T3.1**: Build package and scan with VirusTotal
  - Command: `python -m build`
  - Upload to virustotal.com
  - AC: AC-3.2

- [ ] **T3.2**: Test with Microsoft Defender locally
  - Clone repo fresh
  - Wait for Defender scan
  - AC: AC-3.3

- [ ] **T3.3**: Test pip install from GitHub
  - `pip install git+https://github.com/DmitrL-dev/AISecurity#subdirectory=sentinel-community/rlm-toolkit`
  - Check: No AV alerts
  - AC: AC-3.1

---

### Phase 4: Documentation & Report

- [ ] **T4.1**: Create security_audit_report.md with findings
- [ ] **T4.2**: Update SECURITY.md with security model
- [ ] **T4.3**: Add security section to README.md
- [ ] **T4.4**: Create threat model diagram

---

## Progress Tracking

| Task | Status | Notes |
|------|--------|-------|
| T0.1 | [ ] | |
| T0.2 | [ ] | |
| T1.1 | [x] | Fallback exec() removed |
| T1.2 | [ ] | |
| T1.3 | [ ] | |
| T1.4 | [x] | PythonREPL fixed |
| T1.5 | [ ] | |
| T2.1 | [ ] | |
| T2.2 | [ ] | |
| T2.3 | [ ] | |
| T2.4 | [ ] | |
| T3.1 | [ ] | |
| T3.2 | [ ] | |
| T3.3 | [ ] | |
| T4.1 | [ ] | |
| T4.2 | [ ] | |
| T4.3 | [ ] | |
| T4.4 | [ ] | |

---

*Created: 2026-01-18*
