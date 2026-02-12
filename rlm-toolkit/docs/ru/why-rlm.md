# Почему RLM-Toolkit?

Возможно, вы думаете: **зачем мне RLM-Toolkit вместо LangChain, LlamaIndex или просто прямых API-вызовов?**

Отличный вопрос. Давайте честно о плюсах и минусах.

---

## 🤔 Для кого RLM-Toolkit?

### ✅ RLM подойдёт, если вы:

- Хотите **простой код**, который легко дебажить
- Нужны **встроенные функции безопасности** production-уровня
- Важна обработка **бесконечного контекста** ([InfiniRetri](./glossary.md#infiniretri))
- Хотите **человекоподобную память** ([H-MEM](./glossary.md#hmem))
- Строите ИИ, который **улучшает сам себя** (Self-Evolving)
- Работаете в **security-чувствительных** средах

### ❌ RLM может НЕ подойти, если:

- Нужна **самая большая экосистема** с максимумом интеграций (тут LangChain лидирует)
- Зависите от **специфичных инструментов** сообщества LangChain
- Просто **экспериментируете** и production не важен

---

## 📊 Честное сравнение

| Функция | RLM-Toolkit | LangChain | Прямой OpenAI API |
|---------|-------------|-----------|-------------------|
| **Кривая обучения** | 🟢 Простая | 🟡 Средняя | 🟢 Простая |
| **Сложность кода** | 🟢 Минимум | 🔴 Много | 🟢 Минимум |
| **Отладка** | 🟢 Легко | 🔴 Сложно (chains) | 🟢 Легко |
| **Системы памяти** | 🟢 Продвинутые | 🟡 Базовые | 🔴 Вручную |
| **Бесконечный контекст** | 🟢 InfiniRetri | 🟡 Ручной RAG | 🔴 Нет |
| **Безопасность** | 🟢 Встроенная | 🟡 Дополнения | 🔴 Вручную |
| **Интеграции** | 🟡 50+ | 🟢 700+ | 🔴 1 |

---

## 🎯 Покажи код

### Простой чат

**RLM-Toolkit (3 строки):**
```python
from rlm_toolkit import RLM

rlm = RLM.from_openai("gpt-4o")
response = rlm.run("Привет!")
```

**LangChain (7+ строк):**
```python
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

llm = ChatOpenAI(model="gpt-4o")
messages = [HumanMessage(content="Привет!")]
response = llm.invoke(messages)
print(response.content)
```

**50% меньше кода. Тот же результат.**

---

### RAG сравнение

**RLM-Toolkit (5 строк):**
```python
from rlm_toolkit import RLM, RLMConfig

config = RLMConfig(use_infiniretri=True)
rlm = RLM.from_openai("gpt-4o", config=config)
rlm.add_documents("docs/")
response = rlm.run("Что говорится в документе о X?")
```

**LangChain (20+ строк):**
```python
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.document_loaders import DirectoryLoader
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA

# Загрузка документов
loader = DirectoryLoader("docs/")
documents = loader.load()

# Разбиение
splitter = RecursiveCharacterTextSplitter(chunk_size=1000)
chunks = splitter.split_documents(documents)

# Эмбеддинги и хранилище
embeddings = OpenAIEmbeddings()
vectorstore = Chroma.from_documents(chunks, embeddings)

# Создание цепочки
llm = ChatOpenAI(model="gpt-4o")
qa = RetrievalQA.from_chain_type(llm, retriever=vectorstore.as_retriever())

# Запрос
response = qa.invoke("Что говорится в документе о X?")
```

---

## 🔒 Безопасность в первую очередь

RLM-Toolkit создан командой **SENTINEL** — экспертами в AI-безопасности.

> **Кто такие SENTINEL?** Команда исследователей и разработчиков, специализирующаяся на защите AI-систем. Наши инструменты используются для обнаружения уязвимостей, защиты от prompt injection и обеспечения безопасности LLM-приложений.

| Функция безопасности | RLM | LangChain |
|---------------------|-----|-----------|
| Детекция prompt injection | ✅ Встроено | ❌ Дополнение |
| Мультитенантная изоляция | ✅ TrustZones | ❌ Вручную |
| Аудит-логирование | ✅ Встроено | ❌ Вручную |
| Red team тестирование | ✅ Встроено | ❌ Нет |

---

## 🧠 Уникальные возможности

То, что **нельзя легко сделать** с другими фреймворками:

### 1. InfiniRetri — Бесконечный контекст
Обрабатывайте документы **любого размера** без лимитов контекста. Подробнее в [Глоссарии →](./glossary.md#infiniretri)

### 2. H-MEM — Человекоподобная память
Память, которая имитирует работу человеческого мозга. Подробнее в [Глоссарии →](./glossary.md#hmem)

### 3. Self-Evolving LLMs
ИИ, который критикует и улучшает собственные выводы.

---

## 📈 Когда что выбрать

```
┌─────────────────────────────────────────────────────────────┐
│                    Дерево решений                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Просто экспериментируете? ────────────► Raw API            │
│         │                                                   │
│         ▼                                                   │
│  Нужно много интеграций? ──────────────► LangChain          │
│         │                                                   │
│         ▼                                                   │
│  Строите production-приложение? ───────► RLM-Toolkit        │
│         │                                                   │
│         ▼                                                   │
│  Критична безопасность? ───────────────► RLM-Toolkit ✓      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎓 Начать

Готовы попробовать? Начните здесь:

1. **[Быстрый старт](./quickstart.md)** — 5 минут до первого приложения
2. **[Глоссарий](./glossary.md)** — Понять терминологию
3. **[Первый туториал](./tutorials/01-first-app.md)** — Пошаговое руководство

---

## См. также

- [Миграция](./migration.md) — Переходите с LangChain?
- [Концепции](./concepts/overview.md) — Глубокое погружение в архитектуру
- [Примеры](./examples/) — 150+ production-примеров
