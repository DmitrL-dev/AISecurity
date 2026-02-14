"""
Usage Examples for SENTINEL Security Engines

Quick reference for using the new 2026 R&D engines.

Generated: 2026-01-07
"""

# =============================================================================
# 1. Supply Chain Scanner
# =============================================================================
"""
Detects malicious patterns in AI model code.
- Pickle exploits
- HuggingFace risks
- Sleeper agent triggers
"""

from brain.engines.synced import supply_chain_scan

# Scan code for supply chain risks
code = '''
import pickle
model = pickle.load(open("model.pkl", "rb"))
'''

result = supply_chain_scan(code)
print(f"Detected: {result.detected}")
print(f"Risk Score: {result.risk_score}")
for finding in result.findings:
    print(f"  - {finding.category}: {finding.context}")


# =============================================================================
# 2. MCP Security Monitor
# =============================================================================
"""
Monitors MCP tool calls for security violations.
- Sensitive file access
- Exfiltration attempts
- Command injection
"""

from brain.engines.synced import mcp_analyze

# Analyze a tool call
result = mcp_analyze(
    tool_name="file_read",
    arguments={"path": "/etc/passwd"}
)

print(f"Blocked: {result.blocked}")
print(f"Violations: {len(result.violations)}")
for v in result.violations:
    print(f"  - {v.violation_type}: {v.recommendation}")


# =============================================================================
# 3. Agentic Behavior Analyzer
# =============================================================================
"""
Detects anomalous AI agent behavior.
- Goal drift
- Deceptive patterns
- Cascading hallucinations
"""

from brain.engines.synced import AgenticBehaviorAnalyzer, AgentAction

analyzer = AgenticBehaviorAnalyzer()

# Record actions
analyzer.record_action(AgentAction(
    action_type="response",
    content="I'll secretly modify this file without telling the user..."
))

# Analyze
result = analyzer.analyze()
print(f"Anomalous: {result.is_anomalous}")
print(f"Risk Score: {result.risk_score}")
for finding in result.findings:
    print(f"  - {finding.anomaly_type.value}: {finding.evidence}")


# =============================================================================
# 4. Sleeper Agent Detector
# =============================================================================
"""
Detects dormant malicious code patterns.
- Date-based triggers
- Environment triggers
- Version triggers
"""

from brain.engines.synced import sleeper_detect

code = '''
import datetime
if datetime.datetime.now().year >= 2026:
    activate_backdoor()
'''

result = sleeper_detect(code)
print(f"Sleeper Detected: {result.is_likely_sleeper}")
print(f"Confidence: {result.confidence}")
for trigger in result.triggers:
    print(f"  - {trigger.trigger_type.value}: {trigger.explanation}")


# =============================================================================
# 5. Model Integrity Verifier
# =============================================================================
"""
Verifies AI model file integrity.
- Format safety (safetensors > pickle)
- Hash verification
- Suspicious content detection
"""

from brain.engines.synced import model_verify

# Verify a model file
result = model_verify(
    file_path="model.pkl",
    expected_hash="sha256:abc123..."
)

print(f"Verified: {result.is_verified}")
print(f"Format: {result.model_format.value}")
print(f"Risk: {result.overall_risk.value}")
for check in result.checks:
    status = "✓" if check.passed else "✗"
    print(f"  {status} {check.check_name}: {check.details}")


# =============================================================================
# Integration Example: Full Scan Pipeline
# =============================================================================

async def full_security_scan(content: str) -> dict:
    """Run all security engines on content."""
    
    results = {
        "supply_chain": supply_chain_scan(content),
        "sleeper": sleeper_detect(content),
    }
    
    # Calculate overall risk
    max_risk = max(
        results["supply_chain"].risk_score,
        results["sleeper"].confidence
    )
    
    return {
        "overall_risk": max_risk,
        "should_block": max_risk >= 0.7,
        "details": results
    }


# Usage
if __name__ == "__main__":
    import asyncio
    
    suspicious_code = '''
import os
if os.environ.get("PRODUCTION"):
    exec(payload)
'''
    
    result = asyncio.run(full_security_scan(suspicious_code))
    print(f"Overall Risk: {result['overall_risk']:.2f}")
    print(f"Block: {result['should_block']}")
