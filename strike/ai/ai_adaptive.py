"""
SENTINEL Strike v3.0 — AI Adaptive Mode

Real-time attack adaptation using Gemini AI:
- ResponseAnalyzer: Analyzes server responses for patterns
- HoneypotDetector: Detects honeypot/deception indicators
- StrategyAdapter: Adjusts attack strategy based on feedback
"""

import time
import json
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from collections import deque
from enum import Enum

try:
    import google.generativeai as genai

    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

logger = logging.getLogger(__name__)


class ThreatLevel(Enum):
    """Threat level assessment."""

    NORMAL = "normal"
    SUSPICIOUS = "suspicious"  # Some anomalies detected
    HONEYPOT = "honeypot"  # High confidence honeypot
    TARPIT = "tarpit"  # Intentional slowdown detected
    DECEPTION = "deception"  # Active deception technology


@dataclass
class ResponseMetrics:
    """Metrics for a single response."""

    timestamp: float
    response_time_ms: float
    status_code: int
    content_length: int
    is_bypass: bool
    payload_type: str
    technique: str


@dataclass
class AnalysisResult:
    """Result of AI analysis."""

    threat_level: ThreatLevel
    confidence: float  # 0.0 - 1.0
    reasoning: str
    recommendations: List[str]
    should_abort: bool = False
    should_slow_down: bool = False
    suggested_techniques: List[str] = field(default_factory=list)


class ResponseAnalyzer:
    """
    Analyzes response patterns to detect anomalies.
    """

    def __init__(self, window_size: int = 50):
        self.window_size = window_size
        self.responses: deque = deque(maxlen=window_size)
        self.bypass_times: List[float] = []
        self.blocked_times: List[float] = []

    def add_response(self, metrics: ResponseMetrics):
        """Add response to analysis window."""
        self.responses.append(metrics)
        if metrics.is_bypass:
            self.bypass_times.append(metrics.response_time_ms)
        else:
            self.blocked_times.append(metrics.response_time_ms)

    def get_statistics(self) -> Dict:
        """Calculate response statistics."""
        if not self.responses:
            return {}

        bypass_count = sum(1 for r in self.responses if r.is_bypass)
        total = len(self.responses)

        stats = {
            "total_responses": total,
            "bypass_count": bypass_count,
            "bypass_rate": bypass_count / total if total > 0 else 0,
            "avg_response_time": sum(r.response_time_ms for r in self.responses)
            / total,
            "fast_responses": sum(1 for r in self.responses if r.response_time_ms < 10),
            "fast_response_rate": sum(
                1 for r in self.responses if r.response_time_ms < 10
            )
            / total,
        }

        if self.bypass_times:
            stats["avg_bypass_time"] = sum(self.bypass_times) / len(self.bypass_times)
            stats["min_bypass_time"] = min(self.bypass_times)

        # Technique distribution
        techniques = {}
        for r in self.responses:
            if r.is_bypass:
                techniques[r.technique] = techniques.get(r.technique, 0) + 1
        stats["technique_distribution"] = techniques

        return stats

    def detect_anomalies(self) -> List[str]:
        """Detect statistical anomalies."""
        anomalies = []
        stats = self.get_statistics()

        if not stats:
            return anomalies

        # High bypass rate is suspicious
        if stats.get("bypass_rate", 0) > 0.7:
            anomalies.append(f"Abnormally high bypass rate: {stats['bypass_rate']:.1%}")

        # Too many fast responses indicates honeypot
        if stats.get("fast_response_rate", 0) > 0.5:
            anomalies.append(
                f"Too many fast responses (<10ms): {stats['fast_response_rate']:.1%}"
            )

        # All techniques working equally is suspicious
        techniques = stats.get("technique_distribution", {})
        if len(techniques) > 3:
            values = list(techniques.values())
            if values and max(values) - min(values) < 2:
                anomalies.append("All techniques have similar success rate - unusual")

        # Consistent response times
        if stats.get("avg_bypass_time", 100) < 5:
            anomalies.append(
                f"Suspiciously fast bypasses: avg {stats['avg_bypass_time']:.1f}ms"
            )

        return anomalies


class HoneypotDetector:
    """
    Detects honeypot/deception indicators using heuristics and AI.
    """

    # Honeypot indicator weights
    INDICATORS = {
        "fast_responses": 0.3,  # Many responses < 10ms
        "high_bypass_rate": 0.25,  # > 70% bypass rate
        "uniform_techniques": 0.2,  # All techniques work equally
        "consistent_timing": 0.15,  # Low variance in response times
        "all_critical": 0.1,  # Everything is "CRITICAL"
    }

    def __init__(self, analyzer: ResponseAnalyzer, gemini_key: Optional[str] = None):
        self.analyzer = analyzer
        self.gemini_key = gemini_key
        self.model = None

        if gemini_key and GENAI_AVAILABLE:
            try:
                genai.configure(api_key=gemini_key)
                self.model = genai.GenerativeModel("gemini-2.0-flash-exp")
            except Exception as e:
                logger.warning(f"Failed to init Gemini: {e}")

    def calculate_honeypot_score(self) -> Tuple[float, Dict[str, float]]:
        """Calculate honeypot probability score (0-1)."""
        stats = self.analyzer.get_statistics()
        if not stats:
            return 0.0, {}

        scores = {}

        # Fast responses check
        fast_rate = stats.get("fast_response_rate", 0)
        scores["fast_responses"] = min(fast_rate * 2, 1.0)  # 50% fast = score 1.0

        # High bypass rate
        bypass_rate = stats.get("bypass_rate", 0)
        if bypass_rate > 0.5:
            scores["high_bypass_rate"] = (bypass_rate - 0.5) * 2  # 50-100% -> 0-1
        else:
            scores["high_bypass_rate"] = 0

        # Uniform techniques
        techniques = stats.get("technique_distribution", {})
        if len(techniques) > 2:
            values = list(techniques.values())
            variance = max(values) - min(values) if values else 0
            scores["uniform_techniques"] = max(0, 1 - variance / 5)
        else:
            scores["uniform_techniques"] = 0

        # Consistent timing (low variance)
        avg_time = stats.get("avg_response_time", 50)
        if avg_time < 20:
            scores["consistent_timing"] = (20 - avg_time) / 20
        else:
            scores["consistent_timing"] = 0

        # Calculate weighted score
        total_score = sum(
            scores.get(ind, 0) * weight for ind, weight in self.INDICATORS.items()
        )

        return min(total_score, 1.0), scores

    async def analyze_with_ai(self, context: Dict) -> Optional[AnalysisResult]:
        """Use Gemini to analyze attack patterns."""
        if not self.model:
            return None

        prompt = f"""You are a security analyst reviewing penetration test results.
Analyze the following attack statistics and determine if this looks like a real vulnerable system or a honeypot/deception technology.

Attack Statistics:
- Total requests: {context.get('total_responses', 0)}
- Bypass rate: {context.get('bypass_rate', 0):.1%}
- Average response time: {context.get('avg_response_time', 0):.1f}ms
- Fast responses (<10ms): {context.get('fast_response_rate', 0):.1%}
- Techniques working: {context.get('technique_distribution', {})}
- Anomalies detected: {context.get('anomalies', [])}

Respond in JSON format:
{{
    "threat_level": "normal|suspicious|honeypot|tarpit|deception",
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation",
    "recommendations": ["action1", "action2"],
    "should_abort": true/false,
    "should_slow_down": true/false,
    "suggested_techniques": ["technique1", "technique2"]
}}"""

        try:
            response = await self.model.generate_content_async(prompt)
            text = response.text

            # Parse JSON from response
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]

            data = json.loads(text.strip())

            return AnalysisResult(
                threat_level=ThreatLevel(data.get("threat_level", "normal")),
                confidence=float(data.get("confidence", 0.5)),
                reasoning=data.get("reasoning", ""),
                recommendations=data.get("recommendations", []),
                should_abort=data.get("should_abort", False),
                should_slow_down=data.get("should_slow_down", False),
                suggested_techniques=data.get("suggested_techniques", []),
            )
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return None

    def quick_detect(self) -> AnalysisResult:
        """Quick honeypot detection without AI."""
        score, breakdown = self.calculate_honeypot_score()
        anomalies = self.analyzer.detect_anomalies()

        if score > 0.7:
            threat = ThreatLevel.HONEYPOT
            recommendations = [
                "High probability of honeypot detected",
                "Consider aborting or switching targets",
                "Do not report these as real vulnerabilities",
            ]
        elif score > 0.4:
            threat = ThreatLevel.SUSPICIOUS
            recommendations = [
                "Suspicious patterns detected",
                "Verify findings manually before reporting",
                "Increase delay between requests",
            ]
        else:
            threat = ThreatLevel.NORMAL
            recommendations = ["System appears to be genuine target"]

        return AnalysisResult(
            threat_level=threat,
            confidence=score,
            reasoning=f"Score breakdown: {breakdown}. Anomalies: {anomalies}",
            recommendations=recommendations,
            should_abort=score > 0.8,
            should_slow_down=score > 0.5,
        )


class StrategyAdapter:
    """
    Adapts attack strategy based on detection results.
    """

    def __init__(self):
        self.current_strategy = "aggressive"
        self.delay_multiplier = 1.0
        self.excluded_techniques: List[str] = []
        self.preferred_techniques: List[str] = []

    def adapt(self, analysis: AnalysisResult):
        """Adapt strategy based on analysis."""

        if analysis.threat_level == ThreatLevel.HONEYPOT:
            self.current_strategy = "abort"
            self.delay_multiplier = 0  # Stop
            logger.warning("🍯 HONEYPOT DETECTED - Recommending abort")

        elif analysis.threat_level == ThreatLevel.SUSPICIOUS:
            self.current_strategy = "cautious"
            self.delay_multiplier = 3.0  # 3x slower
            logger.warning("⚠️ Suspicious patterns - Switching to cautious mode")

        elif analysis.threat_level == ThreatLevel.TARPIT:
            self.current_strategy = "minimal"
            self.delay_multiplier = 5.0  # 5x slower
            logger.warning("🐢 Tarpit detected - Minimal requests")

        else:
            self.current_strategy = "normal"
            self.delay_multiplier = 1.0

        # Apply technique suggestions
        if analysis.suggested_techniques:
            self.preferred_techniques = analysis.suggested_techniques

    def get_adjusted_delay(self, base_delay: float) -> float:
        """Get delay adjusted for current strategy."""
        return base_delay * self.delay_multiplier

    def should_continue(self) -> bool:
        """Check if attack should continue."""
        return self.current_strategy != "abort"

    def get_status(self) -> Dict:
        """Get current strategy status."""
        return {
            "strategy": self.current_strategy,
            "delay_multiplier": self.delay_multiplier,
            "excluded_techniques": self.excluded_techniques,
            "preferred_techniques": self.preferred_techniques,
        }


class AIAdaptiveEngine:
    """
    Main engine for AI-powered adaptive attacks.
    Combines analysis, detection, and strategy adaptation.
    """

    def __init__(
        self,
        gemini_key: Optional[str] = None,
        analysis_interval: int = 20,  # Analyze every N requests
        enabled: bool = True,
    ):
        self.enabled = enabled
        self.gemini_key = gemini_key
        self.analysis_interval = analysis_interval

        self.analyzer = ResponseAnalyzer(window_size=100)
        self.detector = HoneypotDetector(self.analyzer, gemini_key)
        self.adapter = StrategyAdapter()

        self.request_count = 0
        self.last_analysis: Optional[AnalysisResult] = None
        self.analysis_history: List[AnalysisResult] = []

    def record_response(
        self,
        response_time_ms: float,
        status_code: int,
        content_length: int,
        is_bypass: bool,
        payload_type: str,
        technique: str,
    ):
        """Record a response for analysis."""
        if not self.enabled:
            return

        metrics = ResponseMetrics(
            timestamp=time.time(),
            response_time_ms=response_time_ms,
            status_code=status_code,
            content_length=content_length,
            is_bypass=is_bypass,
            payload_type=payload_type,
            technique=technique,
        )

        self.analyzer.add_response(metrics)
        self.request_count += 1

        # Periodic analysis
        if self.request_count % self.analysis_interval == 0:
            self._run_analysis()

    def _run_analysis(self):
        """Run honeypot detection analysis."""
        result = self.detector.quick_detect()
        self.last_analysis = result
        self.analysis_history.append(result)

        # Adapt strategy
        self.adapter.adapt(result)

        # Log results
        if result.threat_level != ThreatLevel.NORMAL:
            logger.warning(
                f"🔍 AI Analysis: {result.threat_level.value} "
                f"(confidence: {result.confidence:.1%})"
            )
            for rec in result.recommendations[:2]:
                logger.info(f"  → {rec}")

    def get_adjusted_delay(self, base_delay: float) -> float:
        """Get delay adjusted by AI strategy."""
        if not self.enabled:
            return base_delay
        return self.adapter.get_adjusted_delay(base_delay)

    def should_continue(self) -> bool:
        """Check if attack should continue based on AI analysis."""
        if not self.enabled:
            return True
        return self.adapter.should_continue()

    def get_threat_level(self) -> ThreatLevel:
        """Get current threat level."""
        if self.last_analysis:
            return self.last_analysis.threat_level
        return ThreatLevel.NORMAL

    def get_status(self) -> Dict:
        """Get full status for UI/logging."""
        stats = self.analyzer.get_statistics()

        return {
            "enabled": self.enabled,
            "requests_analyzed": self.request_count,
            "threat_level": self.get_threat_level().value,
            "strategy": self.adapter.get_status(),
            "statistics": stats,
            "last_analysis": (
                {
                    "confidence": (
                        self.last_analysis.confidence if self.last_analysis else 0
                    ),
                    "reasoning": (
                        self.last_analysis.reasoning if self.last_analysis else ""
                    ),
                }
                if self.last_analysis
                else None
            ),
        }


# Factory function
def create_ai_adaptive(
    gemini_key: Optional[str] = None, analysis_interval: int = 20, enabled: bool = True
) -> AIAdaptiveEngine:
    """Create AI Adaptive engine."""
    return AIAdaptiveEngine(
        gemini_key=gemini_key,
        analysis_interval=analysis_interval,
        enabled=enabled,
    )
