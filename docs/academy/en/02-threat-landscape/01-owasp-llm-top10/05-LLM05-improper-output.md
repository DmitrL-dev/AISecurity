# LLM05: Improper Output Handling

> **Lesson:** 02.1.5 - Improper Output Handling  
> **OWASP ID:** LLM05  
> **Time:** 40 minutes  
> **Risk Level:** Medium-High

---

## Learning Objectives

By the end of this lesson, you will be able to:

1. Identify output handling vulnerabilities
2. Implement secure output processing
3. Detect and prevent downstream attacks
4. Design safe LLM integration patterns

---

## What is Improper Output Handling?

LLM outputs are often trusted and passed directly to downstream systems without validation. This creates vulnerabilities when LLM output contains:

| Content Type | Risk | Example |
|--------------|------|---------|
| **Code** | Code Injection | SQL, JavaScript, Shell |
| **Markup** | XSS, SSRF | HTML, Markdown links |
| **Data** | Data Leakage | PII, secrets, internal data |
| **Commands** | Command Injection | System calls, API calls |

---

## Attack Vectors

### 1. Cross-Site Scripting (XSS) via LLM

```python
# Unsafe: LLM output rendered directly in browser
user_message = "Generate a greeting for <script>stealCookies()</script>"

llm_response = llm.generate(user_message)
# Response might contain: "Hello, <script>stealCookies()</script>!"

# Vulnerable rendering
return f"<div>{llm_response}</div>"  # XSS!
```

**Secure Implementation:**

```python
from html import escape

def render_llm_output(response: str) -> str:
    """Safely render LLM output in HTML context."""
    # Escape HTML entities
    safe_response = escape(response)
    
    # Optionally allow safe markdown
    safe_response = allowed_markdown_to_html(safe_response)
    
    return f"<div class='llm-response'>{safe_response}</div>"
```

---

### 2. SQL Injection via LLM

```python
# Dangerous: Using LLM output in SQL query
user_request = "Show me all users named Robert'); DROP TABLE users;--"

llm_response = llm.generate(
    f"Generate SQL to find users: {user_request}"
)
# LLM might generate: SELECT * FROM users WHERE name = 'Robert'); DROP TABLE users;--'

# VULNERABLE CODE
cursor.execute(llm_response)  # SQL Injection!
```

**Secure Implementation:**

```python
from sqlalchemy import text

class SecureSQLGenerator:
    """Generate and validate SQL from LLM output."""
    
    ALLOWED_OPERATIONS = {"SELECT"}
    FORBIDDEN_KEYWORDS = {"DROP", "DELETE", "UPDATE", "INSERT", "TRUNCATE", "ALTER"}
    
    def __init__(self, db_session):
        self.session = db_session
    
    def execute_safe_query(self, llm_sql: str, params: dict = None):
        """Execute LLM-generated SQL safely."""
        
        # 1. Parse and validate SQL
        if not self._is_safe_query(llm_sql):
            raise SecurityError("Unsafe SQL detected")
        
        # 2. Use parameterized queries
        safe_sql = self._parameterize(llm_sql, params)
        
        # 3. Execute with read-only connection
        with self.session.begin_readonly():
            return self.session.execute(text(safe_sql), params)
    
    def _is_safe_query(self, sql: str) -> bool:
        sql_upper = sql.upper()
        
        # Check only allowed operations
        first_word = sql_upper.split()[0]
        if first_word not in self.ALLOWED_OPERATIONS:
            return False
        
        # Check for forbidden keywords
        for keyword in self.FORBIDDEN_KEYWORDS:
            if keyword in sql_upper:
                return False
        
        return True
```

---

### 3. Server-Side Request Forgery (SSRF)

```python
# Dangerous: LLM generates URLs that get fetched
user_input = "Summarize this article: http://internal-api:8080/admin/secrets"

llm_response = llm.generate(f"Fetch and summarize: {user_input}")

# LLM might extract the URL and system fetches it
url = extract_url(llm_response)
content = requests.get(url)  # SSRF - accessing internal resources!
```

**Secure Implementation:**

```python
import ipaddress
from urllib.parse import urlparse

class SafeURLFetcher:
    """Fetch URLs with SSRF protection."""
    
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
        """Check if URL is safe to fetch."""
        parsed = urlparse(url)
        
        # Check scheme
        if parsed.scheme not in self.ALLOWED_SCHEMES:
            return False
        
        # Check hostname
        hostname = parsed.hostname.lower()
        if hostname in self.BLOCKED_HOSTS:
            return False
        
        # Check IP ranges
        try:
            ip = ipaddress.ip_address(hostname)
            for blocked_range in self.blocked_ranges:
                if ip in blocked_range:
                    return False
        except ValueError:
            pass  # Not an IP, continue
        
        return True
    
    def safe_fetch(self, url: str) -> str:
        """Fetch URL only if safe."""
        if not self.is_safe_url(url):
            raise SecurityError(f"Blocked unsafe URL: {url}")
        
        return requests.get(url, timeout=10).text
```

---

### 4. Command Injection

```python
# Dangerous: LLM output used in shell commands
user_request = "Convert image.jpg to PNG; rm -rf /"

llm_suggestion = llm.generate(f"Suggest command for: {user_request}")
# LLM: "convert image.jpg image.png; rm -rf /"

os.system(llm_suggestion)  # Command Injection!
```

**Secure Implementation:**

```python
import subprocess
import shlex

class SafeCommandExecutor:
    """Execute commands with strict validation."""
    
    ALLOWED_COMMANDS = {
        "convert": {"allowed_flags": ["-resize", "-quality"]},
        "ffmpeg": {"allowed_flags": ["-i", "-c:v", "-c:a"]},
    }
    
    def execute(self, llm_command: str) -> str:
        """Parse and safely execute LLM-suggested command."""
        
        # Parse command
        parts = shlex.split(llm_command)
        
        if not parts:
            raise SecurityError("Empty command")
        
        command = parts[0]
        args = parts[1:]
        
        # Validate command
        if command not in self.ALLOWED_COMMANDS:
            raise SecurityError(f"Command not allowed: {command}")
        
        # Validate arguments
        allowed_flags = self.ALLOWED_COMMANDS[command]["allowed_flags"]
        for arg in args:
            if arg.startswith("-") and arg.split("=")[0] not in allowed_flags:
                raise SecurityError(f"Flag not allowed: {arg}")
        
        # Execute safely with no shell
        result = subprocess.run(
            [command] + args,
            capture_output=True,
            timeout=30,
            shell=False  # Critical: no shell interpretation
        )
        
        return result.stdout.decode()
```

---

## Output Sanitization Framework

### Comprehensive Sanitizer

```python
from dataclasses import dataclass
from typing import Callable, List, Optional
from enum import Enum

class OutputContext(Enum):
    HTML = "html"
    SQL = "sql"
    SHELL = "shell"
    URL = "url"
    JSON = "json"
    MARKDOWN = "markdown"

@dataclass
class SanitizationResult:
    original: str
    sanitized: str
    modifications: List[str]
    is_safe: bool
    context: OutputContext

class OutputSanitizer:
    """Context-aware output sanitization."""
    
    def __init__(self):
        self.sanitizers = {
            OutputContext.HTML: self._sanitize_html,
            OutputContext.SQL: self._sanitize_sql,
            OutputContext.SHELL: self._sanitize_shell,
            OutputContext.URL: self._sanitize_url,
            OutputContext.JSON: self._sanitize_json,
            OutputContext.MARKDOWN: self._sanitize_markdown,
        }
    
    def sanitize(self, output: str, context: OutputContext) -> SanitizationResult:
        """Sanitize output for specific context."""
        sanitizer = self.sanitizers.get(context)
        if not sanitizer:
            raise ValueError(f"Unknown context: {context}")
        
        return sanitizer(output)
    
    def _sanitize_html(self, output: str) -> SanitizationResult:
        """Sanitize for HTML context."""
        import bleach
        
        allowed_tags = ["p", "b", "i", "u", "a", "code", "pre", "ul", "ol", "li"]
        allowed_attrs = {"a": ["href", "title"]}
        
        sanitized = bleach.clean(
            output,
            tags=allowed_tags,
            attributes=allowed_attrs,
            strip=True
        )
        
        # Remove javascript: links
        sanitized = re.sub(r'href\s*=\s*["\']javascript:', 'href="#', sanitized)
        
        modifications = []
        if sanitized != output:
            modifications.append("Removed unsafe HTML tags/attributes")
        
        return SanitizationResult(
            original=output,
            sanitized=sanitized,
            modifications=modifications,
            is_safe=True,
            context=OutputContext.HTML
        )
    
    def _sanitize_sql(self, output: str) -> SanitizationResult:
        """Block dangerous SQL or extract safe parts."""
        forbidden = ["DROP", "DELETE", "UPDATE", "INSERT", "EXECUTE", "GRANT"]
        
        output_upper = output.upper()
        is_safe = not any(kw in output_upper for kw in forbidden)
        
        if not is_safe:
            return SanitizationResult(
                original=output,
                sanitized="",
                modifications=["Blocked dangerous SQL keywords"],
                is_safe=False,
                context=OutputContext.SQL
            )
        
        return SanitizationResult(
            original=output,
            sanitized=output,
            modifications=[],
            is_safe=True,
            context=OutputContext.SQL
        )
```

---

## SENTINEL Integration

```python
from sentinel import scan, OutputGuard

# Configure output protection
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
    """Protected LLM output processing."""
    return response

# Usage
try:
    safe_output = process_llm_response(llm_response, "html")
except OutputBlockedError as e:
    log_security_event(e)
    safe_output = "Response blocked for security reasons"
```

---

## Defense Strategies Summary

| Attack | Defense | Implementation |
|--------|---------|----------------|
| XSS | HTML escaping, CSP | `bleach`, Content-Security-Policy |
| SQLi | Parameterized queries | SQLAlchemy, prepared statements |
| SSRF | URL allowlisting | IP range blocking, scheme validation |
| Command Injection | Argument allowlisting | subprocess without shell |
| Data Leakage | Output scanning | PII detection, secret patterns |

---

## Key Takeaways

1. **Never trust LLM output** - Treat it as untrusted user input
2. **Context-aware sanitization** - Different contexts need different escaping
3. **Defense in depth** - Multiple layers of validation
4. **Least privilege** - Minimize downstream permissions
5. **Monitor and log** - Track all output-related security events

---

## Hands-On Exercises

1. Implement HTML output sanitizer
2. Build SQL validation layer
3. Create SSRF-protected URL fetcher
4. Test command injection defenses

---

*AI Security Academy | Lesson 02.1.5*
