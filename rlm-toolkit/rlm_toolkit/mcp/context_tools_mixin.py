"""Context tool handlers for RLMServer.

C³ Crystal tools: load_context, query, list_contexts, analyze.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .contexts import ContextManager

logger = logging.getLogger("rlm_mcp")


class ContextToolsMixin:
    """C³ Context tools for RLMServer."""

    if TYPE_CHECKING:
        context_manager: ContextManager
        session_stats: Dict[str, Any]
        extractor: Any
        indexer: Any

        def _keyword_search(self, content: str, query: str) -> list[dict[str, Any]]: ...
        def _persist_session_stats(self) -> None: ...
        def _analyze_summarize(self, crystal: Any) -> Dict[str, Any]: ...
        def _analyze_find_bugs(self, crystal: Any) -> Dict[str, Any]: ...
        def _analyze_security(self, crystal: Any) -> Dict[str, Any]: ...
        def _analyze_explain(self, crystal: Any) -> Dict[str, Any]: ...

    def _register_context_tools(self) -> None:
        """Register context-related MCP tools."""

        @self.mcp.tool("rlm_load_context")  # type: ignore[attr-defined, misc]
        async def load_context(
            path: str,
            name: Optional[str] = None,
        ) -> Dict[str, Any]:
            """
            Load a file or directory into context.

            Args:
                path: Path to file or directory
                name: Optional name for the context
                    (defaults to filename)

            Returns:
                Context metadata (name, size, token_count)
            """
            try:
                result = await self.context_manager.load(
                    path,
                    name,
                )
                logger.info(
                    f"Loaded context: {result['name']} "
                    f"({result['token_count']} tokens)"
                )
                return {
                    "success": True,
                    "context": result,
                }
            except Exception as e:
                logger.error(f"Failed to load context: {e}")
                return {"success": False, "error": str(e)}

        @self.mcp.tool("rlm_query")  # type: ignore[attr-defined, misc]
        async def query(
            question: str,
            context_name: Optional[str] = None,
        ) -> Dict[str, Any]:
            """
            Search in loaded context.

            Args:
                question: The question to answer
                context_name: Optional context name
                    (uses default if not specified)

            Returns:
                Relevant chunks and answer
            """
            try:
                import time

                if self.session_stats["session_start"] is None:
                    self.session_stats["session_start"] = time.time()

                context = self.context_manager.get(
                    context_name,
                )
                if not context:
                    return {
                        "success": False,
                        "error": (f"Context '{context_name}' " f"not found"),
                    }

                raw_tokens = len(context["content"]) // 4
                chunks = self._keyword_search(
                    context["content"],
                    question,
                )
                served_tokens = sum(len(c.get("content", "")) for c in chunks) // 4
                saved_tokens = raw_tokens - served_tokens

                self.session_stats["queries"] += 1
                self.session_stats["tokens_served"] += served_tokens
                self.session_stats["tokens_saved"] += saved_tokens
                self.session_stats["raw_context_size"] = raw_tokens
                self._persist_session_stats()

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

        @self.mcp.tool("rlm_list_contexts")  # type: ignore[attr-defined, misc]
        async def list_contexts() -> Dict[str, Any]:
            """
            List all loaded contexts.

            Returns:
                List of context metadata
            """
            contexts = self.context_manager.list_all()
            return {
                "success": True,
                "contexts": contexts,
                "count": len(contexts),
            }

        @self.mcp.tool("rlm_analyze")  # type: ignore[attr-defined, misc]
        async def analyze(
            goal: str,
            context_name: Optional[str] = None,
        ) -> Dict[str, Any]:
            """
            Deep analysis through C³ crystals.

            Args:
                goal: Analysis goal - summarize,
                    find_bugs, security_audit, explain
                context_name: Context to analyze
                    (uses default if not specified)

            Returns:
                Analysis results with primitives
                and insights
            """
            try:
                context = self.context_manager.get(
                    context_name,
                )
                if not context:
                    return {
                        "success": False,
                        "error": (
                            f"Context '{context_name}' " f"not found. Load first."
                        ),
                    }

                file_crystal = self.extractor.extract_from_file(
                    context["path"],
                    context["content"],
                )

                self.indexer.clear()
                self.indexer.index_file(file_crystal)
                relations = self.extractor.extract_relations(
                    file_crystal,
                )

                analyzers = {
                    "summarize": self._analyze_summarize,
                    "find_bugs": self._analyze_find_bugs,
                    "security_audit": (self._analyze_security),
                    "explain": self._analyze_explain,
                }
                analyzer = analyzers.get(goal)
                if analyzer:
                    result = analyzer(file_crystal)
                else:
                    result = {"message": f"Unknown goal: {goal}"}

                logger.info(
                    f"Analysis '{goal}' completed: "
                    f"{len(file_crystal.primitives)} "
                    f"primitives"
                )

                return {
                    "success": True,
                    "goal": goal,
                    "context_name": context["name"],
                    "primitives_count": len(
                        file_crystal.primitives,
                    ),
                    "relations_count": len(relations),
                    "result": result,
                }
            except Exception as e:
                logger.error(f"Analysis failed: {e}")
                return {
                    "success": False,
                    "error": str(e),
                }
