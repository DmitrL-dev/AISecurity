# Туториал 1: Ваше первое приложение

Создайте своё первое AI-приложение с RLM-Toolkit за 15 минут.

## Что вы создадите

Простую систему вопросов и ответов, которая:

1. Загружает документ
2. Создаёт эмбеддинги
3. Сохраняет в векторную базу данных
4. Отвечает на вопросы по документу

## Предварительные требования

```bash
pip install rlm-toolkit[all]
```

Установите ваш OpenAI API ключ:
```bash
export OPENAI_API_KEY=ваш-api-ключ
```

## Шаг 1: Создание проекта

Создайте новую директорию и файл:

```bash
mkdir my-first-rlm
cd my-first-rlm
touch app.py
```

## Шаг 2: Импорт зависимостей

```python
# app.py
from rlm_toolkit import RLM, RLMConfig
from rlm_toolkit.loaders import TextLoader
from rlm_toolkit.splitters import RecursiveCharacterTextSplitter
from rlm_toolkit.embeddings import OpenAIEmbeddings
from rlm_toolkit.vectorstores import ChromaVectorStore
```

## Шаг 3: Создание тестовых данных

Создайте файл `data.txt` с контентом:

```text
RLM-Toolkit — современный AI-фреймворк.
Он поддерживает 75+ LLM-провайдеров, включая OpenAI, Anthropic и Google.
Фреймворк включает 135+ загрузчиков документов для различных форматов.
Уникальные возможности включают InfiniRetri для бесконечного контекста и H-MEM для иерархической памяти.
RLM-Toolkit был разработан как безопасная альтернатива LangChain.
```

## Шаг 4: Загрузка и обработка документа

```python
# Загружаем документ
loader = TextLoader("data.txt")
documents = loader.load()

print(f"Загружено {len(documents)} документ(ов)")
print(f"Длина контента: {len(documents[0].content)} символов")
```

## Шаг 5: Разбиение на чанки

```python
# Разбиваем на меньшие части для лучшего поиска
splitter = RecursiveCharacterTextSplitter(
    chunk_size=100,
    chunk_overlap=20
)

chunks = splitter.split_documents(documents)
print(f"Разбито на {len(chunks)} чанков")
```

## Шаг 6: Создание эмбеддингов и сохранение

```python
# Создаём эмбеддинги
embeddings = OpenAIEmbeddings()

# Сохраняем в ChromaDB
vectorstore = ChromaVectorStore.from_documents(
    chunks,
    embeddings,
    collection_name="my-first-collection"
)

print("Векторное хранилище создано!")
```

## Шаг 7: Создание RLM с ретривером

```python
# Создаём ретривер из векторного хранилища
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

# Создаём RLM с ретривером
rlm = RLM.from_openai(
    "gpt-4o-mini",
    retriever=retriever
)
```

## Шаг 8: Задаём вопросы

```python
# Задаём вопросы по документу
questions = [
    "Что такое RLM-Toolkit?",
    "Сколько LLM-провайдеров поддерживается?",
    "Какие уникальные возможности есть?",
]

for question in questions:
    print(f"\n❓ {question}")
    result = rlm.run(question)
    print(f"✅ {result.answer}")
```

## Полный код

```python
# app.py
from rlm_toolkit import RLM
from rlm_toolkit.loaders import TextLoader
from rlm_toolkit.splitters import RecursiveCharacterTextSplitter
from rlm_toolkit.embeddings import OpenAIEmbeddings
from rlm_toolkit.vectorstores import ChromaVectorStore

def main():
    # 1. Загружаем документ
    print("📄 Загрузка документа...")
    loader = TextLoader("data.txt")
    documents = loader.load()
    
    # 2. Разбиваем на чанки
    print("✂️ Разбиение на чанки...")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=100,
        chunk_overlap=20
    )
    chunks = splitter.split_documents(documents)
    print(f"   Создано {len(chunks)} чанков")
    
    # 3. Создаём эмбеддинги и сохраняем
    print("🧮 Создание эмбеддингов...")
    embeddings = OpenAIEmbeddings()
    vectorstore = ChromaVectorStore.from_documents(
        chunks,
        embeddings,
        collection_name="my-first-collection"
    )
    
    # 4. Создаём RLM с ретривером
    print("🤖 Инициализация RLM...")
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
    rlm = RLM.from_openai("gpt-4o-mini", retriever=retriever)
    
    # 5. Интерактивные вопросы и ответы
    print("\n" + "="*50)
    print("🎉 Готово! Задавайте вопросы по документу.")
    print("   Введите 'quit' для выхода.")
    print("="*50 + "\n")
    
    while True:
        question = input("Вы: ")
        if question.lower() in ['quit', 'exit', 'q', 'выход']:
            break
        
        result = rlm.run(question)
        print(f"AI: {result.answer}\n")

if __name__ == "__main__":
    main()
```

## Запуск приложения

```bash
python app.py
```

Ожидаемый вывод:
```
📄 Загрузка документа...
✂️ Разбиение на чанки...
   Создано 5 чанков
🧮 Создание эмбеддингов...
🤖 Инициализация RLM...

==================================================
🎉 Готово! Задавайте вопросы по документу.
   Введите 'quit' для выхода.
==================================================

Вы: Что такое RLM-Toolkit?
AI: RLM-Toolkit — это современный AI-фреймворк, разработанный 
    как безопасная альтернатива LangChain. Он поддерживает 75+ 
    LLM-провайдеров и включает уникальные функции, такие как 
    InfiniRetri и H-MEM.
```

## Что дальше?

- [Туториал 2: Создание чат-бота](02-chatbot.md) — Добавляем память разговора
- [Туториал 3: RAG Pipeline](03-rag.md) — Работа с PDF и большими документами
- [Концепция: Провайдеры](../concepts/providers.md) — Узнайте о LLM-провайдерах

## Устранение проблем

!!! warning "Ошибка API ключа"
    Если видите `AuthenticationError`, убедитесь, что `OPENAI_API_KEY` установлен правильно.

!!! warning "Ошибка импорта"
    Если импорты не работают, переустановите: `pip install rlm-toolkit[all]`

!!! tip "Использование других провайдеров"
    Замените `RLM.from_openai()` на:
    
    - `RLM.from_anthropic("claude-3-sonnet")` для Claude
    - `RLM.from_ollama("llama3")` для локального Ollama
