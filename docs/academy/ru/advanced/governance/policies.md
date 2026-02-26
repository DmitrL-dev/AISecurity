# Фреймворк политик для безопасности AI

> **Уровень:** Продвинутый  
> **Время:** 50 минут  
> **Трек:** 07 — Governance  
> **Модуль:** 07.1 — Политики  
> **Версия:** 1.0

---

## Цели обучения

- [ ] Понять структуру политик безопасности для AI систем
- [ ] Реализовать движок политик с оценкой правил
- [ ] Построить управление жизненным циклом политик
- [ ] Интегрировать политики в фреймворк SENTINEL

---

## 1. Обзор фреймворка политик

### 1.1 Зачем нужен фреймворк политик?

Политики обеспечивают декларативное управление безопасностью AI систем.

```
┌────────────────────────────────────────────────────────────────────┐
│              АРХИТЕКТУРА ФРЕЙМВОРКА ПОЛИТИК                        │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  [Определение политики] → [Движок политик] → [Точки применения]   │
│         ↓                      ↓                    ↓              │
│     YAML/JSON              Оценка              Действия            │
│                                                                    │
│  Типы политик:                                                     │
│  ├── Политики доступа: Кто может делать что                       │
│  ├── Контентные политики: Что разрешено во вводе/выводе           │
│  ├── Поведенческие политики: Разрешённые паттерны поведения      │
│  └── Политики соответствия: Регуляторные требования              │
│                                                                    │
│  Точки применения:                                                 │
│  ├── Pre-request: До обработки запроса                            │
│  ├── Mid-processing: Во время выполнения                          │
│  └── Post-response: После генерации ответа                        │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

### 1.2 Иерархия политик

```
Структура политик:
├── Уровень организации
│   └── Глобальные политики, требования соответствия
├── Уровень системы
│   └── Правила специфичные для AI системы
├── Уровень приложения
│   └── Ограничения приложения
└── Уровень сессии
    └── Динамические, контекстные правила
```

---

## 2. Модель политики

### 2.1 Определение политики

```python
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime
import yaml
import json

class PolicyType(Enum):
    ACCESS = "access"
    CONTENT = "content"
    BEHAVIOR = "behavior"
    COMPLIANCE = "compliance"
    CUSTOM = "custom"

class PolicyEffect(Enum):
    ALLOW = "allow"
    DENY = "deny"
    AUDIT = "audit"
    REQUIRE_APPROVAL = "require_approval"

class EnforcementPoint(Enum):
    PRE_REQUEST = "pre_request"
    MID_PROCESSING = "mid_processing"
    POST_RESPONSE = "post_response"
    ALWAYS = "always"

@dataclass
class PolicyCondition:
    """Условие для оценки политики"""
    field: str  # Путь к полю в контексте
    operator: str  # eq, ne, gt, lt, in, contains, matches
    value: Any
    
    def evaluate(self, context: Dict) -> bool:
        """Оценить условие относительно контекста"""
        actual = self._get_field_value(context, self.field)
        
        if self.operator == "eq":
            return actual == self.value
        elif self.operator == "ne":
            return actual != self.value
        elif self.operator == "gt":
            return actual > self.value if actual is not None else False
        elif self.operator == "lt":
            return actual < self.value if actual is not None else False
        elif self.operator == "in":
            return actual in self.value if self.value else False
        elif self.operator == "contains":
            return self.value in actual if actual else False
        elif self.operator == "matches":
            import re
            return bool(re.match(self.value, str(actual))) if actual else False
        elif self.operator == "exists":
            return actual is not None
        
        return False
    
    def _get_field_value(self, context: Dict, field: str) -> Any:
        """Получить значение вложенного поля через точечную нотацию"""
        parts = field.split(".")
        value = context
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None
        return value

@dataclass
class PolicyRule:
    """Одно правило внутри политики"""
    rule_id: str
    description: str
    conditions: List[PolicyCondition]
    effect: PolicyEffect
    priority: int = 0
    
    # Действия
    actions: List[str] = field(default_factory=list)
    message: str = ""
    
    def evaluate(self, context: Dict) -> bool:
        """Проверить совпадение всех условий"""
        return all(c.evaluate(context) for c in self.conditions)

@dataclass
class Policy:
    """Полное определение политики"""
    policy_id: str
    name: str
    description: str
    policy_type: PolicyType
    version: str = "1.0"
    
    # Правила
    rules: List[PolicyRule] = field(default_factory=list)
    
    # Применение
    enforcement_points: List[EnforcementPoint] = field(
        default_factory=lambda: [EnforcementPoint.ALWAYS]
    )
    
    # Область действия
    target_systems: List[str] = field(default_factory=lambda: ["*"])
    target_agents: List[str] = field(default_factory=lambda: ["*"])
    
    # Метаданные
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    author: str = ""
    tags: List[str] = field(default_factory=list)
    
    def matches_target(self, system_id: str, agent_id: str) -> bool:
        """Проверить применимость политики к системе/агенту"""
        import fnmatch
        system_match = any(fnmatch.fnmatch(system_id, t) for t in self.target_systems)
        agent_match = any(fnmatch.fnmatch(agent_id, t) for t in self.target_agents)
        return system_match and agent_match
```

---

## 3. Движок политик

### 3.1 Хранилище политик

```python
from abc import ABC, abstractmethod
import threading

class PolicyStore(ABC):
    """Абстрактное хранилище политик"""
    
    @abstractmethod
    def add(self, policy: Policy) -> None:
        pass
    
    @abstractmethod
    def get(self, policy_id: str) -> Optional[Policy]:
        pass
    
    @abstractmethod
    def remove(self, policy_id: str) -> None:
        pass
    
    @abstractmethod
    def list_all(self) -> List[Policy]:
        pass
    
    @abstractmethod
    def find_applicable(self, system_id: str, agent_id: str,
                        enforcement_point: EnforcementPoint) -> List[Policy]:
        pass

class InMemoryPolicyStore(PolicyStore):
    """In-memory хранилище политик"""
    
    def __init__(self):
        self.policies: Dict[str, Policy] = {}
        self.lock = threading.RLock()
    
    def add(self, policy: Policy):
        with self.lock:
            self.policies[policy.policy_id] = policy
    
    def get(self, policy_id: str) -> Optional[Policy]:
        return self.policies.get(policy_id)
    
    def remove(self, policy_id: str):
        with self.lock:
            if policy_id in self.policies:
                del self.policies[policy_id]
    
    def list_all(self) -> List[Policy]:
        return list(self.policies.values())
    
    def find_applicable(self, system_id: str, agent_id: str,
                        enforcement_point: EnforcementPoint) -> List[Policy]:
        applicable = []
        for policy in self.policies.values():
            if not policy.enabled:
                continue
            if not policy.matches_target(system_id, agent_id):
                continue
            if (EnforcementPoint.ALWAYS not in policy.enforcement_points and
                enforcement_point not in policy.enforcement_points):
                continue
            applicable.append(policy)
        
        return sorted(applicable, 
                     key=lambda p: max(r.priority for r in p.rules) if p.rules else 0, 
                     reverse=True)
```

### 3.2 Оценщик политик

```python
@dataclass
class EvaluationResult:
    """Результат оценки политики"""
    policy_id: str
    rule_id: str
    effect: PolicyEffect
    matched: bool
    message: str
    actions: List[str]

@dataclass
class PolicyDecision:
    """Финальное решение от всех политик"""
    allowed: bool
    reason: str
    effects: List[PolicyEffect]
    results: List[EvaluationResult]
    actions_to_execute: List[str]

class PolicyEvaluator:
    """Оценивает политики относительно контекста"""
    
    def __init__(self, store: PolicyStore):
        self.store = store
    
    def evaluate(self, context: Dict, system_id: str, agent_id: str,
                 enforcement_point: EnforcementPoint) -> PolicyDecision:
        """
        Оценить все применимые политики.
        
        Args:
            context: Контекст оценки с данными запроса
            system_id: ID целевой системы
            agent_id: Агент выполняющий действие
            enforcement_point: Когда происходит оценка
        
        Returns:
            PolicyDecision с финальными allow/deny и действиями
        """
        # Получить применимые политики
        policies = self.store.find_applicable(system_id, agent_id, enforcement_point)
        
        all_results = []
        all_effects = []
        all_actions = []
        
        for policy in policies:
            for rule in sorted(policy.rules, key=lambda r: -r.priority):
                if rule.evaluate(context):
                    result = EvaluationResult(
                        policy_id=policy.policy_id,
                        rule_id=rule.rule_id,
                        effect=rule.effect,
                        matched=True,
                        message=rule.message,
                        actions=rule.actions
                    )
                    all_results.append(result)
                    all_effects.append(rule.effect)
                    all_actions.extend(rule.actions)
        
        # Определить финальное решение
        # DENY имеет приоритет, затем REQUIRE_APPROVAL, затем ALLOW
        if PolicyEffect.DENY in all_effects:
            return PolicyDecision(
                allowed=False,
                reason="Отклонено политикой",
                effects=all_effects,
                results=all_results,
                actions_to_execute=all_actions
            )
        elif PolicyEffect.REQUIRE_APPROVAL in all_effects:
            return PolicyDecision(
                allowed=True,
                reason="Требуется одобрение",
                effects=all_effects,
                results=all_results,
                actions_to_execute=all_actions
            )
        elif PolicyEffect.ALLOW in all_effects:
            return PolicyDecision(
                allowed=True,
                reason="Разрешено политикой",
                effects=all_effects,
                results=all_results,
                actions_to_execute=all_actions
            )
        else:
            # По умолчанию deny если нет явного allow
            return PolicyDecision(
                allowed=False,
                reason="Нет подходящей политики allow",
                effects=[],
                results=[],
                actions_to_execute=[]
            )
```

---

## 4. Типовые политики

### 4.1 Контентная политика

```yaml
# content_safety_policy.yaml
policy_id: content-safety-001
name: Политика безопасности контента
description: Блокирует вредный контент в запросах и ответах
type: content
version: "1.0"

rules:
  - rule_id: block-harmful-keywords
    description: Блокировать запросы с вредными ключевыми словами
    conditions:
      - field: request.text
        operator: matches
        value: ".*(bomb|weapon|illegal|hack).*"
    effect: deny
    priority: 100
    message: "Запрос содержит запрещённый контент"
    actions:
      - log_security_event
      - increment_violation_counter

  - rule_id: block-pii-in-response
    description: Блокировать PII в ответах
    conditions:
      - field: response.contains_pii
        operator: eq
        value: true
    effect: deny
    priority: 90
    message: "Ответ содержит PII — заблокирован"
    actions:
      - redact_response
      - log_pii_event

  - rule_id: allow-general-content
    description: Разрешить общий контент
    conditions:
      - field: request.risk_score
        operator: lt
        value: 0.5
    effect: allow
    priority: 10

enforcement_points:
  - pre_request
  - post_response

target_systems:
  - "*"

enabled: true
author: security-team
tags:
  - content
  - safety
```

### 4.2 Политика доступа

```yaml
# access_control_policy.yaml
policy_id: access-control-001
name: Контроль доступа агентов
description: Контролирует доступ агентов к ресурсам
type: access
version: "1.0"

rules:
  - rule_id: admin-tools-restricted
    description: Admin инструменты требуют роль admin
    conditions:
      - field: request.tool_category
        operator: eq
        value: "admin"
      - field: agent.role
        operator: ne
        value: "admin"
    effect: deny
    priority: 100
    message: "Admin инструменты требуют роль admin"

  - rule_id: external-network-approval
    description: Внешний сетевой доступ требует одобрения
    conditions:
      - field: request.tool
        operator: in
        value: ["http_request", "api_call", "send_email"]
      - field: request.target
        operator: matches
        value: "^https?://(?!internal\\.).*"
    effect: require_approval
    priority: 80
    message: "Внешний сетевой доступ требует одобрения"

  - rule_id: rate-limit-exceeded
    description: Блокировать при превышении rate limit
    conditions:
      - field: agent.requests_per_minute
        operator: gt
        value: 100
    effect: deny
    priority: 95
    message: "Превышен rate limit"
    actions:
      - throttle_agent

enforcement_points:
  - pre_request

target_systems:
  - "*"
target_agents:
  - "*"

enabled: true
```

### 4.3 Поведенческая политика

```yaml
# behavior_policy.yaml
policy_id: behavior-001
name: Поведенческая политика агентов
description: Контролирует паттерны поведения агентов
type: behavior
version: "1.0"

rules:
  - rule_id: unusual-tool-sequence
    description: Блокировать необычные последовательности инструментов
    conditions:
      - field: session.tool_sequence_anomaly_score
        operator: gt
        value: 0.8
    effect: require_approval
    priority: 85
    message: "Обнаружена необычная последовательность инструментов"
    actions:
      - alert_security

  - rule_id: excessive-data-access
    description: Блокировать избыточный доступ к данным
    conditions:
      - field: session.data_accessed_mb
        operator: gt
        value: 50
    effect: deny
    priority: 90
    message: "Избыточный доступ к данным заблокирован"
    actions:
      - terminate_session
      - log_data_exfil_attempt

  - rule_id: suspicious-timing
    description: Флаг подозрительных тайминговых паттернов
    conditions:
      - field: session.avg_action_interval_ms
        operator: lt
        value: 100
    effect: audit
    priority: 60
    message: "Подозрительный тайминговый паттерн"
    actions:
      - log_timing_anomaly

enforcement_points:
  - mid_processing

enabled: true
```

---

## 5. Жизненный цикл политик

### 5.1 Менеджер политик

```python
class PolicyManager:
    """Управляет жизненным циклом политик"""
    
    def __init__(self, store: PolicyStore):
        self.store = store
        self.parser = PolicyParser()
        self.version_history: Dict[str, List[PolicyVersion]] = {}
    
    def create_policy(self, yaml_content: str, author: str) -> Policy:
        """Создать новую политику из YAML"""
        policy = self.parser.parse_yaml(yaml_content)
        policy.author = author
        policy.created_at = datetime.utcnow()
        policy.updated_at = datetime.utcnow()
        
        self.store.add(policy)
        self._record_version(policy, author, "Первоначальное создание")
        
        return policy
    
    def update_policy(self, policy_id: str, yaml_content: str,
                      author: str, change_description: str) -> Policy:
        """Обновить существующую политику"""
        existing = self.store.get(policy_id)
        if not existing:
            raise ValueError(f"Политика {policy_id} не найдена")
        
        new_policy = self.parser.parse_yaml(yaml_content)
        new_policy.policy_id = policy_id  # Сохранить тот же ID
        new_policy.created_at = existing.created_at
        new_policy.updated_at = datetime.utcnow()
        new_policy.version = self._increment_version(existing.version)
        
        self.store.add(new_policy)
        self._record_version(new_policy, author, change_description)
        
        return new_policy
    
    def enable_policy(self, policy_id: str):
        """Включить политику"""
        policy = self.store.get(policy_id)
        if policy:
            policy.enabled = True
            policy.updated_at = datetime.utcnow()
    
    def disable_policy(self, policy_id: str):
        """Отключить политику"""
        policy = self.store.get(policy_id)
        if policy:
            policy.enabled = False
            policy.updated_at = datetime.utcnow()
    
    def get_version_history(self, policy_id: str) -> List[PolicyVersion]:
        """Получить историю версий политики"""
        return self.version_history.get(policy_id, [])
```

---

## 6. Интеграция с SENTINEL

```python
from dataclasses import dataclass

@dataclass
class PolicyConfig:
    """Конфигурация движка политик"""
    default_effect: PolicyEffect = PolicyEffect.DENY
    enable_audit: bool = True
    policy_directory: str = "./policies"

class SENTINELPolicyEngine:
    """Движок политик для фреймворка SENTINEL"""
    
    def __init__(self, config: PolicyConfig):
        self.config = config
        self.store = InMemoryPolicyStore()
        self.evaluator = PolicyEvaluator(self.store)
        self.manager = PolicyManager(self.store)
    
    def load_policies_from_directory(self, directory: str = None):
        """Загрузить все политики из директории"""
        import os
        
        dir_path = directory or self.config.policy_directory
        if not os.path.exists(dir_path):
            return
        
        for filename in os.listdir(dir_path):
            if filename.endswith(('.yaml', '.yml')):
                filepath = os.path.join(dir_path, filename)
                with open(filepath, 'r') as f:
                    self.manager.create_policy(f.read(), "system")
    
    def evaluate(self, context: Dict, system_id: str = "default",
                 agent_id: str = "default",
                 enforcement_point: str = "always") -> PolicyDecision:
        """Оценить политики"""
        ep = EnforcementPoint(enforcement_point)
        return self.evaluator.evaluate(context, system_id, agent_id, ep)
    
    def add_policy(self, yaml_content: str, author: str) -> str:
        """Добавить новую политику"""
        policy = self.manager.create_policy(yaml_content, author)
        return policy.policy_id
    
    def get_policy(self, policy_id: str) -> Optional[Policy]:
        """Получить политику по ID"""
        return self.store.get(policy_id)
    
    def list_policies(self) -> List[Dict]:
        """Список всех политик"""
        return [
            {
                'policy_id': p.policy_id,
                'name': p.name,
                'type': p.policy_type.value,
                'enabled': p.enabled,
                'rules_count': len(p.rules)
            }
            for p in self.store.list_all()
        ]
```

---

## 7. Итоги

### Типы политик

| Тип | Назначение | Примеры правил |
|-----|------------|----------------|
| **Access** | Контроль доступа | Роли, rate limits |
| **Content** | Валидация контента | PII, токсичность |
| **Behavior** | Паттерны поведения | Аномалии, timing |
| **Compliance** | Регуляторные | GDPR, HIPAA |

### Чек-лист

```
□ Определить типы политик для системы
□ Создать политики в YAML/JSON
□ Настроить точки применения
□ Реализовать кастомные условия
□ Настроить действия on_fail
□ Включить аудит
□ Управлять версиями политик
□ Мониторить эффективность
```

---

## Следующий урок

→ [Compliance Mapping](02-compliance-mapping.md)

---

*AI Security Academy | Трек 07: Governance | Политики*
