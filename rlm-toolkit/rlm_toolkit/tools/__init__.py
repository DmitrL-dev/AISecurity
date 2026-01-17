"""
Tools and Toolkits
==================

Tools for agents to interact with external services.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable
import os


class Tool(ABC):
    """Base class for tools."""
    
    name: str = ""
    description: str = ""
    
    @abstractmethod
    def run(self, input: str) -> str:
        """Run the tool with given input."""
        pass
    
    def __call__(self, input: str) -> str:
        return self.run(input)


# =============================================================================
# Search Tools
# =============================================================================

class SerpAPITool(Tool):
    """Search using SerpAPI."""
    
    name = "search"
    description = "Search the web for current information."
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("SERPAPI_API_KEY")
    
    def run(self, query: str) -> str:
        try:
            from serpapi import GoogleSearch
            
            search = GoogleSearch({
                "q": query,
                "api_key": self.api_key,
            })
            
            results = search.get_dict()
            organic = results.get("organic_results", [])[:3]
            
            output = []
            for r in organic:
                output.append(f"- {r.get('title', '')}: {r.get('snippet', '')}")
            
            return "\n".join(output) if output else "No results found."
        except ImportError:
            raise ImportError("google-search-results required")


class TavilyTool(Tool):
    """Search using Tavily AI."""
    
    name = "tavily_search"
    description = "AI-powered search for research and answers."
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("TAVILY_API_KEY")
    
    def run(self, query: str) -> str:
        try:
            from tavily import TavilyClient
            
            client = TavilyClient(api_key=self.api_key)
            response = client.search(query)
            
            results = response.get("results", [])[:3]
            output = []
            
            for r in results:
                output.append(f"- {r.get('title', '')}: {r.get('content', '')[:200]}")
            
            return "\n".join(output) if output else "No results found."
        except ImportError:
            raise ImportError("tavily-python required")


class DuckDuckGoTool(Tool):
    """Search using DuckDuckGo (no API key needed)."""
    
    name = "ddg_search"
    description = "Search the web using DuckDuckGo."
    
    def run(self, query: str) -> str:
        try:
            from duckduckgo_search import DDGS
            
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=3))
            
            output = []
            for r in results:
                output.append(f"- {r.get('title', '')}: {r.get('body', '')[:200]}")
            
            return "\n".join(output) if output else "No results found."
        except ImportError:
            raise ImportError("duckduckgo-search required")


class BraveSearchTool(Tool):
    """Search using Brave Search API."""
    
    name = "brave_search"
    description = "Search using Brave Search."
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("BRAVE_API_KEY")
    
    def run(self, query: str) -> str:
        try:
            import requests
            
            url = "https://api.search.brave.com/res/v1/web/search"
            headers = {"X-Subscription-Token": self.api_key}
            params = {"q": query}
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            
            results = response.json().get("web", {}).get("results", [])[:3]
            output = []
            
            for r in results:
                output.append(f"- {r.get('title', '')}: {r.get('description', '')[:200]}")
            
            return "\n".join(output) if output else "No results found."
        except ImportError:
            raise ImportError("requests required")


# =============================================================================
# Knowledge Tools
# =============================================================================

class WikipediaTool(Tool):
    """Search and read Wikipedia articles."""
    
    name = "wikipedia"
    description = "Search Wikipedia for information."
    
    def __init__(self, lang: str = "en"):
        self.lang = lang
    
    def run(self, query: str) -> str:
        try:
            import wikipedia
            
            wikipedia.set_lang(self.lang)
            
            try:
                summary = wikipedia.summary(query, sentences=3)
                return summary
            except wikipedia.exceptions.DisambiguationError as e:
                return f"Disambiguation: {', '.join(e.options[:5])}"
            except wikipedia.exceptions.PageError:
                return "Page not found."
        except ImportError:
            raise ImportError("wikipedia required")


class ArxivTool(Tool):
    """Search arXiv for academic papers."""
    
    name = "arxiv"
    description = "Search arXiv for research papers."
    
    def run(self, query: str) -> str:
        try:
            import arxiv
            
            search = arxiv.Search(query=query, max_results=3)
            
            output = []
            for result in search.results():
                output.append(f"- {result.title}: {result.summary[:200]}...")
            
            return "\n".join(output) if output else "No papers found."
        except ImportError:
            raise ImportError("arxiv required")


class WolframAlphaTool(Tool):
    """Query Wolfram Alpha for computational answers."""
    
    name = "wolfram"
    description = "Get computational answers from Wolfram Alpha."
    
    def __init__(self, app_id: Optional[str] = None):
        self.app_id = app_id or os.getenv("WOLFRAM_APP_ID")
    
    def run(self, query: str) -> str:
        try:
            import wolframalpha
            
            client = wolframalpha.Client(self.app_id)
            res = client.query(query)
            
            for pod in res.pods:
                if pod["@title"] == "Result":
                    return pod["subpod"]["plaintext"]
            
            return "No result found."
        except ImportError:
            raise ImportError("wolframalpha required")


# =============================================================================
# Code Tools
# =============================================================================

class PythonREPLTool(Tool):
    """Execute Python code in a sandboxed REPL."""
    
    name = "python"
    description = "Execute Python code. Use for calculations and data processing."
    
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
    
    def run(self, code: str) -> str:
        try:
            # Use RLM's SecureREPL - the ONLY safe way to execute code
            from rlm_toolkit.core.repl import SecureREPL
            
            repl = SecureREPL(timeout=self.timeout)
            result = repl.execute(code)
            return str(result.get("result", result.get("error", "No output")))
        except ImportError:
            raise ImportError(
                "SecureREPL is required for code execution. "
                "Install with: pip install rlm-toolkit[all]"
            )


class ShellTool(Tool):
    """Execute shell commands (USE WITH CAUTION)."""
    
    name = "shell"
    description = "Execute shell commands."
    
    def __init__(self, allowed_commands: Optional[List[str]] = None):
        self.allowed_commands = allowed_commands or ["ls", "pwd", "echo", "cat", "head", "tail"]
    
    def run(self, command: str) -> str:
        import subprocess
        
        # Basic security check
        cmd_name = command.split()[0] if command else ""
        if cmd_name not in self.allowed_commands:
            return f"Command '{cmd_name}' not allowed. Allowed: {self.allowed_commands}"
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.stdout or result.stderr or "No output."
        except subprocess.TimeoutExpired:
            return "Command timed out."


# =============================================================================
# Web Tools
# =============================================================================

class RequestsTool(Tool):
    """Make HTTP requests."""
    
    name = "http_request"
    description = "Make HTTP GET requests to URLs."
    
    def run(self, url: str) -> str:
        try:
            import requests
            from bs4 import BeautifulSoup
            
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            for script in soup(["script", "style"]):
                script.decompose()
            
            text = soup.get_text(separator="\n", strip=True)
            return text[:2000] + "..." if len(text) > 2000 else text
        except ImportError:
            raise ImportError("requests and beautifulsoup4 required")


class ScraperTool(Tool):
    """Scrape content from web pages."""
    
    name = "scraper"
    description = "Scrape and extract structured content from web pages."
    
    def run(self, url: str) -> str:
        try:
            import requests
            from bs4 import BeautifulSoup
            
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Extract main content
            main = soup.find("main") or soup.find("article") or soup.find("body")
            
            if main:
                for script in main(["script", "style", "nav", "footer"]):
                    script.decompose()
                text = main.get_text(separator="\n", strip=True)
            else:
                text = soup.get_text(separator="\n", strip=True)
            
            return text[:3000] + "..." if len(text) > 3000 else text
        except ImportError:
            raise ImportError("requests and beautifulsoup4 required")


# =============================================================================
# Data Tools
# =============================================================================

class SQLDatabaseTool(Tool):
    """Query SQL databases."""
    
    name = "sql"
    description = "Execute SQL queries on a database."
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
    
    def run(self, query: str) -> str:
        try:
            import sqlalchemy
            
            engine = sqlalchemy.create_engine(self.connection_string)
            
            with engine.connect() as conn:
                result = conn.execute(sqlalchemy.text(query))
                rows = result.fetchall()
                columns = result.keys()
            
            if not rows:
                return "No results."
            
            output = [" | ".join(columns)]
            for row in rows[:10]:
                output.append(" | ".join([str(v) for v in row]))
            
            return "\n".join(output)
        except ImportError:
            raise ImportError("sqlalchemy required")


class CalculatorTool(Tool):
    """Perform mathematical calculations."""
    
    name = "calculator"
    description = "Evaluate mathematical expressions."
    
    def run(self, expression: str) -> str:
        import math
        
        # Safe math evaluation
        allowed_names = {
            k: v for k, v in math.__dict__.items()
            if not k.startswith("__")
        }
        allowed_names.update({
            "abs": abs,
            "round": round,
            "min": min,
            "max": max,
            "sum": sum,
        })
        
        try:
            result = eval(expression, {"__builtins__": {}}, allowed_names)
            return str(result)
        except Exception as e:
            return f"Error: {e}"


# =============================================================================
# File Tools
# =============================================================================

class FileReadTool(Tool):
    """Read file contents."""
    
    name = "read_file"
    description = "Read the contents of a file."
    
    def __init__(self, allowed_paths: Optional[List[str]] = None):
        self.allowed_paths = allowed_paths
    
    def run(self, path: str) -> str:
        if self.allowed_paths:
            if not any(path.startswith(p) for p in self.allowed_paths):
                return f"Access denied. Allowed paths: {self.allowed_paths}"
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            return content[:5000] + "..." if len(content) > 5000 else content
        except Exception as e:
            return f"Error: {e}"


class FileWriteTool(Tool):
    """Write content to files."""
    
    name = "write_file"
    description = "Write content to a file."
    
    def __init__(self, allowed_paths: Optional[List[str]] = None):
        self.allowed_paths = allowed_paths
    
    def run(self, input: str) -> str:
        # Expected format: "path|||content"
        if "|||" not in input:
            return "Invalid format. Use: path|||content"
        
        path, content = input.split("|||", 1)
        
        if self.allowed_paths:
            if not any(path.startswith(p) for p in self.allowed_paths):
                return f"Access denied. Allowed paths: {self.allowed_paths}"
        
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Successfully wrote {len(content)} characters to {path}"
        except Exception as e:
            return f"Error: {e}"


# =============================================================================
# API Tools
# =============================================================================

class OpenAPITool(Tool):
    """Execute API calls based on OpenAPI spec."""
    
    name = "api"
    description = "Make API calls based on OpenAPI specification."
    
    def __init__(self, spec_url: str):
        self.spec_url = spec_url
        self._spec = None
    
    def _load_spec(self):
        if self._spec is None:
            import requests
            response = requests.get(self.spec_url)
            self._spec = response.json()
        return self._spec
    
    def run(self, input: str) -> str:
        # Parse input as "METHOD /path {json_body}"
        parts = input.split(" ", 2)
        method = parts[0].upper() if parts else "GET"
        path = parts[1] if len(parts) > 1 else "/"
        body = parts[2] if len(parts) > 2 else None
        
        try:
            import requests
            import json
            
            spec = self._load_spec()
            base_url = spec.get("servers", [{}])[0].get("url", "")
            
            url = base_url + path
            
            if body:
                body = json.loads(body)
            
            response = requests.request(method, url, json=body, timeout=30)
            return response.text[:2000]
        except Exception as e:
            return f"Error: {e}"


# =============================================================================
# Utility Functions
# =============================================================================

class ToolRegistry:
    """Registry for managing tools."""
    
    def __init__(self):
        self._tools: Dict[str, Tool] = {}
    
    def register(self, tool: Tool):
        """Register a tool."""
        self._tools[tool.name] = tool
    
    def get(self, name: str) -> Optional[Tool]:
        """Get a tool by name."""
        return self._tools.get(name)
    
    def list_tools(self) -> List[str]:
        """List all registered tools."""
        return list(self._tools.keys())
    
    def get_tool_descriptions(self) -> str:
        """Get descriptions of all tools."""
        lines = []
        for name, tool in self._tools.items():
            lines.append(f"- {name}: {tool.description}")
        return "\n".join(lines)


def create_tool(
    name: str,
    description: str,
    func: Callable[[str], str],
) -> Tool:
    """Create a tool from a function."""
    
    class FunctionTool(Tool):
        def run(self, input: str) -> str:
            return func(input)
    
    tool = FunctionTool()
    tool.name = name
    tool.description = description
    return tool
