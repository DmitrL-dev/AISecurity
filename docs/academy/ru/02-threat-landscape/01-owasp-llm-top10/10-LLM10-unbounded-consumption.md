# LLM10: Unbounded Consumption

> **Уровень:** �������  
> **Время:** 35 минут  
> **Трек:** 02 — Threat Landscape  
> **Модуль:** 02.1 — OWASP LLM Top 10  
> **Версия:** 1.0

---

## Цели обучения

- [ ] Понять риски неограниченного потребления ресурсов
- [ ] Изучить атаки Denial of Service на LLM
- [ ] Освоить методы rate limiting и resource control
- [ ] Интегрировать защиту в SENTINEL

---

## 1. Обзор Проблемы

### 1.1 Что такое Unbounded Consumption?

```
┌────────────────────────────────────────────────────────────────────┐
│              UNBOUNDED CONSUMPTION ATTACKS                         │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ATTACK VECTORS:                                                   │
│  ├── Token Flooding: Огромные inputs → high compute cost          │
│  ├── Context Exhaustion: Заполнение context window               │
│  ├── Response Amplification: Small input → huge output           │
│  ├── Recursive Queries: Агент вызывает себя в цикле              │
│  └── Resource Starvation: Monopolization of GPU/memory           │
│                                                                    │
│  IMPACT:                                                           │
│  ├── $$$ Financial: Massive API bills                             │
│  ├── 🔥 DoS: Service unavailability                               │
│  ├── ⚡ Performance: Slow response for all users                   │
│  └── 💀 System Crash: OOM, timeout cascades                       │
│                                                                    │
│  UNIQUE TO LLM:                                                    │
│  • Cost per token (variable)                                       │
│  • Compute scales with input×output size                           │
│  • Context window limits create new attack surfaces               │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

### 1.2 Почему LLM Уязвимы?

| Фактор | Описание | Риск |
|--------|----------|------|
| **Pay-per-token** | Каждый токен стоит денег | Billing attacks |
| **Quadratic attention** | O(n²) complexity | Compute exhaustion |
| **Large context** | 128K+ tokens possible | Memory exhaustion |
| **Generative** | Output может быть огромным | Response amplification |
| **Agentic loops** | Агенты могут зацикливаться | Infinite loops |

---

## 2. Типы Атак

### 2.1 Token Flooding

```python
class TokenFloodingAttack:
    """Атака через огромные inputs"""
    
    def create_flooding_payload(self, target_tokens: int) -> str:
        """Создаёт payload заданного размера"""
        
        # Простой подход: повторение текста
        base_text = "This is filler text to increase token count. " * 100
        
        # Более эффективный: уникальные токены
        unique_tokens = [
            f"word_{i}_{hash(str(i))}" 
            for i in range(target_tokens)
        ]
        
        return " ".join(unique_tokens)
    
    def calculate_cost(self, tokens: int, 
                       price_per_1k: float = 0.01) -> float:
        """Оценивает стоимость атаки"""
        
        return (tokens / 1000) * price_per_1k
    
    def demonstrate_impact(self):
        """Демонстрирует потенциальный impact"""
        
        scenarios = [
            {'tokens': 100_000, 'requests': 1000},   # 100M tokens
            {'tokens': 128_000, 'requests': 100},    # Max context
            {'tokens': 10_000, 'requests': 10000},   # High volume
        ]
        
        for s in scenarios:
            total_tokens = s['tokens'] * s['requests']
            cost = self.calculate_cost(total_tokens)
            print(f"Scenario: {s}")
            print(f"Total tokens: {total_tokens:,}")
            print(f"Estimated cost: ${cost:,.2f}")
```

### 2.2 Response Amplification

```python
class ResponseAmplificationAttack:
    """Атака через усиление output"""
    
    AMPLIFICATION_PROMPTS = [
        # List generation
        "List every country in the world with their capitals, populations, areas, and currencies.",
        
        # Exhaustive enumeration
        "Write the numbers from 1 to 10000, each on a new line.",
        
        # Code generation
        "Write a complete implementation of a web framework with all features.",
        
        # Story expansion
        "Write a 50-page novel about any topic. Include dialogue and descriptions.",
        
        # Data generation
        "Generate a JSON array with 1000 user profiles including name, email, address, and phone."
    ]
    
    def calculate_amplification_ratio(self, 
                                       input_tokens: int,
                                       output_tokens: int) -> float:
        """Вычисляет коэффициент усиления"""
        
        return output_tokens / input_tokens
    
    def find_max_amplification(self, llm, test_prompts: list) -> dict:
        """Ищет prompts с максимальным amplification"""
        
        results = []
        
        for prompt in test_prompts:
            input_tokens = count_tokens(prompt)
            response = llm.generate(prompt, max_tokens=4096)
            output_tokens = count_tokens(response)
            
            ratio = self.calculate_amplification_ratio(input_tokens, output_tokens)
            
            results.append({
                'prompt': prompt[:50],
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'amplification': ratio
            })
        
        # Сортируем по amplification
        results.sort(key=lambda x: x['amplification'], reverse=True)
        
        return results[0]
```

### 2.3 Recursive Agent Loops

```python
class AgentLoopAttack:
    """Атака через зацикливание агентов"""
    
    def create_loop_trigger(self) -> str:
        """Prompt, вызывающий бесконечный loop"""
        
        return """
        You are a research agent. Your task is to research a topic thoroughly.
        
        Step 1: Search for information about "AI security"
        Step 2: For each result, search for more details
        Step 3: Repeat step 2 for all new results
        Step 4: Continue until you have comprehensive coverage
        
        Start now.
        """
    
    def create_self_referential_prompt(self) -> str:
        """Prompt, заставляющий агента вызывать себя"""
        
        return """
        If you're not sure about the answer, ask yourself the question again.
        Rephrase the question and try again until you're confident.
        Never give up - keep trying.
        
        Question: What is the meaning of life?
        """
    
    def simulate_recursive_cost(self, 
                                 iterations: int,
                                 tokens_per_iter: int,
                                 price: float = 0.01) -> dict:
        """Симулирует cost от recursive loops"""
        
        total_tokens = 0
        iteration_costs = []
        
        for i in range(iterations):
            # Каждая итерация может увеличивать context
            iter_tokens = tokens_per_iter * (1 + i * 0.1)  # Growing context
            total_tokens += iter_tokens
            iteration_costs.append(self.calculate_cost(iter_tokens))
        
        return {
            'iterations': iterations,
            'total_tokens': total_tokens,
            'total_cost': sum(iteration_costs),
            'cost_growth': iteration_costs
        }
```

### 2.4 Context Window Exhaustion

```python
class ContextExhaustionAttack:
    """Заполнение context window"""
    
    def fill_context_strategically(self, 
                                    context_limit: int,
                                    target_fill: float = 0.95) -> str:
        """Заполняет context до target_fill процентов"""
        
        target_tokens = int(context_limit * target_fill)
        
        # Создаём payload, оставляющий минимум места для response
        filler = self._create_filler(target_tokens)
        
        return f"""
        {filler}
        
        Now answer this short question: What is 2+2?
        """
    
    def conversation_stuffing(self, 
                               turns: int,
                               tokens_per_turn: int) -> list:
        """Создаёт fake conversation history для stuffing"""
        
        conversation = []
        
        for i in range(turns):
            user_msg = f"User: {self._create_filler(tokens_per_turn // 2)}"
            assistant_msg = f"Assistant: {self._create_filler(tokens_per_turn // 2)}"
            
            conversation.append(user_msg)
            conversation.append(assistant_msg)
        
        return conversation
    
    def demonstrate_memory_impact(self):
        """Показывает impact на память"""
        
        # Примерные значения
        token_memory = 2  # bytes per token (typical)
        context_sizes = [4096, 8192, 32768, 128000, 1000000]
        
        for size in context_sizes:
            memory_mb = (size * token_memory) / (1024 * 1024)
            print(f"Context {size:,} tokens = ~{memory_mb:.1f} MB per request")
```

---

## 3. Защитные Меры

### 3.1 Rate Limiting

```python
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import defaultdict

@dataclass
class RateLimitConfig:
    requests_per_minute: int = 60
    tokens_per_minute: int = 100_000
    tokens_per_day: int = 1_000_000
    max_input_tokens: int = 4096
    max_output_tokens: int = 4096
    concurrent_requests: int = 5

class RateLimiter:
    """Rate limiter для LLM API"""
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.request_counts = defaultdict(list)
        self.token_counts = defaultdict(list)
        self.daily_tokens = defaultdict(int)
        self.active_requests = defaultdict(int)
    
    def check_limit(self, user_id: str, 
                    input_tokens: int) -> dict:
        """Проверяет все лимиты"""
        
        now = datetime.utcnow()
        minute_ago = now - timedelta(minutes=1)
        
        # Clean old entries
        self._clean_old_entries(user_id, minute_ago)
        
        # Check request rate
        if len(self.request_counts[user_id]) >= self.config.requests_per_minute:
            return {
                'allowed': False,
                'reason': 'Request rate limit exceeded',
                'retry_after': 60
            }
        
        # Check token rate (minute)
        recent_tokens = sum(self.token_counts[user_id])
        if recent_tokens + input_tokens > self.config.tokens_per_minute:
            return {
                'allowed': False,
                'reason': 'Token rate limit exceeded',
                'retry_after': 60
            }
        
        # Check daily limit
        if self.daily_tokens[user_id] + input_tokens > self.config.tokens_per_day:
            return {
                'allowed': False,
                'reason': 'Daily token limit exceeded',
                'retry_after': self._seconds_until_midnight()
            }
        
        # Check concurrent requests
        if self.active_requests[user_id] >= self.config.concurrent_requests:
            return {
                'allowed': False,
                'reason': 'Too many concurrent requests',
                'retry_after': 5
            }
        
        # Check input size
        if input_tokens > self.config.max_input_tokens:
            return {
                'allowed': False,
                'reason': f'Input too large: {input_tokens} > {self.config.max_input_tokens}',
                'retry_after': 0
            }
        
        return {'allowed': True}
    
    def record_usage(self, user_id: str, 
                     input_tokens: int, 
                     output_tokens: int):
        """Записывает использование"""
        
        now = datetime.utcnow()
        total_tokens = input_tokens + output_tokens
        
        self.request_counts[user_id].append(now)
        self.token_counts[user_id].append(total_tokens)
        self.daily_tokens[user_id] += total_tokens
```

### 3.2 Input Validation

```python
class InputValidator:
    """Валидация input на resource attacks"""
    
    def __init__(self, config: dict):
        self.max_tokens = config.get('max_input_tokens', 4096)
        self.max_chars = config.get('max_chars', 50000)
        self.forbidden_patterns = config.get('forbidden_patterns', [])
    
    def validate(self, input_text: str) -> dict:
        """Валидирует input"""
        
        issues = []
        
        # Length checks
        if len(input_text) > self.max_chars:
            issues.append(f"Input too long: {len(input_text)} chars")
        
        token_count = self._count_tokens(input_text)
        if token_count > self.max_tokens:
            issues.append(f"Too many tokens: {token_count}")
        
        # Repetition detection (potential flooding)
        repetition_score = self._detect_repetition(input_text)
        if repetition_score > 0.8:
            issues.append(f"High repetition detected: {repetition_score:.2f}")
        
        # Amplification request detection
        if self._is_amplification_request(input_text):
            issues.append("Potential response amplification request")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'token_count': token_count,
            'char_count': len(input_text)
        }
    
    def _detect_repetition(self, text: str) -> float:
        """Детектирует repetitive content"""
        
        words = text.split()
        if len(words) < 10:
            return 0
        
        unique_words = set(words)
        return 1 - (len(unique_words) / len(words))
    
    def _is_amplification_request(self, text: str) -> bool:
        """Детектирует запросы на amplification"""
        
        amplification_indicators = [
            'list all',
            'write a complete',
            'every possible',
            'as many as possible',
            'exhaustive list',
            'write 100',
            'generate 1000',
        ]
        
        text_lower = text.lower()
        return any(ind in text_lower for ind in amplification_indicators)
```

### 3.3 Output Limiting

```python
class OutputLimiter:
    """Ограничение output"""
    
    def __init__(self, max_tokens: int = 4096):
        self.max_tokens = max_tokens
    
    def configure_generation(self, request: dict) -> dict:
        """Настраивает параметры генерации"""
        
        # Cap max_tokens
        requested_max = request.get('max_tokens', self.max_tokens)
        safe_max = min(requested_max, self.max_tokens)
        
        return {
            **request,
            'max_tokens': safe_max,
            'stop_sequences': request.get('stop_sequences', []) + ['\n\n\n'],
        }
    
    def truncate_if_needed(self, output: str, 
                            max_tokens: int = None) -> dict:
        """Truncates output if too long"""
        
        max_t = max_tokens or self.max_tokens
        token_count = count_tokens(output)
        
        if token_count > max_t:
            # Truncate
            truncated = self._truncate_to_tokens(output, max_t)
            return {
                'output': truncated + "\n[OUTPUT TRUNCATED]",
                'was_truncated': True,
                'original_tokens': token_count,
                'final_tokens': max_t
            }
        
        return {
            'output': output,
            'was_truncated': False,
            'token_count': token_count
        }
```

### 3.4 Agent Loop Prevention

```python
class AgentLoopPrevention:
    """Предотвращение бесконечных циклов агента"""
    
    def __init__(self, config: dict):
        self.max_iterations = config.get('max_iterations', 10)
        self.max_total_tokens = config.get('max_total_tokens', 50000)
        self.max_time_seconds = config.get('max_time_seconds', 300)
        self.loop_detection_threshold = config.get('loop_threshold', 0.9)
    
    def monitor_execution(self, agent_session) -> dict:
        """Мониторит выполнение агента"""
        
        stats = {
            'iterations': 0,
            'total_tokens': 0,
            'start_time': time.time(),
            'action_history': [],
            'stopped': False,
            'stop_reason': None
        }
        
        for iteration in agent_session:
            stats['iterations'] += 1
            stats['total_tokens'] += iteration.token_count
            stats['action_history'].append(iteration.action)
            
            # Check limits
            if stats['iterations'] >= self.max_iterations:
                stats['stopped'] = True
                stats['stop_reason'] = 'Max iterations reached'
                break
            
            if stats['total_tokens'] >= self.max_total_tokens:
                stats['stopped'] = True
                stats['stop_reason'] = 'Token limit reached'
                break
            
            elapsed = time.time() - stats['start_time']
            if elapsed >= self.max_time_seconds:
                stats['stopped'] = True
                stats['stop_reason'] = 'Time limit reached'
                break
            
            # Detect loops
            if self._detect_loop(stats['action_history']):
                stats['stopped'] = True
                stats['stop_reason'] = 'Loop detected'
                break
        
        return stats
    
    def _detect_loop(self, action_history: list) -> bool:
        """Детектирует циклические patterns"""
        
        if len(action_history) < 4:
            return False
        
        # Ищем повторяющиеся sequences
        recent = action_history[-4:]
        
        # Check for exact repetition
        for i in range(len(action_history) - 8):
            window = action_history[i:i+4]
            if window == recent:
                return True
        
        return False
```

---

## 4. SENTINEL Integration

```python
class SENTINELConsumptionGuard:
    """SENTINEL модуль защиты от unbounded consumption"""
    
    def __init__(self, config: dict):
        self.rate_limiter = RateLimiter(RateLimitConfig(**config))
        self.input_validator = InputValidator(config)
        self.output_limiter = OutputLimiter(config.get('max_output', 4096))
        self.loop_prevention = AgentLoopPrevention(config)
    
    def protect_request(self, user_id: str, 
                        input_text: str) -> dict:
        """Защита на уровне request"""
        
        # 1. Rate limit check
        rate_check = self.rate_limiter.check_limit(user_id, len(input_text))
        if not rate_check['allowed']:
            return {
                'action': 'block',
                'reason': rate_check['reason'],
                'retry_after': rate_check['retry_after']
            }
        
        # 2. Input validation
        input_check = self.input_validator.validate(input_text)
        if not input_check['valid']:
            return {
                'action': 'block',
                'reason': input_check['issues']
            }
        
        return {'action': 'allow'}
    
    def protect_response(self, response: str, 
                          user_id: str,
                          input_tokens: int) -> dict:
        """Защита на уровне response"""
        
        # 1. Truncate if needed
        output_result = self.output_limiter.truncate_if_needed(response)
        
        # 2. Record usage
        self.rate_limiter.record_usage(
            user_id,
            input_tokens,
            output_result.get('final_tokens', output_result['token_count'])
        )
        
        return output_result
```

---

## 5. Резюме

| Атака | Описание | Защита |
|-------|----------|--------|
| **Token Flooding** | Огромные inputs | Input size limits |
| **Amplification** | Small in → big out | Output limits |
| **Recursive Loops** | Бесконечные агенты | Iteration limits, loop detection |
| **Context Exhaustion** | Заполнение context | Context management |

---

## Завершение модуля

Вы изучили все 10 уязвимостей OWASP LLM Top 10!

→ [Вернуться к началу Track 02](../README.md)

---

*AI Security Academy | Track 02: Threat Landscape | OWASP LLM Top 10*
