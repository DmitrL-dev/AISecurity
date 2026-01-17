# Миграция: LangChain → RLM-Toolkit

Руководство для миграции существующего кода LangChain на RLM-Toolkit.

---

## 🎯 Краткая справка

| LangChain | RLM-Toolkit | Примечания |
|-----------|-------------|------------|
| `ChatOpenAI(model="gpt-4o")` | `RLM.from_openai("gpt-4o")` | Те же параметры |
| `ChatAnthropic(model="claude-3")` | `RLM.from_anthropic("claude-3-sonnet")` | Те же параметры |
| `llm.invoke(messages)` | `rlm.run(prompt)` | Проще API |
| `ConversationBufferMemory` | `BufferMemory` | Та же концепция |
| `RecursiveCharacterTextSplitter` | `RecursiveTextSplitter` | Те же параметры |
| `PyPDFLoader` | `PDFLoader` | Тот же интерфейс |
| `Chroma.from_documents()` | `ChromaVectorStore.from_documents()` | Тот же интерфейс |
| `RetrievalQA.from_chain_type()` | `RLMConfig(enable_infiniretri=True)` | Проще |
| `AgentExecutor` | `ReActAgent` | Похожий |
| `@tool` decorator | `@Tool(...)` decorator | Чище синтаксис |

---

## 📝 Примеры миграции

### 1. Базовый вызов LLM

**До (LangChain):**
```python
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

llm = ChatOpenAI(model="gpt-4o", temperature=0.7)
messages = [
    SystemMessage(content="Ты полезный ассистент."),
    HumanMessage(content="Что такое Python?")
]
response = llm.invoke(messages)
print(response.content)
```

**После (RLM-Toolkit):**
```python
from rlm_toolkit import RLM

rlm = RLM.from_openai("gpt-4o", temperature=0.7)
rlm.set_system_prompt("Ты полезный ассистент.")
response = rlm.run("Что такое Python?")
print(response)
```

**Строк кода:** 10 → 5 (**50% меньше**)

---

### 2. Чат-бот с памятью

**До (LangChain):**
```python
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain

llm = ChatOpenAI(model="gpt-4o")
memory = ConversationBufferMemory()
chain = ConversationChain(llm=llm, memory=memory)

response1 = chain.invoke({"input": "Меня зовут Алексей"})
response2 = chain.invoke({"input": "Как меня зовут?"})
```

**После (RLM-Toolkit):**
```python
from rlm_toolkit import RLM
from rlm_toolkit.memory import BufferMemory

rlm = RLM.from_openai("gpt-4o")
rlm.set_memory(BufferMemory())

response1 = rlm.run("Меня зовут Алексей")
response2 = rlm.run("Как меня зовут?")  # Помнит: "Алексей"
```

---

### 3. RAG пайплайн

**После (RLM-Toolkit):**
```python
from rlm_toolkit import RLM, RLMConfig
from rlm_toolkit.loaders import PDFLoader
from rlm_toolkit.vectorstores import ChromaVectorStore
from rlm_toolkit.embeddings import OpenAIEmbeddings

config = RLMConfig(enable_infiniretri=True)
rlm = RLM.from_openai("gpt-4o", config=config)

docs = PDFLoader("document.pdf").load()
vectorstore = ChromaVectorStore.from_documents(docs, OpenAIEmbeddings())
rlm.set_retriever(vectorstore.as_retriever(k=5))

result = rlm.run("Какая основная тема?")
```

**Сокращение кода:** 28 → 12 строк (**57% меньше**)

---

## 🔄 Постепенная миграция

Можно мигрировать постепенно — RLM и LangChain работают вместе:

```python
from langchain_openai import ChatOpenAI
from rlm_toolkit import RLM

# Старый код остаётся
langchain_llm = ChatOpenAI(model="gpt-4o")

# Новый код на RLM
rlm = RLM.from_openai("gpt-4o")

# Используем вместе
old_result = langchain_llm.invoke([...])
new_result = rlm.run("...")
```

---

## ⚠️ Важные отличия

| Аспект | LangChain | RLM-Toolkit |
|--------|-----------|-------------|
| **Формат сообщений** | `[HumanMessage(...)]` | Просто строки |
| **Композиция** | `chain1 \| chain2` | `pipeline.add_step()` |
| **Callbacks** | В каждом вызове | Задаются один раз |
| **Streaming** | `.stream()` метод | `stream=True` параметр |

---

## 🎓 После миграции

1. **[InfiniRetri](./concepts/infiniretri.md)** — Неограниченный контекст
2. **[H-MEM](./concepts/hmem.md)** — Человекоподобная память
3. **[Безопасность](./concepts/security.md)** — Встроенная защита

---

## См. также

- [Почему RLM?](./why-rlm.md) — Сравнение с альтернативами
- [API Reference](./reference/) — Полное API
- [Примеры](./examples/) — 150+ production-примеров
