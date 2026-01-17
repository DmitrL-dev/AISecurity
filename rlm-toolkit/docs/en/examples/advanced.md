# Advanced Examples

Enterprise-grade, production-ready examples showcasing RLM-Toolkit's most powerful capabilities.

---

## 1. Autonomous Research Agent

A fully autonomous agent that researches topics, finds sources, analyzes information, and produces comprehensive reports with citations.

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

# Data models
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

# Custom tools
@Tool(name="save_source", description="Save a source for citation")
def save_source(title: str, url: str, snippet: str, relevance: float) -> str:
    return json.dumps({"saved": True, "id": hash(url)})

@Tool(name="write_section", description="Write a report section")
def write_section(heading: str, content: str, source_ids: List[str]) -> str:
    return json.dumps({"section": heading, "words": len(content.split())})

class AutonomousResearchAgent:
    """
    Multi-stage research agent that:
    1. Plans research strategy
    2. Gathers sources from multiple platforms
    3. Analyzes and synthesizes information
    4. Produces structured report with citations
    """
    
    def __init__(self):
        self.memory = HierarchicalMemory(persist_directory="./research_memory")
        
        # Planner agent
        self.planner = RLM.from_openai("gpt-4o")
        self.planner.set_system_prompt("""
        You are a research planner. Given a topic:
        1. Identify key questions to answer
        2. List sources to check (academic, web, news)
        3. Define report structure
        4. Estimate depth needed
        
        Be thorough but focused.
        """)
        
        # Researcher agent
        self.researcher = ReActAgent.from_openai(
            "gpt-4o",
            tools=[
                WebSearchTool(provider="ddg", max_results=10),
                ArxivTool(max_results=5),
                WikipediaTool(),
                save_source
            ],
            system_prompt="""
            You are a meticulous researcher. For each source:
            - Verify credibility
            - Extract key facts
            - Note contradictions
            - Save with relevance score
            
            Aim for diverse, authoritative sources.
            """,
            max_iterations=20
        )
        
        # Analyst agent
        self.analyst = RLM.from_anthropic("claude-3-sonnet")
        self.analyst.set_system_prompt("""
        You are a critical analyst. Given research findings:
        1. Identify patterns and trends
        2. Note contradictions or gaps
        3. Synthesize into coherent narrative
        4. Highlight key insights
        
        Be objective and evidence-based.
        """)
        
        # Writer agent
        self.writer = RLM.from_openai("gpt-4o")
        self.writer.set_system_prompt("""
        You are an expert technical writer. Create:
        - Clear, engaging prose
        - Proper citations [1], [2], etc.
        - Logical flow between sections
        - Executive summary for quick reading
        
        Write for an educated but non-specialist audience.
        """)
        
    def research(self, topic: str, depth: str = "comprehensive") -> ResearchReport:
        """Execute full research pipeline."""
        
        print(f"🔬 Starting research on: {topic}")
        
        # Phase 1: Planning
        print("📋 Phase 1: Planning research strategy...")
        plan = self.planner.run(f"""
        Create a research plan for: {topic}
        Depth: {depth}
        
        Return:
        1. Key questions (5-10)
        2. Source types to check
        3. Report outline
        """)
        
        # Phase 2: Source gathering
        print("🔍 Phase 2: Gathering sources...")
        sources_raw = self.researcher.run(f"""
        Research topic: {topic}
        
        Plan: {plan}
        
        Find and save at least 10 high-quality sources.
        For each source, save with relevance score.
        Cover: academic papers, authoritative websites, recent news.
        """)
        
        # Phase 3: Analysis
        print("🧠 Phase 3: Analyzing findings...")
        analysis = self.analyst.run(f"""
        Topic: {topic}
        
        Research findings:
        {sources_raw}
        
        Provide:
        1. Key themes identified
        2. Main findings per theme
        3. Contradictions or debates
        4. Knowledge gaps
        5. Synthesis of evidence
        """)
        
        # Phase 4: Report writing
        print("✍️ Phase 4: Writing report...")
        report_content = self.writer.run(f"""
        Topic: {topic}
        
        Analysis:
        {analysis}
        
        Sources summary:
        {sources_raw}
        
        Write a comprehensive research report with:
        1. Executive summary (200 words)
        2. Introduction
        3. Main findings (3-5 sections)
        4. Discussion
        5. Conclusions
        6. Properly formatted citations
        """)
        
        # Phase 5: Structured output
        print("📄 Phase 5: Formatting final report...")
        report = self.writer.run_structured(
            f"""
            Convert this report to structured format:
            
            {report_content}
            """,
            output_schema=ResearchReport
        )
        
        report.generated_at = datetime.now().isoformat()
        
        # Save to memory
        self.memory.add_episode(
            f"Research on {topic}",
            metadata={"topic": topic, "depth": depth}
        )
        
        print("✅ Research complete!")
        return report
    
    def save_report(self, report: ResearchReport, path: str):
        """Save report as Markdown."""
        md = f"# {report.title}\n\n"
        md += f"*Generated: {report.generated_at}*\n\n"
        md += f"## Executive Summary\n\n{report.executive_summary}\n\n"
        
        for section in report.sections:
            md += f"## {section.heading}\n\n{section.content}\n\n"
            if section.sources:
                md += f"*Sources: {', '.join(section.sources)}*\n\n"
        
        md += "## Conclusions\n\n"
        for i, conclusion in enumerate(report.conclusions, 1):
            md += f"{i}. {conclusion}\n"
        
        md += "\n## References\n\n"
        for i, source in enumerate(report.sources, 1):
            md += f"[{i}] {source.title}. {source.url}\n"
        
        with open(path, "w", encoding="utf-8") as f:
            f.write(md)

# Usage
if __name__ == "__main__":
    agent = AutonomousResearchAgent()
    
    report = agent.research(
        topic="The impact of large language models on software development practices in 2024",
        depth="comprehensive"
    )
    
    agent.save_report(report, "llm_impact_research.md")
    
    print(f"\nReport: {report.title}")
    print(f"Sections: {len(report.sections)}")
    print(f"Sources: {len(report.sources)}")
```

---

## 2. Multi-Modal RAG Pipeline

A RAG system that handles PDFs, images, audio, and video in a unified pipeline.

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
    Unified RAG pipeline for multiple content types:
    - PDFs with text and images
    - Standalone images (diagrams, charts)
    - Audio files (transcribed)
    - Video files (transcribed + keyframes)
    """
    
    def __init__(self, collection_name: str = "multimodal"):
        # Text embeddings
        self.text_embeddings = OpenAIEmbeddings("text-embedding-3-large")
        
        # Vision-capable LLM for image understanding
        self.vision_llm = RLM.from_openai("gpt-4o")
        
        # Audio transcription
        self.whisper = OpenAI()
        
        # Vector store with multiple collections
        self.text_store = ChromaVectorStore(
            collection_name=f"{collection_name}_text",
            embedding_function=self.text_embeddings
        )
        self.image_store = ChromaVectorStore(
            collection_name=f"{collection_name}_images",
            embedding_function=self.text_embeddings  # Store image descriptions
        )
        
        # Hybrid retriever
        self.retriever = MultiModalRetriever(
            text_store=self.text_store,
            image_store=self.image_store,
            text_weight=0.7,
            image_weight=0.3
        )
        
        # Main QA LLM
        self.qa_llm = RLM.from_openai("gpt-4o")
        self.qa_llm.set_system_prompt("""
        You are a multimodal AI assistant. You can understand and reason about:
        - Text from documents
        - Images and diagrams
        - Transcribed audio/video
        
        Provide comprehensive answers using all available context.
        Reference specific sources when relevant.
        """)
        
    def ingest_pdf(self, path: str) -> int:
        """Ingest PDF with text and embedded images."""
        loader = PDFLoader(path, extract_images=True)
        docs = loader.load()
        
        text_chunks = []
        image_chunks = []
        
        for doc in docs:
            # Split text
            if doc.page_content:
                splitter = RecursiveTextSplitter(chunk_size=1000, chunk_overlap=200)
                text_chunks.extend(splitter.split_documents([doc]))
            
            # Process images
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
        """Ingest standalone image."""
        with open(path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode()
        
        description = self._describe_image(image_data)
        
        self.image_store.add_texts(
            [description],
            metadatas=[{"source": path, "image_data": image_data}]
        )
        
        return 1
    
    def ingest_audio(self, path: str) -> int:
        """Ingest audio file via transcription."""
        with open(path, "rb") as f:
            transcript = self.whisper.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                response_format="verbose_json"
            )
        
        # Split transcript by segments
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
        """Ingest video: transcript + keyframes."""
        chunks_added = 0
        
        # Extract audio and transcribe
        audio_path = self._extract_audio(path)
        chunks_added += self.ingest_audio(audio_path)
        
        # Extract and analyze keyframes
        if extract_frames:
            keyframes = self._extract_keyframes(path, interval=30)  # Every 30 seconds
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
        """Use vision LLM to describe image."""
        return self.vision_llm.run(
            "Describe this image in detail. Include: main subject, text visible, "
            "colors, layout, any data/charts shown. Be comprehensive.",
            images=[image_data]
        )
    
    def _extract_audio(self, video_path: str) -> str:
        """Extract audio from video."""
        import subprocess
        audio_path = video_path.replace(".mp4", ".mp3")
        subprocess.run([
            "ffmpeg", "-i", video_path, "-vn", "-acodec", "mp3", audio_path
        ], capture_output=True)
        return audio_path
    
    def _extract_keyframes(self, video_path: str, interval: int) -> List[tuple]:
        """Extract keyframes at intervals."""
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
        """Query across all modalities."""
        
        # Retrieve from all stores
        text_results = self.text_store.similarity_search(question, k=k)
        
        if include_images:
            image_results = self.image_store.similarity_search(question, k=3)
        else:
            image_results = []
        
        # Combine context
        context = "## Text Context:\n"
        for doc in text_results:
            context += f"- {doc.page_content}\n"
            context += f"  Source: {doc.metadata.get('source', 'unknown')}\n\n"
        
        if image_results:
            context += "\n## Image Context:\n"
            for doc in image_results:
                context += f"- [Image] {doc.page_content}\n"
        
        # Generate answer
        answer = self.qa_llm.run(f"""
        Question: {question}
        
        Context:
        {context}
        
        Provide a comprehensive answer using the available context.
        Reference specific sources and describe relevant images.
        """)
        
        return {
            "answer": answer,
            "text_sources": [d.metadata.get("source") for d in text_results],
            "image_sources": [d.metadata.get("source") for d in image_results]
        }

# Usage
if __name__ == "__main__":
    rag = MultiModalRAG("company_docs")
    
    # Ingest various content
    rag.ingest_pdf("quarterly_report.pdf")
    rag.ingest_image("architecture_diagram.png")
    rag.ingest_audio("earnings_call.mp3")
    rag.ingest_video("product_demo.mp4")
    
    # Query across all modalities
    result = rag.query("What was the Q3 revenue and how does the architecture support scaling?")
    print(result["answer"])
```

---

## 3. Code Review Agent

An agent that analyzes pull requests, identifies bugs, suggests improvements, and generates tests.

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

# Tools for code analysis
@Tool(name="read_file", description="Read a file from the repository")
def read_file(file_path: str) -> str:
    try:
        with open(file_path, "r") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"

@Tool(name="get_diff", description="Get git diff for a file")
def get_diff(file_path: str) -> str:
    result = subprocess.run(
        ["git", "diff", "HEAD~1", file_path],
        capture_output=True,
        text=True
    )
    return result.stdout or "No changes"

@Tool(name="run_linter", description="Run linter on file")
def run_linter(file_path: str) -> str:
    result = subprocess.run(
        ["ruff", "check", file_path, "--output-format=json"],
        capture_output=True,
        text=True
    )
    return result.stdout

@Tool(name="check_types", description="Run type checker")
def check_types(file_path: str) -> str:
    result = subprocess.run(
        ["mypy", file_path, "--output=json"],
        capture_output=True,
        text=True
    )
    return result.stdout or result.stderr

@Tool(name="run_tests", description="Run tests for a module")
def run_tests(module_path: str) -> str:
    result = subprocess.run(
        ["pytest", module_path, "-v", "--tb=short"],
        capture_output=True,
        text=True
    )
    return result.stdout + result.stderr

@Tool(name="analyze_complexity", description="Analyze code complexity")
def analyze_complexity(file_path: str) -> str:
    result = subprocess.run(
        ["radon", "cc", file_path, "-j"],
        capture_output=True,
        text=True
    )
    return result.stdout

class CodeReviewAgent:
    """
    Comprehensive code review agent that:
    1. Analyzes code changes
    2. Identifies bugs, security issues, performance problems
    3. Checks code style and maintainability
    4. Suggests improvements and refactoring
    5. Generates test cases for new code
    """
    
    def __init__(self):
        # Main review agent
        self.reviewer = ReActAgent.from_openai(
            "gpt-4o",
            tools=[read_file, get_diff, run_linter, check_types, run_tests, analyze_complexity],
            system_prompt="""
            You are an expert code reviewer with deep knowledge of:
            - Software design patterns and best practices
            - Security vulnerabilities (OWASP Top 10)
            - Performance optimization
            - Clean code principles
            - Testing strategies
            
            For each file, systematically:
            1. Read the full file content
            2. Get the diff to see changes
            3. Run linter and type checker
            4. Analyze complexity
            5. Identify issues by category
            
            Be thorough but constructive. Focus on actionable feedback.
            """,
            max_iterations=30
        )
        
        # Security specialist
        self.security_agent = RLM.from_anthropic("claude-3-sonnet")
        self.security_agent.set_system_prompt("""
        You are a security expert. Analyze code for:
        - SQL injection
        - XSS vulnerabilities
        - Authentication/authorization flaws
        - Insecure deserialization
        - Sensitive data exposure
        - SSRF vulnerabilities
        - Path traversal
        - Command injection
        
        Report ONLY confirmed security issues with severity and fix.
        """)
        
        # Test generator
        self.test_generator = RLM.from_openai("gpt-4o")
        self.test_generator.set_system_prompt("""
        You are a test engineer. Given code:
        1. Identify testable units (functions, classes, methods)
        2. Generate comprehensive test cases covering:
           - Happy path
           - Edge cases
           - Error handling
           - Boundary conditions
        3. Use pytest style with descriptive names
        4. Include fixtures and mocks where needed
        """)
        
    def review_pr(self, files: List[str]) -> ReviewResult:
        """Review a pull request."""
        all_issues = []
        
        # Phase 1: Initial analysis with tools
        print("🔍 Phase 1: Analyzing code changes...")
        for file in files:
            analysis = self.reviewer.run(f"""
            Review the file: {file}
            
            Steps:
            1. Read the file
            2. Get the diff
            3. Run linter
            4. Check types
            5. Analyze complexity
            
            Report all issues found with file, line, severity, and suggestion.
            """)
            
            # Parse issues from analysis
            issues = self._parse_issues(analysis, file)
            all_issues.extend(issues)
        
        # Phase 2: Security review
        print("🔐 Phase 2: Security analysis...")
        for file in files:
            if file.endswith(".py"):
                with open(file, "r") as f:
                    code = f.read()
                
                security_issues = self.security_agent.run(f"""
                Analyze this code for security vulnerabilities:
                
                ```python
                {code}
                ```
                
                Report each issue with line number and severity.
                """)
                
                issues = self._parse_security_issues(security_issues, file)
                all_issues.extend(issues)
        
        # Phase 3: Generate tests
        print("🧪 Phase 3: Generating test suggestions...")
        test_suggestions = []
        for file in files:
            if file.endswith(".py") and not file.startswith("test_"):
                with open(file, "r") as f:
                    code = f.read()
                
                tests = self.test_generator.run(f"""
                Generate pytest test cases for:
                
                ```python
                {code}
                ```
                
                Focus on new or changed functions.
                """)
                test_suggestions.append(tests)
        
        # Phase 4: Synthesis
        print("📝 Phase 4: Preparing review summary...")
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
        """Parse issues from analysis text."""
        # Use LLM to extract structured issues
        extractor = RLM.from_openai("gpt-4o-mini")
        issues_json = extractor.run(f"""
        Extract code issues from this analysis as JSON list:
        
        {analysis}
        
        Format: [{{"file": str, "line": int, "severity": str, "category": str, "description": str, "suggestion": str}}]
        """)
        
        try:
            issues_data = json.loads(issues_json)
            return [CodeIssue(**issue) for issue in issues_data]
        except:
            return []
    
    def _parse_security_issues(self, analysis: str, file: str) -> List[CodeIssue]:
        """Parse security-specific issues."""
        issues = self._parse_issues(analysis, file)
        for issue in issues:
            issue.category = "security"
        return issues
    
    def _generate_summary(self, issues: List[CodeIssue]) -> str:
        """Generate review summary."""
        critical = len([i for i in issues if i.severity == Severity.CRITICAL])
        high = len([i for i in issues if i.severity == Severity.HIGH])
        medium = len([i for i in issues if i.severity == Severity.MEDIUM])
        low = len([i for i in issues if i.severity == Severity.LOW])
        
        return f"""
        ## Code Review Summary
        
        **Total Issues Found:** {len(issues)}
        - 🔴 Critical: {critical}
        - 🟠 High: {high}
        - 🟡 Medium: {medium}
        - 🟢 Low: {low}
        
        **Categories:**
        - Security: {len([i for i in issues if i.category == 'security'])}
        - Bugs: {len([i for i in issues if i.category == 'bug'])}
        - Performance: {len([i for i in issues if i.category == 'performance'])}
        - Style: {len([i for i in issues if i.category == 'style'])}
        """
    
    def _get_recommendation(self, issues: List[CodeIssue]) -> str:
        """Determine approval recommendation."""
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
        """Suggest refactoring improvements."""
        suggestions = []
        
        for file in files:
            with open(file, "r") as f:
                code = f.read()
            
            refactoring = RLM.from_openai("gpt-4o").run(f"""
            Suggest refactoring improvements for:
            
            ```python
            {code}
            ```
            
            Focus on:
            - Extract method opportunities
            - Class decomposition
            - Design pattern applications
            - DRY violations
            
            Provide specific, actionable suggestions.
            """)
            suggestions.append(f"## {file}\n{refactoring}")
        
        return suggestions

# Usage
if __name__ == "__main__":
    agent = CodeReviewAgent()
    
    # Review changed files
    files = [
        "src/api/handlers.py",
        "src/services/user_service.py",
        "src/utils/validators.py"
    ]
    
    result = agent.review_pr(files)
    
    print(result.summary)
    print(f"\nRecommendation: {result.approval_recommendation}")
    
    for issue in result.issues:
        print(f"\n[{issue.severity}] {issue.file}:{issue.line}")
        print(f"  {issue.description}")
        print(f"  Suggestion: {issue.suggestion}")
```

---

## 4. Legal Document Analyzer

Enterprise legal AI for contract analysis, risk identification, and amendment generation.

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
    role: str  # buyer, seller, licensor, licensee, etc.
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
    Enterprise legal document analyzer that:
    1. Extracts and categorizes clauses
    2. Identifies risks and non-standard terms
    3. Compares against best practices
    4. Generates suggested amendments
    5. Produces negotiation strategies
    """
    
    def __init__(self):
        # Main legal analyst
        self.analyst = RLM.from_anthropic("claude-3-opus")
        self.analyst.set_system_prompt("""
        You are an expert corporate attorney with 20+ years of experience in:
        - M&A transactions
        - Commercial contracts
        - Technology licensing
        - Employment agreements
        
        Analyze contracts with extreme precision. Identify:
        - Non-standard or unusual terms
        - Hidden risks and liabilities
        - One-sided provisions
        - Missing standard protections
        
        Always cite specific contract language.
        """)
        
        # Risk assessment specialist
        self.risk_assessor = RLM.from_openai("gpt-4o")
        self.risk_assessor.set_system_prompt("""
        You are a legal risk analyst. Evaluate clauses for:
        - Financial exposure
        - Operational constraints
        - Regulatory compliance risks
        - Reputational risks
        - Enforceability concerns
        
        Quantify risks where possible.
        """)
        
        # Amendment drafter
        self.drafter = RLM.from_anthropic("claude-3-sonnet")
        self.drafter.set_system_prompt("""
        You are a senior contract drafter. Create amendments that:
        - Use precise legal language
        - Are enforceable in the governing jurisdiction
        - Balance fairness between parties
        - Follow industry standard formats
        
        Provide clear rationale for each change.
        """)
        
        # Best practices database
        self.embeddings = OpenAIEmbeddings("text-embedding-3-large")
        self.best_practices_store = ChromaVectorStore(
            collection_name="legal_best_practices",
            embedding_function=self.embeddings
        )
        
    def analyze_contract(self, pdf_path: str) -> ContractAnalysis:
        """Full contract analysis."""
        
        # Load and parse
        print("📄 Loading contract...")
        docs = PDFLoader(pdf_path).load()
        full_text = "\n\n".join([d.page_content for d in docs])
        
        # Extract basic info
        print("📋 Extracting contract details...")
        basic_info = self.analyst.run(f"""
        Extract from this contract:
        1. Document title/type
        2. All parties with their roles
        3. Effective date
        4. Term/duration
        5. Total contract value (if stated)
        
        Contract:
        {full_text[:30000]}
        """)
        
        # Identify and analyze clauses
        print("🔍 Analyzing clauses...")
        clauses = self._analyze_clauses(full_text)
        
        # Risk assessment
        print("⚠️ Assessing risks...")
        for clause in clauses:
            clause.risk_level = self._assess_clause_risk(clause)
        
        # Check for missing clauses
        print("📝 Checking completeness...")
        missing = self._check_missing_clauses(clauses)
        
        # Generate negotiation points
        print("🎯 Identifying negotiation points...")
        negotiation_points = self._generate_negotiation_points(clauses)
        
        # Calculate overall risk
        overall_risk = self._calculate_overall_risk(clauses)
        
        return ContractAnalysis(
            title=self._extract_title(basic_info),
            parties=self._extract_parties(basic_info),
            effective_date=self._extract_field(basic_info, "effective date"),
            term=self._extract_field(basic_info, "term"),
            total_value=self._extract_field(basic_info, "value"),
            clauses=clauses,
            overall_risk=overall_risk,
            negotiation_points=negotiation_points,
            missing_clauses=missing
        )
    
    def _analyze_clauses(self, text: str) -> List[Clause]:
        """Extract and analyze each clause type."""
        clauses = []
        
        for clause_type in ClauseType:
            clause_analysis = self.analyst.run(f"""
            Find and analyze the {clause_type.value} clause in this contract.
            
            If found, provide:
            1. Exact text of the clause
            2. Page number (estimate based on position)
            3. Whether it follows industry standards
            4. Specific concerns or unusual terms
            5. Analysis of implications
            
            If not found, state "NOT FOUND".
            
            Contract:
            {text[:40000]}
            """)
            
            if "NOT FOUND" not in clause_analysis.upper():
                clause = self._parse_clause(clause_analysis, clause_type)
                if clause:
                    clauses.append(clause)
        
        return clauses
    
    def _assess_clause_risk(self, clause: Clause) -> RiskLevel:
        """Assess risk level of a clause."""
        assessment = self.risk_assessor.run(f"""
        Assess the risk level of this {clause.type.value} clause:
        
        "{clause.text}"
        
        Consider:
        - Financial exposure
        - One-sidedness
        - Enforceability
        - Industry norms
        
        Rate as: CRITICAL, HIGH, MEDIUM, or LOW
        Explain briefly.
        """)
        
        if "CRITICAL" in assessment.upper():
            return RiskLevel.CRITICAL
        elif "HIGH" in assessment.upper():
            return RiskLevel.HIGH
        elif "MEDIUM" in assessment.upper():
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _check_missing_clauses(self, clauses: List[Clause]) -> List[str]:
        """Check for important missing clauses."""
        found_types = {c.type for c in clauses}
        standard_clauses = {
            ClauseType.INDEMNIFICATION: "Standard for commercial contracts",
            ClauseType.LIABILITY: "Critical for risk management",
            ClauseType.TERMINATION: "Essential for exit strategy",
            ClauseType.CONFIDENTIALITY: "Important for IP protection",
            ClauseType.DISPUTE: "Needed for conflict resolution",
            ClauseType.GOVERNING_LAW: "Required for enforceability"
        }
        
        missing = []
        for clause_type, importance in standard_clauses.items():
            if clause_type not in found_types:
                missing.append(f"{clause_type.value}: {importance}")
        
        return missing
    
    def _generate_negotiation_points(self, clauses: List[Clause]) -> List[str]:
        """Generate key negotiation points."""
        high_risk = [c for c in clauses if c.risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH]]
        
        if not high_risk:
            return ["Contract appears balanced. Minor optimization possible."]
        
        points = []
        for clause in high_risk:
            point = self.analyst.run(f"""
            Suggest a negotiation approach for this {clause.risk_level.value} risk clause:
            
            "{clause.text}"
            
            Concerns: {clause.concerns}
            
            Provide:
            1. Opening position
            2. Acceptable middle ground
            3. Walk-away point
            """)
            points.append(f"**{clause.type.value}**: {point}")
        
        return points
    
    def generate_amendments(self, analysis: ContractAnalysis) -> List[Amendment]:
        """Generate suggested amendments for high-risk clauses."""
        amendments = []
        
        high_risk_clauses = [
            c for c in analysis.clauses 
            if c.risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH]
        ]
        
        for clause in high_risk_clauses:
            amendment = self.drafter.run(f"""
            Draft a revised version of this {clause.type.value} clause:
            
            ORIGINAL:
            "{clause.text}"
            
            CONCERNS:
            {clause.concerns}
            
            Create a balanced revision that:
            1. Addresses the identified concerns
            2. Remains commercially reasonable
            3. Uses standard legal language
            
            Provide the proposed text and rationale.
            """)
            
            amendments.append(Amendment(
                clause_type=clause.type,
                original_text=clause.text,
                proposed_text=self._extract_proposed_text(amendment),
                rationale=self._extract_rationale(amendment),
                risk_reduction=f"Reduces risk from {clause.risk_level.value} to lower level"
            ))
        
        return amendments
    
    def compare_contracts(self, path1: str, path2: str) -> str:
        """Compare two contracts and highlight differences."""
        analysis1 = self.analyze_contract(path1)
        analysis2 = self.analyze_contract(path2)
        
        comparison = self.analyst.run(f"""
        Compare these two contracts:
        
        CONTRACT 1:
        Parties: {analysis1.parties}
        Key terms: {[c.type.value for c in analysis1.clauses]}
        Risk level: {analysis1.overall_risk}
        
        CONTRACT 2:
        Parties: {analysis2.parties}
        Key terms: {[c.type.value for c in analysis2.clauses]}
        Risk level: {analysis2.overall_risk}
        
        Highlight:
        1. Key differences in terms
        2. Which is more favorable (and to whom)
        3. Specific clause variations
        4. Missing protections in each
        """)
        
        return comparison
    
    def _calculate_overall_risk(self, clauses: List[Clause]) -> RiskLevel:
        """Calculate overall contract risk."""
        if any(c.risk_level == RiskLevel.CRITICAL for c in clauses):
            return RiskLevel.CRITICAL
        
        high_count = len([c for c in clauses if c.risk_level == RiskLevel.HIGH])
        if high_count >= 3:
            return RiskLevel.HIGH
        elif high_count >= 1:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

# Usage
if __name__ == "__main__":
    analyzer = LegalDocumentAnalyzer()
    
    # Analyze contract
    analysis = analyzer.analyze_contract("vendor_agreement.pdf")
    
    print(f"Contract: {analysis.title}")
    print(f"Overall Risk: {analysis.overall_risk}")
    print(f"\nParties:")
    for party in analysis.parties:
        print(f"  - {party.name} ({party.role})")
    
    print(f"\nHigh-Risk Clauses:")
    for clause in analysis.clauses:
        if clause.risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH]:
            print(f"  [{clause.risk_level}] {clause.type.value}")
            print(f"    Concerns: {clause.concerns}")
    
    # Generate amendments
    amendments = analyzer.generate_amendments(analysis)
    print(f"\nSuggested Amendments: {len(amendments)}")
```

---

## 5. Real-time Trading Assistant

Financial AI for market analysis, news processing, and signal generation.

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
    indicators: Dict[str, str]  # RSI, MACD, etc.

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

# Market data tools (simulated - use real APIs in production)
@Tool(name="get_price", description="Get current price for a symbol")
def get_price(symbol: str) -> str:
    # In production, use real API (Alpha Vantage, Yahoo Finance, etc.)
    import random
    price = random.uniform(100, 500)
    return json.dumps({"symbol": symbol, "price": round(price, 2), "change": round(random.uniform(-5, 5), 2)})

@Tool(name="get_technicals", description="Get technical indicators")
def get_technicals(symbol: str) -> str:
    import random
    return json.dumps({
        "rsi": random.randint(20, 80),
        "macd": {"value": random.uniform(-5, 5), "signal": random.uniform(-5, 5)},
        "sma_20": random.uniform(100, 500),
        "sma_50": random.uniform(100, 500),
        "bollinger": {"upper": 520, "middle": 500, "lower": 480}
    })

@Tool(name="get_fundamentals", description="Get fundamental data")
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

@Tool(name="get_news", description="Get recent news for symbol")
def get_news(symbol: str, days: int = 7) -> str:
    # In production, use news API
    return json.dumps([
        {"title": f"{symbol} announces new product launch", "sentiment": "positive", "date": "2024-01-15"},
        {"title": f"Analyst upgrades {symbol} to buy", "sentiment": "positive", "date": "2024-01-14"},
        {"title": f"Sector faces headwinds", "sentiment": "negative", "date": "2024-01-13"}
    ])

@Tool(name="get_earnings", description="Get earnings data")
def get_earnings(symbol: str) -> str:
    import random
    return json.dumps({
        "next_earnings": "2024-02-15",
        "last_eps": round(random.uniform(1, 10), 2),
        "eps_estimate": round(random.uniform(1, 10), 2),
        "history": [
            {"quarter": "Q3", "eps": 2.5, "estimate": 2.3, "surprise": 8.7},
            {"quarter": "Q2", "eps": 2.1, "estimate": 2.0, "surprise": 5.0}
        ]
    })

class TradingAssistant:
    """
    Real-time trading assistant that:
    1. Analyzes market conditions
    2. Processes news and sentiment
    3. Performs technical analysis
    4. Evaluates fundamentals
    5. Generates trade signals with risk management
    """
    
    def __init__(self):
        self.memory = HierarchicalMemory(persist_directory="./trading_memory")
        
        # Market analyst
        self.market_analyst = ReActAgent.from_openai(
            "gpt-4o",
            tools=[get_price, get_technicals, get_news],
            system_prompt="""
            You are a professional market analyst. Analyze:
            - Price action and volume
            - Technical indicators (RSI, MACD, Moving Averages)
            - Chart patterns
            - Market sentiment from news
            
            Be objective and data-driven. Avoid emotional bias.
            """,
            max_iterations=10
        )
        
        # Fundamental analyst
        self.fundamental_analyst = ReActAgent.from_openai(
            "gpt-4o",
            tools=[get_fundamentals, get_earnings],
            system_prompt="""
            You are a fundamental analyst. Evaluate:
            - Valuation metrics (P/E, PEG, P/B)
            - Financial health (debt levels, cash flow)
            - Growth trajectory
            - Competitive position
            
            Focus on intrinsic value and long-term prospects.
            """,
            max_iterations=10
        )
        
        # News sentiment analyzer
        self.sentiment_analyzer = RLM.from_anthropic("claude-3-sonnet")
        self.sentiment_analyzer.set_system_prompt("""
        You are a financial news analyst. Evaluate news for:
        - Market impact (high, medium, low)
        - Sentiment (bullish, bearish, neutral)
        - Time horizon of impact
        - Reliability of source
        
        Be skeptical of hype and focus on material information.
        """)
        
        # Trade strategist
        self.strategist = RLM.from_openai("gpt-4o")
        self.strategist.set_system_prompt("""
        You are a professional trader and risk manager. Create trade ideas with:
        - Clear entry and exit criteria
        - Defined stop loss and take profit levels
        - Risk/reward analysis
        - Position sizing recommendations
        
        Always prioritize capital preservation. Never suggest all-in positions.
        """)
        
    async def analyze_symbol(self, symbol: str) -> TradeIdea:
        """Complete analysis for a symbol."""
        
        print(f"📊 Analyzing {symbol}...")
        
        # Run analyses in parallel
        technical_task = asyncio.create_task(self._get_technical_analysis(symbol))
        fundamental_task = asyncio.create_task(self._get_fundamental_analysis(symbol))
        sentiment_task = asyncio.create_task(self._get_sentiment(symbol))
        
        technical = await technical_task
        fundamental = await fundamental_task
        sentiment = await sentiment_task
        
        # Generate trade idea
        trade_idea = self._generate_trade_idea(symbol, technical, fundamental, sentiment)
        
        # Store in memory
        self.memory.add_episode(
            f"Analysis of {symbol}: {trade_idea.signal.value}",
            metadata={"symbol": symbol, "signal": trade_idea.signal.value}
        )
        
        return trade_idea
    
    async def _get_technical_analysis(self, symbol: str) -> TechnicalAnalysis:
        """Get technical analysis."""
        analysis = self.market_analyst.run(f"""
        Perform technical analysis on {symbol}:
        1. Get current price
        2. Get technical indicators
        3. Identify trend and key levels
        4. Determine signal based on technicals
        """)
        
        # Parse into structured format
        return self._parse_technical(analysis)
    
    async def _get_fundamental_analysis(self, symbol: str) -> FundamentalAnalysis:
        """Get fundamental analysis."""
        analysis = self.fundamental_analyst.run(f"""
        Perform fundamental analysis on {symbol}:
        1. Get fundamental metrics
        2. Get earnings data
        3. Evaluate valuation
        4. Assess financial health
        """)
        
        return self._parse_fundamental(analysis)
    
    async def _get_sentiment(self, symbol: str) -> MarketSentiment:
        """Analyze market sentiment."""
        news = get_news(symbol)
        
        sentiment = self.sentiment_analyzer.run(f"""
        Analyze sentiment for {symbol} based on recent news:
        
        {news}
        
        Provide:
        1. Overall sentiment (bullish/bearish/neutral)
        2. Confidence level (0-1)
        3. Key factors driving sentiment
        4. Expected impact on price
        """)
        
        return self._parse_sentiment(sentiment)
    
    def _generate_trade_idea(
        self,
        symbol: str,
        technical: TechnicalAnalysis,
        fundamental: FundamentalAnalysis,
        sentiment: MarketSentiment
    ) -> TradeIdea:
        """Generate trade idea from all analyses."""
        
        idea = self.strategist.run(f"""
        Generate a trade idea for {symbol}:
        
        TECHNICAL ANALYSIS:
        - Trend: {technical.trend}
        - Indicators: {technical.indicators}
        - Support: {technical.support_levels}
        - Resistance: {technical.resistance_levels}
        
        FUNDAMENTAL ANALYSIS:
        - Valuation: {fundamental.valuation}
        - Health: {fundamental.financial_health}
        - Growth: {fundamental.growth_prospects}
        
        SENTIMENT:
        - Overall: {sentiment.overall}
        - Confidence: {sentiment.confidence}
        - Factors: {sentiment.key_factors}
        
        Create a trade idea with:
        1. Signal (strong_buy/buy/hold/sell/strong_sell)
        2. Timeframe (intraday/swing/position)
        3. Entry price
        4. Stop loss
        5. Take profit targets (3 levels)
        6. Risk/reward ratio
        7. Confidence level
        8. Rationale
        9. Catalysts to watch
        10. Key risks
        """)
        
        return self._parse_trade_idea(idea, symbol)
    
    def screen_market(self, symbols: List[str]) -> List[TradeIdea]:
        """Screen multiple symbols and return best ideas."""
        ideas = []
        
        for symbol in symbols:
            try:
                idea = asyncio.run(self.analyze_symbol(symbol))
                if idea.signal in [Signal.STRONG_BUY, Signal.STRONG_SELL]:
                    ideas.append(idea)
            except Exception as e:
                print(f"Error analyzing {symbol}: {e}")
        
        # Sort by confidence
        ideas.sort(key=lambda x: x.confidence, reverse=True)
        
        return ideas[:10]  # Top 10 ideas
    
    def _parse_technical(self, analysis: str) -> TechnicalAnalysis:
        # Simplified parsing - use structured output in production
        return TechnicalAnalysis(
            trend="uptrend",
            support_levels=[450, 440, 430],
            resistance_levels=[460, 470, 480],
            indicators={"RSI": "55 (neutral)", "MACD": "bullish crossover"}
        )
    
    def _parse_fundamental(self, analysis: str) -> FundamentalAnalysis:
        return FundamentalAnalysis(
            valuation="fair",
            financial_health="strong",
            growth_prospects="positive",
            key_metrics={"PE": 25, "PEG": 1.5, "ROE": 18}
        )
    
    def _parse_sentiment(self, analysis: str) -> MarketSentiment:
        return MarketSentiment(
            overall="bullish",
            confidence=0.75,
            key_factors=["product launch", "analyst upgrade"],
            news_impact="moderately positive"
        )
    
    def _parse_trade_idea(self, idea: str, symbol: str) -> TradeIdea:
        # In production, use structured output
        return TradeIdea(
            symbol=symbol,
            signal=Signal.BUY,
            timeframe=TimeFrame.SWING,
            entry_price=455.0,
            stop_loss=440.0,
            take_profit=[470.0, 485.0, 500.0],
            risk_reward=2.5,
            confidence=0.72,
            rationale="Bullish technicals with positive sentiment catalyst",
            catalysts=["Earnings report", "Product launch"],
            risks=["Sector rotation", "Market volatility"]
        )

# Usage
if __name__ == "__main__":
    assistant = TradingAssistant()
    
    # Analyze single symbol
    idea = asyncio.run(assistant.analyze_symbol("AAPL"))
    print(f"\n{idea.symbol}: {idea.signal.value}")
    print(f"Entry: ${idea.entry_price} | Stop: ${idea.stop_loss}")
    print(f"Targets: {idea.take_profit}")
    print(f"R/R: {idea.risk_reward} | Confidence: {idea.confidence}")
    print(f"Rationale: {idea.rationale}")
    
    # Screen market
    watchlist = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META"]
    top_ideas = assistant.screen_market(watchlist)
    
    print("\n=== Top Trade Ideas ===")
    for idea in top_ideas:
        print(f"{idea.symbol}: {idea.signal.value} (conf: {idea.confidence})")
```

---

*Continued in Part 2...*
