"""
Crystal Hierarchy for C³.

Implements the hierarchical crystal structure:
- ProjectCrystal: Contains all modules and global entities
- ModuleCrystal: Contains files in a module/package
- FileCrystal: Contains primitives from a single file
"""

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("rlm_crystal.hierarchy")


@dataclass
class Primitive:
    """A semantic primitive extracted from code."""
    ptype: str  # ENTITY, FUNCTION, CLASS, RELATION, etc.
    name: str
    value: str
    source_file: str
    source_line: int
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FileCrystal:
    """Crystal for a single file."""
    
    path: str
    name: str
    primitives: List[Primitive] = field(default_factory=list)
    token_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    content_hash: str = ""
    
    def add_primitive(self, primitive: Primitive):
        """Add a primitive to the crystal."""
        self.primitives.append(primitive)
    
    def find_by_name(self, name: str) -> List[Primitive]:
        """Find primitives by name."""
        return [p for p in self.primitives if name.lower() in p.name.lower()]
    
    def find_by_type(self, ptype: str) -> List[Primitive]:
        """Find primitives by type."""
        return [p for p in self.primitives if p.ptype == ptype]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "path": self.path,
            "name": self.name,
            "primitives": [
                {
                    "ptype": p.ptype,
                    "name": p.name,
                    "value": p.value,
                    "source_file": p.source_file,
                    "source_line": p.source_line,
                    "confidence": p.confidence,
                    "metadata": p.metadata,
                }
                for p in self.primitives
            ],
            "token_count": self.token_count,
            "created_at": self.created_at,
            "content_hash": self.content_hash,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FileCrystal":
        """Create from dictionary."""
        crystal = cls(
            path=data["path"],
            name=data["name"],
            token_count=data.get("token_count", 0),
            created_at=data.get("created_at", datetime.now().isoformat()),
            content_hash=data.get("content_hash", ""),
        )
        for p in data.get("primitives", []):
            crystal.add_primitive(Primitive(**p))
        return crystal


@dataclass
class ModuleCrystal:
    """Crystal for a module/package."""
    
    path: str
    name: str
    files: Dict[str, FileCrystal] = field(default_factory=dict)
    dependencies: Set[str] = field(default_factory=set)
    entities: Set[str] = field(default_factory=set)  # Global entities in module
    
    def add_file(self, file_crystal: FileCrystal):
        """Add a file crystal."""
        self.files[file_crystal.path] = file_crystal
        # Extract entities
        for p in file_crystal.primitives:
            if p.ptype in ("CLASS", "FUNCTION", "CONSTANT"):
                self.entities.add(p.name)
    
    def get_file(self, path: str) -> Optional[FileCrystal]:
        """Get file crystal by path."""
        return self.files.get(path)
    
    def find_across_files(self, name: str) -> List[Primitive]:
        """Find primitives across all files."""
        results = []
        for file_crystal in self.files.values():
            results.extend(file_crystal.find_by_name(name))
        return results
    
    @property
    def total_primitives(self) -> int:
        """Total number of primitives in module."""
        return sum(len(f.primitives) for f in self.files.values())
    
    @property
    def total_tokens(self) -> int:
        """Total token count in module."""
        return sum(f.token_count for f in self.files.values())


@dataclass
class ProjectCrystal:
    """Crystal for entire project."""
    
    name: str
    root_path: str
    modules: Dict[str, ModuleCrystal] = field(default_factory=dict)
    global_entities: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    cross_references: List[Dict[str, str]] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_updated: str = ""
    
    def add_module(self, module_crystal: ModuleCrystal):
        """Add a module crystal."""
        self.modules[module_crystal.name] = module_crystal
        # Update global entities
        for entity in module_crystal.entities:
            if entity not in self.global_entities:
                self.global_entities[entity] = {
                    "defined_in": [module_crystal.name],
                    "type": "unknown",
                }
            else:
                self.global_entities[entity]["defined_in"].append(module_crystal.name)
    
    def get_module(self, name: str) -> Optional[ModuleCrystal]:
        """Get module crystal by name."""
        return self.modules.get(name)
    
    def find_globally(self, name: str) -> List[Primitive]:
        """Find primitives across all modules."""
        results = []
        for module in self.modules.values():
            results.extend(module.find_across_files(name))
        return results
    
    def add_cross_reference(self, from_entity: str, to_entity: str, relation: str):
        """Add a cross-reference between entities."""
        self.cross_references.append({
            "from": from_entity,
            "to": to_entity,
            "relation": relation,
        })
    
    @property
    def stats(self) -> Dict[str, Any]:
        """Get project statistics."""
        total_files = sum(len(m.files) for m in self.modules.values())
        total_primitives = sum(m.total_primitives for m in self.modules.values())
        total_tokens = sum(m.total_tokens for m in self.modules.values())
        
        return {
            "name": self.name,
            "modules": len(self.modules),
            "files": total_files,
            "primitives": total_primitives,
            "tokens": total_tokens,
            "entities": len(self.global_entities),
            "cross_references": len(self.cross_references),
        }
    
    def update(self):
        """Update last_updated timestamp."""
        self.last_updated = datetime.now().isoformat()
