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
            f"Преобразуйте отчёт в структурированный формат:\n{report_content}",
            output_schema=ResearchReport
        )
        
        report.generated_at = datetime.now().isoformat()
        
        print("✅ Исследование завершено!")
        return report

# Использование
if __name__ == "__main__":
    agent = AutonomousResearchAgent()
    
    report = agent.research(
        topic="Влияние больших языковых моделей на практики разработки ПО в 2024",
        depth="comprehensive"
    )
    
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
from pydantic import BaseModel
from typing import List, Union, Optional
import base64

class MultiModalRAG:
    """
    Унифицированный RAG-пайплайн для различных типов контента:
    - PDF с текстом и изображениями
    - Отдельные изображения (диаграммы, графики)
    - Аудиофайлы (транскрибированные)
    - Видеофайлы (транскрипция + ключевые кадры)
    """
    
    def __init__(self, collection_name: str = "multimodal"):
        self.text_embeddings = OpenAIEmbeddings("text-embedding-3-large")
        self.vision_llm = RLM.from_openai("gpt-4o")
        
        self.text_store = ChromaVectorStore(
            collection_name=f"{collection_name}_text",
            embedding_function=self.text_embeddings
        )
        self.image_store = ChromaVectorStore(
            collection_name=f"{collection_name}_images",
            embedding_function=self.text_embeddings
        )
        
        self.qa_llm = RLM.from_openai("gpt-4o")
        self.qa_llm.set_system_prompt("""
        Вы — мультимодальный ИИ-ассистент. Вы понимаете:
        - Текст из документов
        - Изображения и диаграммы
        - Транскрибированное аудио/видео
        
        Давайте комплексные ответы, используя весь доступный контекст.
        """)
        
    def ingest_pdf(self, path: str) -> int:
        """Загрузить PDF с текстом и изображениями."""
        loader = PDFLoader(path, extract_images=True)
        docs = loader.load()
        
        # Обработка текста и изображений...
        return len(docs)
    
    def query(self, question: str, include_images: bool = True) -> dict:
        """Запрос по всем модальностям."""
        text_results = self.text_store.similarity_search(question, k=5)
        image_results = self.image_store.similarity_search(question, k=3) if include_images else []
        
        context = "## Текстовый контекст:\n"
        for doc in text_results:
            context += f"- {doc.page_content}\n"
        
        if image_results:
            context += "\n## Контекст изображений:\n"
            for doc in image_results:
                context += f"- [Изображение] {doc.page_content}\n"
        
        answer = self.qa_llm.run(f"Вопрос: {question}\n\nКонтекст:\n{context}")
        
        return {"answer": answer, "sources": len(text_results) + len(image_results)}
```

---

## 3. Агент Code Review

Агент, анализирующий pull requests, находящий баги и генерирующий тесты.

```python
from rlm_toolkit import RLM
from rlm_toolkit.agents import ReActAgent
from rlm_toolkit.tools import Tool
from pydantic import BaseModel
from typing import List
from enum import Enum

class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class CodeIssue(BaseModel):
    file: str
    line: int
    severity: Severity
    category: str
    description: str
    suggestion: str

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
        self.reviewer = ReActAgent.from_openai(
            "gpt-4o",
            tools=[read_file, get_diff, run_linter, check_types],
            system_prompt="""
            Вы — эксперт код-ревью с глубокими знаниями:
            - Паттерны проектирования и лучшие практики
            - Уязвимости безопасности (OWASP Top 10)
            - Оптимизация производительности
            - Принципы чистого кода
            """,
            max_iterations=30
        )
        
        self.security_agent = RLM.from_anthropic("claude-3-sonnet")
        self.test_generator = RLM.from_openai("gpt-4o")
        
    def review_pr(self, files: List[str]) -> dict:
        """Провести ревью pull request."""
        # Многофазный анализ...
        return {"issues": [], "tests": [], "recommendation": "approve"}
```

---

## 4. Анализатор юридических документов

Enterprise-ИИ для анализа контрактов и выявления рисков.

```python
from rlm_toolkit import RLM
from rlm_toolkit.loaders import PDFLoader
from pydantic import BaseModel
from typing import List, Optional
from enum import Enum

class RiskLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class Clause(BaseModel):
    type: str
    text: str
    risk_level: RiskLevel
    concerns: List[str]

class LegalDocumentAnalyzer:
    """
    Enterprise-анализатор юридических документов:
    1. Извлекает и категоризирует статьи
    2. Выявляет риски и нестандартные условия
    3. Сравнивает с лучшими практиками
    4. Генерирует предложения по изменениям
    """
    
    def __init__(self):
        self.analyst = RLM.from_anthropic("claude-3-opus")
        self.analyst.set_system_prompt("""
        Вы — опытный корпоративный юрист с 20+ годами опыта в:
        - M&A сделках
        - Коммерческих контрактах
        - Лицензировании технологий
        
        Анализируйте контракты с предельной точностью.
        """)
        
    def analyze_contract(self, pdf_path: str) -> dict:
        """Полный анализ контракта."""
        docs = PDFLoader(pdf_path).load()
        # Многоэтапный анализ...
        return {"clauses": [], "overall_risk": RiskLevel.MEDIUM}
```

---

## 5. Торговый ассистент реального времени

Финансовый ИИ для анализа рынка и генерации сигналов.

```python
from rlm_toolkit import RLM
from rlm_toolkit.agents import ReActAgent
from rlm_toolkit.memory import HierarchicalMemory
from pydantic import BaseModel
from typing import List
from enum import Enum

class Signal(str, Enum):
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    HOLD = "hold"
    SELL = "sell"

class TradeIdea(BaseModel):
    symbol: str
    signal: Signal
    entry_price: float
    stop_loss: float
    take_profit: List[float]
    confidence: float
    rationale: str

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
        
        self.market_analyst = ReActAgent.from_openai(
            "gpt-4o",
            tools=[get_price, get_technicals, get_news],
            system_prompt="""
            Вы — профессиональный рыночный аналитик. Анализируйте:
            - Ценовое движение и объёмы
            - Технические индикаторы (RSI, MACD, скользящие средние)
            - Рыночный сентимент из новостей
            
            Будьте объективны и основывайтесь на данных.
            """
        )
        
    async def analyze_symbol(self, symbol: str) -> TradeIdea:
        """Полный анализ символа."""
        # Параллельные анализы...
        return TradeIdea(
            symbol=symbol,
            signal=Signal.BUY,
            entry_price=455.0,
            stop_loss=440.0,
            take_profit=[470.0, 485.0, 500.0],
            confidence=0.72,
            rationale="Бычьи технические индикаторы с позитивным катализатором"
        )
```

---

*Продолжение в Части 2...*
