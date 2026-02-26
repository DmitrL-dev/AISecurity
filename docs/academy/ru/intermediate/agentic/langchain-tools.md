# Безопасность инструментов LangChain

> **Уровень:** Средний | **Время:** 35 мин | **Трек:** 04 | **Модуль:** 04.2

---

## 1. Обзор инструментов LangChain

LangChain предоставляет структурированные интерфейсы инструментов для LLM-агентов.

```rust
use serde::Deserialize;

#[derive(Deserialize)]
struct SearchInput {
    /// Поисковый запрос
    query: String,
}

struct SecureSearchTool;

impl SecureSearchTool {
    fn name(&self) -> &str { "search" }
    fn description(&self) -> &str { "Поиск в базе знаний" }

    fn run(&self, query: &str) -> String {
        // Валидация
        if !self.validate_query(query) {
            return "Недопустимый запрос".to_string();
        }
        self.perform_search(query)
    }

    fn validate_query(&self, query: &str) -> bool {
        // Проверка на паттерны инъекций
        let dangerous = ["ignore previous", "system:", "admin"];
        !dangerous.iter().any(|d| query.to_lowercase().contains(d))
    }
}
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

```rust
use std::collections::HashMap;

struct SecureToolExecutor {
    tools: HashMap<String, Box<dyn Tool>>,
    audit_log: Vec<serde_json::Value>,
}

impl SecureToolExecutor {
    fn new(allowed_tools: Vec<Box<dyn Tool>>) -> Self {
        let tools = allowed_tools.into_iter()
            .map(|t| (t.name().to_string(), t))
            .collect();
        Self { tools, audit_log: vec![] }
    }

    fn execute(&mut self, tool_name: &str, args: &serde_json::Value, context: &serde_json::Value) -> Result<String, String> {
        // 1. Проверка существования инструмента
        let tool = self.tools.get(tool_name)
            .ok_or_else(|| format!("Неизвестный инструмент: {}", tool_name))?;

        // 2. Валидация аргументов по схеме
        // (schema validation handled by tool)

        // 3. Проверка разрешений
        if !self.check_permission(tool_name, context) {
            return Err("Доступ запрещён".to_string());
        }

        // 4. Выполнение с аудитом
        self.audit_log.push(serde_json::json!({
            "tool": tool_name, "args": args,
            "user": context.get("user_id")
        }));

        Ok(tool.run(args))
    }
}
```

---

## 4. Безопасность цепочек

```rust
struct SecureChain {
    llm: Box<dyn LlmProvider>,
    tool_executor: SecureToolExecutor,
    max_iterations: usize,
}

impl SecureChain {
    fn new(llm: Box<dyn LlmProvider>, tools: Vec<Box<dyn Tool>>) -> Self {
        Self {
            llm,
            tool_executor: SecureToolExecutor::new(tools),
            max_iterations: 10,
        }
    }

    fn run(&mut self, input_text: &str, context: &serde_json::Value) -> Result<String, String> {
        // Санитизация ввода
        let mut sanitized = self.sanitize_input(input_text);

        let mut iterations = 0;
        while iterations < self.max_iterations {
            // Получение ответа LLM
            let response = self.llm.invoke(&sanitized);

            // Проверка на вызов инструмента
            if let Some(tool_call) = self.extract_tool_call(&response) {
                let result = self.tool_executor.execute(
                    tool_call["name"].as_str().unwrap_or(""),
                    &tool_call["args"],
                    context,
                )?;
                sanitized = format!("{}\nРезультат инструмента: {}", sanitized, result);
            } else {
                return Ok(response);
            }

            iterations += 1;
        }

        Err("Превышено максимальное количество итераций".to_string())
    }
}
```

---

## 5. Итоги

1. **Валидация:** Валидация параметров на основе схем
2. **Разрешения:** Контроль доступа на уровне инструментов  
3. **Аудит:** Логирование всех вызовов инструментов
4. **Лимиты:** Ограничения итераций и ресурсов

---

*AI Security Academy | Трек 04: Agentic Security | Модуль 04.2: Протоколы*
