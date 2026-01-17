# Галерея примеров

Практические, готовые к использованию примеры для каждого сценария RLM-Toolkit.

## Быстрая навигация

| Категория | Примеры |
|-----------|---------|
| [Базовые](#базовые) | Hello World, Чат, Streaming |
| [RAG](#rag) | PDF Q&A, Web Scraper, Гибридный поиск |
| [Агенты](#агенты) | Research Agent, Код-ассистент, Аналитик |
| [Память](#память) | Персистентный чат, H-MEM, Менеджер сессий |
| [Продвинутые](#продвинутые) | InfiniRetri, Self-Evolving, Multi-Agent |
| [Продакшн](#продакшн) | FastAPI, Docker, Kubernetes |
| [Интеграции](#интеграции) | Slack Bot, Discord, Telegram |

---

## Базовые

### Hello World

```python
from rlm_toolkit import RLM

rlm = RLM.from_openai("gpt-4o")
print(rlm.run("Привет, мир!"))
```

### Простой чат

```python
from rlm_toolkit import RLM
from rlm_toolkit.memory import BufferMemory

rlm = RLM.from_openai("gpt-4o", memory=BufferMemory())

while True:
    user_input = input("Вы: ")
    if user_input.lower() == "выход":
        break
    response = rlm.run(user_input)
    print(f"AI: {response}")
```

### Streaming ответ

```python
from rlm_toolkit import RLM

rlm = RLM.from_openai("gpt-4o")

for chunk in rlm.stream("Расскажи историю о роботе"):
    print(chunk, end="", flush=True)
```

### JSON вывод

```python
from rlm_toolkit import RLM, RLMConfig

config = RLMConfig(json_mode=True)
rlm = RLM.from_openai("gpt-4o", config=config)

result = rlm.run("""
Извлеки информацию о человеке:
"Иван Петров, 35 лет, работает в Яндексе как Senior Engineer"

Верни как: {"name": str, "age": int, "company": str, "role": str}
""")
print(result)
```

### Структурированный вывод (Pydantic)

```python
from pydantic import BaseModel
from rlm_toolkit import RLM

class Product(BaseModel):
    name: str
    price: float
    in_stock: bool

rlm = RLM.from_openai("gpt-4o")
product = rlm.run_structured(
    "iPhone 15 Pro, 99990₽, в наличии",
    output_schema=Product
)
print(f"{product.name}: {product.price}₽")
```

### Несколько провайдеров

```python
from rlm_toolkit import RLM

# OpenAI
gpt = RLM.from_openai("gpt-4o")

# Anthropic
claude = RLM.from_anthropic("claude-3-sonnet")

# Google
gemini = RLM.from_google("gemini-pro")

# Локальный (Ollama)
llama = RLM.from_ollama("llama3")

# Сравнение выводов
query = "Объясни квантовые вычисления в одном предложении"
print(f"GPT: {gpt.run(query)}")
print(f"Claude: {claude.run(query)}")
print(f"Gemini: {gemini.run(query)}")
print(f"Llama: {llama.run(query)}")
```

### Анализ изображений (Vision)

```python
from rlm_toolkit import RLM

rlm = RLM.from_openai("gpt-4o")

result = rlm.run(
    "Что на этом изображении? Опиши подробно.",
    images=["./photo.jpg"]
)
print(result)
```

### Перевод

```python
from rlm_toolkit import RLM

rlm = RLM.from_openai("gpt-4o")
rlm.set_system_prompt("Ты переводчик. Переводи на запрошенный язык.")

text = "Здравствуйте, как ваши дела?"
print(rlm.run(f"Переведи на английский: {text}"))
print(rlm.run(f"Переведи на японский: {text}"))
print(rlm.run(f"Переведи на испанский: {text}"))
```

### Генерация кода

```python
from rlm_toolkit import RLM

rlm = RLM.from_openai("gpt-4o")
rlm.set_system_prompt("""
Ты эксперт Python. Генерируй чистый, документированный код.
Включай type hints и docstrings.
""")

code = rlm.run("Напиши функцию для поиска всех простых чисел до n")
print(code)
```

### Суммаризация

```python
from rlm_toolkit import RLM
from rlm_toolkit.loaders import WebPageLoader

rlm = RLM.from_openai("gpt-4o")

# Загрузка статьи
docs = WebPageLoader("https://example.com/article").load()
text = docs[0].page_content

# Суммаризация
summary = rlm.run(f"""
Суммируй эту статью в 3 пунктах:

{text}
""")
print(summary)
```

---

## RAG

### PDF вопрос-ответ

```python
from rlm_toolkit import RLM
from rlm_toolkit.loaders import PDFLoader
from rlm_toolkit.splitters import RecursiveTextSplitter
from rlm_toolkit.embeddings import OpenAIEmbeddings
from rlm_toolkit.vectorstores import ChromaVectorStore
from rlm_toolkit.retrievers import VectorStoreRetriever

# Загрузка PDF
docs = PDFLoader("company_report.pdf").load()

# Разбиение на чанки
splitter = RecursiveTextSplitter(chunk_size=1000, chunk_overlap=200)
chunks = splitter.split_documents(docs)

# Создание векторного хранилища
embeddings = OpenAIEmbeddings("text-embedding-3-small")
vectorstore = ChromaVectorStore.from_documents(chunks, embeddings)

# Создание ретривера
retriever = VectorStoreRetriever(vectorstore, search_kwargs={"k": 5})

# Создание RLM с ретривером
rlm = RLM.from_openai("gpt-4o")
rlm.set_retriever(retriever)
rlm.set_system_prompt("""
Отвечай только на основе предоставленного контекста.
Указывай источники. Если не уверен, скажи "Не знаю".
""")

# Задай вопросы
print(rlm.run("Какая была выручка за Q3?"))
print(rlm.run("Кто ключевые руководители?"))
```

### Multi-Document RAG

```python
from rlm_toolkit.loaders import DirectoryLoader, PDFLoader

# Загрузка всех PDF из директории
loader = DirectoryLoader(
    path="./documents",
    glob="**/*.pdf",
    loader_cls=PDFLoader,
    show_progress=True
)
docs = loader.load()

print(f"Загружено {len(docs)} документов")
```

### Web RAG

```python
from rlm_toolkit import RLM
from rlm_toolkit.loaders import WebPageLoader
from rlm_toolkit.splitters import MarkdownSplitter
from rlm_toolkit.embeddings import OpenAIEmbeddings
from rlm_toolkit.vectorstores import ChromaVectorStore

# Парсинг документации
urls = [
    "https://docs.example.com/getting-started",
    "https://docs.example.com/api-reference",
    "https://docs.example.com/tutorials"
]

docs = WebPageLoader(urls).load()
chunks = MarkdownSplitter(chunk_size=1000).split_documents(docs)

vectorstore = ChromaVectorStore.from_documents(
    chunks, OpenAIEmbeddings()
)

rlm = RLM.from_openai("gpt-4o")
rlm.set_retriever(vectorstore.as_retriever(k=5))

print(rlm.run("Как аутентифицироваться в API?"))
```

### Гибридный поиск RAG

```python
from rlm_toolkit.retrievers import HybridRetriever

retriever = HybridRetriever(
    vectorstore=vectorstore,
    keyword_weight=0.3,
    semantic_weight=0.7,
    fusion_method="rrf"
)

rlm = RLM.from_openai("gpt-4o")
rlm.set_retriever(retriever)

# Лучшие результаты для семантических и ключевых запросов
print(rlm.run("код ошибки 404"))  # Ключевые слова
print(rlm.run("Как обработать ошибки аутентификации"))  # Семантика
```

---

## Агенты

### Исследовательский агент

```python
from rlm_toolkit.agents import ReActAgent
from rlm_toolkit.tools import WebSearchTool, WikipediaTool, ArxivTool

agent = ReActAgent.from_openai(
    "gpt-4o",
    tools=[
        WebSearchTool(provider="ddg"),
        WikipediaTool(),
        ArxivTool()
    ]
)

result = agent.run("""
Исследуй последние разработки в квантовых вычислениях.
Найди свежие статьи и суммируй ключевые прорывы.
""")
print(result)
```

### Код-ассистент

```python
from rlm_toolkit.agents import ReActAgent
from rlm_toolkit.tools import PythonREPL, FileReader, FileWriter

agent = ReActAgent.from_openai(
    "gpt-4o",
    tools=[
        PythonREPL(max_execution_time=30),
        FileReader(),
        FileWriter()
    ],
    system_prompt="Ты ассистент по программированию на Python."
)

result = agent.run("""
1. Прочитай файл data.csv
2. Проанализируй данные с pandas
3. Создай визуализацию
4. Сохрани график как chart.png
""")
```

### Аналитик данных

```python
from rlm_toolkit.agents import ReActAgent
from rlm_toolkit.tools import PythonREPL, SQLTool

agent = ReActAgent.from_openai(
    "gpt-4o",
    tools=[
        PythonREPL(),
        SQLTool(connection_string="sqlite:///data.db")
    ]
)

result = agent.run("""
Проанализируй таблицу продаж:
1. Покажи общую выручку по месяцам
2. Найди топ-10 продуктов
3. Посчитай retention клиентов
""")
```

### Математик

```python
from rlm_toolkit.agents import ReActAgent
from rlm_toolkit.tools import Tool
import sympy

@Tool(name="solve_equation", description="Решить уравнение")
def solve_equation(equation: str) -> str:
    x = sympy.Symbol('x')
    result = sympy.solve(equation, x)
    return str(result)

@Tool(name="differentiate", description="Взять производную")
def differentiate(expr: str) -> str:
    x = sympy.Symbol('x')
    result = sympy.diff(expr, x)
    return str(result)

agent = ReActAgent.from_openai("gpt-4o", tools=[solve_equation, differentiate])
print(agent.run("Реши x^2 - 5x + 6 = 0"))
print(agent.run("Найди производную x^3 + 2x^2"))
```

---

## Память

### Персистентный чат

```python
from rlm_toolkit import RLM
from rlm_toolkit.memory import HierarchicalMemory

memory = HierarchicalMemory(persist_directory="./chat_history")

rlm = RLM.from_openai("gpt-4o", memory=memory)

# Разговор сохраняется между сессиями
rlm.run("Меня зовут Алексей и я изучаю Python")
# ... перезапуск ...
rlm.run("Как меня зовут?")  # "Вас зовут Алексей"
```

### Менеджер сессий

```python
from rlm_toolkit import RLM
from rlm_toolkit.memory import SessionMemory

sessions = {}

def get_session(user_id: str) -> RLM:
    if user_id not in sessions:
        memory = SessionMemory(session_id=user_id)
        sessions[user_id] = RLM.from_openai("gpt-4o", memory=memory)
    return sessions[user_id]

# У каждого пользователя изолированная память
alice = get_session("alice")
bob = get_session("bob")

alice.run("Я люблю кошек")
bob.run("Я люблю собак")

print(alice.run("Что я люблю?"))  # кошек
print(bob.run("Что я люблю?"))    # собак
```

---

## Продвинутые

### InfiniRetri (1M+ токенов)

```python
from rlm_toolkit import RLM, RLMConfig
from rlm_toolkit.retrieval import InfiniRetriConfig
from rlm_toolkit.loaders import PDFLoader

config = RLMConfig(
    enable_infiniretri=True,
    infiniretri_config=InfiniRetriConfig(
        chunk_size=4000,
        top_k=5
    ),
    infiniretri_threshold=50000
)

rlm = RLM.from_openai("gpt-4o", config=config)

# Загрузка огромного документа (1000+ страниц)
docs = PDFLoader("massive_report.pdf").load()

result = rlm.run_with_docs(
    query="Найди раздел о выручке Q3 и объясни рост",
    documents=docs
)
print(result)
```

### Self-Evolving (Challenger-Solver)

```python
from rlm_toolkit.evolve import SelfEvolvingRLM, EvolutionConfig

config = EvolutionConfig(
    strategy="challenger_solver",
    max_iterations=5,
    early_stop_threshold=0.95
)

evolving = SelfEvolvingRLM.from_openai("gpt-4o", config=config)

result = evolving.run("""
Напиши Python функцию для эффективного поиска
самой длинной палиндромной подстроки.
Включи edge cases и документацию.
""")
print(result)
```

### Multi-Agent коллаборация

```python
from rlm_toolkit.agents.multiagent import MetaMatrix, Agent
from rlm_toolkit import RLM
from rlm_toolkit.tools import WebSearchTool, PythonREPL, FileWriter

researcher = Agent(
    name="researcher",
    description="Ищет информацию",
    llm=RLM.from_openai("gpt-4o"),
    tools=[WebSearchTool()]
)

analyst = Agent(
    name="analyst", 
    description="Анализирует данные кодом",
    llm=RLM.from_openai("gpt-4o"),
    tools=[PythonREPL()]
)

writer = Agent(
    name="writer",
    description="Пишет отчёты",
    llm=RLM.from_anthropic("claude-3-sonnet"),
    tools=[FileWriter()]
)

matrix = MetaMatrix(topology="mesh", consensus="raft")
matrix.register(researcher)
matrix.register(analyst)
matrix.register(writer)

result = matrix.run("""
1. Исследуй AI тренды 2024
2. Проанализируй данные и создай графики
3. Напиши comprehensive отчёт
Сохрани всё в output/
""")
```

---

## Продакшн

### FastAPI приложение

```python
from fastapi import FastAPI
from pydantic import BaseModel
from rlm_toolkit import RLM
from rlm_toolkit.memory import SessionMemory
import uuid

app = FastAPI(title="RLM Chat API")
sessions = {}

class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str

class ChatResponse(BaseModel):
    session_id: str
    response: str

def get_rlm(session_id: str) -> RLM:
    if session_id not in sessions:
        memory = SessionMemory(session_id=session_id)
        sessions[session_id] = RLM.from_openai("gpt-4o", memory=memory)
    return sessions[session_id]

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    session_id = request.session_id or str(uuid.uuid4())
    rlm = get_rlm(session_id)
    response = rlm.run(request.message)
    return ChatResponse(session_id=session_id, response=response)
```

---

## Интеграции

### Telegram бот

```python
from telegram import Update
from telegram.ext import Application, MessageHandler, filters
from rlm_toolkit import RLM
from rlm_toolkit.memory import SessionMemory

sessions = {}

def get_rlm(user_id: int) -> RLM:
    if user_id not in sessions:
        sessions[user_id] = RLM.from_openai(
            "gpt-4o",
            memory=SessionMemory(session_id=str(user_id))
        )
    return sessions[user_id]

async def handle_message(update: Update, context):
    user_id = update.effective_user.id
    text = update.message.text
    
    rlm = get_rlm(user_id)
    response = rlm.run(text)
    
    await update.message.reply_text(response)

app = Application.builder().token("your-telegram-token").build()
app.add_handler(MessageHandler(filters.TEXT, handle_message))
app.run_polling()
```

### Gradio UI

```python
import gradio as gr
from rlm_toolkit import RLM
from rlm_toolkit.memory import BufferMemory

rlm = RLM.from_openai("gpt-4o", memory=BufferMemory())

def chat(message, history):
    response = rlm.run(message)
    return response

demo = gr.ChatInterface(
    chat,
    title="RLM Чат",
    description="Чат с GPT-4o",
    examples=["Привет!", "Объясни квантовые вычисления", "Напиши стихотворение"]
)

demo.launch()
```

### Streamlit приложение

```python
import streamlit as st
from rlm_toolkit import RLM
from rlm_toolkit.memory import BufferMemory

st.title("🤖 RLM Чат")

if "rlm" not in st.session_state:
    st.session_state.rlm = RLM.from_openai("gpt-4o", memory=BufferMemory())
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

if prompt := st.chat_input("Напишите что-нибудь..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)
    
    response = st.session_state.rlm.run(prompt)
    
    st.session_state.messages.append({"role": "assistant", "content": response})
    with st.chat_message("assistant"):
        st.write(response)
```

---

## Дальнейшие шаги

- [Туториалы](../tutorials/) - Пошаговые руководства
- [Концепции](../concepts/) - Глубокие погружения
- [How-to](../how-to/) - Конкретные рецепты
