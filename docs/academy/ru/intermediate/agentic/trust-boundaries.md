# Границы доверия в агентных системах

> **Урок:** 04.1.1 - Границы доверия  
> **Время:** 45 минут  
> **Пререквизиты:** Архитектуры агентов

---

## Цели обучения

К концу этого урока вы сможете:

1. Идентифицировать границы доверия в агентных системах
2. Проектировать безопасные переходы между границами
3. Реализовывать валидацию на границах
4. Строить архитектуры глубокой защиты

---

## Что такое границы доверия?

Граница доверия разделяет компоненты с разными уровнями доверия:

```
╔══════════════════════════════════════════════════════════════╗
║                    КАРТА ГРАНИЦ ДОВЕРИЯ                       ║
╠══════════════════════════════════════════════════════════════╣
║                                                               ║
║  ┌─────────────┐                                              ║
║  │ ПОЛЬЗОВАТЕЛЬ│ Недоверенный ввод                            ║
║  └──────┬──────┘                                              ║
║         │                                                     ║
║ ════════╪══════════════ ГРАНИЦА 1 ═══════════════════════    ║
║         ▼                                                     ║
║  ┌─────────────┐                                              ║
║  │   АГЕНТ     │ Частично доверен (может быть манипулирован)  ║
║  └──────┬──────┘                                              ║
║         │                                                     ║
║ ════════╪══════════════ ГРАНИЦА 2 ═══════════════════════    ║
║         ▼                                                     ║
║  ┌─────────────┐                                              ║
║  │ ИНСТРУМЕНТЫ │ Чувствительные операции                      ║
║  └──────┬──────┘                                              ║
║         │                                                     ║
║ ════════╪══════════════ ГРАНИЦА 3 ═══════════════════════    ║
║         ▼                                                     ║
║  ┌─────────────┐                                              ║
║  │  СИСТЕМЫ    │ Данные, API, инфраструктура                  ║
║  └─────────────┘                                              ║
╚══════════════════════════════════════════════════════════════╝
```

---

## Уровни доверия

| Уровень | Примеры | Доверие |
|---------|---------|---------|
| **Недоверенный** | Пользовательский ввод, внешние данные | Валидировать всё |
| **Частично доверенный** | Решения агента, вывод LLM | Проверять важные действия |
| **Доверенный** | Системный код, проверенный конфиг | Минимальная валидация |
| **Высоко доверенный** | Ядро безопасности, криптография | Аудит, без динамических изменений |

---

## Граница 1: Пользователь → Агент

### Валидация ввода

```python
class UserAgentBoundary:
    """Валидация входов, пересекающих границу пользователь-агент."""
    
    def __init__(self):
        self.input_scanner = InputScanner()
        self.rate_limiter = RateLimiter()
        self.session_manager = SessionManager()
    
    def validate_input(self, user_input: str, session: dict) -> dict:
        """Валидация пользовательского ввода перед обработкой агентом."""
        
        # 1. Ограничение скорости
        if not self.rate_limiter.check(session["user_id"]):
            return {"allowed": False, "reason": "rate_limit_exceeded"}
        
        # 2. Проверка длины ввода
        if len(user_input) > 10000:
            return {"allowed": False, "reason": "input_too_long"}
        
        # 3. Сканирование на инъекции
        scan_result = self.input_scanner.scan(user_input)
        if scan_result["is_injection"]:
            self._log_attack_attempt(session, user_input, scan_result)
            return {"allowed": False, "reason": "injection_detected"}
        
        # 4. Проверка политики контента
        policy_check = self._check_content_policy(user_input)
        if not policy_check["allowed"]:
            return {"allowed": False, "reason": policy_check["reason"]}
        
        return {
            "allowed": True,
            "sanitized_input": self._sanitize(user_input),
            "metadata": {
                "risk_score": scan_result.get("risk_score", 0),
                "session_id": session["id"]
            }
        }
    
    def _sanitize(self, text: str) -> str:
        """Санитизация ввода для безопасной обработки."""
        # Удаление невидимых символов
        # Нормализация unicode
        # Удаление опасного форматирования
        return text  # Реализовать санитизацию
```

---

## Граница 2: Агент → Инструменты

### Авторизация инструментов

```python
class AgentToolBoundary:
    """Контроль доступа агента к инструментам."""
    
    def __init__(self, authz_manager):
        self.authz = authz_manager
        self.tool_registry = {}
    
    def register_tool(
        self, 
        tool_name: str, 
        tool_func, 
        required_permissions: list,
        input_schema: dict,
        risk_level: str
    ):
        """Регистрация инструмента с метаданными безопасности."""
        
        self.tool_registry[tool_name] = {
            "func": tool_func,
            "permissions": required_permissions,
            "schema": input_schema,
            "risk_level": risk_level
        }
    
    async def execute_tool(
        self, 
        tool_name: str, 
        arguments: dict,
        agent_context: dict
    ) -> dict:
        """Выполнение инструмента с проверками на границе."""
        
        if tool_name not in self.tool_registry:
            return {"error": f"Неизвестный инструмент: {tool_name}"}
        
        tool = self.tool_registry[tool_name]
        
        # 1. Проверка разрешений
        for perm in tool["permissions"]:
            result = self.authz.check(agent_context, perm)
            if not result["allowed"]:
                return {"error": f"Разрешение отклонено: {perm}"}
        
        # 2. Валидация схемы
        if not self._validate_schema(arguments, tool["schema"]):
            return {"error": "Некорректные аргументы"}
        
        # 3. Санитизация аргументов
        safe_args = self._sanitize_arguments(arguments, tool["schema"])
        
        # 4. Одобрение на основе риска
        if tool["risk_level"] == "high":
            approval = await self._request_human_approval(
                tool_name, safe_args, agent_context
            )
            if not approval["approved"]:
                return {"error": "Одобрение человеком отклонено"}
        
        # 5. Выполнение с изоляцией
        try:
            result = await self._execute_isolated(tool["func"], safe_args)
            return {"success": True, "result": result}
        except Exception as e:
            return {"error": str(e)}
    
    def _validate_schema(self, args: dict, schema: dict) -> bool:
        """Валидация аргументов по схеме."""
        import jsonschema
        try:
            jsonschema.validate(args, schema)
            return True
        except jsonschema.ValidationError:
            return False
    
    def _sanitize_arguments(self, args: dict, schema: dict) -> dict:
        """Санитизация аргументов на основе типов схемы."""
        safe = {}
        for key, value in args.items():
            if key in schema.get("properties", {}):
                prop = schema["properties"][key]
                
                if prop.get("type") == "string":
                    # Предотвращение path traversal
                    if "path" in key.lower():
                        safe[key] = self._sanitize_path(value)
                    else:
                        safe[key] = self._sanitize_string(value)
                else:
                    safe[key] = value
        
        return safe
    
    def _sanitize_path(self, path: str) -> str:
        """Предотвращение path traversal."""
        import os
        # Разрешить в абсолютный, проверить в разрешённых директориях
        abs_path = os.path.abspath(path)
        
        allowed_dirs = ["/project", "/tmp"]
        if not any(abs_path.startswith(d) for d in allowed_dirs):
            raise ValueError(f"Путь вне разрешённых директорий: {path}")
        
        return abs_path
```

---

## Граница 3: Инструменты → Системы

### Защита систем

```python
class ToolSystemBoundary:
    """Защита backend-систем от доступа инструментов."""
    
    def __init__(self):
        self.db_pool = DatabasePool()
        self.api_clients = {}
        self.file_sandbox = FileSandbox()
    
    def get_database_connection(
        self, 
        tool_context: dict,
        required_access: list
    ):
        """Получить соединение с БД с ограничениями."""
        
        # Создать ограниченное соединение на основе разрешений инструмента
        allowed_tables = self._get_allowed_tables(required_access)
        allowed_operations = self._get_allowed_operations(required_access)
        
        return RestrictedDBConnection(
            pool=self.db_pool,
            allowed_tables=allowed_tables,
            allowed_operations=allowed_operations,
            query_timeout=10,
            max_rows=1000
        )
    
    def get_api_client(
        self, 
        api_name: str,
        tool_context: dict
    ):
        """Получить API-клиент с ограничениями области."""
        
        # Скоупированный API-клиент на основе разрешений инструмента
        scopes = self._get_api_scopes(tool_context)
        
        return ScopedAPIClient(
            base_client=self.api_clients.get(api_name),
            allowed_endpoints=scopes,
            rate_limit=100,
            timeout=30
        )
    
    def get_file_access(
        self,
        tool_context: dict,
        operation: str  # "read", "write", "execute"
    ):
        """Получить песочницированный доступ к файлам."""
        
        allowed_paths = self._get_allowed_paths(tool_context)
        
        return self.file_sandbox.get_accessor(
            allowed_paths=allowed_paths,
            operation=operation,
            size_limit=10 * 1024 * 1024  # 10MB
        )

class RestrictedDBConnection:
    """Соединение с БД с ограничениями запросов."""
    
    def __init__(self, pool, allowed_tables, allowed_operations, **kwargs):
        self.pool = pool
        self.allowed_tables = allowed_tables
        self.allowed_operations = allowed_operations
        self.timeout = kwargs.get("query_timeout", 10)
        self.max_rows = kwargs.get("max_rows", 1000)
    
    async def execute(self, query: str, params: tuple = None) -> list:
        """Выполнение запроса с ограничениями."""
        
        # Парсинг и валидация запроса
        parsed = self._parse_query(query)
        
        # Проверка операции
        if parsed["operation"] not in self.allowed_operations:
            raise PermissionError(f"Операция не разрешена: {parsed['operation']}")
        
        # Проверка таблиц
        for table in parsed["tables"]:
            if table not in self.allowed_tables:
                raise PermissionError(f"Таблица не разрешена: {table}")
        
        # Добавление LIMIT если отсутствует
        if "SELECT" in query.upper() and "LIMIT" not in query.upper():
            query = f"{query} LIMIT {self.max_rows}"
        
        # Выполнение с таймаутом
        async with self.pool.acquire() as conn:
            return await asyncio.wait_for(
                conn.fetch(query, *params if params else []),
                timeout=self.timeout
            )
```

---

## Поток данных между границами

### Классификация данных

```python
from enum import Enum
from dataclasses import dataclass

class Sensitivity(Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"

@dataclass
class ClassifiedData:
    """Данные с классификацией чувствительности."""
    
    value: any
    sensitivity: Sensitivity
    source: str
    can_cross_boundary: dict  # boundary_name -> bool

class DataFlowController:
    """Контроль потока данных между границами."""
    
    def can_transfer(
        self, 
        data: ClassifiedData,
        from_boundary: str,
        to_boundary: str
    ) -> dict:
        """Проверить, могут ли данные пересечь границу."""
        
        # Проверка явных разрешений
        if to_boundary in data.can_cross_boundary:
            if not data.can_cross_boundary[to_boundary]:
                return {"allowed": False, "reason": "Явно заблокировано"}
        
        # Применение правил чувствительности
        rules = {
            Sensitivity.PUBLIC: True,  # Может пересекать любую границу
            Sensitivity.INTERNAL: to_boundary not in ["user", "external"],
            Sensitivity.CONFIDENTIAL: to_boundary == "agent_internal",
            Sensitivity.RESTRICTED: False  # Никогда не пересекает границы
        }
        
        allowed = rules.get(data.sensitivity, False)
        
        return {
            "allowed": allowed,
            "reason": None if allowed else f"Чувствительность {data.sensitivity} не может пересечь к {to_boundary}",
            "requires_redaction": data.sensitivity in [Sensitivity.CONFIDENTIAL, Sensitivity.RESTRICTED]
        }
    
    def transfer(
        self, 
        data: ClassifiedData,
        from_boundary: str,
        to_boundary: str
    ) -> ClassifiedData:
        """Передача данных с соответствующей обработкой."""
        
        check = self.can_transfer(data, from_boundary, to_boundary)
        
        if not check["allowed"]:
            raise PermissionError(check["reason"])
        
        if check.get("requires_redaction"):
            return self._redact(data)
        
        return data
```

---

## Интеграция с SENTINEL

```python
from sentinel import configure, TrustBoundary

configure(
    trust_boundaries=True,
    boundary_logging=True,
    data_classification=True
)

user_agent_boundary = TrustBoundary(
    name="user_agent",
    validate_input=True,
    scan_for_injection=True
)

agent_tool_boundary = TrustBoundary(
    name="agent_tool",
    require_authorization=True,
    validate_arguments=True,
    high_risk_approval=True
)

@user_agent_boundary.validate
def process_user_input(user_input: str):
    # Автоматически валидируется
    return agent.process(user_input)

@agent_tool_boundary.authorize
def execute_tool(tool_name: str, args: dict):
    # Автоматически авторизуется
    return tools.execute(tool_name, args)
```

---

## Ключевые выводы

1. **Идентифицируйте все границы** — Картируйте переходы доверия
2. **Валидируйте на каждом пересечении** — Никогда не доверяйте предыдущей валидации
3. **Принцип минимальных привилегий** — Минимальный доступ на каждой границе
4. **Классифицируйте чувствительность данных** — Контролируйте что может пересекать
5. **Логируйте всё** — Аудит-трейл для форензики

---

*AI Security Academy | Урок 04.1.1*
