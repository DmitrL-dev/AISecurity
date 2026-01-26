# Membership Inference Attacks

> **Урок:** 03.3.2 - Membership Inference  
> **Время:** 30 минут  
> **Prerequisites:** Data Extraction basics

---

## Цели обучения

После завершения этого урока вы сможете:

1. Понять how membership inference works
2. Assess privacy risks в model deployment
3. Реализовать detection techniques
4. Применять mitigation strategies

---

## Что такое Membership Inference?

Membership inference attacks determine whether a specific data sample was used in model training:

| Question | Privacy Concern |
|----------|-----------------|
| "Was my medical record used?" | Healthcare privacy |
| "Was my email in training?" | Personal data exposure |
| "Was this document used?" | Intellectual property |

---

## How It Works

### The Attack Principle

```
Training Data → Model learns patterns
               ↓
Model behaves differently on:
- Training samples (high confidence, low loss)
- Non-training samples (lower confidence, higher loss)
               ↓
Attacker exploits this difference to infer membership
```

### Attack Implementation

```python
import numpy as np
from typing import Tuple

class MembershipInferenceAttack:
    """Perform membership inference attack on LLM."""
    
    def __init__(self, target_model, shadow_models: list = None):
        self.target = target_model
        self.shadows = shadow_models or []
    
    def get_confidence_features(self, text: str) -> dict:
        """Extract features useful for membership inference."""
        
        response = self.target.generate(
            text, 
            return_logits=True,
            return_perplexity=True
        )
        
        return {
            "perplexity": response.perplexity,
            "avg_token_logprob": np.mean(response.logprobs),
            "min_token_logprob": np.min(response.logprobs),
            "entropy": self._calculate_entropy(response.logits),
            "completion_confidence": response.top_token_probs[0]
        }
    
    def infer_membership(
        self, 
        sample: str, 
        method: str = "threshold"
    ) -> Tuple[bool, float]:
        """Infer whether sample was in training data."""
        
        features = self.get_confidence_features(sample)
        
        if method == "threshold":
            is_member = features["perplexity"] < self.perplexity_threshold
            confidence = 1.0 - (features["perplexity"] / 1000)
            
        elif method == "shadow":
            feature_vector = self._to_vector(features)
            is_member, confidence = self.shadow_classifier.predict(feature_vector)
        
        return is_member, max(0, min(confidence, 1))
```

---

## Shadow Model Training

```python
class ShadowModelTrainer:
    """Train shadow models to calibrate membership inference."""
    
    def __init__(self, model_architecture, num_shadows: int = 5):
        self.architecture = model_architecture
        self.num_shadows = num_shadows
        self.shadows = []
    
    def create_training_sets(
        self, 
        available_data: list, 
        samples_per_shadow: int
    ) -> list:
        """Create disjoint training sets for shadow models."""
        import random
        
        training_sets = []
        for i in range(self.num_shadows):
            shadow_train = random.sample(available_data, samples_per_shadow)
            shadow_out = [d for d in available_data if d not in shadow_train]
            
            training_sets.append({
                "train": shadow_train,
                "out": shadow_out[:samples_per_shadow]
            })
        
        return training_sets
    
    def train_attack_classifier(self):
        """Train classifier to predict membership from features."""
        from sklearn.ensemble import RandomForestClassifier
        
        X, y = [], []
        
        for shadow_data in self.shadows:
            shadow = shadow_data["model"]
            
            # Features for "in" samples
            for sample in shadow_data["train_set"]:
                features = self._extract_features(shadow, sample)
                X.append(features)
                y.append(1)  # Member
            
            # Features for "out" samples
            for sample in shadow_data["out_set"]:
                features = self._extract_features(shadow, sample)
                X.append(features)
                y.append(0)  # Non-member
        
        self.membership_classifier = RandomForestClassifier(n_estimators=100)
        self.membership_classifier.fit(X, y)
```

---

## Detection of Membership Inference Attempts

```python
class MembershipInferenceDetector:
    """Detect potential membership inference attacks."""
    
    def __init__(self):
        self.query_history = []
    
    def analyze_query(self, query: str, response_meta: dict) -> dict:
        """Analyze query for membership inference patterns."""
        
        indicators = []
        
        # 1. Exact text queries
        if self._is_exact_text_query(query):
            indicators.append("exact_text_query")
        
        # 2. Repeated similar queries
        similar_past = self._find_similar_queries(query)
        if len(similar_past) > 3:
            indicators.append("repeated_similar_queries")
        
        # 3. Queries asking for confidence
        if self._asks_for_confidence(query):
            indicators.append("confidence_request")
        
        risk_score = len(indicators) / 4.0
        
        return {
            "is_suspicious": risk_score > 0.25,
            "risk_score": risk_score,
            "indicators": indicators
        }
```

---

## Mitigation Strategies

### 1. Differential Privacy

```python
class DPModelWrapper:
    """Wrapper adding differential privacy to model outputs."""
    
    def __init__(self, model, epsilon: float = 1.0):
        self.model = model
        self.epsilon = epsilon
    
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate with DP noise on output probabilities."""
        
        logits = self.model.get_logits(prompt)
        noise = np.random.laplace(0, 1/self.epsilon, logits.shape)
        noised_logits = logits + noise
        
        return self._sample_from_logits(noised_logits)
```

### 2. Confidence Masking

```python
def mask_confidence(response: dict, threshold: float = 0.9) -> dict:
    """Mask high-confidence signals that leak membership."""
    
    masked = response.copy()
    
    if "top_p" in masked:
        masked["top_p"] = "high" if masked["top_p"] > threshold else "normal"
    
    if "perplexity" in masked:
        noise = np.random.uniform(-0.1, 0.1) * masked["perplexity"]
        masked["perplexity"] = round(masked["perplexity"] + noise, 1)
    
    return masked
```

---

## SENTINEL Integration

```python
from sentinel import configure, scan

configure(
    membership_inference_protection=True,
    confidence_masking=True,
    query_pattern_detection=True
)

result = scan(
    query,
    detect_membership_inference=True
)

if result.membership_inference_detected:
    return masked_response(response)
```

---

## Ключевые выводы

1. **Models leak training data membership** через confidence
2. **Shadow models** calibrate attack accuracy
3. **Differential privacy** is the strongest defense
4. **Mask confidence** signals in production
5. **Monitor for systematic probing**

---

*AI Security Academy | Урок 03.3.2*
