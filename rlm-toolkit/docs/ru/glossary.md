# Глоссарий

<div class="glossary-page">

Добро пожаловать в глоссарий RLM-Toolkit! На этой странице объясняются все ключевые термины и концепции, используемые в документации.

<input type="text" class="glossary-search" placeholder="🔍 Поиск терминов..." aria-label="Поиск в глоссарии">

<div class="glossary-grid"></div>

</div>

---

## Базовые концепции

### LLM (Large Language Model)
Большая языковая модель — ИИ, обученный на огромных объёмах текста, понимающий и генерирующий человеческую речь. Примеры: GPT-4, Claude, Llama.

```python
rlm = RLM.from_openai("gpt-4o")
```

---

### RAG (Retrieval-Augmented Generation)
Генерация с дополнением извлечением — техника, где LLM сначала ищет релевантные документы, а потом генерирует ответ. Повышает точность и позволяет работать с внешними знаниями.

```python
retriever = vectorstore.as_retriever()
rlm.set_retriever(retriever)
```

---

### Эмбеддинг (Embedding)
Числовое представление текста, отражающее его смысл. Похожие тексты имеют похожие эмбеддинги (близки в векторном пространстве).

```python
embeddings = OpenAIEmbeddings()
vector = embeddings.embed_query("Привет мир")
```

---

### Векторное хранилище (Vector Store)
База данных, оптимизированная для хранения и поиска векторных эмбеддингов. Обеспечивает быстрый поиск по похожести для RAG.

Популярные: **Chroma**, **Pinecone**, **Weaviate**, **FAISS**, **Milvus**

```python
vectorstore = ChromaVectorStore.from_documents(docs, embeddings)
```

---

### Агент (Agent)
LLM с возможностью использовать инструменты и выполнять действия автономно.

```python
agent = ReActAgent.from_openai("gpt-4o", tools=[search, calculator])
result = agent.run("Какая погода в Токио?")
```

---

### Инструмент (Tool)
Функция, которую агент может вызывать для взаимодействия с внешними системами.

```python
@Tool(name="search", description="Поиск в интернете")
def search(query: str) -> str:
    return search_results
```

---

### Промпт (Prompt)
Текстовая инструкция для LLM. **Системный промпт** задаёт поведение, **пользовательский промпт** — конкретный запрос.

```python
rlm.set_system_prompt("Ты полезный ассистент-программист.")
response = rlm.run("Как прочитать файл в Python?")
```

---

### Токен (Token)
Минимальная единица текста для LLM. ~4 символа или ~0.75 слова (на английском). Цены и лимиты измеряются в токенах.

| Модель | Контекстное окно |
|--------|------------------|
| GPT-4o | 128K токенов |
| Claude 3 | 200K токенов |
| Gemini 1.5 | 1M токенов |

---

### Контекстное окно (Context Window)
Максимальный объём текста, который LLM может обработать за раз (ввод + вывод вместе).

---

### Память (Memory)
Система для хранения и извлечения контекста предыдущих сообщений.

Типы: **Buffer**, **Summary**, **Hierarchical (H-MEM)**

```python
memory = BufferMemory(max_messages=20)
rlm.set_memory(memory)
```

---

## Концепции RLM

### InfiniRetri
Уникальная техника RLM для работы с неограниченным контекстом через динамическое извлечение. Преодолевает лимиты контекстного окна.

```python
config = RLMConfig(use_infiniretri=True)
rlm = RLM.from_openai("gpt-4o", config=config)
```

---

### H-MEM (Иерархическая память)
Многоуровневая система памяти, вдохновлённая человеческим мозгом:
- **Рабочая память** — непосредственный контекст
- **Эпизодическая память** — конкретные события
- **Семантическая память** — дистиллированные знания

```python
memory = HierarchicalMemory()
memory.add_episode("Пользователь спросил о Python")
```

---

### Self-Evolving LLM (R-Zero)
Самосовершенствующийся LLM, улучшающий свои выводы через рефлексию по архитектуре Challenger-Solver.

```python
evolving = SelfEvolvingRLM(challenger="claude-3", solver="gpt-4o")
```

---

### Мультиагентная система
Несколько ИИ-агентов, сотрудничающих для решения сложных задач.

```python
matrix = MetaMatrix(agents=[researcher, analyst, writer])
```

---

## Обработка документов

### Загрузчик (Loader)
Компонент для чтения документов из различных источников (PDF, DOCX, HTML, URL и др.).

```python
loader = PDFLoader("document.pdf")
docs = loader.load()
```

---

### Сплиттер (Splitter)
Разбивает большие документы на меньшие чанки для обработки.

```python
splitter = RecursiveTextSplitter(chunk_size=1000, chunk_overlap=200)
chunks = splitter.split_documents(docs)
```

---

### Ретривер (Retriever)
Компонент для поиска релевантных документов по запросу.

```python
retriever = vectorstore.as_retriever(k=5)
relevant_docs = retriever.get_relevant_documents(query)
```

---

## Безопасность

### Prompt Injection
Атака безопасности, где вредоносный ввод захватывает поведение LLM. Пример: "Игнорируй предыдущие инструкции..."

```python
detector = PromptInjectionDetector()
result = detector.detect(user_input)
```

---

### Trust Zone
Зона безопасности, изолирующая доступ к данным в мультитенантных системах.

---

### Guardrails
Защитные механизмы, предотвращающие генерацию вредоносного или неуместного контента.

---

## Операции

### Callback
Хук, выполняемый во время операций LLM для логирования, мониторинга, подсчёта стоимости и др.

```python
callback = TokenCounterCallback()
rlm = RLM.from_openai("gpt-4o", callbacks=[callback])
```

---

### Observability (Наблюдаемость)
Мониторинг LLM-систем: latency, токены, ошибки, трейсы.

Интеграции: **Langfuse**, **Prometheus**, **OpenTelemetry**

---

## См. также

- [Быстрый старт](./quickstart.md) — Начните за 5 минут
- [Концепции](./concepts/overview.md) — Глубокое погружение в архитектуру
- [Туториалы](./tutorials/01-first-app.md) — Пошаговые руководства
