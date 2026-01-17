# Примеры автоматизации

Полные workflow автоматизации с RLM агентами.

## Автоматизация email

```python
from rlm_toolkit import RLM
from rlm_toolkit.agents import ReActAgent
from rlm_toolkit.tools import Tool
import smtplib
from email.mime.text import MIMEText

@Tool(name="send_email", description="Отправить email")
def send_email(to: str, subject: str, body: str) -> str:
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['To'] = to
    msg['From'] = "bot@example.com"
    
    with smtplib.SMTP('localhost') as server:
        server.send_message(msg)
    return f"Email отправлен на {to}"

@Tool(name="read_inbox", description="Прочитать входящие")
def read_inbox(count: int = 10) -> str:
    return """
    1. От: client@company.com - Тема: Срочный запрос
    2. От: boss@company.com - Тема: Встреча завтра
    3. От: newsletter@spam.com - Тема: Невероятное предложение
    """

class EmailAutomation:
    def __init__(self):
        self.agent = ReActAgent.from_openai(
            "gpt-4o",
            tools=[send_email, read_inbox],
            system_prompt="""
            Ты ассистент автоматизации email.
            Помогай с чтением, организацией и ответами на письма.
            На спам не отвечай. Срочные письма приоритизируй.
            """
        )
        
    def auto_respond(self, rules: str = None) -> str:
        return self.agent.run(f"""
        Проверь входящие и ответь на важные письма.
        Правила: {rules or 'Отвечай профессионально на срочные запросы'}
        """)

# Использование
automation = EmailAutomation()
result = automation.auto_respond("Отвечай на письма клиентов, игнорируй рассылки")
```

## Web Scraping Pipeline

```python
from rlm_toolkit import RLM
from rlm_toolkit.agents import ReActAgent
from rlm_toolkit.tools import Tool
import requests
from bs4 import BeautifulSoup
import json

@Tool(name="fetch_page", description="Получить контент страницы")
def fetch_page(url: str) -> str:
    response = requests.get(url, timeout=10)
    soup = BeautifulSoup(response.text, 'html.parser')
    for tag in soup(['script', 'style']):
        tag.decompose()
    return soup.get_text()[:10000]

@Tool(name="extract_links", description="Извлечь все ссылки со страницы")
def extract_links(url: str) -> str:
    response = requests.get(url, timeout=10)
    soup = BeautifulSoup(response.text, 'html.parser')
    links = [a.get('href') for a in soup.find_all('a', href=True)]
    return json.dumps(links[:50])

@Tool(name="save_data", description="Сохранить данные в файл")
def save_data(filename: str, data: str) -> str:
    with open(filename, 'w') as f:
        f.write(data)
    return f"Сохранено в {filename}"

class WebScrapingAgent:
    def __init__(self):
        self.agent = ReActAgent.from_openai(
            "gpt-4o",
            tools=[fetch_page, extract_links, save_data]
        )
        
    def scrape(self, task: str) -> str:
        return self.agent.run(task)

# Использование
scraper = WebScrapingAgent()
result = scraper.scrape("""
1. Перейди на https://news.ycombinator.com
2. Извлеки топ-10 заголовков и ссылок
3. Сохрани в hacker_news.json
""")
```

## Организация файлов

```python
from rlm_toolkit.agents import ReActAgent
from rlm_toolkit.tools import Tool
import os
import shutil
from pathlib import Path

@Tool(name="list_files", description="Список файлов в директории")
def list_files(directory: str = ".") -> str:
    files = []
    for f in os.listdir(directory):
        path = os.path.join(directory, f)
        size = os.path.getsize(path) if os.path.isfile(path) else 0
        files.append(f"{f} ({'dir' if os.path.isdir(path) else f'{size} байт'})")
    return "\n".join(files)

@Tool(name="create_folder", description="Создать папку")
def create_folder(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return f"Создано {path}"

@Tool(name="move_file", description="Переместить файл")
def move_file(source: str, destination: str) -> str:
    shutil.move(source, destination)
    return f"Перемещено {source} в {destination}"

class FileOrganizer:
    def __init__(self):
        self.agent = ReActAgent.from_openai(
            "gpt-4o",
            tools=[list_files, create_folder, move_file],
            system_prompt="""
            Организуй файлы разумно:
            - Группируй по типу (изображения, документы, код и т.д.)
            - Создавай подходящие папки
            - Перемещай файлы в правильные места
            """
        )
        
    def organize(self, directory: str) -> str:
        return self.agent.run(f"""
        Организуй все файлы в {directory}:
        1. Список всех файлов
        2. Создай папки: images/, documents/, code/, other/
        3. Перемести каждый файл в подходящую папку по расширению
        """)

# Использование
organizer = FileOrganizer()
result = organizer.organize("./downloads")
```

## Мониторинг экрана

```python
from rlm_toolkit import RLM
import pyautogui
from datetime import datetime
import time

class ScreenMonitor:
    def __init__(self):
        self.rlm = RLM.from_openai("gpt-4o")
        self.alerts = []
        
    def capture_screen(self) -> str:
        screenshot = pyautogui.screenshot()
        screenshot.save("current_screen.png")
        return "current_screen.png"
    
    def analyze_screen(self, image_path: str) -> dict:
        result = self.rlm.run(
            """Проанализируй этот скриншот и сообщи:
            1. Какое приложение в фокусе?
            2. Есть ли диалоги ошибок или предупреждений?
            3. Есть ли проблемы безопасности?
            Верни как: {"app": str, "errors": list, "concerns": list}
            """,
            images=[image_path]
        )
        return eval(result)
    
    def monitor(self, interval: int = 60, duration: int = 3600):
        end_time = time.time() + duration
        
        while time.time() < end_time:
            image = self.capture_screen()
            analysis = self.analyze_screen(image)
            
            if analysis.get("errors") or analysis.get("concerns"):
                self.alerts.append({
                    "time": datetime.now().isoformat(),
                    "analysis": analysis
                })
                print(f"⚠️ Алерт: {analysis}")
            
            time.sleep(interval)
        
        return self.alerts
```

## Обслуживание базы данных

```python
from rlm_toolkit.agents import ReActAgent
from rlm_toolkit.tools import Tool
import sqlite3

@Tool(name="run_query", description="Выполнить SQL запрос")
def run_query(query: str, db_path: str = "app.db") -> str:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(query)
    
    if query.strip().upper().startswith("SELECT"):
        results = cursor.fetchall()
        return str(results[:100])
    else:
        conn.commit()
        return f"Выполнено: {cursor.rowcount} строк затронуто"
    
    conn.close()

@Tool(name="get_schema", description="Получить схему базы данных")
def get_schema(db_path: str = "app.db") -> str:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table'")
    schemas = cursor.fetchall()
    conn.close()
    return "\n".join([s[0] for s in schemas if s[0]])

@Tool(name="analyze_table", description="Анализ статистики таблицы")
def analyze_table(table: str, db_path: str = "app.db") -> str:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    count = cursor.fetchone()[0]
    return f"Таблица {table}: {count} строк"

class DBMaintenanceAgent:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.agent = ReActAgent.from_openai(
            "gpt-4o",
            tools=[run_query, get_schema, analyze_table],
            system_prompt="""
            Ты агент обслуживания баз данных.
            - Анализируй базы данных на проблемы
            - Оптимизируй запросы
            - Очищай старые данные
            Всегда будь осторожен с DELETE операциями.
            """
        )
        
    def maintain(self, task: str) -> str:
        return self.agent.run(f"База данных: {self.db_path}\nЗадача: {task}")

# Использование
agent = DBMaintenanceAgent("production.db")
result = agent.maintain("""
1. Покажи схему
2. Найди таблицы с > 1M строк
3. Предложи очистку старых записей
""")
```

## Планировщик задач

```python
from rlm_toolkit import RLM
import schedule
import time
from datetime import datetime

class TaskRunner:
    def __init__(self):
        self.rlm = RLM.from_openai("gpt-4o")
        self.logs = []
        
    def run_task(self, task_name: str, task_prompt: str) -> str:
        result = self.rlm.run(task_prompt)
        self.logs.append({
            "task": task_name,
            "time": datetime.now().isoformat(),
            "result": result[:500]
        })
        return result
    
    def schedule_daily(self, time_str: str, task_name: str, task_prompt: str):
        schedule.every().day.at(time_str).do(
            self.run_task, task_name, task_prompt
        )
        
    def schedule_hourly(self, task_name: str, task_prompt: str):
        schedule.every().hour.do(
            self.run_task, task_name, task_prompt
        )
        
    def start(self):
        while True:
            schedule.run_pending()
            time.sleep(60)

# Использование
runner = TaskRunner()

runner.schedule_daily(
    "09:00", 
    "morning_summary",
    "Суммируй новости AI и технологий"
)

runner.schedule_hourly(
    "stock_check",
    "Что показывают фьючерсы S&P 500?"
)
```

## CI/CD помощник

```python
from rlm_toolkit import RLM
from rlm_toolkit.agents import ReActAgent
from rlm_toolkit.tools import Tool
import subprocess

@Tool(name="run_tests", description="Запустить тесты")
def run_tests(test_path: str = "tests/") -> str:
    result = subprocess.run(
        ["pytest", test_path, "-v", "--tb=short"],
        capture_output=True,
        text=True
    )
    return result.stdout + result.stderr

@Tool(name="run_linter", description="Запустить линтер")
def run_linter(path: str = ".") -> str:
    result = subprocess.run(
        ["ruff", "check", path],
        capture_output=True,
        text=True
    )
    return result.stdout + result.stderr

@Tool(name="check_dependencies", description="Проверить устаревшие зависимости")
def check_dependencies() -> str:
    result = subprocess.run(
        ["pip", "list", "--outdated"],
        capture_output=True,
        text=True
    )
    return result.stdout

class CICDHelper:
    def __init__(self):
        self.agent = ReActAgent.from_openai(
            "gpt-4o",
            tools=[run_tests, run_linter, check_dependencies]
        )
        
    def pre_commit_check(self) -> str:
        return self.agent.run("""
        Выполни pre-commit проверки:
        1. Запусти линтер и сообщи о проблемах
        2. Запусти тесты и сообщи о падениях
        3. Суммируй что нужно исправить
        """)
    
    def analyze_failure(self, error_log: str) -> str:
        return self.agent.run(f"""
        Проанализируй этот CI падение и предложи исправления:
        
        {error_log}
        """)

# Использование
helper = CICDHelper()
report = helper.pre_commit_check()
print(report)
```

## Связанное

- [Галерея примеров](./index.md)
- [Туториал: Агенты](../tutorials/04-agents.md)
- [How-to: Инструменты](../how-to/tools.md)
