# Продвинутые примеры

Enterprise-уровень, production-ready примеры, демонстрирующие мощные возможности RLM-Toolkit.

---

## 1. Автономный исследовательский агент

Полностью автономный агент, который исследует темы, находит источники, анализирует информацию и создаёт комплексные отчёты с цитатами.

```python
from rlm_toolkit import RLM
from rlm_toolkit.agents import ReActAgent
from rlm_toolkit.agents.multiagent import MetaMatrix, Agent
from rlm_toolkit.tools import Tool, WebSearchTool, ArxivTool, WikipediaTool
from rlm_toolkit.memory import HierarchicalMemory
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import json

# Модели данных
class Source(BaseModel):
    title: str
    url: str
    snippet: str
    relevance_score: float

class Section(BaseModel):
    heading: str
    content: str
    sources: List[str]

class ResearchReport(BaseModel):
    title: str
    executive_summary: str
    sections: List[Section]
    conclusions: List[str]
    sources: List[Source]
    generated_at: str

# Пользовательские инструменты
@Tool(name="save_source", description="Сохранить источник для цитирования")
def save_source(title: str, url: str, snippet: str, relevance: float) -> str:
    return json.dumps({"saved": True, "id": hash(url)})

@Tool(name="write_section", description="Написать раздел отчёта")
def write_section(heading: str, content: str, source_ids: List[str]) -> str:
    return json.dumps({"section": heading, "words": len(content.split())})

class AutonomousResearchAgent:
    """
    Многоэтапный исследовательский агент:
    1. Планирует стратегию исследования
    2. Собирает источники с разных платформ
    3. Анализирует и синтезирует информацию
    4. Создаёт структурированный отчёт с цитатами
    """
    
    def __init__(self):
        self.memory = HierarchicalMemory(persist_directory="./research_memory")
        
        # Агент-планировщик
        self.planner = RLM.from_openai("gpt-4o")
        self.planner.set_system_prompt("""
        Вы — планировщик исследований. По заданной теме:
        1. Определите ключевые вопросы для ответа
        2. Перечислите источники для проверки (академические, веб, новости)
        3. Определите структуру отчёта
        4. Оцените необходимую глубину
        
        Будьте тщательны, но сфокусированы.
        """)
        
        # Агент-исследователь
        self.researcher = ReActAgent.from_openai(
            "gpt-4o",
            tools=[
                WebSearchTool(provider="ddg", max_results=10),
                ArxivTool(max_results=5),
                WikipediaTool(),
                save_source
            ],
            system_prompt="""
            Вы — скрупулёзный исследователь. Для каждого источника:
            - Проверьте достоверность
            - Извлеките ключевые факты
            - Отметьте противоречия
            - Сохраните с оценкой релевантности
            
            Стремитесь к разнообразным, авторитетным источникам.
            """,
            max_iterations=20
        )
        
        # Агент-аналитик
        self.analyst = RLM.from_anthropic("claude-3-sonnet")
        self.analyst.set_system_prompt("""
        Вы — критический аналитик. По результатам исследования:
        1. Выявите закономерности и тренды
        2. Отметьте противоречия или пробелы
        3. Синтезируйте в связное повествование
        4. Выделите ключевые инсайты
        
        Будьте объективны и опирайтесь на доказательства.
        """)
        
        # Агент-писатель
        self.writer = RLM.from_openai("gpt-4o")
        self.writer.set_system_prompt("""
        Вы — эксперт-технический писатель. Создавайте:
        - Ясную, увлекательную прозу
        - Правильные цитаты [1], [2] и т.д.
        - Логичный переход между разделами
        - Резюме для быстрого чтения
        
        Пишите для образованной, но не специализированной аудитории.
        """)
        
    def research(self, topic: str, depth: str = "comprehensive") -> ResearchReport:
        """Выполнить полный исследовательский пайплайн."""
        
        print(f"🔬 Начинаем исследование: {topic}")
        
        # Фаза 1: Планирование
        print("📋 Фаза 1: Планирование стратегии исследования...")
        plan = self.planner.run(f"""
        Создайте план исследования для: {topic}
        Глубина: {depth}
        
        Верните:
        1. Ключевые вопросы (5-10)
        2. Типы источников для проверки
        3. Структура отчёта
        """)
        
        # Фаза 2: Сбор источников
        print("🔍 Фаза 2: Сбор источников...")
        sources_raw = self.researcher.run(f"""
        Тема исследования: {topic}
        
        План: {plan}
        
        Найдите и сохраните минимум 10 качественных источников.
        Для каждого источника сохраните с оценкой релевантности.
        Охватите: академические статьи, авторитетные сайты, новости.
        """)
        
        # Фаза 3: Анализ
        print("🧠 Фаза 3: Анализ находок...")
        analysis = self.analyst.run(f"""
        Тема: {topic}
        
        Результаты исследования:
        {sources_raw}
        
        Предоставьте:
        1. Выявленные ключевые темы
        2. Основные находки по каждой теме
        3. Противоречия или дебаты
        4. Пробелы в знаниях
        5. Синтез доказательств
        """)
        
        # Фаза 4: Написание отчёта
        print("✍️ Фаза 4: Написание отчёта...")
        report_content = self.writer.run(f"""
        Тема: {topic}
        
        Анализ:
        {analysis}
        
        Краткое содержание источников:
        {sources_raw}
        
        Напишите комплексный исследовательский отчёт с:
        1. Резюме (200 слов)
        2. Введение
        3. Основные находки (3-5 разделов)
        4. Обсуждение
        5. Выводы
        6. Правильно оформленные цитаты
        """)
        
        # Фаза 5: Структурированный вывод
        print("📄 Фаза 5: Форматирование финального отчёта...")
        report = self.writer.run_structured(
            f"""
            Преобразуйте этот отчёт в структурированный формат:
            
            {report_content}
            """,
            output_schema=ResearchReport
        )
        
        report.generated_at = datetime.now().isoformat()
        
        # Сохранение в память
        self.memory.add_episode(
            f"Исследование по теме {topic}",
            metadata={"topic": topic, "depth": depth}
        )
        
        print("✅ Исследование завершено!")
        return report
    
    def save_report(self, report: ResearchReport, path: str):
        """Сохранить отчёт в формате Markdown."""
        md = f"# {report.title}\n\n"
        md += f"*Сгенерировано: {report.generated_at}*\n\n"
        md += f"## Резюме\n\n{report.executive_summary}\n\n"
        
        for section in report.sections:
            md += f"## {section.heading}\n\n{section.content}\n\n"
            if section.sources:
                md += f"*Источники: {', '.join(section.sources)}*\n\n"
        
        md += "## Выводы\n\n"
        for i, conclusion in enumerate(report.conclusions, 1):
            md += f"{i}. {conclusion}\n"
        
        md += "\n## Список литературы\n\n"
        for i, source in enumerate(report.sources, 1):
            md += f"[{i}] {source.title}. {source.url}\n"
        
        with open(path, "w", encoding="utf-8") as f:
            f.write(md)

# Использование
if __name__ == "__main__":
    agent = AutonomousResearchAgent()
    
    report = agent.research(
        topic="Влияние больших языковых моделей на практики разработки ПО в 2024",
        depth="comprehensive"
    )
    
    agent.save_report(report, "llm_impact_research.md")
    
    print(f"\nОтчёт: {report.title}")
    print(f"Разделов: {len(report.sections)}")
    print(f"Источников: {len(report.sources)}")
```

---

## 2. Мультимодальный RAG-пайплайн

RAG-система, обрабатывающая PDF, изображения, аудио и видео в едином пайплайне.

```python
from rlm_toolkit import RLM, RLMConfig
from rlm_toolkit.loaders import PDFLoader, ImageLoader, AudioLoader, VideoLoader
from rlm_toolkit.splitters import RecursiveTextSplitter, SemanticSplitter
from rlm_toolkit.embeddings import OpenAIEmbeddings, MultiModalEmbeddings
from rlm_toolkit.vectorstores import ChromaVectorStore
from rlm_toolkit.retrievers import HybridRetriever, MultiModalRetriever
from pydantic import BaseModel
from typing import List, Union, Optional
from pathlib import Path
import base64

class ContentChunk(BaseModel):
    content: str
    content_type: str  # text, image, audio, video
    source: str
    metadata: dict

class MultiModalRAG:
    """
    Унифицированный RAG-пайплайн для различных типов контента:
    - PDF с текстом и изображениями
    - Отдельные изображения (диаграммы, графики)
    - Аудиофайлы (транскрибированные)
    - Видеофайлы (транскрипция + ключевые кадры)
    """
    
    def __init__(self, collection_name: str = "multimodal"):
        # Текстовые эмбеддинги
        self.text_embeddings = OpenAIEmbeddings("text-embedding-3-large")
        
        # LLM с поддержкой визуального контента
        self.vision_llm = RLM.from_openai("gpt-4o")
        
        # Транскрипция аудио
        self.whisper = OpenAI()
        
        # Векторное хранилище с несколькими коллекциями
        self.text_store = ChromaVectorStore(
            collection_name=f"{collection_name}_text",
            embedding_function=self.text_embeddings
        )
        self.image_store = ChromaVectorStore(
            collection_name=f"{collection_name}_images",
            embedding_function=self.text_embeddings  # Храним описания изображений
        )
        
        # Гибридный ретривер
        self.retriever = MultiModalRetriever(
            text_store=self.text_store,
            image_store=self.image_store,
            text_weight=0.7,
            image_weight=0.3
        )
        
        # Основной QA LLM
        self.qa_llm = RLM.from_openai("gpt-4o")
        self.qa_llm.set_system_prompt("""
        Вы — мультимодальный ИИ-ассистент. Вы понимаете и анализируете:
        - Текст из документов
        - Изображения и диаграммы
        - Транскрибированное аудио/видео
        
        Давайте комплексные ответы, используя весь доступный контекст.
        При необходимости ссылайтесь на конкретные источники.
        """)
        
    def ingest_pdf(self, path: str) -> int:
        """Загрузить PDF с текстом и встроенными изображениями."""
        loader = PDFLoader(path, extract_images=True)
        docs = loader.load()
        
        text_chunks = []
        image_chunks = []
        
        for doc in docs:
            # Разделение текста
            if doc.page_content:
                splitter = RecursiveTextSplitter(chunk_size=1000, chunk_overlap=200)
                text_chunks.extend(splitter.split_documents([doc]))
            
            # Обработка изображений
            if doc.metadata.get("images"):
                for img in doc.metadata["images"]:
                    description = self._describe_image(img["data"])
                    image_chunks.append(ContentChunk(
                        content=description,
                        content_type="image",
                        source=f"{path}:page{doc.metadata['page']}",
                        metadata={"image_data": img["data"]}
                    ))
        
        self.text_store.add_documents(text_chunks)
        for chunk in image_chunks:
            self.image_store.add_texts([chunk.content], metadatas=[chunk.metadata])
        
        return len(text_chunks) + len(image_chunks)
    
    def ingest_image(self, path: str) -> int:
        """Загрузить отдельное изображение."""
        with open(path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode()
        
        description = self._describe_image(image_data)
        
        self.image_store.add_texts(
            [description],
            metadatas=[{"source": path, "image_data": image_data}]
        )
        
        return 1
    
    def ingest_audio(self, path: str) -> int:
        """Загрузить аудиофайл через транскрипцию."""
        with open(path, "rb") as f:
            transcript = self.whisper.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                response_format="verbose_json"
            )
        
        # Разделение транскрипции по сегментам
        chunks = []
        for segment in transcript.segments:
            chunks.append(ContentChunk(
                content=segment["text"],
                content_type="audio",
                source=path,
                metadata={
                    "start": segment["start"],
                    "end": segment["end"]
                }
            ))
        
        self.text_store.add_texts(
            [c.content for c in chunks],
            metadatas=[c.metadata for c in chunks]
        )
        
        return len(chunks)
    
    def ingest_video(self, path: str, extract_frames: bool = True) -> int:
        """Загрузить видео: транскрипция + ключевые кадры."""
        chunks_added = 0
        
        # Извлечение аудио и транскрипция
        audio_path = self._extract_audio(path)
        chunks_added += self.ingest_audio(audio_path)
        
        # Извлечение и анализ ключевых кадров
        if extract_frames:
            keyframes = self._extract_keyframes(path, interval=30)  # Каждые 30 секунд
            for timestamp, frame_data in keyframes:
                description = self._describe_image(frame_data)
                self.image_store.add_texts(
                    [description],
                    metadatas={
                        "source": path,
                        "timestamp": timestamp,
                        "image_data": frame_data
                    }
                )
                chunks_added += 1
        
        return chunks_added
    
    def _describe_image(self, image_data: str) -> str:
        """Использовать Vision LLM для описания изображения."""
        return self.vision_llm.run(
            "Опишите это изображение подробно. Укажите: основной объект, видимый текст, "
            "цвета, компоновку, любые данные/графики. Будьте исчерпывающими.",
            images=[image_data]
        )
    
    def _extract_audio(self, video_path: str) -> str:
        """Извлечь аудио из видео."""
        import subprocess
        audio_path = video_path.replace(".mp4", ".mp3")
        subprocess.run([
            "ffmpeg", "-i", video_path, "-vn", "-acodec", "mp3", audio_path
        ], capture_output=True)
        return audio_path
    
    def _extract_keyframes(self, video_path: str, interval: int) -> List[tuple]:
        """Извлечь ключевые кадры с заданным интервалом."""
        import cv2
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        keyframes = []
        frame_interval = int(fps * interval)
        frame_count = 0
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_count % frame_interval == 0:
                _, buffer = cv2.imencode('.jpg', frame)
                frame_data = base64.b64encode(buffer).decode()
                timestamp = frame_count / fps
                keyframes.append((timestamp, frame_data))
            
            frame_count += 1
        
        cap.release()
        return keyframes
    
    def query(
        self,
        question: str,
        include_images: bool = True,
        k: int = 5
    ) -> dict:
        """Запрос по всем модальностям."""
        
        # Поиск по всем хранилищам
        text_results = self.text_store.similarity_search(question, k=k)
        
        if include_images:
            image_results = self.image_store.similarity_search(question, k=3)
        else:
            image_results = []
        
        # Объединение контекста
        context = "## Текстовый контекст:\n"
        for doc in text_results:
            context += f"- {doc.page_content}\n"
            context += f"  Источник: {doc.metadata.get('source', 'неизвестен')}\n\n"
        
        if image_results:
            context += "\n## Контекст изображений:\n"
            for doc in image_results:
                context += f"- [Изображение] {doc.page_content}\n"
        
        # Генерация ответа
        answer = self.qa_llm.run(f"""
        Вопрос: {question}
        
        Контекст:
        {context}
        
        Дайте исчерпывающий ответ, используя доступный контекст.
        Ссылайтесь на конкретные источники и описывайте релевантные изображения.
        """)
        
        return {
            "answer": answer,
            "text_sources": [d.metadata.get("source") for d in text_results],
            "image_sources": [d.metadata.get("source") for d in image_results]
        }

# Использование
if __name__ == "__main__":
    rag = MultiModalRAG("company_docs")
    
    # Загрузка различного контента
    rag.ingest_pdf("quarterly_report.pdf")
    rag.ingest_image("architecture_diagram.png")
    rag.ingest_audio("earnings_call.mp3")
    rag.ingest_video("product_demo.mp4")
    
    # Запрос по всем модальностям
    result = rag.query("Какой был доход в Q3 и как архитектура поддерживает масштабирование?")
    print(result["answer"])
```

---

## 3. Агент Code Review

Агент, анализирующий pull requests, находящий баги, предлагающий улучшения и генерирующий тесты.

```python
from rlm_toolkit import RLM
from rlm_toolkit.agents import ReActAgent
from rlm_toolkit.tools import Tool
from rlm_toolkit.memory import BufferMemory
from pydantic import BaseModel
from typing import List, Optional
from enum import Enum
import subprocess
import json
import ast

class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

class CodeIssue(BaseModel):
    file: str
    line: int
    severity: Severity
    category: str  # bug, security, performance, style, maintainability
    description: str
    suggestion: str
    code_snippet: Optional[str]

class ReviewResult(BaseModel):
    summary: str
    issues: List[CodeIssue]
    suggested_tests: List[str]
    refactoring_suggestions: List[str]
    approval_recommendation: str  # approve, request_changes, comment

# Инструменты для анализа кода
@Tool(name="read_file", description="Прочитать файл из репозитория")
def read_file(file_path: str) -> str:
    try:
        with open(file_path, "r") as f:
            return f.read()
    except Exception as e:
        return f"Ошибка чтения файла: {e}"

@Tool(name="get_diff", description="Получить git diff для файла")
def get_diff(file_path: str) -> str:
    result = subprocess.run(
        ["git", "diff", "HEAD~1", file_path],
        capture_output=True,
        text=True
    )
    return result.stdout or "Нет изменений"

@Tool(name="run_linter", description="Запустить линтер на файле")
def run_linter(file_path: str) -> str:
    result = subprocess.run(
        ["ruff", "check", file_path, "--output-format=json"],
        capture_output=True,
        text=True
    )
    return result.stdout

@Tool(name="check_types", description="Запустить проверку типов")
def check_types(file_path: str) -> str:
    result = subprocess.run(
        ["mypy", file_path, "--output=json"],
        capture_output=True,
        text=True
    )
    return result.stdout or result.stderr

@Tool(name="run_tests", description="Запустить тесты для модуля")
def run_tests(module_path: str) -> str:
    result = subprocess.run(
        ["pytest", module_path, "-v", "--tb=short"],
        capture_output=True,
        text=True
    )
    return result.stdout + result.stderr

@Tool(name="analyze_complexity", description="Анализ сложности кода")
def analyze_complexity(file_path: str) -> str:
    result = subprocess.run(
        ["radon", "cc", file_path, "-j"],
        capture_output=True,
        text=True
    )
    return result.stdout

class CodeReviewAgent:
    """
    Комплексный агент код-ревью:
    1. Анализирует изменения кода
    2. Находит баги, проблемы безопасности, производительности
    3. Проверяет стиль и поддерживаемость
    4. Предлагает улучшения и рефакторинг
    5. Генерирует тест-кейсы для нового кода
    """
    
    def __init__(self):
        # Основной агент ревью
        self.reviewer = ReActAgent.from_openai(
            "gpt-4o",
            tools=[read_file, get_diff, run_linter, check_types, run_tests, analyze_complexity],
            system_prompt="""
            Вы — эксперт код-ревью с глубокими знаниями:
            - Паттерны проектирования и лучшие практики
            - Уязвимости безопасности (OWASP Top 10)
            - Оптимизация производительности
            - Принципы чистого кода
            - Стратегии тестирования
            
            Для каждого файла систематически:
            1. Прочитайте полный контент файла
            2. Получите diff для просмотра изменений
            3. Запустите линтер и проверку типов
            4. Проанализируйте сложность
            5. Выявите проблемы по категориям
            
            Будьте тщательны, но конструктивны. Фокусируйтесь на actionable фидбеке.
            """,
            max_iterations=30
        )
        
        # Специалист по безопасности
        self.security_agent = RLM.from_anthropic("claude-3-sonnet")
        self.security_agent.set_system_prompt("""
        Вы — эксперт по безопасности. Анализируйте код на:
        - SQL-инъекции
        - XSS-уязвимости
        - Ошибки аутентификации/авторизации
        - Небезопасную десериализацию
        - Утечку чувствительных данных
        - SSRF-уязвимости
        - Path traversal
        - Command injection
        
        Сообщайте ТОЛЬКО подтверждённые проблемы безопасности с серьёзностью и исправлением.
        """)
        
        # Генератор тестов
        self.test_generator = RLM.from_openai("gpt-4o")
        self.test_generator.set_system_prompt("""
        Вы — инженер по тестированию. По заданному коду:
        1. Определите тестируемые единицы (функции, классы, методы)
        2. Сгенерируйте комплексные тест-кейсы, покрывающие:
           - Happy path
           - Граничные случаи
           - Обработку ошибок
           - Пограничные условия
        3. Используйте стиль pytest с описательными именами
        4. Включите фикстуры и моки где необходимо
        """)
        
    def review_pr(self, files: List[str]) -> ReviewResult:
        """Провести ревью pull request."""
        all_issues = []
        
        # Фаза 1: Первичный анализ с инструментами
        print("🔍 Фаза 1: Анализ изменений кода...")
        for file in files:
            analysis = self.reviewer.run(f"""
            Проведите ревью файла: {file}
            
            Шаги:
            1. Прочитать файл
            2. Получить diff
            3. Запустить линтер
            4. Проверить типы
            5. Проанализировать сложность
            
            Сообщите обо всех найденных проблемах с файлом, строкой, серьёзностью и предложением.
            """)
            
            # Парсинг проблем из анализа
            issues = self._parse_issues(analysis, file)
            all_issues.extend(issues)
        
        # Фаза 2: Проверка безопасности
        print("🔐 Фаза 2: Анализ безопасности...")
        for file in files:
            if file.endswith(".py"):
                with open(file, "r") as f:
                    code = f.read()
                
                security_issues = self.security_agent.run(f"""
                Проанализируйте этот код на уязвимости безопасности:
                
                ```python
                {code}
                ```
                
                Сообщите о каждой проблеме с номером строки и серьёзностью.
                """)
                
                issues = self._parse_security_issues(security_issues, file)
                all_issues.extend(issues)
        
        # Фаза 3: Генерация тестов
        print("🧪 Фаза 3: Генерация предложений по тестам...")
        test_suggestions = []
        for file in files:
            if file.endswith(".py") and not file.startswith("test_"):
                with open(file, "r") as f:
                    code = f.read()
                
                tests = self.test_generator.run(f"""
                Сгенерируйте pytest тест-кейсы для:
                
                ```python
                {code}
                ```
                
                Сфокусируйтесь на новых или изменённых функциях.
                """)
                test_suggestions.append(tests)
        
        # Фаза 4: Синтез
        print("📝 Фаза 4: Подготовка резюме ревью...")
        summary = self._generate_summary(all_issues)
        recommendation = self._get_recommendation(all_issues)
        
        refactoring = self._suggest_refactoring(files)
        
        return ReviewResult(
            summary=summary,
            issues=all_issues,
            suggested_tests=test_suggestions,
            refactoring_suggestions=refactoring,
            approval_recommendation=recommendation
        )
    
    def _parse_issues(self, analysis: str, file: str) -> List[CodeIssue]:
        """Извлечь проблемы из текста анализа."""
        extractor = RLM.from_openai("gpt-4o-mini")
        issues_json = extractor.run(f"""
        Извлеките проблемы кода из этого анализа как JSON-список:
        
        {analysis}
        
        Формат: [{{"file": str, "line": int, "severity": str, "category": str, "description": str, "suggestion": str}}]
        """)
        
        try:
            issues_data = json.loads(issues_json)
            return [CodeIssue(**issue) for issue in issues_data]
        except:
            return []
    
    def _parse_security_issues(self, analysis: str, file: str) -> List[CodeIssue]:
        """Извлечь проблемы безопасности."""
        issues = self._parse_issues(analysis, file)
        for issue in issues:
            issue.category = "security"
        return issues
    
    def _generate_summary(self, issues: List[CodeIssue]) -> str:
        """Сгенерировать резюме ревью."""
        critical = len([i for i in issues if i.severity == Severity.CRITICAL])
        high = len([i for i in issues if i.severity == Severity.HIGH])
        medium = len([i for i in issues if i.severity == Severity.MEDIUM])
        low = len([i for i in issues if i.severity == Severity.LOW])
        
        return f"""
        ## Резюме Code Review
        
        **Всего найдено проблем:** {len(issues)}
        - 🔴 Критичных: {critical}
        - 🟠 Высоких: {high}
        - 🟡 Средних: {medium}
        - 🟢 Низких: {low}
        
        **Категории:**
        - Безопасность: {len([i for i in issues if i.category == 'security'])}
        - Баги: {len([i for i in issues if i.category == 'bug'])}
        - Производительность: {len([i for i in issues if i.category == 'performance'])}
        - Стиль: {len([i for i in issues if i.category == 'style'])}
        """
    
    def _get_recommendation(self, issues: List[CodeIssue]) -> str:
        """Определить рекомендацию по аппруву."""
        critical = len([i for i in issues if i.severity == Severity.CRITICAL])
        high = len([i for i in issues if i.severity == Severity.HIGH])
        
        if critical > 0:
            return "request_changes"
        elif high > 2:
            return "request_changes"
        elif high > 0:
            return "comment"
        else:
            return "approve"
    
    def _suggest_refactoring(self, files: List[str]) -> List[str]:
        """Предложить улучшения рефакторинга."""
        suggestions = []
        
        for file in files:
            with open(file, "r") as f:
                code = f.read()
            
            refactoring = RLM.from_openai("gpt-4o").run(f"""
            Предложите улучшения рефакторинга для:
            
            ```python
            {code}
            ```
            
            Сфокусируйтесь на:
            - Возможностях Extract Method
            - Декомпозиции классов
            - Применении паттернов проектирования
            - Нарушениях DRY
            
            Дайте конкретные, actionable предложения.
            """)
            suggestions.append(f"## {file}\n{refactoring}")
        
        return suggestions

# Использование
if __name__ == "__main__":
    agent = CodeReviewAgent()
    
    # Ревью изменённых файлов
    files = [
        "src/api/handlers.py",
        "src/services/user_service.py",
        "src/utils/validators.py"
    ]
    
    result = agent.review_pr(files)
    
    print(result.summary)
    print(f"\nРекомендация: {result.approval_recommendation}")
    
    for issue in result.issues:
        print(f"\n[{issue.severity}] {issue.file}:{issue.line}")
        print(f"  {issue.description}")
        print(f"  Предложение: {issue.suggestion}")
```

---

## 4. Анализатор юридических документов

Enterprise-ИИ для анализа контрактов, выявления рисков и генерации поправок.

```python
from rlm_toolkit import RLM, RLMConfig
from rlm_toolkit.loaders import PDFLoader
from rlm_toolkit.splitters import RecursiveTextSplitter
from rlm_toolkit.embeddings import OpenAIEmbeddings
from rlm_toolkit.vectorstores import ChromaVectorStore
from pydantic import BaseModel
from typing import List, Optional, Dict
from enum import Enum
from datetime import date
import json

class RiskLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class ClauseType(str, Enum):
    INDEMNIFICATION = "indemnification"
    LIABILITY = "liability"
    TERMINATION = "termination"
    CONFIDENTIALITY = "confidentiality"
    IP_OWNERSHIP = "ip_ownership"
    PAYMENT = "payment"
    DISPUTE = "dispute"
    GOVERNING_LAW = "governing_law"
    FORCE_MAJEURE = "force_majeure"
    ASSIGNMENT = "assignment"

class Clause(BaseModel):
    type: ClauseType
    text: str
    page: int
    risk_level: RiskLevel
    analysis: str
    industry_standard: bool
    concerns: List[str]

class Party(BaseModel):
    name: str
    role: str  # buyer, seller, licensor, licensee и т.д.
    obligations: List[str]
    rights: List[str]

class ContractAnalysis(BaseModel):
    title: str
    parties: List[Party]
    effective_date: Optional[str]
    term: Optional[str]
    total_value: Optional[str]
    clauses: List[Clause]
    overall_risk: RiskLevel
    negotiation_points: List[str]
    missing_clauses: List[str]

class Amendment(BaseModel):
    clause_type: ClauseType
    original_text: str
    proposed_text: str
    rationale: str
    risk_reduction: str

class LegalDocumentAnalyzer:
    """
    Enterprise-анализатор юридических документов:
    1. Извлекает и категоризирует статьи
    2. Выявляет риски и нестандартные условия
    3. Сравнивает с лучшими практиками
    4. Генерирует предложения по поправкам
    5. Создаёт стратегии переговоров
    """
    
    def __init__(self):
        # Основной юридический аналитик
        self.analyst = RLM.from_anthropic("claude-3-opus")
        self.analyst.set_system_prompt("""
        Вы — опытный корпоративный юрист с 20+ годами опыта в:
        - M&A сделках
        - Коммерческих контрактах
        - Лицензировании технологий
        - Трудовых договорах
        
        Анализируйте контракты с предельной точностью. Выявляйте:
        - Нестандартные или необычные условия
        - Скрытые риски и обязательства
        - Односторонние положения
        - Отсутствующие стандартные защиты
        
        Всегда цитируйте конкретные формулировки контракта.
        """)
        
        # Специалист по оценке рисков
        self.risk_assessor = RLM.from_openai("gpt-4o")
        self.risk_assessor.set_system_prompt("""
        Вы — аналитик юридических рисков. Оценивайте статьи на:
        - Финансовые риски
        - Операционные ограничения
        - Риски соблюдения регуляций
        - Репутационные риски
        - Проблемы с исполнимостью
        
        Где возможно, квантифицируйте риски.
        """)
        
        # Составитель поправок
        self.drafter = RLM.from_anthropic("claude-3-sonnet")
        self.drafter.set_system_prompt("""
        Вы — старший составитель контрактов. Создавайте поправки, которые:
        - Используют точный юридический язык
        - Исполнимы в применимой юрисдикции
        - Сбалансированы между сторонами
        - Следуют отраслевым стандартам
        
        Предоставляйте чёткое обоснование каждого изменения.
        """)
        
        # База лучших практик
        self.embeddings = OpenAIEmbeddings("text-embedding-3-large")
        self.best_practices_store = ChromaVectorStore(
            collection_name="legal_best_practices",
            embedding_function=self.embeddings
        )
        
    def analyze_contract(self, pdf_path: str) -> ContractAnalysis:
        """Полный анализ контракта."""
        
        # Загрузка и парсинг
        print("📄 Загрузка контракта...")
        docs = PDFLoader(pdf_path).load()
        full_text = "\n\n".join([d.page_content for d in docs])
        
        # Извлечение базовой информации
        print("📋 Извлечение деталей контракта...")
        basic_info = self.analyst.run(f"""
        Извлеките из этого контракта:
        1. Название/тип документа
        2. Все стороны с их ролями
        3. Дата вступления в силу
        4. Срок действия
        5. Общая стоимость контракта (если указана)
        
        Контракт:
        {full_text[:30000]}
        """)
        
        # Идентификация и анализ статей
        print("🔍 Анализ статей...")
        clauses = self._analyze_clauses(full_text)
        
        # Оценка рисков
        print("⚠️ Оценка рисков...")
        for clause in clauses:
            clause.risk_level = self._assess_clause_risk(clause)
        
        # Проверка отсутствующих статей
        print("📝 Проверка полноты...")
        missing = self._check_missing_clauses(clauses)
        
        # Генерация точек для переговоров
        print("🎯 Определение точек переговоров...")
        negotiation_points = self._generate_negotiation_points(clauses)
        
        # Расчёт общего риска
        overall_risk = self._calculate_overall_risk(clauses)
        
        return ContractAnalysis(
            title=self._extract_title(basic_info),
            parties=self._extract_parties(basic_info),
            effective_date=self._extract_field(basic_info, "дата вступления"),
            term=self._extract_field(basic_info, "срок"),
            total_value=self._extract_field(basic_info, "стоимость"),
            clauses=clauses,
            overall_risk=overall_risk,
            negotiation_points=negotiation_points,
            missing_clauses=missing
        )
    
    def generate_amendments(self, analysis: ContractAnalysis) -> List[Amendment]:
        """Сгенерировать предложения по поправкам для высокорисковых статей."""
        amendments = []
        
        high_risk_clauses = [
            c for c in analysis.clauses 
            if c.risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH]
        ]
        
        for clause in high_risk_clauses:
            amendment = self.drafter.run(f"""
            Составьте исправленную версию этой статьи {clause.type.value}:
            
            ОРИГИНАЛ:
            "{clause.text}"
            
            ПРОБЛЕМЫ:
            {clause.concerns}
            
            Создайте сбалансированную редакцию, которая:
            1. Устраняет выявленные проблемы
            2. Остаётся коммерчески разумной
            3. Использует стандартный юридический язык
            
            Предоставьте предлагаемый текст и обоснование.
            """)
            
            amendments.append(Amendment(
                clause_type=clause.type,
                original_text=clause.text,
                proposed_text=self._extract_proposed_text(amendment),
                rationale=self._extract_rationale(amendment),
                risk_reduction=f"Снижает риск с {clause.risk_level.value} до более низкого уровня"
            ))
        
        return amendments

# Использование
if __name__ == "__main__":
    analyzer = LegalDocumentAnalyzer()
    
    # Анализ контракта
    analysis = analyzer.analyze_contract("vendor_agreement.pdf")
    
    print(f"Контракт: {analysis.title}")
    print(f"Общий риск: {analysis.overall_risk}")
    print(f"\nСтороны:")
    for party in analysis.parties:
        print(f"  - {party.name} ({party.role})")
    
    print(f"\nВысокорисковые статьи:")
    for clause in analysis.clauses:
        if clause.risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH]:
            print(f"  [{clause.risk_level}] {clause.type.value}")
            print(f"    Проблемы: {clause.concerns}")
    
    # Генерация поправок
    amendments = analyzer.generate_amendments(analysis)
    print(f"\nПредложено поправок: {len(amendments)}")
```

---

## 5. Торговый ассистент реального времени

Финансовый ИИ для анализа рынка, обработки новостей и генерации сигналов.

```python
from rlm_toolkit import RLM
from rlm_toolkit.agents import ReActAgent
from rlm_toolkit.tools import Tool, WebSearchTool
from rlm_toolkit.memory import HierarchicalMemory
from rlm_toolkit.callbacks import TokenCounterCallback
from pydantic import BaseModel
from typing import List, Optional, Dict
from enum import Enum
from datetime import datetime, timedelta
import asyncio
import json

class Signal(str, Enum):
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    HOLD = "hold"
    SELL = "sell"
    STRONG_SELL = "strong_sell"

class TimeFrame(str, Enum):
    INTRADAY = "intraday"
    SWING = "swing"
    POSITION = "position"

class MarketSentiment(BaseModel):
    overall: str  # bullish, bearish, neutral
    confidence: float  # 0-1
    key_factors: List[str]
    news_impact: str

class TechnicalAnalysis(BaseModel):
    trend: str  # uptrend, downtrend, sideways
    support_levels: List[float]
    resistance_levels: List[float]
    indicators: Dict[str, str]  # RSI, MACD и т.д.

class FundamentalAnalysis(BaseModel):
    valuation: str  # undervalued, fair, overvalued
    financial_health: str
    growth_prospects: str
    key_metrics: Dict[str, float]

class TradeIdea(BaseModel):
    symbol: str
    signal: Signal
    timeframe: TimeFrame
    entry_price: float
    stop_loss: float
    take_profit: List[float]
    risk_reward: float
    confidence: float
    rationale: str
    catalysts: List[str]
    risks: List[str]

# Инструменты для рыночных данных (симуляция — используйте реальные API в продакшене)
@Tool(name="get_price", description="Получить текущую цену для символа")
def get_price(symbol: str) -> str:
    import random
    price = random.uniform(100, 500)
    return json.dumps({"symbol": symbol, "price": round(price, 2), "change": round(random.uniform(-5, 5), 2)})

@Tool(name="get_technicals", description="Получить технические индикаторы")
def get_technicals(symbol: str) -> str:
    import random
    return json.dumps({
        "rsi": random.randint(20, 80),
        "macd": {"value": random.uniform(-5, 5), "signal": random.uniform(-5, 5)},
        "sma_20": random.uniform(100, 500),
        "sma_50": random.uniform(100, 500),
        "bollinger": {"upper": 520, "middle": 500, "lower": 480}
    })

@Tool(name="get_fundamentals", description="Получить фундаментальные данные")
def get_fundamentals(symbol: str) -> str:
    import random
    return json.dumps({
        "pe_ratio": random.uniform(10, 50),
        "peg_ratio": random.uniform(0.5, 3),
        "debt_equity": random.uniform(0.1, 2),
        "roe": random.uniform(5, 30),
        "revenue_growth": random.uniform(-10, 50),
        "eps_growth": random.uniform(-20, 100)
    })

@Tool(name="get_news", description="Получить последние новости по символу")
def get_news(symbol: str, days: int = 7) -> str:
    return json.dumps([
        {"title": f"{symbol} анонсирует запуск нового продукта", "sentiment": "positive", "date": "2024-01-15"},
        {"title": f"Аналитик повышает рейтинг {symbol} до 'покупать'", "sentiment": "positive", "date": "2024-01-14"},
        {"title": f"Сектор сталкивается с проблемами", "sentiment": "negative", "date": "2024-01-13"}
    ])

class TradingAssistant:
    """
    Торговый ассистент реального времени:
    1. Анализирует рыночные условия
    2. Обрабатывает новости и сентимент
    3. Проводит технический анализ
    4. Оценивает фундаментальные показатели
    5. Генерирует торговые сигналы с управлением рисками
    """
    
    def __init__(self):
        self.memory = HierarchicalMemory(persist_directory="./trading_memory")
        
        # Рыночный аналитик
        self.market_analyst = ReActAgent.from_openai(
            "gpt-4o",
            tools=[get_price, get_technicals, get_news],
            system_prompt="""
            Вы — профессиональный рыночный аналитик. Анализируйте:
            - Ценовое движение и объёмы
            - Технические индикаторы (RSI, MACD, скользящие средние)
            - Графические паттерны
            - Рыночный сентимент из новостей
            
            Будьте объективны и основывайтесь на данных. Избегайте эмоциональных искажений.
            """,
            max_iterations=10
        )
        
        # Фундаментальный аналитик
        self.fundamental_analyst = ReActAgent.from_openai(
            "gpt-4o",
            tools=[get_fundamentals],
            system_prompt="""
            Вы — фундаментальный аналитик. Оценивайте:
            - Мультипликаторы оценки (P/E, PEG, P/B)
            - Финансовое здоровье (долг, денежный поток)
            - Траектория роста
            - Конкурентная позиция
            
            Фокусируйтесь на внутренней стоимости и долгосрочных перспективах.
            """,
            max_iterations=10
        )
        
        # Анализатор новостного сентимента
        self.sentiment_analyzer = RLM.from_anthropic("claude-3-sonnet")
        self.sentiment_analyzer.set_system_prompt("""
        Вы — аналитик финансовых новостей. Оценивайте новости на:
        - Влияние на рынок (high, medium, low)
        - Сентимент (bullish, bearish, neutral)
        - Временной горизонт влияния
        - Надёжность источника
        
        Будьте скептичны к хайпу и фокусируйтесь на материальной информации.
        """)
        
        # Торговый стратег
        self.strategist = RLM.from_openai("gpt-4o")
        self.strategist.set_system_prompt("""
        Вы — профессиональный трейдер и риск-менеджер. Создавайте торговые идеи с:
        - Чёткими критериями входа и выхода
        - Определённым стоп-лоссом и тейк-профитом
        - Анализом риск/доходность
        - Рекомендациями по размеру позиции
        
        Всегда приоритизируйте сохранение капитала. Никогда не предлагайте позиции «all-in».
        """)
        
    async def analyze_symbol(self, symbol: str) -> TradeIdea:
        """Полный анализ символа."""
        
        print(f"📊 Анализируем {symbol}...")
        
        # Запуск анализов параллельно
        technical_task = asyncio.create_task(self._get_technical_analysis(symbol))
        fundamental_task = asyncio.create_task(self._get_fundamental_analysis(symbol))
        sentiment_task = asyncio.create_task(self._get_sentiment(symbol))
        
        technical = await technical_task
        fundamental = await fundamental_task
        sentiment = await sentiment_task
        
        # Генерация торговой идеи
        trade_idea = self._generate_trade_idea(symbol, technical, fundamental, sentiment)
        
        # Сохранение в память
        self.memory.add_episode(
            f"Анализ {symbol}: {trade_idea.signal.value}",
            metadata={"symbol": symbol, "signal": trade_idea.signal.value}
        )
        
        return trade_idea
    
    def screen_market(self, symbols: List[str]) -> List[TradeIdea]:
        """Скрининг нескольких символов и возврат лучших идей."""
        ideas = []
        
        for symbol in symbols:
            try:
                idea = asyncio.run(self.analyze_symbol(symbol))
                if idea.signal in [Signal.STRONG_BUY, Signal.STRONG_SELL]:
                    ideas.append(idea)
            except Exception as e:
                print(f"Ошибка анализа {symbol}: {e}")
        
        # Сортировка по уверенности
        ideas.sort(key=lambda x: x.confidence, reverse=True)
        
        return ideas[:10]  # Топ-10 идей

# Использование
if __name__ == "__main__":
    assistant = TradingAssistant()
    
    # Анализ одного символа
    idea = asyncio.run(assistant.analyze_symbol("AAPL"))
    print(f"\n{idea.symbol}: {idea.signal.value}")
    print(f"Вход: ${idea.entry_price} | Стоп: ${idea.stop_loss}")
    print(f"Цели: {idea.take_profit}")
    print(f"R/R: {idea.risk_reward} | Уверенность: {idea.confidence}")
    print(f"Обоснование: {idea.rationale}")
    
    # Скрининг рынка
    watchlist = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META"]
    top_ideas = assistant.screen_market(watchlist)
    
    print("\n=== Топ торговых идей ===")
    for idea in top_ideas:
        print(f"{idea.symbol}: {idea.signal.value} (уверенность: {idea.confidence})")
```

---

*Продолжение в Части 2...*
