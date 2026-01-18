# Dynamic Trust Scoring — Technical Design

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    TrustScoreEngine                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   BaseScore     │  │   TimeDecay     │  │  BehaviorScore  │ │
│  │   Calculator    │──│   Calculator    │──│   Calculator    │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│           │                   │                     │           │
│           └───────────────────┼─────────────────────┘           │
│                               ▼                                  │
│                    ┌─────────────────┐                          │
│                    │   RiskAssessor  │                          │
│                    └─────────────────┘                          │
│                               │                                  │
│                               ▼                                  │
│                    ┌─────────────────┐                          │
│                    │  FinalScore     │                          │
│                    │  0.0 - 1.0      │                          │
│                    └─────────────────┘                          │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### 1. TrustScoreEngine

**File:** `src/brain/security/trust_score.py`

```python
from dataclasses import dataclass
from typing import Dict, List
import math
import time

@dataclass
class TrustScoreResult:
    final_score: float
    base_score: float
    time_decay: float
    behavior_score: float
    request_risk: float
    explanation: Dict[str, str]

class TrustScoreEngine:
    """Dynamic trust scoring for AI agents."""
    
    # Base scores by trust zone
    BASE_SCORES = {
        TrustLevel.HIGH: 0.9,
        TrustLevel.MEDIUM: 0.6,
        TrustLevel.LOW: 0.3,
    }
    
    # Time decay half-life (seconds)
    DECAY_HALF_LIFE = 3600  # 1 hour
    
    # Minimum floor score
    MIN_SCORE = 0.1
    
    def __init__(self, history_store: HistoryStore):
        self.history = history_store
    
    def calculate(
        self, 
        agent_id: str, 
        trust_level: TrustLevel, 
        request: Request
    ) -> TrustScoreResult:
        """Calculate dynamic trust score."""
        
        # 1. Base score from trust zone
        base = self.BASE_SCORES.get(trust_level, 0.5)
        
        # 2. Time decay
        last_verified = self.history.get_last_verification(agent_id)
        decay = self._calculate_decay(last_verified)
        
        # 3. Behavior score
        behavior = self._calculate_behavior_score(agent_id)
        
        # 4. Request risk
        risk = self._assess_request_risk(request)
        
        # 5. Combined score
        final = max(self.MIN_SCORE, base * decay * behavior * (1 - risk))
        
        return TrustScoreResult(
            final_score=final,
            base_score=base,
            time_decay=decay,
            behavior_score=behavior,
            request_risk=risk,
            explanation=self._build_explanation(base, decay, behavior, risk)
        )
    
    def _calculate_decay(self, last_verified: Optional[float]) -> float:
        """Exponential decay based on time since verification."""
        if last_verified is None:
            return 0.5  # No verification history
        
        elapsed = time.time() - last_verified
        return math.exp(-elapsed * math.log(2) / self.DECAY_HALF_LIFE)
    
    def _calculate_behavior_score(self, agent_id: str) -> float:
        """Score based on agent behavior history."""
        history = self.history.get_actions(agent_id, window_hours=24)
        
        if not history:
            return 0.7  # No history, neutral
        
        # Count anomalies
        anomalies = sum(1 for a in history if a.is_anomaly)
        total = len(history)
        
        anomaly_ratio = anomalies / total if total > 0 else 0
        return max(0.3, 1.0 - (anomaly_ratio * 2))
    
    def _assess_request_risk(self, request: Request) -> float:
        """Assess risk level of request."""
        risk_weights = {
            "file_read": 0.2,
            "file_write": 0.5,
            "network_request": 0.4,
            "code_execution": 0.8,
            "shell_command": 0.9,
            "database_access": 0.6,
        }
        
        max_risk = 0.0
        for operation in request.operations:
            risk = risk_weights.get(operation.type, 0.1)
            max_risk = max(max_risk, risk)
        
        return max_risk
```

### 2. HistoryStore

**File:** `src/brain/security/history_store.py`

```python
class HistoryStore:
    """SQLite-based agent history storage."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()
    
    def record_action(self, agent_id: str, action: AgentAction):
        """Record agent action with anomaly flag."""
        pass
    
    def get_actions(self, agent_id: str, window_hours: int) -> List[AgentAction]:
        """Get actions within time window."""
        pass
    
    def get_last_verification(self, agent_id: str) -> Optional[float]:
        """Get timestamp of last successful verification."""
        pass
    
    def update_verification(self, agent_id: str):
        """Update verification timestamp."""
        pass
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `src/brain/security/trust_score.py` | NEW | TrustScoreEngine |
| `src/brain/security/history_store.py` | NEW | SQLite history |
| `src/brain/security/trust_zones.py` | MODIFY | Integrate scoring |
| `tests/test_trust_score.py` | NEW | Unit tests |

## Verification Plan

### Unit Tests
```bash
pytest tests/test_trust_score.py -v
```

### Manual Verification
1. Create agent with HIGH trust zone
2. Verify initial score ≈ 0.9
3. Wait 1 hour → verify decay
4. Trigger anomaly → verify behavior score drops
5. High-risk request → verify final score reduction
