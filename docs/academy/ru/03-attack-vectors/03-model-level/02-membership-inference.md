# Атаки на членство в обучающих данных

> **Урок:** 03.3.2 - Атаки членства  
> **Время:** 30 минут  
> **Пререквизиты:** Основы извлечения данных

---

## Цели обучения

К концу этого урока вы сможете:

1. Понимать как работают атаки на членство
2. Оценивать риски приватности при деплое модели
3. Реализовывать техники обнаружения
4. Применять стратегии митигации

---

## Что такое атаки на членство?

Атаки на членство определяют, был ли конкретный образец данных использован при обучении модели:

| Вопрос | Риск приватности |
|--------|------------------|
| "Была ли моя медкарта использована?" | Приватность здравоохранения |
| "Был ли мой email в обучении?" | Раскрытие персональных данных |
| "Был ли этот документ использован?" | Интеллектуальная собственность |

---

## Как это работает

### Принцип атаки

```
Обучающие данные → Модель изучает паттерны
               ↓
Модель ведёт себя по-разному на:
- Обучающих образцах (высокая уверенность, низкий loss)
- Необучающих образцах (ниже уверенность, выше loss)
               ↓
Атакующий эксплуатирует эту разницу для определения членства
```

### Реализация атаки

```python
import numpy as np
from typing import Tuple

class MembershipInferenceAttack:
    """Выполнение атаки на членство для LLM."""
    
    def __init__(self, target_model, shadow_models: list = None):
        self.target = target_model
        self.shadows = shadow_models or []
    
    def get_confidence_features(self, text: str) -> dict:
        """Извлечение признаков для атаки членства."""
        
        # Получаем характеристики ответа модели
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
        """Расчёт энтропии распределения вывода."""
        probs = np.exp(logits) / np.sum(np.exp(logits), axis=-1, keepdims=True)
        return -np.sum(probs * np.log(probs + 1e-10), axis=-1).mean()
    
    def infer_membership(
        self, 
        sample: str, 
        method: str = "threshold"
    ) -> Tuple[bool, float]:
        """Определить, был ли образец в обучающих данных."""
        
        features = self.get_confidence_features(sample)
        
        if method == "threshold":
            # Простой порог на перплексию
            is_member = features["perplexity"] < self.perplexity_threshold
            confidence = 1.0 - (features["perplexity"] / 1000)
            
        elif method == "shadow":
            # Использование классификатора теневых моделей
            feature_vector = self._to_vector(features)
            is_member, confidence = self.shadow_classifier.predict(feature_vector)
            
        elif method == "likelihood_ratio":
            # Сравнение с эталонным распределением
            ratio = self._likelihood_ratio(features)
            is_member = ratio > 1.0
            confidence = min(ratio / 2, 1.0)
        
        return is_member, max(0, min(confidence, 1))
    
    def _likelihood_ratio(self, features: dict) -> float:
        """Расчёт отношения правдоподобия для членства."""
        # P(features | member) / P(features | non-member)
        # Оценивается по теневым моделям
        
        member_likelihood = self._fit_member_distribution(features)
        nonmember_likelihood = self._fit_nonmember_distribution(features)
        
        return member_likelihood / (nonmember_likelihood + 1e-10)
```

---

## Обучение теневых моделей

```python
class ShadowModelTrainer:
    """Обучение теневых моделей для калибровки атаки членства."""
    
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
        """Создание непересекающихся обучающих наборов для теневых моделей."""
        import random
        
        training_sets = []
        for i in range(self.num_shadows):
            # Случайная выборка (часть данных "внутри", часть "снаружи")
            shadow_train = random.sample(available_data, samples_per_shadow)
            shadow_out = [d for d in available_data if d not in shadow_train]
            
            training_sets.append({
                "train": shadow_train,
                "out": shadow_out[:samples_per_shadow]  # Равный размер
            })
        
        return training_sets
    
    def train_shadows(self, training_sets: list):
        """Обучение теневых моделей."""
        for i, dataset in enumerate(training_sets):
            shadow = self._create_model()
            shadow.train(dataset["train"])
            self.shadows.append({
                "model": shadow,
                "train_set": set(dataset["train"]),
                "out_set": set(dataset["out"])
            })
    
    def train_attack_classifier(self):
        """Обучение классификатора для предсказания членства по признакам."""
        from sklearn.ensemble import RandomForestClassifier
        
        X, y = [], []
        
        for shadow_data in self.shadows:
            shadow = shadow_data["model"]
            
            # Признаки для образцов "внутри"
            for sample in shadow_data["train_set"]:
                features = self._extract_features(shadow, sample)
                X.append(features)
                y.append(1)  # Член
            
            # Признаки для образцов "снаружи"
            for sample in shadow_data["out_set"]:
                features = self._extract_features(shadow, sample)
                X.append(features)
                y.append(0)  # Не член
        
        self.membership_classifier = RandomForestClassifier(n_estimators=100)
        self.membership_classifier.fit(X, y)
    
    def _extract_features(self, model, sample: str) -> list:
        """Извлечение признаков предсказания для образца."""
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

## Обнаружение попыток атак на членство

```python
class MembershipInferenceDetector:
    """Обнаружение потенциальных атак на членство."""
    
    def __init__(self):
        self.query_history = []
        self.suspicious_patterns = []
    
    def analyze_query(self, query: str, response_meta: dict) -> dict:
        """Анализ запроса на паттерны атаки членства."""
        
        indicators = []
        
        # 1. Запросы точного текста (попытка получить перплексию)
        if self._is_exact_text_query(query):
            indicators.append("exact_text_query")
        
        # 2. Повторяющиеся похожие запросы
        similar_past = self._find_similar_queries(query)
        if len(similar_past) > 3:
            indicators.append("repeated_similar_queries")
        
        # 3. Запросы уверенности/вероятности
        if self._asks_for_confidence(query):
            indicators.append("confidence_request")
        
        # 4. Систематический паттерн зондирования
        if self._is_systematic_probe(query):
            indicators.append("systematic_probing")
        
        risk_score = len(indicators) / 4.0
        
        self.query_history.append({
            "query": query[:100],  # Усечение для хранения
            "timestamp": datetime.now(),
            "indicators": indicators
        })
        
        return {
            "is_suspicious": risk_score > 0.25,
            "risk_score": risk_score,
            "indicators": indicators
        }
    
    def _is_exact_text_query(self, query: str) -> bool:
        """Проверка, является ли запрос зондом точного обучающего образца."""
        import re
        return bool(re.search(r'^["\'"].*["\'"]$', query.strip()))
    
    def _asks_for_confidence(self, query: str) -> bool:
        """Проверка, спрашивает ли запрос уверенность модели."""
        confidence_keywords = [
            "уверенность", "вероятность", "правдоподобие", "уверен",
            "насколько точно", "перплексия", "logprob",
            "confidence", "probability", "likelihood"
        ]
        return any(kw in query.lower() for kw in confidence_keywords)
```

---

## Стратегии митигации

### 1. Дифференциальная приватность

```python
class DPModelWrapper:
    """Обёртка, добавляющая дифференциальную приватность к выводам модели."""
    
    def __init__(self, model, epsilon: float = 1.0):
        self.model = model
        self.epsilon = epsilon
    
    def generate(self, prompt: str, **kwargs) -> str:
        """Генерация с DP-шумом на вероятностях вывода."""
        
        # Получаем сырые логиты
        logits = self.model.get_logits(prompt)
        
        # Добавляем лапласовский шум для DP
        noise = np.random.laplace(0, 1/self.epsilon, logits.shape)
        noised_logits = logits + noise
        
        # Сэмплируем из зашумлённого распределения
        return self._sample_from_logits(noised_logits)
```

### 2. Маскирование уверенности

```python
def mask_confidence(response: dict, threshold: float = 0.9) -> dict:
    """Маскирование сигналов высокой уверенности, утекающих членство."""
    
    masked = response.copy()
    
    # Не возвращаем точные вероятности
    if "top_p" in masked:
        masked["top_p"] = "high" if masked["top_p"] > threshold else "normal"
    
    # Добавляем шум к перплексии
    if "perplexity" in masked:
        noise = np.random.uniform(-0.1, 0.1) * masked["perplexity"]
        masked["perplexity"] = round(masked["perplexity"] + noise, 1)
    
    return masked
```

### 3. Интеграция с SENTINEL

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

1. **Модели утекают членство обучающих данных** через уверенность
2. **Теневые модели** калибруют точность атаки
3. **Дифференциальная приватность** — самая сильная защита
4. **Маскируйте сигналы уверенности** в продакшене
5. **Мониторьте систематическое зондирование**

---

*AI Security Academy | Урок 03.3.2*
