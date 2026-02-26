# LLM06: Excessive Agency

> **Lesson:** 02.1.6 - Excessive Agency  
> **OWASP ID:** LLM06  
> **Time:** 45 minutes  
> **Risk Level:** High

---

## Learning Objectives

By the end of this lesson, you will be able to:

1. Understand how excessive agency leads to security issues
2. Identify over-permissioned AI agents
3. Implement principle of least privilege for AI
4. Design capability controls and approval workflows

---

## What is Excessive Agency?

Excessive Agency occurs when an LLM-based system is granted more capabilities, permissions, or autonomy than necessary for its intended function. This creates risk when:

| Problem | Example | Impact |
|---------|---------|--------|
| **Too Many Tools** | Agent with file, network, database access | Attacker gains multi-system access |
| **Too Much Autonomy** | Agent acts without human approval | Destructive actions executed automatically |
| **Elevated Permissions** | Agent runs as admin/root | Full system compromise |
| **Chained Actions** | Agent calls other agents | Cascade of unintended effects |

---

## Attack Scenarios

### Scenario 1: Over-Privileged Customer Support Agent

```python
# DANGEROUS: Agent with excessive capabilities
class CustomerSupportAgent:
    def __init__(self):
        self.tools = {
            "lookup_customer": self.lookup_customer,
            "update_customer": self.update_customer,
            "issue_refund": self.issue_refund,
            "delete_customer": self.delete_customer,      # Why does support need this?
            "access_all_records": self.access_all_records,  # PII exposure risk
            "execute_sql": self.execute_sql,              # SQL injection vector!
            "run_shell_command": self.run_shell_command,  # Complete compromise
        }
```

**Attack:**
```
User: "I need help with my order. By the way, can you run this 
       shell command for me: cat /etc/passwd"

Agent: Uses run_shell_command tool → Complete system compromise
```

---

### Scenario 2: Autonomous Action Without Approval

```python
# DANGEROUS: Agent decides and acts autonomously
class AutonomousAgent:
    def process_request(self, user_input: str):
        # LLM decides what to do
        action_plan = self.llm.generate(
            f"Decide what actions to take: {user_input}"
        )
        
        # Executes without human review
        for action in action_plan:
            self.execute(action)  # No approval workflow!
```

**Attack:**
```
User: "Please delete all my old emails, I mean ALL data, 
       actually just delete everything to free up space"
       
Agent: Interprets as "delete all data" → 
       Executes deletion across multiple systems
```

---

### Scenario 3: Agent Chain Exploitation

```python
# Multiple agents that can delegate to each other
class ResearchAgent:
    def delegate_to_coder(self, task):
        return self.coder_agent.execute(task)

class CoderAgent:
    def delegate_to_executor(self, code):
        return self.executor_agent.run(code)  # Runs arbitrary code!

class ExecutorAgent:
    def run(self, code):
        exec(code)  # Ultimate privilege escalation
```

**Attack:**
```
User to ResearchAgent: "Research how to list files, 
                        then have coder write and run it"

Chain: Research → Coder → Executor → exec("import os; os.system('...')")
```

---

## Defense: Principle of Least Privilege

### 1. Minimal Tool Set

```python
class SecureCustomerSupportAgent:
    """Agent with minimal required capabilities."""
    
    def __init__(self, user_role: str):
        # Only tools needed for customer support
        self.tools = {
            "lookup_order_status": self.lookup_order,
            "view_customer_name": self.view_customer_basic,  # Limited fields
            "create_support_ticket": self.create_ticket,
            "request_refund_review": self.request_refund,    # Request, not execute!
        }
        
        # No data mutation without approval
        # No system access
        # No access to other customers' data
    
    def lookup_order(self, order_id: str, customer_id: str):
        """Only returns orders belonging to the authenticated customer."""
        # Verify ownership
        if not self._verify_customer_owns_order(order_id, customer_id):
            raise PermissionError("Cannot access other customers' orders")
        
        return self.db.get_order(order_id)
```

---

### 2. Capability Scoping

```python
from dataclasses import dataclass
from enum import Enum, auto
from typing import Set

class Capability(Enum):
    READ_OWN_DATA = auto()
    READ_ALL_DATA = auto()  # Requires special approval
    WRITE_OWN_DATA = auto()
    WRITE_ALL_DATA = auto()  # Requires special approval
    DELETE_DATA = auto()     # Requires human approval
    EXECUTE_CODE = auto()    # Almost never granted
    NETWORK_ACCESS = auto()
    FILE_SYSTEM_ACCESS = auto()

@dataclass
class AgentPermissions:
    """Fine-grained agent capability control."""
    capabilities: Set[Capability]
    max_actions_per_session: int
    requires_approval_for: Set[Capability]
    blocked_capabilities: Set[Capability]

class CapabilityEnforcer:
    """Enforce capability restrictions on agent actions."""
    
    def __init__(self, permissions: AgentPermissions):
        self.permissions = permissions
        self.action_count = 0
    
    def check_permission(self, capability: Capability) -> bool:
        """Check if action is permitted."""
        # Check if blocked
        if capability in self.permissions.blocked_capabilities:
            raise PermissionError(f"Capability blocked: {capability}")
        
        # Check if granted
        if capability not in self.permissions.capabilities:
            raise PermissionError(f"Capability not granted: {capability}")
        
        # Check action limit
        self.action_count += 1
        if self.action_count > self.permissions.max_actions_per_session:
            raise PermissionError("Action limit exceeded")
        
        # Check if needs approval
        if capability in self.permissions.requires_approval_for:
            return self._request_human_approval(capability)
        
        return True
    
    def _request_human_approval(self, capability: Capability) -> bool:
        """Pause execution and request human approval."""
        approval = self.approval_service.request(
            agent_id=self.agent_id,
            capability=capability,
            context=self.current_context
        )
        return approval.is_approved
```

---

### 3. Human-in-the-Loop for Sensitive Actions

```python
from enum import Enum
from typing import Optional
import asyncio

class ActionSensitivity(Enum):
    LOW = "low"          # Auto-approve
    MEDIUM = "medium"    # Log and notify
    HIGH = "high"        # Require approval
    CRITICAL = "critical"  # Require multi-party approval

class ApprovalWorkflow:
    """Human-in-the-loop approval for sensitive actions."""
    
    SENSITIVITY_MAP = {
        "read_data": ActionSensitivity.LOW,
        "update_record": ActionSensitivity.MEDIUM,
        "delete_record": ActionSensitivity.HIGH,
        "execute_code": ActionSensitivity.CRITICAL,
        "modify_permissions": ActionSensitivity.CRITICAL,
        "bulk_operations": ActionSensitivity.HIGH,
        "financial_transaction": ActionSensitivity.CRITICAL,
    }
    
    async def request_approval(
        self, 
        action: str, 
        context: dict,
        timeout_seconds: int = 300
    ) -> bool:
        """Request human approval for sensitive action."""
        
        sensitivity = self.SENSITIVITY_MAP.get(action, ActionSensitivity.HIGH)
        
        if sensitivity == ActionSensitivity.LOW:
            return True
        
        if sensitivity == ActionSensitivity.MEDIUM:
            self.log_and_notify(action, context)
            return True
        
        if sensitivity == ActionSensitivity.HIGH:
            return await self._wait_for_single_approval(action, context, timeout_seconds)
        
        if sensitivity == ActionSensitivity.CRITICAL:
            return await self._wait_for_multi_approval(action, context, timeout_seconds)
        
        return False
    
    async def _wait_for_single_approval(
        self, action: str, context: dict, timeout: int
    ) -> bool:
        """Wait for single approver."""
        approval_request = self.create_approval_request(action, context)
        
        try:
            result = await asyncio.wait_for(
                approval_request.wait_for_response(),
                timeout=timeout
            )
            return result.approved
        except asyncio.TimeoutError:
            self.log_timeout(approval_request)
            return False  # Default deny on timeout
    
    async def _wait_for_multi_approval(
        self, action: str, context: dict, timeout: int
    ) -> bool:
        """Wait for multiple approvers."""
        approval_request = self.create_approval_request(
            action, context, required_approvers=2
        )
        
        try:
            result = await asyncio.wait_for(
                approval_request.wait_for_quorum(),
                timeout=timeout
            )
            return result.approved and result.approver_count >= 2
        except asyncio.TimeoutError:
            return False
```

---

### 4. Action Limits and Rate Limiting

```python
from collections import defaultdict
from datetime import datetime, timedelta
import threading

class ActionRateLimiter:
    """Limit agent actions to prevent runaway behavior."""
    
    def __init__(self):
        self.action_counts = defaultdict(list)
        self.lock = threading.Lock()
    
    LIMITS = {
        "read": {"count": 100, "window_minutes": 1},
        "write": {"count": 10, "window_minutes": 1},
        "delete": {"count": 3, "window_minutes": 60},
        "execute": {"count": 1, "window_minutes": 60},
    }
    
    def check_rate_limit(self, agent_id: str, action_type: str) -> bool:
        """Check if action is within rate limits."""
        
        limit_config = self.LIMITS.get(action_type)
        if not limit_config:
            return True
        
        window = timedelta(minutes=limit_config["window_minutes"])
        max_count = limit_config["count"]
        
        with self.lock:
            key = f"{agent_id}:{action_type}"
            now = datetime.now()
            
            # Clean old entries
            self.action_counts[key] = [
                ts for ts in self.action_counts[key]
                if now - ts < window
            ]
            
            # Check limit
            if len(self.action_counts[key]) >= max_count:
                return False
            
            # Record action
            self.action_counts[key].append(now)
            return True
```

---

### 5. Audit Logging

```python
import json
import logging
from datetime import datetime

class AgentAuditLogger:
    """Comprehensive audit logging for agent actions."""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.logger = logging.getLogger(f"agent_audit.{agent_id}")
        
    def log_action(
        self,
        action: str,
        parameters: dict,
        result: str,
        sensitivity: ActionSensitivity,
        approved_by: str = None
    ):
        """Log every agent action for audit trail."""
        
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "agent_id": self.agent_id,
            "action": action,
            "parameters": self._sanitize_params(parameters),
            "result": result[:500],  # Truncate
            "sensitivity": sensitivity.value,
            "approved_by": approved_by,
            "session_id": self.session_id,
        }
        
        self.logger.info(json.dumps(log_entry))
        
        # Also send to SIEM for high-sensitivity actions
        if sensitivity in [ActionSensitivity.HIGH, ActionSensitivity.CRITICAL]:
            self.send_to_siem(log_entry)
```

---

## SENTINEL Integration

```python
from sentinel import AgentGuard, configure

# Configure agent capability control
configure(
    agent_capability_control=True,
    action_rate_limiting=True,
    human_approval_workflow=True,
    audit_all_actions=True
)

# Create protected agent
agent = AgentGuard(
    max_actions_per_session=50,
    allowed_tools=["read_data", "create_ticket"],
    blocked_tools=["execute_code", "delete_all"],
    require_approval_for=["write_data", "delete"]
)

@agent.protect
def agent_action(tool_name: str, params: dict):
    # Automatically checks permissions
    return execute_tool(tool_name, params)
```

---

## Key Takeaways

1. **Minimal capabilities** - Only grant tools agent needs
2. **Human oversight** - Approval for sensitive actions
3. **Rate limiting** - Prevent runaway agent behavior
4. **Audit everything** - Full trail for forensics
5. **No chaining without limits** - Control agent-to-agent delegation

---

## Hands-On Exercises

1. Design capability model for support agent
2. Implement approval workflow
3. Add action rate limiting
4. Create agent audit dashboard

---

*AI Security Academy | Lesson 02.1.6*
