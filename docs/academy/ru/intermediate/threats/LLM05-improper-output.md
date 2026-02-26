# LLM05: Improper Output Handling

> **Урок:** 02.1.5 - Improper Output Handling  
> **OWASP ID:** LLM05  
> **Время:** 40 минут  
> **Уровень риска:** Medium-High

---

## Цели обучения

К концу этого урока вы сможете:

1. Идентифицировать уязвимости обработки output
2. Внедрять безопасную обработку output
3. Обнаруживать и предотвращать downstream атаки
4. Проектировать безопасные паттерны интеграции LLM

---

## Что такое Improper Output Handling?

LLM outputs часто считаются доверенными и передаются напрямую в downstream системы без валидации. Это создаёт уязвимости когда LLM output содержит:

| Тип контента | Риск | Пример |
|--------------|------|--------|
| **Code** | Code Injection | SQL, JavaScript, Shell |
| **Markup** | XSS, SSRF | HTML, Markdown links |
| **Data** | Data Leakage | PII, secrets, internal data |
| **Commands** | Command Injection | System calls, API calls |

---

## Векторы атак

### 1. Cross-Site Scripting (XSS) через LLM

```rust
// Небезопасно: LLM output рендерится напрямую в браузере
let user_message = "Generate a greeting for <script>stealCookies()</script>";

let llm_response = llm.generate(user_message);
// Response может содержать: "Hello, <script>stealCookies()</script>!"

// Уязвимый рендеринг
let html = format!("<div>{}</div>", llm_response); // XSS!
```

**Безопасная реализация:**

```rust
use html_escape::encode_text;

/// Безопасный рендеринг LLM output в HTML контексте.
fn render_llm_output(response: &str) -> String {
    // Escape HTML entities
    let safe_response = encode_text(response).to_string();

    // Опционально разрешаем safe markdown
    let safe_response = allowed_markdown_to_html(&safe_response);

    format!("<div class='llm-response'>{}</div>", safe_response)
}
```

---

### 2. SQL Injection через LLM

```rust
// Опасно: Использование LLM output в SQL query
let user_request = "Show me all users named Robert'); DROP TABLE users;--";

let llm_response = llm.generate(
    &format!("Generate SQL to find users: {}", user_request)
);
// LLM может сгенерировать: SELECT * FROM users WHERE name = 'Robert'); DROP TABLE users;--'

// УЯЗВИМЫЙ КОД
cursor.execute(&llm_response); // SQL Injection!
```

**Безопасная реализация:**

```rust
use std::collections::HashSet;

struct SecureSQLGenerator {
    /// Генерация и валидация SQL из LLM output.
    allowed_operations: HashSet<String>,
    forbidden_keywords: HashSet<String>,
}

impl SecureSQLGenerator {
    fn new() -> Self {
        Self {
            allowed_operations: HashSet::from(["SELECT".to_string()]),
            forbidden_keywords: HashSet::from([
                "DROP".into(), "DELETE".into(), "UPDATE".into(),
                "INSERT".into(), "TRUNCATE".into(), "ALTER".into(),
            ]),
        }
    }

    /// Безопасное выполнение LLM-сгенерированного SQL.
    fn execute_safe_query(
        &self,
        llm_sql: &str,
        params: Option<&HashMap<String, String>>,
    ) -> Result<Vec<Row>, String> {
        // 1. Parse и validate SQL
        if !self.is_safe_query(llm_sql) {
            return Err("Unsafe SQL detected".to_string());
        }

        // 2. Используем parameterized queries
        let safe_sql = self.parameterize(llm_sql, params);

        // 3. Выполняем с read-only connection
        self.session.execute_readonly(&safe_sql, params)
    }

    fn is_safe_query(&self, sql: &str) -> bool {
        let sql_upper = sql.to_uppercase();

        // Проверяем только allowed operations
        let first_word = sql_upper.split_whitespace().next().unwrap_or("");
        if !self.allowed_operations.contains(first_word) {
            return false;
        }

        // Проверяем на forbidden keywords
        for keyword in &self.forbidden_keywords {
            if sql_upper.contains(keyword.as_str()) {
                return false;
            }
        }

        true
    }
}
```

---

### 3. Server-Side Request Forgery (SSRF)

```rust
// Опасно: LLM генерирует URLs которые потом fetched
let user_input = "Summarize this article: http://internal-api:8080/admin/secrets";

let llm_response = llm.generate(&format!("Fetch and summarize: {}", user_input));

// LLM может извлечь URL и система его fetch
let url = extract_url(&llm_response);
let content = reqwest::get(&url).await?; // SSRF - доступ к internal resources!
```

**Безопасная реализация:**

```rust
use std::collections::HashSet;
use std::net::IpAddr;
use url::Url;

struct SafeURLFetcher {
    /// Fetch URLs с SSRF защитой.
    blocked_hosts: HashSet<String>,
    allowed_schemes: HashSet<String>,
    blocked_ranges: Vec<ipnet::IpNet>,
}

impl SafeURLFetcher {
    fn new() -> Self {
        let blocked_hosts = HashSet::from([
            "localhost".into(), "127.0.0.1".into(),
            "0.0.0.0".into(), "internal-api".into(),
        ]);
        let allowed_schemes = HashSet::from(["http".into(), "https".into()]);
        let blocked_ranges = vec![
            "10.0.0.0/8".parse().unwrap(),
            "172.16.0.0/12".parse().unwrap(),
            "192.168.0.0/16".parse().unwrap(),
            "127.0.0.0/8".parse().unwrap(),
        ];
        Self { blocked_hosts, allowed_schemes, blocked_ranges }
    }

    /// Проверка безопасен ли URL для fetch.
    fn is_safe_url(&self, url_str: &str) -> bool {
        let parsed = match Url::parse(url_str) {
            Ok(u) => u,
            Err(_) => return false,
        };

        // Проверяем scheme
        if !self.allowed_schemes.contains(parsed.scheme()) {
            return false;
        }

        // Проверяем hostname
        let hostname = match parsed.host_str() {
            Some(h) => h.to_lowercase(),
            None => return false,
        };
        if self.blocked_hosts.contains(&hostname) {
            return false;
        }

        // Проверяем IP ranges
        if let Ok(ip) = hostname.parse::<IpAddr>() {
            for blocked_range in &self.blocked_ranges {
                if blocked_range.contains(&ip) {
                    return false;
                }
            }
        }

        true
    }
}
```

---

### 4. Command Injection

```rust
// Опасно: LLM output используется в shell commands
let user_request = "Convert image.jpg to PNG; rm -rf /";

let llm_suggestion = llm.generate(&format!("Suggest command for: {}", user_request));
// LLM: "convert image.jpg image.png; rm -rf /"

std::process::Command::new("sh").arg("-c").arg(&llm_suggestion).status(); // Command Injection!
```

**Безопасная реализация:**

```rust
use std::collections::HashMap;
use std::process::Command;

struct SafeCommandExecutor {
    /// Выполнение команд со строгой валидацией.
    allowed_commands: HashMap<String, Vec<String>>,
}

impl SafeCommandExecutor {
    fn new() -> Self {
        let mut allowed = HashMap::new();
        allowed.insert("convert".into(), vec!["-resize".into(), "-quality".into()]);
        allowed.insert("ffmpeg".into(), vec!["-i".into(), "-c:v".into(), "-c:a".into()]);
        Self { allowed_commands: allowed }
    }

    /// Parse и безопасное выполнение LLM-suggested команды.
    fn execute(&self, llm_command: &str) -> Result<String, String> {
        // Parse команду
        let parts: Vec<&str> = shell_words::split(llm_command)
            .map_err(|e| format!("Parse error: {}", e))?
            .iter().map(|s| s.as_str()).collect::<Vec<_>>();

        if parts.is_empty() {
            return Err("Empty command".to_string());
        }

        let command = parts[0];
        let args = &parts[1..];

        // Validate команду
        let allowed_flags = match self.allowed_commands.get(command) {
            Some(flags) => flags,
            None => return Err(format!("Command not allowed: {}", command)),
        };

        // Validate аргументы
        for arg in args {
            if arg.starts_with('-') {
                let flag = arg.split('=').next().unwrap_or(arg);
                if !allowed_flags.contains(&flag.to_string()) {
                    return Err(format!("Flag not allowed: {}", arg));
                }
            }
        }

        // Выполняем безопасно без shell
        let output = Command::new(command)
            .args(args)
            .output()
            .map_err(|e| e.to_string())?;

        Ok(String::from_utf8_lossy(&output.stdout).to_string())
    }
}
```

---

## SENTINEL Integration

```rust
use sentinel_core::engines::SentinelEngine;

let engine = SentinelEngine::new();

// Сканирование LLM output перед передачей в downstream системы
let result = engine.analyze(&llm_response);
if result.detected {
    log::warn!(
        "Improper output обнаружен: risk={}, categories={:?}, time={}μs",
        result.risk_score, result.categories, result.processing_time_us
    );
    // Блокировка или санитизация output
}
```

---

## Стратегии защиты Summary

| Атака | Защита | Реализация |
|-------|--------|------------|
| XSS | HTML escaping, CSP | `bleach`, Content-Security-Policy |
| SQLi | Parameterized queries | SQLAlchemy, prepared statements |
| SSRF | URL allowlisting | IP range blocking, scheme validation |
| Command Injection | Argument allowlisting | subprocess without shell |
| Data Leakage | Output scanning | PII detection, secret patterns |

---

## Ключевые выводы

1. **Никогда не доверяйте LLM output** - Обращайтесь как с untrusted user input
2. **Context-aware sanitization** - Разные контексты требуют разного escaping
3. **Defense in depth** - Множество слоёв валидации
4. **Least privilege** - Минимизируйте downstream permissions
5. **Monitor and log** - Отслеживайте все output-related security events

---

*AI Security Academy | Урок 02.1.5*
