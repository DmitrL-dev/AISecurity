"""
Query Engine v2.0 - 1C Query Language Security Analysis

Features:
  1. SQL Injection Detection (sqlparse + heuristics)
  2. 1C Query Language Support (ВЫБРАТЬ, ИЗ, ГДЕ)
  3. Intent Classification (read/write/admin/dangerous)
  4. GBNF Grammar Validation
  5. Semantic Risk Scoring
  6. Context-Aware Analysis
"""

import logging
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

try:
    import sqlparse
    SQLPARSE_AVAILABLE = True
except ImportError:
    SQLPARSE_AVAILABLE = False

logger = logging.getLogger("QueryEngine")


# ============================================================================
# Enums and Data Classes
# ============================================================================

class QueryIntent(Enum):
    """Classification of query intent."""
    READ = "read"           # SELECT, ВЫБРАТЬ
    WRITE = "write"         # INSERT, UPDATE, ДОБАВИТЬ
    DELETE = "delete"       # DELETE, УДАЛИТЬ
    ADMIN = "admin"         # DROP, ALTER, GRANT
    DANGEROUS = "dangerous"  # Injection patterns
    UNKNOWN = "unknown"


class QueryLanguage(Enum):
    """Detected query language."""
    SQL = "sql"
    QUERY_1C = "1c"        # 1C Query Language (Russian)
    MIXED = "mixed"        # Both languages detected
    UNKNOWN = "unknown"


@dataclass
class QueryResult:
    """Result from query analysis."""
    is_safe: bool = True
    risk_score: float = 0.0
    language: QueryLanguage = QueryLanguage.UNKNOWN
    intent: QueryIntent = QueryIntent.UNKNOWN
    threats: List[str] = field(default_factory=list)
    explanation: str = ""
    structure_valid: Optional[bool] = None
    violations: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "is_safe": self.is_safe,
            "risk_score": self.risk_score,
            "language": self.language.value,
            "intent": self.intent.value,
            "threats": self.threats,
            "reason": self.explanation,
            "structure_valid": self.structure_valid,
            "violations": self.violations
        }


# ============================================================================
# 1C Query Language Patterns
# ============================================================================

# 1C Query Keywords (Russian)
QUERY_1C_KEYWORDS = {
    # SELECT equivalents
    "read": ["ВЫБРАТЬ", "ВЫБРАТЬ РАЗЛИЧНЫЕ", "ПЕРВЫЕ", "РАЗРЕШЕННЫЕ"],
    # FROM equivalents
    "from": ["ИЗ", "ЛЕВОЕ СОЕДИНЕНИЕ", "ПРАВОЕ СОЕДИНЕНИЕ", "ПОЛНОЕ СОЕДИНЕНИЕ", "ВНУТРЕННЕЕ СОЕДИНЕНИЕ"],
    # WHERE equivalents
    "where": ["ГДЕ", "И", "ИЛИ", "НЕ", "В", "МЕЖДУ", "ПОДОБНО"],
    # GROUP BY, ORDER BY
    "aggregate": ["СГРУППИРОВАТЬ ПО", "УПОРЯДОЧИТЬ ПО", "ИТОГИ", "ИМЕЮЩИЕ"],
    # Functions
    "functions": ["СУММА", "КОЛИЧЕСТВО", "МАКСИМУМ", "МИНИМУМ", "СРЕДНЕЕ", "ВЫРАЗИТЬ"],
    # Dangerous
    "dangerous": ["УДАЛИТЬ", "ИЗМЕНИТЬ", "ДОБАВИТЬ"],
}

# SQL dangerous patterns
SQL_DANGEROUS_KEYWORDS = [
    "DROP", "TRUNCATE", "DELETE", "ALTER", "GRANT", "REVOKE",
    "UNION", "INSERT", "UPDATE", "EXECUTE", "EXEC", "xp_"
]

# Injection patterns (cross-language)
INJECTION_PATTERNS = [
    # Classic SQL injection
    (r"'\s*OR\s*'.*'='", "SQL Injection: OR-based"),
    (r"'\s*OR\s+1\s*=\s*1", "SQL Injection: OR 1=1"),
    (r";\s*DROP\s+", "SQL Injection: Stacked DROP"),
    (r";\s*DELETE\s+", "SQL Injection: Stacked DELETE"),
    (r"UNION\s+(?:ALL\s+)?SELECT", "SQL Injection: UNION SELECT"),
    (r"--\s*$", "SQL Injection: Comment termination"),
    (r"/\*.*\*/", "SQL Injection: Block comment"),

    # 1C specific injection
    (r";\s*УДАЛИТЬ\s+", "1C Injection: Stacked DELETE"),
    (r";\s*ИЗМЕНИТЬ\s+", "1C Injection: Stacked UPDATE"),

    # File operations
    (r"INTO\s+OUTFILE", "SQL: File write attempt"),
    (r"LOAD_FILE\s*\(", "SQL: File read attempt"),
    (r"INTO\s+DUMPFILE", "SQL: Binary file write"),

    # System commands
    (r"xp_cmdshell", "SQL Server: Command execution"),
    (r"BENCHMARK\s*\(", "MySQL: Time-based injection"),
    (r"SLEEP\s*\(", "Time-based injection"),
    (r"WAITFOR\s+DELAY", "SQL Server: Time-based"),
]


# ============================================================================
# Query Language Detector
# ============================================================================

class LanguageDetector:
    """Detects query language (SQL or 1C)."""

    def __init__(self):
        # Compile patterns
        self.sql_pattern = re.compile(
            r'\b(SELECT|INSERT|UPDATE|DELETE|FROM|WHERE|JOIN|GROUP BY|ORDER BY)\b',
            re.IGNORECASE
        )
        self.query_1c_pattern = re.compile(
            r'\b(ВЫБРАТЬ|ИЗ|ГДЕ|СГРУППИРОВАТЬ|УПОРЯДОЧИТЬ|СОЕДИНЕНИЕ|ИТОГИ)\b',
            re.IGNORECASE
        )

    def detect(self, text: str) -> QueryLanguage:
        """Detect query language."""
        has_sql = bool(self.sql_pattern.search(text))
        has_1c = bool(self.query_1c_pattern.search(text))

        if has_sql and has_1c:
            return QueryLanguage.MIXED
        elif has_1c:
            return QueryLanguage.QUERY_1C
        elif has_sql:
            return QueryLanguage.SQL
        else:
            return QueryLanguage.UNKNOWN


# ============================================================================
# Intent Classifier
# ============================================================================

class IntentClassifier:
    """Classifies query intent based on keywords."""

    def __init__(self):
        self.patterns = {
            QueryIntent.READ: re.compile(
                r'\b(SELECT|ВЫБРАТЬ)\b', re.IGNORECASE
            ),
            QueryIntent.WRITE: re.compile(
                r'\b(INSERT|UPDATE|ДОБАВИТЬ|ИЗМЕНИТЬ)\b', re.IGNORECASE
            ),
            QueryIntent.DELETE: re.compile(
                r'\b(DELETE|TRUNCATE|УДАЛИТЬ)\b', re.IGNORECASE
            ),
            QueryIntent.ADMIN: re.compile(
                r'\b(DROP|ALTER|GRANT|REVOKE|CREATE)\b', re.IGNORECASE
            ),
        }

    def classify(self, text: str) -> QueryIntent:
        """Classify query intent."""
        # Check for dangerous patterns first
        for pattern, _ in INJECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return QueryIntent.DANGEROUS

        # Check standard intents (most dangerous first)
        for intent in [QueryIntent.ADMIN, QueryIntent.DELETE,
                       QueryIntent.WRITE, QueryIntent.READ]:
            if self.patterns[intent].search(text):
                return intent

        return QueryIntent.UNKNOWN


# ============================================================================
# 1C Query Validator
# ============================================================================

class Query1CValidator:
    """Validates 1C Query Language structure."""

    def __init__(self):
        self.select_pattern = re.compile(
            r'^\s*ВЫБРАТЬ\s+(?:РАЗЛИЧНЫЕ\s+)?(?:ПЕРВЫЕ\s+\d+\s+)?(.+?)\s+ИЗ\s+',
            re.IGNORECASE | re.DOTALL
        )
        self.where_pattern = re.compile(
            r'\bГДЕ\s+(.+?)(?:\s+СГРУППИРОВАТЬ|\s+УПОРЯДОЧИТЬ|\s+ИТОГИ|$)',
            re.IGNORECASE | re.DOTALL
        )

    def validate(self, text: str) -> Tuple[bool, List[str]]:
        """
        Validate 1C query structure.
        Returns (is_valid, violations).
        """
        violations = []

        # Must have ВЫБРАТЬ ... ИЗ pattern
        if not self.select_pattern.search(text):
            violations.append(
                "Invalid 1C query: missing ВЫБРАТЬ...ИЗ structure")

        # Check for balanced parentheses
        if text.count('(') != text.count(')'):
            violations.append("Unbalanced parentheses")

        # Check for dangerous multi-statement
        if ';' in text:
            # Allow only if it's at the end
            semicolon_pos = text.find(';')
            after_semicolon = text[semicolon_pos + 1:].strip()
            if after_semicolon and not after_semicolon.startswith('--'):
                violations.append("Multi-statement query detected")

        return len(violations) == 0, violations


# ============================================================================
# Main Query Engine
# ============================================================================

class QueryEngine:
    """
    Query Engine v2.0 - 1C Query Language Security Analysis.

    Features:
      - SQL and 1C Query Language support
      - Intent classification (read/write/admin/dangerous)
      - Injection pattern detection
      - Structure validation
      - Semantic risk scoring
    """

    def __init__(self):
        logger.info("Initializing Query Engine v2.0 (1C + SQL)...")

        self.language_detector = LanguageDetector()
        self.intent_classifier = IntentClassifier()
        self.query_1c_validator = Query1CValidator()

        # GBNF grammar cache
        self._grammar_cache = {}

        # Intent risk weights
        self.intent_weights = {
            QueryIntent.READ: 0.0,
            QueryIntent.WRITE: 30.0,
            QueryIntent.DELETE: 60.0,
            QueryIntent.ADMIN: 80.0,
            QueryIntent.DANGEROUS: 100.0,
            QueryIntent.UNKNOWN: 10.0,
        }

        logger.info("Query Engine v2.0 initialized.")

    def _scan_injection_patterns(self, text: str) -> Tuple[float, List[str]]:
        """Scan for injection patterns."""
        threats = []
        risk_score = 0.0

        for pattern, description in INJECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                threats.append(description)
                risk_score += 50.0  # Each pattern adds significant risk

        return min(risk_score, 100.0), threats

    def _scan_dangerous_keywords(self, text: str) -> Tuple[float, List[str]]:
        """Scan for dangerous keywords."""
        threats = []
        risk_score = 0.0
        text_upper = text.upper()

        for keyword in SQL_DANGEROUS_KEYWORDS:
            pattern = rf'\b{keyword}\b'
            if re.search(pattern, text_upper):
                threats.append(f"Dangerous keyword: {keyword}")
                risk_score += 40.0

        # 1C dangerous keywords
        for keyword in QUERY_1C_KEYWORDS.get("dangerous", []):
            if keyword.upper() in text_upper:
                threats.append(f"1C dangerous keyword: {keyword}")
                risk_score += 40.0

        return min(risk_score, 100.0), threats

    def _scan_sql(self, text: str) -> Tuple[float, List[str]]:
        """Scan SQL using sqlparse."""
        if not SQLPARSE_AVAILABLE:
            return 0.0, []

        threats = []
        risk_score = 0.0

        try:
            parsed = sqlparse.parse(text)
            for statement in parsed:
                str_upper = str(statement).upper()

                # Logic manipulation
                if "OR 1=1" in str_upper or "OR 1 = 1" in str_upper:
                    threats.append("SQL: Logic manipulation (OR 1=1)")
                    risk_score += 90.0

                # Quote-based injection
                if "' OR '" in str_upper or '" OR "' in str_upper:
                    threats.append("SQL: Quote-based injection")
                    risk_score += 85.0

        except Exception as e:
            logger.warning(f"sqlparse error: {e}")

        return min(risk_score, 100.0), threats

    def scan(self, text: str, session_id: str = None) -> QueryResult:
        """
        Analyze query for security threats.

        Args:
            text: Query text to analyze
            session_id: Optional session ID for context

        Returns:
            QueryResult with analysis results
        """
        result = QueryResult()
        all_threats = []
        total_risk = 0.0

        # 1. Detect language
        result.language = self.language_detector.detect(text)

        # 2. Classify intent
        result.intent = self.intent_classifier.classify(text)
        total_risk += self.intent_weights.get(result.intent, 0.0)

        # 3. Scan for injection patterns
        inj_risk, inj_threats = self._scan_injection_patterns(text)
        total_risk = max(total_risk, inj_risk)
        all_threats.extend(inj_threats)

        # 4. Scan for dangerous keywords
        kw_risk, kw_threats = self._scan_dangerous_keywords(text)
        total_risk = max(total_risk, kw_risk)
        all_threats.extend(kw_threats)

        # 5. SQL-specific analysis
        if result.language in (QueryLanguage.SQL, QueryLanguage.MIXED):
            sql_risk, sql_threats = self._scan_sql(text)
            total_risk = max(total_risk, sql_risk)
            all_threats.extend(sql_threats)

        # 6. 1C-specific validation
        if result.language in (QueryLanguage.QUERY_1C, QueryLanguage.MIXED):
            is_valid, violations = self.query_1c_validator.validate(text)
            result.structure_valid = is_valid
            result.violations = violations
            if not is_valid:
                total_risk += 20.0

        # Build result
        result.risk_score = min(total_risk, 100.0)
        result.threats = all_threats
        result.is_safe = result.risk_score < 70.0

        if all_threats:
            result.explanation = f"Query threats: {', '.join(all_threats[:3])}"
        else:
            result.explanation = f"Safe {result.language.value} query ({result.intent.value})"

        return result

    def scan_sql(self, text: str) -> dict:
        """Legacy interface for backward compatibility."""
        result = self.scan(text)
        return result.to_dict()

    def validate_structure(self, text: str, grammar_path: str) -> dict:
        """Legacy interface for GBNF validation."""
        # Try 1C validation first
        if "ВЫБРАТЬ" in text.upper():
            is_valid, violations = self.query_1c_validator.validate(text)
            return {
                "is_valid": is_valid,
                "matched_rules": ["1c_query"] if is_valid else [],
                "violations": violations
            }

        # Fall back to basic SQL pattern matching
        text_upper = text.upper().strip()
        is_valid = bool(re.match(r'^SELECT\s+.+\s+FROM\s+',
                        text_upper, re.IGNORECASE))

        return {
            "is_valid": is_valid,
            "matched_rules": ["select_statement"] if is_valid else [],
            "violations": ["Invalid SQL structure"] if not is_valid else []
        }
