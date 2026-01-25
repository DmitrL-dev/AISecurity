#!/bin/bash
# SENTINEL DevKit Pre-commit Hook
# Enforces TDD Iron Law and basic quality checks

set -e

echo "🔍 SENTINEL DevKit Pre-commit Check..."

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ERRORS=0

# === Check 1: TDD Iron Law ===
echo ""
echo "📋 Check 1: TDD Iron Law"

# Get staged files
STAGED_SRC=$(git diff --cached --name-only | grep -E "^src/" || true)
STAGED_TESTS=$(git diff --cached --name-only | grep -E "test_|_test\.py|tests/" || true)

if [ -n "$STAGED_SRC" ] && [ -z "$STAGED_TESTS" ]; then
    echo -e "${RED}❌ TDD Iron Law Violation!${NC}"
    echo "   Production code changed without test changes."
    echo "   Changed src files:"
    echo "$STAGED_SRC" | sed 's/^/   - /'
    echo ""
    echo "   Add tests before committing or use --no-verify to bypass (NOT RECOMMENDED)"
    ERRORS=$((ERRORS + 1))
else
    echo -e "${GREEN}✅ TDD Iron Law: OK${NC}"
fi

# === Check 2: No Debug Code ===
echo ""
echo "📋 Check 2: Debug Code Check"

DEBUG_PATTERNS="console\.log|print\(|debugger|import pdb|breakpoint\(\)"
DEBUG_FILES=$(git diff --cached --name-only | xargs grep -l -E "$DEBUG_PATTERNS" 2>/dev/null || true)

if [ -n "$DEBUG_FILES" ]; then
    echo -e "${YELLOW}⚠️ Warning: Debug code detected${NC}"
    echo "$DEBUG_FILES" | sed 's/^/   - /'
    echo "   Consider removing before commit."
    # Warning only, not blocking
fi

# === Check 3: No Hardcoded Secrets ===
echo ""
echo "📋 Check 3: Secrets Check"

SECRET_PATTERNS="password\s*=|api_key\s*=|secret\s*=|token\s*="
SECRET_FILES=$(git diff --cached -U0 | grep -E "^\+" | grep -iE "$SECRET_PATTERNS" || true)

if [ -n "$SECRET_FILES" ]; then
    echo -e "${RED}❌ Potential hardcoded secrets detected!${NC}"
    echo "$SECRET_FILES" | head -5
    echo "   Review and remove before committing."
    ERRORS=$((ERRORS + 1))
else
    echo -e "${GREEN}✅ Secrets Check: OK${NC}"
fi

# === Check 4: Python Syntax ===
echo ""
echo "📋 Check 4: Python Syntax"

PYTHON_FILES=$(git diff --cached --name-only | grep -E "\.py$" || true)
SYNTAX_ERRORS=0

for file in $PYTHON_FILES; do
    if [ -f "$file" ]; then
        python -m py_compile "$file" 2>/dev/null || {
            echo -e "${RED}❌ Syntax error in $file${NC}"
            SYNTAX_ERRORS=$((SYNTAX_ERRORS + 1))
        }
    fi
done

if [ $SYNTAX_ERRORS -eq 0 ]; then
    echo -e "${GREEN}✅ Python Syntax: OK${NC}"
else
    ERRORS=$((ERRORS + SYNTAX_ERRORS))
fi

# === Summary ===
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ $ERRORS -gt 0 ]; then
    echo -e "${RED}❌ Pre-commit failed with $ERRORS error(s)${NC}"
    echo "   Fix issues or use 'git commit --no-verify' to bypass"
    exit 1
else
    echo -e "${GREEN}✅ All checks passed!${NC}"
    exit 0
fi
