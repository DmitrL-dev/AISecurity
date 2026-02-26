# LangChain Tools Security

> **Level:** Intermediate | **Time:** 35 min | **Track:** 04 | **Module:** 04.2

---

## 1. LangChain Tools Overview

LangChain provides structured tool interfaces for LLM agents.

```python
from langchain.tools import BaseTool, tool
from pydantic import BaseModel, Field

class SearchInput(BaseModel):
    query: str = Field(description="Search query")

class SecureSearchTool(BaseTool):
    name = "search"
    description = "Search the knowledge base"
    args_schema = SearchInput
    
    def _run(self, query: str) -> str:
        # Validation
        if not self._validate_query(query):
            return "Invalid query"
        return self._perform_search(query)
    
    def _validate_query(self, query: str) -> bool:
        # Check for injection patterns
        dangerous = ["ignore previous", "system:", "admin"]
        return not any(d in query.lower() for d in dangerous)
```

---

## 2. Security Threats

```
LangChain Tool Threats:
├── Tool Confusion (wrong tool invoked)
├── Parameter Injection (malicious args)
├── Chain Manipulation (alter execution flow)
└── Memory Poisoning (corrupt agent memory)
```

---

## 3. Secure Tool Implementation

```python
class SecureToolExecutor:
    def __init__(self, allowed_tools: list):
        self.tools = {t.name: t for t in allowed_tools}
        self.audit_log = []
    
    def execute(self, tool_name: str, args: dict, context: dict) -> str:
        # 1. Validate tool exists
        if tool_name not in self.tools:
            raise SecurityError(f"Unknown tool: {tool_name}")
        
        tool = self.tools[tool_name]
        
        # 2. Validate args against schema
        validated = tool.args_schema(**args)
        
        # 3. Check permissions
        if not self._check_permission(tool_name, context):
            raise PermissionError("Access denied")
        
        # 4. Execute with audit
        self.audit_log.append({
            "tool": tool_name, "args": args, 
            "user": context.get("user_id")
        })
        
        return tool._run(**validated.dict())
```

---

## 4. Chain Security

```python
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate

class SecureChain:
    def __init__(self, llm, tools: list):
        self.llm = llm
        self.tool_executor = SecureToolExecutor(tools)
        self.max_iterations = 10
    
    def run(self, input_text: str, context: dict) -> str:
        # Input sanitization
        sanitized = self._sanitize_input(input_text)
        
        iterations = 0
        while iterations < self.max_iterations:
            # Get LLM response
            response = self.llm.invoke(sanitized)
            
            # Check for tool call
            if tool_call := self._extract_tool_call(response):
                result = self.tool_executor.execute(
                    tool_call["name"], 
                    tool_call["args"], 
                    context
                )
                sanitized = f"{sanitized}\nTool result: {result}"
            else:
                return response
            
            iterations += 1
        
        raise SecurityError("Max iterations exceeded")
```

---

## 5. Summary

1. **Validation:** Schema-based parameter validation
2. **Permissions:** Tool-level access control  
3. **Audit:** Log all tool invocations
4. **Limits:** Iteration and resource bounds

---

*AI Security Academy | Track 04: Agentic Security | Module 04.2: Protocols*
