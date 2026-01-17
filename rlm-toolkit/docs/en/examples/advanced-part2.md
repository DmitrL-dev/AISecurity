# Advanced Examples - Part 2

R&D and cutting-edge examples showcasing RLM-Toolkit's unique capabilities.

---

## 6. Self-Improving Code Generator

R-Zero pattern that iteratively improves its own code through self-critique.

```python
from rlm_toolkit import RLM
from rlm_toolkit.evolve import SelfEvolvingRLM, EvolutionConfig
from rlm_toolkit.tools import PythonREPL, Tool
from rlm_toolkit.agents import ReActAgent
from pydantic import BaseModel
from typing import List, Optional
from enum import Enum
import ast
import subprocess

class CodeQuality(BaseModel):
    correctness: float  # 0-1
    efficiency: float
    readability: float
    test_coverage: float
    overall: float

class CodeIteration(BaseModel):
    version: int
    code: str
    quality: CodeQuality
    issues: List[str]
    improvements: List[str]

class SelfImprovingCodeGenerator:
    """
    Self-improving code generator using R-Zero Challenger-Solver pattern:
    1. Generates initial code
    2. Challenger critiques and finds issues
    3. Solver improves based on critique
    4. Repeat until quality threshold met
    """
    
    def __init__(self, max_iterations: int = 5, quality_threshold: float = 0.9):
        self.max_iterations = max_iterations
        self.quality_threshold = quality_threshold
        
        # Initial generator
        self.generator = RLM.from_openai("gpt-4o")
        self.generator.set_system_prompt("""
        You are an expert Python developer. Write:
        - Clean, readable code
        - Comprehensive docstrings
        - Type hints throughout
        - Error handling
        - Edge case handling
        
        Follow PEP 8 and best practices.
        """)
        
        # Challenger (critic)
        self.challenger = RLM.from_anthropic("claude-3-opus")
        self.challenger.set_system_prompt("""
        You are a ruthless code reviewer. Find:
        - Bugs and logical errors
        - Performance issues (O(n²) vs O(n log n))
        - Missing edge cases
        - Security vulnerabilities
        - Code smells
        - Missing tests
        - Unclear variable names
        
        Be extremely critical. Rate each aspect 0-1.
        """)
        
        # Solver (improver)
        self.solver = RLM.from_openai("gpt-4o")
        self.solver.set_system_prompt("""
        You are a code improvement expert. Given critique:
        1. Address each issue systematically
        2. Optimize performance where possible
        3. Add missing tests
        4. Improve readability
        5. Fix all bugs
        
        Return only the improved code, nothing else.
        """)
        
        # Test runner
        self.repl = PythonREPL(max_execution_time=30)
        
    def generate(self, task: str) -> CodeIteration:
        """Generate code with iterative improvement."""
        
        iterations: List[CodeIteration] = []
        
        # Initial generation
        print("📝 Generating initial code...")
        code = self.generator.run(f"""
        Write Python code for: {task}
        
        Include:
        - Main implementation
        - Helper functions as needed
        - Comprehensive tests using pytest
        - Usage example in if __name__ == "__main__"
        """)
        
        code = self._extract_code(code)
        
        for i in range(self.max_iterations):
            print(f"\n🔄 Iteration {i + 1}/{self.max_iterations}")
            
            # Challenger critiques
            print("  🎯 Challenger analyzing...")
            critique = self.challenger.run(f"""
            Analyze this code critically:
            
            ```python
            {code}
            ```
            
            Provide:
            1. Correctness score (0-1) with bugs found
            2. Efficiency score (0-1) with optimization opportunities
            3. Readability score (0-1) with clarity issues
            4. Test coverage score (0-1) with missing tests
            5. List of specific issues to fix
            6. Overall score (0-1)
            """)
            
            quality = self._parse_quality(critique)
            issues = self._extract_issues(critique)
            
            iteration = CodeIteration(
                version=i + 1,
                code=code,
                quality=quality,
                issues=issues,
                improvements=[]
            )
            iterations.append(iteration)
            
            print(f"  📊 Quality: {quality.overall:.2f}")
            
            # Check if good enough
            if quality.overall >= self.quality_threshold:
                print(f"  ✅ Quality threshold met!")
                break
            
            # Run tests to find actual failures
            print("  🧪 Running tests...")
            test_results = self._run_tests(code)
            
            # Solver improves
            print("  🔧 Solver improving...")
            improved_code = self.solver.run(f"""
            Improve this code based on the critique:
            
            CURRENT CODE:
            ```python
            {code}
            ```
            
            CRITIQUE:
            {critique}
            
            TEST RESULTS:
            {test_results}
            
            ISSUES TO FIX:
            {issues}
            
            Return the improved code only, no explanations.
            """)
            
            code = self._extract_code(improved_code)
            iteration.improvements = self._summarize_improvements(code, iteration.code)
        
        # Final iteration
        final = iterations[-1]
        final.code = code
        
        return final
    
    def _extract_code(self, response: str) -> str:
        """Extract Python code from response."""
        if "```python" in response:
            start = response.find("```python") + 9
            end = response.find("```", start)
            return response[start:end].strip()
        elif "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            return response[start:end].strip()
        return response.strip()
    
    def _parse_quality(self, critique: str) -> CodeQuality:
        """Parse quality scores from critique."""
        # Use LLM to extract structured scores
        extractor = RLM.from_openai("gpt-4o-mini")
        scores = extractor.run(f"""
        Extract scores from this critique as JSON:
        
        {critique}
        
        Return: {{"correctness": float, "efficiency": float, "readability": float, "test_coverage": float, "overall": float}}
        All values 0-1.
        """)
        
        try:
            import json
            data = json.loads(scores)
            return CodeQuality(**data)
        except:
            return CodeQuality(
                correctness=0.5,
                efficiency=0.5,
                readability=0.5,
                test_coverage=0.5,
                overall=0.5
            )
    
    def _extract_issues(self, critique: str) -> List[str]:
        """Extract list of issues from critique."""
        extractor = RLM.from_openai("gpt-4o-mini")
        issues = extractor.run(f"""
        Extract issues list from this critique:
        
        {critique}
        
        Return as JSON array of strings.
        """)
        
        try:
            import json
            return json.loads(issues)
        except:
            return ["Unable to parse issues"]
    
    def _run_tests(self, code: str) -> str:
        """Run tests and return results."""
        # Write code to temp file
        with open("temp_code.py", "w") as f:
            f.write(code)
        
        # Run pytest
        result = subprocess.run(
            ["pytest", "temp_code.py", "-v", "--tb=short"],
            capture_output=True,
            text=True
        )
        
        return result.stdout + result.stderr
    
    def _summarize_improvements(self, new_code: str, old_code: str) -> List[str]:
        """Summarize what was improved."""
        summarizer = RLM.from_openai("gpt-4o-mini")
        summary = summarizer.run(f"""
        What was improved between these versions?
        
        OLD:
        {old_code[:2000]}
        
        NEW:
        {new_code[:2000]}
        
        List improvements as JSON array.
        """)
        
        try:
            import json
            return json.loads(summary)
        except:
            return ["Code improved"]

# Usage
if __name__ == "__main__":
    generator = SelfImprovingCodeGenerator(
        max_iterations=5,
        quality_threshold=0.85
    )
    
    result = generator.generate("""
    Create a function to find the longest palindromic substring in a string.
    Should handle edge cases and be efficient (better than O(n³)).
    Include comprehensive tests.
    """)
    
    print(f"\n=== Final Result ===")
    print(f"Iterations: {result.version}")
    print(f"Quality: {result.quality.overall:.2f}")
    print(f"\nCode:\n{result.code}")
```

---

## 7. Knowledge Graph Builder

Automatically builds knowledge graphs from documents using entity extraction and relationship mapping.

```python
from rlm_toolkit import RLM
from rlm_toolkit.loaders import PDFLoader, DirectoryLoader
from rlm_toolkit.splitters import SemanticSplitter
from rlm_toolkit.embeddings import OpenAIEmbeddings
from pydantic import BaseModel
from typing import List, Dict, Optional, Set, Tuple
from neo4j import GraphDatabase
import json

class Entity(BaseModel):
    name: str
    type: str  # person, organization, concept, technology, location, event
    description: Optional[str]
    aliases: List[str] = []
    properties: Dict[str, str] = {}

class Relationship(BaseModel):
    source: str
    target: str
    type: str  # works_for, uses, created_by, part_of, related_to, etc.
    description: Optional[str]
    confidence: float
    source_text: str

class KnowledgeGraph(BaseModel):
    entities: List[Entity]
    relationships: List[Relationship]

class KnowledgeGraphBuilder:
    """
    Builds knowledge graphs from documents:
    1. Extracts entities (people, orgs, concepts)
    2. Identifies relationships between entities
    3. Resolves entity coreferences
    4. Stores in Neo4j graph database
    5. Enables graph queries
    """
    
    def __init__(self, neo4j_uri: str = "bolt://localhost:7687", 
                 neo4j_user: str = "neo4j", neo4j_password: str = "password"):
        # Entity extractor
        self.entity_extractor = RLM.from_openai("gpt-4o")
        self.entity_extractor.set_system_prompt("""
        You are an expert at extracting entities from text.
        Extract:
        - People (with roles/titles if mentioned)
        - Organizations (companies, teams, groups)
        - Technologies (frameworks, languages, tools)
        - Concepts (abstract ideas, methodologies)
        - Locations (if relevant)
        - Events (if mentioned)
        
        For each entity provide:
        - Canonical name
        - Type
        - Brief description
        - Any aliases or alternate names
        """)
        
        # Relationship extractor
        self.relationship_extractor = RLM.from_anthropic("claude-3-sonnet")
        self.relationship_extractor.set_system_prompt("""
        You are an expert at identifying relationships between entities.
        
        Relationship types:
        - WORKS_FOR: employment
        - FOUNDED: created organization
        - USES: utilizes technology
        - PART_OF: membership/component
        - DEPENDS_ON: technical dependency
        - RELATED_TO: general relation
        - CREATED: authorship
        - LOCATED_IN: geographic
        - COLLABORATED_WITH: partnership
        - SUCCESSOR_OF: timeline
        
        Extract relationships with confidence scores.
        """)
        
        # Entity resolver (coreference)
        self.resolver = RLM.from_openai("gpt-4o-mini")
        self.resolver.set_system_prompt("""
        You resolve entity coreferences. Given entities:
        - Identify which refer to the same thing
        - Choose canonical name
        - Merge properties
        
        Example: "Microsoft", "MSFT", "Microsoft Corporation" -> "Microsoft"
        """)
        
        # Neo4j connection
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        
        # Embeddings for semantic similarity
        self.embeddings = OpenAIEmbeddings("text-embedding-3-small")
        
        # Entity cache for deduplication
        self.entity_cache: Dict[str, Entity] = {}
        
    def build_from_documents(self, paths: List[str]) -> KnowledgeGraph:
        """Build knowledge graph from documents."""
        
        all_entities = []
        all_relationships = []
        
        for path in paths:
            print(f"📄 Processing: {path}")
            
            # Load and split
            if path.endswith(".pdf"):
                docs = PDFLoader(path).load()
            else:
                with open(path, "r") as f:
                    from rlm_toolkit.loaders import Document
                    docs = [Document(page_content=f.read(), metadata={"source": path})]
            
            splitter = SemanticSplitter(chunk_size=1000, threshold=0.7)
            chunks = splitter.split_documents(docs)
            
            for i, chunk in enumerate(chunks):
                print(f"  🔍 Chunk {i+1}/{len(chunks)}")
                
                # Extract entities
                entities = self._extract_entities(chunk.page_content)
                all_entities.extend(entities)
                
                # Extract relationships
                relationships = self._extract_relationships(
                    chunk.page_content, 
                    entities
                )
                all_relationships.extend(relationships)
        
        # Resolve coreferences
        print("🔗 Resolving entity coreferences...")
        resolved_entities = self._resolve_entities(all_entities)
        
        # Update relationships with resolved names
        resolved_relationships = self._update_relationships(
            all_relationships, 
            resolved_entities
        )
        
        # Store in Neo4j
        print("💾 Storing in Neo4j...")
        self._store_graph(resolved_entities, resolved_relationships)
        
        return KnowledgeGraph(
            entities=resolved_entities,
            relationships=resolved_relationships
        )
    
    def _extract_entities(self, text: str) -> List[Entity]:
        """Extract entities from text chunk."""
        result = self.entity_extractor.run(f"""
        Extract all entities from this text:
        
        {text}
        
        Return as JSON array:
        [
            {{"name": str, "type": str, "description": str, "aliases": [str]}}
        ]
        """)
        
        try:
            data = json.loads(result)
            return [Entity(**e) for e in data]
        except:
            return []
    
    def _extract_relationships(self, text: str, entities: List[Entity]) -> List[Relationship]:
        """Extract relationships between entities."""
        entity_names = [e.name for e in entities]
        
        result = self.relationship_extractor.run(f"""
        Extract relationships between these entities:
        Entities: {entity_names}
        
        Text:
        {text}
        
        Return as JSON array:
        [
            {{
                "source": str,
                "target": str,
                "type": str,
                "description": str,
                "confidence": float
            }}
        ]
        """)
        
        try:
            data = json.loads(result)
            relationships = []
            for r in data:
                r["source_text"] = text[:200]
                relationships.append(Relationship(**r))
            return relationships
        except:
            return []
    
    def _resolve_entities(self, entities: List[Entity]) -> List[Entity]:
        """Resolve entity coreferences."""
        # Group potentially same entities
        entity_names = list(set([e.name for e in entities]))
        
        resolution = self.resolver.run(f"""
        Group these entities that refer to the same thing:
        
        {entity_names}
        
        Return as JSON:
        {{
            "canonical_name": ["alias1", "alias2", ...]
        }}
        """)
        
        try:
            groups = json.loads(resolution)
        except:
            groups = {}
        
        # Create mapping
        name_to_canonical = {}
        for canonical, aliases in groups.items():
            for alias in aliases:
                name_to_canonical[alias] = canonical
            name_to_canonical[canonical] = canonical
        
        # Merge entities
        canonical_entities = {}
        for entity in entities:
            canonical_name = name_to_canonical.get(entity.name, entity.name)
            
            if canonical_name not in canonical_entities:
                entity.name = canonical_name
                canonical_entities[canonical_name] = entity
            else:
                # Merge properties
                existing = canonical_entities[canonical_name]
                existing.aliases.extend(entity.aliases)
                existing.properties.update(entity.properties)
        
        return list(canonical_entities.values())
    
    def _update_relationships(
        self, 
        relationships: List[Relationship], 
        entities: List[Entity]
    ) -> List[Relationship]:
        """Update relationship entity names to canonical forms."""
        entity_names = {e.name for e in entities}
        
        valid_relationships = []
        for rel in relationships:
            if rel.source in entity_names and rel.target in entity_names:
                valid_relationships.append(rel)
        
        return valid_relationships
    
    def _store_graph(self, entities: List[Entity], relationships: List[Relationship]):
        """Store graph in Neo4j."""
        with self.driver.session() as session:
            # Clear existing
            session.run("MATCH (n) DETACH DELETE n")
            
            # Create entities
            for entity in entities:
                session.run(f"""
                CREATE (n:{entity.type} {{
                    name: $name,
                    description: $description,
                    aliases: $aliases
                }})
                """, 
                name=entity.name,
                description=entity.description or "",
                aliases=entity.aliases
                )
            
            # Create relationships
            for rel in relationships:
                session.run(f"""
                MATCH (a {{name: $source}})
                MATCH (b {{name: $target}})
                CREATE (a)-[r:{rel.type} {{
                    description: $description,
                    confidence: $confidence
                }}]->(b)
                """,
                source=rel.source,
                target=rel.target,
                description=rel.description or "",
                confidence=rel.confidence
                )
    
    def query(self, question: str) -> str:
        """Query the knowledge graph with natural language."""
        # Generate Cypher query
        cypher = RLM.from_openai("gpt-4o").run(f"""
        Convert this question to a Cypher query:
        
        Question: {question}
        
        Available node types: Person, Organization, Technology, Concept, Location, Event
        Available relationship types: WORKS_FOR, FOUNDED, USES, PART_OF, DEPENDS_ON, RELATED_TO, CREATED, COLLABORATED_WITH
        
        Return only the Cypher query.
        """)
        
        # Execute query
        with self.driver.session() as session:
            try:
                result = session.run(cypher)
                records = [dict(record) for record in result]
            except Exception as e:
                return f"Query error: {e}"
        
        # Generate natural answer
        answer = RLM.from_openai("gpt-4o").run(f"""
        Answer this question based on the graph data:
        
        Question: {question}
        Data: {records}
        
        Provide a natural language answer.
        """)
        
        return answer
    
    def visualize(self, output_path: str = "graph.html"):
        """Generate interactive graph visualization."""
        with self.driver.session() as session:
            nodes = session.run("MATCH (n) RETURN n.name as name, labels(n)[0] as type")
            edges = session.run("MATCH (a)-[r]->(b) RETURN a.name as source, b.name as target, type(r) as type")
        
        # Generate vis.js visualization
        html = self._generate_vis_html(
            [dict(n) for n in nodes],
            [dict(e) for e in edges]
        )
        
        with open(output_path, "w") as f:
            f.write(html)
        
        print(f"Visualization saved to {output_path}")

# Usage
if __name__ == "__main__":
    builder = KnowledgeGraphBuilder()
    
    # Build from documents
    graph = builder.build_from_documents([
        "company_wiki.md",
        "team_structure.pdf",
        "technology_stack.md"
    ])
    
    print(f"Entities: {len(graph.entities)}")
    print(f"Relationships: {len(graph.relationships)}")
    
    # Query the graph
    answer = builder.query("Who works on the AI team?")
    print(f"\nAnswer: {answer}")
    
    # Visualize
    builder.visualize("knowledge_graph.html")
```

---

## 8. Semantic Code Search

Search codebase by meaning, not just text matching.

```python
from rlm_toolkit import RLM
from rlm_toolkit.embeddings import OpenAIEmbeddings
from rlm_toolkit.vectorstores import ChromaVectorStore
from rlm_toolkit.loaders import DirectoryLoader
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
    semantic_description: str  # AI-generated

class SearchResult(BaseModel):
    element: CodeElement
    similarity: float
    explanation: str

class SemanticCodeSearch:
    """
    Search codebase by semantic meaning:
    1. Parses code into elements (functions, classes)
    2. Generates semantic descriptions using LLM
    3. Creates embeddings for search
    4. Returns results with explanations
    """
    
    def __init__(self, project_path: str):
        self.project_path = project_path
        
        # Embeddings
        self.embeddings = OpenAIEmbeddings("text-embedding-3-large")
        
        # Vector store
        self.vectorstore = ChromaVectorStore(
            collection_name="code_search",
            embedding_function=self.embeddings,
            persist_directory="./code_search_db"
        )
        
        # Code describer
        self.describer = RLM.from_openai("gpt-4o")
        self.describer.set_system_prompt("""
        You are a code documentation expert. Given code:
        1. Describe what it does in plain English
        2. Explain the algorithm/approach
        3. Note any patterns used
        4. Mention dependencies and side effects
        
        Be concise but comprehensive.
        """)
        
        # Search explainer
        self.explainer = RLM.from_openai("gpt-4o-mini")
        
        # Index
        self.elements: Dict[str, CodeElement] = {}
        
    def index_codebase(self):
        """Index entire codebase."""
        print(f"📂 Indexing {self.project_path}...")
        
        python_files = []
        for root, dirs, files in os.walk(self.project_path):
            # Skip common non-code directories
            dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'node_modules', '.venv', 'venv']]
            
            for file in files:
                if file.endswith('.py'):
                    python_files.append(os.path.join(root, file))
        
        total_elements = 0
        
        for file_path in python_files:
            print(f"  📄 {file_path}")
            elements = self._parse_file(file_path)
            
            for element in elements:
                # Generate semantic description
                element.semantic_description = self._describe_code(element)
                
                # Store
                element_id = f"{element.file_path}:{element.name}"
                self.elements[element_id] = element
                
                # Add to vector store
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
        
        print(f"✅ Indexed {total_elements} code elements")
    
    def _parse_file(self, file_path: str) -> List[CodeElement]:
        """Parse Python file into code elements."""
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
        """Extract function details."""
        # Get source lines
        lines = source.split('\n')
        start = node.lineno - 1
        end = node.end_lineno if hasattr(node, 'end_lineno') else start + 1
        code = '\n'.join(lines[start:end])
        
        # Build signature
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
        
        # Get docstring
        docstring = ast.get_docstring(node)
        
        return CodeElement(
            type="function",
            name=node.name,
            signature=signature,
            docstring=docstring,
            code=code,
            file_path=file_path,
            line_number=node.lineno,
            semantic_description=""  # Will be filled later
        )
    
    def _extract_class(self, node, source: str, file_path: str) -> CodeElement:
        """Extract class details."""
        lines = source.split('\n')
        start = node.lineno - 1
        end = node.end_lineno if hasattr(node, 'end_lineno') else start + 10
        code = '\n'.join(lines[start:min(end, start + 50)])  # Limit length
        
        # Get bases
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
        """Generate semantic description using LLM."""
        return self.describer.run(f"""
        Describe this {element.type}:
        
        {element.signature}
        
        ```python
        {element.code[:1500]}
        ```
        
        Provide a 2-3 sentence description of what it does and how.
        """)
    
    def search(self, query: str, k: int = 10) -> List[SearchResult]:
        """Search codebase semantically."""
        
        # Enhance query with LLM
        enhanced_query = RLM.from_openai("gpt-4o-mini").run(f"""
        Expand this code search query with related technical terms:
        
        Query: {query}
        
        Add: synonyms, related patterns, implementation details.
        Keep it under 100 words.
        """)
        
        # Search vector store
        results = self.vectorstore.similarity_search_with_score(
            enhanced_query, 
            k=k
        )
        
        search_results = []
        for doc, score in results:
            element_id = doc.metadata.get("id")
            if element_id and element_id in self.elements:
                element = self.elements[element_id]
                
                # Generate explanation
                explanation = self.explainer.run(f"""
                Explain why this code matches the query "{query}":
                
                {element.signature}
                {element.semantic_description}
                
                One sentence explanation.
                """)
                
                search_results.append(SearchResult(
                    element=element,
                    similarity=1 - score,  # Convert distance to similarity
                    explanation=explanation
                ))
        
        return search_results
    
    def find_similar(self, file_path: str, name: str, k: int = 5) -> List[SearchResult]:
        """Find code similar to a specific element."""
        element_id = f"{file_path}:{name}"
        
        if element_id not in self.elements:
            return []
        
        element = self.elements[element_id]
        
        # Search using the element's description
        return self.search(element.semantic_description, k=k+1)[1:]  # Exclude self

# Usage
if __name__ == "__main__":
    search = SemanticCodeSearch("./src")
    
    # Index codebase
    search.index_codebase()
    
    # Semantic search
    results = search.search("function that validates user email addresses")
    
    print("\n=== Search Results ===")
    for r in results[:5]:
        print(f"\n📍 {r.element.file_path}:{r.element.line_number}")
        print(f"   {r.element.signature}")
        print(f"   Similarity: {r.similarity:.2f}")
        print(f"   {r.explanation}")
    
    # Find similar code
    similar = search.find_similar("./src/auth.py", "validate_password")
    print("\n=== Similar Functions ===")
    for r in similar:
        print(f"  - {r.element.name}: {r.explanation}")
```

---

## 9. Multi-Agent Debate System

Agents debate and reach consensus through structured argumentation.

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
    Multi-agent debate system where:
    1. Multiple agents argue positions
    2. Agents can change positions based on arguments
    3. Moderator guides discussion
    4. System synthesizes consensus or highlights disagreements
    """
    
    def __init__(self, num_agents: int = 4):
        # Create diverse debater agents with different perspectives
        self.agents: Dict[str, Agent] = {}
        
        perspectives = [
            ("Pragmatist", "Focus on practical implications, real-world evidence, and implementation challenges."),
            ("Theorist", "Focus on principles, frameworks, and logical consistency."),
            ("Devil's Advocate", "Challenge assumptions, find counterarguments, stress-test ideas."),
            ("Synthesizer", "Look for common ground, integrate perspectives, find middle paths."),
            ("Skeptic", "Demand evidence, question claims, identify logical fallacies."),
            ("Visionary", "Consider long-term implications, emerging trends, potential futures.")
        ]
        
        for i in range(min(num_agents, len(perspectives))):
            name, style = perspectives[i]
            
            agent = Agent(
                name=name.lower(),
                description=style,
                llm=RLM.from_openai("gpt-4o")
            )
            agent.llm.set_system_prompt(f"""
            You are the {name} in a structured debate. Your style:
            {style}
            
            Rules:
            - Present clear, evidence-based arguments
            - Acknowledge valid points from others
            - Be willing to update position based on new evidence
            - Stay respectful but intellectually rigorous
            - Rate your confidence 0-1
            """)
            
            self.agents[name.lower()] = agent
        
        # Moderator
        self.moderator = RLM.from_anthropic("claude-3-opus")
        self.moderator.set_system_prompt("""
        You are a debate moderator. Your role:
        1. Ensure fair discussion
        2. Identify key points of agreement/disagreement
        3. Ask clarifying questions
        4. Determine when consensus is reached
        5. Synthesize final conclusions
        
        Be neutral and focused on truth-seeking.
        """)
        
    def debate(self, topic: str, max_rounds: int = 5) -> DebateResult:
        """Run structured debate on a topic."""
        
        print(f"🎤 Debate Topic: {topic}\n")
        
        rounds = []
        
        for round_num in range(1, max_rounds + 1):
            print(f"=== Round {round_num} ===")
            
            # Each agent presents argument
            arguments = []
            previous_args = rounds[-1].arguments if rounds else []
            
            for name, agent in self.agents.items():
                print(f"  🗣️ {name.title()} presenting...")
                
                context = f"Topic: {topic}\n\n"
                if previous_args:
                    context += "Previous arguments:\n"
                    for arg in previous_args:
                        context += f"- {arg.agent}: {arg.claim} (confidence: {arg.confidence})\n"
                
                response = agent.llm.run(f"""
                {context}
                
                Present your argument on: {topic}
                
                Provide:
                1. Your position (strongly_agree/agree/neutral/disagree/strongly_disagree)
                2. Your main claim
                3. Evidence supporting your position
                4. Rebuttals to opposing views (if any)
                5. Confidence level (0-1)
                
                Format as JSON.
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
            
            # Moderator checks for consensus
            print("  🧑‍⚖️ Moderator evaluating...")
            
            positions = [arg.position for arg in arguments]
            confidences = [arg.confidence for arg in arguments]
            
            consensus_check = self.moderator.run(f"""
            Analyze these debate positions:
            
            {json.dumps([{"agent": a.agent, "position": a.position.value, "claim": a.claim, "confidence": a.confidence} for a in arguments], indent=2)}
            
            Determine:
            1. Is there consensus? (majority agreement with high confidence)
            2. What is the consensus position if any?
            3. What are the remaining points of disagreement?
            
            Return as JSON: {{"consensus": bool, "position": str or null, "disagreements": [str]}}
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
                print(f"  ✅ Consensus reached: {consensus_position.value}")
                break
            else:
                print(f"  🔄 No consensus yet, continuing...")
        
        # Final synthesis
        print("\n📝 Generating synthesis...")
        
        all_arguments = [arg for round in rounds for arg in round.arguments]
        
        synthesis = self.moderator.run(f"""
        Synthesize this debate on: {topic}
        
        All arguments:
        {json.dumps([{"agent": a.agent, "position": a.position.value, "claim": a.claim} for a in all_arguments], indent=2)}
        
        Provide:
        1. Summary of main conclusions
        2. Points of agreement
        3. Remaining disagreements
        4. Recommendations for further investigation
        """)
        
        # Identify dissenting views
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
        """Quick consensus check without full debate."""
        responses = []
        
        for name, agent in self.agents.items():
            response = agent.llm.run(f"""
            Quick answer: {question}
            
            Provide: position (agree/disagree), one-sentence rationale, confidence (0-1)
            """)
            responses.append(f"{name}: {response}")
        
        return self.moderator.run(f"""
        Summarize the consensus on: {question}
        
        Responses:
        {'\n'.join(responses)}
        
        Provide: majority position, confidence level, key reasons
        """)

# Usage
if __name__ == "__main__":
    debate = MultiAgentDebate(num_agents=4)
    
    result = debate.debate(
        topic="Should AI systems be allowed to make autonomous decisions in healthcare?",
        max_rounds=4
    )
    
    print(f"\n=== Debate Result ===")
    print(f"Topic: {result.topic}")
    print(f"Rounds: {len(result.rounds)}")
    print(f"Final Consensus: {result.final_consensus}")
    print(f"\nSynthesis:\n{result.synthesis}")
    
    if result.dissenting_views:
        print(f"\nDissenting Views:")
        for view in result.dissenting_views:
            print(f"  - {view}")
```

---

## 10. Recursive Document Summarizer (InfiniRetri)

Handle 1000+ page documents with recursive summarization using InfiniRetri.

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
    Summarizes massive documents (1000+ pages) using:
    1. Hierarchical chunking
    2. Recursive map-reduce summarization
    3. InfiniRetri for context-aware queries
    4. Multi-level abstraction
    """
    
    def __init__(self):
        # InfiniRetri-enabled RLM for large context
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
        
        # Summarizer for individual sections
        self.section_summarizer = RLM.from_openai("gpt-4o")
        self.section_summarizer.set_system_prompt("""
        You are an expert document summarizer. For each section:
        1. Identify the main topic
        2. Extract key points (max 5)
        3. Note important entities (people, orgs, numbers)
        4. Preserve critical details
        
        Be concise but comprehensive.
        """)
        
        # Meta-summarizer for combining summaries
        self.meta_summarizer = RLM.from_anthropic("claude-3-opus")
        self.meta_summarizer.set_system_prompt("""
        You synthesize multiple summaries into coherent narratives.
        - Eliminate redundancy
        - Maintain logical flow
        - Highlight cross-cutting themes
        - Preserve important details
        """)
        
        # Embeddings and vector store for retrieval
        self.embeddings = OpenAIEmbeddings("text-embedding-3-large")
        
    def summarize(self, pdf_path: str, target_length: str = "comprehensive") -> DocumentSummary:
        """
        Summarize a large document.
        
        target_length: "brief" (1 page), "standard" (3-5 pages), "comprehensive" (10+ pages)
        """
        
        print(f"📖 Loading document: {pdf_path}")
        
        # Load document
        docs = PDFLoader(pdf_path).load()
        total_pages = len(docs)
        full_text = "\n\n".join([d.page_content for d in docs])
        
        print(f"   Pages: {total_pages}")
        print(f"   Characters: {len(full_text):,}")
        
        # Determine chunking strategy based on size
        if total_pages < 50:
            chunk_size = 5000
            levels = 2
        elif total_pages < 200:
            chunk_size = 3000
            levels = 3
        else:
            chunk_size = 2000
            levels = 4
        
        print(f"   Using {levels}-level recursive summarization")
        
        # Level 1: Chunk and summarize
        print("\n🔄 Level 1: Section summaries...")
        
        splitter = RecursiveTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=500
        )
        chunks = splitter.split_documents(docs)
        
        section_summaries = []
        chunk_groups = self._group_chunks(chunks, max_group_size=10)
        
        for i, group in enumerate(chunk_groups):
            print(f"   Section {i+1}/{len(chunk_groups)}")
            
            combined_text = "\n\n".join([c.page_content for c in group])
            page_start = group[0].metadata.get("page", i * 10)
            page_end = group[-1].metadata.get("page", (i + 1) * 10)
            
            summary = self.section_summarizer.run(f"""
            Summarize this section (pages {page_start}-{page_end}):
            
            {combined_text[:15000]}
            
            Provide:
            1. Section title (inferred from content)
            2. Summary (200-300 words)
            3. Key points (max 5)
            4. Important entities mentioned
            """)
            
            section_summaries.append(SectionSummary(
                title=self._extract_title(summary),
                page_range=f"{page_start}-{page_end}",
                summary=summary,
                key_points=self._extract_key_points(summary),
                entities=self._extract_entities(summary)
            ))
        
        # Level 2+: Recursive meta-summarization
        current_summaries = [s.summary for s in section_summaries]
        
        for level in range(2, levels + 1):
            print(f"\n🔄 Level {level}: Meta-summarization...")
            
            if len(current_summaries) <= 3:
                break
            
            grouped = self._group_texts(current_summaries, max_group_size=5)
            meta_summaries = []
            
            for group in grouped:
                combined = "\n\n---\n\n".join(group)
                
                meta_summary = self.meta_summarizer.run(f"""
                Synthesize these summaries into a coherent narrative:
                
                {combined}
                
                Preserve key information while eliminating redundancy.
                Target length: {500 // level} words.
                """)
                
                meta_summaries.append(meta_summary)
            
            current_summaries = meta_summaries
        
        # Final executive summary
        print("\n📝 Generating executive summary...")
        
        all_section_content = "\n\n".join(current_summaries)
        
        executive_summary = self.meta_summarizer.run(f"""
        Create an executive summary from these section summaries:
        
        {all_section_content}
        
        The executive summary should:
        1. Capture the main purpose/thesis
        2. Highlight key findings
        3. Note important conclusions
        4. Be suitable for senior executives
        
        Length: {self._get_target_words(target_length)} words
        """)
        
        # Extract themes and recommendations
        themes = self._extract_themes(section_summaries)
        recommendations = self._extract_recommendations(executive_summary, section_summaries)
        
        # Build vector store for Q&A
        print("\n💾 Building search index...")
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
        """Query the summarized document."""
        return self.rlm.run(f"""
        Based on the document, answer: {question}
        
        Provide specific information with page references where possible.
        """)
    
    def _group_chunks(self, chunks, max_group_size: int):
        """Group chunks for section summarization."""
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
        """Group texts for meta-summarization."""
        return [texts[i:i+max_group_size] for i in range(0, len(texts), max_group_size)]
    
    def _extract_title(self, text: str) -> str:
        """Extract section title from summary."""
        if ":" in text[:100]:
            return text[:text.find(":")].strip()
        return text[:50].strip() + "..."
    
    def _extract_key_points(self, text: str) -> List[str]:
        """Extract key points from summary."""
        lines = text.split("\n")
        points = [l.strip("- •*").strip() for l in lines if l.strip().startswith(("-", "•", "*", "1", "2", "3", "4", "5"))]
        return points[:5]
    
    def _extract_entities(self, text: str) -> List[str]:
        """Extract named entities."""
        extractor = RLM.from_openai("gpt-4o-mini")
        result = extractor.run(f"Extract named entities from: {text[:1000]}\nReturn as JSON array.")
        try:
            import json
            return json.loads(result)
        except:
            return []
    
    def _extract_themes(self, sections: List[SectionSummary]) -> List[str]:
        """Extract cross-cutting themes."""
        all_content = "\n".join([s.summary for s in sections])
        
        result = self.meta_summarizer.run(f"""
        Identify the main themes across these sections:
        
        {all_content[:5000]}
        
        Return 5-7 key themes as a list.
        """)
        
        return result.split("\n")[:7]
    
    def _extract_recommendations(self, executive: str, sections: List[SectionSummary]) -> List[str]:
        """Extract or generate recommendations."""
        result = self.meta_summarizer.run(f"""
        Based on this summary, what are the key recommendations or action items?
        
        {executive}
        
        Provide 3-5 concrete recommendations.
        """)
        
        return result.split("\n")[:5]
    
    def _get_target_words(self, length: str) -> int:
        """Get target word count."""
        return {"brief": 300, "standard": 800, "comprehensive": 1500}.get(length, 800)
    
    def _infer_title(self, first_page: str) -> str:
        """Infer document title from first page."""
        result = RLM.from_openai("gpt-4o-mini").run(f"""
        What is the title of this document?
        
        {first_page}
        
        Return only the title.
        """)
        return result.strip()

# Usage
if __name__ == "__main__":
    summarizer = RecursiveDocumentSummarizer()
    
    # Summarize large document
    summary = summarizer.summarize(
        "annual_report_500pages.pdf",
        target_length="comprehensive"
    )
    
    print(f"\n=== {summary.title} ===")
    print(f"Pages: {summary.total_pages}")
    print(f"\n--- Executive Summary ---\n{summary.executive_summary}")
    
    print(f"\n--- Key Themes ---")
    for theme in summary.key_themes:
        print(f"  • {theme}")
    
    print(f"\n--- Sections ({len(summary.section_summaries)}) ---")
    for section in summary.section_summaries[:5]:
        print(f"  📑 {section.title} (pp. {section.page_range})")
    
    # Query the document
    answer = summarizer.query("What were the main financial results?")
    print(f"\n--- Q&A ---\n{answer}")
```

---

*Continued in Part 3: Security & Production Examples...*
