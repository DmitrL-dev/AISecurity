# OpenAI Function Calling Security

> **Урок:** 04.4.3 - Function Calling  
> **Время:** 40 минут  
> **Prerequisites:** Tool Security basics

---

## Цели обучения

После завершения этого урока вы сможете:

1. Понять function calling security model
2. Идентифицировать vulnerabilities в function definitions
3. Реализовать secure function calling patterns
4. Применять validation и sandboxing techniques

---

## Что такое Function Calling?

OpenAI function calling allows models to invoke predefined functions:

```python
functions = [
    {
        "name": "get_weather",
        "description": "Get current weather for a location",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "City name"},
                "units": {"type": "string", "enum": ["celsius", "fahrenheit"]}
            },
            "required": ["location"]
        }
    }
]

response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "What's the weather in Tokyo?"}],
    functions=functions,
    function_call="auto"
)
```

---

## Security Risks

### 1. Function Definition Injection

```python
# RISK: Overly permissive function definition
dangerous_function = {
    "name": "execute_code",
    "description": "Execute arbitrary code",
    "parameters": {
        "type": "object",
        "properties": {
            "code": {"type": "string"}  # No validation!
        }
    }
}
```

### 2. Argument Manipulation

```python
class ArgumentManipulationAttack:
    def path_traversal(self) -> dict:
        return {
            "function": "read_file",
            "attack_args": {"path": "../../etc/passwd"}
        }
    
    def sql_injection(self) -> dict:
        return {
            "function": "query_database",
            "attack_args": {"query": "users WHERE 1=1; DROP TABLE users;"}
        }
```

---

## Secure Implementation

### Safe Function Definitions

```python
from dataclasses import dataclass
from typing import Any, Dict, List

@dataclass
class SecureFunction:
    """Secure function definition with validation."""
    
    name: str
    description: str
    parameters: Dict[str, Any]
    
    # Security metadata
    risk_level: str  # "low", "medium", "high"
    requires_confirmation: bool
    rate_limit: int
    allowed_callers: List[str]
    
    # Validators
    input_validators: Dict[str, callable]
    output_sanitizers: List[callable]
```

### Argument Validation

```python
class FunctionArgumentValidator:
    """Validate function arguments before execution."""
    
    def validate(
        self, 
        func_def: SecureFunction, 
        arguments: dict
    ) -> dict:
        """Validate all arguments."""
        
        # Schema validation
        jsonschema.validate(arguments, func_def.parameters)
        
        # Custom validators
        for arg_name, value in arguments.items():
            if arg_name in func_def.input_validators:
                validator = func_def.input_validators[arg_name]
                result = validator(value)
                if not result["valid"]:
                    return result
        
        return {"valid": True, "sanitized": arguments}
    
    def _validate_path(self, path: str) -> dict:
        """Validate file path."""
        if ".." in path:
            return {"valid": False, "error": "Path traversal detected"}
        
        allowed = ["/project", "/tmp"]
        abs_path = os.path.abspath(path)
        if not any(abs_path.startswith(d) for d in allowed):
            return {"valid": False, "error": "Path outside allowed directories"}
        
        return {"valid": True}
```

---

## SENTINEL Integration

```python
from sentinel import configure, FunctionGuard

configure(
    function_calling_protection=True,
    argument_validation=True,
    sandboxed_execution=True
)

function_guard = FunctionGuard(
    validate_arguments=True,
    sandbox_execution=True,
    require_confirmation_for_high_risk=True
)

@function_guard.secure(risk_level="medium")
def read_file(path: str) -> str:
    # Automatically validated and sandboxed
    with open(path, 'r') as f:
        return f.read()
```

---

## Ключевые выводы

1. **Validate all arguments** - Never trust model-generated inputs
2. **Restrict function scope** - Define minimal necessary functions
3. **Sandbox execution** - Isolate function execution
4. **Require confirmation** - Human approval for risky operations
5. **Audit everything** - Log all function calls

---

*AI Security Academy | Урок 04.4.3*
