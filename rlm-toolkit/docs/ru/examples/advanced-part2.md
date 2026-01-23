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
from typing import List, Optional, Tuple
import json

class CodeQuality(BaseModel):
    correctness: float
    efficiency: float
    readability: float
    test_coverage: float
    overall: float
    issues: List[str] = []

class CodeIteration(BaseModel):
    version: int
    code: str
    quality: CodeQuality
    improvements: List[str]

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
        
        # Начальный генератор
        self.generator = RLM.from_openai("gpt-4o")
        self.generator.set_system_prompt("""
        Вы эксперт Python разработчик. Генерируйте чистый, эффективный код.
        Включайте type hints, docstrings и обработку ошибок.
        """)
        
        # Challenger - критикует код
        self.challenger = RLM.from_anthropic("claude-3-opus")
        self.challenger.set_system_prompt("""
        Вы жёсткий code reviewer. Найдите ВСЕ проблемы:
        - Баги и крайние случаи
        - Проблемы производительности
        - Вопросы безопасности
        - Нарушения стиля
        - Отсутствующие тесты
        
        Будьте беспощадны но конструктивны.
        """)
        
        # Solver - улучшает на основе критики
        self.solver = RLM.from_openai("gpt-4o")
        self.solver.set_system_prompt("""
        Вы улучшаете код на основе обратной связи от reviewer.
        Исправьте все поднятые проблемы, сохраняя работающий функционал.
        """)
        
        # Тестер - выполняет код
        self.repl = PythonREPL()
        
    def generate(self, task: str) -> dict:
        """Генерация кода с итеративным улучшением."""
        
        print(f"🎯 Задача: {task}\n")
        
        iterations: List[CodeIteration] = []
        
        # Генерация начальной версии
        print("📝 Генерация начальной версии...")
        
        initial_code = self.generator.run(f"""
        Реализуйте следующее:
        
        {task}
        
        Требования:
        - Чистый Python 3.10+
        - Type hints обязательны
        - Docstrings для всех публичных функций
        - Обработка ошибок
        - Включите тесты
        
        Верните только код Python.
        """)
        
        current_code = self._extract_code(initial_code)
        
        for iteration in range(1, self.max_iterations + 1):
            print(f"\n🔄 Итерация {iteration}/{self.max_iterations}")
            
            # Тестирование кода
            print("  🧪 Тестирование...")
            test_result = self._test_code(current_code)
            
            # Challenger критикует
            print("  🔍 Challenger анализирует...")
            
            critique = self.challenger.run(f"""
            Проанализируйте этот код:
            
            ```python
            {current_code}
            ```
            
            Результат тестов:
            {test_result}
            
            Предоставьте:
            1. Оценки (0-1): correctness, efficiency, readability, test_coverage
            2. Список проблем
            3. Конкретные улучшения
            
            Формат JSON:
            {{
                "scores": {{"correctness": 0.8, "efficiency": 0.7, "readability": 0.9, "test_coverage": 0.6}},
                "issues": ["проблема 1", "проблема 2"],
                "improvements": ["улучшение 1", "улучшение 2"]
            }}
            """)
            
            # Парсинг оценки
            quality = self._parse_quality(critique)
            
            print(f"  📊 Качество: {quality.overall:.2f}")
            
            iterations.append(CodeIteration(
                version=iteration,
                code=current_code,
                quality=quality,
                improvements=[]
            ))
            
            # Проверка достижения порога
            if quality.overall >= self.quality_threshold:
                print(f"  ✅ Достигнут порог качества!")
                break
            
            # Solver улучшает
            print("  🛠️ Solver улучшает...")
            
            improved = self.solver.run(f"""
            Улучшите этот код на основе обратной связи:
            
            Код:
            ```python
            {current_code}
            ```
            
            Проблемы:
            {json.dumps(quality.issues, ensure_ascii=False)}
            
            Исправьте ВСЕ поднятые проблемы.
            Верните только улучшенный код.
            """)
            
            current_code = self._extract_code(improved)
        
        # Финальный анализ
        final_quality = iterations[-1].quality
        
        return {
            "code": current_code,
            "quality": final_quality.overall,
            "iterations": len(iterations),
            "history": [
                {
                    "version": i.version,
                    "quality": i.quality.overall,
                    "issues_count": len(i.quality.issues)
                }
                for i in iterations
            ]
        }
    
    def _extract_code(self, response: str) -> str:
        """Извлечь код из ответа."""
        if "```python" in response:
            start = response.find("```python") + 9
            end = response.find("```", start)
            return response[start:end].strip()
        return response.strip()
    
    def _test_code(self, code: str) -> str:
        """Выполнить код и вернуть результат."""
        try:
            result = self.repl.run(code)
            return f"Успех: {result[:500]}" if result else "Успех: код выполнен"
        except Exception as e:
            return f"Ошибка: {str(e)}"
    
    def _parse_quality(self, critique: str) -> CodeQuality:
        """Парсинг оценки качества из ответа."""
        try:
            # Извлечь JSON
            start = critique.find("{")
            end = critique.rfind("}") + 1
            data = json.loads(critique[start:end])
            
            scores = data.get("scores", {})
            issues = data.get("issues", [])
            
            return CodeQuality(
                correctness=scores.get("correctness", 0.5),
                efficiency=scores.get("efficiency", 0.5),
                readability=scores.get("readability", 0.5),
                test_coverage=scores.get("test_coverage", 0.5),
                overall=sum(scores.values()) / len(scores) if scores else 0.5,
                issues=issues
            )
        except:
            return CodeQuality(
                correctness=0.5,
                efficiency=0.5,
                readability=0.5,
                test_coverage=0.5,
                overall=0.5,
                issues=["Не удалось распарсить оценку"]
            )

# Использование
if __name__ == "__main__":
    generator = SelfImprovingCodeGenerator(
        max_iterations=5,
        quality_threshold=0.85
    )
    
    result = generator.generate("""
    Создайте класс LRU Cache с:
    - get(key) - O(1)
    - put(key, value) - O(1)
    - Поддержка TTL (опционально)
    - Потокобезопасность
    - Статистика (hits/misses)
    """)
    
    print(f"\n=== Результат ===")
    print(f"Итераций: {result['iterations']}")
    print(f"Финальное качество: {result['quality']:.2f}")
    print(f"\n--- Код ---\n{result['code'][:1000]}...")
```

---

## 7. Построитель графа знаний

Автоматическое построение графов знаний из документов.

```python
from rlm_toolkit import RLM
from rlm_toolkit.embeddings import OpenAIEmbeddings
from rlm_toolkit.loaders import DirectoryLoader
from neo4j import GraphDatabase
from pydantic import BaseModel
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import json
import hashlib

class Entity(BaseModel):
    id: str
    name: str
    type: str  # PERSON, ORG, CONCEPT, TECH, EVENT
    description: str
    attributes: Dict[str, str] = {}
    source_chunks: List[str] = []

class Relationship(BaseModel):
    source_id: str
    target_id: str
    type: str  # WORKS_FOR, USES, RELATES_TO, PART_OF, etc.
    description: str
    confidence: float
    evidence: str

@dataclass
class GraphStats:
    total_entities: int
    total_relationships: int
    entity_types: Dict[str, int]
    relationship_types: Dict[str, int]

class KnowledgeGraphBuilder:
    """
    Построитель графов знаний из документов:
    1. Извлекает сущности (люди, организации, концепции)
    2. Определяет связи между сущностями
    3. Разрешает корреференции
    4. Сохраняет в Neo4j
    5. Позволяет делать графовые запросы
    """
    
    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        # Экстрактор сущностей
        self.entity_extractor = RLM.from_openai("gpt-4o")
        self.entity_extractor.set_system_prompt("""
        Вы эксперт по извлечению сущностей. Извлеките из текста:
        - PERSON: люди, авторы, эксперты
        - ORG: компании, организации, команды
        - CONCEPT: идеи, методологии, теории
        - TECH: технологии, инструменты, языки
        - EVENT: события, релизы, конференции
        
        Будьте точны и избегайте дублирования.
        """)
        
        # Экстрактор связей
        self.relationship_extractor = RLM.from_anthropic("claude-3-sonnet")
        self.relationship_extractor.set_system_prompt("""
        Вы анализируете связи между сущностями.
        Определите тип связи и её силу (confidence 0-1).
        
        Типы связей:
        - WORKS_FOR: трудовые отношения
        - CREATED: авторство, создание
        - USES: использование технологии
        - PART_OF: часть чего-то
        - RELATES_TO: общая связь
        - COMPETES_WITH: конкуренция
        - DEPENDS_ON: зависимость
        """)
        
        # Резолвер корреференций
        self.coreference_resolver = RLM.from_openai("gpt-4o-mini")
        
        # Генератор Cypher запросов
        self.query_generator = RLM.from_openai("gpt-4o")
        
        # Neo4j подключение
        self.driver = GraphDatabase.driver(
            neo4j_uri,
            auth=(neo4j_user, neo4j_password)
        )
        
        # Кэш сущностей для дедупликации
        self.entity_cache: Dict[str, Entity] = {}
        
        # Эмбеддинги для семантического сравнения
        self.embeddings = OpenAIEmbeddings("text-embedding-3-large")
    
    def build_from_documents(self, directory: str, file_pattern: str = "**/*.md") -> GraphStats:
        """Построить граф знаний из директории документов."""
        
        print(f"📂 Загрузка документов из: {directory}")
        
        # Загрузка документов
        loader = DirectoryLoader(directory, glob=file_pattern)
        docs = loader.load()
        
        print(f"   Найдено документов: {len(docs)}")
        
        all_entities = []
        all_relationships = []
        
        for i, doc in enumerate(docs):
            print(f"\n📄 Обработка [{i+1}/{len(docs)}]: {doc.metadata.get('source', 'unknown')}")
            
            # Разбивка на чанки
            chunks = self._chunk_document(doc.page_content)
            
            for chunk_id, chunk in enumerate(chunks):
                # Извлечение сущностей
                entities = self._extract_entities(chunk, doc.metadata)
                all_entities.extend(entities)
                
                # Извлечение связей
                if entities:
                    relationships = self._extract_relationships(chunk, entities)
                    all_relationships.extend(relationships)
        
        print(f"\n🔗 Разрешение корреференций...")
        resolved_entities = self._resolve_coreferences(all_entities)
        
        print(f"📊 Сохранение в Neo4j...")
        self._save_to_neo4j(resolved_entities, all_relationships)
        
        # Статистика
        stats = self._compute_stats(resolved_entities, all_relationships)
        
        print(f"\n=== Граф знаний построен ===")
        print(f"   Сущностей: {stats.total_entities}")
        print(f"   Связей: {stats.total_relationships}")
        
        return stats
    
    def _chunk_document(self, text: str, chunk_size: int = 2000) -> List[str]:
        """Разбить документ на чанки."""
        chunks = []
        sentences = text.split(". ")
        
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            if current_length + len(sentence) > chunk_size and current_chunk:
                chunks.append(". ".join(current_chunk) + ".")
                current_chunk = []
                current_length = 0
            
            current_chunk.append(sentence)
            current_length += len(sentence)
        
        if current_chunk:
            chunks.append(". ".join(current_chunk))
        
        return chunks
    
    def _extract_entities(self, text: str, metadata: dict) -> List[Entity]:
        """Извлечь сущности из текста."""
        
        response = self.entity_extractor.run(f"""
        Извлеките сущности из текста:
        
        {text[:3000]}
        
        Формат JSON:
        [
            {{"name": "OpenAI", "type": "ORG", "description": "Компания по разработке ИИ"}},
            {{"name": "GPT-4", "type": "TECH", "description": "Большая языковая модель"}}
        ]
        """)
        
        entities = []
        try:
            data = json.loads(self._extract_json(response))
            
            for item in data:
                entity_id = self._generate_id(item["name"], item["type"])
                
                entity = Entity(
                    id=entity_id,
                    name=item["name"],
                    type=item["type"],
                    description=item.get("description", ""),
                    source_chunks=[text[:200]]
                )
                entities.append(entity)
                
        except Exception as e:
            print(f"   ⚠️ Ошибка парсинга сущностей: {e}")
        
        return entities
    
    def _extract_relationships(self, text: str, entities: List[Entity]) -> List[Relationship]:
        """Извлечь связи между сущностями."""
        
        entity_names = [e.name for e in entities]
        
        response = self.relationship_extractor.run(f"""
        Определите связи между этими сущностями в контексте текста:
        
        Сущности: {entity_names}
        
        Текст: {text[:2000]}
        
        Формат JSON:
        [
            {{
                "source": "OpenAI",
                "target": "GPT-4",
                "type": "CREATED",
                "description": "OpenAI создала GPT-4",
                "confidence": 0.95
            }}
        ]
        """)
        
        relationships = []
        try:
            data = json.loads(self._extract_json(response))
            
            # Создаём маппинг имён на ID
            name_to_id = {e.name: e.id for e in entities}
            
            for item in data:
                source_id = name_to_id.get(item["source"])
                target_id = name_to_id.get(item["target"])
                
                if source_id and target_id:
                    rel = Relationship(
                        source_id=source_id,
                        target_id=target_id,
                        type=item["type"],
                        description=item.get("description", ""),
                        confidence=item.get("confidence", 0.5),
                        evidence=text[:200]
                    )
                    relationships.append(rel)
                    
        except Exception as e:
            print(f"   ⚠️ Ошибка парсинга связей: {e}")
        
        return relationships
    
    def _resolve_coreferences(self, entities: List[Entity]) -> List[Entity]:
        """Объединить дублирующиеся сущности."""
        
        if not entities:
            return []
        
        # Группировка по типу
        by_type: Dict[str, List[Entity]] = {}
        for entity in entities:
            by_type.setdefault(entity.type, []).append(entity)
        
        resolved = []
        
        for entity_type, type_entities in by_type.items():
            if len(type_entities) <= 1:
                resolved.extend(type_entities)
                continue
            
            # Получаем эмбеддинги имён
            names = [e.name for e in type_entities]
            
            # Используем LLM для группировки похожих
            response = self.coreference_resolver.run(f"""
            Сгруппируйте эти сущности типа {entity_type}, которые относятся к одному объекту:
            
            {names}
            
            Формат JSON - список групп:
            [["GPT-4", "GPT4", "gpt-4o"], ["Claude", "Claude 3"]]
            
            Если сущности разные, поместите каждую в отдельную группу.
            """)
            
            try:
                groups = json.loads(self._extract_json(response))
                
                for group in groups:
                    # Объединяем сущности в группе
                    group_entities = [e for e in type_entities if e.name in group]
                    
                    if group_entities:
                        # Берём сущность с самым длинным описанием
                        merged = max(group_entities, key=lambda e: len(e.description))
                        
                        # Объединяем исходные чанки
                        for e in group_entities:
                            merged.source_chunks.extend(e.source_chunks)
                        
                        resolved.append(merged)
                        
            except:
                resolved.extend(type_entities)
        
        return resolved
    
    def _save_to_neo4j(self, entities: List[Entity], relationships: List[Relationship]):
        """Сохранить граф в Neo4j."""
        
        with self.driver.session() as session:
            # Очистка
            session.run("MATCH (n) DETACH DELETE n")
            
            # Создание сущностей
            for entity in entities:
                session.run("""
                    CREATE (e:Entity {
                        id: $id,
                        name: $name,
                        type: $type,
                        description: $description
                    })
                """, id=entity.id, name=entity.name, 
                    type=entity.type, description=entity.description)
            
            # Создание связей
            for rel in relationships:
                session.run("""
                    MATCH (a:Entity {id: $source_id})
                    MATCH (b:Entity {id: $target_id})
                    CREATE (a)-[r:RELATES {
                        type: $type,
                        description: $description,
                        confidence: $confidence
                    }]->(b)
                """, source_id=rel.source_id, target_id=rel.target_id,
                    type=rel.type, description=rel.description, 
                    confidence=rel.confidence)
    
    def query(self, question: str) -> str:
        """Запрос к графу знаний на естественном языке."""
        
        # Генерация Cypher запроса
        cypher = self.query_generator.run(f"""
        Преобразуйте этот вопрос в Cypher запрос для Neo4j:
        
        Вопрос: {question}
        
        Схема:
        - Узлы: Entity (id, name, type, description)
        - Связи: RELATES (type, description, confidence)
        
        Верните только Cypher запрос.
        """)
        
        cypher = self._extract_code(cypher, "cypher")
        
        # Выполнение запроса
        with self.driver.session() as session:
            try:
                result = session.run(cypher)
                records = list(result)
                
                if not records:
                    return "Результатов не найдено."
                
                # Форматирование результатов
                formatted = []
                for record in records[:10]:
                    formatted.append(str(dict(record)))
                
                return "\n".join(formatted)
                
            except Exception as e:
                return f"Ошибка запроса: {e}"
    
    def find_path(self, entity1: str, entity2: str, max_hops: int = 4) -> str:
        """Найти путь между двумя сущностями."""
        
        with self.driver.session() as session:
            result = session.run(f"""
                MATCH path = shortestPath(
                    (a:Entity {{name: $name1}})-[*..{max_hops}]-(b:Entity {{name: $name2}})
                )
                RETURN path
            """, name1=entity1, name2=entity2)
            
            records = list(result)
            
            if not records:
                return f"Путь между {entity1} и {entity2} не найден."
            
            # Форматировать путь
            path = records[0]["path"]
            nodes = [node["name"] for node in path.nodes]
            
            return " → ".join(nodes)
    
    def _generate_id(self, name: str, entity_type: str) -> str:
        """Генерация ID сущности."""
        content = f"{entity_type}:{name.lower()}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def _extract_json(self, text: str) -> str:
        """Извлечь JSON из ответа."""
        if "[" in text:
            start = text.find("[")
            end = text.rfind("]") + 1
            return text[start:end]
        elif "{" in text:
            start = text.find("{")
            end = text.rfind("}") + 1
            return text[start:end]
        return text
    
    def _extract_code(self, text: str, lang: str = "") -> str:
        """Извлечь код из markdown блока."""
        marker = f"```{lang}"
        if marker in text:
            start = text.find(marker) + len(marker)
            end = text.find("```", start)
            return text[start:end].strip()
        return text.strip()
    
    def _compute_stats(self, entities: List[Entity], relationships: List[Relationship]) -> GraphStats:
        """Вычислить статистику графа."""
        entity_types: Dict[str, int] = {}
        for e in entities:
            entity_types[e.type] = entity_types.get(e.type, 0) + 1
        
        rel_types: Dict[str, int] = {}
        for r in relationships:
            rel_types[r.type] = rel_types.get(r.type, 0) + 1
        
        return GraphStats(
            total_entities=len(entities),
            total_relationships=len(relationships),
            entity_types=entity_types,
            relationship_types=rel_types
        )

# Использование
if __name__ == "__main__":
    builder = KnowledgeGraphBuilder(
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="password"
    )
    
    # Построение графа
    stats = builder.build_from_documents("./docs")
    
    print(f"\n=== Статистика ===")
    print(f"Сущности по типам: {stats.entity_types}")
    print(f"Связи по типам: {stats.relationship_types}")
    
    # Запросы к графу
    answer = builder.query("Какие технологии использует OpenAI?")
    print(f"\n--- Запрос ---\n{answer}")
    
    # Поиск пути
    path = builder.find_path("Python", "Machine Learning")
    print(f"\n--- Путь ---\n{path}")
```

---

## 8. Семантический поиск по коду

Поиск по кодовой базе по смыслу, а не просто текстовый поиск.

```python
from rlm_toolkit import RLM
from rlm_toolkit.embeddings import OpenAIEmbeddings
from rlm_toolkit.vectorstores import ChromaVectorStore
from pydantic import BaseModel
from typing import List, Dict, Optional
import ast
import os

class CodeElement(BaseModel):
    type: str  # function, class, method, module
    name: str
    signature: str
    docstring: Optional[str]
    code: str
    file_path: str
    line_number: int
    semantic_description: str  # Сгенерировано AI

class SearchResult(BaseModel):
    element: CodeElement
    similarity: float
    explanation: str

class SemanticCodeSearch:
    """
    Семантический поиск по кодовой базе:
    1. Парсит код в элементы (функции, классы)
    2. Генерирует семантические описания через LLM
    3. Создаёт эмбеддинги для поиска
    4. Возвращает результаты с объяснениями
    """
    
    def __init__(self, project_path: str):
        self.project_path = project_path
        
        # Эмбеддинги
        self.embeddings = OpenAIEmbeddings("text-embedding-3-large")
        
        # Векторное хранилище
        self.vectorstore = ChromaVectorStore(
            collection_name="code_search",
            embedding_function=self.embeddings,
            persist_directory="./code_search_db"
        )
        
        # Описатель кода
        self.describer = RLM.from_openai("gpt-4o")
        self.describer.set_system_prompt("""
        Вы эксперт по документации кода. Для данного кода:
        1. Опишите что он делает простым языком
        2. Объясните алгоритм/подход
        3. Отметьте используемые паттерны
        4. Укажите зависимости и побочные эффекты
        
        Будьте кратки но исчерпывающи.
        """)
        
        # Объяснитель поиска
        self.explainer = RLM.from_openai("gpt-4o-mini")
        
        # Индекс
        self.elements: Dict[str, CodeElement] = {}
        
    def index_codebase(self):
        """Индексировать всю кодовую базу."""
        print(f"📂 Индексация {self.project_path}...")
        
        python_files = []
        for root, dirs, files in os.walk(self.project_path):
            # Пропуск стандартных не-кодовых директорий
            dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'node_modules', '.venv', 'venv']]
            
            for file in files:
                if file.endswith('.py'):
                    python_files.append(os.path.join(root, file))
        
        total_elements = 0
        
        for file_path in python_files:
            print(f"  📄 {file_path}")
            elements = self._parse_file(file_path)
            
            for element in elements:
                # Генерация семантического описания
                element.semantic_description = self._describe_code(element)
                
                # Сохранение
                element_id = f"{element.file_path}:{element.name}"
                self.elements[element_id] = element
                
                # Добавление в векторное хранилище
                search_text = f"""
                {element.type}: {element.name}
                {element.signature}
                {element.docstring or ''}
                {element.semantic_description}
                """
                
                self.vectorstore.add_texts(
                    [search_text],
                    metadatas=[{"id": element_id}]
                )
                
                total_elements += 1
        
        print(f"✅ Проиндексировано {total_elements} элементов кода")
    
    def _parse_file(self, file_path: str) -> List[CodeElement]:
        """Парсинг Python файла в элементы кода."""
        elements = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                source = f.read()
                tree = ast.parse(source)
            except:
                return []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                elements.append(self._extract_function(node, source, file_path))
            elif isinstance(node, ast.AsyncFunctionDef):
                elements.append(self._extract_function(node, source, file_path, is_async=True))
            elif isinstance(node, ast.ClassDef):
                elements.append(self._extract_class(node, source, file_path))
        
        return elements
    
    def _extract_function(self, node, source: str, file_path: str, is_async: bool = False) -> CodeElement:
        """Извлечь детали функции."""
        lines = source.split('\n')
        start = node.lineno - 1
        end = node.end_lineno if hasattr(node, 'end_lineno') else start + 1
        code = '\n'.join(lines[start:end])
        
        # Построение сигнатуры
        args = []
        for arg in node.args.args:
            arg_str = arg.arg
            if arg.annotation:
                arg_str += f": {ast.unparse(arg.annotation)}"
            args.append(arg_str)
        
        returns = ""
        if node.returns:
            returns = f" -> {ast.unparse(node.returns)}"
        
        prefix = "async def" if is_async else "def"
        signature = f"{prefix} {node.name}({', '.join(args)}){returns}"
        
        docstring = ast.get_docstring(node)
        
        return CodeElement(
            type="function",
            name=node.name,
            signature=signature,
            docstring=docstring,
            code=code,
            file_path=file_path,
            line_number=node.lineno,
            semantic_description=""
        )
    
    def _extract_class(self, node, source: str, file_path: str) -> CodeElement:
        """Извлечь детали класса."""
        lines = source.split('\n')
        start = node.lineno - 1
        end = node.end_lineno if hasattr(node, 'end_lineno') else start + 10
        code = '\n'.join(lines[start:min(end, start + 50)])
        
        bases = [ast.unparse(b) for b in node.bases]
        signature = f"class {node.name}({', '.join(bases)})" if bases else f"class {node.name}"
        
        docstring = ast.get_docstring(node)
        
        return CodeElement(
            type="class",
            name=node.name,
            signature=signature,
            docstring=docstring,
            code=code,
            file_path=file_path,
            line_number=node.lineno,
            semantic_description=""
        )
    
    def _describe_code(self, element: CodeElement) -> str:
        """Генерация семантического описания через LLM."""
        return self.describer.run(f"""
        Опишите этот {element.type}:
        
        {element.signature}
        
        ```python
        {element.code[:1500]}
        ```
        
        Дайте 2-3 предложения описания что он делает и как.
        """)
    
    def search(self, query: str, k: int = 10) -> List[SearchResult]:
        """Семантический поиск по кодовой базе."""
        
        # Расширение запроса через LLM
        enhanced_query = RLM.from_openai("gpt-4o-mini").run(f"""
        Расширьте этот поисковый запрос по коду техническими терминами:
        
        Запрос: {query}
        
        Добавьте: синонимы, связанные паттерны, детали реализации.
        Не более 100 слов.
        """)
        
        # Поиск в векторном хранилище
        results = self.vectorstore.similarity_search_with_score(
            enhanced_query, 
            k=k
        )
        
        search_results = []
        for doc, score in results:
            element_id = doc.metadata.get("id")
            if element_id and element_id in self.elements:
                element = self.elements[element_id]
                
                # Генерация объяснения
                explanation = self.explainer.run(f"""
                Объясните почему этот код соответствует запросу "{query}":
                
                {element.signature}
                {element.semantic_description}
                
                Одно предложение.
                """)
                
                search_results.append(SearchResult(
                    element=element,
                    similarity=1 - score,
                    explanation=explanation
                ))
        
        return search_results
    
    def find_similar(self, file_path: str, name: str, k: int = 5) -> List[SearchResult]:
        """Найти код похожий на конкретный элемент."""
        element_id = f"{file_path}:{name}"
        
        if element_id not in self.elements:
            return []
        
        element = self.elements[element_id]
        
        return self.search(element.semantic_description, k=k+1)[1:]

# Использование
if __name__ == "__main__":
    search = SemanticCodeSearch("./src")
    
    # Индексация кодовой базы
    search.index_codebase()
    
    # Семантический поиск
    results = search.search("функция валидации email адресов пользователей")
    
    print("\n=== Результаты поиска ===")
    for r in results[:5]:
        print(f"\n📍 {r.element.file_path}:{r.element.line_number}")
        print(f"   {r.element.signature}")
        print(f"   Сходство: {r.similarity:.2f}")
        print(f"   {r.explanation}")
    
    # Поиск похожего кода
    similar = search.find_similar("./src/auth.py", "validate_password")
    print("\n=== Похожие функции ===")
    for r in similar:
        print(f"  - {r.element.name}: {r.explanation}")
```

---

## 9. Система мультиагентных дебатов

Агенты дебатируют и приходят к консенсусу через структурированную аргументацию.

```python
from rlm_toolkit import RLM
from rlm_toolkit.agents.multiagent import MetaMatrix, Agent
from rlm_toolkit.memory import BufferMemory
from pydantic import BaseModel
from typing import List, Optional, Dict
from enum import Enum
import json

class Position(str, Enum):
    STRONGLY_AGREE = "strongly_agree"
    AGREE = "agree"
    NEUTRAL = "neutral"
    DISAGREE = "disagree"
    STRONGLY_DISAGREE = "strongly_disagree"

class Argument(BaseModel):
    agent: str
    position: Position
    claim: str
    evidence: List[str]
    rebuttals: List[str] = []
    confidence: float

class DebateRound(BaseModel):
    round_number: int
    topic: str
    arguments: List[Argument]
    consensus_reached: bool
    consensus_position: Optional[Position]

class DebateResult(BaseModel):
    topic: str
    rounds: List[DebateRound]
    final_consensus: Optional[Position]
    synthesis: str
    dissenting_views: List[str]

class MultiAgentDebate:
    """
    Система мультиагентных дебатов:
    1. Несколько агентов аргументируют позиции
    2. Агенты могут менять позиции на основе аргументов
    3. Модератор направляет дискуссию
    4. Система синтезирует консенсус или выделяет разногласия
    """
    
    def __init__(self, num_agents: int = 4):
        # Создание разнообразных агентов-дебатёров с разными перспективами
        self.agents: Dict[str, Agent] = {}
        
        perspectives = [
            ("Прагматик", "Фокус на практических последствиях, реальных доказательствах и проблемах внедрения."),
            ("Теоретик", "Фокус на принципах, фреймворках и логической согласованности."),
            ("Адвокат дьявола", "Оспаривает предположения, находит контраргументы, стресс-тестирует идеи."),
            ("Синтезатор", "Ищет общую почву, интегрирует перспективы, находит средний путь."),
            ("Скептик", "Требует доказательств, ставит под сомнение утверждения, выявляет логические ошибки."),
            ("Визионер", "Рассматривает долгосрочные последствия, новые тренды, возможные будущие сценарии.")
        ]
        
        for i in range(min(num_agents, len(perspectives))):
            name, style = perspectives[i]
            
            agent = Agent(
                name=name.lower(),
                description=style,
                llm=RLM.from_openai("gpt-4o")
            )
            agent.llm.set_system_prompt(f"""
            Вы {name} в структурированных дебатах. Ваш стиль:
            {style}
            
            Правила:
            - Представляйте чёткие, доказательные аргументы
            - Признавайте обоснованные пункты от других
            - Будьте готовы обновить позицию на основе новых доказательств
            - Оставайтесь уважительным но интеллектуально строгим
            - Оценивайте уверенность 0-1
            """)
            
            self.agents[name.lower()] = agent
        
        # Модератор
        self.moderator = RLM.from_anthropic("claude-3-opus")
        self.moderator.set_system_prompt("""
        Вы модератор дебатов. Ваша роль:
        1. Обеспечить честную дискуссию
        2. Выявить ключевые точки согласия/несогласия
        3. Задавать уточняющие вопросы
        4. Определить когда достигнут консенсус
        5. Синтезировать финальные выводы
        
        Будьте нейтральны и сфокусированы на поиске истины.
        """)
        
    def debate(self, topic: str, max_rounds: int = 5) -> DebateResult:
        """Провести структурированные дебаты по теме."""
        
        print(f"🎤 Тема дебатов: {topic}\n")
        
        rounds = []
        
        for round_num in range(1, max_rounds + 1):
            print(f"=== Раунд {round_num} ===")
            
            # Каждый агент представляет аргумент
            arguments = []
            previous_args = rounds[-1].arguments if rounds else []
            
            for name, agent in self.agents.items():
                print(f"  🗣️ {name.title()} выступает...")
                
                context = f"Тема: {topic}\n\n"
                if previous_args:
                    context += "Предыдущие аргументы:\n"
                    for arg in previous_args:
                        context += f"- {arg.agent}: {arg.claim} (уверенность: {arg.confidence})\n"
                
                response = agent.llm.run(f"""
                {context}
                
                Представьте ваш аргумент по теме: {topic}
                
                Укажите:
                1. Вашу позицию (strongly_agree/agree/neutral/disagree/strongly_disagree)
                2. Ваше главное утверждение
                3. Доказательства поддерживающие позицию
                4. Возражения на противоположные взгляды (если есть)
                5. Уровень уверенности (0-1)
                
                Формат JSON.
                """)
                
                try:
                    data = json.loads(response)
                    argument = Argument(
                        agent=name,
                        position=Position(data.get("position", "neutral")),
                        claim=data.get("claim", ""),
                        evidence=data.get("evidence", []),
                        rebuttals=data.get("rebuttals", []),
                        confidence=data.get("confidence", 0.5)
                    )
                    arguments.append(argument)
                except:
                    arguments.append(Argument(
                        agent=name,
                        position=Position.NEUTRAL,
                        claim=response[:200],
                        evidence=[],
                        confidence=0.5
                    ))
            
            # Модератор проверяет консенсус
            print("  🧑‍⚖️ Модератор оценивает...")
            
            consensus_check = self.moderator.run(f"""
            Проанализируйте эти позиции в дебатах:
            
            {json.dumps([{"agent": a.agent, "position": a.position.value, "claim": a.claim, "confidence": a.confidence} for a in arguments], indent=2, ensure_ascii=False)}
            
            Определите:
            1. Есть ли консенсус? (большинство согласно с высокой уверенностью)
            2. Какова консенсусная позиция если есть?
            3. Какие остаются точки разногласий?
            
            Верните JSON: {{"consensus": bool, "position": str или null, "disagreements": [str]}}
            """)
            
            try:
                consensus_data = json.loads(consensus_check)
                consensus_reached = consensus_data.get("consensus", False)
                consensus_position = Position(consensus_data["position"]) if consensus_data.get("position") else None
            except:
                consensus_reached = False
                consensus_position = None
            
            round_result = DebateRound(
                round_number=round_num,
                topic=topic,
                arguments=arguments,
                consensus_reached=consensus_reached,
                consensus_position=consensus_position
            )
            rounds.append(round_result)
            
            if consensus_reached:
                print(f"  ✅ Консенсус достигнут: {consensus_position.value}")
                break
            else:
                print(f"  🔄 Консенсус не достигнут, продолжаем...")
        
        # Финальный синтез
        print("\n📝 Генерация синтеза...")
        
        all_arguments = [arg for round in rounds for arg in round.arguments]
        
        synthesis = self.moderator.run(f"""
        Синтезируйте эти дебаты по теме: {topic}
        
        Все аргументы:
        {json.dumps([{"agent": a.agent, "position": a.position.value, "claim": a.claim} for a in all_arguments], indent=2, ensure_ascii=False)}
        
        Предоставьте:
        1. Резюме главных выводов
        2. Точки согласия
        3. Оставшиеся разногласия
        4. Рекомендации для дальнейшего исследования
        """)
        
        # Выявление особых мнений
        final_round = rounds[-1]
        final_consensus = final_round.consensus_position
        
        dissenting = []
        if final_consensus:
            for arg in final_round.arguments:
                if arg.position != final_consensus and arg.confidence > 0.6:
                    dissenting.append(f"{arg.agent}: {arg.claim}")
        
        return DebateResult(
            topic=topic,
            rounds=rounds,
            final_consensus=final_consensus,
            synthesis=synthesis,
            dissenting_views=dissenting
        )
    
    def quick_consensus(self, question: str) -> str:
        """Быстрая проверка консенсуса без полных дебатов."""
        responses = []
        
        for name, agent in self.agents.items():
            response = agent.llm.run(f"""
            Быстрый ответ: {question}
            
            Укажите: позиция (agree/disagree), обоснование в одно предложение, уверенность (0-1)
            """)
            responses.append(f"{name}: {response}")
        
        return self.moderator.run(f"""
        Подведите итог консенсуса по: {question}
        
        Ответы:
        {chr(10).join(responses)}
        
        Укажите: позиция большинства, уровень уверенности, ключевые причины
        """)

# Использование
if __name__ == "__main__":
    debate = MultiAgentDebate(num_agents=4)
    
    result = debate.debate(
        topic="Должны ли AI системы принимать автономные решения в здравоохранении?",
        max_rounds=4
    )
    
    print(f"\n=== Результат дебатов ===")
    print(f"Тема: {result.topic}")
    print(f"Раундов: {len(result.rounds)}")
    print(f"Финальный консенсус: {result.final_consensus}")
    print(f"\nСинтез:\n{result.synthesis}")
    
    if result.dissenting_views:
        print(f"\nОсобые мнения:")
        for view in result.dissenting_views:
            print(f"  - {view}")
```

---

## 10. Рекурсивный суммаризатор документов (InfiniRetri)

Обработка документов на 1000+ страниц с рекурсивной суммаризацией через InfiniRetri.

```python
from rlm_toolkit import RLM, RLMConfig
from rlm_toolkit.retrieval import InfiniRetriConfig
from rlm_toolkit.loaders import PDFLoader
from rlm_toolkit.splitters import RecursiveTextSplitter
from rlm_toolkit.embeddings import OpenAIEmbeddings
from rlm_toolkit.vectorstores import ChromaVectorStore
from pydantic import BaseModel
from typing import List, Dict, Optional
import math

class SectionSummary(BaseModel):
    title: str
    page_range: str
    summary: str
    key_points: List[str]
    entities: List[str]

class DocumentSummary(BaseModel):
    title: str
    total_pages: int
    executive_summary: str
    section_summaries: List[SectionSummary]
    key_themes: List[str]
    recommendations: List[str]

class RecursiveDocumentSummarizer:
    """
    Суммаризация массивных документов (1000+ страниц):
    1. Иерархическое разбиение на чанки
    2. Рекурсивная map-reduce суммаризация
    3. InfiniRetri для контекстно-зависимых запросов
    4. Многоуровневая абстракция
    """
    
    def __init__(self):
        # RLM с InfiniRetri для большого контекста
        self.config = RLMConfig(
            enable_infiniretri=True,
            infiniretri_config=InfiniRetriConfig(
                chunk_size=8000,
                top_k=10,
                overlap=1000
            ),
            infiniretri_threshold=50000
        )
        
        self.rlm = RLM.from_openai("gpt-4o", config=self.config)
        
        # Суммаризатор для отдельных секций
        self.section_summarizer = RLM.from_openai("gpt-4o")
        self.section_summarizer.set_system_prompt("""
        Вы эксперт по суммаризации документов. Для каждой секции:
        1. Определите главную тему
        2. Извлеките ключевые пункты (макс 5)
        3. Отметьте важные сущности (люди, организации, числа)
        4. Сохраните критические детали
        
        Будьте кратки но исчерпывающи.
        """)
        
        # Мета-суммаризатор для объединения саммари
        self.meta_summarizer = RLM.from_anthropic("claude-3-opus")
        self.meta_summarizer.set_system_prompt("""
        Вы синтезируете несколько саммари в связный нарратив.
        - Устраняйте избыточность
        - Поддерживайте логический поток
        - Выделяйте сквозные темы
        - Сохраняйте важные детали
        """)
        
        # Эмбеддинги и векторное хранилище для поиска
        self.embeddings = OpenAIEmbeddings("text-embedding-3-large")
        
    def summarize(self, pdf_path: str, target_length: str = "comprehensive") -> DocumentSummary:
        """
        Суммаризировать большой документ.
        
        target_length: "brief" (1 стр), "standard" (3-5 стр), "comprehensive" (10+ стр)
        """
        
        print(f"📖 Загрузка документа: {pdf_path}")
        
        # Загрузка документа
        docs = PDFLoader(pdf_path).load()
        total_pages = len(docs)
        full_text = "\n\n".join([d.page_content for d in docs])
        
        print(f"   Страниц: {total_pages}")
        print(f"   Символов: {len(full_text):,}")
        
        # Определение стратегии разбиения по размеру
        if total_pages < 50:
            chunk_size = 5000
            levels = 2
        elif total_pages < 200:
            chunk_size = 3000
            levels = 3
        else:
            chunk_size = 2000
            levels = 4
        
        print(f"   Используется {levels}-уровневая рекурсивная суммаризация")
        
        # Уровень 1: Разбиение и суммаризация
        print("\n🔄 Уровень 1: Суммаризация секций...")
        
        splitter = RecursiveTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=500
        )
        chunks = splitter.split_documents(docs)
        
        section_summaries = []
        chunk_groups = self._group_chunks(chunks, max_group_size=10)
        
        for i, group in enumerate(chunk_groups):
            print(f"   Секция {i+1}/{len(chunk_groups)}")
            
            combined_text = "\n\n".join([c.page_content for c in group])
            page_start = group[0].metadata.get("page", i * 10)
            page_end = group[-1].metadata.get("page", (i + 1) * 10)
            
            summary = self.section_summarizer.run(f"""
            Суммаризируйте эту секцию (страницы {page_start}-{page_end}):
            
            {combined_text[:15000]}
            
            Укажите:
            1. Название секции (выведите из контента)
            2. Саммари (200-300 слов)
            3. Ключевые пункты (макс 5)
            4. Важные упомянутые сущности
            """)
            
            section_summaries.append(SectionSummary(
                title=self._extract_title(summary),
                page_range=f"{page_start}-{page_end}",
                summary=summary,
                key_points=self._extract_key_points(summary),
                entities=self._extract_entities(summary)
            ))
        
        # Уровень 2+: Рекурсивная мета-суммаризация
        current_summaries = [s.summary for s in section_summaries]
        
        for level in range(2, levels + 1):
            print(f"\n🔄 Уровень {level}: Мета-суммаризация...")
            
            if len(current_summaries) <= 3:
                break
            
            grouped = self._group_texts(current_summaries, max_group_size=5)
            meta_summaries = []
            
            for group in grouped:
                combined = "\n\n---\n\n".join(group)
                
                meta_summary = self.meta_summarizer.run(f"""
                Синтезируйте эти саммари в связный нарратив:
                
                {combined}
                
                Сохраните ключевую информацию устраняя избыточность.
                Целевая длина: {500 // level} слов.
                """)
                
                meta_summaries.append(meta_summary)
            
            current_summaries = meta_summaries
        
        # Финальное executive summary
        print("\n📝 Генерация executive summary...")
        
        all_section_content = "\n\n".join(current_summaries)
        
        executive_summary = self.meta_summarizer.run(f"""
        Создайте executive summary из этих саммари секций:
        
        {all_section_content}
        
        Executive summary должно:
        1. Передать главную цель/тезис
        2. Выделить ключевые находки
        3. Отметить важные выводы
        4. Быть подходящим для руководителей высшего звена
        
        Длина: {self._get_target_words(target_length)} слов
        """)
        
        # Извлечение тем и рекомендаций
        themes = self._extract_themes(section_summaries)
        recommendations = self._extract_recommendations(executive_summary, section_summaries)
        
        # Построение векторного хранилища для Q&A
        print("\n💾 Построение поискового индекса...")
        self.vectorstore = ChromaVectorStore.from_documents(
            chunks,
            self.embeddings,
            collection_name="doc_summary"
        )
        self.rlm.set_retriever(self.vectorstore.as_retriever(k=10))
        
        return DocumentSummary(
            title=self._infer_title(docs[0].page_content[:2000]),
            total_pages=total_pages,
            executive_summary=executive_summary,
            section_summaries=section_summaries,
            key_themes=themes,
            recommendations=recommendations
        )
    
    def query(self, question: str) -> str:
        """Запрос к суммаризированному документу."""
        return self.rlm.run(f"""
        На основе документа ответьте: {question}
        
        Предоставьте конкретную информацию со ссылками на страницы где возможно.
        """)
    
    def _group_chunks(self, chunks, max_group_size: int):
        """Группировка чанков для секционной суммаризации."""
        groups = []
        current_group = []
        
        for chunk in chunks:
            current_group.append(chunk)
            if len(current_group) >= max_group_size:
                groups.append(current_group)
                current_group = []
        
        if current_group:
            groups.append(current_group)
        
        return groups
    
    def _group_texts(self, texts, max_group_size: int):
        """Группировка текстов для мета-суммаризации."""
        return [texts[i:i+max_group_size] for i in range(0, len(texts), max_group_size)]
    
    def _extract_title(self, text: str) -> str:
        """Извлечь название секции из саммари."""
        if ":" in text[:100]:
            return text[:text.find(":")].strip()
        return text[:50].strip() + "..."
    
    def _extract_key_points(self, text: str) -> List[str]:
        """Извлечь ключевые пункты из саммари."""
        lines = text.split("\n")
        points = [l.strip("- •*").strip() for l in lines if l.strip().startswith(("-", "•", "*", "1", "2", "3", "4", "5"))]
        return points[:5]
    
    def _extract_entities(self, text: str) -> List[str]:
        """Извлечь именованные сущности."""
        extractor = RLM.from_openai("gpt-4o-mini")
        result = extractor.run(f"Извлеките именованные сущности из: {text[:1000]}\nВерните JSON массив.")
        try:
            import json
            return json.loads(result)
        except:
            return []
    
    def _extract_themes(self, sections: List[SectionSummary]) -> List[str]:
        """Извлечь сквозные темы."""
        all_content = "\n".join([s.summary for s in sections])
        
        result = self.meta_summarizer.run(f"""
        Определите главные темы в этих секциях:
        
        {all_content[:5000]}
        
        Верните 5-7 ключевых тем списком.
        """)
        
        return result.split("\n")[:7]
    
    def _extract_recommendations(self, executive: str, sections: List[SectionSummary]) -> List[str]:
        """Извлечь или сгенерировать рекомендации."""
        result = self.meta_summarizer.run(f"""
        На основе этого саммари, какие ключевые рекомендации или действия?
        
        {executive}
        
        Предоставьте 3-5 конкретных рекомендаций.
        """)
        
        return result.split("\n")[:5]
    
    def _get_target_words(self, length: str) -> int:
        """Получить целевое количество слов."""
        return {"brief": 300, "standard": 800, "comprehensive": 1500}.get(length, 800)
    
    def _infer_title(self, first_page: str) -> str:
        """Определить название документа по первой странице."""
        result = RLM.from_openai("gpt-4o-mini").run(f"""
        Какое название этого документа?
        
        {first_page}
        
        Верните только название.
        """)
        return result.strip()

# Использование
if __name__ == "__main__":
    summarizer = RecursiveDocumentSummarizer()
    
    # Суммаризация большого документа
    summary = summarizer.summarize(
        "annual_report_500pages.pdf",
        target_length="comprehensive"
    )
    
    print(f"\n=== {summary.title} ===")
    print(f"Страниц: {summary.total_pages}")
    print(f"\n--- Executive Summary ---\n{summary.executive_summary}")
    
    print(f"\n--- Ключевые темы ---")
    for theme in summary.key_themes:
        print(f"  • {theme}")
    
    print(f"\n--- Секции ({len(summary.section_summaries)}) ---")
    for section in summary.section_summaries[:5]:
        print(f"  📑 {section.title} (стр. {section.page_range})")
    
    # Запрос к документу
    answer = summarizer.query("Какие были главные финансовые результаты?")
    print(f"\n--- Q&A ---\n{answer}")
```

---

*Продолжение в Части 3: Безопасность и продакшен примеры...*
