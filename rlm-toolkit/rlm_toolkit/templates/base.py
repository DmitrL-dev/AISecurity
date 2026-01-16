"""
Template Base
=============

Base classes for prompt templates.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import re


@dataclass
class PromptTemplate:
    """Prompt template with variable substitution.
    
    Example:
        >>> template = PromptTemplate(
        ...     name="greeting",
        ...     template="Hello, {name}! You are a {role}.",
        ...     variables=["name", "role"],
        ... )
        >>> prompt = template.format(name="Alice", role="developer")
        >>> print(prompt)
        Hello, Alice! You are a developer.
    
    Attributes:
        name: Template identifier
        template: Template string with {variable} placeholders
        variables: List of required variables
        description: Human-readable description
        metadata: Additional template metadata
    """
    name: str
    template: str
    variables: List[str] = field(default_factory=list)
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        # Auto-detect variables if not provided
        if not self.variables:
            self.variables = self._extract_variables()
    
    def _extract_variables(self) -> List[str]:
        """Extract variable names from template."""
        pattern = r'\{(\w+)\}'
        return list(set(re.findall(pattern, self.template)))
    
    def format(self, **kwargs) -> str:
        """Format template with provided values.
        
        Args:
            **kwargs: Variable values
        
        Returns:
            Formatted string
        
        Raises:
            KeyError: If required variable is missing
        """
        # Check for missing variables
        missing = set(self.variables) - set(kwargs.keys())
        if missing:
            raise KeyError(f"Missing template variables: {missing}")
        
        return self.template.format(**kwargs)
    
    def format_safe(self, **kwargs) -> str:
        """Format template, leaving missing variables unchanged.
        
        Args:
            **kwargs: Variable values
        
        Returns:
            Formatted string (missing vars kept as {var})
        """
        result = self.template
        for key, value in kwargs.items():
            result = result.replace(f'{{{key}}}', str(value))
        return result
    
    def validate(self, **kwargs) -> List[str]:
        """Validate provided kwargs against template.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Check missing
        missing = set(self.variables) - set(kwargs.keys())
        if missing:
            errors.append(f"Missing variables: {missing}")
        
        # Check extra (warning only)
        extra = set(kwargs.keys()) - set(self.variables)
        if extra:
            errors.append(f"Unused variables: {extra}")
        
        return errors


class TemplateRegistry:
    """Registry of prompt templates.
    
    Example:
        >>> registry = TemplateRegistry()
        >>> registry.register(my_template)
        >>> template = registry.get("my_template_name")
    """
    
    def __init__(self):
        self._templates: Dict[str, PromptTemplate] = {}
    
    def register(self, template: PromptTemplate) -> None:
        """Register a template."""
        self._templates[template.name] = template
    
    def get(self, name: str) -> Optional[PromptTemplate]:
        """Get template by name."""
        return self._templates.get(name)
    
    def list_names(self) -> List[str]:
        """List all template names."""
        return list(self._templates.keys())
    
    def list_all(self) -> List[PromptTemplate]:
        """List all templates."""
        return list(self._templates.values())
    
    def remove(self, name: str) -> bool:
        """Remove template by name."""
        if name in self._templates:
            del self._templates[name]
            return True
        return False
    
    def clear(self) -> int:
        """Clear all templates."""
        count = len(self._templates)
        self._templates.clear()
        return count


# Global registry
_global_registry = TemplateRegistry()


def get_registry() -> TemplateRegistry:
    """Get global template registry."""
    return _global_registry
