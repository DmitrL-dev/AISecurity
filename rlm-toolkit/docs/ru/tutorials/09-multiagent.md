# Туториал 9: Многоагентные системы

Создавайте децентрализованные P2P многоагентные системы с зонами доверия на основе архитектуры Meta Matrix.

## Что такое Multi-Agent?

Многоагентная система RLM-Toolkit обеспечивает:

- **Децентрализованный P2P**: Без узкого места центрального оркестратора
- **Зоны доверия**: Изоляция памяти и безопасность
- **Message-Driven**: Асинхронная коммуникация между агентами
- **Self-Evolving агенты**: Агенты, которые улучшаются со временем

## Архитектура Multi-Agent

```
┌─────────────────────────────────────────────────────────────────┐
│                    Архитектура Meta Matrix                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│    Агент A ←──────→ Агент B                                      │
│       ↑                ↑                                        │
│       ↓                ↓                                        │
│    Агент C ←──────→ Агент D                                      │
│                                                                  │
│  • P2P обмен сообщениями (без центрального оркестратора)        │
│  • Каждый агент имеет свою память + общий пул                   │
│  • Зоны доверия контролируют видимость                          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Предварительные требования

```bash
pip install rlm-toolkit[all]
export OPENAI_API_KEY=your-key
```

## Шаг 1: Создание базовых агентов

```python
from rlm_toolkit.agents import Agent, AgentConfig

# Создаём агента-исследователя
researcher = Agent(
    name="researcher",
    role="Специалист по исследованиям",
    goal="Находить точную информацию из множества источников",
    llm="gpt-4o"
)

# Создаём агента-писателя
writer = Agent(
    name="writer", 
    role="Автор контента",
    goal="Создавать чёткий, вовлекающий контент",
    llm="gpt-4o"
)

# Создаём агента-рецензента
reviewer = Agent(
    name="reviewer",
    role="Рецензент качества",
    goal="Обеспечивать точность и качество",
    llm="gpt-4o"
)
```

## Шаг 2: Создание Multi-Agent Runtime

```python
from rlm_toolkit.agents import MultiAgentRuntime

# Создаём runtime
runtime = MultiAgentRuntime()

# Регистрируем агентов
runtime.register(researcher)
runtime.register(writer)
runtime.register(reviewer)

# Запускаем задачу
result = runtime.run(
    task="Написать комплексную статью о квантовых вычислениях",
    workflow=[
        {"agent": "researcher", "action": "исследовать тему"},
        {"agent": "writer", "action": "написать статью"},
        {"agent": "reviewer", "action": "проверить и предложить улучшения"},
        {"agent": "writer", "action": "учесть обратную связь"}
    ]
)

print(result.final_output)
```

## Шаг 3: Message-Driven коммуникация

```python
from rlm_toolkit.agents import Agent, AgentMessage, MessageQueue

# Создаём очередь сообщений
queue = MessageQueue()

# Агенты общаются через сообщения
researcher = Agent(name="researcher", message_queue=queue)
writer = Agent(name="writer", message_queue=queue)

# Отправляем сообщение
researcher.send(AgentMessage(
    to="writer",
    content="Вот результаты исследования: ...",
    metadata={"sources": ["arxiv", "wikipedia"]}
))

# Писатель получает и обрабатывает
message = writer.receive()
response = writer.process(message)
```

## Шаг 4: Зоны доверия

```python
from rlm_toolkit.agents import SecureAgent, TrustZone

# Определяем зоны доверия
public_zone = TrustZone(name="public", level=0)
internal_zone = TrustZone(name="internal", level=1)
confidential_zone = TrustZone(name="confidential", level=2)

# Создаём агентов в разных зонах
public_agent = SecureAgent(
    name="public_helper",
    trust_zone=public_zone
)

internal_agent = SecureAgent(
    name="internal_processor",
    trust_zone=internal_zone
)

confidential_agent = SecureAgent(
    name="data_handler",
    trust_zone=confidential_zone,
    encryption_enabled=True
)

# Агенты могут общаться только в пределах или выше своего уровня доверия
# confidential может общаться со всеми
# internal может общаться с internal и public
# public может общаться только с public
```

## Шаг 5: Self-Evolving агенты

```python
from rlm_toolkit.agents import EvolvingAgent

# Создаём агента, который улучшается со временем
evolving = EvolvingAgent(
    name="learning_agent",
    role="Адаптивный решатель задач",
    evolution_strategy="challenger_solver",
    meta_store_path="./agent_evolution"
)

# Агент учится из каждого взаимодействия
for task in tasks:
    result = evolving.run(task)
    # Агент сохраняет успешные паттерны
    
# Последующие взаимодействия получают пользу от обучения
```

## Шаг 6: Безопасные эволюционирующие агенты

Комбинация безопасности и эволюции:

```python
from rlm_toolkit.agents import SecureEvolvingAgent, TrustZone

# Агент с безопасностью и самосовершенствованием
agent = SecureEvolvingAgent(
    name="secure_evolution",
    trust_zone=TrustZone(name="confidential", level=2),
    encryption_enabled=True,
    evolution_strategy="challenger_solver",
    h_mem_enabled=True  # Использовать иерархическую память
)

# Безопасный, персистентный и улучшающийся
result = agent.run("Проанализировать чувствительные финансовые данные")
```

## Шаг 7: Реестр и обнаружение агентов

```python
from rlm_toolkit.agents import AgentRegistry, MultiAgentRuntime

# Создаём реестр
registry = AgentRegistry()

# Регистрируем агентов со способностями
registry.register(
    Agent(name="math_expert"),
    capabilities=["calculation", "statistics", "algebra"]
)

registry.register(
    Agent(name="code_expert"),
    capabilities=["python", "javascript", "debugging"]
)

registry.register(
    Agent(name="writer"),
    capabilities=["writing", "editing", "summarization"]
)

# Runtime обнаруживает агентов по способностям
runtime = MultiAgentRuntime(registry=registry)

# Автоматически выбирает подходящих агентов
result = runtime.run(
    "Рассчитать статистику по этим данным, затем написать отчёт",
    auto_select=True  # Автовыбор по способностям
)
```

## Полное приложение: Исследовательская команда

```python
# research_team.py
from rlm_toolkit.agents import (
    Agent, SecureAgent, EvolvingAgent,
    MultiAgentRuntime, AgentRegistry, TrustZone
)
from rlm_toolkit.tools import WebSearch, Calculator, PythonREPL

class ResearchTeam:
    def __init__(self):
        self.registry = AgentRegistry()
        self._setup_agents()
        self.runtime = MultiAgentRuntime(registry=self.registry)
    
    def _setup_agents(self):
        # Лидер исследований - эволюционирующий с памятью
        research_lead = EvolvingAgent(
            name="research_lead",
            role="Лидер исследовательской команды",
            goal="Координировать исследования и синтезировать находки",
            llm="gpt-4o",
            tools=[WebSearch()],
            evolution_strategy="self_critique"
        )
        
        # Аналитик данных - с инструментами
        data_analyst = Agent(
            name="data_analyst",
            role="Специалист по анализу данных",
            goal="Анализировать данные и находить паттерны",
            llm="gpt-4o",
            tools=[Calculator(), PythonREPL(sandbox=True)]
        )
        
        # Писатель - фокус на коммуникации
        writer = Agent(
            name="writer",
            role="Технический писатель",
            goal="Создавать чёткие отчёты и документацию",
            llm="gpt-4o"
        )
        
        # Рецензент качества - безопасная зона
        reviewer = SecureAgent(
            name="reviewer",
            role="Контроль качества",
            goal="Обеспечивать точность и полноту",
            llm="gpt-4o",
            trust_zone=TrustZone(name="internal", level=1)
        )
        
        # Регистрируем со способностями
        self.registry.register(research_lead, 
            capabilities=["research", "coordination", "synthesis"])
        self.registry.register(data_analyst,
            capabilities=["data", "statistics", "analysis"])
        self.registry.register(writer,
            capabilities=["writing", "documentation", "reports"])
        self.registry.register(reviewer,
            capabilities=["review", "quality", "validation"])
    
    def research(self, topic: str) -> dict:
        """Провести комплексное исследование по теме."""
        
        workflow = [
            {"agent": "research_lead", "action": f"исследовать {topic} тщательно"},
            {"agent": "data_analyst", "action": "проанализировать количественные данные"},
            {"agent": "writer", "action": "написать комплексный отчёт"},
            {"agent": "reviewer", "action": "проверить на точность и полноту"},
            {"agent": "writer", "action": "учесть правки и финализировать"}
        ]
        
        result = self.runtime.run(
            task=f"Исследовать и составить отчёт по: {topic}",
            workflow=workflow
        )
        
        return {
            "report": result.final_output,
            "agents_used": result.agents_used,
            "iterations": result.workflow_iterations,
            "sources": result.sources
        }

def main():
    print("🔬 Многоагентная исследовательская команда")
    print("   На базе RLM-Toolkit\n")
    
    team = ResearchTeam()
    
    while True:
        topic = input("📝 Тема исследования: ").strip()
        
        if topic.lower() in ['выход', 'quit', 'exit']:
            break
        
        print("\n⏳ Команда работает...\n")
        
        result = team.research(topic)
        
        print(f"📄 Отчёт исследования:\n")
        print(result["report"])
        print(f"\n👥 Задействованные агенты: {', '.join(result['agents_used'])}")
        print(f"🔄 Итераций workflow: {result['iterations']}\n")

if __name__ == "__main__":
    main()
```

## Сравнение с другими фреймворками

| Функция | LangGraph | CrewAI | RLM Multi-Agent |
|---------|-----------|--------|-----------------|
| Архитектура | Централизованная | Централизованная | **Децентрализованная P2P** |
| Зоны доверия | ❌ | ❌ | ✅ |
| Self-Evolving | ❌ | ❌ | ✅ |
| Интеграция H-MEM | ❌ | ❌ | ✅ |
| Шифрование | ❌ | ❌ | ✅ |

## Лучшие практики

!!! tip "Специализация агентов"
    Создавайте агентов с конкретными, узкими ролями:
    ```python
    Agent(name="sql_expert", role="Специалист по базам данных")
    ```

!!! tip "Проектирование зон доверия"
    Используйте зоны доверия для безопасности:
    - Public: Агенты для пользователей
    - Internal: Агенты обработки
    - Confidential: Обработчики данных

!!! tip "Таймауты сообщений"
    Устанавливайте таймауты для коммуникации агентов:
    ```python
    runtime = MultiAgentRuntime(message_timeout=30)
    ```

!!! warning "Управление ресурсами"
    Мониторьте количество агентов и память:
    ```python
    runtime.get_stats()  # Проверить использование ресурсов
    ```

## Следующие шаги

- [Концепция: Архитектура Multi-Agent](../concepts/agents.md)
- [Концепция: Зоны доверия](../concepts/security.md)
- [API Reference: Агенты](../api/agents.md)
