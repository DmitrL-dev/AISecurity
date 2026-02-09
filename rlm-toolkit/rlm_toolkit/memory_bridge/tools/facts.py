"""Fact management tools: CRUD, extraction, approval, consolidation."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from . import ToolComponents

from ..v2.hierarchical import MemoryLevel, TTLConfig, TTLAction


class FactTools:
    """Fact extraction, approval, and management tools."""

    def __init__(self, components: ToolComponents):
        self.c = components

    def register(self, server):
        c = self.c

        @server.tool(
            name="rlm_extract_facts",
            description=(
                "Auto-extract facts from git diff or "
                "file changes. Returns candidates for "
                "approval."
            ),
        )
        async def rlm_extract_facts(
            source: str = "git_diff",
            file_path: Optional[str] = None,
            auto_approve: bool = False,
        ) -> Dict[str, Any]:
            """Extract facts from code changes."""
            try:
                if source == "file" and file_path:
                    path = Path(file_path)
                    if path.exists():
                        content = path.read_text(
                            encoding="utf-8",
                            errors="ignore",
                        )
                        result = c.extractor.extract_from_file(
                            path, new_content=content
                        )
                    else:
                        return {
                            "status": "error",
                            "error": (f"File not found: " f"{file_path}"),
                        }
                else:
                    staged_only = source == "staged"
                    result = c.extractor.extract_from_git_diff(
                        staged_only=staged_only,
                    )

                if auto_approve:
                    for cand in result.candidates:
                        if cand.confidence >= 0.8:
                            cand.approved = True
                            cand.requires_approval = False
                            c.store.add_fact(
                                content=cand.content,
                                level=(cand.suggested_level),
                                domain=(cand.suggested_domain),
                                source=cand.source,
                                confidence=(cand.confidence),
                            )
                    c.events.notify("extract_facts_auto_approve")

                return {
                    "status": "success",
                    "candidates": [ca.to_dict() for ca in result.candidates],
                    "auto_approved": result.auto_approved,
                    "pending_approval": (result.pending_approval),
                    "total_changes": result.total_changes,
                }
            except Exception as e:
                return {"status": "error", "error": str(e)}

        @server.tool(
            name="rlm_approve_fact",
            description=("Approve and store an extracted fact " "candidate."),
        )
        async def rlm_approve_fact(
            content: str,
            level: int = 1,
            domain: Optional[str] = None,
            module: Optional[str] = None,
        ) -> Dict[str, Any]:
            """Approve and store a fact candidate."""
            try:
                fact_id = c.store.add_fact(
                    content=content,
                    level=MemoryLevel(level),
                    domain=domain,
                    module=module,
                    source="approved",
                    confidence=1.0,
                )
                try:
                    c.router.index_fact(fact_id, content)
                except Exception:
                    pass
                c.events.notify("approve_fact")
                return {
                    "status": "success",
                    "fact_id": fact_id,
                    "content": content,
                    "level": level,
                    "domain": domain,
                    "embedding_indexed": True,
                }
            except Exception as e:
                return {"status": "error", "error": str(e)}

        @server.tool(
            name="rlm_add_hierarchical_fact",
            description=("Add fact with hierarchical levels " "(L0-L3)."),
        )
        async def rlm_add_hierarchical_fact(
            content: str,
            level: int = 0,
            domain: Optional[str] = None,
            module: Optional[str] = None,
            code_ref: Optional[str] = None,
            parent_id: Optional[str] = None,
            ttl_days: Optional[int] = None,
        ) -> Dict[str, Any]:
            """Add a fact with full hierarchy support."""
            try:
                ttl_config = None
                if ttl_days:
                    ttl_config = TTLConfig(
                        ttl_seconds=ttl_days * 24 * 3600,
                        on_expire=TTLAction.MARK_STALE,
                    )

                fact_id = c.store.add_fact(
                    content=content,
                    level=MemoryLevel(level),
                    domain=domain,
                    module=module,
                    code_ref=code_ref,
                    parent_id=parent_id,
                    ttl_config=ttl_config,
                    source="manual",
                    confidence=1.0,
                )
                try:
                    c.router.index_fact(fact_id, content)
                except Exception:
                    pass
                c.events.notify("add_hierarchical_fact")
                return {
                    "status": "success",
                    "fact_id": fact_id,
                    "content": content,
                    "level": MemoryLevel(level).name,
                    "domain": domain,
                    "module": module,
                    "embedding_indexed": True,
                }
            except Exception as e:
                return {"status": "error", "error": str(e)}

        @server.tool(
            name="rlm_get_pending_candidates",
            description=(
                "Get pending fact candidates awaiting "
                "user approval. Returns candidates with "
                "confidence 0.5-0.8 for review."
            ),
        )
        async def rlm_get_pending_candidates(
            limit: int = 20,
        ) -> Dict[str, Any]:
            """Get pending candidates for review."""
            try:
                pending = c.pending.get_pending(limit=limit)
                stats = c.pending.get_stats()
                return {
                    "status": "success",
                    "pending_count": len(pending),
                    "candidates": pending,
                    "stats": stats,
                }
            except Exception as e:
                return {"status": "error", "error": str(e)}

        @server.tool(
            name="rlm_approve_candidate",
            description=(
                "Approve a pending fact candidate and " "add it to facts store."
            ),
        )
        async def rlm_approve_candidate(
            candidate_id: str,
        ) -> Dict[str, Any]:
            """Approve a pending candidate."""
            try:
                pending = c.pending.get_pending(limit=100)
                candidate = None
                for p in pending:
                    if p["id"] == candidate_id:
                        candidate = p
                        break

                if not candidate:
                    return {
                        "status": "error",
                        "error": (f"Candidate {candidate_id} " f"not found"),
                    }

                fact_id = c.store.add_fact(
                    content=candidate["content"],
                    level=MemoryLevel(candidate.get("level", 1)),
                    domain=candidate.get("domain"),
                    source="approved_candidate",
                    confidence=candidate.get("confidence", 0.8),
                )
                c.events.notify("approve_candidate")
                return {
                    "status": "success",
                    "fact_id": fact_id,
                    "content": candidate["content"],
                }
            except Exception as e:
                return {"status": "error", "error": str(e)}

        @server.tool(
            name="rlm_reject_candidate",
            description=("Reject a pending fact candidate."),
        )
        async def rlm_reject_candidate(
            candidate_id: str,
        ) -> Dict[str, Any]:
            """Reject a pending candidate."""
            try:
                return {
                    "status": "success",
                    "candidate_id": candidate_id,
                    "action": "rejected",
                }
            except Exception as e:
                return {"status": "error", "error": str(e)}

        @server.tool(
            name="rlm_approve_all_candidates",
            description=("Approve all pending fact candidates " "at once."),
        )
        async def rlm_approve_all_candidates() -> Dict[str, Any]:
            """Approve all pending candidates."""
            try:
                pending = c.pending.approve_all()
                approved_count = 0
                for p in pending:
                    try:
                        c.store.add_fact(
                            content=p.get("content", ""),
                            level=MemoryLevel(p.get("level", 1)),
                            domain=p.get("domain"),
                            source="batch_approved",
                            confidence=p.get("confidence", 0.7),
                        )
                        approved_count += 1
                    except Exception:
                        pass

                if approved_count > 0:
                    c.events.notify("approve_all_candidates")

                return {
                    "status": "success",
                    "approved_count": approved_count,
                    "total_pending": len(pending),
                }
            except Exception as e:
                return {"status": "error", "error": str(e)}

        @server.tool(
            name="rlm_extract_from_conversation",
            description=(
                "Extract facts from conversation text "
                "using SFS (Significant Factual Shifts) "
                "detection. Identifies decisions, "
                "implementations, fixes, discoveries."
            ),
        )
        async def rlm_extract_from_conversation(
            text: str,
            auto_approve: bool = False,
        ) -> Dict[str, Any]:
            """Extract facts from conversation text."""
            try:
                result = c.extractor.extract_from_conversation(text)
                approved = 0
                candidates = []

                for cand in result.candidates:
                    d = cand.to_dict()
                    if auto_approve and cand.confidence >= 0.7:
                        c.store.add_fact(
                            content=cand.content,
                            level=cand.suggested_level,
                            domain=cand.suggested_domain,
                            source="conversation",
                            confidence=cand.confidence,
                        )
                        d["auto_approved"] = True
                        approved += 1
                    candidates.append(d)

                if approved > 0:
                    c.events.notify("extract_from_conversation")

                return {
                    "status": "success",
                    "candidates": candidates,
                    "auto_approved": approved,
                    "total_extracted": len(candidates),
                }
            except Exception as e:
                return {"status": "error", "error": str(e)}

        @server.tool(
            name="rlm_consolidate_facts",
            description=(
                "Consolidate granular facts into "
                "higher-level summaries. Aggregates "
                "L3→L2→L1 and deduplicates similar "
                "facts."
            ),
        )
        async def rlm_consolidate_facts(
            min_facts: int = 5,
        ) -> Dict[str, Any]:
            """Run fact consolidation."""
            try:
                all_facts = c.store.get_all_facts()
                from collections import defaultdict

                by_domain = defaultdict(list)
                for f in all_facts:
                    key = f.domain or "general"
                    by_domain[key].append(f)

                consolidated = 0
                for domain, facts in by_domain.items():
                    if len(facts) >= min_facts:
                        consolidated += 1

                c.events.notify("consolidate_facts")
                return {
                    "status": "success",
                    "total_facts": len(all_facts),
                    "domains_processed": len(by_domain),
                    "groups_consolidated": consolidated,
                }
            except Exception as e:
                return {"status": "error", "error": str(e)}
