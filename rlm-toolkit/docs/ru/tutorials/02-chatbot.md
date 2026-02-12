# Туториал 2: Создание чат-бота

Создайте разговорного чат-бота с памятью, который помнит предыдущие сообщения.

## Что вы создадите

Чат-бот, который:

1. Ведёт историю разговора
2. Запоминает предпочтения пользователя
3. Использует иерархическую память для долгосрочного контекста

## Предварительные требования

```bash
pip install rlm-toolkit[all]
export OPENAI_API_KEY=your-api-key
```

## Шаг 1: Простой чат-бот (без памяти)

Начнём с базового чат-бота без памяти:

```python
from rlm_toolkit import RLM

rlm = RLM.from_openai("gpt-4o")

# Первое сообщение
result = rlm.run("Привет, меня зовут Алиса")
print(result.answer)

# Второе сообщение - он не запомнит!
result = rlm.run("Как меня зовут?")
print(result.answer)  # "Я не знаю вашего имени"
```

Проблема: чат-бот ничего не помнит между сообщениями.

## Шаг 2: Добавляем буферную память

Буферная память хранит историю разговора:

```python
from rlm_toolkit import RLM
from rlm_toolkit.memory import BufferMemory

# Создаём память
memory = BufferMemory(max_messages=50)

# Создаём RLM с памятью
rlm = RLM.from_openai("gpt-4o", memory=memory)

# Теперь он запоминает!
rlm.run("Привет, меня зовут Алиса")
result = rlm.run("Как меня зовут?")
print(result.answer)  # "Вас зовут Алиса"
```

## Шаг 3: Добавляем иерархическую память (H-MEM)

H-MEM обеспечивает 4-уровневую память с автоматической консолидацией:

```python
from rlm_toolkit import RLM
from rlm_toolkit.memory import HierarchicalMemory

# Создаём H-MEM
hmem = HierarchicalMemory(
    consolidation_enabled=True,
    consolidation_threshold=10  # Консолидация после 10 сообщений
)

# Создаём RLM с H-MEM
rlm = RLM.from_openai("gpt-4o", memory=hmem)

# Ведём разговор
rlm.run("Привет, я Борис. Работаю программистом.")
rlm.run("Специализируюсь на Python и машинном обучении.")
rlm.run("Мой любимый фреймворк — RLM-Toolkit.")
rlm.run("Создаю чат-бота для своей компании.")

# Позже он помнит ключевые концепции
result = rlm.run("Что ты знаешь обо мне?")
print(result.answer)
# "Вы Борис, программист, специализирующийся на Python и ML..."
```

## Шаг 4: Эпизодическая память

Эпизодическая память хранит факты как сущности:

```python
from rlm_toolkit import RLM
from rlm_toolkit.memory import EpisodicMemory

# Создаём эпизодическую память
episodic = EpisodicMemory()

# Создаём RLM
rlm = RLM.from_openai("gpt-4o", memory=episodic)

# Сохраняем факты о сущностях
rlm.run("Ивану 30 лет, и он живёт в Москве")
rlm.run("Мария — сестра Ивана, она врач")

# Запрашиваем информацию о конкретных сущностях
result = rlm.run("Сколько лет Ивану?")
print(result.answer)  # "Ивану 30 лет"

result = rlm.run("Кем работает Мария?")
print(result.answer)  # "Мария — врач"
```

## Шаг 5: Персистентная память

Сохраняем память на диск для использования между сессиями:

```python
from rlm_toolkit import RLM
from rlm_toolkit.memory import HierarchicalMemory

# Создаём H-MEM с персистентностью
hmem = HierarchicalMemory(
    persist_directory="./memory_store",
    auto_save=True
)

# Создаём RLM
rlm = RLM.from_openai("gpt-4o", memory=hmem)

# Общаемся и автоматически сохраняем память
rlm.run("Запомни, что мой день рождения 15 марта")

# Позже, в новой сессии:
# Память автоматически загружается с диска
hmem2 = HierarchicalMemory(persist_directory="./memory_store")
rlm2 = RLM.from_openai("gpt-4o", memory=hmem2)

result = rlm2.run("Когда мой день рождения?")
print(result.answer)  # "Ваш день рождения 15 марта"
```

## Полное приложение чат-бота

```python
# chatbot.py
from rlm_toolkit import RLM
from rlm_toolkit.memory import HierarchicalMemory
from datetime import datetime

def create_chatbot():
    """Создаёт чат-бота с иерархической памятью."""
    
    # Инициализируем H-MEM с персистентностью
    memory = HierarchicalMemory(
        persist_directory="./chatbot_memory",
        auto_save=True,
        consolidation_enabled=True
    )
    
    # Системный промпт для личности
    system_prompt = """Ты полезный и дружелюбный ассистент по имени Ариа.
Ты помнишь все предыдущие разговоры с пользователем.
Будь краткой, но тёплой в ответах.
Если чего-то не знаешь, честно скажи об этом."""
    
    # Создаём RLM
    rlm = RLM.from_openai(
        "gpt-4o",
        memory=memory,
        system_prompt=system_prompt
    )
    
    return rlm

def main():
    print("="*50)
    print("🤖 Чат-бот Ариа — на базе RLM-Toolkit")
    print("   Введите 'выход' для выхода, 'очистить' для сброса памяти")
    print("="*50)
    
    rlm = create_chatbot()
    
    while True:
        user_input = input("\n👤 Вы: ").strip()
        
        if not user_input:
            continue
        
        if user_input.lower() in ['выход', 'quit']:
            print("👋 До свидания!")
            break
        
        if user_input.lower() in ['очистить', 'clear']:
            rlm.memory.clear()
            print("🧹 Память очищена!")
            continue
        
        if user_input.lower() in ['память', 'memory']:
            # Показываем статистику памяти
            stats = rlm.memory.get_stats()
            print(f"📊 Статистика памяти:")
            print(f"   Эпизоды: {stats.get('episode_count', 0)}")
            print(f"   Трейсы: {stats.get('trace_count', 0)}")
            print(f"   Категории: {stats.get('category_count', 0)}")
            continue
        
        # Получаем ответ
        result = rlm.run(user_input)
        print(f"\n🤖 Ариа: {result.answer}")

if __name__ == "__main__":
    main()
```

## Запуск чат-бота

```bash
python chatbot.py
```

Пример разговора:

```
==================================================
🤖 Чат-бот Ариа — на базе RLM-Toolkit
   Введите 'выход' для выхода, 'очистить' для сброса памяти
==================================================

👤 Вы: Привет! Я Алекс и люблю походы.

🤖 Ариа: Привет, Алекс! Приятно познакомиться. Походы — это 
   замечательно! Есть любимые маршруты?

👤 Вы: Я люблю Кавказские горы

🤖 Ариа: Кавказ прекрасен! Невероятные виды и разнообразие 
   маршрутов. Бывали на Эльбрусе?

👤 Вы: Что ты помнишь обо мне?

🤖 Ариа: Я помню, что вас зовут Алекс, вы любите походы,
   особенно в Кавказских горах!
```

## Архитектура памяти

```
┌─────────────────────────────────────────────────────┐
│                   Уровни H-MEM                       │
├─────────────────────────────────────────────────────┤
│ Уровень 0: Эпизод  │ "Пользователь сказал: меня зовут Алекс" │
│ Уровень 1: Трейс   │ "Пользователь: Алекс, хобби: походы"    │
│ Уровень 2: Категория│ "Предпочтения и хобби пользователя"   │
│ Уровень 3: Домен   │ "Профиль и история пользователя"       │
└─────────────────────────────────────────────────────┘
                    ↓ консолидация ↓
         Автоматическое LLM-суммирование
```

## Лучшие практики работы с памятью

!!! tip "Размер памяти"
    Устанавливайте подходящие лимиты для предотвращения переполнения контекста:
    ```python
    memory = HierarchicalMemory(
        episode_limit=100,      # Максимум эпизодов до консолидации
        context_limit=4000      # Максимум токенов в контексте
    )
    ```

!!! tip "Консолидация"
    Включайте консолидацию для длинных разговоров:
    ```python
    memory = HierarchicalMemory(
        consolidation_enabled=True,
        consolidation_threshold=20  # Консолидация после 20 сообщений
    )
    ```

!!! warning "Приватность"
    Для чувствительных данных используйте SecureHierarchicalMemory:
    ```python
    from rlm_toolkit.memory import SecureHierarchicalMemory
    memory = SecureHierarchicalMemory(
        encryption_key="ваш-секретный-ключ",
        trust_zone="confidential"
    )
    ```

## Следующие шаги

- [Туториал 3: RAG Pipeline](03-rag.md)
- [Концепция: Архитектура H-MEM](../concepts/hmem.md)
- [Концепция: Системы памяти](../concepts/memory.md)
