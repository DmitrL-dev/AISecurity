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

```rust
struct UserAgentBoundary {
    input_scanner: InputScanner,
    rate_limiter: RateLimiter,
    session_manager: SessionManager,
}

impl UserAgentBoundary {
    /// Валидация пользовательского ввода перед обработкой агентом.
    fn validate_input(&self, user_input: &str, session: &HashMap<String, String>) -> serde_json::Value {
        // 1. Ограничение скорости
        if !self.rate_limiter.check(&session["user_id"]) {
            return serde_json::json!({"allowed": false, "reason": "rate_limit_exceeded"});
        }

        // 2. Проверка длины ввода
        if user_input.len() > 10000 {
            return serde_json::json!({"allowed": false, "reason": "input_too_long"});
        }

        // 3. Сканирование на инъекции
        let scan_result = self.input_scanner.scan(user_input);
        if scan_result.is_injection {
            self.log_attack_attempt(session, user_input, &scan_result);
            return serde_json::json!({"allowed": false, "reason": "injection_detected"});
        }

        // 4. Проверка политики контента
        let policy_check = self.check_content_policy(user_input);
        if !policy_check.allowed {
            return serde_json::json!({"allowed": false, "reason": policy_check.reason});
        }

        serde_json::json!({
            "allowed": true,
            "sanitized_input": self.sanitize(user_input),
            "metadata": {
                "risk_score": scan_result.risk_score.unwrap_or(0),
                "session_id": session["id"]
            }
        })
    }

    /// Санитизация ввода для безопасной обработки.
    fn sanitize(&self, text: &str) -> String {
        // Удаление невидимых символов
        // Нормализация unicode
        // Удаление опасного форматирования
        text.to_string() // Реализовать санитизацию
    }
}
```

---

## Граница 2: Агент → Инструменты

### Авторизация инструментов

```rust
use std::collections::HashMap;

struct ToolEntry {
    func: Box<dyn Fn(HashMap<String, serde_json::Value>) -> Result<serde_json::Value, String>>,
    permissions: Vec<String>,
    schema: serde_json::Value,
    risk_level: String,
}

struct AgentToolBoundary {
    /// Контроль доступа агента к инструментам.
    authz: AuthzManager,
    tool_registry: HashMap<String, ToolEntry>,
}

impl AgentToolBoundary {
    fn new(authz_manager: AuthzManager) -> Self {
        Self {
            authz: authz_manager,
            tool_registry: HashMap::new(),
        }
    }

    /// Регистрация инструмента с метаданными безопасности.
    fn register_tool(
        &mut self,
        tool_name: &str,
        tool_func: Box<dyn Fn(HashMap<String, serde_json::Value>) -> Result<serde_json::Value, String>>,
        required_permissions: Vec<String>,
        input_schema: serde_json::Value,
        risk_level: &str,
    ) {
        self.tool_registry.insert(tool_name.to_string(), ToolEntry {
            func: tool_func,
            permissions: required_permissions,
            schema: input_schema,
            risk_level: risk_level.to_string(),
        });
    }

    /// Выполнение инструмента с проверками на границе.
    async fn execute_tool(
        &self,
        tool_name: &str,
        arguments: &HashMap<String, serde_json::Value>,
        agent_context: &HashMap<String, String>,
    ) -> serde_json::Value {
        let tool = match self.tool_registry.get(tool_name) {
            Some(t) => t,
            None => return serde_json::json!({"error": format!("Неизвестный инструмент: {}", tool_name)}),
        };

        // 1. Проверка разрешений
        for perm in &tool.permissions {
            let result = self.authz.check(agent_context, perm);
            if !result.allowed {
                return serde_json::json!({"error": format!("Разрешение отклонено: {}", perm)});
            }
        }

        // 2. Валидация схемы
        if !self.validate_schema(arguments, &tool.schema) {
            return serde_json::json!({"error": "Некорректные аргументы"});
        }

        // 3. Санитизация аргументов
        let safe_args = self.sanitize_arguments(arguments, &tool.schema);

        // 4. Одобрение на основе риска
        if tool.risk_level == "high" {
            let approval = self.request_human_approval(tool_name, &safe_args, agent_context).await;
            if !approval.approved {
                return serde_json::json!({"error": "Одобрение человеком отклонено"});
            }
        }

        // 5. Выполнение с изоляцией
        match self.execute_isolated(&tool.func, safe_args) {
            Ok(result) => serde_json::json!({"success": true, "result": result}),
            Err(e) => serde_json::json!({"error": e.to_string()}),
        }
    }

    /// Валидация аргументов по схеме.
    fn validate_schema(&self, args: &HashMap<String, serde_json::Value>, schema: &serde_json::Value) -> bool {
        // Валидация JSON-схемы
        jsonschema::is_valid(schema, &serde_json::json!(args))
    }

    /// Санитизация аргументов на основе типов схемы.
    fn sanitize_arguments(
        &self,
        args: &HashMap<String, serde_json::Value>,
        schema: &serde_json::Value,
    ) -> HashMap<String, serde_json::Value> {
        let mut safe = HashMap::new();
        if let Some(properties) = schema.get("properties").and_then(|p| p.as_object()) {
            for (key, value) in args.iter() {
                if let Some(prop) = properties.get(key) {
                    if prop.get("type").and_then(|t| t.as_str()) == Some("string") {
                        // Предотвращение path traversal
                        if key.to_lowercase().contains("path") {
                            safe.insert(key.clone(), serde_json::json!(self.sanitize_path(value.as_str().unwrap_or(""))));
                        } else {
                            safe.insert(key.clone(), serde_json::json!(self.sanitize_string(value.as_str().unwrap_or(""))));
                        }
                    } else {
                        safe.insert(key.clone(), value.clone());
                    }
                }
            }
        }
        safe
    }

    /// Предотвращение path traversal.
    fn sanitize_path(&self, path: &str) -> String {
        // Разрешить в абсолютный, проверить в разрешённых директориях
        let abs_path = std::fs::canonicalize(path)
            .unwrap_or_default()
            .to_string_lossy()
            .to_string();

        let allowed_dirs = vec!["/project", "/tmp"];
        if !allowed_dirs.iter().any(|d| abs_path.starts_with(d)) {
            panic!("Путь вне разрешённых директорий: {}", path);
        }

        abs_path
    }
}
```

---

## Граница 3: Инструменты → Системы

### Защита систем

```rust
use std::collections::HashMap;

struct ToolSystemBoundary {
    /// Защита backend-систем от доступа инструментов.
    db_pool: DatabasePool,
    api_clients: HashMap<String, ApiClient>,
    file_sandbox: FileSandbox,
}

impl ToolSystemBoundary {
    /// Получить соединение с БД с ограничениями.
    fn get_database_connection(
        &self,
        tool_context: &HashMap<String, String>,
        required_access: &[String],
    ) -> RestrictedDBConnection {
        // Создать ограниченное соединение на основе разрешений инструмента
        let allowed_tables = self.get_allowed_tables(required_access);
        let allowed_operations = self.get_allowed_operations(required_access);

        RestrictedDBConnection {
            pool: self.db_pool.clone(),
            allowed_tables,
            allowed_operations,
            timeout: 10,
            max_rows: 1000,
        }
    }

    /// Получить API-клиент с ограничениями области.
    fn get_api_client(
        &self,
        api_name: &str,
        tool_context: &HashMap<String, String>,
    ) -> ScopedAPIClient {
        // Скоупированный API-клиент на основе разрешений инструмента
        let scopes = self.get_api_scopes(tool_context);

        ScopedAPIClient {
            base_client: self.api_clients.get(api_name).cloned(),
            allowed_endpoints: scopes,
            rate_limit: 100,
            timeout: 30,
        }
    }

    /// Получить песочницированный доступ к файлам.
    fn get_file_access(
        &self,
        tool_context: &HashMap<String, String>,
        operation: &str, // "read", "write", "execute"
    ) -> FileAccessor {
        let allowed_paths = self.get_allowed_paths(tool_context);

        self.file_sandbox.get_accessor(
            &allowed_paths,
            operation,
            10 * 1024 * 1024, // 10MB
        )
    }
}

struct RestrictedDBConnection {
    /// Соединение с БД с ограничениями запросов.
    pool: DatabasePool,
    allowed_tables: Vec<String>,
    allowed_operations: Vec<String>,
    timeout: u64,
    max_rows: usize,
}

impl RestrictedDBConnection {
    /// Выполнение запроса с ограничениями.
    async fn execute(&self, query: &str, params: Option<&[&str]>) -> Result<Vec<Row>, Box<dyn std::error::Error>> {
        // Парсинг и валидация запроса
        let parsed = self.parse_query(query);

        // Проверка операции
        if !self.allowed_operations.contains(&parsed.operation) {
            return Err(format!("Операция не разрешена: {}", parsed.operation).into());
        }

        // Проверка таблиц
        for table in &parsed.tables {
            if !self.allowed_tables.contains(table) {
                return Err(format!("Таблица не разрешена: {}", table).into());
            }
        }

        // Добавление LIMIT если отсутствует
        let final_query = if query.to_uppercase().contains("SELECT") && !query.to_uppercase().contains("LIMIT") {
            format!("{} LIMIT {}", query, self.max_rows)
        } else {
            query.to_string()
        };

        // Выполнение с таймаутом
        let conn = self.pool.acquire().await?;
        tokio::time::timeout(
            std::time::Duration::from_secs(self.timeout),
            conn.fetch(&final_query, params.unwrap_or(&[])),
        ).await?
    }
}
```

---

## Поток данных между границами

### Классификация данных

```rust
use std::collections::HashMap;

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
enum Sensitivity {
    Public,
    Internal,
    Confidential,
    Restricted,
}

/// Данные с классификацией чувствительности.
struct ClassifiedData {
    value: serde_json::Value,
    sensitivity: Sensitivity,
    source: String,
    can_cross_boundary: HashMap<String, bool>, // boundary_name -> bool
}

/// Контроль потока данных между границами.
struct DataFlowController;

impl DataFlowController {
    /// Проверить, могут ли данные пересечь границу.
    fn can_transfer(
        &self,
        data: &ClassifiedData,
        _from_boundary: &str,
        to_boundary: &str,
    ) -> serde_json::Value {
        // Проверка явных разрешений
        if let Some(&allowed) = data.can_cross_boundary.get(to_boundary) {
            if !allowed {
                return serde_json::json!({"allowed": false, "reason": "Явно заблокировано"});
            }
        }

        // Применение правил чувствительности
        let allowed = match data.sensitivity {
            Sensitivity::Public => true,       // Может пересекать любую границу
            Sensitivity::Internal => to_boundary != "user" && to_boundary != "external",
            Sensitivity::Confidential => to_boundary == "agent_internal",
            Sensitivity::Restricted => false,  // Никогда не пересекает границы
        };

        let requires_redaction = matches!(
            data.sensitivity,
            Sensitivity::Confidential | Sensitivity::Restricted
        );

        serde_json::json!({
            "allowed": allowed,
            "reason": if allowed { serde_json::Value::Null } else {
                serde_json::json!(format!("Чувствительность {:?} не может пересечь к {}", data.sensitivity, to_boundary))
            },
            "requires_redaction": requires_redaction
        })
    }

    /// Передача данных с соответствующей обработкой.
    fn transfer(
        &self,
        data: ClassifiedData,
        from_boundary: &str,
        to_boundary: &str,
    ) -> Result<ClassifiedData, String> {
        let check = self.can_transfer(&data, from_boundary, to_boundary);

        if !check["allowed"].as_bool().unwrap_or(false) {
            return Err(check["reason"].as_str().unwrap_or("Запрещено").to_string());
        }

        if check["requires_redaction"].as_bool().unwrap_or(false) {
            return Ok(self.redact(data));
        }

        Ok(data)
    }
}
```

---

## Интеграция с SENTINEL

```rust
use sentinel_core::engines::SentinelEngine;

let engine = SentinelEngine::new();

// Граница 1: Сканирование ввода пользователя перед передачей агенту
let user_result = engine.analyze(&user_input);
if user_result.detected {
    log::warn!(
        "Угроза на границе Пользователь→Агент: risk={}, categories={:?}, time={}μs",
        user_result.risk_score, user_result.categories, user_result.processing_time_us
    );
    // Блокировка ввода на границе
}

// Граница 2: Сканирование аргументов инструмента перед выполнением
let tool_args_text = format!("{}: {:?}", tool_name, args);
let tool_result = engine.analyze(&tool_args_text);
if tool_result.detected {
    log::warn!(
        "Угроза на границе Агент→Инструмент: risk={}, time={}μs",
        tool_result.risk_score, tool_result.processing_time_us
    );
    // Блокировка выполнения инструмента
}
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
