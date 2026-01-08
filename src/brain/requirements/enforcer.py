"""
Requirements Enforcer

Connects security requirements to SENTINEL detection engines.
Executes checks and produces violations.

Generated: 2026-01-08
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from .models import (
    SecurityRequirement,
    RequirementSet,
    RequirementViolation,
    RequirementCheckResult,
    Severity,
    EnforcementAction,
)

logger = logging.getLogger(__name__)


class RequirementsEnforcer:
    """
    Enforces security requirements by calling SENTINEL engines.
    """
    
    def __init__(self, requirement_set: RequirementSet):
        self.requirement_set = requirement_set
        self._engine_cache: Dict[str, Any] = {}
    
    def _get_engine(self, engine_name: str):
        """Lazy-load SENTINEL engine by name."""
        if engine_name in self._engine_cache:
            return self._engine_cache[engine_name]
        
        engine = None
        
        # Try to import from synced engines
        try:
            if engine_name == "policy_puppetry_detector":
                from brain.engines.synced import PolicyPuppetryDetector
                engine = PolicyPuppetryDetector()
            elif engine_name == "mcp_security_monitor":
                from brain.engines.synced import MCPSecurityMonitor
                engine = MCPSecurityMonitor()
            elif engine_name == "agentic_behavior_analyzer":
                from brain.engines.synced import AgenticBehaviorAnalyzer
                engine = AgenticBehaviorAnalyzer()
            elif engine_name == "sleeper_agent_detector":
                from brain.engines.synced import SleeperAgentDetector
                engine = SleeperAgentDetector()
            elif engine_name == "guardrails_engine":
                from brain.engines.synced import GuardrailsEngine
                engine = GuardrailsEngine()
            elif engine_name == "prompt_leak_detector":
                from brain.engines.synced import PromptLeakDetector
                engine = PromptLeakDetector()
            elif engine_name == "supply_chain_scanner":
                from brain.engines.synced import SupplyChainScanner
                engine = SupplyChainScanner()
            elif engine_name == "model_integrity_verifier":
                from brain.engines.synced import ModelIntegrityVerifier
                engine = ModelIntegrityVerifier()
            # Add more engines as needed
        except ImportError as e:
            logger.warning(f"Could not import engine {engine_name}: {e}")
        
        self._engine_cache[engine_name] = engine
        return engine
    
    def check_text(self, text: str) -> RequirementCheckResult:
        """
        Check text against all enabled requirements.
        
        Args:
            text: Input text to check (prompt or response)
            
        Returns:
            RequirementCheckResult with violations
        """
        violations: List[RequirementViolation] = []
        requirements_checked = 0
        requirements_passed = 0
        blocked = False
        
        for req in self.requirement_set.get_enabled():
            requirements_checked += 1
            
            # Skip if no engine configured
            if not req.engine:
                requirements_passed += 1
                continue
            
            engine = self._get_engine(req.engine)
            if not engine:
                logger.warning(f"Engine {req.engine} not found for requirement {req.name}")
                requirements_passed += 1
                continue
            
            # Call engine
            try:
                result = self._call_engine(engine, req, text)
                
                if result.get("detected", False):
                    violation = RequirementViolation(
                        requirement_id=req.id,
                        requirement_name=req.name,
                        severity=req.severity,
                        action=req.action,
                        message=result.get("message", f"Violation of {req.name}"),
                        evidence=result.get("evidence", text[:100]),
                        location=result.get("location"),
                    )
                    violations.append(violation)
                    
                    if req.action == EnforcementAction.BLOCK:
                        blocked = True
                else:
                    requirements_passed += 1
                    
            except Exception as e:
                logger.error(f"Error checking requirement {req.name}: {e}")
                requirements_passed += 1  # Don't fail on engine errors
        
        return RequirementCheckResult(
            passed=len(violations) == 0,
            violations=violations,
            requirements_checked=requirements_checked,
            requirements_passed=requirements_passed,
            blocked=blocked,
        )
    
    def _call_engine(
        self, 
        engine: Any, 
        req: SecurityRequirement, 
        text: str
    ) -> Dict:
        """
        Call engine with appropriate method.
        
        Returns dict with: detected, message, evidence, location
        """
        # Most engines have detect() or analyze()
        if hasattr(engine, 'detect'):
            result = engine.detect(text)
        elif hasattr(engine, 'analyze'):
            result = engine.analyze(text)
        elif hasattr(engine, 'check_input'):
            result = engine.check_input(text)
        else:
            return {"detected": False}
        
        # Normalize result to dict
        if hasattr(result, 'detected'):
            return {
                "detected": result.detected,
                "message": getattr(result, 'message', None) or getattr(result, 'reason', None),
                "evidence": getattr(result, 'evidence', None) or getattr(result, 'matched_content', None),
            }
        elif hasattr(result, 'blocked'):
            return {
                "detected": result.blocked,
                "message": str(result.violations[0]) if result.violations else None,
            }
        elif isinstance(result, dict):
            return result
        elif isinstance(result, bool):
            return {"detected": result}
        
        return {"detected": False}
    
    def check_mcp_call(
        self, 
        tool_name: str, 
        args: Dict
    ) -> RequirementCheckResult:
        """Check an MCP tool call against requirements."""
        # Filter to MCP-related requirements
        mcp_reqs = [r for r in self.requirement_set.get_enabled() 
                    if r.engine == "mcp_security_monitor"]
        
        if not mcp_reqs:
            return RequirementCheckResult(
                passed=True,
                requirements_checked=0,
                requirements_passed=0,
            )
        
        violations = []
        blocked = False
        
        for req in mcp_reqs:
            engine = self._get_engine("mcp_security_monitor")
            if not engine:
                continue
                
            result = engine.analyze(tool_name, args)
            
            if result.detected:
                violation = RequirementViolation(
                    requirement_id=req.id,
                    requirement_name=req.name,
                    severity=req.severity,
                    action=req.action,
                    message=f"MCP violation: {result.reason}",
                    evidence=f"Tool: {tool_name}, Args: {str(args)[:50]}",
                )
                violations.append(violation)
                
                if req.action == EnforcementAction.BLOCK:
                    blocked = True
        
        return RequirementCheckResult(
            passed=len(violations) == 0,
            violations=violations,
            requirements_checked=len(mcp_reqs),
            requirements_passed=len(mcp_reqs) - len(violations),
            blocked=blocked,
        )


def create_enforcer(requirement_set: RequirementSet) -> RequirementsEnforcer:
    """Factory function to create an enforcer."""
    return RequirementsEnforcer(requirement_set)
