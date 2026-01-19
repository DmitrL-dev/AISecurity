"""
SafeCrystal - Integrity-Protected Crystal Wrapper.

Provides integrity verification for crystals:
- Content hashing
- Tamper detection
- Confidence scoring with decay
- Source traceability
"""

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .hierarchy import FileCrystal, ModuleCrystal, ProjectCrystal, Primitive

logger = logging.getLogger("rlm_crystal.safe")


@dataclass
class IntegrityRecord:
    """Record of crystal integrity check."""
    crystal_id: str
    content_hash: str
    checked_at: str
    is_valid: bool
    primitives_count: int
    confidence_score: float


class SafeCrystal:
    """
    Integrity wrapper for crystals.
    
    Provides:
    - Hash-based integrity verification
    - Confidence decay over time
    - Tamper detection
    - Full source traceability
    """
    
    # Confidence decay rate per day
    CONFIDENCE_DECAY_RATE = 0.01
    
    def __init__(self, crystal: FileCrystal):
        """
        Wrap a crystal with safety features.
        
        Args:
            crystal: The crystal to protect
        """
        self.crystal = crystal
        self.created_at = datetime.now()
        self.last_verified = datetime.now()
        
        # Calculate initial integrity hash
        self._original_hash = self._calculate_hash()
        self._primitive_hashes: Dict[str, str] = {}
        self._update_primitive_hashes()
    
    def _calculate_hash(self) -> str:
        """Calculate hash of crystal content."""
        content = f"{self.crystal.path}:{self.crystal.name}:{len(self.crystal.primitives)}"
        for p in self.crystal.primitives:
            content += f":{p.ptype}:{p.name}:{p.source_line}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _update_primitive_hashes(self):
        """Update hashes for individual primitives."""
        for p in self.crystal.primitives:
            key = f"{p.ptype}:{p.name}:{p.source_line}"
            content = f"{p.value}:{p.confidence}"
            self._primitive_hashes[key] = hashlib.md5(content.encode()).hexdigest()[:8]
    
    def verify_integrity(self) -> IntegrityRecord:
        """
        Verify crystal integrity.
        
        Returns:
            IntegrityRecord with verification results
        """
        current_hash = self._calculate_hash()
        is_valid = current_hash == self._original_hash
        
        self.last_verified = datetime.now()
        
        record = IntegrityRecord(
            crystal_id=f"{self.crystal.path}:{self.crystal.name}",
            content_hash=current_hash,
            checked_at=self.last_verified.isoformat(),
            is_valid=is_valid,
            primitives_count=len(self.crystal.primitives),
            confidence_score=self.get_confidence(),
        )
        
        if not is_valid:
            logger.warning(f"Integrity violation detected for {self.crystal.name}")
        
        return record
    
    def get_confidence(self) -> float:
        """
        Get current confidence score with time decay.
        
        Returns:
            Confidence score 0.0-1.0
        """
        if not self.crystal.primitives:
            return 0.0
        
        # Base confidence from primitives
        base_confidence = sum(p.confidence for p in self.crystal.primitives) / len(self.crystal.primitives)
        
        # Apply time decay
        days_since_created = (datetime.now() - self.created_at).days
        decay = 1.0 - (days_since_created * self.CONFIDENCE_DECAY_RATE)
        decay = max(0.5, decay)  # Minimum 50% confidence
        
        return base_confidence * decay
    
    def get_low_confidence_primitives(self, threshold: float = 0.7) -> List[Primitive]:
        """Get primitives with confidence below threshold."""
        return [p for p in self.crystal.primitives if p.confidence < threshold]
    
    def trace_primitive(self, primitive: Primitive) -> Dict[str, Any]:
        """
        Get full traceability info for a primitive.
        
        Returns:
            Dict with source file, line, hash, and context
        """
        key = f"{primitive.ptype}:{primitive.name}:{primitive.source_line}"
        return {
            "primitive": primitive.name,
            "type": primitive.ptype,
            "source_file": primitive.source_file,
            "source_line": primitive.source_line,
            "confidence": primitive.confidence,
            "hash": self._primitive_hashes.get(key, "unknown"),
            "class_context": primitive.metadata.get("class_context"),
            "crystal": self.crystal.name,
            "crystal_hash": self._original_hash,
        }
    
    def refresh(self, new_content: str = None):
        """
        Refresh the crystal and update integrity.
        
        Args:
            new_content: Optional new content to re-extract
        """
        self._original_hash = self._calculate_hash()
        self._update_primitive_hashes()
        self.last_verified = datetime.now()
        logger.info(f"SafeCrystal refreshed: {self.crystal.name}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "crystal": self.crystal.to_dict(),
            "original_hash": self._original_hash,
            "created_at": self.created_at.isoformat(),
            "last_verified": self.last_verified.isoformat(),
            "confidence": self.get_confidence(),
            "primitives_count": len(self.crystal.primitives),
        }


def wrap_crystal(crystal: FileCrystal) -> SafeCrystal:
    """Convenience function to wrap a crystal."""
    return SafeCrystal(crystal)
