"""
RLM-Toolkit Crystal Module (C³ - Context Consciousness Crystal).

Provides semantic compression and knowledge structuring for large contexts.

Components:
- ProjectCrystal: Top-level crystal for entire project
- ModuleCrystal: Crystal for a module/package
- FileCrystal: Crystal for a single file
- SafeCrystal: Integrity-protected crystal wrapper
"""

from .hierarchy import ProjectCrystal, ModuleCrystal, FileCrystal, Primitive
from .extractor import HPEExtractor, PrimitiveType
from .indexer import CrystalIndexer
from .safe import SafeCrystal, IntegrityRecord, wrap_crystal

__all__ = [
    "ProjectCrystal",
    "ModuleCrystal", 
    "FileCrystal",
    "Primitive",
    "HPEExtractor",
    "PrimitiveType",
    "CrystalIndexer",
    "SafeCrystal",
    "IntegrityRecord",
    "wrap_crystal",
]

__version__ = "1.0.0"
