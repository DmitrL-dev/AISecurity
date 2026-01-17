# Решение проблем

Частые проблемы и способы их решения.

---

## Проблемы установки

### ❌ `pip install rlm-toolkit` не работает

**Симптомы:** Ошибка при установке, отсутствующие зависимости.

**Решения:**

1. **Обновите pip:**
   ```bash
   pip install --upgrade pip
   ```

2. **Используйте Python 3.9+:**
   ```bash
   python --version  # Должен быть 3.9 или выше
   ```

3. **Установите в чистом виртуальном окружении:**
   ```bash
   python -m venv rlm-env
   source rlm-env/bin/activate  # Linux/Mac
   rlm-env\Scripts\activate     # Windows
   pip install rlm-toolkit
   ```

---

### ❌ Ошибки импорта после установки

**Симптомы:** `ModuleNotFoundError: No module named 'rlm_toolkit'`

**Решения:**

1. Убедитесь, что вы в правильном виртуальном окружении
2. Проверьте, установлен ли пакет:
   ```bash
   pip show rlm-toolkit
   ```
3. Попробуйте переустановить:
   ```bash
   pip uninstall rlm-toolkit
   pip install rlm-toolkit
   ```

---

## Проблемы с API ключами

### ❌ `AuthenticationError: Incorrect API key`

**Симптомы:** Ошибка при создании экземпляра RLM.

**Решения:**

1. **Проверьте переменную окружения:**
   ```bash
   # Linux/Mac
   echo $OPENAI_API_KEY
   
   # Windows PowerShell
   echo $env:OPENAI_API_KEY
   ```

2. **Установите API ключ правильно:**
   ```bash
   # Linux/Mac (добавьте в ~/.bashrc или ~/.zshrc)
   export OPENAI_API_KEY="sk-..."
   
   # Windows PowerShell
   $env:OPENAI_API_KEY = "sk-..."
   ```

3. **Передайте ключ напрямую:**
   ```python
   rlm = RLM.from_openai("gpt-4o", api_key="sk-...")
   ```

4. **Используйте .env файл:**
   ```bash
   # .env файл
   OPENAI_API_KEY=sk-...
   ```
   ```python
   from dotenv import load_dotenv
   load_dotenv()
   ```

---

### ❌ Где взять API ключ?

| Провайдер | Получить ключ |
|-----------|---------------|
| OpenAI | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) |
| Anthropic | [console.anthropic.com](https://console.anthropic.com) |
| Google | [aistudio.google.com](https://aistudio.google.com) |
| Groq | [console.groq.com](https://console.groq.com) |

---

## Лимиты запросов

### ❌ `RateLimitError: Too many requests`

**Симптомы:** Ошибка после многих запросов.

**Решения:**

1. **Добавьте задержку между запросами:**
   ```python
   import time
   
   for item in items:
       response = rlm.run(item)
       time.sleep(1)  # Подождать 1 секунду
   ```

2. **Используйте экспоненциальный backoff:**
   ```python
   from rlm_toolkit.utils import with_retry
   
   @with_retry(max_attempts=3, backoff_factor=2)
   def safe_request(prompt):
       return rlm.run(prompt)
   ```

3. **Батчите запросы** вместо отправки по одному

4. **Повысьте тарифный план API** для больших лимитов

---

## Проблемы с памятью

### ❌ `OutOfMemoryError` с большими документами

**Решения:**

1. **Используйте меньшие чанки:**
   ```python
   splitter = RecursiveTextSplitter(chunk_size=500)  # Меньше чанки
   ```

2. **Включите InfiniRetri:**
   ```python
   config = RLMConfig(enable_infiniretri=True)
   rlm = RLM.from_openai("gpt-4o", config=config)
   ```

3. **Обрабатывайте батчами:**
   ```python
   for batch in chunks(documents, size=10):
       process_batch(batch)
   ```

---

## Слишком длинный контекст

### ❌ `ContextLengthExceeded: Maximum context length exceeded`

**Симптомы:** Ошибка когда промпт слишком большой.

**Решения:**

1. **Проверьте длину промпта:**
   ```python
   import tiktoken
   enc = tiktoken.encoding_for_model("gpt-4o")
   tokens = len(enc.encode(your_prompt))
   print(f"Токены: {tokens}")
   ```

2. **Используйте модель с большим контекстом:**
   ```python
   # GPT-4o: 128K токенов
   # Claude 3: 200K токенов
   rlm = RLM.from_anthropic("claude-3-sonnet")
   ```

3. **Включите InfiniRetri** для автоматического управления контекстом

4. **Суммаризируйте длинные тексты** перед отправкой

---

## Проблемы подключения

### ❌ `ConnectionError: Failed to connect to API`

**Решения:**

1. **Проверьте интернет-соединение**

2. **Проверьте настройки прокси:**
   ```python
   import os
   os.environ["HTTP_PROXY"] = "http://proxy:8080"
   os.environ["HTTPS_PROXY"] = "http://proxy:8080"
   ```

3. **Увеличьте таймаут:**
   ```python
   rlm = RLM.from_openai("gpt-4o", timeout=60)
   ```

---

## Ollama (Локальные LLM)

### ❌ Не удаётся подключиться к Ollama

**Решения:**

1. **Убедитесь, что Ollama запущен:**
   ```bash
   ollama serve
   ```

2. **Проверьте, скачана ли модель:**
   ```bash
   ollama list
   ollama pull llama3
   ```

3. **Укажите правильный URL:**
   ```python
   rlm = RLM.from_ollama("llama3", base_url="http://localhost:11434")
   ```

---

## Получение помощи

Если вашей проблемы нет в списке:

1. **Проверьте [GitHub Issues](https://github.com/sentinel/rlm-toolkit/issues)**
2. **Поищите в документации** через поиск
3. **Спросите в [Discussions](https://github.com/sentinel/rlm-toolkit/discussions)**
4. **Создайте новый issue** с:
   - Версией RLM-Toolkit (`pip show rlm-toolkit`)
   - Версией Python (`python --version`)
   - Полным текстом ошибки
   - Минимальным кодом для воспроизведения

---

## См. также

- [Быстрый старт](./quickstart.md) — Руководство для начала
- [Глоссарий](./glossary.md) — Понять терминологию
- [API Reference](./reference/) — Подробная документация API
