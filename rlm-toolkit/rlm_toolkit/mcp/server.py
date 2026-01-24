"""
RLM-Toolkit MCP Server.

Main entry point for the MCP server. Implements tools for:
- rlm_load_context: Load file or directory into context
- rlm_query: Search in loaded context
- rlm_list_contexts: List all loaded contexts
- rlm_analyze: Deep analysis through C³ crystals
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# MCP SDK imports (will need to be installed)
try:
    # FastMCP is the recommended API for MCP SDK 1.25+
    from mcp.server.fastmcp import FastMCP
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    FastMCP = None

from .contexts import ContextManager
from .providers import ProviderRouter

# Crystal imports for C³ integration
from ..crystal import HPEExtractor, CrystalIndexer, ProjectCrystal, ModuleCrystal

# H-MEM imports for memory integration
from ..memory.hierarchical import HierarchicalMemory, HMEMConfig, MemoryLevel
from ..memory.secure import SecureHierarchicalMemory, SecurityPolicy

# Memory Bridge imports for bi-temporal cognitive state
from ..memory_bridge import (
    MemoryBridgeManager,
    StateStorage,
    register_memory_bridge_tools,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("rlm_mcp")


class RLMServer:
    """RLM MCP Server implementation with C³ and H-MEM integration."""

    def __init__(self):
        self.context_manager = ContextManager()
        self.provider_router = ProviderRouter()

        # C³ Crystal components
        self.extractor = HPEExtractor()
        self.indexer = CrystalIndexer()
        self.project_crystal: Optional[ProjectCrystal] = None

        # Session stats for real-time savings tracking
        self.session_stats = {
            "queries": 0,
            "tokens_served": 0,
            "tokens_saved": 0,
            "raw_context_size": 0,
            "session_start": None,
        }

        # Rate limiting for reindex (T5.4: max 1 per 60s)
        self._last_reindex_time = 0
        self._reindex_rate_limit_seconds = 60

        # H-MEM Secure Memory component (encryption enabled by default)
        memory_file = self.context_manager.storage_dir / "memory" / "hmem.json"
        memory_file.parent.mkdir(parents=True, exist_ok=True)

        # Use SecureHierarchicalMemory by default (per Council decision)
        use_secure = os.getenv("RLM_SECURE_MEMORY", "true").lower() != "false"

        if use_secure:
            import secrets

            encryption_key = os.getenv("RLM_ENCRYPTION_KEY")
            if not encryption_key:
                # Generate key if not provided (store in .rlm/)
                key_file = self.context_manager.storage_dir / ".encryption_key"
                if key_file.exists():
                    encryption_key = key_file.read_bytes()
                else:
                    encryption_key = secrets.token_bytes(32)
                    key_file.write_bytes(encryption_key)
            elif isinstance(encryption_key, str):
                encryption_key = encryption_key.encode()[:32].ljust(32, b"\0")

            self.memory = SecureHierarchicalMemory(
                agent_id="mcp_server",
                trust_zone="default",
                security_policy=SecurityPolicy(encrypt_at_rest=True),
                encryption_key=encryption_key,
                config=HMEMConfig(auto_persist=True),
            )
            logger.info("SecureHierarchicalMemory enabled with encryption")
        else:
            self.memory = HierarchicalMemory(
                HMEMConfig(
                    persistence_path=str(memory_file) if memory_file.exists() else None,
                    auto_persist=True,
                )
            )
            logger.warning("Using non-secure memory (RLM_SECURE_MEMORY=false)")

        # Initialize Memory Bridge (bi-temporal cognitive state)
        memory_bridge_db = (
            self.context_manager.storage_dir / "memory" / "memory_bridge.db"
        )
        memory_bridge_storage = StateStorage(db_path=memory_bridge_db)
        self.memory_bridge = MemoryBridgeManager(storage=memory_bridge_storage)
        logger.info(f"Memory Bridge initialized at {memory_bridge_db}")

        # Initialize Memory Bridge v2.0 (enterprise hierarchical memory)
        from ..memory_bridge.v2.hierarchical import HierarchicalMemoryStore
        from ..memory_bridge.mcp_tools_v2 import register_memory_bridge_v2_tools

        memory_bridge_v2_db = (
            self.context_manager.storage_dir / "memory" / "memory_bridge_v2.db"
        )
        self.memory_bridge_v2_store = HierarchicalMemoryStore(
            db_path=memory_bridge_v2_db
        )
        logger.info(f"Memory Bridge v2.0 initialized at {memory_bridge_v2_db}")

        # Initialize default embedder for auto-embedding (v2.1 fix)
        try:
            from sentence_transformers import SentenceTransformer

            embedder = SentenceTransformer("all-MiniLM-L6-v2")
            self.memory_bridge_v2_store.set_embedder(embedder)
            logger.info("Default embedder (all-MiniLM-L6-v2) initialized")
        except ImportError:
            logger.warning(
                "sentence-transformers not installed. "
                "Auto-embedding disabled. Install: pip install sentence-transformers"
            )

        if MCP_AVAILABLE:
            self.mcp = FastMCP("rlm-toolkit")
            self._register_tools()
            # Register Memory Bridge v1 tools (10 tools)
            register_memory_bridge_tools(self.mcp, self.memory_bridge)
            logger.info("Memory Bridge v1 tools registered")

            # Register Memory Bridge v2 tools (15 tools for enterprise features)
            project_root = Path(os.getenv("RLM_PROJECT_ROOT", os.getcwd()))
            self.memory_bridge_v2_components = register_memory_bridge_v2_tools(
                self.mcp,
                self.memory_bridge_v2_store,
                project_root=project_root,
            )
            logger.info("Memory Bridge v2.0 enterprise tools registered")

            # Start background processors (v2.3)
            self._start_background_processors(project_root)
        else:
            self.mcp = None
            logger.warning("MCP SDK not installed. Run: pip install mcp")

    def _start_background_processors(self, project_root: Path):
        """Start background processors for TTL and FileWatcher."""
        import asyncio

        # Get TTL manager from v2 components
        ttl_manager = self.memory_bridge_v2_components.get("ttl_manager")
        if ttl_manager:
            # Start FileWatcher
            try:
                ttl_manager.start_file_watcher()
                logger.info("FileWatcher started")
            except Exception as e:
                logger.warning(f"FileWatcher not started: {e}")

            # Schedule TTL processor (every 6 hours)
            async def ttl_processor_loop():
                while True:
                    await asyncio.sleep(6 * 3600)  # 6 hours
                    try:
                        report = ttl_manager.process_expired()
                        logger.info(f"TTL auto-process: {report.to_dict()}")
                    except Exception as e:
                        logger.error(f"TTL auto-process error: {e}")

            try:
                loop = asyncio.get_event_loop()
                loop.create_task(ttl_processor_loop())
                logger.info("TTL auto-processor scheduled (6h interval)")
            except RuntimeError:
                logger.warning("No event loop for TTL scheduler")

    def _persist_session_stats(self):
        """Persist session stats to SQLite for Dashboard access."""
        try:
            from .contexts import ContextManager
            from ..storage import get_storage
            from pathlib import Path
            import os

            project_root = os.getenv("RLM_PROJECT_ROOT", os.getcwd())
            storage = get_storage(Path(project_root))
            storage.set_metadata("session_stats", self.session_stats)
        except Exception as e:
            logger.debug(f"Could not persist session stats: {e}")

    def _register_tools(self):
        """Register all MCP tools."""

        @self.mcp.tool("rlm_load_context")
        async def load_context(path: str, name: Optional[str] = None) -> Dict[str, Any]:
            """
            Load a file or directory into context.

            Args:
                path: Path to file or directory
                name: Optional name for the context (defaults to filename)

            Returns:
                Context metadata (name, size, token_count)
            """
            try:
                result = await self.context_manager.load(path, name)
                logger.info(
                    f"Loaded context: {result['name']} ({result['token_count']} tokens)"
                )
                return {"success": True, "context": result}
            except Exception as e:
                logger.error(f"Failed to load context: {e}")
                return {"success": False, "error": str(e)}

        @self.mcp.tool("rlm_query")
        async def query(
            question: str, context_name: Optional[str] = None
        ) -> Dict[str, Any]:
            """
            Search in loaded context.

            Args:
                question: The question to answer
                context_name: Optional context name (uses default if not specified)

            Returns:
                Relevant chunks and answer
            """
            try:
                import time

                # Initialize session if needed
                if self.session_stats["session_start"] is None:
                    self.session_stats["session_start"] = time.time()

                # Get context
                context = self.context_manager.get(context_name)
                if not context:
                    return {
                        "success": False,
                        "error": f"Context '{context_name}' not found",
                    }

                # Calculate raw context size (what would be sent without RLM)
                raw_tokens = len(context["content"]) // 4  # ~4 chars per token

                # Simple keyword search for MVP
                chunks = self._keyword_search(context["content"], question)

                # Calculate served tokens (compressed response)
                served_tokens = sum(len(c.get("content", "")) for c in chunks) // 4
                saved_tokens = raw_tokens - served_tokens

                # Update session stats
                self.session_stats["queries"] += 1
                self.session_stats["tokens_served"] += served_tokens
                self.session_stats["tokens_saved"] += saved_tokens
                self.session_stats["raw_context_size"] = raw_tokens
                self._persist_session_stats()  # Persist to SQLite

                return {
                    "success": True,
                    "question": question,
                    "chunks": chunks,
                    "context_name": context["name"],
                    "stats": {
                        "raw_tokens": raw_tokens,
                        "served_tokens": served_tokens,
                        "saved_tokens": saved_tokens,
                    },
                }
            except Exception as e:
                logger.error(f"Query failed: {e}")
                return {"success": False, "error": str(e)}

        @self.mcp.tool("rlm_list_contexts")
        async def list_contexts() -> Dict[str, Any]:
            """
            List all loaded contexts.

            Returns:
                List of context metadata
            """
            contexts = self.context_manager.list_all()
            return {"success": True, "contexts": contexts, "count": len(contexts)}

        @self.mcp.tool("rlm_analyze")
        async def analyze(
            goal: str, context_name: Optional[str] = None
        ) -> Dict[str, Any]:
            """
            Deep analysis through C³ crystals.

            Args:
                goal: Analysis goal - summarize, find_bugs, security_audit, explain
                context_name: Context to analyze (uses default if not specified)

            Returns:
                Analysis results with primitives and insights
            """
            try:
                # Get context
                context = self.context_manager.get(context_name)
                if not context:
                    return {
                        "success": False,
                        "error": f"Context '{context_name}' not found. Load a context first.",
                    }

                # Build crystal from context
                file_crystal = self.extractor.extract_from_file(
                    context["path"], context["content"]
                )

                # Index for search
                self.indexer.clear()
                self.indexer.index_file(file_crystal)

                # Extract relations
                relations = self.extractor.extract_relations(file_crystal)

                # Generate analysis based on goal
                if goal == "summarize":
                    result = self._analyze_summarize(file_crystal)
                elif goal == "find_bugs":
                    result = self._analyze_find_bugs(file_crystal)
                elif goal == "security_audit":
                    result = self._analyze_security(file_crystal)
                elif goal == "explain":
                    result = self._analyze_explain(file_crystal)
                else:
                    result = {"message": f"Unknown goal: {goal}"}

                logger.info(
                    f"Analysis '{goal}' completed: {len(file_crystal.primitives)} primitives"
                )

                return {
                    "success": True,
                    "goal": goal,
                    "context_name": context["name"],
                    "primitives_count": len(file_crystal.primitives),
                    "relations_count": len(relations),
                    "result": result,
                }
            except Exception as e:
                logger.error(f"Analysis failed: {e}")
                return {"success": False, "error": str(e)}

        @self.mcp.tool("rlm_memory")
        async def memory(
            action: str, content: Optional[str] = None, topic: Optional[str] = None
        ) -> Dict[str, Any]:
            """
            Manage H-MEM hierarchical memory.

            Args:
                action: Action to perform - recall, store, forget, consolidate, stats
                content: Content to store (for 'store' action)
                topic: Topic to recall/forget (for 'recall'/'forget' actions)

            Returns:
                Memory operation result
            """
            try:
                if action == "store":
                    if not content:
                        return {"success": False, "error": "Content required for store"}

                    memory_id = self.memory.add_episode(
                        content=content, metadata={"source": "mcp_tool"}
                    )
                    logger.info(f"Stored episode: {memory_id}")

                    return {"success": True, "action": "store", "memory_id": memory_id}

                elif action == "recall":
                    query = topic or ""
                    results = self.memory.retrieve(query, top_k=5)

                    return {
                        "success": True,
                        "action": "recall",
                        "query": query,
                        "count": len(results),
                        "memories": [
                            {
                                "id": m.id,
                                "content": m.content[:200],  # Truncate
                                "level": m.level.name,
                                "score": getattr(m, "score", 0),
                            }
                            for m in results[:10]
                        ],
                    }

                elif action == "forget":
                    if not topic:
                        return {"success": False, "error": "Topic required for forget"}

                    # Find and remove matching memories
                    results = self.memory.retrieve(topic, top_k=5)
                    removed = 0
                    for m in results:
                        if hasattr(self.memory, "remove"):
                            self.memory.remove(m.id)
                            removed += 1

                    return {
                        "success": True,
                        "action": "forget",
                        "topic": topic,
                        "removed_count": removed,
                    }

                elif action == "consolidate":
                    # Trigger consolidation
                    if hasattr(self.memory, "consolidate"):
                        self.memory.consolidate()

                    return {
                        "success": True,
                        "action": "consolidate",
                        "message": "Consolidation triggered",
                    }

                elif action == "stats":
                    stats = (
                        self.memory.get_stats()
                        if hasattr(self.memory, "get_stats")
                        else {}
                    )

                    return {"success": True, "action": "stats", "stats": stats}

                else:
                    return {
                        "success": False,
                        "error": f"Unknown action: {action}. Use: recall, store, forget, consolidate, stats",
                    }

            except Exception as e:
                logger.error(f"Memory operation failed: {e}")
                return {"success": False, "error": str(e)}

        @self.mcp.tool("rlm_status")
        async def status() -> Dict[str, Any]:
            """
            Get RLM server status and index info.

            Returns:
                Server status, index stats, memory stats
            """
            try:
                # Import here to avoid circular
                from ..storage import get_storage
                from ..freshness import CrossReferenceValidator
                from pathlib import Path

                project_root = os.getenv("RLM_PROJECT_ROOT", os.getcwd())
                storage = get_storage(Path(project_root))
                stats = storage.get_stats()

                memory_stats = {}
                if hasattr(self.memory, "get_stats"):
                    memory_stats = self.memory.get_stats()

                return {
                    "success": True,
                    "server": "rlm-toolkit",
                    "version": "1.2.0",
                    "project_root": project_root,
                    "index": {
                        "crystals": stats.get("total_crystals", 0),
                        "tokens": stats.get("total_tokens", 0),
                        "db_size_mb": stats.get("db_size_mb", 0),
                    },
                    "memory": memory_stats,
                    "secure_mode": isinstance(self.memory, SecureHierarchicalMemory),
                    # L0 Context Auto-Injection (v2.1 fix)
                    "l0_context": self.memory_bridge_v2_store.get_l0_context(
                        max_tokens=500
                    ),
                }
            except Exception as e:
                logger.error(f"Status check failed: {e}")
                return {"success": False, "error": str(e)}

        @self.mcp.tool("rlm_session_stats")
        async def session_stats(reset: bool = False) -> Dict[str, Any]:
            """
            Get real-time session statistics showing token savings.

            Args:
                reset: Reset session stats to zero

            Returns:
                Session statistics including queries, tokens, and savings
            """
            import time

            if reset:
                self.session_stats = {
                    "queries": 0,
                    "tokens_served": 0,
                    "tokens_saved": 0,
                    "raw_context_size": 0,
                    "session_start": time.time(),
                }
                return {"success": True, "message": "Session stats reset"}

            # Calculate session duration
            session_start = self.session_stats.get("session_start")
            duration_minutes = 0
            if session_start:
                duration_minutes = (time.time() - session_start) / 60

            # Calculate savings percentage
            total_requested = (
                self.session_stats["tokens_served"] + self.session_stats["tokens_saved"]
            )
            savings_percent = 0
            if total_requested > 0:
                savings_percent = (
                    self.session_stats["tokens_saved"] / total_requested * 100
                )

            return {
                "success": True,
                "session": {
                    "queries": self.session_stats["queries"],
                    "tokens_served": self.session_stats["tokens_served"],
                    "tokens_saved": self.session_stats["tokens_saved"],
                    "savings_percent": round(savings_percent, 1),
                    "duration_minutes": round(duration_minutes, 1),
                    "raw_context_size": self.session_stats["raw_context_size"],
                },
            }

        @self.mcp.tool("rlm_reindex")
        async def reindex(
            path: Optional[str] = None, force: bool = False
        ) -> Dict[str, Any]:
            """
            Reindex project or specific path.

            Args:
                path: Path to reindex (defaults to project root)
                force: Force full reindex even if up-to-date

            Returns:
                Reindex results
            """
            try:
                import time as time_module
                from ..indexer import AutoIndexer
                from pathlib import Path

                # Rate limiting check (T5.4: max 1 reindex per 60s)
                current_time = time_module.time()
                if (
                    current_time - self._last_reindex_time
                    < self._reindex_rate_limit_seconds
                ):
                    wait_time = int(
                        self._reindex_rate_limit_seconds
                        - (current_time - self._last_reindex_time)
                    )
                    return {
                        "success": False,
                        "error": f"Rate limited. Try again in {wait_time}s",
                        "rate_limited": True,
                    }
                self._last_reindex_time = current_time

                project_root = path or os.getenv("RLM_PROJECT_ROOT", os.getcwd())
                indexer = AutoIndexer(Path(project_root))

                if force:
                    result = indexer._index_full()
                    return {
                        "success": True,
                        "action": "full_reindex",
                        "files_indexed": result.files_indexed,
                        "duration": result.duration_seconds,
                    }
                else:
                    # Delta update
                    from ..storage import get_storage

                    storage = get_storage(Path(project_root))
                    modified = storage.get_modified_files(Path(project_root))

                    if modified:
                        updated = indexer.delta_update(modified)
                        return {
                            "success": True,
                            "action": "delta_update",
                            "files_updated": updated,
                        }
                    else:
                        return {
                            "success": True,
                            "action": "none",
                            "message": "Index is up-to-date",
                        }
            except Exception as e:
                logger.error(f"Reindex failed: {e}")
                return {"success": False, "error": str(e)}

        @self.mcp.tool("rlm_validate")
        async def validate() -> Dict[str, Any]:
            """
            Validate index freshness and cross-references.

            Returns:
                Validation results
            """
            try:
                from ..storage import get_storage
                from ..freshness import CrossReferenceValidator, ActualityReviewQueue
                from pathlib import Path

                project_root = os.getenv("RLM_PROJECT_ROOT", os.getcwd())
                storage = get_storage(Path(project_root))

                # Load crystals
                crystals = {
                    c["crystal"]["path"]: c["crystal"] for c in storage.load_all()
                }

                # Cross-reference validation
                validator = CrossReferenceValidator(crystals)
                stats = validator.get_validation_stats()

                # Check stale files
                stale = storage.get_stale_crystals(ttl_hours=24)

                return {
                    "success": True,
                    "symbols": stats,
                    "stale_files": len(stale),
                    "total_files": len(crystals),
                    "health": "good" if len(stale) == 0 else "needs_refresh",
                }
            except Exception as e:
                logger.error(f"Validation failed: {e}")
                return {"success": False, "error": str(e)}

        @self.mcp.tool("rlm_settings")
        async def settings(
            action: str = "get", key: Optional[str] = None, value: Optional[str] = None
        ) -> Dict[str, Any]:
            """
            Get or set RLM settings.

            Args:
                action: 'get' or 'set'
                key: Setting key
                value: Setting value (for set)

            Returns:
                Current settings or update result
            """
            try:
                from ..storage import get_storage
                from pathlib import Path

                project_root = os.getenv("RLM_PROJECT_ROOT", os.getcwd())
                storage = get_storage(Path(project_root))

                if action == "get":
                    settings = {
                        "project_root": project_root,
                        "secure_mode": isinstance(
                            self.memory, SecureHierarchicalMemory
                        ),
                        "ttl_hours": storage.get_metadata("ttl_hours") or 24,
                        "auto_index": storage.get_metadata("auto_index") or True,
                    }
                    return {"success": True, "settings": settings}

                elif action == "set" and key:
                    storage.set_metadata(key, value)
                    return {"success": True, "updated": {key: value}}

                else:
                    return {
                        "success": False,
                        "error": "Use action='get' or action='set' with key/value",
                    }
            except Exception as e:
                logger.error(f"Settings failed: {e}")
                return {"success": False, "error": str(e)}

    def _keyword_search(self, content: str, query: str, top_k: int = 5) -> List[Dict]:
        """Simple keyword search for MVP."""
        lines = content.split("\n")
        query_words = set(query.lower().split())

        scored_lines = []
        for i, line in enumerate(lines):
            line_words = set(line.lower().split())
            score = len(query_words & line_words)
            if score > 0:
                scored_lines.append(
                    {"line_number": i + 1, "content": line.strip(), "score": score}
                )

        # Sort by score descending
        scored_lines.sort(key=lambda x: x["score"], reverse=True)
        return scored_lines[:top_k]

    def _analyze_summarize(self, crystal) -> Dict[str, Any]:
        """Generate a summary of the code structure."""
        classes = [p for p in crystal.primitives if p.ptype == "CLASS"]
        functions = [p for p in crystal.primitives if p.ptype == "FUNCTION"]
        methods = [p for p in crystal.primitives if p.ptype == "METHOD"]
        imports = [p for p in crystal.primitives if p.ptype == "IMPORT"]

        return {
            "type": "summary",
            "total_primitives": len(crystal.primitives),
            "classes": [{"name": c.name, "line": c.source_line} for c in classes],
            "functions": [{"name": f.name, "line": f.source_line} for f in functions],
            "methods_count": len(methods),
            "imports_count": len(imports),
            "summary_text": self.extractor.summarize(crystal),
        }

    def _analyze_find_bugs(self, crystal) -> Dict[str, Any]:
        """Find potential bugs and code smells."""
        issues = []

        for p in crystal.primitives:
            # Check for low confidence (uncertain code)
            if p.confidence < 0.8:
                issues.append(
                    {
                        "type": "low_confidence",
                        "name": p.name,
                        "line": p.source_line,
                        "message": f"Uncertain pattern: {p.value[:50]}...",
                    }
                )

            # Check for very short function names
            if p.ptype in ("FUNCTION", "METHOD") and len(p.name) <= 2:
                issues.append(
                    {
                        "type": "naming",
                        "name": p.name,
                        "line": p.source_line,
                        "message": f"Short function name: '{p.name}'",
                    }
                )

            # Check for eval/exec usage
            if "eval(" in p.value or "exec(" in p.value:
                issues.append(
                    {
                        "type": "security",
                        "name": p.name,
                        "line": p.source_line,
                        "message": "Dynamic code execution detected",
                    }
                )

        return {"type": "bugs", "issues_count": len(issues), "issues": issues}

    def _analyze_security(self, crystal) -> Dict[str, Any]:
        """Security audit of the code."""
        findings = []

        dangerous_patterns = [
            ("eval(", "code_injection", "Use of eval() is dangerous"),
            ("exec(", "code_injection", "Use of exec() is dangerous"),
            ("subprocess", "command_injection", "Subprocess usage - verify inputs"),
            ("os.system", "command_injection", "os.system usage - verify inputs"),
            ("pickle", "deserialization", "Pickle usage may be unsafe"),
            ("SQL", "sql_injection", "SQL detected - verify parameterization"),
            ("password", "credential", "Password handling detected"),
            ("secret", "credential", "Secret handling detected"),
            ("api_key", "credential", "API key handling detected"),
        ]

        for p in crystal.primitives:
            for pattern, category, message in dangerous_patterns:
                if pattern.lower() in p.value.lower():
                    findings.append(
                        {
                            "category": category,
                            "pattern": pattern,
                            "line": p.source_line,
                            "message": message,
                            "confidence": p.confidence,
                        }
                    )

        return {
            "type": "security",
            "findings_count": len(findings),
            "findings": findings,
            "risk_level": (
                "high"
                if len(findings) > 5
                else "medium" if len(findings) > 0 else "low"
            ),
        }

    def _analyze_explain(self, crystal) -> Dict[str, Any]:
        """Explain the code structure."""
        summary = self.extractor.summarize(crystal)

        # Get top-level structure
        classes = [p for p in crystal.primitives if p.ptype == "CLASS"]

        explanations = []
        for cls in classes:
            methods = [
                p
                for p in crystal.primitives
                if p.ptype == "METHOD" and p.metadata.get("class_context") == cls.name
            ]
            explanations.append(
                {
                    "class": cls.name,
                    "line": cls.source_line,
                    "methods": [m.name for m in methods],
                }
            )

        return {
            "type": "explanation",
            "summary": summary,
            "structure": explanations,
            "primitives_breakdown": self.indexer.get_stats().get("type_counts", {}),
        }

    async def run(self):
        """Run the MCP server."""
        if not MCP_AVAILABLE:
            logger.error("MCP SDK not available. Install with: pip install mcp")
            return

        logger.info("Starting RLM MCP Server...")

        # FastMCP handles stdio internally
        await self.mcp.run()


def create_server() -> RLMServer:
    """Create a new RLM MCP Server instance."""
    return RLMServer()


def run_server():
    """Run the MCP server (blocking)."""
    server = create_server()
    # FastMCP.run() handles its own event loop via anyio
    server.mcp.run()


if __name__ == "__main__":
    run_server()
