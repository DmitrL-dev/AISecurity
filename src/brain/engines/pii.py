"""
PII Engine v2.0 - Enhanced Personal Data Detection

Recognizers:
  Standard (Presidio built-in):
    - PERSON, EMAIL, PHONE, CREDIT_CARD, IP_ADDRESS, etc.
  
  Russian Legal Entities:
    - RU_PASSPORT: 1234 567890
    - RU_INN_PERSONAL: 12 digits (физлицо)
    - RU_INN_COMPANY: 10 digits (юрлицо)
    - RU_OGRN: 13 digits (ОГРН юрлица)
    - RU_OGRNIP: 15 digits (ОГРНИП ИП)
    - RU_SNILS: 123-456-789 00
    - RU_BANK_ACCOUNT: 20 digits
    - RU_BIK: 9 digits
    - RU_KPP: 9 digits
  
  1C-Specific:
    - 1C_USER_ID: User identifiers
    - 1C_SESSION_ID: Session identifiers
    - 1C_CONFIG_PATH: Configuration paths
"""

import logging
import re
from typing import List, Dict, Optional
from dataclasses import dataclass, field

try:
    from presidio_analyzer import (
        AnalyzerEngine, RecognizerRegistry,
        PatternRecognizer, Pattern, EntityRecognizer
    )
    from presidio_analyzer.nlp_engine import NlpEngineProvider
    from presidio_anonymizer import AnonymizerEngine
    from presidio_anonymizer.entities import OperatorConfig
    PRESIDIO_AVAILABLE = True
except ImportError:
    PRESIDIO_AVAILABLE = False

logger = logging.getLogger("PIIEngine")


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class PIIEntity:
    """Detected PII entity."""
    entity_type: str
    text: str
    start: int
    end: int
    score: float
    category: str = "general"

    def to_dict(self) -> dict:
        return {
            "type": self.entity_type,
            "text": self.text,
            "start": self.start,
            "end": self.end,
            "score": self.score,
            "category": self.category
        }


@dataclass
class PIIResult:
    """Result from PII analysis."""
    has_pii: bool = False
    risk_score: float = 0.0
    entities: List[PIIEntity] = field(default_factory=list)
    anonymized_text: Optional[str] = None
    entity_counts: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "has_pii": self.has_pii,
            "risk_score": self.risk_score,
            "entity_count": len(self.entities),
            "entity_counts": self.entity_counts,
            "entities": [e.to_dict() for e in self.entities]
        }


# ============================================================================
# Russian Entity Patterns
# ============================================================================

RUSSIAN_PATTERNS = {
    # ИНН физлица (12 цифр) с контрольными суммами
    "RU_INN_PERSONAL": {
        "patterns": [
            r"\b\d{12}\b",  # 12 digits
        ],
        "score": 0.7,
        "category": "legal",
        "context": ["инн", "идентификационный номер", "налогоплательщик"]
    },

    # ИНН юрлица (10 цифр)
    "RU_INN_COMPANY": {
        "patterns": [
            r"\b\d{10}\b",  # 10 digits
        ],
        "score": 0.5,  # Lower score, need context
        "category": "legal",
        "context": ["инн", "организация", "компания", "юрлицо"]
    },

    # ОГРН (13 цифр)
    "RU_OGRN": {
        "patterns": [
            r"\b1\d{12}\b",  # Starts with 1, 13 digits total
        ],
        "score": 0.8,
        "category": "legal",
        "context": ["огрн", "регистрационный номер", "реестр"]
    },

    # ОГРНИП (15 цифр)
    "RU_OGRNIP": {
        "patterns": [
            r"\b3\d{14}\b",  # Starts with 3, 15 digits total
        ],
        "score": 0.8,
        "category": "legal",
        "context": ["огрнип", "предприниматель", "ип"]
    },

    # СНИЛС (XXX-XXX-XXX XX)
    "RU_SNILS": {
        "patterns": [
            r"\b\d{3}[-\s]?\d{3}[-\s]?\d{3}[-\s]?\d{2}\b",
        ],
        "score": 0.9,
        "category": "personal",
        "context": ["снилс", "страховой номер", "пенсионный"]
    },

    # Паспорт РФ (XXXX XXXXXX)
    "RU_PASSPORT": {
        "patterns": [
            r"\b\d{4}\s?\d{6}\b",
        ],
        "score": 0.8,
        "category": "personal",
        "context": ["паспорт", "серия", "номер"]
    },

    # Банковский счёт (20 цифр)
    "RU_BANK_ACCOUNT": {
        "patterns": [
            r"\b[34]\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\b",
            r"\b[34]\d{19}\b",
        ],
        "score": 0.7,
        "category": "financial",
        "context": ["счёт", "счет", "р/с", "расчётный"]
    },

    # БИК (9 цифр, начинается с 04)
    "RU_BIK": {
        "patterns": [
            r"\b04\d{7}\b",
        ],
        "score": 0.8,
        "category": "financial",
        "context": ["бик", "банк"]
    },

    # КПП (9 цифр)
    "RU_KPP": {
        "patterns": [
            r"\b\d{4}[0-9A-Z]{2}\d{3}\b",
        ],
        "score": 0.6,
        "category": "legal",
        "context": ["кпп", "код причины"]
    },
}


# ============================================================================
# 1C-Specific Patterns
# ============================================================================

ONEС_PATTERNS = {
    # 1C User IDs
    "1C_USER_ID": {
        "patterns": [
            r"\b[Uu]ser[_-]?[Ii][Dd][:=]\s*\w+",
            r"\bПользователь[:=]\s*\w+",
            r"\bИмяПользователя[:=]\s*\w+",
        ],
        "score": 0.6,
        "category": "1c",
        "context": ["1с", "1c", "пользователь", "user"]
    },

    # 1C Session IDs
    "1C_SESSION_ID": {
        "patterns": [
            r"\b[Ss]ession[_-]?[Ii][Dd][:=]\s*[a-f0-9-]+",
            r"\bСеанс[:=]\s*[a-f0-9-]+",
        ],
        "score": 0.5,
        "category": "1c",
        "context": ["сеанс", "session"]
    },

    # 1C Configuration paths
    "1C_CONFIG_PATH": {
        "patterns": [
            r"[A-Za-z]:\\[^\\]+\\1[CcСс][^\\]*\\",
            r"/home/[^/]+/1[CcСс]/",
            r"\\\\[^\\]+\\1[CcСс]",
        ],
        "score": 0.4,
        "category": "1c",
        "context": ["путь", "path", "конфигурация"]
    },

    # Database connection strings
    "1C_DB_CONNECTION": {
        "patterns": [
            r"Srvr=['\"]?[^;'\"]+['\"]?;Ref=['\"]?[^;'\"]+",
            r"File=['\"]?[A-Za-z]:[^;'\"]+",
        ],
        "score": 0.7,
        "category": "1c",
        "context": ["база", "database", "подключение"]
    },
}


# ============================================================================
# INN Validator
# ============================================================================

class INNValidator:
    """Validates Russian INN (ИНН) using checksum algorithm."""

    @staticmethod
    def validate_inn_10(inn: str) -> bool:
        """Validate 10-digit company INN."""
        if len(inn) != 10 or not inn.isdigit():
            return False

        weights = [2, 4, 10, 3, 5, 9, 4, 6, 8]
        checksum = sum(int(inn[i]) * weights[i] for i in range(9)) % 11 % 10
        return checksum == int(inn[9])

    @staticmethod
    def validate_inn_12(inn: str) -> bool:
        """Validate 12-digit personal INN."""
        if len(inn) != 12 or not inn.isdigit():
            return False

        weights1 = [7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
        weights2 = [3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8]

        checksum1 = sum(int(inn[i]) * weights1[i] for i in range(10)) % 11 % 10
        checksum2 = sum(int(inn[i]) * weights2[i] for i in range(11)) % 11 % 10

        return checksum1 == int(inn[10]) and checksum2 == int(inn[11])


# ============================================================================
# Context-Aware Recognizer
# ============================================================================

class ContextAwareRecognizer:
    """Recognizer that boosts score when context words are present."""

    def __init__(self, entity_type: str, patterns: List[str],
                 base_score: float, context_words: List[str],
                 category: str = "general"):
        self.entity_type = entity_type
        self.patterns = [re.compile(p, re.IGNORECASE) for p in patterns]
        self.base_score = base_score
        self.context_words = [w.lower() for w in context_words]
        self.category = category

    def analyze(self, text: str) -> List[PIIEntity]:
        """Find entities with context-aware scoring."""
        entities = []
        text_lower = text.lower()

        # Check for context words (boost score)
        has_context = any(cw in text_lower for cw in self.context_words)
        score_boost = 0.2 if has_context else 0.0

        for pattern in self.patterns:
            for match in pattern.finditer(text):
                final_score = min(1.0, self.base_score + score_boost)

                # Validate INN if applicable
                if self.entity_type in ("RU_INN_PERSONAL", "RU_INN_COMPANY"):
                    matched_text = match.group()
                    if self.entity_type == "RU_INN_PERSONAL":
                        if not INNValidator.validate_inn_12(matched_text):
                            final_score *= 0.3  # Reduce score for invalid
                    else:
                        if not INNValidator.validate_inn_10(matched_text):
                            final_score *= 0.3

                entities.append(PIIEntity(
                    entity_type=self.entity_type,
                    text=match.group(),
                    start=match.start(),
                    end=match.end(),
                    score=final_score,
                    category=self.category
                ))

        return entities


# ============================================================================
# Main PII Engine
# ============================================================================

class PIIEngine:
    """
    PII Engine v2.0 - Enhanced Personal Data Detection.

    Supports:
      - Standard entities (via Presidio)
      - Russian legal entities (ИНН, ОГРН, СНИЛС, etc.)
      - 1C-specific patterns
      - Context-aware scoring
      - INN validation with checksums
    """

    def __init__(self, use_presidio: bool = True, languages: List[str] = None):
        logger.info("Initializing PII Engine v2.0...")

        self.use_presidio = use_presidio and PRESIDIO_AVAILABLE
        self.languages = languages or ["ru", "en"]

        # Presidio components
        self.analyzer = None
        self.anonymizer = None

        # Custom recognizers
        self.custom_recognizers: List[ContextAwareRecognizer] = []

        # Initialize
        self._init_presidio()
        self._init_custom_recognizers()

        logger.info(
            f"PII Engine v2.0 initialized (Presidio: {self.use_presidio})")

    def _init_presidio(self):
        """Initialize Presidio components."""
        if not self.use_presidio:
            return

        try:
            # Configure NLP Engine
            configuration = {
                "nlp_engine_name": "spacy",
                "models": [
                    {"lang_code": "en", "model_name": "en_core_web_lg"},
                    {"lang_code": "ru", "model_name": "ru_core_news_lg"},
                ],
            }
            provider = NlpEngineProvider(nlp_configuration=configuration)
            nlp_engine = provider.create_engine()

            # Initialize Registry
            registry = RecognizerRegistry()
            registry.load_predefined_recognizers(
                languages=self.languages, nlp_engine=nlp_engine
            )

            # Add Russian pattern recognizers
            for entity_type, config in RUSSIAN_PATTERNS.items():
                patterns = [
                    Pattern(name=f"{entity_type}_p{i}",
                            regex=p, score=config["score"])
                    for i, p in enumerate(config["patterns"])
                ]
                recognizer = PatternRecognizer(
                    supported_entity=entity_type,
                    supported_language="ru",
                    patterns=patterns,
                    context=config.get("context", [])
                )
                registry.add_recognizer(recognizer)

            # Create Analyzer
            self.analyzer = AnalyzerEngine(
                registry=registry,
                nlp_engine=nlp_engine
            )
            self.anonymizer = AnonymizerEngine()

        except Exception as e:
            logger.warning(
                f"Presidio init failed: {e}. Using custom recognizers only.")
            self.use_presidio = False

    def _init_custom_recognizers(self):
        """Initialize custom recognizers."""
        # Russian patterns
        for entity_type, config in RUSSIAN_PATTERNS.items():
            self.custom_recognizers.append(ContextAwareRecognizer(
                entity_type=entity_type,
                patterns=config["patterns"],
                base_score=config["score"],
                context_words=config.get("context", []),
                category=config.get("category", "general")
            ))

        # 1C patterns
        for entity_type, config in ONEС_PATTERNS.items():
            self.custom_recognizers.append(ContextAwareRecognizer(
                entity_type=entity_type,
                patterns=config["patterns"],
                base_score=config["score"],
                context_words=config.get("context", []),
                category=config.get("category", "1c")
            ))

    def analyze(self, text: str, language: str = "ru") -> PIIResult:
        """
        Analyze text for PII.

        Returns PIIResult with detected entities and risk score.
        """
        result = PIIResult()
        entities = []

        # Run Presidio analysis if available
        if self.use_presidio and self.analyzer:
            try:
                presidio_results = self.analyzer.analyze(
                    text=text, language=language)
                for r in presidio_results:
                    entities.append(PIIEntity(
                        entity_type=r.entity_type,
                        text=text[r.start:r.end],
                        start=r.start,
                        end=r.end,
                        score=r.score,
                        category="standard"
                    ))
            except Exception as e:
                logger.warning(f"Presidio analysis error: {e}")

        # Run custom recognizers
        for recognizer in self.custom_recognizers:
            custom_entities = recognizer.analyze(text)
            entities.extend(custom_entities)

        # Deduplicate (same span, keep highest score)
        entities = self._deduplicate(entities)

        # Build result
        result.entities = entities
        result.has_pii = len(entities) > 0

        # Calculate risk score
        if entities:
            max_score = max(e.score for e in entities)
            category_weights = {
                "personal": 1.0,
                "financial": 0.9,
                "legal": 0.7,
                "1c": 0.5,
                "standard": 0.8,
                "general": 0.6
            }
            weighted_scores = [
                e.score * category_weights.get(e.category, 0.6)
                for e in entities
            ]
            result.risk_score = min(100.0, sum(weighted_scores) * 20)

        # Count by type
        for e in entities:
            result.entity_counts[e.entity_type] = \
                result.entity_counts.get(e.entity_type, 0) + 1

        return result

    def _deduplicate(self, entities: List[PIIEntity]) -> List[PIIEntity]:
        """Remove duplicate detections for same span."""
        if not entities:
            return entities

        # Group by span
        by_span: Dict[tuple, PIIEntity] = {}
        for e in entities:
            key = (e.start, e.end)
            if key not in by_span or e.score > by_span[key].score:
                by_span[key] = e

        return list(by_span.values())

    def anonymize(self, text: str, result: PIIResult = None) -> str:
        """Anonymize detected PII in text."""
        if result is None:
            result = self.analyze(text)

        if not result.entities:
            return text

        # Sort by position (reverse) to replace from end
        sorted_entities = sorted(
            result.entities, key=lambda e: e.start, reverse=True)

        anonymized = text
        for entity in sorted_entities:
            placeholder = f"<{entity.entity_type}>"
            anonymized = anonymized[:entity.start] + \
                placeholder + anonymized[entity.end:]

        return anonymized

    # Backward compatibility
    def scan(self, text: str) -> dict:
        """Legacy interface."""
        result = self.analyze(text)
        return result.to_dict()
