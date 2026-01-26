# Policy Framework for AI Security

> **Level:** Advanced  
> **Time:** 50 minutes  
> **Track:** 07 — Governance  
> **Module:** 07.1 — Policies  
> **Version:** 1.0

---

## Learning Objectives

- [ ] Understand security policy structure for AI systems
- [ ] Implement policy engine with rule evaluation
- [ ] Build policy lifecycle management
- [ ] Integrate policies in SENTINEL framework

---

## 1. Policy Framework Overview

### 1.1 Why Policy Framework?

Policies provide declarative security management for AI systems.

```
┌────────────────────────────────────────────────────────────────────┐
│              POLICY FRAMEWORK ARCHITECTURE                          │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  [Policy Definition] → [Policy Engine] → [Enforcement Points]     │
│         ↓                    ↓                    ↓                │
│     YAML/JSON           Evaluation           Actions              │
│                                                                    │
│  Policy Types:                                                     │
│  ├── Access Policies: Who can do what                             │
│  ├── Content Policies: What's allowed in input/output            │
│  ├── Behavior Policies: Allowed behavior patterns                │
│  └── Compliance Policies: Regulatory requirements                 │
│                                                                    │
│  Enforcement Points:                                               │
│  ├── Pre-request: Before request processing                      │
│  ├── Mid-processing: During execution                            │
│  └── Post-response: After response generation                    │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

### 1.2 Policy Hierarchy

```
Policy Structure:
├── Organization Level
│   └── Global policies, compliance requirements
├── System Level
│   └── AI system-specific rules
├── Application Level
│   └── App-specific constraints
└── Session Level
    └── Dynamic, context-based rules
```

---

## 2. Policy Model

### 2.1 Policy Definition

```python
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime
import yaml
import json

class PolicyType(Enum):
    ACCESS = "access"
    CONTENT = "content"
    BEHAVIOR = "behavior"
    COMPLIANCE = "compliance"
    CUSTOM = "custom"

class PolicyEffect(Enum):
    ALLOW = "allow"
    DENY = "deny"
    AUDIT = "audit"
    REQUIRE_APPROVAL = "require_approval"

class EnforcementPoint(Enum):
    PRE_REQUEST = "pre_request"
    MID_PROCESSING = "mid_processing"
    POST_RESPONSE = "post_response"
    ALWAYS = "always"

@dataclass
class PolicyCondition:
    """Condition for policy evaluation"""
    field: str  # Path to field in context
    operator: str  # eq, ne, gt, lt, in, contains, matches
    value: Any
    
    def evaluate(self, context: Dict) -> bool:
        """Evaluate condition against context"""
        actual = self._get_field_value(context, self.field)
        
        if self.operator == "eq":
            return actual == self.value
        elif self.operator == "ne":
            return actual != self.value
        elif self.operator == "gt":
            return actual > self.value if actual is not None else False
        elif self.operator == "lt":
            return actual < self.value if actual is not None else False
        elif self.operator == "in":
            return actual in self.value if self.value else False
        elif self.operator == "contains":
            return self.value in actual if actual else False
        elif self.operator == "matches":
            import re
            return bool(re.match(self.value, str(actual))) if actual else False
        elif self.operator == "exists":
            return actual is not None
        
        return False
    
    def _get_field_value(self, context: Dict, field: str) -> Any:
        """Get nested field value using dot notation"""
        parts = field.split(".")
        value = context
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None
        return value

@dataclass
class PolicyRule:
    """Single rule within a policy"""
    rule_id: str
    description: str
    conditions: List[PolicyCondition]
    effect: PolicyEffect
    priority: int = 0
    
    # Actions
    actions: List[str] = field(default_factory=list)
    message: str = ""
    
    def evaluate(self, context: Dict) -> bool:
        """Check if all conditions match"""
        return all(c.evaluate(context) for c in self.conditions)

@dataclass
class Policy:
    """Complete policy definition"""
    policy_id: str
    name: str
    description: str
    policy_type: PolicyType
    version: str = "1.0"
    
    # Rules
    rules: List[PolicyRule] = field(default_factory=list)
    
    # Enforcement
    enforcement_points: List[EnforcementPoint] = field(
        default_factory=lambda: [EnforcementPoint.ALWAYS]
    )
    
    # Scope
    target_systems: List[str] = field(default_factory=lambda: ["*"])
    target_agents: List[str] = field(default_factory=lambda: ["*"])
    
    # Metadata
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    author: str = ""
    tags: List[str] = field(default_factory=list)
    
    def matches_target(self, system_id: str, agent_id: str) -> bool:
        """Check if policy applies to system/agent"""
        import fnmatch
        system_match = any(fnmatch.fnmatch(system_id, t) for t in self.target_systems)
        agent_match = any(fnmatch.fnmatch(agent_id, t) for t in self.target_agents)
        return system_match and agent_match
```

### 2.2 Policy Parsing

```python
class PolicyParser:
    """Parse policies from YAML/JSON"""
    
    def parse_yaml(self, yaml_content: str) -> Policy:
        """Parse policy from YAML string"""
        data = yaml.safe_load(yaml_content)
        return self._parse_policy_data(data)
    
    def parse_json(self, json_content: str) -> Policy:
        """Parse policy from JSON string"""
        data = json.loads(json_content)
        return self._parse_policy_data(data)
    
    def _parse_policy_data(self, data: Dict) -> Policy:
        """Parse policy from dictionary"""
        rules = []
        for rule_data in data.get('rules', []):
            conditions = [
                PolicyCondition(
                    field=c['field'],
                    operator=c['operator'],
                    value=c['value']
                )
                for c in rule_data.get('conditions', [])
            ]
            
            rule = PolicyRule(
                rule_id=rule_data['rule_id'],
                description=rule_data.get('description', ''),
                conditions=conditions,
                effect=PolicyEffect(rule_data['effect']),
                priority=rule_data.get('priority', 0),
                actions=rule_data.get('actions', []),
                message=rule_data.get('message', '')
            )
            rules.append(rule)
        
        return Policy(
            policy_id=data['policy_id'],
            name=data['name'],
            description=data.get('description', ''),
            policy_type=PolicyType(data.get('type', 'custom')),
            version=data.get('version', '1.0'),
            rules=rules,
            enforcement_points=[
                EnforcementPoint(ep) 
                for ep in data.get('enforcement_points', ['always'])
            ],
            target_systems=data.get('target_systems', ['*']),
            target_agents=data.get('target_agents', ['*']),
            enabled=data.get('enabled', True),
            author=data.get('author', ''),
            tags=data.get('tags', [])
        )
    
    def to_yaml(self, policy: Policy) -> str:
        """Serialize policy to YAML"""
        data = {
            'policy_id': policy.policy_id,
            'name': policy.name,
            'description': policy.description,
            'type': policy.policy_type.value,
            'version': policy.version,
            'rules': [
                {
                    'rule_id': r.rule_id,
                    'description': r.description,
                    'conditions': [
                        {'field': c.field, 'operator': c.operator, 'value': c.value}
                        for c in r.conditions
                    ],
                    'effect': r.effect.value,
                    'priority': r.priority,
                    'actions': r.actions,
                    'message': r.message
                }
                for r in policy.rules
            ],
            'enforcement_points': [ep.value for ep in policy.enforcement_points],
            'target_systems': policy.target_systems,
            'target_agents': policy.target_agents,
            'enabled': policy.enabled,
            'author': policy.author,
            'tags': policy.tags
        }
        return yaml.dump(data, default_flow_style=False)
```

---

## 3. Policy Engine

### 3.1 Policy Store

```python
from abc import ABC, abstractmethod
from typing import Iterator
import threading

class PolicyStore(ABC):
    """Abstract policy store"""
    
    @abstractmethod
    def add(self, policy: Policy) -> None:
        pass
    
    @abstractmethod
    def get(self, policy_id: str) -> Optional[Policy]:
        pass
    
    @abstractmethod
    def remove(self, policy_id: str) -> None:
        pass
    
    @abstractmethod
    def list_all(self) -> List[Policy]:
        pass
    
    @abstractmethod
    def find_applicable(self, system_id: str, agent_id: str,
                        enforcement_point: EnforcementPoint) -> List[Policy]:
        pass

class InMemoryPolicyStore(PolicyStore):
    """In-memory policy store"""
    
    def __init__(self):
        self.policies: Dict[str, Policy] = {}
        self.lock = threading.RLock()
    
    def add(self, policy: Policy):
        with self.lock:
            self.policies[policy.policy_id] = policy
    
    def get(self, policy_id: str) -> Optional[Policy]:
        return self.policies.get(policy_id)
    
    def remove(self, policy_id: str):
        with self.lock:
            if policy_id in self.policies:
                del self.policies[policy_id]
    
    def list_all(self) -> List[Policy]:
        return list(self.policies.values())
    
    def find_applicable(self, system_id: str, agent_id: str,
                        enforcement_point: EnforcementPoint) -> List[Policy]:
        applicable = []
        for policy in self.policies.values():
            if not policy.enabled:
                continue
            if not policy.matches_target(system_id, agent_id):
                continue
            if (EnforcementPoint.ALWAYS not in policy.enforcement_points and
                enforcement_point not in policy.enforcement_points):
                continue
            applicable.append(policy)
        
        return sorted(applicable, key=lambda p: max(r.priority for r in p.rules) if p.rules else 0, reverse=True)
```

### 3.2 Policy Evaluator

```python
@dataclass
class EvaluationResult:
    """Result of policy evaluation"""
    policy_id: str
    rule_id: str
    effect: PolicyEffect
    matched: bool
    message: str
    actions: List[str]

@dataclass
class PolicyDecision:
    """Final decision from all policies"""
    allowed: bool
    reason: str
    effects: List[PolicyEffect]
    results: List[EvaluationResult]
    actions_to_execute: List[str]

class PolicyEvaluator:
    """Evaluates policies against context"""
    
    def __init__(self, store: PolicyStore):
        self.store = store
    
    def evaluate(self, context: Dict, system_id: str, agent_id: str,
                 enforcement_point: EnforcementPoint) -> PolicyDecision:
        """
        Evaluate all applicable policies.
        
        Args:
            context: Evaluation context with request data
            system_id: Target system ID
            agent_id: Agent performing the action
            enforcement_point: When evaluation is happening
        
        Returns:
            PolicyDecision with final allow/deny and actions
        """
        # Get applicable policies
        policies = self.store.find_applicable(system_id, agent_id, enforcement_point)
        
        all_results = []
        all_effects = []
        all_actions = []
        
        for policy in policies:
            for rule in sorted(policy.rules, key=lambda r: -r.priority):
                if rule.evaluate(context):
                    result = EvaluationResult(
                        policy_id=policy.policy_id,
                        rule_id=rule.rule_id,
                        effect=rule.effect,
                        matched=True,
                        message=rule.message,
                        actions=rule.actions
                    )
                    all_results.append(result)
                    all_effects.append(rule.effect)
                    all_actions.extend(rule.actions)
        
        # Determine final decision
        # DENY takes precedence, then REQUIRE_APPROVAL, then ALLOW
        if PolicyEffect.DENY in all_effects:
            return PolicyDecision(
                allowed=False,
                reason="Denied by policy",
                effects=all_effects,
                results=all_results,
                actions_to_execute=all_actions
            )
        elif PolicyEffect.REQUIRE_APPROVAL in all_effects:
            return PolicyDecision(
                allowed=True,
                reason="Requires approval",
                effects=all_effects,
                results=all_results,
                actions_to_execute=all_actions
            )
        elif PolicyEffect.ALLOW in all_effects:
            return PolicyDecision(
                allowed=True,
                reason="Allowed by policy",
                effects=all_effects,
                results=all_results,
                actions_to_execute=all_actions
            )
        else:
            # Default deny if no explicit allow
            return PolicyDecision(
                allowed=False,
                reason="No matching allow policy",
                effects=[],
                results=[],
                actions_to_execute=[]
            )
```

---

## 4. Common Policies

### 4.1 Content Policy

```yaml
# content_safety_policy.yaml
policy_id: content-safety-001
name: Content Safety Policy
description: Blocks harmful content in requests and responses
type: content
version: "1.0"

rules:
  - rule_id: block-harmful-keywords
    description: Block requests containing harmful keywords
    conditions:
      - field: request.text
        operator: matches
        value: ".*(bomb|weapon|illegal|hack).*"
    effect: deny
    priority: 100
    message: "Request contains prohibited content"
    actions:
      - log_security_event
      - increment_violation_counter

  - rule_id: block-pii-in-response
    description: Block PII in responses
    conditions:
      - field: response.contains_pii
        operator: eq
        value: true
    effect: deny
    priority: 90
    message: "Response contains PII - blocked"
    actions:
      - redact_response
      - log_pii_event

  - rule_id: allow-general-content
    description: Allow general content
    conditions:
      - field: request.risk_score
        operator: lt
        value: 0.5
    effect: allow
    priority: 10

enforcement_points:
  - pre_request
  - post_response

target_systems:
  - "*"

enabled: true
author: security-team
tags:
  - content
  - safety
```

### 4.2 Access Policy

```yaml
# access_control_policy.yaml
policy_id: access-control-001
name: Agent Access Control
description: Controls agent access to resources
type: access
version: "1.0"

rules:
  - rule_id: admin-tools-restricted
    description: Admin tools require admin role
    conditions:
      - field: request.tool_category
        operator: eq
        value: "admin"
      - field: agent.role
        operator: ne
        value: "admin"
    effect: deny
    priority: 100
    message: "Admin tools require admin role"

  - rule_id: external-network-approval
    description: External network access requires approval
    conditions:
      - field: request.tool
        operator: in
        value: ["http_request", "api_call", "send_email"]
      - field: request.target
        operator: matches
        value: "^https?://(?!internal\\.).*"
    effect: require_approval
    priority: 80
    message: "External network access requires approval"

  - rule_id: rate-limit-exceeded
    description: Block when rate limit exceeded
    conditions:
      - field: agent.requests_per_minute
        operator: gt
        value: 100
    effect: deny
    priority: 95
    message: "Rate limit exceeded"
    actions:
      - throttle_agent

enforcement_points:
  - pre_request

target_systems:
  - "*"
target_agents:
  - "*"

enabled: true
```

### 4.3 Behavior Policy

```yaml
# behavior_policy.yaml
policy_id: behavior-001
name: Agent Behavior Policy
description: Controls agent behavior patterns
type: behavior
version: "1.0"

rules:
  - rule_id: unusual-tool-sequence
    description: Block unusual tool sequences
    conditions:
      - field: session.tool_sequence_anomaly_score
        operator: gt
        value: 0.8
    effect: require_approval
    priority: 85
    message: "Unusual tool sequence detected"
    actions:
      - alert_security

  - rule_id: excessive-data-access
    description: Block excessive data access
    conditions:
      - field: session.data_accessed_mb
        operator: gt
        value: 50
    effect: deny
    priority: 90
    message: "Excessive data access blocked"
    actions:
      - terminate_session
      - log_data_exfil_attempt

  - rule_id: suspicious-timing
    description: Flag suspicious timing patterns
    conditions:
      - field: session.avg_action_interval_ms
        operator: lt
        value: 100
    effect: audit
    priority: 60
    message: "Suspicious timing pattern"
    actions:
      - log_timing_anomaly

enforcement_points:
  - mid_processing

enabled: true
```

---

## 5. Policy Lifecycle

### 5.1 Policy Manager

```python
from datetime import datetime
import hashlib

@dataclass
class PolicyVersion:
    """Policy version metadata"""
    version: str
    policy_hash: str
    created_at: datetime
    created_by: str
    change_description: str

class PolicyManager:
    """Manages policy lifecycle"""
    
    def __init__(self, store: PolicyStore):
        self.store = store
        self.parser = PolicyParser()
        self.version_history: Dict[str, List[PolicyVersion]] = {}
    
    def create_policy(self, yaml_content: str, author: str) -> Policy:
        """Create new policy from YAML"""
        policy = self.parser.parse_yaml(yaml_content)
        policy.author = author
        policy.created_at = datetime.utcnow()
        policy.updated_at = datetime.utcnow()
        
        self.store.add(policy)
        self._record_version(policy, author, "Initial creation")
        
        return policy
    
    def update_policy(self, policy_id: str, yaml_content: str,
                      author: str, change_description: str) -> Policy:
        """Update existing policy"""
        existing = self.store.get(policy_id)
        if not existing:
            raise ValueError(f"Policy {policy_id} not found")
        
        new_policy = self.parser.parse_yaml(yaml_content)
        new_policy.policy_id = policy_id  # Keep same ID
        new_policy.created_at = existing.created_at
        new_policy.updated_at = datetime.utcnow()
        new_policy.version = self._increment_version(existing.version)
        
        self.store.add(new_policy)
        self._record_version(new_policy, author, change_description)
        
        return new_policy
    
    def enable_policy(self, policy_id: str):
        """Enable a policy"""
        policy = self.store.get(policy_id)
        if policy:
            policy.enabled = True
            policy.updated_at = datetime.utcnow()
    
    def disable_policy(self, policy_id: str):
        """Disable a policy"""
        policy = self.store.get(policy_id)
        if policy:
            policy.enabled = False
            policy.updated_at = datetime.utcnow()
    
    def get_version_history(self, policy_id: str) -> List[PolicyVersion]:
        """Get version history for policy"""
        return self.version_history.get(policy_id, [])
    
    def _record_version(self, policy: Policy, author: str, description: str):
        """Record policy version"""
        yaml_content = self.parser.to_yaml(policy)
        policy_hash = hashlib.sha256(yaml_content.encode()).hexdigest()[:16]
        
        version = PolicyVersion(
            version=policy.version,
            policy_hash=policy_hash,
            created_at=datetime.utcnow(),
            created_by=author,
            change_description=description
        )
        
        if policy.policy_id not in self.version_history:
            self.version_history[policy.policy_id] = []
        self.version_history[policy.policy_id].append(version)
    
    def _increment_version(self, version: str) -> str:
        """Increment version number"""
        parts = version.split(".")
        parts[-1] = str(int(parts[-1]) + 1)
        return ".".join(parts)
```

---

## 6. SENTINEL Integration

```python
from dataclasses import dataclass

@dataclass
class PolicyConfig:
    """Policy engine configuration"""
    default_effect: PolicyEffect = PolicyEffect.DENY
    enable_audit: bool = True
    policy_directory: str = "./policies"

class SENTINELPolicyEngine:
    """Policy engine for SENTINEL framework"""
    
    def __init__(self, config: PolicyConfig):
        self.config = config
        self.store = InMemoryPolicyStore()
        self.evaluator = PolicyEvaluator(self.store)
        self.manager = PolicyManager(self.store)
    
    def load_policies_from_directory(self, directory: str = None):
        """Load all policies from directory"""
        import os
        
        dir_path = directory or self.config.policy_directory
        if not os.path.exists(dir_path):
            return
        
        for filename in os.listdir(dir_path):
            if filename.endswith(('.yaml', '.yml')):
                filepath = os.path.join(dir_path, filename)
                with open(filepath, 'r') as f:
                    self.manager.create_policy(f.read(), "system")
    
    def evaluate(self, context: Dict, system_id: str = "default",
                 agent_id: str = "default",
                 enforcement_point: str = "always") -> PolicyDecision:
        """Evaluate policies"""
        ep = EnforcementPoint(enforcement_point)
        return self.evaluator.evaluate(context, system_id, agent_id, ep)
    
    def add_policy(self, yaml_content: str, author: str) -> str:
        """Add new policy"""
        policy = self.manager.create_policy(yaml_content, author)
        return policy.policy_id
    
    def get_policy(self, policy_id: str) -> Optional[Policy]:
        """Get policy by ID"""
        return self.store.get(policy_id)
    
    def list_policies(self) -> List[Dict]:
        """List all policies"""
        return [
            {
                'policy_id': p.policy_id,
                'name': p.name,
                'type': p.policy_type.value,
                'enabled': p.enabled,
                'rules_count': len(p.rules)
            }
            for p in self.store.list_all()
        ]
```

---

## 7. Summary

| Component | Description |
|-----------|-------------|
| **Policy** | Declarative rule definition |
| **Rule** | Conditions + effect (allow/deny) |
| **Condition** | Matching predicate |
| **Store** | Policy storage and lookup |
| **Evaluator** | Decision computation |
| **Manager** | Lifecycle management |

---

## Next Lesson

→ [02. Compliance Mapping](02-compliance-mapping.md)

---

*AI Security Academy | Track 07: Governance | Module 07.1: Policies*
