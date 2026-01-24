# TDD Enforcement (MANDATORY)

## Iron Law
Before writing ANY implementation code (*.py, *.ts, *.js files that are NOT tests):

1. **CHECK**: Does a test file exist for this feature?
2. **IF NO**: Create the test file FIRST
3. **IF YES**: Proceed with implementation

## Test File Patterns
- Python: `test_*.py` or `*_test.py`
- TypeScript/JavaScript: `*.test.ts`, `*.test.js`, `*.spec.ts`, `*.spec.js`

## Violation = BLOCKED
If you attempt to create/modify implementation code without corresponding tests:
- STOP immediately
- Create tests first
- Run tests (expect RED)
- Then implement

## No Exceptions
This rule applies to:
- New features
- Bug fixes
- Refactoring
- Performance improvements

The only exception is pure documentation changes (*.md files).
