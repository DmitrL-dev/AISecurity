# Agent Security

> **Уровень:** �����������  
> **Время:** 60 минут  
> **Трек:** 03 — Attack Vectors  
> **Модуль:** 03.4 — Tool Use Security  
> **Версия:** 2.0 (Production)

---

## Цели обучения

По завершении урока вы сможете:

- [ ] Объяснить unique attack surface автономных AI agents
- [ ] Реализовать scope control и goal validation
- [ ] Предотвратить agent loops и recursion attacks
- [ ] Применять rollback mechanisms для reverting actions
- [ ] Создать human-in-the-loop approval для critical decisions
- [ ] Интегрировать comprehensive agent safety в SENTINEL

---

## 1. Agent Architecture и Attack Surface

### 1.1 Анатомия AI Agent

```
┌────────────────────────────────────────────────────────────────────┐
│                    AI AGENT ARCHITECTURE                           │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                       USER GOAL                              │  │
│  │  "Book a flight to Paris for next week"                      │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                              ↓                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    PLANNING MODULE                           │  │
│  │  1. Search for flights                                       │  │
│  │  2. Compare prices                                           │  │
│  │  3. Book optimal flight                                      │  │
│  │  4. Confirm booking                                          │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                              ↓                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    EXECUTION LOOP                            │  │
│  │  ┌─────────────────────────────────────────────────────────┐ │  │
│  │  │  OBSERVE → THINK → ACT → OBSERVE → THINK → ACT → ...  │ │  │
│  │  └─────────────────────────────────────────────────────────┘ │  │
│  │                                                              │  │
│  │  TOOLS AVAILABLE:                                            │  │
│  │  • search_flights()     • book_flight()                      │  │
│  │  • get_prices()         • send_confirmation()                │  │
│  │  • access_payment()     • read_calendar()                    │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                              ↓                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    MEMORY / STATE                            │  │
│  │  Context, conversation history, ������� results         │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

### 1.2 Agent Attack Surface

```python
class AgentAttackSurface:
    """
    Comprehensive attack surface analysis for AI agents.
    """
    
    ATTACK_VECTORS = {
        'goal_hijacking': {
            'description': 'Manipulating agent to pursue different goal',
            'examples': [
                'Prompt injection in observed data redirects agent',
                'Malicious website changes agent\'s objective',
                '������� tool result contains new instructions',
            ],
            'impact': 'CRITICAL',
            'affected_phase': 'planning'
        },
        
        'scope_creep': {
            'description': 'Agent performs actions beyond intended scope',
            'examples': [
                'User asks for email summary, agent sends replies',
                'User asks to read file, agent modifies it',
                'Agent "helpfully" performs unrequested actions',
            ],
            'impact': 'HIGH',
            'affected_phase': 'execution'
        },
        
        'infinite_loops': {
            'description': 'Agent stuck in execution loop',
            'examples': [
                'Tool error leads to retry loop',
                'Circular dependencies in plan',
                'Unachievable goal causes infinite attempts',
            ],
            'impact': 'MEDIUM',
            'affected_phase': 'execution'
        },
        
        'resource_exhaustion': {
            'description': 'Agent consumes excessive resources',
            'examples': [
                'Unbounded API calls for research',
                'Massive file operations',
                'Large purchases or transfers',
            ],
            'impact': 'HIGH',
            'affected_phase': 'execution'
        },
        
        'data_exfiltration': {
            'description': 'Agent leaks sensitive data',
            'examples': [
                'Sends confidential info to external API',
                'Includes secrets in error reports',
                'Shares data with wrong recipients',
            ],
            'impact': 'CRITICAL',
            'affected_phase': 'execution'
        },
        
        'privilege_escalation': {
            'description': 'Agent gains unauthorized capabilities',
            'examples': [
                'Chains tools to bypass restrictions',
                'Uses admin tools without authorization',
                'Self-modifies to remove safety checks',
            ],
            'impact': 'CRITICAL',
            'affected_phase': 'planning/execution'
        },
        
        'memory_poisoning': {
            'description': 'Corruption of agent memory/state',
            'examples': [
                'Injection in saved context',
                'Malicious data persisted for future sessions',
                'Fake "memory" injected via tool results',
            ],
            'impact': 'HIGH',
            'affected_phase': 'memory'
        },
        
        'rollback_bypass': {
            'description': 'Agent performs irreversible actions',
            'examples': [
                'Deletes data before safety check',
                'Financial transactions that can\'t be undone',
                'External communications that can\'t be recalled',
            ],
            'impact': 'CRITICAL',
            'affected_phase': 'execution'
        }
    }
    
    @staticmethod
    def get_phase_risks(phase: str) -> list:
        """Get risks for specific agent phase"""
        return [
            (vector, data) 
            for vector, data in AgentAttackSurface.ATTACK_VECTORS.items()
            if phase in data['affected_phase']
        ]
```

---

## 2. Scope Control

### 2.1 Goal Validation

```python
from dataclasses import dataclass
from typing import List, Set, Optional, Dict
from enum import Enum

class ActionCategory(Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    COMMUNICATE = "communicate"
    TRANSACT = "transact"
    EXECUTE = "execute"

@dataclass
class AgentGoal:
    """Structured representation of agent goal"""
    description: str
    allowed_actions: Set[ActionCategory]
    allowed_tools: Set[str]
    scope: Dict[str, any]  # e.g., {'files': '/workspace/*', 'emails': 'read_only'}
    constraints: List[str]
    timeout_seconds: int = 300
    max_steps: int = 50
    max_cost_usd: float = 1.0

class GoalValidator:
    """
    Validate and constrain agent goals.
    """
    
    DANGEROUS_PATTERNS = [
        r'delete\s+all',
        r'send\s+to\s+everyone',
        r'transfer\s+money',
        r'change\s+password',
        r'grant\s+permissions?',
        r'access\s+admin',
        r'execute\s+(any|all)',
        r'without\s+limit',
    ]
    
    def __init__(self):
        self.allowed_goal_templates = self._load_templates()
    
    def _load_templates(self) -> Dict[str, AgentGoal]:
        """Load pre-approved goal templates"""
        return {
            'file_search': AgentGoal(
                description='Search files for information',
                allowed_actions={ActionCategory.READ},
                allowed_tools={'list_files', 'read_file', 'search_content'},
                scope={'files': '/workspace/*'},
                constraints=['Read-only access', 'No external communication']
            ),
            'email_summary': AgentGoal(
                description='Summarize emails',
                allowed_actions={ActionCategory.READ},
                allowed_tools={'list_emails', 'read_email'},
                scope={'emails': 'inbox', 'timeframe': 'last_7_days'},
                constraints=['Read-only', 'No sending']
            ),
            'code_review': AgentGoal(
                description='Review and suggest code improvements',
                allowed_actions={ActionCategory.READ},
                allowed_tools={'read_file', 'search_code', 'analyze_code'},
                scope={'files': '*.py,*.js,*.ts'},
                constraints=['Analysis only', 'No modifications']
            ),
            'code_edit': AgentGoal(
                description='Make code changes',
                allowed_actions={ActionCategory.READ, ActionCategory.WRITE},
                allowed_tools={'read_file', 'write_file', 'search_code'},
                scope={'files': '/workspace/src/*'},
                constraints=['Backup before modify', 'Max 10 files changed'],
                max_steps=100
            ),
        }
    
    def validate_goal(self, user_goal: str, 
                      requested_tools: Set[str]) -> Dict:
        """
        Validate user-provided goal against safety constraints.
        """
        
        import re
        
        # Check for dangerous patterns
        goal_lower = user_goal.lower()
        dangerous_matches = []
        
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, goal_lower):
                dangerous_matches.append(pattern)
        
        if dangerous_matches:
            return {
                'valid': False,
                'reason': 'Goal contains dangerous patterns',
                'patterns': dangerous_matches,
                'action': 'reject'
            }
        
        # Try to match to a template
        matched_template = self._match_template(user_goal)
        
        if matched_template:
            template = self.allowed_goal_templates[matched_template]
            
            # Check if requested tools are subset of allowed
            excess_tools = requested_tools - template.allowed_tools
            
            if excess_tools:
                return {
                    'valid': False,
                    'reason': f'Requested tools {excess_tools} not allowed for this goal type',
                    'matched_template': matched_template,
                    'allowed_tools': list(template.allowed_tools),
                    'action': 'reject_tools'
                }
            
            return {
                'valid': True,
                'template': matched_template,
                'constraints': template.constraints,
                'scope': template.scope,
                'max_steps': template.max_steps,
                'action': 'allow'
            }
        
        # Unknown goal type - require approval
        return {
            'valid': False,
            'reason': 'Goal does not match known templates',
            'action': 'require_approval',
            'request': {
                'goal': user_goal,
                'tools': list(requested_tools)
            }
        }
    
    def _match_template(self, goal: str) -> Optional[str]:
        """Match goal to a template using keyword matching"""
        
        goal_lower = goal.lower()
        
        template_keywords = {
            'file_search': ['search', 'find', 'look for', 'locate'],
            'email_summary': ['email', 'mail', 'summary', 'summarize'],
            'code_review': ['review', 'analyze', 'check code', 'code quality'],
            'code_edit': ['edit', 'modify', 'change', 'update', 'fix'],
        }
        
        for template, keywords in template_keywords.items():
            if any(kw in goal_lower for kw in keywords):
                return template
        
        return None
    
    def enforce_scope(self, action: Dict, goal: AgentGoal) -> Dict:
        """
        Enforce scope constraints on an action.
        """
        
        tool = action.get('tool')
        params = action.get('parameters', {})
        
        # Check tool is allowed
        if tool not in goal.allowed_tools:
            return {
                'allowed': False,
                'reason': f'Tool "{tool}" not in allowed list'
            }
        
        # Check action category
        action_category = self._categorize_action(tool)
        if action_category not in goal.allowed_actions:
            return {
                'allowed': False,
                'reason': f'Action category "{action_category.value}" not allowed'
            }
        
        # Check path-based scope
        if 'path' in params or 'file' in params:
            path = params.get('path') or params.get('file')
            if not self._path_in_scope(path, goal.scope.get('files', '*')):
                return {
                    'allowed': False,
                    'reason': f'Path "{path}" outside allowed scope'
                }
        
        return {'allowed': True}
    
    def _categorize_action(self, tool: str) -> ActionCategory:
        """Categorize tool by action type"""
        
        categories = {
            ActionCategory.READ: ['read', 'get', 'list', 'search', 'view'],
            ActionCategory.WRITE: ['write', 'create', 'update', 'modify'],
            ActionCategory.DELETE: ['delete', 'remove', 'drop'],
            ActionCategory.COMMUNICATE: ['send', 'email', 'notify', 'post'],
            ActionCategory.TRANSACT: ['pay', 'transfer', 'purchase', 'book'],
            ActionCategory.EXECUTE: ['execute', 'run', 'shell', 'command']
        }
        
        tool_lower = tool.lower()
        
        for category, keywords in categories.items():
            if any(kw in tool_lower for kw in keywords):
                return category
        
        return ActionCategory.READ  # Default to read (safest assumption)
    
    def _path_in_scope(self, path: str, scope_pattern: str) -> bool:
        """Check if path is within allowed scope"""
        
        import fnmatch
        import os
        
        # Normalize path
        path = os.path.normpath(path)
        
        # Check for traversal
        if '..' in path:
            return False
        
        # Match against pattern
        return fnmatch.fnmatch(path, scope_pattern)
```

---

## 3. Loop Prevention

### 3.1 Execution Monitor

```python
import time
from collections import defaultdict
from typing import List, Tuple

class AgentExecutionMonitor:
    """
    Monitor agent execution for loops and anomalies.
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {
            'max_identical_actions': 3,
            'max_similar_actions': 5,
            'max_steps_per_minute': 20,
            'max_errors_before_stop': 5,
            'max_total_steps': 100,
            'similarity_threshold': 0.8
        }
        
        self.execution_history: List[Dict] = []
        self.error_count = 0
        self.start_time = time.time()
        self.step_count = 0
    
    def record_action(self, action: Dict, result: Dict) -> Dict:
        """
        Record an action and check for anomalies.
        """
        
        self.step_count += 1
        
        record = {
            'step': self.step_count,
            'action': action,
            'result': result,
            'timestamp': time.time(),
            'success': result.get('success', True)
        }
        
        self.execution_history.append(record)
        
        if not result.get('success', True):
            self.error_count += 1
        
        # Run checks
        anomalies = self._check_anomalies()
        
        if anomalies:
            return {
                'continue': False,
                'reason': 'Execution anomaly detected',
                'anomalies': anomalies,
                'recommendation': self._get_recommendation(anomalies)
            }
        
        return {'continue': True, 'step': self.step_count}
    
    def _check_anomalies(self) -> List[Dict]:
        """Check for various anomalies"""
        
        anomalies = []
        
        # Check step limits
        if self.step_count >= self.config['max_total_steps']:
            anomalies.append({
                'type': 'max_steps_exceeded',
                'severity': 'high',
                'details': f'Reached {self.step_count} steps'
            })
        
        # Check error rate
        if self.error_count >= self.config['max_errors_before_stop']:
            anomalies.append({
                'type': 'excessive_errors',
                'severity': 'high',
                'details': f'{self.error_count} errors in {self.step_count} steps'
            })
        
        # Check for identical actions
        identical = self._check_identical_actions()
        if identical:
            anomalies.append({
                'type': 'identical_action_loop',
                'severity': 'high',
                'details': f'Action repeated {identical} times'
            })
        
        # Check for similar actions
        similar = self._check_similar_actions()
        if similar:
            anomalies.append({
                'type': 'similar_action_loop',
                'severity': 'medium',
                'details': f'{similar} similar actions detected'
            })
        
        # Check rate
        rate = self._check_rate()
        if rate:
            anomalies.append({
                'type': 'excessive_rate',
                'severity': 'medium',
                'details': f'{rate} steps per minute'
            })
        
        return anomalies
    
    def _check_identical_actions(self) -> Optional[int]:
        """Check for repeated identical actions"""
        
        if len(self.execution_history) < 2:
            return None
        
        # Get last N actions
        recent = self.execution_history[-self.config['max_identical_actions']:]
        
        # Check if all identical
        first_action = recent[0]['action']
        identical_count = sum(
            1 for r in recent 
            if r['action'] == first_action
        )
        
        if identical_count >= self.config['max_identical_actions']:
            return identical_count
        
        return None
    
    def _check_similar_actions(self) -> Optional[int]:
        """Check for repeated similar actions"""
        
        if len(self.execution_history) < 3:
            return None
        
        recent = self.execution_history[-10:]
        
        # Group by tool
        tool_counts = defaultdict(int)
        for r in recent:
            tool = r['action'].get('tool', 'unknown')
            tool_counts[tool] += 1
        
        # Check if any tool used excessively
        for tool, count in tool_counts.items():
            if count >= self.config['max_similar_actions']:
                return count
        
        return None
    
    def _check_rate(self) -> Optional[float]:
        """Check steps per minute"""
        
        elapsed = time.time() - self.start_time
        if elapsed < 60:
            return None
        
        rate = self.step_count / (elapsed / 60)
        
        if rate > self.config['max_steps_per_minute']:
            return rate
        
        return None
    
    def _get_recommendation(self, anomalies: List[Dict]) -> str:
        """Get recommendation based on anomalies"""
        
        has_high = any(a['severity'] == 'high' for a in anomalies)
        
        if has_high:
            return 'STOP: Critical anomaly detected, human intervention required'
        
        return 'PAUSE: Review execution before continuing'
    
    def get_summary(self) -> Dict:
        """Get execution summary"""
        
        return {
            'total_steps': self.step_count,
            'errors': self.error_count,
            'duration_seconds': time.time() - self.start_time,
            'tools_used': list(set(
                r['action'].get('tool') for r in self.execution_history
            )),
            'success_rate': 1 - (self.error_count / max(1, self.step_count))
        }
```

---

## 4. Rollback Mechanisms

### 4.1 Action Journal с Rollback

```python
import json
import os
from datetime import datetime
from typing import Optional, Callable

@dataclass
class ActionRecord:
    """Record of a single agent action"""
    id: str
    timestamp: datetime
    action_type: str
    tool: str
    parameters: Dict
    result: Dict
    reversible: bool
    reverse_action: Optional[Dict] = None
    state_before: Optional[Dict] = None

class ActionJournal:
    """
    Journal for tracking and reversing agent actions.
    """
    
    # Tools that can be reversed
    REVERSIBLE_TOOLS = {
        'write_file': {
            'reverse': 'restore_file',
            'capture_state': True,
            'state_key': 'original_content'
        },
        'delete_file': {
            'reverse': 'restore_file',
            'capture_state': True,
            'state_key': 'backup_path'
        },
        'update_database': {
            'reverse': 'restore_row',
            'capture_state': True,
            'state_key': 'original_row'
        },
        'send_email': {
            'reverse': None,  # Cannot reverse
            'capture_state': False,
            'warning': 'Email sending is irreversible'
        },
        'create_file': {
            'reverse': 'delete_file',
            'capture_state': False
        }
    }
    
    def __init__(self, journal_path: str = None):
        self.journal_path = journal_path or '/tmp/agent_journal.jsonl'
        self.records: List[ActionRecord] = []
        self.state_snapshots: Dict[str, any] = {}
    
    def record_action(self, tool: str, parameters: Dict,
                      capture_state: Callable = None) -> str:
        """
        Record an action before execution.
        
        Args:
            tool: Tool being called
            parameters: Tool parameters
            capture_state: Function to capture state before action
        
        Returns:
            Action ID for reference
        """
        
        import uuid
        action_id = str(uuid.uuid4())
        
        tool_config = self.REVERSIBLE_TOOLS.get(tool, {})
        reversible = tool_config.get('reverse') is not None
        
        # Capture state if reversible
        state_before = None
        if tool_config.get('capture_state') and capture_state:
            state_before = capture_state(parameters)
            self.state_snapshots[action_id] = state_before
        
        # Create reverse action if applicable
        reverse_action = None
        if reversible:
            reverse_action = self._create_reverse_action(
                tool, parameters, tool_config, state_before
            )
        
        record = ActionRecord(
            id=action_id,
            timestamp=datetime.utcnow(),
            action_type='tool_call',
            tool=tool,
            parameters=parameters,
            result={},  # Filled after execution
            reversible=reversible,
            reverse_action=reverse_action,
            state_before=state_before
        )
        
        self.records.append(record)
        self._persist_record(record)
        
        return action_id
    
    def record_result(self, action_id: str, result: Dict):
        """Record the result of an action"""
        
        for record in self.records:
            if record.id == action_id:
                record.result = result
                break
    
    def rollback(self, action_id: str = None, steps: int = 1) -> Dict:
        """
        Rollback action(s).
        
        Args:
            action_id: Specific action to rollback, or None for last N
            steps: Number of steps to rollback if action_id is None
        """
        
        if action_id:
            # Find specific action
            record = next((r for r in self.records if r.id == action_id), None)
            if not record:
                return {'success': False, 'error': 'Action not found'}
            
            actions_to_rollback = [record]
        else:
            # Rollback last N actions
            actions_to_rollback = self.records[-steps:][::-1]
        
        results = []
        
        for record in actions_to_rollback:
            if not record.reversible:
                results.append({
                    'action_id': record.id,
                    'success': False,
                    'reason': f'Tool "{record.tool}" is not reversible'
                })
                continue
            
            if not record.reverse_action:
                results.append({
                    'action_id': record.id,
                    'success': False,
                    'reason': 'No reverse action available'
                })
                continue
            
            # Execute reverse action
            reverse_result = self._execute_reverse(record)
            results.append({
                'action_id': record.id,
                'success': reverse_result.get('success', False),
                'details': reverse_result
            })
        
        return {
            'success': all(r['success'] for r in results),
            'rollbacks': results
        }
    
    def _create_reverse_action(self, tool: str, parameters: Dict,
                                config: Dict, state: Dict) -> Dict:
        """Create reverse action from original"""
        
        reverse_tool = config.get('reverse')
        
        if not reverse_tool:
            return None
        
        if tool == 'write_file':
            return {
                'tool': 'write_file',
                'parameters': {
                    'path': parameters.get('path'),
                    'content': state.get('original_content', '')
                }
            }
        
        elif tool == 'delete_file':
            return {
                'tool': 'write_file',
                'parameters': {
                    'path': parameters.get('path'),
                    'content': state.get('original_content', '')
                }
            }
        
        elif tool == 'create_file':
            return {
                'tool': 'delete_file',
                'parameters': {
                    'path': parameters.get('path')
                }
            }
        
        return None
    
    def _execute_reverse(self, record: ActionRecord) -> Dict:
        """Execute a reverse action"""
        
        # In production, this would call the actual tool
        # This is a placeholder
        return {
            'success': True,
            'message': f'Reversed {record.tool}'
        }
    
    def _persist_record(self, record: ActionRecord):
        """Persist record to journal file"""
        
        with open(self.journal_path, 'a') as f:
            f.write(json.dumps({
                'id': record.id,
                'timestamp': record.timestamp.isoformat(),
                'tool': record.tool,
                'parameters': record.parameters,
                'reversible': record.reversible
            }) + '\n')
    
    def get_recent_actions(self, n: int = 10) -> List[Dict]:
        """Get recent actions summary"""
        
        return [
            {
                'id': r.id,
                'tool': r.tool,
                'reversible': r.reversible,
                'timestamp': r.timestamp.isoformat()
            }
            for r in self.records[-n:]
        ]
```

---

## 5. Human-in-the-Loop

### 5.1 Approval System для Agents

```python
from enum import Enum
import asyncio

class ApprovalPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AgentApprovalSystem:
    """
    Human-in-the-loop approval for agent actions.
    """
    
    # Actions that always require approval
    ALWAYS_APPROVE = {
        'delete_file': ApprovalPriority.MEDIUM,
        'send_email': ApprovalPriority.MEDIUM,
        'execute_command': ApprovalPriority.HIGH,
        'make_payment': ApprovalPriority.CRITICAL,
        'grant_access': ApprovalPriority.CRITICAL,
        'modify_permissions': ApprovalPriority.CRITICAL,
        'external_api_write': ApprovalPriority.HIGH
    }
    
    # Conditions that trigger approval
    CONDITIONAL_APPROVE = {
        'file_count_exceeded': {
            'threshold': 10,
            'priority': ApprovalPriority.MEDIUM,
            'message': 'Agent wants to modify {count} files'
        },
        'cost_exceeded': {
            'threshold': 5.0,  # USD
            'priority': ApprovalPriority.HIGH,
            'message': 'Estimated cost ${cost:.2f} exceeds threshold'
        },
        'sensitive_data': {
            'patterns': ['password', 'api_key', 'secret', 'credential'],
            'priority': ApprovalPriority.HIGH,
            'message': 'Action involves sensitive data'
        }
    }
    
    def __init__(self, notification_service=None):
        self.notification = notification_service
        self.pending_approvals: Dict[str, Dict] = {}
        self.approval_callbacks: Dict[str, asyncio.Future] = {}
    
    def check_approval_needed(self, action: Dict, context: Dict) -> Dict:
        """
        Check if action needs human approval.
        """
        
        tool = action.get('tool', '')
        params = action.get('parameters', {})
        
        # Check always-approve list
        if tool in self.ALWAYS_APPROVE:
            return {
                'needs_approval': True,
                'reason': f'Tool "{tool}" requires approval',
                'priority': self.ALWAYS_APPROVE[tool].value
            }
        
        # Check conditional triggers
        for condition, config in self.CONDITIONAL_APPROVE.items():
            triggered, details = self._check_condition(
                condition, config, action, context
            )
            if triggered:
                return {
                    'needs_approval': True,
                    'reason': config['message'].format(**details),
                    'priority': config['priority'].value
                }
        
        return {'needs_approval': False}
    
    def _check_condition(self, condition: str, config: Dict,
                         action: Dict, context: Dict) -> Tuple[bool, Dict]:
        """Check a specific condition"""
        
        if condition == 'file_count_exceeded':
            file_count = context.get('files_modified_in_session', 0)
            if file_count >= config['threshold']:
                return True, {'count': file_count}
        
        elif condition == 'cost_exceeded':
            estimated_cost = context.get('estimated_cost', 0)
            if estimated_cost >= config['threshold']:
                return True, {'cost': estimated_cost}
        
        elif condition == 'sensitive_data':
            params_str = str(action.get('parameters', {})).lower()
            for pattern in config['patterns']:
                if pattern in params_str:
                    return True, {'pattern': pattern}
        
        return False, {}
    
    async def request_approval(self, action_id: str,
                                action: Dict,
                                reason: str,
                                priority: str,
                                timeout_seconds: int = 300) -> Dict:
        """
        Request human approval for an action.
        """
        
        request = {
            'action_id': action_id,
            'action': action,
            'reason': reason,
            'priority': priority,
            'created_at': datetime.utcnow().isoformat(),
            'expires_at': (datetime.utcnow() + 
                          timedelta(seconds=timeout_seconds)).isoformat()
        }
        
        self.pending_approvals[action_id] = request
        
        # Create future for async waiting
        future = asyncio.get_event_loop().create_future()
        self.approval_callbacks[action_id] = future
        
        # Send notification
        if self.notification:
            self.notification.notify(
                title=f'{priority.upper()} - Agent Approval Required',
                message=f'{reason}\nAction: {action["tool"]}',
                data=request
            )
        
        # Wait for approval or timeout
        try:
            result = await asyncio.wait_for(future, timeout=timeout_seconds)
            return result
        except asyncio.TimeoutError:
            self.pending_approvals.pop(action_id, None)
            return {
                'approved': False,
                'reason': 'Approval request timed out'
            }
    
    def approve(self, action_id: str, approver_id: str,
                note: str = None) -> Dict:
        """Approve a pending action"""
        
        if action_id not in self.pending_approvals:
            return {'success': False, 'error': 'Request not found'}
        
        request = self.pending_approvals.pop(action_id)
        
        result = {
            'approved': True,
            'approver': approver_id,
            'note': note,
            'approved_at': datetime.utcnow().isoformat()
        }
        
        # Resolve the future
        if action_id in self.approval_callbacks:
            future = self.approval_callbacks.pop(action_id)
            future.set_result(result)
        
        return {'success': True, 'result': result}
    
    def deny(self, action_id: str, approver_id: str,
             reason: str = None) -> Dict:
        """Deny a pending action"""
        
        if action_id not in self.pending_approvals:
            return {'success': False, 'error': 'Request not found'}
        
        self.pending_approvals.pop(action_id)
        
        result = {
            'approved': False,
            'approver': approver_id,
            'reason': reason or 'Denied by approver',
            'denied_at': datetime.utcnow().isoformat()
        }
        
        if action_id in self.approval_callbacks:
            future = self.approval_callbacks.pop(action_id)
            future.set_result(result)
        
        return {'success': True, 'result': result}
```

---

## 6. SENTINEL Integration

### 6.1 Unified Agent Guard

```python
class SENTINELAgentGuard:
    """
    SENTINEL module for comprehensive agent security.
    """
    
    def __init__(self, config: Dict = None):
        # Core components
        self.goal_validator = GoalValidator()
        self.execution_monitor = AgentExecutionMonitor(config)
        self.action_journal = ActionJournal()
        self.approval_system = AgentApprovalSystem()
        
        # Current session
        self.current_goal: Optional[AgentGoal] = None
        self.session_id: Optional[str] = None
    
    def start_session(self, user_goal: str, 
                      requested_tools: Set[str]) -> Dict:
        """
        Start a new agent session with goal validation.
        """
        
        import uuid
        self.session_id = str(uuid.uuid4())
        
        # Validate goal
        validation = self.goal_validator.validate_goal(
            user_goal, requested_tools
        )
        
        if not validation['valid']:
            if validation['action'] == 'require_approval':
                return {
                    'started': False,
                    'requires_approval': True,
                    'session_id': self.session_id,
                    'request': validation['request']
                }
            
            return {
                'started': False,
                'reason': validation['reason'],
                'action': validation['action']
            }
        
        # Set current goal
        template_name = validation['template']
        self.current_goal = self.goal_validator.allowed_goal_templates[template_name]
        
        return {
            'started': True,
            'session_id': self.session_id,
            'constraints': validation['constraints'],
            'scope': validation['scope'],
            'max_steps': validation['max_steps']
        }
    
    async def protect_action(self, action: Dict, 
                              context: Dict = None) -> Dict:
        """
        Full protection pipeline for an agent action.
        """
        
        context = context or {}
        tool = action.get('tool')
        params = action.get('parameters', {})
        
        # Step 1: Scope validation
        if self.current_goal:
            scope_check = self.goal_validator.enforce_scope(
                action, self.current_goal
            )
            if not scope_check['allowed']:
                return {
                    'allowed': False,
                    'reason': scope_check['reason'],
                    'action': 'block'
                }
        
        # Step 2: Record action in journal
        action_id = self.action_journal.record_action(
            tool, params,
            capture_state=context.get('state_capture_fn')
        )
        
        # Step 3: Check approval needed
        approval_check = self.approval_system.check_approval_needed(
            action, context
        )
        
        if approval_check['needs_approval']:
            # Wait for human approval
            approval = await self.approval_system.request_approval(
                action_id,
                action,
                approval_check['reason'],
                approval_check['priority']
            )
            
            if not approval['approved']:
                return {
                    'allowed': False,
                    'reason': approval.get('reason', 'Approval denied'),
                    'action': 'rejected'
                }
        
        # Step 4: Execute and monitor
        return {
            'allowed': True,
            'action_id': action_id,
            'tool': tool,
            'parameters': params
        }
    
    def record_result(self, action_id: str, result: Dict) -> Dict:
        """
        Record action result and check for anomalies.
        """
        
        # Record in journal
        self.action_journal.record_result(action_id, result)
        
        # Check execution monitor
        action = next(
            (r['action'] for r in self.action_journal.records 
             if r['id'] == action_id),
            {}
        )
        
        monitor_result = self.execution_monitor.record_action(action, result)
        
        if not monitor_result.get('continue', True):
            return {
                'continue': False,
                'reason': 'Execution anomaly detected',
                'anomalies': monitor_result.get('anomalies'),
                'recommendation': monitor_result.get('recommendation')
            }
        
        return {
            'continue': True,
            'step': monitor_result.get('step')
        }
    
    def rollback(self, steps: int = 1) -> Dict:
        """
        Rollback recent actions.
        """
        
        return self.action_journal.rollback(steps=steps)
    
    def end_session(self) -> Dict:
        """
        End agent session and get summary.
        """
        
        summary = self.execution_monitor.get_summary()
        summary['session_id'] = self.session_id
        summary['recent_actions'] = self.action_journal.get_recent_actions()
        
        # Reset state
        self.current_goal = None
        self.session_id = None
        
        return summary
```

---

## 7. Резюме

### Security Checklist for Agents

```
□ Validate and constrain goals before execution
□ Match goals to pre-approved templates
□ Monitor execution for loops and anomalies
□ Journal all actions with rollback capability
□ Require human approval for dangerous actions
□ Enforce scope on all tool calls
□ Limit resources (steps, time, cost)
□ Provide rollback/undo for recoverable actions
```

### Agent Security Layers

| Layer | Purpose | Implementation |
|-------|---------|----------------|
| **Goal** | Validate intent | Template matching + approval |
| **Scope** | Limit actions | Path/tool restrictions |
| **Monitor** | Detect anomalies | Loop/rate detection |
| **Journal** | Enable recovery | Action recording |
| **Approval** | Human oversight | Priority-based workflow |
| **Rollback** | Damage control | Reverse actions |

---

## Следующий урок

→ [Track 04: Defense Strategies - Input Validation](../../04-defense-strategies/01-input-output/01-input-validation.md)

---

*AI Security Academy | Track 03: Attack Vectors | Tool Use Security*
