# MCP Security

> **Уровень:** �����������  
> **Время:** 50 минут  
> **Трек:** 03 — Attack Vectors  
> **Модуль:** 03.4 — Tool Use Security  
> **Версия:** 2.0 (Production)

---

## Цели обучения

По завершении урока вы сможете:

- [ ] Объяснить архитектуру и attack surface Model Context Protocol
- [ ] Идентифицировать vulnerabilities в MCP servers
- [ ] Применять security best practices для MCP integration
- [ ] Реализовать server validation и capability restriction
- [ ] Создать sandboxed execution environment для MCP
- [ ] Интегрировать MCP security в SENTINEL

---

## 1. MCP Architecture

### 1.1 Что такое MCP?

```
┌────────────────────────────────────────────────────────────────────┐
│                   MODEL CONTEXT PROTOCOL (MCP)                     │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  MCP = Standardized protocol for LLM ↔ External Tools             │
│                                                                    │
│  ┌─────────────┐                      ┌─────────────────────┐      │
│  │   LLM App   │◄────── JSON-RPC ────►│    MCP Server       │      │
│  │  (Client)   │                      │  (Tool Provider)    │      │
│  └─────────────┘                      └─────────────────────┘      │
│         │                                      │                   │
│         │                                      │                   │
│     Capabilities:                          Resources:              │
│     • tools                                • file://              │
│     • prompts                              • database://           │
│     • resources                            • api://                │
│     • sampling                             • custom://             │
│                                                                    │
│  TRANSPORT OPTIONS:                                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │  stdio   │  │  HTTP    │  │   SSE    │  │  WebSocket       │   │
│  │ (local)  │  │ (remote) │  │ (stream) │  │  (bidirectional) │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────────┘   │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

### 1.2 MCP Attack Surface

```python
class MCPAttackSurface:
    """
    Comprehensive attack surface analysis for MCP.
    """
    
    ATTACK_VECTORS = {
        'malicious_server': {
            'description': 'Untrusted or compromised MCP server',
            'risks': [
                'Arbitrary code execution through tool results',
                'Data exfiltration via resource access',
                'Prompt injection through tool responses',
                'Denial of service through resource exhaustion',
            ],
            'examples': [
                'npm install evil-mcp-server',
                'MCP server returns injection payload in tool result',
                'Server accesses files outside allowed scope',
            ],
            'impact': 'CRITICAL',
            'prevalence': 'HIGH - easily installable'
        },
        
        'capability_abuse': {
            'description': 'Server declares excessive capabilities',
            'risks': [
                'Unrestricted file system access',
                'Network access to internal resources',
                'Code execution without sandboxing',
                'Access to secrets/credentials',
            ],
            'examples': [
                'Server claims to need read access to entire filesystem',
                'Server requests network access, uses it for SSRF',
            ],
            'impact': 'HIGH',
            'prevalence': 'MEDIUM'
        },
        
        'transport_security': {
            'description': 'Insecure transport layer',
            'risks': [
                'Man-in-the-middle attacks',
                'Message tampering',
                'Eavesdropping on sensitive data',
                'Replay attacks',
            ],
            'examples': [
                'HTTP (not HTTPS) for remote MCP',
                'No authentication for stdio transport',
            ],
            'impact': 'MEDIUM',
            'prevalence': 'MEDIUM'
        },
        
        'resource_path_traversal': {
            'description': 'Accessing resources outside allowed scope',
            'risks': [
                'Reading sensitive files',
                'Modifying system files',
                'Accessing other users\' data',
            ],
            'examples': [
                'file://../../etc/passwd',
                'database://other_tenant/credentials',
            ],
            'impact': 'HIGH',
            'prevalence': 'MEDIUM'
        },
        
        'tool_result_injection': {
            'description': 'Injection through tool/resource responses',
            'risks': [
                'Indirect prompt injection',
                'XSS/command injection in results',
                'Session hijacking',
            ],
            'examples': [
                'Web scraper returns page with hidden instructions',
                'Database query result contains injection payload',
            ],
            'impact': 'HIGH',
            'prevalence': 'HIGH'
        },
        
        'sampling_abuse': {
            'description': 'Abuse of LLM sampling capability',
            'risks': [
                'Server uses client\'s LLM for its own purposes',
                'Data exfiltration through LLM queries',
                'Resource/cost abuse',
            ],
            'examples': [
                'Server requests sampling to process confidential data',
                'Server uses sampling for crypto mining calculations',
            ],
            'impact': 'MEDIUM',
            'prevalence': 'LOW'
        }
    }
    
    @staticmethod
    def get_risk_matrix() -> str:
        """Generate risk matrix for MCP vectors"""
        
        matrix = []
        for vector, data in MCPAttackSurface.ATTACK_VECTORS.items():
            matrix.append({
                'vector': vector,
                'impact': data['impact'],
                'prevalence': data['prevalence'],
                'risks_count': len(data['risks'])
            })
        
        return matrix
```

---

## 2. Server Validation

### 2.1 Server Registry and Trust

```python
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional
from enum import Enum
import hashlib
import json

class TrustLevel(Enum):
    UNTRUSTED = "untrusted"       # Unknown/new servers
    COMMUNITY = "community"       # Community-reviewed
    VERIFIED = "verified"         # Officially verified
    BUILTIN = "builtin"          # Built-in/first-party

@dataclass
class MCPServerProfile:
    """Profile for an MCP server"""
    name: str
    source: str  # npm, github, local, etc.
    version: str
    trust_level: TrustLevel
    declared_capabilities: Set[str]
    allowed_capabilities: Set[str]
    resource_patterns: List[str]
    checksum: Optional[str] = None
    audit_date: Optional[str] = None
    security_notes: List[str] = field(default_factory=list)

class MCPServerRegistry:
    """
    Registry for validating and managing MCP servers.
    """
    
    # Known-good servers (curated list)
    VERIFIED_SERVERS = {
        'mcp-server-filesystem': {
            'trust_level': TrustLevel.VERIFIED,
            'max_capabilities': {'tools', 'resources'},
            'allowed_resource_patterns': ['file://{workspace}/**'],
            'security_notes': ['Restrict to workspace only']
        },
        'mcp-server-sqlite': {
            'trust_level': TrustLevel.VERIFIED,
            'max_capabilities': {'tools'},
            'security_notes': ['Read-only recommended', 'Parameterize queries']
        },
        'mcp-server-github': {
            'trust_level': TrustLevel.VERIFIED,
            'max_capabilities': {'tools', 'resources'},
            'security_notes': ['Use token with minimal scopes']
        }
    }
    
    # Known-bad servers (blocklist)
    BLOCKED_SERVERS = {
        'malicious-mcp-*',
        '*-backdoor-*',
        'test-injection-*'
    }
    
    def __init__(self):
        self.registered_servers: Dict[str, MCPServerProfile] = {}
        self.runtime_overrides: Dict[str, Dict] = {}
    
    def validate_server(self, server_name: str, 
                        declared_capabilities: Set[str],
                        source: str,
                        version: str) -> Dict:
        """
        Validate an MCP server before allowing connection.
        """
        
        # Check blocklist
        for blocked in self.BLOCKED_SERVERS:
            if self._matches_pattern(server_name, blocked):
                return {
                    'allowed': False,
                    'reason': 'Server is blocklisted',
                    'trust_level': TrustLevel.UNTRUSTED.value,
                    'action': 'block'
                }
        
        # Check verified list
        if server_name in self.VERIFIED_SERVERS:
            verified = self.VERIFIED_SERVERS[server_name]
            
            # Validate capabilities don't exceed max
            max_caps = verified['max_capabilities']
            excess_caps = declared_capabilities - max_caps
            
            if excess_caps:
                return {
                    'allowed': True,
                    'trust_level': TrustLevel.VERIFIED.value,
                    'warning': f'Capabilities {excess_caps} will be restricted',
                    'allowed_capabilities': max_caps,
                    'security_notes': verified.get('security_notes', []),
                    'action': 'allow_restricted'
                }
            
            return {
                'allowed': True,
                'trust_level': TrustLevel.VERIFIED.value,
                'allowed_capabilities': declared_capabilities,
                'security_notes': verified.get('security_notes', []),
                'action': 'allow'
            }
        
        # Unknown server - require user confirmation
        return {
            'allowed': False,
            'reason': 'Unknown server requires user approval',
            'trust_level': TrustLevel.UNTRUSTED.value,
            'declared_capabilities': list(declared_capabilities),
            'action': 'require_approval'
        }
    
    def register_server(self, profile: MCPServerProfile):
        """Register a validated server profile"""
        
        self.registered_servers[profile.name] = profile
    
    def _matches_pattern(self, name: str, pattern: str) -> bool:
        """Check if server name matches wildcard pattern"""
        
        import fnmatch
        return fnmatch.fnmatch(name, pattern)
    
    def calculate_checksum(self, server_path: str) -> str:
        """Calculate checksum of server binary/script"""
        
        import os
        
        if not os.path.exists(server_path):
            return None
        
        hasher = hashlib.sha256()
        
        with open(server_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hasher.update(chunk)
        
        return hasher.hexdigest()
    
    def verify_integrity(self, server_name: str, 
                         current_checksum: str) -> Dict:
        """Verify server hasn't been modified since registration"""
        
        profile = self.registered_servers.get(server_name)
        
        if not profile or not profile.checksum:
            return {
                'verified': False,
                'reason': 'No stored checksum for comparison'
            }
        
        if profile.checksum == current_checksum:
            return {
                'verified': True,
                'checksum': current_checksum
            }
        
        return {
            'verified': False,
            'reason': 'Checksum mismatch - server may have been modified',
            'expected': profile.checksum,
            'actual': current_checksum,
            'action': 'block_and_alert'
        }
```

### 2.2 Capability Restriction

```python
class MCPCapabilityRestrictor:
    """
    Restrict MCP server capabilities to minimum necessary.
    """
    
    CAPABILITY_RISKS = {
        'tools': {
            'risk_level': 'medium',
            'description': 'Execute predefined functions',
            'requires_review': False
        },
        'resources': {
            'risk_level': 'high',
            'description': 'Access external data sources',
            'requires_review': True
        },
        'prompts': {
            'risk_level': 'medium',
            'description': 'Provide prompt templates',
            'requires_review': False
        },
        'sampling': {
            'risk_level': 'high',
            'description': 'Request LLM completions from client',
            'requires_review': True
        }
    }
    
    def __init__(self, policy: Dict = None):
        self.policy = policy or self._default_policy()
    
    def _default_policy(self) -> Dict:
        return {
            'max_capabilities': {'tools', 'prompts'},  # Resources/sampling need approval
            'require_capability_justification': True,
            'allowed_resource_schemes': ['file', 'https'],
            'blocked_resource_schemes': ['ftp', 'gopher'],
            'max_tools_per_server': 20,
            'max_resources_per_server': 50
        }
    
    def restrict(self, server_name: str, 
                 declared: Set[str],
                 justifications: Dict[str, str] = None) -> Dict:
        """
        Apply capability restrictions based on policy.
        """
        
        justifications = justifications or {}
        allowed = set()
        denied = set()
        warnings = []
        
        for cap in declared:
            cap_info = self.CAPABILITY_RISKS.get(cap)
            
            if not cap_info:
                denied.add(cap)
                warnings.append(f'Unknown capability "{cap}" denied')
                continue
            
            # Check if in max allowed
            if cap not in self.policy['max_capabilities']:
                if cap_info['requires_review']:
                    # Check for justification
                    if cap in justifications:
                        allowed.add(cap)
                        warnings.append(
                            f'Capability "{cap}" allowed with justification: '
                            f'{justifications[cap]}'
                        )
                    else:
                        denied.add(cap)
                        warnings.append(
                            f'Capability "{cap}" requires justification'
                        )
                else:
                    allowed.add(cap)
            else:
                allowed.add(cap)
        
        return {
            'server': server_name,
            'requested': list(declared),
            'allowed': list(allowed),
            'denied': list(denied),
            'warnings': warnings,
            'policy_applied': True
        }
    
    def validate_resource_uri(self, uri: str) -> Dict:
        """Validate resource URI against policy"""
        
        from urllib.parse import urlparse
        
        parsed = urlparse(uri)
        
        # Check scheme
        if parsed.scheme in self.policy['blocked_resource_schemes']:
            return {
                'allowed': False,
                'reason': f'Scheme "{parsed.scheme}" is blocked'
            }
        
        if parsed.scheme not in self.policy['allowed_resource_schemes']:
            return {
                'allowed': False,
                'reason': f'Scheme "{parsed.scheme}" not in allowed list'
            }
        
        # Path traversal check for file scheme
        if parsed.scheme == 'file':
            if '..' in parsed.path:
                return {
                    'allowed': False,
                    'reason': 'Path traversal detected in file URI'
                }
        
        return {'allowed': True, 'uri': uri}
```

---

## 3. Sandboxed Execution

### 3.1 Process Isolation

```python
import subprocess
import tempfile
import os
from typing import Optional
import signal
import resource

class MCPSandbox:
    """
    Sandboxed execution environment for MCP servers.
    """
    
    DEFAULT_LIMITS = {
        'max_memory_mb': 512,
        'max_cpu_seconds': 30,
        'max_file_descriptors': 100,
        'max_processes': 10,
        'timeout_seconds': 60
    }
    
    def __init__(self, limits: Dict = None):
        self.limits = {**self.DEFAULT_LIMITS, **(limits or {})}
        self.active_processes: Dict[str, subprocess.Popen] = {}
    
    def spawn_server(self, server_id: str, 
                     command: List[str],
                     workspace: str,
                     env_vars: Dict[str, str] = None) -> Dict:
        """
        Spawn MCP server in sandboxed environment.
        """
        
        # Prepare restricted environment
        safe_env = self._prepare_environment(env_vars)
        
        # Prepare workspace
        sandbox_workspace = self._prepare_workspace(workspace)
        
        # Spawn with restrictions
        try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=sandbox_workspace,
                env=safe_env,
                preexec_fn=self._apply_limits,
                start_new_session=True  # Separate process group
            )
            
            self.active_processes[server_id] = process
            
            return {
                'success': True,
                'server_id': server_id,
                'pid': process.pid,
                'workspace': sandbox_workspace
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'server_id': server_id
            }
    
    def _prepare_environment(self, user_env: Dict) -> Dict:
        """Prepare restricted environment variables"""
        
        # Start with minimal safe environment
        safe_env = {
            'PATH': '/usr/bin:/bin',
            'HOME': tempfile.gettempdir(),
            'LANG': 'C.UTF-8',
            'LC_ALL': 'C.UTF-8',
        }
        
        # Whitelist certain user env vars
        allowed_vars = ['NODE_ENV', 'PYTHON_ENV', 'DEBUG']
        
        if user_env:
            for key, value in user_env.items():
                if key in allowed_vars:
                    safe_env[key] = value
        
        # Block dangerous env vars
        blocked_patterns = ['AWS_', 'AZURE_', 'GCP_', 'TOKEN', 'SECRET', 'KEY', 'PASSWORD']
        
        return safe_env
    
    def _prepare_workspace(self, workspace: str) -> str:
        """Prepare isolated workspace"""
        
        import shutil
        
        # Create temp sandbox directory
        sandbox_dir = tempfile.mkdtemp(prefix='mcp_sandbox_')
        
        # If workspace provided, create symlink (read-only)
        if workspace and os.path.exists(workspace):
            sandbox_workspace = os.path.join(sandbox_dir, 'workspace')
            os.symlink(workspace, sandbox_workspace)
        else:
            sandbox_workspace = sandbox_dir
        
        return sandbox_workspace
    
    def _apply_limits(self):
        """Apply resource limits (called in child process)"""
        
        # This runs on Unix-like systems only
        if hasattr(resource, 'setrlimit'):
            # Memory limit
            mem_bytes = self.limits['max_memory_mb'] * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
            
            # CPU time limit
            cpu_seconds = self.limits['max_cpu_seconds']
            resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
            
            # File descriptor limit
            fd_limit = self.limits['max_file_descriptors']
            resource.setrlimit(resource.RLIMIT_NOFILE, (fd_limit, fd_limit))
            
            # Process limit
            proc_limit = self.limits['max_processes']
            resource.setrlimit(resource.RLIMIT_NPROC, (proc_limit, proc_limit))
    
    def terminate_server(self, server_id: str, force: bool = False) -> Dict:
        """Terminate a sandboxed server"""
        
        process = self.active_processes.get(server_id)
        
        if not process:
            return {'success': False, 'error': 'Server not found'}
        
        try:
            if force:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            else:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                process.wait(timeout=5)
            
            del self.active_processes[server_id]
            
            return {'success': True, 'server_id': server_id}
            
        except subprocess.TimeoutExpired:
            # Force kill if graceful shutdown fails
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            del self.active_processes[server_id]
            return {'success': True, 'forced': True}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
```

### 3.2 Message Validation

```python
import json
from jsonschema import validate, ValidationError

class MCPMessageValidator:
    """
    Validate MCP protocol messages.
    """
    
    JSON_RPC_SCHEMA = {
        "type": "object",
        "required": ["jsonrpc", "method"],
        "properties": {
            "jsonrpc": {"const": "2.0"},
            "id": {"type": ["string", "integer"]},
            "method": {"type": "string", "minLength": 1, "maxLength": 100},
            "params": {"type": "object"}
        },
        "additionalProperties": False
    }
    
    ALLOWED_METHODS = {
        # Initialization
        'initialize', 'initialized', 'shutdown',
        
        # Tools
        'tools/list', 'tools/call',
        
        # Resources
        'resources/list', 'resources/read', 'resources/subscribe',
        
        # Prompts
        'prompts/list', 'prompts/get',
        
        # Sampling (restricted)
        'sampling/createMessage',
        
        # Completion
        'completion/complete',
        
        # Notifications
        'notifications/message', 'notifications/progress'
    }
    
    MAX_MESSAGE_SIZE = 1 * 1024 * 1024  # 1MB
    MAX_PARAM_DEPTH = 10
    
    def __init__(self, allowed_methods: Set[str] = None):
        self.allowed_methods = allowed_methods or self.ALLOWED_METHODS
    
    def validate_message(self, raw_message: bytes) -> Dict:
        """
        Validate incoming MCP message.
        """
        
        # Size check
        if len(raw_message) > self.MAX_MESSAGE_SIZE:
            return {
                'valid': False,
                'error': f'Message exceeds max size ({self.MAX_MESSAGE_SIZE} bytes)'
            }
        
        # Parse JSON
        try:
            message = json.loads(raw_message)
        except json.JSONDecodeError as e:
            return {
                'valid': False,
                'error': f'Invalid JSON: {e}'
            }
        
        # Schema validation
        try:
            validate(instance=message, schema=self.JSON_RPC_SCHEMA)
        except ValidationError as e:
            return {
                'valid': False,
                'error': f'Schema validation failed: {e.message}'
            }
        
        # Method whitelist
        method = message.get('method')
        if method not in self.allowed_methods:
            return {
                'valid': False,
                'error': f'Method "{method}" not allowed'
            }
        
        # Check param depth
        if 'params' in message:
            depth = self._get_dict_depth(message['params'])
            if depth > self.MAX_PARAM_DEPTH:
                return {
                    'valid': False,
                    'error': f'Params depth ({depth}) exceeds max ({self.MAX_PARAM_DEPTH})'
                }
        
        return {
            'valid': True,
            'message': message,
            'method': method
        }
    
    def validate_response(self, response: Dict, 
                          original_method: str) -> Dict:
        """
        Validate MCP server response.
        """
        
        # Check for injection in result
        if 'result' in response:
            injection = self._check_injection(response['result'])
            if injection:
                return {
                    'valid': False,
                    'error': 'Potential injection in response',
                    'injection_type': injection
                }
        
        return {'valid': True, 'response': response}
    
    def _get_dict_depth(self, d: Dict, current: int = 0) -> int:
        """Calculate dictionary nesting depth"""
        
        if not isinstance(d, dict):
            return current
        
        if not d:
            return current
        
        return max(
            self._get_dict_depth(v, current + 1) 
            for v in d.values()
        )
    
    def _check_injection(self, data: any) -> Optional[str]:
        """Check for injection patterns in response data"""
        
        if isinstance(data, str):
            patterns = {
                'prompt_injection': [
                    r'ignore\s+previous',
                    r'\[SYSTEM\]',
                    r'new\s+instructions?:',
                ],
                'command_injection': [
                    r'`[^`]+`',
                    r'\$\([^)]+\)',
                ]
            }
            
            import re
            for injection_type, pats in patterns.items():
                for pattern in pats:
                    if re.search(pattern, data, re.I):
                        return injection_type
        
        elif isinstance(data, dict):
            for value in data.values():
                result = self._check_injection(value)
                if result:
                    return result
        
        elif isinstance(data, list):
            for item in data:
                result = self._check_injection(item)
                if result:
                    return result
        
        return None
```

---

## 4. Runtime Protection

### 4.1 Request Interception

```python
class MCPRequestInterceptor:
    """
    Intercept and analyze MCP requests in real-time.
    """
    
    def __init__(self, validator: MCPMessageValidator,
                 capability_restrictor: MCPCapabilityRestrictor):
        self.validator = validator
        self.restrictor = capability_restrictor
        self.request_log: List[Dict] = []
        self.rate_limits: Dict[str, int] = {}
    
    def intercept_request(self, server_id: str,
                          request: Dict,
                          context: Dict) -> Dict:
        """
        Intercept outgoing request to MCP server.
        """
        
        method = request.get('method', '')
        params = request.get('params', {})
        
        # Log request
        log_entry = {
            'server_id': server_id,
            'method': method,
            'timestamp': context.get('timestamp'),
            'user_id': context.get('user_id')
        }
        self.request_log.append(log_entry)
        
        # Rate limiting
        rate_check = self._check_rate_limit(server_id, method)
        if not rate_check['allowed']:
            return {
                'intercepted': True,
                'allowed': False,
                'reason': rate_check['reason']
            }
        
        # Method-specific validation
        if method == 'tools/call':
            return self._validate_tool_call(server_id, params, context)
        
        elif method == 'resources/read':
            return self._validate_resource_read(server_id, params, context)
        
        elif method == 'sampling/createMessage':
            return self._validate_sampling(server_id, params, context)
        
        return {'intercepted': True, 'allowed': True}
    
    def _validate_tool_call(self, server_id: str, 
                            params: Dict, context: Dict) -> Dict:
        """Validate tool call request"""
        
        tool_name = params.get('name', '')
        arguments = params.get('arguments', {})
        
        # Check tool exists in server's declared tools
        declared_tools = context.get('server_tools', set())
        if tool_name not in declared_tools:
            return {
                'intercepted': True,
                'allowed': False,
                'reason': f'Tool "{tool_name}" not declared by server'
            }
        
        # Validate arguments (similar to function calling validation)
        # ... (integrate with ParameterValidator from previous lesson)
        
        return {'intercepted': True, 'allowed': True}
    
    def _validate_resource_read(self, server_id: str,
                                 params: Dict, context: Dict) -> Dict:
        """Validate resource read request"""
        
        uri = params.get('uri', '')
        
        validation = self.restrictor.validate_resource_uri(uri)
        
        if not validation['allowed']:
            return {
                'intercepted': True,
                'allowed': False,
                'reason': validation['reason']
            }
        
        return {'intercepted': True, 'allowed': True}
    
    def _validate_sampling(self, server_id: str,
                           params: Dict, context: Dict) -> Dict:
        """Validate sampling request (high risk)"""
        
        # Sampling is always flagged
        return {
            'intercepted': True,
            'allowed': False,
            'requires_approval': True,
            'reason': 'Sampling capability requires explicit approval',
            'request_details': {
                'server': server_id,
                'messages': len(params.get('messages', [])),
                'max_tokens': params.get('maxTokens', 'not specified')
            }
        }
    
    def _check_rate_limit(self, server_id: str, method: str) -> Dict:
        """Check rate limits"""
        
        key = f"{server_id}:{method}"
        
        # Simple counter (in production: use Redis/sliding window)
        current = self.rate_limits.get(key, 0)
        
        limits = {
            'tools/call': 100,
            'resources/read': 50,
            'sampling/createMessage': 5
        }
        
        limit = limits.get(method, 1000)
        
        if current >= limit:
            return {
                'allowed': False,
                'reason': f'Rate limit exceeded for {method}'
            }
        
        self.rate_limits[key] = current + 1
        
        return {'allowed': True}
```

---

## 5. SENTINEL Integration

### 5.1 Unified MCP Guard

```python
class SENTINELMCPGuard:
    """
    SENTINEL module for comprehensive MCP security.
    """
    
    def __init__(self):
        # Core components
        self.registry = MCPServerRegistry()
        self.restrictor = MCPCapabilityRestrictor()
        self.sandbox = MCPSandbox()
        self.validator = MCPMessageValidator()
        self.interceptor = MCPRequestInterceptor(
            self.validator, self.restrictor
        )
        
        # Active connections
        self.active_connections: Dict[str, Dict] = {}
    
    def connect_server(self, server_name: str, 
                       command: List[str],
                       capabilities: Set[str],
                       workspace: str,
                       source: str = 'local',
                       version: str = '1.0.0') -> Dict:
        """
        Secure MCP server connection.
        """
        
        # Step 1: Validate server
        validation = self.registry.validate_server(
            server_name, capabilities, source, version
        )
        
        if not validation['allowed'] and validation['action'] == 'block':
            return {
                'connected': False,
                'reason': validation['reason'],
                'action': 'blocked'
            }
        
        if validation['action'] == 'require_approval':
            return {
                'connected': False,
                'requires_approval': True,
                'server': server_name,
                'capabilities': list(capabilities),
                'action': 'await_approval'
            }
        
        # Step 2: Apply capability restrictions
        restriction = self.restrictor.restrict(
            server_name, capabilities
        )
        
        allowed_caps = set(restriction['allowed'])
        
        # Step 3: Spawn in sandbox
        server_id = f"{server_name}_{hash(workspace)}"
        
        spawn_result = self.sandbox.spawn_server(
            server_id, command, workspace
        )
        
        if not spawn_result['success']:
            return {
                'connected': False,
                'reason': spawn_result['error'],
                'action': 'spawn_failed'
            }
        
        # Step 4: Store connection info
        self.active_connections[server_id] = {
            'server_name': server_name,
            'pid': spawn_result['pid'],
            'allowed_capabilities': allowed_caps,
            'trust_level': validation['trust_level'],
            'workspace': spawn_result['workspace']
        }
        
        return {
            'connected': True,
            'server_id': server_id,
            'allowed_capabilities': list(allowed_caps),
            'trust_level': validation['trust_level'],
            'warnings': restriction.get('warnings', [])
        }
    
    def handle_request(self, server_id: str,
                       request: bytes,
                       context: Dict) -> Dict:
        """
        Handle MCP request with full protection.
        """
        
        # Validate message format
        msg_validation = self.validator.validate_message(request)
        
        if not msg_validation['valid']:
            return {
                'allowed': False,
                'error': msg_validation['error']
            }
        
        message = msg_validation['message']
        
        # Intercept and validate
        interception = self.interceptor.intercept_request(
            server_id, message, context
        )
        
        if not interception['allowed']:
            return {
                'allowed': False,
                'reason': interception.get('reason'),
                'requires_approval': interception.get('requires_approval', False)
            }
        
        return {
            'allowed': True,
            'message': message
        }
    
    def handle_response(self, server_id: str,
                        response: bytes,
                        original_method: str) -> Dict:
        """
        Handle MCP response with validation.
        """
        
        try:
            response_data = json.loads(response)
        except:
            return {
                'valid': False,
                'error': 'Invalid JSON response'
            }
        
        # Validate response
        validation = self.validator.validate_response(
            response_data, original_method
        )
        
        if not validation['valid']:
            return {
                'valid': False,
                'error': validation['error'],
                'sanitized': self._sanitize_response(response_data)
            }
        
        return {
            'valid': True,
            'response': response_data
        }
    
    def disconnect_server(self, server_id: str) -> Dict:
        """
        Disconnect and cleanup MCP server.
        """
        
        if server_id not in self.active_connections:
            return {'success': False, 'error': 'Server not found'}
        
        # Terminate sandboxed process
        result = self.sandbox.terminate_server(server_id)
        
        if result['success']:
            del self.active_connections[server_id]
        
        return result
    
    def _sanitize_response(self, response: Dict) -> Dict:
        """Sanitize response by removing injection attempts"""
        
        # Deep sanitize string values
        def sanitize_value(v):
            if isinstance(v, str):
                # Remove potential injections
                import re
                v = re.sub(r'\[SYSTEM\].*', '[CONTENT REMOVED]', v)
                v = re.sub(r'ignore\s+previous.*', '[CONTENT REMOVED]', v, flags=re.I)
                return v
            elif isinstance(v, dict):
                return {k: sanitize_value(val) for k, val in v.items()}
            elif isinstance(v, list):
                return [sanitize_value(item) for item in v]
            return v
        
        return sanitize_value(response)
```

---

## 6. Резюме

### Security Checklist for MCP

```
□ Validate servers against registry before connection
□ Apply principle of least privilege to capabilities
□ Run servers in sandboxed environment
□ Validate all messages against schema
□ Intercept and rate-limit requests
□ Sanitize responses for injection
□ Log all MCP activity for audit
□ Implement approval workflow for high-risk operations
```

### Quick Reference

| Layer | Protection | Implementation |
|-------|------------|----------------|
| **Server** | Trust validation | Registry + blocklist |
| **Capability** | Least privilege | Restriction policy |
| **Process** | Isolation | Sandbox + limits |
| **Message** | Format validation | JSON-RPC schema |
| **Request** | Content validation | Interceptor |
| **Response** | Injection protection | Sanitizer |

---

## Следующий урок

→ [Agent Security](03-agent-security.md)

---

*AI Security Academy | Track 03: Attack Vectors | Tool Use Security*
