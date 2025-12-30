"""
Hook Specifications — pluggy-based hook system for SENTINEL.

Defines all extension points that plugins can implement.
"""

try:
    import pluggy
    hookspec = pluggy.HookspecMarker("sentinel")
    hookimpl = pluggy.HookimplMarker("sentinel")
    PLUGGY_AVAILABLE = True
except ImportError:
    # Fallback if pluggy not installed
    PLUGGY_AVAILABLE = False
    
    def hookspec(func):
        """Dummy hookspec marker."""
        func._sentinel_hookspec = True
        return func
    
    def hookimpl(func=None, **kwargs):
        """Dummy hookimpl marker."""
        def decorator(f):
            f._sentinel_hookimpl = True
            return f
        return decorator(func) if func else decorator

from typing import List, Optional, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from sentinel.core.context import AnalysisContext
    from sentinel.core.engine import BaseEngine, EngineResult
    from sentinel.core.finding import Finding


class SentinelHookSpec:
    """
    Hook specifications for SENTINEL plugins.
    
    Plugins implement these hooks to extend SENTINEL functionality.
    All hooks are optional - implement only what you need.
    
    Lifecycle:
        1. sentinel_configure - modify configuration
        2. sentinel_register_engines - add custom engines
        3. sentinel_before_analysis - preprocess context
        4. [engine analysis happens]
        5. sentinel_on_finding - process each finding
        6. sentinel_after_analysis - postprocess results
    """
    
    @hookspec
    def sentinel_configure(self, config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Modify configuration before analysis.
        
        Args:
            config: Current configuration dict
            
        Returns:
            Modified config or None to keep unchanged
        """
        pass
    
    @hookspec
    def sentinel_register_engines(self) -> Optional[List[type]]:
        """
        Register custom engine classes.
        
        Returns:
            List of BaseEngine subclasses to register
            
        Example:
            def sentinel_register_engines(self):
                return [MyCustomEngine, AnotherEngine]
        """
        pass
    
    @hookspec
    def sentinel_register_rules(self) -> Optional[List[Dict[str, Any]]]:
        """
        Register custom rules (YAML format).
        
        Returns:
            List of rule dictionaries
            
        Example:
            def sentinel_register_rules(self):
                return [{
                    "id": "custom-001",
                    "pattern": "bad_word",
                    "severity": "high"
                }]
        """
        pass
    
    @hookspec
    def sentinel_before_analysis(
        self, 
        context: "AnalysisContext"
    ) -> Optional["AnalysisContext"]:
        """
        Called before analysis begins.
        
        Can modify or replace the context.
        
        Args:
            context: AnalysisContext to be analyzed
            
        Returns:
            Modified context or None to keep unchanged
        """
        pass
    
    @hookspec
    def sentinel_after_analysis(
        self,
        context: "AnalysisContext",
        results: List["EngineResult"]
    ) -> Optional[List["EngineResult"]]:
        """
        Called after all engines complete.
        
        Can modify, filter, or add to results.
        
        Args:
            context: Original context
            results: List of engine results
            
        Returns:
            Modified results or None to keep unchanged
        """
        pass
    
    @hookspec
    def sentinel_on_finding(
        self, 
        finding: "Finding"
    ) -> Optional["Finding"]:
        """
        Called for each finding.
        
        Can modify finding or return None to drop it.
        
        Args:
            finding: Finding to process
            
        Returns:
            Modified finding, None to drop, or unchanged
        """
        pass
    
    @hookspec
    def sentinel_on_threat(
        self,
        context: "AnalysisContext",
        results: List["EngineResult"]
    ) -> None:
        """
        Called when high-risk threat is detected.
        
        Use for alerting, logging, or blocking actions.
        
        Args:
            context: Analysis context
            results: Results containing threat
        """
        pass
    
    @hookspec
    def sentinel_format_output(
        self,
        results: List["EngineResult"],
        format: str
    ) -> Optional[str]:
        """
        Custom output formatter.
        
        Args:
            results: Analysis results
            format: Requested format (json, sarif, text, etc.)
            
        Returns:
            Formatted string or None for default formatting
        """
        pass
