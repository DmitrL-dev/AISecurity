"""Unit tests for templates module."""

import pytest
from rlm_toolkit.templates.base import PromptTemplate, TemplateRegistry, get_registry
from rlm_toolkit.templates.builtin import (
    ANALYSIS_TEMPLATE,
    SUMMARY_TEMPLATE,
    QA_TEMPLATE,
    DEFAULT_SYSTEM_PROMPT,
)


class TestPromptTemplate:
    """Tests for PromptTemplate."""
    
    def test_simple_template(self):
        """Test simple template formatting."""
        template = PromptTemplate(
            name="test",
            template="Hello, {name}!",
        )
        
        result = template.format(name="World")
        assert result == "Hello, World!"
    
    def test_multiple_variables(self):
        """Test multiple variable substitution."""
        template = PromptTemplate(
            name="greeting",
            template="{greeting}, {name}! Today is {day}.",
        )
        
        result = template.format(
            greeting="Hi",
            name="Alice",
            day="Monday",
        )
        
        assert result == "Hi, Alice! Today is Monday."
    
    def test_template_with_description(self):
        """Test template with description."""
        template = PromptTemplate(
            name="test",
            template="Hello",
            description="A greeting template",
        )
        
        assert template.description == "A greeting template"
    
    def test_missing_variable_error(self):
        """Test error on missing variable."""
        template = PromptTemplate(
            name="test",
            template="Hello, {name}!",
        )
        
        with pytest.raises(KeyError):
            template.format()  # Missing 'name'
    
    def test_auto_extract_variables(self):
        """Test auto-extraction of variable names."""
        template = PromptTemplate(
            name="test",
            template="{a} + {b} = {c}",
        )
        
        assert "a" in template.variables
        assert "b" in template.variables
        assert "c" in template.variables
    
    def test_format_safe(self):
        """Test safe format with missing vars."""
        template = PromptTemplate(
            name="test",
            template="Hello, {name}! {greeting}",
        )
        
        result = template.format_safe(name="World")
        assert "World" in result
        assert "{greeting}" in result


class TestTemplateRegistry:
    """Tests for TemplateRegistry."""
    
    def test_register_and_get(self):
        """Test registering and getting templates."""
        registry = TemplateRegistry()
        template = PromptTemplate(name="test", template="Hello")
        
        registry.register(template)
        retrieved = registry.get("test")
        
        assert retrieved.template == "Hello"
    
    def test_get_missing_returns_none(self):
        """Test getting missing template returns None."""
        registry = TemplateRegistry()
        
        result = registry.get("nonexistent")
        assert result is None
    
    def test_list_names(self):
        """Test listing registered template names."""
        registry = TemplateRegistry()
        registry.register(PromptTemplate(name="a", template="A"))
        registry.register(PromptTemplate(name="b", template="B"))
        
        names = registry.list_names()
        assert "a" in names
        assert "b" in names
    
    def test_remove_template(self):
        """Test removing template."""
        registry = TemplateRegistry()
        registry.register(PromptTemplate(name="test", template="T"))
        
        removed = registry.remove("test")
        assert removed
        assert registry.get("test") is None
    
    def test_clear(self):
        """Test clearing registry."""
        registry = TemplateRegistry()
        registry.register(PromptTemplate(name="a", template="A"))
        
        count = registry.clear()
        assert count == 1
        assert len(registry.list_names()) == 0


class TestBuiltinTemplates:
    """Tests for builtin templates."""
    
    def test_analysis_template_exists(self):
        """Test analysis template exists."""
        assert ANALYSIS_TEMPLATE is not None
        assert ANALYSIS_TEMPLATE.name == "analysis"
    
    def test_summary_template_exists(self):
        """Test summary template exists."""
        assert SUMMARY_TEMPLATE is not None
        assert SUMMARY_TEMPLATE.name == "summary"
    
    def test_qa_template_exists(self):
        """Test QA template exists."""
        assert QA_TEMPLATE is not None
        assert QA_TEMPLATE.name == "qa"
    
    def test_default_system_prompt(self):
        """Test default system prompt is defined."""
        assert DEFAULT_SYSTEM_PROMPT is not None
        assert len(DEFAULT_SYSTEM_PROMPT) > 0
    
    def test_analysis_template_format(self):
        """Test formatting analysis template."""
        result = ANALYSIS_TEMPLATE.format(
            context="Test context",
            query="What is this?",
        )
        
        assert "Test context" in result
        assert "What is this?" in result
    
    def test_summary_template_format(self):
        """Test formatting summary template."""
        result = SUMMARY_TEMPLATE.format(
            context="Long document text here...",
            max_length=500,
            style="concise",
        )
        
        assert "Long document text here" in result


class TestGetRegistry:
    """Tests for global registry function."""
    
    def test_get_registry(self):
        """Test getting global registry."""
        registry = get_registry()
        assert isinstance(registry, TemplateRegistry)
