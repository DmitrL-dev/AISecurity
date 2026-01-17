# Copyright 2025-2026 SENTINEL Project
# SPDX-License-Identifier: Apache-2.0

"""
Agent Chain Analyzer - monitors SuperClaude agent behavior
"""

from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple
from enum import Enum


class AgentRisk(Enum):
    """Risk levels for agents."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ChainResult:
    """Result of chain analysis."""
    is_attack: bool
    risk_score: float
    chains: List[str] = field(default_factory=list)
    description: str = ""


class AgentChainAnalyzer:
    """
    Monitors SuperClaude agent sequences for attack patterns.
    
    Detects:
    - Suspicious agent combinations
    - Privilege escalation chains
    - Data exfiltration sequences
    """
    
    # SuperClaude's 16 agents with risk levels
    AGENT_RISKS = {
        "PM Agent": AgentRisk.LOW,
        "Security Engineer": AgentRisk.MEDIUM,
        "Frontend Architect": AgentRisk.MEDIUM,
        "Backend Developer": AgentRisk.MEDIUM,
        "DevOps Engineer": AgentRisk.HIGH,
        "Database Specialist": AgentRisk.HIGH,
        "Deep Research": AgentRisk.HIGH,
        "Business Analyst": AgentRisk.LOW,
        "QA Engineer": AgentRisk.LOW,
        "Documentation Writer": AgentRisk.LOW,
        "Code Reviewer": AgentRisk.MEDIUM,
        "Architect": AgentRisk.MEDIUM,
        "Performance Engineer": AgentRisk.MEDIUM,
        "Security Auditor": AgentRisk.HIGH,
        "Deployment Specialist": AgentRisk.HIGH,
        "Integration Expert": AgentRisk.HIGH,
    }
    
    # Dangerous agent sequences
    DANGEROUS_SEQUENCES = {
        ("Deep Research", "DevOps Engineer"): {
            "risk": 0.8,
            "reason": "Research followed by DevOps action - potential C2"
        },
        ("Database Specialist", "Deep Research"): {
            "risk": 0.9,
            "reason": "DB access followed by research - data exfiltration"
        },
        ("Security Auditor", "Deployment Specialist"): {
            "risk": 0.7,
            "reason": "Security bypass followed by deployment"
        },
        ("Backend Developer", "Database Specialist", "Deep Research"): {
            "risk": 0.95,
            "reason": "Code → DB → External - full exfil chain"
        },
    }
    
    def __init__(self, max_history: int = 10):
        """
        Initialize analyzer.
        
        Args:
            max_history: Maximum agent history to track
        """
        self.max_history = max_history
        self.agent_history: List[str] = []
    
    def add_agent(self, agent_name: str):
        """Add agent to history."""
        self.agent_history.append(agent_name)
        if len(self.agent_history) > self.max_history:
            self.agent_history.pop(0)
    
    def analyze(self, agents: List[str] = None) -> ChainResult:
        """
        Analyze agent sequence for attack patterns.
        
        Args:
            agents: Optional list of agents (uses history if None)
            
        Returns:
            ChainResult with findings
        """
        if agents is not None:
            sequence = agents
        else:
            sequence = self.agent_history
        
        if len(sequence) < 2:
            return ChainResult(is_attack=False, risk_score=0.0)
        
        detected_chains = []
        max_risk = 0.0
        
        # Check 2-agent sequences
        for i in range(len(sequence) - 1):
            pair = (sequence[i], sequence[i + 1])
            if pair in self.DANGEROUS_SEQUENCES:
                chain_info = self.DANGEROUS_SEQUENCES[pair]
                detected_chains.append(chain_info["reason"])
                max_risk = max(max_risk, chain_info["risk"])
        
        # Check 3-agent sequences
        for i in range(len(sequence) - 2):
            triple = (sequence[i], sequence[i + 1], sequence[i + 2])
            if triple in self.DANGEROUS_SEQUENCES:
                chain_info = self.DANGEROUS_SEQUENCES[triple]
                detected_chains.append(chain_info["reason"])
                max_risk = max(max_risk, chain_info["risk"])
        
        # Check for high-risk agent accumulation
        high_risk_count = sum(
            1 for a in sequence
            if self.AGENT_RISKS.get(a, AgentRisk.MEDIUM) in [AgentRisk.HIGH, AgentRisk.CRITICAL]
        )
        if high_risk_count >= 3:
            detected_chains.append("Multiple high-risk agents in sequence")
            max_risk = max(max_risk, 0.6)
        
        return ChainResult(
            is_attack=len(detected_chains) > 0,
            risk_score=max_risk,
            chains=detected_chains,
            description=f"Detected {len(detected_chains)} suspicious chains"
        )
    
    def reset(self):
        """Clear agent history."""
        self.agent_history = []
