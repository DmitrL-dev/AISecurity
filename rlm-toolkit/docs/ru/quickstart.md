# Быстрый старт

Запустите RLM-Toolkit за 5 минут.

## Установка

=== "Базовая"
    ```bash
    pip install rlm-toolkit
    ```

=== "Со всеми провайдерами"
    ```bash
    pip install rlm-toolkit[all]
    ```

=== "Разработка"
    ```bash
    git clone https://github.com/DmitrL-dev/AISecurity.git
    cd AISecurity/sentinel-community/rlm-toolkit
    pip install -e ".[dev]"
    ```

## Ваш первый RLM

```python
from rlm_toolkit import RLM

# Создаём RLM с OpenAI
rlm = RLM.from_openai("gpt-4o")

# Простой запрос
result = rlm.run("Объясни квантовые вычисления простыми словами")
print(result.final_answer)
```

!!! tip "API ключ"
    Установите ключ: `export OPENAI_API_KEY=your-key`

## С памятью

```python
from rlm_toolkit import RLM
from rlm_toolkit.memory import HierarchicalMemory

# Создаём RLM с памятью
memory = HierarchicalMemory()
rlm = RLM.from_openai("gpt-4o", memory=memory)

# Первый разговор
rlm.run("Меня зовут Алексей")

# Память сохраняется
result = rlm.run("Как меня зовут?")
print(result.final_answer)  # "Вас зовут Алексей"
```

## RAG Pipeline

```python
from rlm_toolkit import RLM
from rlm_toolkit.loaders import PDFLoader
from rlm_toolkit.vectorstores import ChromaVectorStore
from rlm_toolkit.embeddings import OpenAIEmbeddings

# Загружаем документы
docs = PDFLoader("отчёт.pdf").load()

# Создаём векторное хранилище
vectorstore = ChromaVectorStore.from_documents(
    docs, 
    OpenAIEmbeddings()
)

# Запрос с RAG
rlm = RLM.from_openai("gpt-4o", retriever=vectorstore.as_retriever())
result = rlm.run("Какие ключевые выводы?")
```

## Использование InfiniRetri

Для документов с 100K+ токенов:

```python
from rlm_toolkit import RLM, RLMConfig

config = RLMConfig(
    enable_infiniretri=True,
    infiniretri_threshold=50000
)

rlm = RLM.from_openai("gpt-4o", config=config)
result = rlm.run("Найди бюджет за Q3", context=massive_document)
```

## VS Code Extension (v1.2.1)

Установите расширение RLM-Toolkit для отслеживания экономии токенов:

1. Откройте VS Code Extensions
2. Поиск "RLM-Toolkit"
3. Install → Reload

**Функции Sidebar:**
- Статус сервера
- Трекер экономии токенов
- Быстрая переиндексация

## MCP Server

Для интеграции с IDE (Antigravity, Cursor, Claude Desktop):

```bash
pip install rlm-toolkit[mcp]
```

Настройте в `mcp_config.json`:
```json
{
  "mcpServers": {
    "rlm-toolkit": {
      "command": "python",
      "args": ["-m", "rlm_toolkit.mcp.server"]
    }
  }
}
```

→ [Полный туториал MCP](tutorials/10-mcp-server.md)

## Следующие шаги

- [Туториал: Создание чат-бота](tutorials/02-chatbot.md)
- [Туториал: RAG Pipeline](tutorials/03-rag.md)
- [Туториал: MCP Server](tutorials/10-mcp-server.md)
- [Концепция: C³ Crystal](concepts/crystal.md)
- [Концепция: InfiniRetri](concepts/infiniretri.md)
- [Концепция: H-MEM](concepts/hmem.md)
