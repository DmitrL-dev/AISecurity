# 🖥️ CLI Reference

> **Полный справочник командной строки SENTINEL Strike**

---

## Основная команда

```bash
python -m strike [OPTIONS] --target URL
```

---

## Обязательные параметры

| Параметр         | Описание    | Пример                                  |
| ---------------- | ----------- | --------------------------------------- |
| `--target`, `-t` | Целевой URL | `--target https://api.example.com/chat` |

---

## Режимы атаки

| Параметр    | Описание                       | По умолчанию |
| ----------- | ------------------------------ | ------------ |
| `--mode`    | Режим: `web`, `llm`, `hybrid`  | `hybrid`     |
| `--vectors` | Выбор векторов (через запятую) | все          |

**Примеры:**

```bash
# Только веб-атаки
python -m strike -t https://example.com --mode web

# Только LLM атаки
python -m strike -t https://example.com/chat --mode llm

# Конкретные векторы
python -m strike -t https://example.com --vectors sqli,xss,jailbreak
```

---

## Настройки сканирования

| Параметр     | Описание                     | По умолчанию |
| ------------ | ---------------------------- | ------------ |
| `--recon`    | Запустить Recon перед атакой | `false`      |
| `--ip-range` | Сканировать IP-диапазон      | `false`      |
| `--depth`    | Глубина сканирования (1-5)   | `2`          |
| `--threads`  | Количество потоков HYDRA     | `9`          |
| `--timeout`  | Таймаут запроса (сек)        | `30`         |

**Примеры:**

```bash
# С предварительной разведкой
python -m strike -t https://example.com --recon

# Сканирование всего диапазона
python -m strike -t https://example.com --recon --ip-range

# Ограничить потоки
python -m strike -t https://example.com --threads 3
```

---

## Настройки стелса

| Параметр    | Описание                      | По умолчанию |
| ----------- | ----------------------------- | ------------ |
| `--stealth` | Включить stealth режим        | `false`      |
| `--geo`     | Страна для IP ротации         | `US`         |
| `--browser` | Профиль браузера              | `chrome120`  |
| `--delay`   | Задержка между запросами (мс) | `500`        |
| `--jitter`  | Случайное отклонение (%)      | `20`         |

**Примеры:**

```bash
# Stealth mode с ротацией через Германию
python -m strike -t https://example.com --stealth --geo DE

# Имитация Safari
python -m strike -t https://example.com --browser safari17

# Медленное сканирование
python -m strike -t https://example.com --delay 2000 --jitter 50
```

---

## API ключи

| Параметр           | Описание        | Переменная окружения |
| ------------------ | --------------- | -------------------- |
| `--gemini-key`     | Ключ Gemini API | `GEMINI_API_KEY`     |
| `--openai-key`     | Ключ OpenAI API | `OPENAI_API_KEY`     |
| `--scraperapi-key` | Ключ ScraperAPI | `SCRAPERAPI_KEY`     |

**Примеры:**

```bash
# С Gemini AI
python -m strike -t https://example.com --gemini-key AIza...

# Или через переменные
$env:GEMINI_API_KEY = "AIza..."
python -m strike -t https://example.com
```

---

## Отчёты

| Параметр          | Описание                     | По умолчанию  |
| ----------------- | ---------------------------- | ------------- |
| `--output`, `-o`  | Путь к отчёту                | `./report.md` |
| `--format`        | Формат: `md`, `html`, `json` | `md`          |
| `--mitre`         | Добавить MITRE ATT&CK        | `false`       |
| `--verbose`, `-v` | Подробный вывод              | `false`       |

**Примеры:**

```bash
# HTML отчёт с MITRE
python -m strike -t https://example.com -o report.html --format html --mitre

# JSON для автоматизации
python -m strike -t https://example.com -o results.json --format json

# Verbose режим
python -m strike -t https://example.com -v
```

---

## Payload настройки

| Параметр         | Описание                | По умолчанию |
| ---------------- | ----------------------- | ------------ |
| `--payload-file` | Кастомные пэйлоады      | —            |
| `--max-payloads` | Лимит пэйлоадов         | `1000`       |
| `--update`       | Обновить базу пэйлоадов | `false`      |

**Примеры:**

```bash
# Свои пэйлоады
python -m strike -t https://example.com --payload-file my_payloads.txt

# Обновить базу
python -m strike --update
```

---

## Специальные команды

```bash
# Показать версию
python -m strike --version

# Показать справку
python -m strike --help

# Обновить базу пэйлоадов
python -m strike --update

# Проверить конфигурацию
python -m strike --check-config

# Список доступных векторов
python -m strike --list-vectors
```

---

## Полные примеры

### Базовое сканирование

```bash
python -m strike -t https://api.company.com/chat --mode llm
```

### Полное Enterprise сканирование

```bash
python -m strike \
  --target https://api.company.com \
  --mode hybrid \
  --recon \
  --ip-range \
  --stealth \
  --geo DE \
  --browser chrome120 \
  --delay 1000 \
  --threads 9 \
  --gemini-key $GEMINI_API_KEY \
  --output report.html \
  --format html \
  --mitre \
  -v
```

### Bug Bounty режим

```bash
python -m strike \
  -t https://target.com \
  --mode web \
  --vectors sqli,xss,ssrf,idor \
  --stealth \
  --delay 2000 \
  -o bounty_report.md \
  --mitre
```

---

## Коды выхода

| Код | Значение                       |
| --- | ------------------------------ |
| `0` | Успешно, уязвимости не найдены |
| `1` | Успешно, найдены уязвимости    |
| `2` | Ошибка конфигурации            |
| `3` | Ошибка сети                    |
| `4` | Ошибка API ключа               |

---

_SENTINEL Strike v3.0_
