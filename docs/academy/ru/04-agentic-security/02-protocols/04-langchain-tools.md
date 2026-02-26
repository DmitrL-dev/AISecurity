# Безопасность инструментов LangChain

> **Уровень:** Средний | **Время:** 35 мин | **Трек:** 04 | **Модуль:** 04.2

---

## 1. Обзор инструментов LangChain

LangChain предоставляет структурированные интерфейсы инструментов для LLM-агентов.

```python
from langchain.tools import BaseTool, tool
from pydantic import BaseModel, Field

class SearchInput(BaseModel):
    query: str = Field(description="Поисковый запрос")

class SecureSearchTool(BaseTool):
    name = "search"
    description = "Поиск в базе знаний"
    args_schema = SearchInput
    
    def _run(self, query: str) -> str:
        # Валидация
        if not self._validate_query(query):
            return "Недопустимый запрос"
        return self._perform_search(query)
    
    def _validate_query(self, query: str) -> bool:
        # Проверка на паттерны инъекций
        dangerous = ["ignore previous", "system:", "admin"]
        return not any(d in query.lower() for d in dangerous)
```

---

## 2. Угрозы безопасности

```
Угрозы инструментов LangChain:
├── Путаница инструментов (вызван неправильный инструмент)
├── Инъекция параметров (вредоносные аргументы)
├── Манипуляция цепочками (изменение потока выполнения)
└── Отравление памяти (повреждение памяти агента)
```

---

## 3. Безопасная реализация инструментов

```python
class SecureToolExecutor:
    def __init__(self, allowed_tools: list):
        self.tools = {t.name: t for t in allowed_tools}
        self.audit_log = []
    
    def execute(self, tool_name: str, args: dict, context: dict) -> str:
        # 1. Проверка существования инструмента
        if tool_name not in self.tools:
            raise SecurityError(f"Неизвестный инструмент: {tool_name}")
        
        tool = self.tools[tool_name]
        
        # 2. Валидация аргументов по схеме
        validated = tool.args_schema(**args)
        
        # 3. Проверка разрешений
        if not self._check_permission(tool_name, context):
            raise PermissionError("Доступ запрещён")
        
        # 4. Выполнение с аудитом
        self.audit_log.append({
            "tool": tool_name, "args": args, 
            "user": context.get("user_id")
        })
        
        return tool._run(**validated.dict())
```

---

## 4. Безопасность цепочек

```python
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate

class SecureChain:
    def __init__(self, llm, tools: list):
        self.llm = llm
        self.tool_executor = SecureToolExecutor(tools)
        self.max_iterations = 10
    
    def run(self, input_text: str, context: dict) -> str:
        # Санитизация ввода
        sanitized = self._sanitize_input(input_text)
        
        iterations = 0
        while iterations < self.max_iterations:
            # Получение ответа LLM
            response = self.llm.invoke(sanitized)
            
            # Проверка на вызов инструмента
            if tool_call := self._extract_tool_call(response):
                result = self.tool_executor.execute(
                    tool_call["name"], 
                    tool_call["args"], 
                    context
                )
                sanitized = f"{sanitized}\nРезультат инструмента: {result}"
            else:
                return response
            
            iterations += 1
        
        raise SecurityError("Превышено максимальное количество итераций")
```

---

## 5. Итоги

1. **Валидация:** Валидация параметров на основе схем
2. **Разрешения:** Контроль доступа на уровне инструментов  
3. **Аудит:** Логирование всех вызовов инструментов
4. **Лимиты:** Ограничения итераций и ресурсов

---

*AI Security Academy | Трек 04: Agentic Security | Модуль 04.2: Протоколы*
