# 🔬 Урок 4.2: Engine Development

> **Время: 50 минут** | Expert Module 4 — Contribution

---

## Full Engine Lifecycle

```
Research → Design → Implement → Test → Review → Deploy → Monitor
```

---

## Step 1: Research

```markdown
## Engine Proposal: [Name]

### Attack Vector
- Paper/source: [link]
- Attack description: ...
- Real-world impact: ...

### Detection Approach
- Method: Pattern / ML / Hybrid
- Key indicators: ...
- Expected FP rate: <X%

### OWASP Mapping
- LLM: [LLM01, LLM02, ...]
- ASI: [ASI01, ASI03, ...]
```

---

## Step 2: Design

```python
# Design doc pseudo-code
"""
Engine: ExampleAttackDetector

Input: text (str)
Output: ScanResult

Algorithm:
1. Preprocess text (lowercase, normalize)
2. Extract features (patterns, embeddings)
3. Apply detection logic
4. Return threat assessment

Complexity: O(n) where n = text length
Memory: ~100MB for model
Latency target: <50ms
"""
```

---

## Step 3: Implement

```python
# src/brain/engines/example_attack_detector.py
"""
Example Attack Detector

Detects [attack name] attacks based on [paper reference].
Implements detection via [approach].

Author: [Your Name]
Date: [Date]
OWASP: LLM01, ASI01
"""

from sentinel.engine import BaseEngine, ScanResult
from typing import List
import re

class ExampleAttackDetector(BaseEngine):
    """Detect example attacks."""
    
    name = "example_attack_detector"
    category = "injection"
    tier = 2  # 1=fast, 2=medium, 3=slow
    owasp = ["LLM01", "ASI01"]
    mitre = ["T1059"]
    
    # Configuration
    PATTERNS: List[str] = [
        r"pattern_one",
        r"pattern_two",
    ]
    
    THRESHOLD = 0.75
    
    def __init__(self):
        super().__init__()
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Pre-compile regex patterns."""
        self._compiled = [
            re.compile(p, re.IGNORECASE)
            for p in self.PATTERNS
        ]
    
    def scan(self, text: str) -> ScanResult:
        """Scan text for threats.
        
        Args:
            text: Input text to analyze
            
        Returns:
            ScanResult with threat assessment
        """
        matches = []
        
        for pattern in self._compiled:
            match = pattern.search(text)
            if match:
                matches.append(match.group())
        
        if matches:
            confidence = min(len(matches) * 0.3, 1.0)
            return ScanResult(
                is_threat=True,
                confidence=confidence,
                threat_type="injection",
                matched_patterns=matches,
                engine=self.name
            )
        
        return ScanResult(
            is_threat=False,
            confidence=0.0,
            engine=self.name
        )
```

---

## Step 4: Test

```python
# tests/test_example_attack_detector.py
"""Tests for ExampleAttackDetector."""

import pytest
from src.brain.engines.example_attack_detector import ExampleAttackDetector

class TestExampleAttackDetector:
    """Test suite for ExampleAttackDetector."""
    
    @pytest.fixture
    def engine(self):
        return ExampleAttackDetector()
    
    # === Positive Tests (should detect) ===
    
    @pytest.mark.parametrize("payload", [
        "known attack payload 1",
        "known attack payload 2",
        "known attack payload 3",
    ])
    def test_detects_known_attacks(self, engine, payload):
        result = engine.scan(payload)
        assert result.is_threat, f"Should detect: {payload}"
        assert result.confidence > 0.5
    
    # === Negative Tests (should allow) ===
    
    @pytest.mark.parametrize("safe_input", [
        "Hello, how are you?",
        "Please help me with my code",
        "What is the weather today?",
    ])
    def test_allows_safe_inputs(self, engine, safe_input):
        result = engine.scan(safe_input)
        assert not result.is_threat, f"False positive: {safe_input}"
    
    # === Edge Cases ===
    
    def test_empty_input(self, engine):
        result = engine.scan("")
        assert not result.is_threat
    
    def test_unicode_input(self, engine):
        result = engine.scan("Привет мир 你好世界")
        assert not result.is_threat
    
    # === Performance ===
    
    def test_performance(self, engine, benchmark):
        result = benchmark(engine.scan, "test input " * 100)
        assert benchmark.stats["mean"] < 0.05  # <50ms
```

---

## Step 5: Submit PR

```bash
# Branch naming
git checkout -b feat/engine-example-attack

# Commit message format
git commit -m "feat(brain): add ExampleAttackDetector

- Detects [attack type] attacks
- Based on [paper reference]
- OWASP: LLM01, ASI01
- 20 unit tests, all passing

Closes #123"

# Push and create PR
git push origin feat/engine-example-attack
```

---

## Quality Checklist

- [ ] Engine follows BaseEngine interface
- [ ] Docstrings on all public methods
- [ ] Type hints complete
- [ ] >90% test coverage
- [ ] Performance within tier budget
- [ ] OWASP mapping documented
- [ ] No hardcoded secrets
- [ ] Logging uses proper levels

---

## Следующий урок

→ [4.3: Testing Standards](./16-testing-standards.md)
