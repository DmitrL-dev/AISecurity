# Tokenization and Security

> **Lesson:** 01.2.2 - Tokenization  
> **Time:** 35 minutes  
> **Prerequisites:** Attention basics

---

## Learning Objectives

By the end of this lesson, you will be able to:

1. Understand how tokenization works
2. Identify tokenization-based attack vectors
3. Exploit and defend against tokenization quirks
4. Design token-aware security measures

---

## What is Tokenization?

Tokenization converts text into numerical tokens that models can process:

```
"Hello, world!" → [15496, 11, 995, 0]
                   Hello  ,   world !
```

| Tokenizer Type | Example |
|---------------|---------|
| **BPE** | Most GPT models |
| **WordPiece** | BERT, some others |
| **SentencePiece** | Many multilingual models |
| **Unigram** | XLNet, T5 |

---

## Security Implications

### 1. Token Boundaries Enable Attacks

```python
# Word-level detection fails on split tokens
keyword = "bomb"  # Blocked as keyword

# But tokenizer may split it differently:
evasion = "b" + "omb"  # May tokenize as ["b", "omb"]
evasion2 = "bo" + "mb"  # May tokenize as ["bo", "mb"]

# Regex looking for "bomb" misses the split versions
```

### 2. Tokenization Inconsistency

```python
from transformers import AutoTokenizer

tokenizer = AutoTokenizer.from_pretrained("gpt2")

# Same word, different tokenizations based on context
print(tokenizer.encode("bomb"))      # [21901]
print(tokenizer.encode(" bomb"))     # [6202]   (with space)
print(tokenizer.encode("Bomb"))      # [33, 2381]  (capitalized)
print(tokenizer.encode("BOMB"))      # [33, 2662, 33]  (all caps)

# Detection must account for all variants!
```

---

## Token-Based Attacks

### 1. Token Splitting Evasion

```python
class TokenSplitAttack:
    """Evade keyword detection via token splitting."""
    
    def __init__(self, tokenizer):
        self.tokenizer = tokenizer
    
    def find_evasive_spellings(self, keyword: str) -> list:
        """Find spellings that avoid the keyword's token."""
        
        original_tokens = self.tokenizer.encode(keyword)
        evasions = []
        
        # Try various splitting strategies
        for i in range(1, len(keyword)):
            # Split with spaces
            split = keyword[:i] + " " + keyword[i:]
            tokens = self.tokenizer.encode(split)
            if tokens != original_tokens:
                evasions.append({
                    "variant": split,
                    "tokens": tokens,
                    "strategy": "space_split"
                })
            
            # Split with zero-width characters
            zwsp = "\u200b"
            split_zwsp = keyword[:i] + zwsp + keyword[i:]
            tokens = self.tokenizer.encode(split_zwsp)
            if tokens != original_tokens:
                evasions.append({
                    "variant": split_zwsp,
                    "tokens": tokens,
                    "strategy": "zero_width_split"
                })
        
        return evasions
    
    def find_homoglyph_evasions(self, keyword: str) -> list:
        """Find homoglyph substitutions that change tokens."""
        
        homoglyphs = {
            'a': 'а', 'e': 'е', 'o': 'о', 'p': 'р',
            'c': 'с', 'x': 'х', 'i': 'і'
        }
        
        original_tokens = self.tokenizer.encode(keyword)
        evasions = []
        
        for i, char in enumerate(keyword):
            if char.lower() in homoglyphs:
                variant = keyword[:i] + homoglyphs[char.lower()] + keyword[i+1:]
                tokens = self.tokenizer.encode(variant)
                
                if tokens != original_tokens:
                    evasions.append({
                        "variant": variant,
                        "tokens": tokens,
                        "strategy": "homoglyph"
                    })
        
        return evasions
```

---

### 2. Token Boundary Manipulation

```python
class TokenBoundaryManipulator:
    """Exploit token boundaries for attacks."""
    
    def __init__(self, tokenizer):
        self.tokenizer = tokenizer
    
    def fragment_instruction(self, instruction: str) -> str:
        """Fragment instruction across token boundaries."""
        
        # Find natural token breaks
        tokens = self.tokenizer.encode(instruction)
        decoded_tokens = [self.tokenizer.decode([t]) for t in tokens]
        
        # Insert characters that change boundaries
        fragmented = ""
        for i, token_text in enumerate(decoded_tokens):
            fragmented += token_text
            if i < len(decoded_tokens) - 1:
                # Insert boundary-breaking character
                fragmented += "\u200b"  # Zero-width space
        
        return fragmented
    
    def embed_in_tokens(self, payload: str, carrier: str) -> str:
        """Embed payload within carrier text tokens."""
        
        # Strategy: insert payload where it won't be detected
        # by token-level keyword matching
        
        carrier_tokens = self.tokenizer.encode(carrier)
        payload_tokens = self.tokenizer.encode(payload)
        
        # Find position where payload integrates smoothly
        # This is model-specific and requires experimentation
        
        return carrier + "\n\n" + payload
```

---

### 3. Glitch Tokens

```python
# Some tokenizers have "glitch tokens" - tokens that cause unusual behavior

glitch_tokens = {
    "gpt-2": [
        " petertodd",  # Known glitch token
        "SolidGoldMagikarp",  # Another example
    ]
}

class GlitchTokenExplorer:
    """Explore glitch tokens in tokenizer."""
    
    def __init__(self, tokenizer, model):
        self.tokenizer = tokenizer
        self.model = model
    
    def find_glitch_tokens(self, sample_size: int = 1000) -> list:
        """Find tokens with unusual embedding properties."""
        
        unusual = []
        
        for token_id in range(min(sample_size, len(self.tokenizer))):
            token_text = self.tokenizer.decode([token_id])
            embedding = self.model.get_input_embeddings()(
                torch.tensor([token_id])
            )
            
            # Check for unusual embedding properties
            norm = torch.norm(embedding).item()
            if norm > 100 or norm < 0.01:
                unusual.append({
                    "token_id": token_id,
                    "text": token_text,
                    "embedding_norm": norm
                })
        
        return unusual
```

---

## Defense Techniques

### 1. Token-Aware Keyword Detection

```python
class TokenAwareDetector:
    """Keyword detection that accounts for tokenization."""
    
    def __init__(self, tokenizer, keywords: list):
        self.tokenizer = tokenizer
        
        # Pre-compute all token variants of keywords
        self.keyword_token_sets = {}
        for keyword in keywords:
            self.keyword_token_sets[keyword] = self._get_all_variants(keyword)
    
    def _get_all_variants(self, keyword: str) -> set:
        """Get all token sequences for keyword variants."""
        
        variants = set()
        
        # Original
        variants.add(tuple(self.tokenizer.encode(keyword)))
        
        # With leading space
        variants.add(tuple(self.tokenizer.encode(" " + keyword)))
        
        # Capitalization variants
        variants.add(tuple(self.tokenizer.encode(keyword.lower())))
        variants.add(tuple(self.tokenizer.encode(keyword.upper())))
        variants.add(tuple(self.tokenizer.encode(keyword.capitalize())))
        
        return variants
    
    def detect(self, text: str) -> dict:
        """Detect keywords accounting for tokenization."""
        
        tokens = tuple(self.tokenizer.encode(text))
        
        found = []
        for keyword, token_variants in self.keyword_token_sets.items():
            for variant in token_variants:
                if self._contains_subsequence(tokens, variant):
                    found.append(keyword)
                    break
        
        return {
            "found_keywords": found,
            "is_suspicious": len(found) > 0
        }
    
    def _contains_subsequence(self, sequence: tuple, subseq: tuple) -> bool:
        """Check if sequence contains subsequence."""
        n, m = len(sequence), len(subseq)
        for i in range(n - m + 1):
            if sequence[i:i+m] == subseq:
                return True
        return False
```

---

### 2. Pre-Tokenization Normalization

```python
class TokenizationNormalizer:
    """Normalize text before tokenization to prevent evasion."""
    
    def __init__(self):
        # Zero-width characters to remove
        self.invisible_chars = [
            '\u200b', '\u200c', '\u200d', '\u2060', '\ufeff'
        ]
        
        # Homoglyph replacements
        self.homoglyphs = {
            'а': 'a', 'е': 'e', 'о': 'o', 'р': 'p',
            'с': 'c', 'х': 'x', 'і': 'i', 'у': 'y'
        }
    
    def normalize(self, text: str) -> str:
        """Normalize text to consistent form."""
        
        # Remove invisible characters
        for char in self.invisible_chars:
            text = text.replace(char, '')
        
        # Replace homoglyphs
        for homoglyph, replacement in self.homoglyphs.items():
            text = text.replace(homoglyph, replacement)
        
        # Normalize unicode
        import unicodedata
        text = unicodedata.normalize('NFKC', text)
        
        return text
```

---

### 3. Semantic Detection (Token-Agnostic)

```python
class SemanticDetector:
    """Detect harmful content regardless of tokenization."""
    
    def __init__(self, embedding_model, harmful_examples: list):
        self.embed = embedding_model
        
        # Pre-compute embeddings for known harmful patterns
        self.harmful_embeddings = [
            self.embed(ex) for ex in harmful_examples
        ]
    
    def detect(self, text: str, threshold: float = 0.85) -> dict:
        """Detect harmful content via semantic similarity."""
        
        text_emb = self.embed(text)
        
        max_similarity = 0
        most_similar_idx = -1
        
        for i, harmful_emb in enumerate(self.harmful_embeddings):
            sim = self._cosine_similarity(text_emb, harmful_emb)
            if sim > max_similarity:
                max_similarity = sim
                most_similar_idx = i
        
        return {
            "is_harmful": max_similarity > threshold,
            "confidence": max_similarity,
            "matched_pattern": most_similar_idx if max_similarity > threshold else None
        }
    
    def _cosine_similarity(self, a, b):
        import numpy as np
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
```

---

## SENTINEL Integration

```python
from sentinel import configure, TokenGuard

configure(
    tokenization_normalization=True,
    token_aware_detection=True,
    glitch_token_protection=True
)

token_guard = TokenGuard(
    normalize_before_detection=True,
    block_glitch_tokens=True
)

@token_guard.protect  
def process_input(text: str):
    # Automatically normalized and checked
    return llm.generate(text)
```

---

## Key Takeaways

1. **Tokenization affects detection** - Same word, different tokens
2. **Attackers exploit splits** - Bypass keyword filters
3. **Normalize before detection** - Remove invisible chars, homoglyphs
4. **Use semantic detection** - Token-agnostic is more robust
5. **Test your tokenizer** - Know its quirks

---

*AI Security Academy | Lesson 01.2.2*
