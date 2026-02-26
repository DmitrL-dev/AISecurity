#!/usr/bin/env python3
"""
GoMCP Python Bridge — NLP operations for the Go MCP server.

Protocol:
  - Invoked as subprocess per call: python rlm_bridge.py
  - Reads JSON from stdin:  {"method": "method_name", "params": {...}}
  - Writes JSON to stdout:  {"result": ...} or {"error": "message"}

Requires: sentence-transformers, numpy (installed via requirements-bridge.txt)
Database:  .rlm/memory/memory_bridge_v2.db (same SQLite as GoMCP)
"""

import json
import os
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Globals (lazy-loaded)
# ---------------------------------------------------------------------------

_embedder = None
_MODEL_NAME = "all-MiniLM-L6-v2"


def _get_db_path() -> str:
    """Resolve the memory database path."""
    # Check environment variable first, then walk up from script location
    rlm_dir = os.environ.get("RLM_DIR", "")
    if rlm_dir:
        return os.path.join(rlm_dir, "memory", "memory_bridge_v2.db")

    # Walk up from script dir looking for .rlm/
    current = Path(__file__).resolve().parent
    for _ in range(5):
        candidate = current / ".rlm" / "memory" / "memory_bridge_v2.db"
        if candidate.exists():
            return str(candidate)
        current = current.parent

    # Fallback
    return os.path.join(".rlm", "memory", "memory_bridge_v2.db")


def _get_db() -> sqlite3.Connection:
    """Open a read/write connection to the fact database."""
    db_path = _get_db_path()
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def _get_embedder():
    """Lazy-load the sentence-transformers model."""
    global _embedder
    if _embedder is None:
        try:
            from sentence_transformers import SentenceTransformer

            _embedder = SentenceTransformer(_MODEL_NAME)
        except ImportError:
            raise RuntimeError(
                "sentence-transformers not installed. "
                "Run: pip install sentence-transformers"
            )
    return _embedder


def _encode(text: str) -> List[float]:
    """Encode text to embedding vector."""
    emb = _get_embedder().encode(text)
    return emb.tolist()


def _encode_batch(texts: List[str]) -> List[List[float]]:
    """Encode multiple texts to embedding vectors."""
    embeddings = _get_embedder().encode(texts)
    return [e.tolist() for e in embeddings]


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    import numpy as np

    a_np = np.array(a, dtype=np.float32)
    b_np = np.array(b, dtype=np.float32)
    dot = np.dot(a_np, b_np)
    norm_a = np.linalg.norm(a_np)
    norm_b = np.linalg.norm(b_np)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot / (norm_a * norm_b))


def _cosine_similarity_batch(
    query_vec: List[float], matrix: "np.ndarray"
) -> "np.ndarray":
    """Compute cosine similarity between query and matrix of vectors."""
    import numpy as np

    q = np.array(query_vec, dtype=np.float32)
    norm_q = np.linalg.norm(q)
    if norm_q == 0:
        return np.zeros(matrix.shape[0])
    norms = np.linalg.norm(matrix, axis=1)
    norms[norms == 0] = 1.0
    return np.dot(matrix, q) / (norms * norm_q)


# ---------------------------------------------------------------------------
# Method handlers
# ---------------------------------------------------------------------------


def handle_compute_embedding(params: Dict[str, Any]) -> Dict[str, Any]:
    """Compute embedding vector for text."""
    text = params.get("text", "")
    if not text:
        raise ValueError("text parameter is required")

    embedding = _encode(text)
    return {"embedding": embedding, "model": _MODEL_NAME}


def handle_semantic_search(params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Semantic vector similarity search across facts."""
    import numpy as np

    query = params.get("query", "")
    limit = params.get("limit", 10)
    threshold = params.get("threshold", 0.0)

    if not query:
        raise ValueError("query parameter is required")

    # Encode query
    query_vec = _encode(query)

    # Load all embeddings from the database
    conn = _get_db()
    try:
        rows = conn.execute("""
            SELECT e.fact_id, e.embedding, f.content
            FROM embeddings_index e
            JOIN hierarchical_facts f ON f.id = e.fact_id
            WHERE f.is_archived = 0
        """).fetchall()
    finally:
        conn.close()

    if not rows:
        return []

    # Build matrix for batch cosine similarity
    fact_ids = []
    contents = []
    embeddings = []
    for row in rows:
        try:
            emb = json.loads(row["embedding"])
            fact_ids.append(row["fact_id"])
            contents.append(row["content"])
            embeddings.append(emb)
        except (json.JSONDecodeError, TypeError):
            continue

    if not embeddings:
        return []

    matrix = np.array(embeddings, dtype=np.float32)
    scores = _cosine_similarity_batch(query_vec, matrix)

    # Sort by score descending, apply threshold and limit
    indices = np.argsort(-scores)
    results = []
    for idx in indices:
        score = float(scores[idx])
        if score < threshold:
            break
        results.append(
            {
                "fact_id": fact_ids[idx],
                "content": contents[idx][:500],
                "similarity": round(score, 4),
            }
        )
        if len(results) >= limit:
            break

    return results


def handle_reindex_embeddings(params: Dict[str, Any]) -> Dict[str, Any]:
    """Reindex all fact embeddings."""
    force = params.get("force", False)

    conn = _get_db()
    try:
        # Get facts that need embedding
        if force:
            rows = conn.execute(
                "SELECT id, content FROM hierarchical_facts WHERE is_archived = 0"
            ).fetchall()
        else:
            # Only facts without embeddings
            rows = conn.execute("""
                SELECT f.id, f.content FROM hierarchical_facts f
                LEFT JOIN embeddings_index e ON f.id = e.fact_id
                WHERE f.is_archived = 0 AND e.fact_id IS NULL
            """).fetchall()

        if not rows:
            return {"indexed": 0, "total": 0, "status": "up_to_date"}

        # Batch encode
        ids = [r["id"] for r in rows]
        texts = [r["content"] for r in rows]
        embeddings = _encode_batch(texts)

        # Upsert into embeddings_index
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        for fact_id, emb in zip(ids, embeddings):
            emb_json = json.dumps(emb)
            conn.execute(
                """
                INSERT INTO embeddings_index (fact_id, embedding, model_name, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(fact_id) DO UPDATE SET
                    embedding = excluded.embedding,
                    model_name = excluded.model_name,
                    updated_at = excluded.updated_at
            """,
                (fact_id, emb_json, _MODEL_NAME, now),
            )

        conn.commit()
        return {"indexed": len(ids), "total": len(ids), "status": "completed"}
    finally:
        conn.close()


def handle_index_embeddings(params: Dict[str, Any]) -> Dict[str, Any]:
    """Index embeddings for specific facts or all facts."""
    index_all = params.get("all", False)
    fact_ids_str = params.get("fact_ids", "")

    if index_all:
        return handle_reindex_embeddings({"force": False})

    if not fact_ids_str:
        raise ValueError("fact_ids or all=true is required")

    fact_ids = [fid.strip() for fid in fact_ids_str.split(",") if fid.strip()]
    if not fact_ids:
        return {"indexed": 0, "status": "no_ids"}

    conn = _get_db()
    try:
        indexed = 0
        for fact_id in fact_ids:
            row = conn.execute(
                "SELECT content FROM hierarchical_facts WHERE id = ?", (fact_id,)
            ).fetchone()
            if not row:
                continue
            emb = _encode(row["content"])
            emb_json = json.dumps(emb)
            now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            conn.execute(
                """
                INSERT INTO embeddings_index (fact_id, embedding, model_name, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(fact_id) DO UPDATE SET
                    embedding = excluded.embedding,
                    model_name = excluded.model_name,
                    updated_at = excluded.updated_at
            """,
                (fact_id, emb_json, _MODEL_NAME, now),
            )
            indexed += 1

        conn.commit()
        return {"indexed": indexed, "requested": len(fact_ids), "status": "completed"}
    finally:
        conn.close()


def handle_consolidate_facts(params: Dict[str, Any]) -> Dict[str, Any]:
    """Consolidate duplicate/similar facts using NLP."""
    import numpy as np

    sim_threshold = params.get("similarity_threshold", 0.85)
    domain_filter = params.get("domain")

    conn = _get_db()
    try:
        # Load facts with embeddings
        if domain_filter:
            rows = conn.execute(
                """
                SELECT f.id, f.content, f.domain, f.level, e.embedding
                FROM hierarchical_facts f
                JOIN embeddings_index e ON f.id = e.fact_id
                WHERE f.is_archived = 0 AND f.is_stale = 0 AND f.domain = ?
            """,
                (domain_filter,),
            ).fetchall()
        else:
            rows = conn.execute("""
                SELECT f.id, f.content, f.domain, f.level, e.embedding
                FROM hierarchical_facts f
                JOIN embeddings_index e ON f.id = e.fact_id
                WHERE f.is_archived = 0 AND f.is_stale = 0
            """).fetchall()

        if len(rows) < 2:
            return {"duplicates_found": 0, "groups": [], "status": "insufficient_data"}

        # Parse embeddings and build matrix
        facts = []
        embeddings = []
        for r in rows:
            try:
                emb = json.loads(r["embedding"])
                facts.append(
                    {
                        "id": r["id"],
                        "content": r["content"][:200],
                        "domain": r["domain"],
                        "level": r["level"],
                    }
                )
                embeddings.append(emb)
            except (json.JSONDecodeError, TypeError):
                continue

        if len(facts) < 2:
            return {
                "duplicates_found": 0,
                "groups": [],
                "status": "insufficient_embeddings",
            }

        matrix = np.array(embeddings, dtype=np.float32)
        # Normalize for fast cosine
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        matrix_norm = matrix / norms

        # Find duplicate groups via pairwise similarity
        sim_matrix = np.dot(matrix_norm, matrix_norm.T)
        visited = set()
        groups = []

        for i in range(len(facts)):
            if i in visited:
                continue
            group = [i]
            visited.add(i)
            for j in range(i + 1, len(facts)):
                if j in visited:
                    continue
                if sim_matrix[i][j] >= sim_threshold:
                    group.append(j)
                    visited.add(j)
            if len(group) > 1:
                groups.append(
                    {
                        "facts": [facts[idx] for idx in group],
                        "similarity": round(
                            float(
                                np.mean(
                                    [
                                        sim_matrix[group[a]][group[b]]
                                        for a in range(len(group))
                                        for b in range(a + 1, len(group))
                                    ]
                                )
                            ),
                            4,
                        ),
                    }
                )

        return {
            "duplicates_found": sum(len(g["facts"]) for g in groups),
            "groups": groups[:20],  # Limit output size
            "total_checked": len(facts),
            "threshold": sim_threshold,
            "status": "completed",
        }
    finally:
        conn.close()


def handle_enterprise_context(params: Dict[str, Any]) -> Dict[str, Any]:
    """Get enterprise-level context summary."""
    max_tokens = params.get("max_tokens", 2000)

    conn = _get_db()
    try:
        # Get L0 facts (project-level)
        l0_rows = conn.execute("""
            SELECT id, content, domain FROM hierarchical_facts
            WHERE level = 0 AND is_archived = 0 AND is_stale = 0
            ORDER BY created_at DESC
        """).fetchall()

        # Get domain summary
        domain_rows = conn.execute("""
            SELECT domain, COUNT(*) as cnt
            FROM hierarchical_facts
            WHERE is_archived = 0 AND domain IS NOT NULL AND domain != ''
            GROUP BY domain ORDER BY cnt DESC LIMIT 20
        """).fetchall()

        # Get level distribution
        level_rows = conn.execute("""
            SELECT level, COUNT(*) as cnt
            FROM hierarchical_facts WHERE is_archived = 0
            GROUP BY level ORDER BY level
        """).fetchall()

        # Build summary within token budget
        l0_facts = []
        char_budget = max_tokens * 4  # ~4 chars per token
        used = 0
        for r in l0_rows:
            entry = {"content": r["content"], "domain": r["domain"] or ""}
            entry_len = len(r["content"]) + 20
            if used + entry_len > char_budget:
                break
            l0_facts.append(entry)
            used += entry_len

        return {
            "project_facts": l0_facts,
            "domains": [{"name": r["domain"], "count": r["cnt"]} for r in domain_rows],
            "level_distribution": {str(r["level"]): r["cnt"] for r in level_rows},
            "total_project_facts": len(l0_rows),
        }
    finally:
        conn.close()


def handle_route_context(params: Dict[str, Any]) -> Dict[str, Any]:
    """Route context to appropriate handler based on intent."""
    query = params.get("query", "")
    if not query:
        raise ValueError("query parameter is required")

    # Simple keyword-based routing (no ML needed)
    query_lower = query.lower()

    # Determine intent
    intent = "general"
    if any(w in query_lower for w in ["search", "find", "look for", "where"]):
        intent = "search"
    elif any(w in query_lower for w in ["add", "remember", "save", "store"]):
        intent = "store"
    elif any(w in query_lower for w in ["why", "because", "reason", "decision"]):
        intent = "causal"
    elif any(w in query_lower for w in ["status", "health", "stats", "summary"]):
        intent = "status"
    elif any(w in query_lower for w in ["code", "function", "class", "file"]):
        intent = "code"

    # Suggest tools based on intent
    tool_suggestions = {
        "search": ["search_facts", "semantic_search"],
        "store": ["add_fact"],
        "causal": ["get_causal_chain", "add_causal_node"],
        "status": ["dashboard", "fact_stats"],
        "code": ["search_crystals", "get_crystal"],
        "general": ["search_facts", "dashboard"],
    }

    return {
        "intent": intent,
        "suggested_tools": tool_suggestions.get(intent, []),
        "query": query,
    }


def handle_discover_deep(params: Dict[str, Any]) -> Dict[str, Any]:
    """Deep discovery of related facts and patterns."""
    import numpy as np

    topic = params.get("topic", "")
    depth = params.get("depth", 2)
    max_results = params.get("max_results", 20)

    if not topic:
        raise ValueError("topic parameter is required")

    # Start with semantic search for the topic
    seed_results = handle_semantic_search(
        {
            "query": topic,
            "limit": min(max_results, 10),
            "threshold": 0.3,
        }
    )

    if not seed_results or depth <= 1:
        return {
            "topic": topic,
            "depth": 1,
            "results": seed_results,
            "total": len(seed_results),
        }

    # Depth 2+: find facts related to the seed results
    all_fact_ids = {r["fact_id"] for r in seed_results}
    expanded_results = list(seed_results)

    for result in seed_results[:5]:  # Expand top 5 seeds
        related = handle_semantic_search(
            {
                "query": result["content"][:200],
                "limit": 5,
                "threshold": 0.5,
            }
        )
        for r in related:
            if r["fact_id"] not in all_fact_ids:
                all_fact_ids.add(r["fact_id"])
                r["discovered_via"] = result["fact_id"]
                expanded_results.append(r)
                if len(expanded_results) >= max_results:
                    break
        if len(expanded_results) >= max_results:
            break

    return {
        "topic": topic,
        "depth": min(depth, 2),
        "results": expanded_results[:max_results],
        "total": len(expanded_results),
    }


def handle_extract_from_conversation(params: Dict[str, Any]) -> Dict[str, Any]:
    """Extract facts from conversation text."""
    text = params.get("text", "")
    if not text:
        raise ValueError("text parameter is required")

    # Simple sentence-based extraction
    # Split on sentence boundaries
    import re

    sentences = re.split(r"(?<=[.!?])\s+", text.strip())

    # Filter for fact-worthy sentences (heuristic)
    candidates = []
    for sent in sentences:
        sent = sent.strip()
        if len(sent) < 20 or len(sent) > 500:
            continue
        # Skip questions, greetings, filler
        if sent.endswith("?"):
            continue
        lower = sent.lower()
        if any(w in lower for w in ["hello", "hi ", "thanks", "please", "okay"]):
            continue
        # Prefer statements with technical content
        has_technical = any(
            w in lower
            for w in [
                "function",
                "class",
                "module",
                "api",
                "database",
                "service",
                "architecture",
                "pattern",
                "config",
                "deploy",
                "security",
                "error",
                "bug",
                "fix",
                "implement",
                "design",
                "protocol",
                "version",
                "release",
                "test",
                "build",
                "dependency",
            ]
        )
        candidates.append(
            {
                "content": sent,
                "confidence": 0.8 if has_technical else 0.5,
                "is_technical": has_technical,
            }
        )

    # Deduplicate by embedding similarity if we have enough candidates
    if len(candidates) > 3:
        try:
            texts = [c["content"] for c in candidates]
            embeddings = _encode_batch(texts)
            # Remove near-duplicates
            import numpy as np

            keep = [0]
            for i in range(1, len(candidates)):
                is_dup = False
                for j in keep:
                    sim = _cosine_similarity(embeddings[i], embeddings[j])
                    if sim > 0.85:
                        is_dup = True
                        break
                if not is_dup:
                    keep.append(i)
            candidates = [candidates[i] for i in keep]
        except Exception:
            pass  # Proceed without dedup

    return {
        "extracted": candidates[:20],
        "total_sentences": len(sentences),
        "total_candidates": len(candidates),
        "status": "completed",
    }


def handle_build_communities(params: Dict[str, Any]) -> Dict[str, Any]:
    """Build fact communities using graph clustering."""
    import numpy as np

    min_size = params.get("min_community_size", 3)
    sim_threshold = params.get("similarity_threshold", 0.7)

    conn = _get_db()
    try:
        rows = conn.execute("""
            SELECT f.id, f.content, f.domain, e.embedding
            FROM hierarchical_facts f
            JOIN embeddings_index e ON f.id = e.fact_id
            WHERE f.is_archived = 0 AND f.is_stale = 0
        """).fetchall()
    finally:
        conn.close()

    if len(rows) < min_size:
        return {
            "communities": [],
            "total_facts": len(rows),
            "status": "insufficient_data",
        }

    # Parse embeddings
    facts = []
    embeddings = []
    for r in rows:
        try:
            emb = json.loads(r["embedding"])
            facts.append(
                {
                    "id": r["id"],
                    "content": r["content"][:150],
                    "domain": r["domain"] or "",
                }
            )
            embeddings.append(emb)
        except (json.JSONDecodeError, TypeError):
            continue

    if len(facts) < min_size:
        return {
            "communities": [],
            "total_facts": len(facts),
            "status": "insufficient_embeddings",
        }

    matrix = np.array(embeddings, dtype=np.float32)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    matrix_norm = matrix / norms
    sim_matrix = np.dot(matrix_norm, matrix_norm.T)

    # Simple connected-component clustering
    n = len(facts)
    visited = [False] * n
    communities = []

    for i in range(n):
        if visited[i]:
            continue
        # BFS from node i
        queue = [i]
        visited[i] = True
        component = [i]
        while queue:
            node = queue.pop(0)
            for j in range(n):
                if not visited[j] and sim_matrix[node][j] >= sim_threshold:
                    visited[j] = True
                    queue.append(j)
                    component.append(j)

        if len(component) >= min_size:
            # Find dominant domain
            domains = {}
            for idx in component:
                d = facts[idx]["domain"]
                if d:
                    domains[d] = domains.get(d, 0) + 1
            dominant = max(domains, key=domains.get) if domains else "unknown"

            communities.append(
                {
                    "size": len(component),
                    "dominant_domain": dominant,
                    "facts": [facts[idx] for idx in component[:10]],  # Cap display
                    "avg_similarity": round(
                        float(
                            np.mean(
                                [
                                    sim_matrix[component[a]][component[b]]
                                    for a in range(min(len(component), 10))
                                    for b in range(a + 1, min(len(component), 10))
                                ]
                            )
                        ),
                        4,
                    )
                    if len(component) > 1
                    else 1.0,
                }
            )

    # Sort by size descending
    communities.sort(key=lambda c: c["size"], reverse=True)

    return {
        "communities": communities[:15],
        "total_facts": len(facts),
        "total_communities": len(communities),
        "threshold": sim_threshold,
        "status": "completed",
    }


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

HANDLERS = {
    "compute_embedding": handle_compute_embedding,
    "semantic_search": handle_semantic_search,
    "reindex_embeddings": handle_reindex_embeddings,
    "index_embeddings": handle_index_embeddings,
    "consolidate_facts": handle_consolidate_facts,
    "enterprise_context": handle_enterprise_context,
    "route_context": handle_route_context,
    "discover_deep": handle_discover_deep,
    "extract_from_conversation": handle_extract_from_conversation,
    "build_communities": handle_build_communities,
}


def main():
    """Read JSON-RPC request from stdin, dispatch, write response to stdout."""
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            json.dump({"error": "empty request"}, sys.stdout)
            return

        request = json.loads(raw)
        method = request.get("method", "")
        params = request.get("params", {}) or {}

        handler = HANDLERS.get(method)
        if handler is None:
            json.dump({"error": f"unknown method: {method}"}, sys.stdout)
            return

        result = handler(params)
        json.dump({"result": result}, sys.stdout)

    except json.JSONDecodeError as e:
        json.dump({"error": f"invalid JSON: {e}"}, sys.stdout)
    except Exception as e:
        json.dump({"error": f"{type(e).__name__}: {e}"}, sys.stdout)


if __name__ == "__main__":
    main()
