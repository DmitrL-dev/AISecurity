# 🔌 Plugin System

> Расширение SENTINEL без изменения исходного кода

---

## Что такое плагины?

Плагины позволяют:
- 📦 Добавлять собственные движки
- 🔧 Модифицировать поведение
- 📊 Интегрировать с системами мониторинга
- 🔐 Добавлять корпоративную логику

**Всё это БЕЗ изменения кода SENTINEL!**

---

## Hook System

SENTINEL использует [pluggy](https://pluggy.readthedocs.io/) — ту же систему, что и pytest.

### Доступные хуки

```
┌─────────────────────────────────────────────────────────────┐
│                      Жизненный цикл                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  sentinel_configure        ← Конфигурация                   │
│         │                                                   │
│         ▼                                                   │
│  sentinel_register_engines ← Регистрация движков            │
│  sentinel_register_rules   ← Регистрация правил             │
│         │                                                   │
│         ▼                                                   │
│  sentinel_before_analysis  ← ДО анализа                     │
│         │                                                   │
│         ▼                                                   │
│    [Анализ движками]                                        │
│         │                                                   │
│         ▼                                                   │
│  sentinel_on_finding       ← На каждый finding              │
│         │                                                   │
│         ▼                                                   │
│  sentinel_after_analysis   ← ПОСЛЕ анализа                  │
│         │                                                   │
│         ▼                                                   │
│  sentinel_on_threat        ← При обнаружении угрозы         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Таблица хуков

| Хук | Аргументы | Возврат | Описание |
|-----|-----------|---------|----------|
| `sentinel_configure` | `config: dict` | `dict?` | Модификация конфига |
| `sentinel_register_engines` | — | `list[type]` | Список классов движков |
| `sentinel_register_rules` | — | `list[dict]` | YAML правила |
| `sentinel_before_analysis` | `context` | `context?` | Препроцессинг |
| `sentinel_after_analysis` | `context, results` | `results?` | Постпроцессинг |
| `sentinel_on_finding` | `finding` | `finding?` | Фильтрация/модификация |
| `sentinel_on_threat` | `context, results` | — | Алертинг |
| `sentinel_format_output` | `results, format` | `str?` | Кастомный формат |

---

## Создание плагина

### Минимальный плагин

```python
from sentinel.hooks import hookimpl


class MyPlugin:
    """Мой первый плагин."""
    
    @hookimpl
    def sentinel_before_analysis(self, context):
        """Препроцессинг: убираем лишние пробелы."""
        context.prompt = context.prompt.strip()
        return context
```

### Полный плагин

```python
from sentinel.hooks import hookimpl
from sentinel.core.finding import Severity
import logging

logger = logging.getLogger(__name__)


class EnterpriseSecurityPlugin:
    """
    Корпоративный плагин безопасности.
    
    Возможности:
    - Кастомные движки
    - Фильтрация findings
    - Интеграция с SIEM
    - Аудит логирование
    """
    
    def __init__(self, siem_endpoint: str = None):
        self.siem_endpoint = siem_endpoint
    
    @hookimpl
    def sentinel_configure(self, config: dict):
        """Добавляем корпоративные настройки."""
        config["enterprise_mode"] = True
        config["audit_logging"] = True
        return config
    
    @hookimpl
    def sentinel_register_engines(self):
        """Регистрируем корпоративные движки."""
        from .engines import (
            CompanyPolicyEngine,
            InternalDocsDetector,
            VIPClientProtector,
        )
        return [
            CompanyPolicyEngine,
            InternalDocsDetector,
            VIPClientProtector,
        ]
    
    @hookimpl
    def sentinel_register_rules(self):
        """Добавляем корпоративные правила."""
        return [
            {
                "id": "corp-001",
                "name": "Block internal codenames",
                "pattern": r"project\s+(alpha|omega|delta)",
                "severity": "critical",
            },
            {
                "id": "corp-002", 
                "name": "Protect VIP names",
                "pattern": r"клиент\s+(Иванов|Петров)",
                "severity": "high",
            },
        ]
    
    @hookimpl
    def sentinel_before_analysis(self, context):
        """Аудит входящих запросов."""
        logger.info(
            f"[AUDIT] User={context.user_id}, "
            f"Session={context.session_id}, "
            f"Prompt length={len(context.prompt)}"
        )
        
        # Добавляем метаданные
        context.metadata["audit_timestamp"] = time.time()
        context.metadata["source_ip"] = self._get_source_ip()
        
        return context
    
    @hookimpl
    def sentinel_on_finding(self, finding):
        """Фильтрация и обогащение findings."""
        # Игнорируем INFO в production
        if finding.severity == Severity.INFO:
            return None  # Отбрасываем
        
        # Добавляем корпоративные метаданные
        finding.metadata["reviewed_by"] = "enterprise_plugin"
        finding.metadata["policy_id"] = self._get_policy_id(finding)
        
        return finding
    
    @hookimpl
    def sentinel_on_threat(self, context, results):
        """Отправка алертов в SIEM."""
        if self.siem_endpoint:
            self._send_to_siem(context, results)
        
        # Email для критических угроз
        max_severity = max(
            r.max_severity for r in results 
            if r.max_severity
        )
        if max_severity == Severity.CRITICAL:
            self._send_critical_alert(context, results)
    
    @hookimpl
    def sentinel_after_analysis(self, context, results):
        """Финальный аудит."""
        total_findings = sum(r.finding_count for r in results)
        is_safe = all(r.is_safe for r in results)
        
        logger.info(
            f"[AUDIT] Request={context.request_id}, "
            f"Safe={is_safe}, Findings={total_findings}"
        )
        
        return results
    
    def _send_to_siem(self, context, results):
        """Отправка в SIEM (Splunk, ELK, etc.)."""
        import requests
        
        event = {
            "timestamp": time.time(),
            "user_id": context.user_id,
            "request_id": context.request_id,
            "is_safe": all(r.is_safe for r in results),
            "findings": [
                f.to_dict() 
                for r in results 
                for f in r.findings.findings
            ],
        }
        
        requests.post(self.siem_endpoint, json=event)
    
    def _send_critical_alert(self, context, results):
        """Email для критических угроз."""
        # Интеграция с PagerDuty, Slack, etc.
        pass
```

---

## Регистрация плагинов

### Способ 1: Entry Points (pip установка)

**pyproject.toml вашего пакета:**

```toml
[project.entry-points."sentinel.plugins"]
my_plugin = "my_package:MyPlugin"
enterprise = "my_package.enterprise:EnterprisePlugin"
```

**Установка:**

```bash
pip install my-sentinel-plugin
# Плагин автоматически загружается!
```

### Способ 2: Локальный файл

Создайте `sentinel_plugins.py` в рабочей директории:

```python
# sentinel_plugins.py
from sentinel.hooks import hookimpl


class LocalPlugin:
    @hookimpl
    def sentinel_before_analysis(self, context):
        print(f"Анализируем: {context.prompt[:50]}...")
        return context


class AnotherLocalPlugin:
    @hookimpl
    def sentinel_on_threat(self, context, results):
        print("⚠️ УГРОЗА ОБНАРУЖЕНА!")
```

### Способ 3: Программная регистрация

```python
from sentinel.hooks.manager import get_plugin_manager

pm = get_plugin_manager()
pm.register(MyPlugin(), "my_plugin")
```

---

## Порядок выполнения

Хуки выполняются в порядке регистрации плагинов:

```
Plugin A: before_analysis
Plugin B: before_analysis
Plugin C: before_analysis
    ↓
  [Анализ]
    ↓
Plugin A: after_analysis
Plugin B: after_analysis
Plugin C: after_analysis
```

**Для изменения порядка используйте приоритет:**

```python
@hookimpl(tryfirst=True)  # Выполняется первым
def sentinel_before_analysis(self, context):
    ...

@hookimpl(trylast=True)   # Выполняется последним
def sentinel_after_analysis(self, context, results):
    ...
```

---

## Примеры использования

### Логирование всех запросов

```python
class LoggingPlugin:
    @hookimpl
    def sentinel_before_analysis(self, context):
        logging.info(f"Request: {context.request_id}")
    
    @hookimpl
    def sentinel_after_analysis(self, context, results):
        logging.info(f"Result: safe={results[0].is_safe}")
```

### Фильтрация false positives

```python
class FilterPlugin:
    WHITELIST = ["безопасное слово", "разрешённый паттерн"]
    
    @hookimpl
    def sentinel_on_finding(self, finding):
        if any(w in finding.title for w in self.WHITELIST):
            return None  # Отбрасываем
        return finding
```

### Интеграция с Prometheus

```python
from prometheus_client import Counter, Histogram

requests_total = Counter('sentinel_requests_total', 'Total requests')
threats_total = Counter('sentinel_threats_total', 'Total threats')
latency = Histogram('sentinel_latency_seconds', 'Latency')


class PrometheusPlugin:
    @hookimpl
    def sentinel_before_analysis(self, context):
        requests_total.inc()
        context.metadata["start_time"] = time.time()
    
    @hookimpl
    def sentinel_after_analysis(self, context, results):
        duration = time.time() - context.metadata["start_time"]
        latency.observe(duration)
        
        if not all(r.is_safe for r in results):
            threats_total.inc()
```

---

## Отладка плагинов

```python
import logging
logging.basicConfig(level=logging.DEBUG)

from sentinel.hooks.manager import get_plugin_manager

pm = get_plugin_manager()
print("Зарегистрированные плагины:")
for name in pm.list_plugins():
    print(f"  - {name}")
```

---

<p align="center">
  <strong>Расширяйте SENTINEL под свои нужды! 🔌</strong>
</p>
