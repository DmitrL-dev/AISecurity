# Data Extraction Attacks

> **Урок:** 03.3.1 - Data Extraction  
> **Время:** 40 минут  
> **Prerequisites:** Model Architecture basics

---

## Цели обучения

После завершения этого урока вы сможете:

1. Понять как LLMs memorize и leak data
2. Идентифицировать extraction attack techniques
3. Реализовать detection mechanisms
4. Применять mitigation strategies

---

## Что такое Data Extraction?

LLMs memorize portions of training data. Attackers can extract:

| Data Type | Risk | Example |
|-----------|------|---------|
| **PII** | Privacy violation | Names, emails, phone numbers |
| **Credentials** | Security breach | API keys, passwords |
| **Code** | IP theft | Proprietary algorithms |
| **Documents** | Confidentiality | Internal communications |

---

## How LLMs Memorize Data

### Verbatim Memorization

```python
class MemorizationAnalyzer:
    """Analyze model memorization behavior."""
    
    def __init__(self, model):
        self.model = model
    
    def test_verbatim_recall(self, prefix: str, expected_continuation: str) -> dict:
        """Test if model reproduces exact training content."""
        
        # Generate continuation
        generated = self.model.generate(prefix, max_tokens=len(expected_continuation.split()) * 2)
        
        # Check for exact match
        is_verbatim = expected_continuation.lower() in generated.lower()
        
        # Check for near-match
        similarity = self._compute_similarity(generated, expected_continuation)
        
        return {
            "prefix": prefix,
            "expected": expected_continuation,
            "generated": generated,
            "is_verbatim": is_verbatim,
            "similarity": similarity,
            "memorized": is_verbatim or similarity > 0.9
        }
```

### Factors Affecting Memorization

```
High Memorization Risk:
├── Repeated content (seen many times in training)
├── Distinctive patterns (unique formatting)
├── Longer sequences (more context = better recall)
├── Specific prompts (exact prefix matching)
└── High model capacity (larger models = more memory)

Lower Memorization Risk:
├── Common phrases (many variations exist)
├── Modified content (slight variations)
└── Short sequences (less distinctive)
```

---

## Extraction Techniques

### 1. Prefix-Based Extraction

```python
class PrefixExtractAttack:
    """Extract memorized content using prefixes."""
    
    def __init__(self, model):
        self.model = model
    
    def extract_with_prefix(self, prefix: str, num_samples: int = 10) -> list:
        """Generate multiple completions to find memorized content."""
        
        extractions = []
        
        for i in range(num_samples):
            temp = 0.1 + (i * 0.1)  # 0.1 to 1.0
            
            completion = self.model.generate(
                prefix, 
                temperature=temp,
                max_tokens=200
            )
            
            extractions.append({
                "temperature": temp,
                "completion": completion,
                "contains_pii": self._check_pii(completion),
                "contains_credentials": self._check_credentials(completion)
            })
        
        return extractions
    
    def _check_pii(self, text: str) -> list:
        """Check for PII patterns."""
        import re
        
        patterns = {
            "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "phone": r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            "ssn": r'\b\d{3}-\d{2}-\d{4}\b',
        }
        
        found = []
        for pii_type, pattern in patterns.items():
            matches = re.findall(pattern, text)
            if matches:
                found.append({"type": pii_type, "matches": matches})
        
        return found
```

---

### 2. Divergence Attack

```python
class DivergenceAttack:
    """
    Exploit low-entropy completions to extract memorized data.
    
    When perplexity is very low, model is likely reproducing
    memorized content rather than generating.
    """
    
    def __init__(self, model):
        self.model = model
    
    def find_memorized_content(
        self, 
        prefixes: list, 
        perplexity_threshold: float = 5.0
    ) -> list:
        """Find content with suspiciously low perplexity."""
        
        memorized = []
        
        for prefix in prefixes:
            completion, perplexity = self.model.generate_with_perplexity(
                prefix, 
                max_tokens=100
            )
            
            if perplexity < perplexity_threshold:
                memorized.append({
                    "prefix": prefix,
                    "completion": completion,
                    "perplexity": perplexity,
                    "confidence": 1 - (perplexity / perplexity_threshold)
                })
        
        return memorized
```

---

## Detection Techniques

### Output Monitoring

```python
class DataLeakageDetector:
    """Detect data leakage in model outputs."""
    
    def __init__(self):
        self.pii_patterns = self._compile_pii_patterns()
        self.credential_patterns = self._compile_credential_patterns()
    
    def scan_output(self, text: str) -> dict:
        """Scan output for potential data leakage."""
        
        findings = {
            "pii": [],
            "credentials": [],
            "risk_score": 0
        }
        
        # Check for PII
        for pattern_name, pattern in self.pii_patterns.items():
            matches = pattern.findall(text)
            if matches:
                findings["pii"].append({
                    "type": pattern_name,
                    "count": len(matches),
                    "redacted": [self._redact(m) for m in matches]
                })
        
        # Check for credentials
        for pattern_name, pattern in self.credential_patterns.items():
            matches = pattern.findall(text)
            if matches:
                findings["credentials"].append({
                    "type": pattern_name,
                    "count": len(matches)
                })
        
        findings["risk_score"] = self._calculate_risk(findings)
        return findings
    
    def _redact(self, text: str) -> str:
        """Redact sensitive content for logging."""
        if len(text) <= 4:
            return "****"
        return text[:2] + "****" + text[-2:]
```

---

## SENTINEL Integration

```python
from sentinel import configure, scan

configure(
    data_extraction_detection=True,
    pii_filtering=True,
    credential_detection=True
)

result = scan(
    model_output,
    detect_pii=True,
    detect_credentials=True,
    detect_memorization=True
)

if result.data_leakage_detected:
    return redact(model_output, result.sensitive_spans)
```

---

## Ключевые выводы

1. **LLMs memorize training data** - Especially repeated or distinctive content
2. **Low perplexity indicates memorization** - Model is reproducing, not generating
3. **Scan all outputs** - Detect PII and credentials before returning
4. **Filter aggressively** - Better to over-redact than leak data
5. **Monitor extraction attempts** - Look for suspicious prompt patterns

---

*AI Security Academy | Урок 03.3.1*
