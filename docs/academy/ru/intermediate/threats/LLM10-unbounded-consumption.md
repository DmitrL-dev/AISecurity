# LLM10: Неограниченное потребление

> **Урок:** 02.1.10 - Неограниченное потребление  
> **OWASP ID:** LLM10  
> **Время:** 30 минут  
> **Уровень риска:** Низкий-Средний

---

## Цели обучения

К концу этого урока вы сможете:

1. Идентифицировать паттерны атак на исчерпание ресурсов
2. Внедрять ограничение скорости и квоты
3. Проектировать cost-aware LLM-архитектуры
4. Мониторить и настраивать алерты на аномалии потребления

---

## Что такое неограниченное потребление?

Операции LLM вычислительно дороги. Неограниченное потребление возникает, когда атакующие эксплуатируют это для:

| Тип атаки | Цель | Последствия |
|-----------|------|-------------|
| **Флуд токенов** | Стоимость API | Финансовые потери |
| **Бомбардировка промптами** | Вычислительные ресурсы | Деградация сервиса |
| **Долгоработающие агенты** | Время/память | Исчерпание ресурсов |
| **Рекурсивные запросы** | API-вызовы | Взрыв стоимости |
| **Набивка контекста** | Память | OOM-краши |

---

## Паттерны атак

### 1. Взрыв стоимости токенов

```python
# Атакующий отправляет промпты, максимизирующие выходные токены
expensive_prompt = """
Напиши крайне детальный, всеобъемлющий, исчерпывающий анализ
всей истории вычислений с 1800 года до сегодняшнего дня.
Включи каждую значимую фигуру, изобретение, компанию и разработку.
Оформи как академическую статью на 50,000 слов с полными цитатами.
"""

# При $0.02 за 1K выходных токенов:
# 50,000 слов ≈ 65,000 токенов ≈ $1.30 за запрос
# 1,000 запросов/час = $1,300/час

response = llm.generate(expensive_prompt, max_tokens=65000)
```

### 2. Рекурсивный цикл агента

```python
# Вредоносный промпт вызывает бесконечный цикл агента
attack_prompt = """
Ты исследовательский ассистент. Для каждой темы, которую исследуешь:
1. Найди 3 связанные темы
2. Исследуй каждую из этих 3 тем тем же способом
3. Продолжай пока не получишь полную информацию

Тема исследования: "Всё о науке"
"""

# Без ограничений:
# Глубина 1: 3 темы
# Глубина 2: 9 тем  
# Глубина 3: 27 тем
# Глубина 4: 81 тема = 120 API-вызовов
# Глубина 10: 88,573 API-вызова!
```

### 3. Набивка контекстного окна

```python
# Атакующий заполняет контекст дорогой обработкой
context_bomb = "A" * 100000  # Заполнить контекстное окно

response = llm.generate(
    context_bomb + "\n\nСуммаризируй вышесказанное и переведи на 10 языков"
)

# Принуждает обработку огромного контекста + большой вывод
```

### 4. Пакетное усиление

```python
# Один запрос, запускающий много LLM-вызовов
amplification_prompt = """
Проанализируй каждый из этих 1000 URL и предоставь детальные отчёты:
{list_of_1000_urls}

Для каждого URL:
1. Суммаризируй контент (требует загрузки + LLM-вызов)
2. Извлеки ключевые сущности (LLM-вызов)  
3. Анализ тональности (LLM-вызов)
4. Сгенерируй action items (LLM-вызов)
"""

# 1 пользовательский запрос = 4,000+ LLM API-вызовов
```

---

## Стратегии защиты

### 1. Управление бюджетом токенов

```python
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional
import threading

@dataclass
class TokenBudget:
    user_id: str
    daily_limit: int
    hourly_limit: int
    per_request_limit: int
    used_today: int = 0
    used_this_hour: int = 0
    last_reset_daily: datetime = None
    last_reset_hourly: datetime = None

class TokenBudgetManager:
    """Управление бюджетами потребления токенов по пользователям."""
    
    def __init__(self):
        self.budgets = {}
        self.lock = threading.Lock()
    
    DEFAULT_LIMITS = {
        "free": {"daily": 10000, "hourly": 2000, "per_request": 1000},
        "pro": {"daily": 100000, "hourly": 20000, "per_request": 4000},
        "enterprise": {"daily": 1000000, "hourly": 100000, "per_request": 32000}
    }
    
    def get_budget(self, user_id: str, tier: str = "free") -> TokenBudget:
        """Получить или создать бюджет токенов для пользователя."""
        with self.lock:
            if user_id not in self.budgets:
                limits = self.DEFAULT_LIMITS.get(tier, self.DEFAULT_LIMITS["free"])
                self.budgets[user_id] = TokenBudget(
                    user_id=user_id,
                    daily_limit=limits["daily"],
                    hourly_limit=limits["hourly"],
                    per_request_limit=limits["per_request"],
                    last_reset_daily=datetime.utcnow(),
                    last_reset_hourly=datetime.utcnow()
                )
            
            budget = self.budgets[user_id]
            self._check_reset(budget)
            return budget
    
    def _check_reset(self, budget: TokenBudget):
        """Сброс счётчиков при истечении временного окна."""
        now = datetime.utcnow()
        
        if now - budget.last_reset_daily > timedelta(days=1):
            budget.used_today = 0
            budget.last_reset_daily = now
        
        if now - budget.last_reset_hourly > timedelta(hours=1):
            budget.used_this_hour = 0
            budget.last_reset_hourly = now
    
    def check_and_consume(
        self, 
        user_id: str, 
        estimated_tokens: int,
        tier: str = "free"
    ) -> dict:
        """Проверить, укладывается ли запрос в бюджет, и потребить токены."""
        budget = self.get_budget(user_id, tier)
        
        # Проверка лимита на запрос
        if estimated_tokens > budget.per_request_limit:
            return {
                "allowed": False,
                "reason": f"Запрос превышает лимит на запрос ({budget.per_request_limit})",
                "limit_type": "per_request"
            }
        
        # Проверка часового лимита
        if budget.used_this_hour + estimated_tokens > budget.hourly_limit:
            return {
                "allowed": False,
                "reason": "Часовой лимит превышен",
                "remaining": budget.hourly_limit - budget.used_this_hour
            }
        
        # Проверка дневного лимита
        if budget.used_today + estimated_tokens > budget.daily_limit:
            return {
                "allowed": False,
                "reason": "Дневной лимит превышен",
                "remaining": budget.daily_limit - budget.used_today
            }
        
        # Потребление токенов
        with self.lock:
            budget.used_this_hour += estimated_tokens
            budget.used_today += estimated_tokens
        
        return {"allowed": True, "tokens_used": estimated_tokens}
```

---

### 2. Анализ сложности запроса

```python
class RequestComplexityAnalyzer:
    """Анализ и ограничение сложности запроса перед обработкой."""
    
    def __init__(self):
        self.complexity_weights = {
            "translation": 1.5,
            "summarization": 1.2,
            "generation": 1.0,
            "analysis": 1.3,
            "code": 1.4,
        }
    
    def estimate_tokens(self, prompt: str, task_type: str = "generation") -> int:
        """Оценка потребления токенов для запроса."""
        # Входные токены
        input_tokens = len(prompt.split()) * 1.3  # Грубая оценка токенов
        
        # Оценка выхода на основе задачи
        output_multipliers = {
            "summarization": 0.3,      # Выход меньше входа
            "translation": 1.0,        # Похожий размер
            "generation": 2.0,         # Потенциально больше
            "analysis": 1.5,           # Среднее расширение
            "code": 2.5,              # Код многословен
        }
        
        output_mult = output_multipliers.get(task_type, 1.5)
        estimated_output = input_tokens * output_mult
        
        # Применение веса сложности
        weight = self.complexity_weights.get(task_type, 1.0)
        
        return int((input_tokens + estimated_output) * weight)
    
    def detect_amplification(self, prompt: str) -> dict:
        """Обнаружение промптов, способных вызвать усиление вызовов."""
        amplification_patterns = [
            (r"(?:для каждого|для всех|анализируй все|обработай каждый)\s+(?:\d+|сотни|тысячи)", "batch_amplification"),
            (r"(?:рекурсивно|повторно|продолжай пока)", "recursive_loop"),
            (r"список из \d{2,} (?:элементов|url|тем)", "large_batch"),
            (r"переведи (?:на|в) (?:\d+|все|каждый) язык", "multi_output"),
        ]
        
        import re
        findings = []
        
        for pattern, risk_type in amplification_patterns:
            if re.search(pattern, prompt, re.IGNORECASE):
                findings.append(risk_type)
        
        return {
            "has_amplification_risk": len(findings) > 0,
            "risks": findings,
            "recommendation": "Применить строгие лимиты" if findings else None
        }
```

---

### 3. Защита от циклов агентов

```python
class AgentLoopProtector:
    """Защита от неконтролируемых циклов агентов."""
    
    def __init__(self, max_iterations: int = 10, max_depth: int = 3):
        self.max_iterations = max_iterations
        self.max_depth = max_depth
        self.current_sessions = {}
    
    def start_session(self, session_id: str) -> dict:
        """Начать отслеживание новой сессии агента."""
        self.current_sessions[session_id] = {
            "iterations": 0,
            "depth": 0,
            "total_tokens": 0,
            "start_time": datetime.utcnow(),
            "calls": []
        }
        return self.current_sessions[session_id]
    
    def record_iteration(
        self, 
        session_id: str, 
        tokens_used: int,
        depth_change: int = 0
    ) -> dict:
        """Записать итерацию агента и проверить лимиты."""
        if session_id not in self.current_sessions:
            self.start_session(session_id)
        
        session = self.current_sessions[session_id]
        session["iterations"] += 1
        session["depth"] += depth_change
        session["total_tokens"] += tokens_used
        session["calls"].append({
            "time": datetime.utcnow(),
            "tokens": tokens_used
        })
        
        # Проверка лимитов
        if session["iterations"] > self.max_iterations:
            return {
                "continue": False,
                "reason": f"Превышено максимум итераций ({self.max_iterations})"
            }
        
        if session["depth"] > self.max_depth:
            return {
                "continue": False,
                "reason": f"Превышена максимальная глубина рекурсии ({self.max_depth})"
            }
        
        # Проверка на быстрые вызовы (потенциальный цикл)
        if len(session["calls"]) >= 5:
            recent = session["calls"][-5:]
            time_span = (recent[-1]["time"] - recent[0]["time"]).total_seconds()
            if time_span < 2:  # 5 вызовов за 2 секунды = подозрительно
                return {
                    "continue": False,
                    "reason": "Обнаружена быстрая итерация (потенциальный цикл)"
                }
        
        return {"continue": True}
    
    def end_session(self, session_id: str) -> dict:
        """Завершить сессию и вернуть сводку."""
        if session_id in self.current_sessions:
            session = self.current_sessions.pop(session_id)
            duration = (datetime.utcnow() - session["start_time"]).total_seconds()
            return {
                "total_iterations": session["iterations"],
                "max_depth": session["depth"],
                "total_tokens": session["total_tokens"],
                "duration_seconds": duration,
                "tokens_per_second": session["total_tokens"] / max(duration, 1)
            }
        return None
```

---

### 4. Ограничение скорости

```python
from collections import defaultdict
import time

class MultiLevelRateLimiter:
    """Многоуровневое ограничение скорости для LLM-запросов."""
    
    def __init__(self):
        self.request_times = defaultdict(list)
        self.token_counts = defaultdict(list)
    
    LIMITS = {
        "requests_per_minute": 60,
        "requests_per_hour": 1000,
        "tokens_per_minute": 40000,
        "tokens_per_hour": 500000,
    }
    
    def check_rate_limit(self, user_id: str, estimated_tokens: int) -> dict:
        """Проверить все лимиты скорости для пользователя."""
        now = time.time()
        
        # Очистка старых записей
        self._clean_old_entries(user_id, now)
        
        # Проверка частоты запросов
        requests_last_minute = len([
            t for t in self.request_times[user_id]
            if now - t < 60
        ])
        
        if requests_last_minute >= self.LIMITS["requests_per_minute"]:
            return {
                "allowed": False,
                "reason": "Превышен лимит частоты запросов",
                "retry_after": 60
            }
        
        # Проверка частоты токенов
        tokens_last_minute = sum([
            t for t, _ in self.token_counts[user_id]
            if now - _ < 60
        ])
        
        if tokens_last_minute + estimated_tokens > self.LIMITS["tokens_per_minute"]:
            return {
                "allowed": False,
                "reason": "Превышен лимит частоты токенов",
                "retry_after": 60
            }
        
        # Запись этого запроса
        self.request_times[user_id].append(now)
        self.token_counts[user_id].append((estimated_tokens, now))
        
        return {"allowed": True}
```

---

## Интеграция с SENTINEL

```python
from sentinel import configure, CostGuard

configure(
    cost_protection=True,
    rate_limiting=True,
    agent_loop_protection=True
)

cost_guard = CostGuard(
    daily_budget=100.00,  # $100/день максимум
    per_request_max=1.00,  # $1 максимум за запрос
    alert_threshold=0.8   # Алерт при 80% бюджета
)

@cost_guard.protect
def llm_request(prompt: str, user_id: str):
    # Автоматически проверяет бюджет и лимиты скорости
    return llm.generate(prompt)
```

---

## Ключевые выводы

1. **Бюджетируйте всё** — Токены, запросы, время
2. **Ограничивайте рекурсию** — Предотвращайте неконтролируемых агентов
3. **Анализируйте сложность** — До обработки
4. **Ограничивайте скорость** — На нескольких уровнях
5. **Мониторьте и алертите** — Ловите аномалии рано

---

## Практические упражнения

1. Реализовать менеджер бюджета токенов
2. Построить анализатор сложности
3. Создать защитник от циклов агентов
4. Настроить дашборд мониторинга стоимости

---

*AI Security Academy | Урок 02.1.10*
