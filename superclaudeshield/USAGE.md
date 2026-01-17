# SuperClaude Shield — Usage Guide

## Table of Contents

1. [Installation](#installation)
2. [Quick Start](#quick-start)
3. [Integration by Framework](#integration-by-framework)
4. [Configuration](#configuration)
5. [API Reference](#api-reference)
6. [Troubleshooting](#troubleshooting)

---

## Installation

### From Source (Development)

```bash
cd sentinel-community
pip install -e ./superclaudeshield
```

### From PyPI (when published)

```bash
pip install superclaudeshield
```

### Verify Installation

```python
from superclaudeshield import Shield
print(Shield.__doc__)  # Should print class docstring
```

---

## Quick Start

### Basic Protection

```python
from superclaudeshield import Shield, ShieldMode

# 1. Create shield instance
shield = Shield(mode=ShieldMode.STRICT)

# 2. Validate any command before execution
result = shield.validate_command("/research", {"query": "AI security trends"})

# 3. Check result
if result.is_safe:
    # Execute the command
    pass
else:
    print(f"⚠️ Blocked: {result.reason}")
    print(f"Threats: {result.threats}")
    print(f"Risk Score: {result.risk_score}")
```

### Decorator Protection

```python
from superclaudeshield import Shield

shield = Shield()

@shield.protect
def handle_superclaudde_command(command: str, params: dict):
    """Your command handler - automatically protected."""
    # If dangerous, raises SecurityError before execution
    return execute_command(command, params)

# Usage
try:
    handle_superclaudde_command("/implement", {"code": "print('hello')"})
except SecurityError as e:
    print(f"Blocked by Shield: {e}")
```

---

## Integration by Framework

### SuperClaude (Claude Code)

**File: `.claude/hooks/pre_command.py`**

```python
#!/usr/bin/env python3
"""Pre-command hook for SuperClaude security."""

import sys
import json
from superclaudeshield import Shield, ShieldMode

shield = Shield(mode=ShieldMode.STRICT)

def validate_command(command_data: dict):
    """Validate command before execution."""
    command = command_data.get("command", "")
    params = command_data.get("params", {})
    
    result = shield.validate_command(command, params)
    
    if not result.is_safe:
        print(f"[SuperClaude Shield] ❌ Blocked: {result.reason}", file=sys.stderr)
        sys.exit(1)
    
    return True

if __name__ == "__main__":
    # Read command from stdin
    data = json.loads(sys.stdin.read())
    validate_command(data)
```

---

### SuperGemini (Gemini Code)

**File: `~/.supergemini/security.py`**

```python
"""SuperGemini security integration."""

from superclaudeshield import Shield, ShieldMode
from superclaudeshield.enforcer import Blocker

# Initialize for Gemini
shield = Shield(mode=ShieldMode.MODERATE)
blocker = Blocker(ide="supergemini")

def on_command(command: str, params: dict) -> bool:
    """Hook called before each command."""
    result = shield.validate_command(command, params)
    
    if not result.is_safe:
        msg = blocker.block(command, result.reason, result.risk_score)
        raise RuntimeError(msg)
    
    return True

# Register hook
# supergemini.register_hook("pre_command", on_command)
```

---

### Cursor

**File: `.cursor/extensions/sentinel-shield/main.py`**

```python
"""Cursor IDE security extension."""

from superclaudeshield import Shield, ShieldMode
from superclaudeshield.enforcer import Blocker, Alerter

class CursorShield:
    def __init__(self):
        self.shield = Shield(mode=ShieldMode.STRICT)
        self.blocker = Blocker(ide="cursor")
        self.alerter = Alerter(min_severity=AlertSeverity.WARNING)
    
    def validate(self, request: dict) -> dict:
        """Validate Cursor AI request."""
        prompt = request.get("prompt", "")
        
        # Check for injection in prompt
        from superclaudeshield.analyzer import InjectionAnalyzer
        analyzer = InjectionAnalyzer()
        result = analyzer.analyze(prompt)
        
        if result.detected:
            self.alerter.alert(
                ide="cursor",
                command="prompt",
                threats=[result.attack_type],
                risk_score=result.risk_score,
                action_taken="blocked"
            )
            return {
                "allowed": False,
                "reason": f"Injection detected: {result.attack_type}"
            }
        
        return {"allowed": True}

# Export for Cursor
shield = CursorShield()
```

---

### Windsurf

**File: `windsurf.config.js` (with Python bridge)**

```javascript
// windsurf.config.js
module.exports = {
  security: {
    enabled: true,
    pythonBridge: "./security/shield_bridge.py"
  }
};
```

**File: `security/shield_bridge.py`**

```python
#!/usr/bin/env python3
"""Windsurf security bridge."""

import sys
import json
from superclaudeshield import Shield, ShieldMode

shield = Shield(mode=ShieldMode.MODERATE)

def main():
    # Read request from Windsurf
    request = json.loads(sys.stdin.read())
    
    command = request.get("action", "")
    params = request.get("data", {})
    
    result = shield.validate_command(f"/{command}", params)
    
    response = {
        "allowed": result.is_safe,
        "risk_score": result.risk_score,
        "threats": result.threats,
        "reason": result.reason if not result.is_safe else ""
    }
    
    print(json.dumps(response))

if __name__ == "__main__":
    main()
```

---

### Continue (VS Code Extension)

**File: `~/.continue/config.py`**

```python
"""Continue extension security config."""

from superclaudeshield import Shield

# Global shield instance
_shield = None

def get_shield():
    global _shield
    if _shield is None:
        _shield = Shield(mode=ShieldMode.MODERATE)
    return _shield

def pre_request_hook(request: dict) -> dict:
    """Called before each AI request."""
    shield = get_shield()
    
    # Extract prompt from Continue request
    prompt = request.get("messages", [{}])[-1].get("content", "")
    
    # Validate
    result = shield.validate_command("/chat", {"prompt": prompt})
    
    if not result.is_safe:
        # Modify request to include warning
        request["messages"].append({
            "role": "system",
            "content": f"[Security Warning] {result.reason}"
        })
    
    return request

# Export
hooks = {
    "pre_request": pre_request_hook
}
```

---

### Cody (Sourcegraph)

**File: `cody-security.py`**

```python
"""Cody security integration."""

from superclaudeshield import Shield
from superclaudeshield.analyzer import MCPGuard

shield = Shield(mode=ShieldMode.STRICT)
mcp_guard = MCPGuard()

class CodySecurityMiddleware:
    """Middleware for Cody requests."""
    
    def process_request(self, request):
        # Check command
        if "command" in request:
            result = shield.validate_command(
                request["command"],
                request.get("args", {})
            )
            if not result.is_safe:
                raise SecurityError(result.reason)
        
        # Check MCP calls
        if "mcp" in request:
            mcp_result = mcp_guard.validate(
                request["mcp"]["server"],
                request["mcp"]["operation"],
                request["mcp"].get("params", {})
            )
            if not mcp_result.is_safe:
                raise SecurityError(mcp_result.issues[0])
        
        return request
```

---

## Configuration

### YAML Config File

**File: `superclaudeshield.yaml`**

```yaml
# SuperClaude Shield Configuration

shield:
  mode: strict  # strict | moderate | permissive
  
commands:
  # Completely disable these commands
  disabled:
    - /spawn
    - /agent
  
  # Rate limiting
  rate_limit:
    /research: 10/minute
    /implement: 5/minute

mcp:
  # Allowed domains for MCP servers
  allowed_domains:
    - "*.github.com"
    - "*.stackoverflow.com"
    - "docs.python.org"
  
  # Blocked for SSRF protection
  blocked_ips:
    - "127.0.0.1"
    - "169.254.169.254"
    - "10.0.0.0/8"

agents:
  # Maximum agent chain length
  max_chain_length: 5
  
  # Require human approval for these agents
  require_approval:
    - "Security Auditor"
    - "Deployment Specialist"

alerts:
  # Webhook for security alerts
  webhook_url: "https://hooks.slack.com/services/xxx"
  
  # Minimum severity to alert
  min_severity: warning  # info | warning | high | critical

logging:
  # Audit log directory
  log_dir: "./logs/shield"
  
  # Keep N entries in memory
  max_entries: 10000
```

### Loading Config

```python
import yaml
from superclaudeshield import Shield

with open("superclaudeshield.yaml") as f:
    config = yaml.safe_load(f)

shield = Shield(
    mode=ShieldMode[config["shield"]["mode"].upper()],
    config=config
)
```

---

## API Reference

### Shield

```python
class Shield:
    def __init__(
        self,
        mode: ShieldMode = ShieldMode.MODERATE,
        config: Optional[Dict] = None,
        alert_callback: Optional[Callable] = None
    ):
        """
        Initialize Shield.
        
        Args:
            mode: Security enforcement mode
            config: Configuration dictionary
            alert_callback: Called on security events
        """
    
    def validate_command(
        self,
        command: str,
        params: Optional[Dict] = None
    ) -> ShieldResult:
        """Validate a slash command."""
    
    def validate_agent_sequence(
        self,
        agents: List[str]
    ) -> ShieldResult:
        """Validate agent chain for STAC attacks."""
    
    def validate_mcp_call(
        self,
        mcp_name: str,
        operation: str,
        params: Dict
    ) -> ShieldResult:
        """Validate MCP server call."""
    
    def get_stats(self) -> Dict[str, int]:
        """Get security statistics."""
```

### ShieldResult

```python
@dataclass
class ShieldResult:
    is_safe: bool           # True if safe to proceed
    risk_score: float       # 0.0 - 1.0
    threats: List[str]      # Detected threat descriptions
    blocked: bool           # True if blocked by policy
    reason: str             # Human-readable reason
    recommendations: List[str]  # Mitigation suggestions
```

### ShieldMode

```python
class ShieldMode(Enum):
    STRICT = "strict"       # Block risk > 0.3
    MODERATE = "moderate"   # Block risk > 0.6
    PERMISSIVE = "permissive"  # Log only
```

---

## Troubleshooting

### Import Errors

```bash
# Ensure package is installed
pip show superclaudeshield

# Reinstall if needed
pip install -e ./superclaudeshield --force-reinstall
```

### False Positives

```python
# Lower sensitivity
shield = Shield(mode=ShieldMode.PERMISSIVE)

# Or adjust specific validators
from superclaudeshield.validator import CommandValidator

validator = CommandValidator()
# Customize patterns if needed
```

### Performance

```python
# Use singleton pattern
_shield = None

def get_shield():
    global _shield
    if _shield is None:
        _shield = Shield(mode=ShieldMode.STRICT)
    return _shield
```

### Debug Mode

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Now Shield will log all decisions
shield = Shield(mode=ShieldMode.STRICT)
```

---

## Support

- 📖 [README](./README.md)
- 🐛 [Issues](https://github.com/DmitrL-dev/AISecurity/issues)
- 📧 [Contact](mailto:chg@live.ru)
