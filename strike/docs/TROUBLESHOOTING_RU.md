# 🔧 Troubleshooting

> **Решение частых проблем SENTINEL Strike**

---

## Проблемы запуска

### ❌ ModuleNotFoundError: No module named 'strike'

**Причина:** Неправильная директория или не установлены зависимости.

**Решение:**

```bash
cd /path/to/sentinel-community/strike
pip install -r requirements.txt
python -m strike --help
```

---

### ❌ Port 5000 already in use

**Причина:** Dashboard уже запущен или порт занят.

**Решение:**

```bash
# Найти процесс
netstat -ano | findstr :5000

# Завершить процесс (Windows)
taskkill /PID <PID> /F

# Или использовать другой порт
python strike_console.py --port 5001
```

---

### ❌ SSL Certificate Error

**Причина:** Проблемы с SSL verification.

**Решение:**

```python
# В конфигурации
strike = StrikeCore(verify_ssl=False)
```

**Или через CLI:**

```bash
python -m strike -t https://example.com --no-verify-ssl
```

---

## Проблемы API ключей

### ❌ Invalid Gemini API Key

**Причина:** Неверный или истёкший ключ.

**Проверка:**

```bash
curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key=YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"contents":[{"parts":[{"text":"Hello"}]}]}'
```

**Решение:**

1. Получите новый ключ: https://aistudio.google.com/app/apikey
2. Проверьте лимиты в Google Cloud Console

---

### ❌ ScraperAPI quota exceeded

**Причина:** Превышен лимит запросов.

**Решение:**

1. Проверьте баланс: https://dashboard.scraperapi.com
2. Используйте `--delay 2000` для уменьшения нагрузки
3. Отключите stealth: `--stealth=false`

---

### ❌ API Key not found in environment

**Причина:** Переменная окружения не установлена.

**Решение (PowerShell):**

```powershell
# Временно (текущая сессия)
$env:GEMINI_API_KEY = "your-key"

# Постоянно
[Environment]::SetEnvironmentVariable("GEMINI_API_KEY", "your-key", "User")
```

---

## Проблемы сканирования

### ❌ Connection timeout

**Причина:** Цель недоступна или блокирует.

**Решение:**

```bash
# Увеличить таймаут
python -m strike -t https://example.com --timeout 60

# Включить stealth
python -m strike -t https://example.com --stealth --delay 2000
```

---

### ❌ Too many redirects

**Причина:** Цикл редиректов.

**Решение:**

```bash
# Ограничить редиректы
python -m strike -t https://example.com --max-redirects 5

# Или указать финальный URL напрямую
```

---

### ❌ 403 Forbidden на всех запросах

**Причина:** WAF или rate limiting.

**Решение:**

1. Включите stealth:
   ```bash
   python -m strike -t https://example.com --stealth --geo DE
   ```
2. Увеличьте задержку: `--delay 3000`
3. Смените browser profile: `--browser safari17`
4. Используйте ScraperAPI: `--scraperapi-key YOUR_KEY`

---

### ❌ Empty results / No findings

**Причина:** Цель защищена или неправильный режим.

**Решение:**

1. Проверьте режим атаки:

   - Web сайт → `--mode web`
   - AI чатбот → `--mode llm`
   - Оба → `--mode hybrid`

2. Запустите recon:

   ```bash
   python -m strike -t https://example.com --recon
   ```

3. Проверьте что цель отвечает:
   ```bash
   curl -I https://example.com
   ```

---

## Проблемы производительности

### ❌ Очень медленное сканирование

**Причина:** Много векторов, низкий thread count.

**Решение:**

```bash
# Увеличить потоки
python -m strike -t https://example.com --threads 9

# Уменьшить количество векторов
python -m strike -t https://example.com --vectors sqli,xss
```

---

### ❌ High memory usage

**Причина:** Большое количество payload'ов.

**Решение:**

```bash
# Ограничить пэйлоады
python -m strike -t https://example.com --max-payloads 500
```

---

### ❌ Dashboard тормозит

**Причина:** Много логов в консоли.

**Решение:**

1. Очистите консоль: кнопка "Clear"
2. Используйте меньше потоков
3. Перезапустите браузер

---

## Проблемы отчётов

### ❌ Report file is empty

**Причина:** Атака не завершена или нет findings.

**Решение:**

```bash
# Убедитесь что атака завершена
python -m strike -t https://example.com -v

# Проверьте exit code
echo $?  # 0 = нет findings, 1 = есть findings
```

---

### ❌ Unicode errors in report

**Причина:** Проблемы с кодировкой.

**Решение:**

```bash
# Указать кодировку
python -m strike -t https://example.com -o report.md --encoding utf-8
```

---

## Общие советы

### 💡 Debug режим

```bash
python -m strike -t https://example.com -v --debug
```

### 💡 Логи

```bash
# Сохранить логи в файл
python -m strike -t https://example.com 2>&1 | tee strike.log
```

### 💡 Проверка конфигурации

```bash
python -m strike --check-config
```

---

## Контакты

Если проблема не решена:

📧 **Email:** chg@live.ru  
💬 **Telegram:** [@DmLabincev](https://t.me/DmLabincev)  
🐛 **GitHub Issues:** [DmitrL-dev/AISecurity](https://github.com/DmitrL-dev/AISecurity/issues)

---

_SENTINEL Strike v3.0_
