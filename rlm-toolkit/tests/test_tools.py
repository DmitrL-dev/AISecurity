"""Tests for tools module."""

import pytest


class TestToolsImport:
    """Test tools can be imported."""
    
    def test_import_tool_base(self):
        from rlm_toolkit.tools import Tool
        assert Tool is not None
    
    def test_import_serpapi(self):
        from rlm_toolkit.tools import SerpAPITool
        assert SerpAPITool is not None
    
    def test_import_tavily(self):
        from rlm_toolkit.tools import TavilyTool
        assert TavilyTool is not None
    
    def test_import_ddg(self):
        from rlm_toolkit.tools import DuckDuckGoTool
        assert DuckDuckGoTool is not None
    
    def test_import_wikipedia(self):
        from rlm_toolkit.tools import WikipediaTool
        assert WikipediaTool is not None
    
    def test_import_arxiv(self):
        from rlm_toolkit.tools import ArxivTool
        assert ArxivTool is not None
    
    def test_import_python_repl(self):
        from rlm_toolkit.tools import PythonREPLTool
        assert PythonREPLTool is not None
    
    def test_import_shell(self):
        from rlm_toolkit.tools import ShellTool
        assert ShellTool is not None
    
    def test_import_requests(self):
        from rlm_toolkit.tools import RequestsTool
        assert RequestsTool is not None
    
    def test_import_sql(self):
        from rlm_toolkit.tools import SQLDatabaseTool
        assert SQLDatabaseTool is not None
    
    def test_import_calculator(self):
        from rlm_toolkit.tools import CalculatorTool
        assert CalculatorTool is not None
    
    def test_import_file_read(self):
        from rlm_toolkit.tools import FileReadTool
        assert FileReadTool is not None
    
    def test_import_registry(self):
        from rlm_toolkit.tools import ToolRegistry
        assert ToolRegistry is not None
    
    def test_import_create_tool(self):
        from rlm_toolkit.tools import create_tool
        assert create_tool is not None


class TestToolsFunction:
    """Test tools function correctly."""
    
    def test_calculator(self):
        from rlm_toolkit.tools import CalculatorTool
        
        calc = CalculatorTool()
        result = calc.run("2 + 2 * 3")
        assert result == "8"
    
    def test_calculator_math(self):
        from rlm_toolkit.tools import CalculatorTool
        
        calc = CalculatorTool()
        result = calc.run("sqrt(16)")
        assert result == "4.0"
    
    def test_shell_allowed(self):
        from rlm_toolkit.tools import ShellTool
        
        shell = ShellTool(allowed_commands=["echo"])
        result = shell.run("echo hello")
        assert "hello" in result
    
    def test_shell_blocked(self):
        from rlm_toolkit.tools import ShellTool
        
        shell = ShellTool(allowed_commands=["echo"])
        result = shell.run("rm -rf /")
        assert "not allowed" in result
    
    def test_tool_registry(self):
        from rlm_toolkit.tools import ToolRegistry, CalculatorTool
        
        registry = ToolRegistry()
        calc = CalculatorTool()
        
        registry.register(calc)
        
        assert "calculator" in registry.list_tools()
        assert registry.get("calculator") is not None
    
    def test_create_tool(self):
        from rlm_toolkit.tools import create_tool
        
        my_tool = create_tool(
            name="my_tool",
            description="A custom tool",
            func=lambda x: f"Got: {x}",
        )
        
        assert my_tool.name == "my_tool"
        result = my_tool.run("test")
        assert result == "Got: test"


class TestExtendedLoadersImport:
    """Test extended loaders can be imported."""
    
    def test_import_hubspot(self):
        from rlm_toolkit.loaders.extended import HubSpotLoader
        assert HubSpotLoader is not None
    
    def test_import_salesforce(self):
        from rlm_toolkit.loaders.extended import SalesforceLoader
        assert SalesforceLoader is not None
    
    def test_import_jira(self):
        from rlm_toolkit.loaders.extended import JiraLoader
        assert JiraLoader is not None
    
    def test_import_airtable(self):
        from rlm_toolkit.loaders.extended import AirtableLoader
        assert AirtableLoader is not None
    
    def test_import_google_docs(self):
        from rlm_toolkit.loaders.extended import GoogleDocsLoader
        assert GoogleDocsLoader is not None
    
    def test_import_discord(self):
        from rlm_toolkit.loaders.extended import DiscordLoader
        assert DiscordLoader is not None
    
    def test_import_bigquery(self):
        from rlm_toolkit.loaders.extended import BigQueryLoader
        assert BigQueryLoader is not None
    
    def test_import_arxiv_loader(self):
        from rlm_toolkit.loaders.extended import ArxivLoader
        assert ArxivLoader is not None
    
    def test_import_wikipedia_loader(self):
        from rlm_toolkit.loaders.extended import WikipediaLoader
        assert WikipediaLoader is not None
    
    def test_import_git(self):
        from rlm_toolkit.loaders.extended import GitLoader
        assert GitLoader is not None
