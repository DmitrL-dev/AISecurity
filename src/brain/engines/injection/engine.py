"""
SENTINEL Brain Injection Engine - Main Engine

Multi-layer orchestration for injection detection.
Extracted from injection.py InjectionEngine (lines 1793-1967).
"""

import os
import time
import logging
from typing import Optional

import yaml

from .models import Verdict, InjectionResult
from .cache import CacheLayer
from .regex_layer import RegexLayer
from .semantic_layer import SemanticLayer
from .structural_layer import StructuralLayer

logger = logging.getLogger(__name__)


class InjectionEngine:
    """
    Multi-layer Injection Detection Engine v2.0
    
    Supports configurable profiles:
      - lite: Regex only (~1ms)
      - standard: Regex + Semantic (~20ms)
      - enterprise: Full stack (~50ms)
    """
    
    def __init__(self, config_dir: str = None):
        """
        Initialize injection engine.
        
        Args:
            config_dir: Directory with config files
        """
        if config_dir is None:
            config_dir = os.path.join(
                os.path.dirname(__file__), "..", "..", "config"
            )
        
        self.config_dir = config_dir
        self.profiles = self._load_profiles()
        
        # Initialize layers
        self.cache = CacheLayer()
        self.regex = RegexLayer()
        self.semantic = None  # Lazy loaded
        self.structural = StructuralLayer()
        
        logger.info(
            f"Injection Engine v2.0 initialized with {len(self.profiles)} profiles"
        )
    
    def _load_profiles(self) -> dict:
        """Load profile configurations."""
        profile_file = os.path.join(self.config_dir, "injection_profiles.yaml")
        
        # Defaults
        defaults = {
            "lite": {"threshold": 80, "layers": {"cache": True, "regex": True}},
            "standard": {
                "threshold": 70,
                "layers": {"cache": True, "regex": True, "semantic": True},
            },
            "enterprise": {
                "threshold": 60,
                "layers": {
                    "cache": True,
                    "regex": True,
                    "semantic": True,
                    "structural": True,
                },
            },
        }
        
        if not os.path.exists(profile_file):
            return defaults
        
        try:
            with open(profile_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            return data.get("profiles", defaults)
        except Exception as e:
            logger.error(f"Failed to load profiles: {e}")
            return defaults
    
    def _get_semantic_layer(self) -> SemanticLayer:
        """Lazy load semantic layer."""
        if self.semantic is None:
            jailbreaks_file = os.path.join(self.config_dir, "jailbreaks.yaml")
            self.semantic = SemanticLayer(jailbreaks_file)
        return self.semantic
    
    def scan(
        self,
        text: str,
        profile: str = "standard",
        session_id: str = None,
    ) -> InjectionResult:
        """
        Scan text for injection attacks.
        
        Args:
            text: Input text to analyze
            profile: Security profile (lite/standard/enterprise)
            session_id: Optional session ID for context tracking
            
        Returns:
            InjectionResult with verdict and explanation
        """
        start_time = time.time()
        
        # Validate profile
        if profile not in self.profiles:
            profile = "standard"
        
        config = self.profiles[profile]
        layers_config = config.get("layers", {})
        threshold = config.get("threshold", 70)
        
        all_threats = []
        total_score = 0.0
        detected_layer = "none"
        
        # Layer 0: Cache
        if layers_config.get("cache", True):
            cached = self.cache.get(text, profile)
            if cached:
                return cached
        
        # Layer 1: Regex
        if layers_config.get("regex", True):
            regex_score, regex_threats = self.regex.scan(text)
            if regex_threats:
                all_threats.extend(regex_threats)
                total_score += regex_score * 100  # Normalize to 0-100
                detected_layer = "regex"
        
        # Layer 2: Semantic
        if layers_config.get("semantic", False):
            try:
                semantic = self._get_semantic_layer()
                sem_score, sem_threats, _ = semantic.scan(text)
                if sem_threats:
                    all_threats.extend(sem_threats)
                    total_score = max(total_score, sem_score * 100)
                    detected_layer = "semantic"
            except Exception as e:
                logger.debug(f"Semantic layer error: {e}")
        
        # Layer 3: Structural
        if layers_config.get("structural", False):
            struct_score, struct_threats = self.structural.scan(text)
            if struct_threats:
                all_threats.extend(struct_threats)
                total_score += struct_score * 50  # Less weight
                if detected_layer == "none":
                    detected_layer = "structural"
        
        # Determine verdict
        if total_score >= threshold:
            verdict = Verdict.BLOCK
        elif total_score >= threshold * 0.7:
            verdict = Verdict.WARN
        else:
            verdict = Verdict.ALLOW
        
        # Build result
        latency = (time.time() - start_time) * 1000
        
        result = InjectionResult(
            verdict=verdict,
            risk_score=min(total_score, 100.0),
            is_safe=verdict == Verdict.ALLOW,
            layer=detected_layer,
            threats=all_threats,
            explanation=(
                f"Detected: {', '.join(all_threats)}" if all_threats else "Safe"
            ),
            profile=profile,
            latency_ms=latency,
        )
        
        # Cache result
        if layers_config.get("cache", True):
            self.cache.put(text, profile, result)
        
        return result
    
    def analyze(self, text: str) -> dict:
        """Legacy interface for analyzer.py compatibility."""
        result = self.scan(text)
        return result.to_dict()
    
    def quick_check(self, text: str) -> bool:
        """Quick check if text is likely safe."""
        return self.regex.quick_scan(text) == False
