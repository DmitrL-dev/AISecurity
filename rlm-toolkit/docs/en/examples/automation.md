# Automation Examples

Complete automation workflows with RLM agents.

## Email Automation

```python
from rlm_toolkit import RLM
from rlm_toolkit.agents import ReActAgent
from rlm_toolkit.tools import Tool
import smtplib
from email.mime.text import MIMEText

@Tool(name="send_email", description="Send an email")
def send_email(to: str, subject: str, body: str) -> str:
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['To'] = to
    msg['From'] = "bot@example.com"
    
    with smtplib.SMTP('localhost') as server:
        server.send_message(msg)
    return f"Email sent to {to}"

@Tool(name="read_inbox", description="Read recent emails")
def read_inbox(count: int = 10) -> str:
    # Simulated - use imaplib in production
    return """
    1. From: client@company.com - Subject: Urgent request
    2. From: boss@company.com - Subject: Meeting tomorrow
    3. From: newsletter@spam.com - Subject: Amazing offer
    """

class EmailAutomation:
    def __init__(self):
        self.agent = ReActAgent.from_openai(
            "gpt-4o",
            tools=[send_email, read_inbox],
            system_prompt="""
            You are an email automation assistant.
            Help with reading, organizing, and responding to emails.
            For spam, don't respond. For urgent emails, prioritize.
            """
        )
        
    def auto_respond(self, rules: str = None) -> str:
        return self.agent.run(f"""
        Check my inbox and respond to important emails.
        Rules: {rules or 'Respond professionally to urgent requests'}
        """)

# Usage
automation = EmailAutomation()
result = automation.auto_respond("Reply to client emails, ignore newsletters")
```

## Web Scraping Pipeline

```python
from rlm_toolkit import RLM
from rlm_toolkit.agents import ReActAgent
from rlm_toolkit.tools import Tool
import requests
from bs4 import BeautifulSoup
import json

@Tool(name="fetch_page", description="Fetch webpage content")
def fetch_page(url: str) -> str:
    response = requests.get(url, timeout=10)
    soup = BeautifulSoup(response.text, 'html.parser')
    # Remove scripts and styles
    for tag in soup(['script', 'style']):
        tag.decompose()
    return soup.get_text()[:10000]

@Tool(name="extract_links", description="Extract all links from a page")
def extract_links(url: str) -> str:
    response = requests.get(url, timeout=10)
    soup = BeautifulSoup(response.text, 'html.parser')
    links = [a.get('href') for a in soup.find_all('a', href=True)]
    return json.dumps(links[:50])

@Tool(name="save_data", description="Save extracted data to file")
def save_data(filename: str, data: str) -> str:
    with open(filename, 'w') as f:
        f.write(data)
    return f"Saved to {filename}"

class WebScrapingAgent:
    def __init__(self):
        self.agent = ReActAgent.from_openai(
            "gpt-4o",
            tools=[fetch_page, extract_links, save_data]
        )
        
    def scrape(self, task: str) -> str:
        return self.agent.run(task)

# Usage
scraper = WebScrapingAgent()
result = scraper.scrape("""
1. Go to https://news.ycombinator.com
2. Extract the top 10 story titles and links
3. Save to hacker_news.json
""")
```

## File Organization

```python
from rlm_toolkit.agents import ReActAgent
from rlm_toolkit.tools import Tool
import os
import shutil
from pathlib import Path

@Tool(name="list_files", description="List files in directory")
def list_files(directory: str = ".") -> str:
    files = []
    for f in os.listdir(directory):
        path = os.path.join(directory, f)
        size = os.path.getsize(path) if os.path.isfile(path) else 0
        files.append(f"{f} ({'dir' if os.path.isdir(path) else f'{size} bytes'})")
    return "\n".join(files)

@Tool(name="create_folder", description="Create a new folder")
def create_folder(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return f"Created {path}"

@Tool(name="move_file", description="Move file to new location")
def move_file(source: str, destination: str) -> str:
    shutil.move(source, destination)
    return f"Moved {source} to {destination}"

class FileOrganizer:
    def __init__(self):
        self.agent = ReActAgent.from_openai(
            "gpt-4o",
            tools=[list_files, create_folder, move_file],
            system_prompt="""
            Organize files intelligently:
            - Group by type (images, documents, code, etc.)
            - Create appropriate folders
            - Move files to correct locations
            """
        )
        
    def organize(self, directory: str) -> str:
        return self.agent.run(f"""
        Organize all files in {directory}:
        1. List all files
        2. Create folders: images/, documents/, code/, other/
        3. Move each file to appropriate folder based on extension
        """)

# Usage
organizer = FileOrganizer()
result = organizer.organize("./downloads")
```

## Screenshot Monitoring

```python
from rlm_toolkit import RLM
import pyautogui
from datetime import datetime
import time
import base64

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
            """Analyze this screenshot and report:
            1. What application is in focus?
            2. Any error dialogs or warnings?
            3. Any security concerns?
            Return as: {"app": str, "errors": list, "concerns": list}
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
                print(f"⚠️ Alert: {analysis}")
            
            time.sleep(interval)
        
        return self.alerts

# Usage (careful - captures screen)
# monitor = ScreenMonitor()
# alerts = monitor.monitor(interval=60, duration=300)
```

## Database Maintenance

```python
from rlm_toolkit.agents import ReActAgent
from rlm_toolkit.tools import Tool
import sqlite3

@Tool(name="run_query", description="Run SQL query")
def run_query(query: str, db_path: str = "app.db") -> str:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(query)
    
    if query.strip().upper().startswith("SELECT"):
        results = cursor.fetchall()
        return str(results[:100])
    else:
        conn.commit()
        return f"Executed: {cursor.rowcount} rows affected"
    
    conn.close()

@Tool(name="get_schema", description="Get database schema")
def get_schema(db_path: str = "app.db") -> str:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table'")
    schemas = cursor.fetchall()
    conn.close()
    return "\n".join([s[0] for s in schemas if s[0]])

@Tool(name="analyze_table", description="Analyze table statistics")
def analyze_table(table: str, db_path: str = "app.db") -> str:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    count = cursor.fetchone()[0]
    return f"Table {table}: {count} rows"

class DBMaintenanceAgent:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.agent = ReActAgent.from_openai(
            "gpt-4o",
            tools=[run_query, get_schema, analyze_table],
            system_prompt="""
            You are a database maintenance agent.
            - Analyze databases for issues
            - Optimize queries
            - Clean up old data
            Always be careful with DELETE operations.
            """
        )
        
    def maintain(self, task: str) -> str:
        return self.agent.run(f"Database: {self.db_path}\nTask: {task}")

# Usage
agent = DBMaintenanceAgent("production.db")
result = agent.maintain("""
1. Show the schema
2. Find tables with > 1M rows
3. Suggest cleanup for old records
""")
```

## Scheduled Task Runner

```python
from rlm_toolkit import RLM
from rlm_toolkit.agents import ReActAgent
from rlm_toolkit.tools import Tool
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

# Usage
runner = TaskRunner()

runner.schedule_daily(
    "09:00", 
    "morning_summary",
    "Summarize today's news headlines for AI and technology"
)

runner.schedule_hourly(
    "stock_check",
    "What are current S&P 500 futures indicating?"
)

# runner.start()  # Runs forever
```

## CI/CD Helper

```python
from rlm_toolkit import RLM
from rlm_toolkit.agents import ReActAgent
from rlm_toolkit.tools import Tool
import subprocess

@Tool(name="run_tests", description="Run test suite")
def run_tests(test_path: str = "tests/") -> str:
    result = subprocess.run(
        ["pytest", test_path, "-v", "--tb=short"],
        capture_output=True,
        text=True
    )
    return result.stdout + result.stderr

@Tool(name="run_linter", description="Run linter")
def run_linter(path: str = ".") -> str:
    result = subprocess.run(
        ["ruff", "check", path],
        capture_output=True,
        text=True
    )
    return result.stdout + result.stderr

@Tool(name="check_dependencies", description="Check for outdated deps")
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
        Run pre-commit checks:
        1. Run linter and report issues
        2. Run tests and report failures
        3. Summarize what needs to be fixed
        """)
    
    def analyze_failure(self, error_log: str) -> str:
        return self.agent.run(f"""
        Analyze this CI failure and suggest fixes:
        
        {error_log}
        """)

# Usage
helper = CICDHelper()
report = helper.pre_commit_check()
print(report)
```

## Related

- [Examples Gallery](./index.md)
- [Tutorial: Agents](../tutorials/04-agents.md)
- [How-to: Tools](../how-to/tools.md)
