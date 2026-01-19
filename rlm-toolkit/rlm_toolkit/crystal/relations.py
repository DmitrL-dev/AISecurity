"""
Cross-File Relations Graph.

Builds a graph of relationships between code elements across files.
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("rlm_crystal.relations")


@dataclass
class CodeNode:
    """Node in the code graph."""

    name: str
    node_type: str  # function, class, module, constant
    file: str
    line: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CodeRelation:
    """Relation between code nodes."""

    source: str
    target: str
    relation_type: str  # imports, calls, inherits, uses, contains
    file: str
    line: int
    confidence: float = 1.0


class RelationsGraph:
    """
    Cross-file code relations graph.

    Tracks:
    - Import relationships
    - Inheritance hierarchies
    - Function call graphs
    - Module dependencies

    Example:
        >>> graph = RelationsGraph()
        >>> graph.add_from_crystal(crystal)
        >>> dependents = graph.get_dependents("MyClass")
    """

    def __init__(self):
        self.nodes: Dict[str, CodeNode] = {}
        self.relations: List[CodeRelation] = []

        # Indexes for fast lookup
        self._outgoing: Dict[str, List[CodeRelation]] = defaultdict(list)
        self._incoming: Dict[str, List[CodeRelation]] = defaultdict(list)
        self._by_type: Dict[str, List[CodeRelation]] = defaultdict(list)
        self._by_file: Dict[str, List[str]] = defaultdict(list)

    def add_node(self, node: CodeNode) -> None:
        """Add a node to the graph."""
        self.nodes[node.name] = node
        self._by_file[node.file].append(node.name)

    def add_relation(self, relation: CodeRelation) -> None:
        """Add a relation to the graph."""
        self.relations.append(relation)
        self._outgoing[relation.source].append(relation)
        self._incoming[relation.target].append(relation)
        self._by_type[relation.relation_type].append(relation)

    def add_from_crystal(self, crystal) -> int:
        """Add nodes and relations from a crystal."""
        added = 0

        # Handle both object and dict formats
        if isinstance(crystal, dict):
            primitives = crystal.get("primitives", [])
            crystal_path = crystal.get("path", "")
        else:
            primitives = crystal.primitives
            crystal_path = getattr(crystal, "path", "")

        for prim in primitives:
            # Handle dict primitives
            if isinstance(prim, dict):
                ptype = prim.get("ptype", "")
                name = prim.get("name", "")
                source_file = prim.get("source_file", crystal_path)
                source_line = prim.get("source_line", 0)
                metadata = prim.get("metadata", {})
            else:
                ptype = prim.ptype
                name = prim.name
                source_file = prim.source_file
                source_line = prim.source_line
                metadata = prim.metadata or {}

            # Add nodes for functions, classes, etc.
            if ptype in ("FUNCTION", "CLASS", "METHOD", "CONSTANT"):
                self.add_node(
                    CodeNode(
                        name=name,
                        node_type=ptype.lower(),
                        file=source_file,
                        line=source_line,
                        metadata=metadata,
                    )
                )
                added += 1

            # Add relations
            elif ptype == "RELATION":
                parts = name.split("->")
                if len(parts) == 3:
                    self.add_relation(
                        CodeRelation(
                            source=parts[0],
                            target=parts[2],
                            relation_type=parts[1],
                            file=source_file,
                            line=source_line,
                        )
                    )
                    added += 1

            # Add import relations
            elif ptype == "IMPORT":
                module = metadata.get("module", "") if metadata else ""
                if module:
                    self.add_relation(
                        CodeRelation(
                            source=crystal_path,
                            target=module,
                            relation_type="imports",
                            file=source_file,
                            line=source_line,
                        )
                    )
                    added += 1

        return added

    def get_dependents(self, name: str) -> List[CodeRelation]:
        """Get all nodes that depend on this node."""
        return self._incoming.get(name, [])

    def get_dependencies(self, name: str) -> List[CodeRelation]:
        """Get all nodes this node depends on."""
        return self._outgoing.get(name, [])

    def get_inheritance_chain(self, class_name: str) -> List[str]:
        """Get inheritance chain for a class."""
        chain = [class_name]
        current = class_name

        while True:
            parents = [
                r.target
                for r in self._outgoing.get(current, [])
                if r.relation_type == "inherits"
            ]
            if not parents:
                break
            current = parents[0]
            chain.append(current)

        return chain

    def get_file_dependencies(self, file_path: str) -> Set[str]:
        """Get all files this file depends on."""
        deps = set()

        for node_name in self._by_file.get(file_path, []):
            for rel in self._outgoing.get(node_name, []):
                if rel.relation_type == "imports":
                    deps.add(rel.target)

        return deps

    def get_affected_by_change(self, changed_file: str) -> Set[str]:
        """Get all files affected if this file changes."""
        affected = set()

        # Find all nodes in this file
        file_nodes = self._by_file.get(changed_file, [])

        # Find all dependents
        for node_name in file_nodes:
            for rel in self._incoming.get(node_name, []):
                affected.add(rel.file)

        return affected

    def find_cycles(self) -> List[List[str]]:
        """Find dependency cycles."""
        cycles = []
        visited = set()
        rec_stack = set()

        def dfs(node: str, path: List[str]):
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for rel in self._outgoing.get(node, []):
                if rel.target not in visited:
                    dfs(rel.target, path)
                elif rel.target in rec_stack:
                    # Found cycle
                    cycle_start = path.index(rel.target)
                    cycles.append(path[cycle_start:] + [rel.target])

            path.pop()
            rec_stack.remove(node)

        for node in self.nodes:
            if node not in visited:
                dfs(node, [])

        return cycles

    def get_stats(self) -> Dict[str, Any]:
        """Get graph statistics."""
        return {
            "nodes": len(self.nodes),
            "relations": len(self.relations),
            "files": len(self._by_file),
            "relation_types": {
                rtype: len(rels) for rtype, rels in self._by_type.items()
            },
        }

    def to_dict(self) -> Dict[str, Any]:
        """Export graph as dictionary."""
        return {
            "nodes": [
                {
                    "name": n.name,
                    "type": n.node_type,
                    "file": n.file,
                    "line": n.line,
                }
                for n in self.nodes.values()
            ],
            "relations": [
                {
                    "source": r.source,
                    "target": r.target,
                    "type": r.relation_type,
                    "file": r.file,
                }
                for r in self.relations
            ],
        }


def build_project_graph(crystals: Dict[str, Any]) -> RelationsGraph:
    """Build relations graph from project crystals."""
    graph = RelationsGraph()

    for path, crystal in crystals.items():
        graph.add_from_crystal(crystal)

    logger.info(f"Built graph: {graph.get_stats()}")
    return graph
