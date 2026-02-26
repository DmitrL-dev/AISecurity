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

```python
# Небезопасно: LLM output рендерится напрямую в браузере
user_message = "Generate a greeting for <script>stealCookies()</script>"

llm_response = llm.generate(user_message)
# Response может содержать: "Hello, <script>stealCookies()</script>!"

# Уязвимый рендеринг
return f"<div>{llm_response}</div>"  # XSS!
```

**Безопасная реализация:**

```python
from html import escape

def render_llm_output(response: str) -> str:
    """Безопасный рендеринг LLM output в HTML контексте."""
    # Escape HTML entities
    safe_response = escape(response)
    
    # Опционально разрешаем safe markdown
    safe_response = allowed_markdown_to_html(safe_response)
    
    return f"<div class='llm-response'>{safe_response}</div>"
```

---

### 2. SQL Injection через LLM

```python
# Опасно: Использование LLM output в SQL query
user_request = "Show me all users named Robert'); DROP TABLE users;--"

llm_response = llm.generate(
    f"Generate SQL to find users: {user_request}"
)
# LLM может сгенерировать: SELECT * FROM users WHERE name = 'Robert'); DROP TABLE users;--'

# УЯЗВИМЫЙ КОД
cursor.execute(llm_response)  # SQL Injection!
```

**Безопасная реализация:**

```python
from sqlalchemy import text

class SecureSQLGenerator:
    """Генерация и валидация SQL из LLM output."""
    
    ALLOWED_OPERATIONS = {"SELECT"}
    FORBIDDEN_KEYWORDS = {"DROP", "DELETE", "UPDATE", "INSERT", "TRUNCATE", "ALTER"}
    
    def execute_safe_query(self, llm_sql: str, params: dict = None):
        """Безопасное выполнение LLM-сгенерированного SQL."""
        
        # 1. Parse и validate SQL
        if not self._is_safe_query(llm_sql):
            raise SecurityError("Unsafe SQL detected")
        
        # 2. Используем parameterized queries
        safe_sql = self._parameterize(llm_sql, params)
        
        # 3. Выполняем с read-only connection
        with self.session.begin_readonly():
            return self.session.execute(text(safe_sql), params)
    
    def _is_safe_query(self, sql: str) -> bool:
        sql_upper = sql.upper()
        
        # Проверяем только allowed operations
        first_word = sql_upper.split()[0]
        if first_word not in self.ALLOWED_OPERATIONS:
            return False
        
        # Проверяем на forbidden keywords
        for keyword in self.FORBIDDEN_KEYWORDS:
            if keyword in sql_upper:
                return False
        
        return True
```

---

### 3. Server-Side Request Forgery (SSRF)

```python
# Опасно: LLM генерирует URLs которые потом fetched
user_input = "Summarize this article: http://internal-api:8080/admin/secrets"

llm_response = llm.generate(f"Fetch and summarize: {user_input}")

# LLM может извлечь URL и система его fetch
url = extract_url(llm_response)
content = requests.get(url)  # SSRF - доступ к internal resources!
```

**Безопасная реализация:**

```python
import ipaddress
from urllib.parse import urlparse

class SafeURLFetcher:
    """Fetch URLs с SSRF защитой."""
    
    BLOCKED_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "internal-api"}
    ALLOWED_SCHEMES = {"http", "https"}
    
    def __init__(self):
        self.blocked_ranges = [
            ipaddress.ip_network("10.0.0.0/8"),
            ipaddress.ip_network("172.16.0.0/12"),
            ipaddress.ip_network("192.168.0.0/16"),
            ipaddress.ip_network("127.0.0.0/8"),
        ]
    
    def is_safe_url(self, url: str) -> bool:
        """Проверка безопасен ли URL для fetch."""
        parsed = urlparse(url)
        
        # Проверяем scheme
        if parsed.scheme not in self.ALLOWED_SCHEMES:
            return False
        
        # Проверяем hostname
        hostname = parsed.hostname.lower()
        if hostname in self.BLOCKED_HOSTS:
            return False
        
        # Проверяем IP ranges
        try:
            ip = ipaddress.ip_address(hostname)
            for blocked_range in self.blocked_ranges:
                if ip in blocked_range:
                    return False
        except ValueError:
            pass  # Not an IP, continue
        
        return True
```

---

### 4. Command Injection

```python
# Опасно: LLM output используется в shell commands
user_request = "Convert image.jpg to PNG; rm -rf /"

llm_suggestion = llm.generate(f"Suggest command for: {user_request}")
# LLM: "convert image.jpg image.png; rm -rf /"

os.system(llm_suggestion)  # Command Injection!
```

**Безопасная реализация:**

```python
import subprocess
import shlex

class SafeCommandExecutor:
    """Выполнение команд со строгой валидацией."""
    
    ALLOWED_COMMANDS = {
        "convert": {"allowed_flags": ["-resize", "-quality"]},
        "ffmpeg": {"allowed_flags": ["-i", "-c:v", "-c:a"]},
    }
    
    def execute(self, llm_command: str) -> str:
        """Parse и безопасное выполнение LLM-suggested команды."""
        
        # Parse команду
        parts = shlex.split(llm_command)
        
        if not parts:
            raise SecurityError("Empty command")
        
        command = parts[0]
        args = parts[1:]
        
        # Validate команду
        if command not in self.ALLOWED_COMMANDS:
            raise SecurityError(f"Command not allowed: {command}")
        
        # Validate аргументы
        allowed_flags = self.ALLOWED_COMMANDS[command]["allowed_flags"]
        for arg in args:
            if arg.startswith("-") and arg.split("=")[0] not in allowed_flags:
                raise SecurityError(f"Flag not allowed: {arg}")
        
        # Выполняем безопасно без shell
        result = subprocess.run(
            [command] + args,
            capture_output=True,
            timeout=30,
            shell=False  # Критично: без shell interpretation
        )
        
        return result.stdout.decode()
```

---

## SENTINEL Integration

```python
from sentinel import scan, OutputGuard

# Конфигурация output protection
output_guard = OutputGuard(
    contexts=[
        OutputContext.HTML,
        OutputContext.SQL,
        OutputContext.SHELL
    ],
    block_on_threat=True,
    sanitize_automatically=True
)

@output_guard
def process_llm_response(response: str, target_context: str):
    """Защищённая обработка LLM output."""
    return response

# Использование
try:
    safe_output = process_llm_response(llm_response, "html")
except OutputBlockedError as e:
    log_security_event(e)
    safe_output = "Response blocked for security reasons"
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
