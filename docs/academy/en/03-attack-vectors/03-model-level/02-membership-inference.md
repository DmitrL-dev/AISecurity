# Membership Inference Attacks

> **Lesson:** 03.3.2 - Membership Inference  
> **Time:** 30 minutes  
> **Prerequisites:** Data Extraction basics

---

## Learning Objectives

By the end of this lesson, you will be able to:

1. Understand how membership inference works
2. Assess privacy risks in model deployment
3. Implement detection techniques
4. Apply mitigation strategies

---

## What is Membership Inference?

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
        
        # Get model's response characteristics
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
    
    def _calculate_entropy(self, logits: np.ndarray) -> float:
        """Calculate entropy of output distribution."""
        probs = np.exp(logits) / np.sum(np.exp(logits), axis=-1, keepdims=True)
        return -np.sum(probs * np.log(probs + 1e-10), axis=-1).mean()
    
    def infer_membership(
        self, 
        sample: str, 
        method: str = "threshold"
    ) -> Tuple[bool, float]:
        """Infer whether sample was in training data."""
        
        features = self.get_confidence_features(sample)
        
        if method == "threshold":
            # Simple threshold on perplexity
            is_member = features["perplexity"] < self.perplexity_threshold
            confidence = 1.0 - (features["perplexity"] / 1000)
            
        elif method == "shadow":
            # Use shadow model classifier
            feature_vector = self._to_vector(features)
            is_member, confidence = self.shadow_classifier.predict(feature_vector)
            
        elif method == "likelihood_ratio":
            # Compare to reference distribution
            ratio = self._likelihood_ratio(features)
            is_member = ratio > 1.0
            confidence = min(ratio / 2, 1.0)
        
        return is_member, max(0, min(confidence, 1))
    
    def _likelihood_ratio(self, features: dict) -> float:
        """Calculate likelihood ratio for membership."""
        # P(features | member) / P(features | non-member)
        # Estimated from shadow models
        
        member_likelihood = self._fit_member_distribution(features)
        nonmember_likelihood = self._fit_nonmember_distribution(features)
        
        return member_likelihood / (nonmember_likelihood + 1e-10)
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
        self.membership_classifier = None
    
    def create_training_sets(
        self, 
        available_data: list, 
        samples_per_shadow: int
    ) -> list:
        """Create disjoint training sets for shadow models."""
        import random
        
        training_sets = []
        for i in range(self.num_shadows):
            # Random sample (some data is "in", some is "out")
            shadow_train = random.sample(available_data, samples_per_shadow)
            shadow_out = [d for d in available_data if d not in shadow_train]
            
            training_sets.append({
                "train": shadow_train,
                "out": shadow_out[:samples_per_shadow]  # Equal size
            })
        
        return training_sets
    
    def train_shadows(self, training_sets: list):
        """Train shadow models."""
        for i, dataset in enumerate(training_sets):
            shadow = self._create_model()
            shadow.train(dataset["train"])
            self.shadows.append({
                "model": shadow,
                "train_set": set(dataset["train"]),
                "out_set": set(dataset["out"])
            })
    
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
    
    def _extract_features(self, model, sample: str) -> list:
        """Extract prediction features for a sample."""
        response = model.generate(sample, return_logits=True)
        
        return [
            response.perplexity,
            np.mean(response.logprobs),
            np.std(response.logprobs),
            np.min(response.logprobs),
            self._entropy(response.logits)
        ]
```

---

## Detection of Membership Inference Attempts

```python
class MembershipInferenceDetector:
    """Detect potential membership inference attacks."""
    
    def __init__(self):
        self.query_history = []
        self.suspicious_patterns = []
    
    def analyze_query(self, query: str, response_meta: dict) -> dict:
        """Analyze query for membership inference patterns."""
        
        indicators = []
        
        # 1. Exact text queries (trying to get perplexity)
        if self._is_exact_text_query(query):
            indicators.append("exact_text_query")
        
        # 2. Repeated similar queries
        similar_past = self._find_similar_queries(query)
        if len(similar_past) > 3:
            indicators.append("repeated_similar_queries")
        
        # 3. Queries asking for confidence/probability
        if self._asks_for_confidence(query):
            indicators.append("confidence_request")
        
        # 4. Systematic probing pattern
        if self._is_systematic_probe(query):
            indicators.append("systematic_probing")
        
        risk_score = len(indicators) / 4.0
        
        self.query_history.append({
            "query": query[:100],  # Truncate for storage
            "timestamp": datetime.now(),
            "indicators": indicators
        })
        
        return {
            "is_suspicious": risk_score > 0.25,
            "risk_score": risk_score,
            "indicators": indicators
        }
    
    def _is_exact_text_query(self, query: str) -> bool:
        """Check if query appears to be exact training sample probe."""
        # Very specific, unusual formatting
        # Contains quotes suggesting exact text
        import re
        return bool(re.search(r'^["\'].*["\']$', query.strip()))
    
    def _asks_for_confidence(self, query: str) -> bool:
        """Check if query asks for model confidence."""
        confidence_keywords = [
            "confidence", "probability", "likelihood", "certain",
            "how sure", "perplexity", "logprob"
        ]
        return any(kw in query.lower() for kw in confidence_keywords)
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
        
        # Get raw logits
        logits = self.model.get_logits(prompt)
        
        # Add Laplacian noise for DP
        noise = np.random.laplace(0, 1/self.epsilon, logits.shape)
        noised_logits = logits + noise
        
        # Sample from noised distribution
        return self._sample_from_logits(noised_logits)
```

### 2. Confidence Masking

```python
def mask_confidence(response: dict, threshold: float = 0.9) -> dict:
    """Mask high-confidence signals that leak membership."""
    
    masked = response.copy()
    
    # Don't return exact probabilities
    if "top_p" in masked:
        masked["top_p"] = "high" if masked["top_p"] > threshold else "normal"
    
    # Add noise to perplexity
    if "perplexity" in masked:
        noise = np.random.uniform(-0.1, 0.1) * masked["perplexity"]
        masked["perplexity"] = round(masked["perplexity"] + noise, 1)
    
    return masked
```

### 3. SENTINEL Integration

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

## Key Takeaways

1. **Models leak training data membership** through confidence
2. **Shadow models** calibrate attack accuracy
3. **Differential privacy** is the strongest defense
4. **Mask confidence** signals in production
5. **Monitor for systematic probing**

---

*AI Security Academy | Lesson 03.3.2*
