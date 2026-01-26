# Adversarial Examples в LLM Context

> **Урок:** 03.3.3 - Adversarial Examples  
> **Время:** 45 минут  
> **Prerequisites:** Model-Level Attacks basics

---

## Цели обучения

После завершения этого урока вы сможете:

1. Понять adversarial examples в LLM context
2. Идентифицировать adversarial attack techniques
3. Реализовать detection mechanisms
4. Применять robustness improvements

---

## Что такое Adversarial Examples?

Adversarial examples — inputs deliberately crafted to cause incorrect or unintended model behavior:

| Type | Description | Example |
|------|-------------|---------|
| **Perturbations** | Small changes that flip predictions | Adding hidden characters |
| **Suffixes** | Appended strings that bypass safety | GCG attack suffixes |
| **Token Manipulation** | Exploiting tokenization | Word splitting tricks |
| **Visual Attacks** | Text rendered in images | Unicode lookalikes |

---

## LLM-Specific Adversarial Attacks

### 1. Adversarial Suffixes (GCG Attack)

The Greedy Coordinate Gradient attack finds suffixes that jailbreak models:

```python
class AdversarialSuffixGenerator:
    """Generate adversarial suffixes using gradient-based optimization."""
    
    def __init__(self, target_model, tokenizer):
        self.model = target_model
        self.tokenizer = tokenizer
        self.suffix_length = 20
    
    def generate_suffix(
        self, 
        prompt: str, 
        target_response: str = "Sure, here's",
        iterations: int = 500
    ) -> str:
        """Find adversarial suffix that elicits target response."""
        
        # Initialize random suffix
        suffix_tokens = torch.randint(
            0, len(self.tokenizer), 
            (self.suffix_length,)
        )
        
        target_tokens = self.tokenizer.encode(target_response)
        
        for iteration in range(iterations):
            full_input = prompt + self._decode_suffix(suffix_tokens)
            loss, gradients = self._compute_loss_and_grad(
                full_input, target_tokens
            )
            
            # Greedy token substitution
            for pos in range(self.suffix_length):
                best_token = self._find_best_token(
                    suffix_tokens, pos, prompt, target_tokens
                )
                suffix_tokens[pos] = best_token
            
            if loss < 0.1:  # Convergence
                break
        
        return self._decode_suffix(suffix_tokens)
```

---

### 2. Token-Level Attacks

Exploiting tokenization for evasion:

```python
class TokenizationExploits:
    """Exploit tokenizer quirks for adversarial attacks."""
    
    def __init__(self, tokenizer):
        self.tokenizer = tokenizer
    
    def split_word_attack(self, word: str) -> list:
        """Find ways to split word that evades detection."""
        # "bomb" might be detected, but "bo" + "mb" might not
        
        splits = []
        for i in range(1, len(word)):
            part1, part2 = word[:i], word[i:]
            token1 = self.tokenizer.encode(part1)
            token2 = self.tokenizer.encode(part2)
            
            splits.append({
                "split": (part1, part2),
                "tokens": (token1, token2)
            })
        
        return splits
    
    def unicode_substitution(self, text: str) -> str:
        """Substitute characters with visual lookalikes."""
        substitutions = {
            'a': 'а',  # Cyrillic
            'e': 'е',  # Cyrillic
            'o': 'о',  # Cyrillic
            'p': 'р',  # Cyrillic
        }
        
        return ''.join(substitutions.get(c, c) for c in text)
    
    def insert_zero_width(self, text: str) -> str:
        """Insert zero-width characters to break pattern matching."""
        zwsp = '\u200B'  # Zero-width space
        return zwsp.join(list(text))
```

---

### 3. Embedding Space Attacks

Finding inputs that map to similar embeddings as dangerous content:

```python
class EmbeddingSpaceAttack:
    """Find adversarial examples in embedding space."""
    
    def __init__(self, embedding_model, target_embeddings: dict):
        self.embed = embedding_model
        self.targets = target_embeddings
    
    def find_adversarial(
        self, 
        benign_text: str, 
        target_category: str,
        similarity_threshold: float = 0.9
    ) -> Tuple[str, float]:
        """Find variation of benign text that embeds near target."""
        
        target_emb = self.targets[target_category]
        current_text = benign_text
        best_similarity = 0
        
        for _ in range(100):
            current_emb = self.embed(current_text)
            similarity = self._cosine_similarity(current_emb, target_emb)
            
            if similarity > best_similarity:
                best_similarity = similarity
                best_text = current_text
            
            if similarity > similarity_threshold:
                break
            
            current_text = self._perturb_toward_target(current_text, target_emb)
        
        return best_text, best_similarity
```

---

## Detection Techniques

### Adversarial Input Detection

```python
class AdversarialDetector:
    """Detect adversarial inputs before processing."""
    
    def __init__(self):
        self.checks = [
            self._check_unusual_characters,
            self._check_tokenization_anomalies,
            self._check_perplexity_spikes,
        ]
    
    def analyze(self, text: str) -> dict:
        """Analyze text for adversarial properties."""
        results = {}
        
        for check in self.checks:
            check_name = check.__name__.replace('_check_', '')
            results[check_name] = check(text)
        
        risks = [r['risk_score'] for r in results.values()]
        overall_risk = max(risks) if risks else 0
        
        return {
            "is_adversarial": overall_risk > 0.7,
            "risk_score": overall_risk,
            "details": results
        }
    
    def _check_unusual_characters(self, text: str) -> dict:
        """Check for unicode tricks and unusual characters."""
        import unicodedata
        
        suspicious_chars = []
        for i, char in enumerate(text):
            category = unicodedata.category(char)
            
            # Zero-width characters
            if category == 'Cf':
                suspicious_chars.append((i, char, 'zero_width'))
            
            # Homoglyphs (e.g., Cyrillic lookalikes)
            if category == 'Ll' and ord(char) > 127:
                name = unicodedata.name(char, 'UNKNOWN')
                if 'LATIN' not in name and 'CYRILLIC' in name:
                    suspicious_chars.append((i, char, 'homoglyph'))
        
        return {
            "suspicious_chars": suspicious_chars,
            "risk_score": min(len(suspicious_chars) / 5, 1.0)
        }
```

---

## SENTINEL Integration

```python
from sentinel import configure, scan

configure(
    adversarial_detection=True,
    unicode_normalization=True,
    embedding_outlier_detection=True
)

result = scan(
    user_input,
    detect_adversarial=True,
    normalize_unicode=True
)

if result.adversarial_detected:
    return safe_response("Input appears unusual. Please rephrase.")
```

---

## Ключевые выводы

1. **LLMs are vulnerable** to carefully crafted inputs
2. **Suffixes can jailbreak** even aligned models
3. **Tokenization is exploitable** through unicode/splitting
4. **Detect anomalies** in character sets and perplexity
5. **Adversarial training** improves robustness

---

*AI Security Academy | Урок 03.3.3*
