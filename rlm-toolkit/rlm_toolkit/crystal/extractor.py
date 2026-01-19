"""
HPE (Hierarchical Primitive Encoder) Extractor for C³.

Extracts semantic primitives from source code:
- Classes, functions, methods
- Variables, constants
- Imports, dependencies
- Relations between entities
"""

import re
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .hierarchy import Primitive, FileCrystal

logger = logging.getLogger("rlm_crystal.extractor")


class PrimitiveType(Enum):
    """Types of primitives that can be extracted."""

    CLASS = "CLASS"
    FUNCTION = "FUNCTION"
    METHOD = "METHOD"
    VARIABLE = "VARIABLE"
    CONSTANT = "CONSTANT"
    IMPORT = "IMPORT"
    DECORATOR = "DECORATOR"
    DOCSTRING = "DOCSTRING"
    COMMENT = "COMMENT"
    RELATION = "RELATION"


class HPEExtractor:
    """
    Hierarchical Primitive Encoder.

    Extracts semantic primitives from source code using pattern matching
    and optional NER (when spaCy is available).
    """

    # Python patterns for extraction
    PATTERNS = {
        PrimitiveType.CLASS: r"^\s*class\s+(\w+)\s*[:\(]",
        PrimitiveType.FUNCTION: r"^\s*def\s+(\w+)\s*\(",
        PrimitiveType.DECORATOR: r"^\s*@(\w+)",
        PrimitiveType.IMPORT: r"^(?:from\s+(\S+)\s+)?import\s+(.+)",
        PrimitiveType.CONSTANT: r"^([A-Z][A-Z0-9_]+)\s*=",
        PrimitiveType.VARIABLE: r"^(\w+)\s*=\s*(?!lambda)",
        PrimitiveType.DOCSTRING: r'"""(.+?)"""',
    }

    # Confidence modifiers
    UNCERTAINTY_MARKERS = [
        "maybe",
        "probably",
        "perhaps",
        "might",
        "could",
        "approximately",
    ]

    def __init__(self, use_spacy: bool = True):
        """
        Initialize the extractor.

        Args:
            use_spacy: Whether to use spaCy for NER (requires spacy installed)
        """
        self.use_spacy = use_spacy
        self.nlp = None

        if use_spacy:
            try:
                import spacy

                self.nlp = spacy.load("en_core_web_sm")
                logger.info("spaCy NER enabled")
            except ImportError:
                logger.warning("spaCy not installed, falling back to regex")
                self.use_spacy = False
            except OSError:
                logger.warning(
                    "spaCy model not found, run: python -m spacy download en_core_web_sm"
                )
                self.use_spacy = False

    def extract_from_file(self, path: str, content: str) -> FileCrystal:
        """
        Extract primitives from a file.

        Args:
            path: File path
            content: File content

        Returns:
            FileCrystal with extracted primitives
        """
        name = Path(path).name
        crystal = FileCrystal(path=path, name=name)
        crystal.token_count = len(content) // 4  # Rough token estimate
        crystal.content_hash = str(hash(content))[:8]

        lines = content.split("\n")
        current_class = None

        for line_num, line in enumerate(lines, 1):
            primitives = self._extract_from_line(line, line_num, path, current_class)

            for prim in primitives:
                crystal.add_primitive(prim)

                # Track current class for method detection
                if prim.ptype == PrimitiveType.CLASS.value:
                    current_class = prim.name

            # Reset class context on dedent
            if line.strip() and not line.startswith(" ") and not line.startswith("\t"):
                if not any(
                    line.strip().startswith(k)
                    for k in ["class ", "def ", "@", "#", "import", "from"]
                ):
                    current_class = None

        # Extract entities using spaCy if available
        if self.use_spacy and self.nlp:
            entities = self._extract_entities(content, path)
            for entity in entities:
                crystal.add_primitive(entity)

        logger.debug(f"Extracted {len(crystal.primitives)} primitives from {name}")
        return crystal

    def _extract_from_line(
        self,
        line: str,
        line_num: int,
        source_file: str,
        current_class: Optional[str] = None,
    ) -> List[Primitive]:
        """Extract primitives from a single line."""
        primitives = []

        for ptype, pattern in self.PATTERNS.items():
            match = re.search(pattern, line, re.MULTILINE)
            if match:
                name = match.group(1) if match.lastindex >= 1 else ""
                value = line.strip()

                # Convert function to method if inside class
                actual_type = ptype
                if ptype == PrimitiveType.FUNCTION and current_class:
                    actual_type = PrimitiveType.METHOD

                # Calculate confidence
                confidence = self._calculate_confidence(line, name)

                primitives.append(
                    Primitive(
                        ptype=actual_type.value,
                        name=name,
                        value=value,
                        source_file=source_file,
                        source_line=line_num,
                        confidence=confidence,
                        metadata={
                            "class_context": current_class,
                            "indentation": len(line) - len(line.lstrip()),
                        },
                    )
                )

        return primitives

    def _calculate_confidence(self, line: str, name: str) -> float:
        """Calculate confidence score for extraction."""
        confidence = 1.0

        # Handle None or empty name
        if not name:
            return 0.9  # Default confidence for unnamed extractions

        # Lower confidence for lines with uncertainty markers
        line_lower = line.lower()
        for marker in self.UNCERTAINTY_MARKERS:
            if marker in line_lower:
                confidence *= 0.8

        # Lower confidence for dynamic constructs
        if "eval(" in line or "exec(" in line:
            confidence *= 0.7

        # Lower confidence for very short names (likely temp vars)
        if len(name) <= 2:
            confidence *= 0.8

        return min(confidence, 1.0)

    def _extract_entities(
        self,
        content: str,
        source_file: str,
    ) -> List[Primitive]:
        """
        Extract named entities using spaCy.

        Extracts:
        - PERSON, ORG, GPE (locations)
        - Technical entities from docstrings
        """
        if not self.nlp:
            return []

        entities = []
        doc = self.nlp(content)

        for ent in doc.ents:
            # Map spaCy labels to our types
            if ent.label_ in ("PERSON", "ORG", "GPE", "PRODUCT"):
                entities.append(
                    Primitive(
                        ptype="ENTITY",
                        name=ent.text,
                        value=f"{ent.label_}: {ent.text}",
                        source_file=source_file,
                        source_line=content[: ent.start_char].count("\n") + 1,
                        confidence=0.85,
                        metadata={
                            "entity_type": ent.label_,
                            "start": ent.start_char,
                            "end": ent.end_char,
                        },
                    )
                )

        return entities

    def extract_relations(self, crystal: FileCrystal) -> List[Primitive]:
        """
        Extract relations between primitives in a crystal.

        Returns relations like:
        - CLASS uses FUNCTION
        - FUNCTION calls FUNCTION
        - CLASS inherits CLASS
        """
        relations = []

        # Get all class and function names
        classes = {p.name for p in crystal.primitives if p.ptype == "CLASS"}
        functions = {
            p.name for p in crystal.primitives if p.ptype in ("FUNCTION", "METHOD")
        }

        for prim in crystal.primitives:
            # Check for inheritance
            if prim.ptype == "CLASS":
                inherit_match = re.search(r"class\s+\w+\s*\(([^)]+)\)", prim.value)
                if inherit_match:
                    parents = [p.strip() for p in inherit_match.group(1).split(",")]
                    for parent in parents:
                        relations.append(
                            Primitive(
                                ptype=PrimitiveType.RELATION.value,
                                name=f"{prim.name}_inherits_{parent}",
                                value=f"{prim.name} inherits {parent}",
                                source_file=prim.source_file,
                                source_line=prim.source_line,
                                metadata={
                                    "from": prim.name,
                                    "to": parent,
                                    "type": "inherits",
                                },
                            )
                        )

            # Check for function calls
            if prim.ptype in ("FUNCTION", "METHOD"):
                for func_name in functions:
                    if func_name != prim.name and f"{func_name}(" in prim.value:
                        relations.append(
                            Primitive(
                                ptype=PrimitiveType.RELATION.value,
                                name=f"{prim.name}_calls_{func_name}",
                                value=f"{prim.name} calls {func_name}",
                                source_file=prim.source_file,
                                source_line=prim.source_line,
                                metadata={
                                    "from": prim.name,
                                    "to": func_name,
                                    "type": "calls",
                                },
                            )
                        )

        return relations

    def summarize(self, crystal: FileCrystal) -> str:
        """
        Generate a summary of the crystal.

        Returns a compressed text representation.
        """
        classes = [p for p in crystal.primitives if p.ptype == "CLASS"]
        functions = [p for p in crystal.primitives if p.ptype == "FUNCTION"]
        methods = [p for p in crystal.primitives if p.ptype == "METHOD"]
        imports = [p for p in crystal.primitives if p.ptype == "IMPORT"]

        lines = [f"# File: {crystal.name}"]

        if imports:
            lines.append(f"Imports: {', '.join(p.name for p in imports[:5])}")

        if classes:
            lines.append(f"Classes: {', '.join(p.name for p in classes)}")

        if functions:
            lines.append(f"Functions: {', '.join(p.name for p in functions[:10])}")

        if methods:
            lines.append(f"Methods: {len(methods)}")

        return "\n".join(lines)
