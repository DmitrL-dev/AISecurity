# Tokenization и Embeddings

> **Урок:** 01.3.1 - Tokenization and Embeddings  
> **Время:** 35 минут  
> **Пререквизиты:** ML basics

---

## Цели обучения

К концу этого урока вы сможете:

1. Понимать tokenization algorithms
2. Объяснять embedding representations
3. Идентифицировать tokenization-related vulnerabilities
4. Применять embedding security techniques

---

## Tokenization Fundamentals

Tokenization конвертирует text в numerical tokens:

```python
from transformers import AutoTokenizer

tokenizer = AutoTokenizer.from_pretrained("gpt2")

text = "Hello, world!"
tokens = tokenizer.encode(text)
# [15496, 11, 995, 0]  # Token IDs

decoded = [tokenizer.decode([t]) for t in tokens]
# ['Hello', ',', 'world', '!']
```

| Algorithm | Description | Used By |
|-----------|-------------|---------|
| **BPE** | Byte-Pair Encoding | GPT-2, GPT-3/4 |
| **WordPiece** | Word-level + subwords | BERT |
| **SentencePiece** | Unigram-based | T5, LLaMA |

---

## Security Implications of Tokenization

### 1. Token Boundary Attacks

```python
class TokenBoundaryAttack:
    """Exploit token boundaries для evasion."""
    
    def __init__(self, tokenizer):
        self.tokenizer = tokenizer
    
    def find_split_evasions(self, keyword: str) -> list:
        """Найти spellings которые split keyword на different tokens."""
        
        original_tokens = self.tokenizer.encode(keyword)
        evasions = []
        
        # Try space insertion
        for i in range(1, len(keyword)):
            variant = keyword[:i] + " " + keyword[i:]
            new_tokens = self.tokenizer.encode(variant)
            
            if new_tokens != original_tokens:
                evasions.append({
                    "variant": variant,
                    "original_tokens": original_tokens,
                    "new_tokens": new_tokens
                })
        
        return evasions
    
    def homoglyph_evasion(self, keyword: str) -> list:
        """Использовать similar-looking characters чтобы change tokenization."""
        
        homoglyphs = {'a': 'а', 'e': 'е', 'o': 'о', 'c': 'с'}
        
        original_tokens = self.tokenizer.encode(keyword)
        evasions = []
        
        for i, char in enumerate(keyword):
            if char.lower() in homoglyphs:
                variant = keyword[:i] + homoglyphs[char.lower()] + keyword[i+1:]
                new_tokens = self.tokenizer.encode(variant)
                
                if new_tokens != original_tokens:
                    evasions.append({
                        "variant": variant,
                        "substituted": char,
                        "with": homoglyphs[char.lower()]
                    })
        
        return evasions
```

### 2. Glitch Tokens

```python
# Некоторые tokenizers имеют "glitch tokens" с unusual behavior
known_glitch_tokens = {
    "gpt2": [
        " SolidGoldMagikarp",  # Known anomaly token
        " petertodd",          # Another example
    ]
}

def detect_glitch_tokens(tokenizer, model) -> list:
    """Detect tokens с anomalous embeddings."""
    
    anomalies = []
    
    for token_id in range(min(50000, len(tokenizer))):
        embedding = model.get_input_embeddings()(torch.tensor([token_id]))
        norm = torch.norm(embedding).item()
        
        # Extremely high или low norms suspicious
        if norm > 100 or norm < 0.001:
            anomalies.append({
                "token_id": token_id,
                "text": tokenizer.decode([token_id]),
                "embedding_norm": norm
            })
    
    return anomalies
```

---

## Embedding Security

### 1. Semantic Understanding

```python
import numpy as np

class EmbeddingSecurityAnalyzer:
    """Analyze embeddings для security applications."""
    
    def __init__(self, embedding_model):
        self.model = embedding_model
    
    def semantic_similarity(self, text1: str, text2: str) -> float:
        """Compute semantic similarity."""
        
        emb1 = self.model.encode(text1)
        emb2 = self.model.encode(text2)
        
        return np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
    
    def detect_semantic_attack(
        self, 
        input_text: str,
        attack_references: list,
        threshold: float = 0.75
    ) -> dict:
        """Detect attack через embedding similarity."""
        
        input_emb = self.model.encode(input_text)
        
        for ref in attack_references:
            ref_emb = self.model.encode(ref)
            similarity = np.dot(input_emb, ref_emb) / (
                np.linalg.norm(input_emb) * np.linalg.norm(ref_emb)
            )
            
            if similarity > threshold:
                return {
                    "is_attack": True,
                    "matched_reference": ref,
                    "similarity": similarity
                }
        
        return {"is_attack": False}
```

### 2. Embedding Anomaly Detection

```python
class EmbeddingAnomalyDetector:
    """Detect anomalous inputs через embeddings."""
    
    def __init__(self, embedding_model):
        self.model = embedding_model
        self.baseline = None
        self.threshold = None
    
    def fit(self, normal_samples: list):
        """Fit на normal samples."""
        
        embeddings = [self.model.encode(s) for s in normal_samples]
        self.baseline = np.mean(embeddings, axis=0)
        
        distances = [np.linalg.norm(e - self.baseline) for e in embeddings]
        self.threshold = np.percentile(distances, 95)
    
    def detect(self, text: str) -> dict:
        """Detect anomaly."""
        
        embedding = self.model.encode(text)
        distance = np.linalg.norm(embedding - self.baseline)
        
        return {
            "is_anomaly": distance > self.threshold,
            "distance": distance,
            "threshold": self.threshold
        }
```

### 3. Adversarial Embedding Defense

```python
class EmbeddingDefense:
    """Defend против embedding-level attacks."""
    
    def __init__(self, embedding_model):
        self.model = embedding_model
    
    def robust_similarity(
        self, 
        text1: str, 
        text2: str, 
        n_augments: int = 5
    ) -> float:
        """Robust similarity через augmentation."""
        
        augments1 = self._augment(text1, n_augments)
        augments2 = self._augment(text2, n_augments)
        
        similarities = []
        for a1 in augments1:
            for a2 in augments2:
                emb1 = self.model.encode(a1)
                emb2 = self.model.encode(a2)
                sim = np.dot(emb1, emb2) / (
                    np.linalg.norm(emb1) * np.linalg.norm(emb2)
                )
                similarities.append(sim)
        
        # Использовать median для robustness
        return np.median(similarities)
    
    def _augment(self, text: str, n: int) -> list:
        """Simple text augmentations."""
        
        augments = [text]
        
        # Lowercase
        augments.append(text.lower())
        
        # Remove extra spaces
        augments.append(' '.join(text.split()))
        
        # Truncation
        words = text.split()
        if len(words) > 3:
            augments.append(' '.join(words[:-1]))
            augments.append(' '.join(words[1:]))
        
        return augments[:n]
```

---

## Token-Aware Detection

```python
class TokenAwareDetector:
    """Detection который accounts for tokenization."""
    
    def __init__(self, tokenizer, keywords: list):
        self.tokenizer = tokenizer
        
        # Pre-compute все token variants
        self.keyword_tokens = {}
        for keyword in keywords:
            self.keyword_tokens[keyword] = self._get_token_variants(keyword)
    
    def _get_token_variants(self, keyword: str) -> set:
        """Get все token representations keyword."""
        
        variants = set()
        
        # Plain
        variants.add(tuple(self.tokenizer.encode(keyword)))
        
        # With leading space
        variants.add(tuple(self.tokenizer.encode(" " + keyword)))
        
        # Case variants
        variants.add(tuple(self.tokenizer.encode(keyword.lower())))
        variants.add(tuple(self.tokenizer.encode(keyword.upper())))
        variants.add(tuple(self.tokenizer.encode(keyword.capitalize())))
        
        return variants
    
    def detect(self, text: str) -> dict:
        """Detect keywords accounting for tokenization."""
        
        text_tokens = tuple(self.tokenizer.encode(text))
        
        found = []
        for keyword, token_variants in self.keyword_tokens.items():
            for variant in token_variants:
                if self._subsequence_in(variant, text_tokens):
                    found.append(keyword)
                    break
        
        return {
            "found_keywords": found,
            "is_suspicious": len(found) > 0
        }
    
    def _subsequence_in(self, subseq: tuple, seq: tuple) -> bool:
        """Check если subsequence в sequence."""
        n, m = len(seq), len(subseq)
        for i in range(n - m + 1):
            if seq[i:i+m] == subseq:
                return True
        return False
```

---

## Интеграция с SENTINEL

```python
from sentinel import configure, TokenGuard, EmbeddingGuard

configure(
    tokenization_protection=True,
    embedding_detection=True
)

token_guard = TokenGuard(
    normalize_homoglyphs=True,
    detect_glitch_tokens=True
)

embedding_guard = EmbeddingGuard(
    embedding_model="all-MiniLM-L6-v2",
    anomaly_detection=True
)

@token_guard.protect
@embedding_guard.protect
def process_input(text: str):
    # Protected на обоих token и embedding level
    return llm.generate(text)
```

---

## Ключевые выводы

1. **Tokenization affects detection** — Одно слово, разные tokens
2. **Homoglyphs evade filters** — Normalize before matching
3. **Embeddings capture meaning** — Semantic attack detection
4. **Glitch tokens exist** — Monitor for anomalies
5. **Layer your defenses** — Token + embedding + pattern

---

*AI Security Academy | Урок 01.3.1*
