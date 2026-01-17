# Продвинутые примеры - Часть 2

R&D и передовые примеры, демонстрирующие уникальные возможности RLM-Toolkit.

---

## 6. Самосовершенствующийся генератор кода

R-Zero паттерн, итеративно улучшающий собственный код через самокритику.

```python
from rlm_toolkit import RLM
from rlm_toolkit.evolve import SelfEvolvingRLM
from rlm_toolkit.tools import PythonREPL
from pydantic import BaseModel
from typing import List

class CodeQuality(BaseModel):
    correctness: float
    efficiency: float
    readability: float
    test_coverage: float
    overall: float

class SelfImprovingCodeGenerator:
    """
    Самосовершенствующийся генератор кода по паттерну R-Zero Challenger-Solver:
    1. Генерирует начальный код
    2. Challenger критикует и находит проблемы
    3. Solver улучшает на основе критики
    4. Повторяет до достижения порога качества
    """
    
    def __init__(self, max_iterations: int = 5, quality_threshold: float = 0.9):
        self.max_iterations = max_iterations
        self.quality_threshold = quality_threshold
        
        self.generator = RLM.from_openai("gpt-4o")
        self.challenger = RLM.from_anthropic("claude-3-opus")
        self.solver = RLM.from_openai("gpt-4o")
        
    def generate(self, task: str) -> dict:
        """Генерация кода с итеративным улучшением."""
        # Challenger-Solver цикл...
        return {"code": "...", "quality": 0.92, "iterations": 3}
```

---

## 7. Построитель графа знаний

Автоматическое построение графов знаний из документов.

```python
from rlm_toolkit import RLM
from rlm_toolkit.embeddings import OpenAIEmbeddings
from neo4j import GraphDatabase
from pydantic import BaseModel
from typing import List, Dict

class Entity(BaseModel):
    name: str
    type: str
    description: str

class Relationship(BaseModel):
    source: str
    target: str
    type: str
    confidence: float

class KnowledgeGraphBuilder:
    """
    Построитель графов знаний из документов:
    1. Извлекает сущности (люди, организации, концепции)
    2. Определяет связи между сущностями
    3. Разрешает корреференции
    4. Сохраняет в Neo4j
    5. Позволяет делать графовые запросы
    """
    
    def __init__(self, neo4j_uri: str):
        self.entity_extractor = RLM.from_openai("gpt-4o")
        self.relationship_extractor = RLM.from_anthropic("claude-3-sonnet")
        self.driver = GraphDatabase.driver(neo4j_uri)
        
    def build_from_documents(self, paths: List[str]) -> dict:
        """Построить граф знаний из документов."""
        # Извлечение сущностей и связей...
        return {"entities": 150, "relationships": 320}
    
    def query(self, question: str) -> str:
        """Запрос к графу знаний на естественном языке."""
        # Генерация Cypher и выполнение...
        return "Ответ на основе графа"
```

---

## 8. Семантический поиск по коду

Поиск по кодовой базе по смыслу, а не просто текстовый поиск.

```python
from rlm_toolkit import RLM
from rlm_toolkit.embeddings import OpenAIEmbeddings
from rlm_toolkit.vectorstores import ChromaVectorStore
from pydantic import BaseModel
from typing import List
import ast

class CodeElement(BaseModel):
    type: str  # function, class, method
    name: str
    signature: str
    semantic_description: str
    file_path: str
    line_number: int

class SemanticCodeSearch:
    """
    Семантический поиск по кодовой базе:
    1. Парсит код в элементы (функции, классы)
    2. Генерирует семантические описания через LLM
    3. Создаёт эмбеддинги для поиска
    4. Возвращает результаты с объяснениями
    """
    
    def __init__(self, project_path: str):
        self.embeddings = OpenAIEmbeddings("text-embedding-3-large")
        self.vectorstore = ChromaVectorStore(
            collection_name="code_search",
            embedding_function=self.embeddings
        )
        self.describer = RLM.from_openai("gpt-4o")
        
    def index_codebase(self):
        """Индексировать всю кодовую базу."""
        # Парсинг и индексация...
        pass
    
    def search(self, query: str, k: int = 10) -> List[dict]:
        """Семантический поиск по коду."""
        # Поиск с объяснениями...
        return []
```

---

## 9. Система мультиагентных дебатов

Агенты дебатируют и приходят к консенсусу через структурированную аргументацию.

```python
from rlm_toolkit import RLM
from rlm_toolkit.agents.multiagent import Agent
from pydantic import BaseModel
from typing import List, Optional
from enum import Enum

class Position(str, Enum):
    STRONGLY_AGREE = "strongly_agree"
    AGREE = "agree"
    NEUTRAL = "neutral"
    DISAGREE = "disagree"

class Argument(BaseModel):
    agent: str
    position: Position
    claim: str
    evidence: List[str]
    confidence: float

class MultiAgentDebate:
    """
    Система мультиагентных дебатов:
    1. Несколько агентов аргументируют позиции
    2. Агенты могут менять позиции на основе аргументов
    3. Модератор направляет дискуссию
    4. Система синтезирует консенсус или выделяет разногласия
    """
    
    def __init__(self, num_agents: int = 4):
        perspectives = [
            ("Прагматик", "Фокус на практических последствиях"),
            ("Теоретик", "Фокус на принципах и логике"),
            ("Адвокат дьявола", "Оспаривает предположения"),
            ("Синтезатор", "Ищет общую почву")
        ]
        
        self.agents = {}
        for name, style in perspectives[:num_agents]:
            self.agents[name.lower()] = Agent(
                name=name.lower(),
                description=style,
                llm=RLM.from_openai("gpt-4o")
            )
        
        self.moderator = RLM.from_anthropic("claude-3-opus")
        
    def debate(self, topic: str, max_rounds: int = 5) -> dict:
        """Провести структурированные дебаты по теме."""
        # Многораундовые дебаты...
        return {"consensus": Position.AGREE, "synthesis": "..."}
```

---

## 10. Рекурсивный суммаризатор документов (InfiniRetri)

Обработка документов на 1000+ страниц с рекурсивной суммаризацией.

```python
from rlm_toolkit import RLM, RLMConfig
from rlm_toolkit.retrieval import InfiniRetriConfig
from rlm_toolkit.loaders import PDFLoader
from rlm_toolkit.splitters import RecursiveTextSplitter
from pydantic import BaseModel
from typing import List

class SectionSummary(BaseModel):
    title: str
    page_range: str
    summary: str
    key_points: List[str]

class DocumentSummary(BaseModel):
    title: str
    total_pages: int
    executive_summary: str
    section_summaries: List[SectionSummary]
    key_themes: List[str]

class RecursiveDocumentSummarizer:
    """
    Суммаризация массивных документов (1000+ страниц):
    1. Иерархическое разбиение
    2. Рекурсивная map-reduce суммаризация
    3. InfiniRetri для контекстно-зависимых запросов
    4. Многоуровневая абстракция
    """
    
    def __init__(self):
        self.config = RLMConfig(
            enable_infiniretri=True,
            infiniretri_config=InfiniRetriConfig(
                chunk_size=8000,
                top_k=10
            )
        )
        
        self.rlm = RLM.from_openai("gpt-4o", config=self.config)
        self.section_summarizer = RLM.from_openai("gpt-4o")
        self.meta_summarizer = RLM.from_anthropic("claude-3-opus")
        
    def summarize(self, pdf_path: str, target_length: str = "comprehensive") -> DocumentSummary:
        """Суммаризировать большой документ."""
        docs = PDFLoader(pdf_path).load()
        total_pages = len(docs)
        
        # Многоуровневая суммаризация...
        return DocumentSummary(
            title="Название документа",
            total_pages=total_pages,
            executive_summary="...",
            section_summaries=[],
            key_themes=[]
        )
    
    def query(self, question: str) -> str:
        """Запрос к суммаризированному документу."""
        return self.rlm.run(f"Ответьте на основе документа: {question}")
```

---

*Продолжение в Части 3: Безопасность...*
