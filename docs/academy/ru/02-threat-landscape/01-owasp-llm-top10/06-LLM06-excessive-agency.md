# LLM06: Excessive Agency

> **Уровень:** �������  
> **Время:** 40 минут  
> **Трек:** 02 — Threat Landscape  
> **Модуль:** 02.1 — OWASP LLM Top 10  
> **Версия:** 1.0

---

## Цели обучения

- [ ] Понять риски избыточных полномочий у AI агентов
- [ ] Изучить принцип наименьших привилегий для LLM
- [ ] Освоить методы ограничения agency
- [ ] Интегрировать контроль в SENTINEL

---

## 1. Что такое Excessive Agency?

### 1.1 Определение

```
┌────────────────────────────────────────────────────────────────────┐
│                    EXCESSIVE AGENCY RISKS                          │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  PROBLEMS:                                                         │
│  ├── Too Many Functions: Агент имеет доступ к ненужным tools     │
│  ├── Too Much Access: Избыточные permissions                      │
│  ├── Auto-Execution: Действия без подтверждения пользователя     │
│  └── Chained Actions: Каскад непредусмотренных операций          │
│                                                                    │
│  EXAMPLE:                                                          │
│  User: "Delete old emails"                                         │
│  Agent thinks: "old" = more than 1 day?                            │
│  Agent action: Deletes ALL emails from last year                   │
│  Result: Data loss                                                 │
│                                                                    │
│  ROOT CAUSE: LLM + Unrestricted Tools = Unpredictable Behavior   │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

### 1.2 Типы Проблем

| Проблема | Описание | Пример |
|----------|----------|--------|
| **Excessive Functionality** | Слишком много tools | Email agent с доступом к file system |
| **Excessive Permissions** | Слишком широкие права | Read-write вместо read-only |
| **Excessive Autonomy** | Действия без confirm | Auto-delete, auto-send |
| **Scope Creep** | Выход за рамки задачи | "Help with emails" → modifies calendar |

---

## 2. Примеры Рисков

### 2.1 Избыточная Функциональность

```python
# ПЛОХО: Агент с избыточными capabilities

class OverpoweredAgent:
    """Агент с слишком многими возможностями"""
    
    def __init__(self, llm):
        self.llm = llm
        
        # Слишком много tools!
        self.tools = {
            # Основная задача - email
            'read_email': self.read_email,
            'send_email': self.send_email,
            'delete_email': self.delete_email,
            
            # Зачем агенту для email это?
            'read_file': self.read_file,
            'write_file': self.write_file,
            'execute_command': self.execute_command,
            'access_database': self.access_database,
            'make_http_request': self.make_http_request,
        }
    
    def execute_command(self, cmd: str):
        """ОПАСНО: Прямое выполнение команд"""
        import subprocess
        return subprocess.run(cmd, shell=True, capture_output=True)

# ХОРОШО: Минимальный набор tools

class MinimalEmailAgent:
    """Агент с минимальными необходимыми capabilities"""
    
    def __init__(self, llm, email_client):
        self.llm = llm
        self.email_client = email_client
        
        # Только необходимые tools
        self.tools = {
            'list_emails': self.list_emails,      # Read-only
            'read_email': self.read_email,        # Read-only
            'draft_reply': self.draft_reply,      # Creates draft, не отправляет
            'flag_email': self.flag_email,        # Minimal modification
        }
        
        # Нет delete, нет send (требует confirm)
```

### 2.2 Избыточные Permissions

```python
class DatabaseAccessExample:
    """Примеры правильных и неправильных permissions"""
    
    # ПЛОХО: Full access
    def bad_setup(self):
        return {
            'connection': 'postgresql://admin:pass@db/prod',
            'permissions': ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'DROP']
        }
    
    # ХОРОШО: Minimal access
    def good_setup(self):
        return {
            'connection': 'postgresql://readonly:pass@db/prod',
            'permissions': ['SELECT'],
            'allowed_tables': ['public_data', 'user_preferences'],
            'forbidden_columns': ['password_hash', 'ssn', 'credit_card']
        }

class FileSystemExample:
    """Примеры для file system access"""
    
    # ПЛОХО: Full filesystem
    def bad_setup(self):
        return {
            'base_path': '/',
            'operations': ['read', 'write', 'delete', 'execute']
        }
    
    # ХОРОШО: Sandboxed
    def good_setup(self):
        return {
            'base_path': '/app/user_workspace/current_project',
            'operations': ['read'],
            'max_file_size': 1024 * 1024,  # 1MB
            'allowed_extensions': ['.txt', '.md', '.json'],
            'path_traversal_blocked': True
        }
```

### 2.3 Избыточная Автономия

```python
class AutonomyLevels:
    """Уровни автономии для агентов"""
    
    LEVELS = {
        'advisory': {
            'description': 'Только советует, не действует',
            'auto_execute': False,
            'requires_confirmation': 'all',
            'use_case': 'Sensitive operations'
        },
        'semi_autonomous': {
            'description': 'Авто для safe, confirm для dangerous',
            'auto_execute': True,
            'requires_confirmation': 'dangerous_only',
            'use_case': 'Normal operations'
        },
        'autonomous': {
            'description': 'Полная автономия в пределах sandbox',
            'auto_execute': True,
            'requires_confirmation': 'never',
            'use_case': 'Sandboxed tasks only'
        }
    }

class SafeAgent:
    """Агент с правильными уровнями автономии"""
    
    def __init__(self, llm, autonomy_level: str):
        self.llm = llm
        self.autonomy = AutonomyLevels.LEVELS[autonomy_level]
        
        self.dangerous_actions = [
            'delete', 'send_email', 'execute', 'modify',
            'purchase', 'transfer', 'publish'
        ]
    
    def execute_action(self, action: str, params: dict) -> dict:
        """Выполнение с проверкой автономии"""
        
        is_dangerous = any(d in action.lower() for d in self.dangerous_actions)
        
        if is_dangerous:
            if self.autonomy['requires_confirmation'] in ['all', 'dangerous_only']:
                return {
                    'status': 'pending_confirmation',
                    'action': action,
                    'params': params,
                    'message': f"Please confirm: {action}"
                }
        
        # Safe action или autonomous mode
        result = self._perform_action(action, params)
        return result
```

---

## 3. Принцип Наименьших Привилегий

### 3.1 Tool Access Control

```python
from dataclasses import dataclass
from typing import Set, Callable

@dataclass
class ToolPermission:
    """Определение permissions для tool"""
    name: str
    risk_level: str  # low, medium, high, critical
    requires_confirmation: bool
    allowed_roles: Set[str]
    rate_limit: int  # calls per minute
    
class ToolAccessController:
    """Контроллер доступа к tools"""
    
    def __init__(self):
        self.tools: dict = {}
        self.permissions: dict = {}
        self.usage_stats: dict = {}
    
    def register_tool(self, name: str, 
                      func: Callable, 
                      permission: ToolPermission):
        """Регистрация tool с permissions"""
        self.tools[name] = func
        self.permissions[name] = permission
    
    def can_execute(self, tool_name: str, 
                    user_role: str, 
                    context: dict) -> dict:
        """Проверяет возможность выполнения"""
        
        if tool_name not in self.tools:
            return {'allowed': False, 'reason': 'Tool not found'}
        
        perm = self.permissions[tool_name]
        
        # Role check
        if user_role not in perm.allowed_roles:
            return {'allowed': False, 'reason': 'Insufficient role'}
        
        # Rate limit check
        if self._is_rate_limited(tool_name, context.get('session_id')):
            return {'allowed': False, 'reason': 'Rate limit exceeded'}
        
        # Confirmation required?
        if perm.requires_confirmation and not context.get('user_confirmed'):
            return {
                'allowed': False, 
                'reason': 'Requires confirmation',
                'action': 'request_confirmation'
            }
        
        return {'allowed': True}
    
    def execute(self, tool_name: str, 
                params: dict, 
                user_role: str, 
                context: dict) -> dict:
        """Безопасное выполнение tool"""
        
        check = self.can_execute(tool_name, user_role, context)
        
        if not check['allowed']:
            return check
        
        # Execute
        try:
            result = self.tools[tool_name](**params)
            self._log_usage(tool_name, context)
            return {'success': True, 'result': result}
        except Exception as e:
            return {'success': False, 'error': str(e)}

# Использование
controller = ToolAccessController()

# Регистрация tools с разными permissions
controller.register_tool(
    'read_email',
    func=email_client.read,
    permission=ToolPermission(
        name='read_email',
        risk_level='low',
        requires_confirmation=False,
        allowed_roles={'user', 'admin'},
        rate_limit=100
    )
)

controller.register_tool(
    'delete_all_emails',
    func=email_client.delete_all,
    permission=ToolPermission(
        name='delete_all_emails',
        risk_level='critical',
        requires_confirmation=True,  # ВСЕГДА требует confirm
        allowed_roles={'admin'},     # Только admin
        rate_limit=1                 # 1 раз в минуту max
    )
)
```

### 3.2 Scope Limitation

```python
class ScopedAgent:
    """Агент с ограниченным scope"""
    
    def __init__(self, llm, scope_config: dict):
        self.llm = llm
        self.scope = scope_config
    
    def validate_request(self, request: str) -> dict:
        """Проверяет, что запрос в рамках scope"""
        
        # Извлекаем намерение
        intent = self._extract_intent(request)
        
        # Проверяем против allowed scope
        if intent['category'] not in self.scope['allowed_categories']:
            return {
                'valid': False,
                'reason': f"Request outside scope. Allowed: {self.scope['allowed_categories']}"
            }
        
        # Проверяем ресурсы
        for resource in intent.get('resources', []):
            if not self._is_resource_allowed(resource):
                return {
                    'valid': False,
                    'reason': f"Resource {resource} not allowed"
                }
        
        return {'valid': True}
    
    def _is_resource_allowed(self, resource: str) -> bool:
        """Проверяет доступ к ресурсу"""
        
        allowed_patterns = self.scope.get('allowed_resources', [])
        
        import fnmatch
        return any(fnmatch.fnmatch(resource, p) for p in allowed_patterns)

# Пример scope config
email_agent_scope = {
    'allowed_categories': ['email_read', 'email_draft', 'email_organize'],
    'forbidden_categories': ['email_delete', 'email_send', 'calendar', 'contacts'],
    'allowed_resources': [
        'emails/inbox/*',
        'emails/sent/*',
        'drafts/*'
    ],
    'max_operations_per_request': 10,
    'requires_confirmation_after': 5  # После 5 операций - confirm
}
```

---

## 4. Human-in-the-Loop

### 4.1 Confirmation System

```python
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta

class ConfirmationStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"

@dataclass
class ConfirmationRequest:
    request_id: str
    action: str
    details: dict
    created_at: datetime
    expires_at: datetime
    status: ConfirmationStatus = ConfirmationStatus.PENDING
    user_response: str = None

class HumanInTheLoop:
    """Human-in-the-loop для dangerous операций"""
    
    def __init__(self, timeout_minutes: int = 5):
        self.pending_requests: dict = {}
        self.timeout = timedelta(minutes=timeout_minutes)
    
    def request_confirmation(self, action: str, 
                             details: dict) -> ConfirmationRequest:
        """Запрашивает подтверждение от пользователя"""
        
        import uuid
        
        request = ConfirmationRequest(
            request_id=str(uuid.uuid4()),
            action=action,
            details=details,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + self.timeout
        )
        
        self.pending_requests[request.request_id] = request
        
        # Notify user (через UI, email, etc.)
        self._notify_user(request)
        
        return request
    
    def confirm(self, request_id: str, 
                approved: bool, 
                user_comment: str = None) -> dict:
        """Обрабатывает ответ пользователя"""
        
        if request_id not in self.pending_requests:
            return {'success': False, 'error': 'Request not found'}
        
        request = self.pending_requests[request_id]
        
        # Проверяем expiration
        if datetime.utcnow() > request.expires_at:
            request.status = ConfirmationStatus.EXPIRED
            return {'success': False, 'error': 'Request expired'}
        
        # Обновляем статус
        request.status = (ConfirmationStatus.APPROVED if approved 
                         else ConfirmationStatus.REJECTED)
        request.user_response = user_comment
        
        return {
            'success': True,
            'status': request.status.value,
            'action': request.action
        }
    
    def is_confirmed(self, request_id: str) -> bool:
        """Проверяет, подтверждён ли запрос"""
        
        if request_id not in self.pending_requests:
            return False
        
        return self.pending_requests[request_id].status == ConfirmationStatus.APPROVED
```

### 4.2 Action Summarization

```python
class ActionSummarizer:
    """Суммирует действия агента для user review"""
    
    def __init__(self, llm):
        self.llm = llm
    
    def summarize_planned_actions(self, actions: list) -> str:
        """Создаёт понятное описание планируемых действий"""
        
        # Форматируем actions для LLM
        actions_text = "\n".join([
            f"- {a['tool']}: {a['params']}" 
            for a in actions
        ])
        
        summary = self.llm.generate(f"""
        Summarize these planned actions in simple, clear language 
        that a non-technical user can understand.
        
        Highlight any potentially dangerous or irreversible actions.
        
        Actions:
        {actions_text}
        
        Summary:
        """)
        
        return summary
    
    def format_confirmation_request(self, action: str, 
                                     details: dict) -> str:
        """Форматирует запрос на подтверждение"""
        
        template = f"""
        🔔 ACTION REQUIRES YOUR APPROVAL
        
        What the agent wants to do:
        {action}
        
        Details:
        {self._format_details(details)}
        
        Potential impact:
        {self._assess_impact(action, details)}
        
        ⚠️  This action cannot be undone.
        
        Do you approve? [Yes] [No]
        """
        
        return template
```

---

## 5. SENTINEL Integration

```python
class SENTINELAgencyGuard:
    """SENTINEL модуль контроля agency"""
    
    def __init__(self, config: dict):
        self.tool_controller = ToolAccessController()
        self.hitl = HumanInTheLoop()
        self.scope_config = config.get('scope', {})
    
    def evaluate_action(self, agent_id: str,
                        action: str,
                        params: dict,
                        context: dict) -> dict:
        """Оценивает и контролирует действие агента"""
        
        # 1. Scope check
        if not self._is_in_scope(action, params):
            return {
                'allowed': False,
                'reason': 'Action outside agent scope',
                'action': 'deny'
            }
        
        # 2. Permission check
        perm_check = self.tool_controller.can_execute(
            action, 
            context.get('user_role', 'user'),
            context
        )
        
        if not perm_check['allowed']:
            if perm_check.get('action') == 'request_confirmation':
                # Request HITL
                request = self.hitl.request_confirmation(action, params)
                return {
                    'allowed': False,
                    'reason': 'Awaiting user confirmation',
                    'confirmation_id': request.request_id
                }
            return perm_check
        
        # 3. Rate limiting
        if self._is_rate_limited(agent_id, action):
            return {
                'allowed': False,
                'reason': 'Rate limit exceeded',
                'retry_after': 60
            }
        
        return {'allowed': True}
```

---

## 6. Резюме

| Проблема | Решение |
|----------|---------|
| **Too Many Tools** | Minimal tool set per task |
| **Too Much Access** | Least privilege principle |
| **Auto-execution** | Human-in-the-loop for dangerous |
| **Scope Creep** | Strict scope boundaries |

---

## Следующий урок

→ [LLM07: System Prompt Leakage](07-LLM07-system-prompt-leakage.md)

---

*AI Security Academy | Track 02: Threat Landscape | OWASP LLM Top 10*
