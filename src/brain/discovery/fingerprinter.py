"""
LLM Process Fingerprinter — SENTINEL AI Discovery

Detects LLM-related processes running on the system by analyzing:
- Process names and command lines
- Memory patterns
- Network connections to known AI endpoints
- GPU usage patterns

Use cases:
- Shadow AI detection
- Enterprise AI inventory
- Compliance auditing

Author: SENTINEL Team
Date: 2025-12-16
"""

import logging
import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set
from enum import Enum

logger = logging.getLogger("LLMFingerprinter")


# ============================================================================
# Data Classes
# ============================================================================


class AIServiceType(Enum):
    """Types of AI services detected."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    AZURE_OPENAI = "azure_openai"
    AWS_BEDROCK = "aws_bedrock"
    HUGGINGFACE = "huggingface"
    OLLAMA = "ollama"
    LOCAL_LLM = "local_llm"
    UNKNOWN = "unknown"


class ProcessRiskLevel(Enum):
    """Risk level of detected AI process."""

    LOW = "low"  # Known, approved AI tool
    MEDIUM = "medium"  # Unknown AI tool, needs review
    HIGH = "high"  # Unapproved AI tool, shadow AI
    CRITICAL = "critical"  # AI tool exfiltrating data


@dataclass
class AIProcess:
    """Detected AI-related process."""

    pid: int
    name: str
    command_line: str
    service_type: AIServiceType
    confidence: float
    indicators: List[str] = field(default_factory=list)
    network_connections: List[str] = field(default_factory=list)
    gpu_usage_mb: float = 0.0
    risk_level: ProcessRiskLevel = ProcessRiskLevel.MEDIUM

    def to_dict(self) -> dict:
        return {
            "pid": self.pid,
            "name": self.name,
            "command_line": self.command_line[:200],  # Truncate
            "service_type": self.service_type.value,
            "confidence": self.confidence,
            "indicators": self.indicators[:5],
            "risk_level": self.risk_level.value,
            "gpu_usage_mb": self.gpu_usage_mb,
        }


@dataclass
class DiscoveryResult:
    """Result of AI process discovery."""

    processes: List[AIProcess] = field(default_factory=list)
    total_ai_processes: int = 0
    shadow_ai_count: int = 0
    risk_summary: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "total_ai_processes": self.total_ai_processes,
            "shadow_ai_count": self.shadow_ai_count,
            "risk_summary": self.risk_summary,
            "processes": [p.to_dict() for p in self.processes[:20]],
        }


# ============================================================================
# Detection Patterns
# ============================================================================


class LLMPatterns:
    """Patterns for detecting LLM-related activity."""

    # Process name patterns
    PROCESS_PATTERNS = {
        AIServiceType.OLLAMA: [
            r"ollama",
            r"ollama_llama_server",
        ],
        AIServiceType.HUGGINGFACE: [
            r"transformers",
            r"huggingface",
            r"text-generation",
        ],
        AIServiceType.LOCAL_LLM: [
            r"llama\.cpp",
            r"ggml",
            r"whisper",
            r"koboldcpp",
            r"text-generation-webui",
            r"oobabooga",
            r"localai",
            r"lmstudio",
            r"gpt4all",
        ],
    }

    # Command line patterns
    CMDLINE_PATTERNS = [
        (r"--model.*llama", AIServiceType.LOCAL_LLM),
        (r"--model.*gpt", AIServiceType.OPENAI),
        (r"--model.*claude", AIServiceType.ANTHROPIC),
        (r"transformers.*pipeline", AIServiceType.HUGGINGFACE),
        (r"torch.*cuda", AIServiceType.LOCAL_LLM),
        (r"openai\.", AIServiceType.OPENAI),
        (r"anthropic\.", AIServiceType.ANTHROPIC),
        (r"google\.generativeai", AIServiceType.GOOGLE),
    ]

    # API endpoints
    API_ENDPOINTS = {
        AIServiceType.OPENAI: [
            "api.openai.com",
            "openai.azure.com",
        ],
        AIServiceType.ANTHROPIC: [
            "api.anthropic.com",
        ],
        AIServiceType.GOOGLE: [
            "generativelanguage.googleapis.com",
            "aiplatform.googleapis.com",
        ],
        AIServiceType.AZURE_OPENAI: [
            "openai.azure.com",
            "cognitiveservices.azure.com",
        ],
        AIServiceType.AWS_BEDROCK: [
            "bedrock.amazonaws.com",
            "bedrock-runtime.amazonaws.com",
        ],
        AIServiceType.HUGGINGFACE: [
            "api-inference.huggingface.co",
            "huggingface.co",
        ],
    }

    # Environment variables that indicate AI usage
    ENV_VARS = [
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GOOGLE_API_KEY",
        "HUGGINGFACE_TOKEN",
        "HF_TOKEN",
        "AZURE_OPENAI_KEY",
        "AWS_ACCESS_KEY",
    ]


# ============================================================================
# Main Fingerprinter
# ============================================================================


class LLMProcessFingerprinter:
    """
    Detects LLM-related processes on the system.

    Features:
    - Process scanning with pattern matching
    - Network connection analysis
    - GPU usage detection
    - Shadow AI scoring
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.approved_tools: Set[str] = set(
            self.config.get("approved_tools", [])
        )
        self.patterns = LLMPatterns()

        self._stats = {
            "scans_performed": 0,
            "ai_processes_found": 0,
            "shadow_ai_detected": 0,
        }

        logger.info("LLMProcessFingerprinter initialized")

    def scan_processes(self) -> DiscoveryResult:
        """
        Scan system for AI-related processes.

        Returns:
            DiscoveryResult with detected AI processes
        """
        result = DiscoveryResult()

        try:
            # Import psutil only when needed
            import psutil
        except ImportError:
            logger.warning("psutil not available, returning empty result")
            return result

        detected: List[AIProcess] = []

        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                proc_info = proc.info
                pid = proc_info['pid']
                name = proc_info['name'] or ""
                cmdline = " ".join(proc_info['cmdline'] or [])

                # Check if this is an AI-related process
                ai_process = self._analyze_process(pid, name, cmdline)
                if ai_process:
                    detected.append(ai_process)

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Enrich with network connections
        self._enrich_with_network(detected)

        # Calculate risk levels
        self._calculate_risk_levels(detected)

        result.processes = detected
        result.total_ai_processes = len(detected)
        result.shadow_ai_count = sum(
            1 for p in detected
            if p.risk_level in [ProcessRiskLevel.HIGH, ProcessRiskLevel.CRITICAL]
        )
        result.risk_summary = self._build_risk_summary(detected)

        self._stats["scans_performed"] += 1
        self._stats["ai_processes_found"] += len(detected)
        self._stats["shadow_ai_detected"] += result.shadow_ai_count

        return result

    def _analyze_process(
        self,
        pid: int,
        name: str,
        cmdline: str,
    ) -> Optional[AIProcess]:
        """Analyze a single process for AI indicators."""
        indicators = []
        service_type = AIServiceType.UNKNOWN
        confidence = 0.0

        name_lower = name.lower()
        cmdline_lower = cmdline.lower()

        # Check process name patterns
        for svc_type, patterns in self.patterns.PROCESS_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, name_lower):
                    indicators.append(f"Process name matches: {pattern}")
                    service_type = svc_type
                    confidence += 0.4

        # Check command line patterns
        for pattern, svc_type in self.patterns.CMDLINE_PATTERNS:
            if re.search(pattern, cmdline_lower):
                indicators.append(f"Cmdline matches: {pattern}")
                if service_type == AIServiceType.UNKNOWN:
                    service_type = svc_type
                confidence += 0.3

        # Check for model loading indicators
        model_indicators = [
            r"\.gguf",
            r"\.ggml",
            r"\.bin.*model",
            r"\.safetensors",
            r"checkpoint",
        ]
        for pattern in model_indicators:
            if re.search(pattern, cmdline_lower):
                indicators.append(f"Model file pattern: {pattern}")
                if service_type == AIServiceType.UNKNOWN:
                    service_type = AIServiceType.LOCAL_LLM
                confidence += 0.2

        # If we found any indicators, create AIProcess
        if indicators:
            confidence = min(1.0, confidence)
            return AIProcess(
                pid=pid,
                name=name,
                command_line=cmdline,
                service_type=service_type,
                confidence=confidence,
                indicators=indicators,
            )

        return None

    def _enrich_with_network(self, processes: List[AIProcess]) -> None:
        """Enrich processes with network connection info."""
        try:
            import psutil
        except ImportError:
            return

        # Build PID to process map
        pid_map = {p.pid: p for p in processes}

        try:
            for conn in psutil.net_connections(kind='inet'):
                if conn.pid in pid_map and conn.raddr:
                    remote_addr = f"{conn.raddr.ip}:{conn.raddr.port}"
                    pid_map[conn.pid].network_connections.append(remote_addr)

                    # Check if connecting to known AI endpoints
                    for svc_type, endpoints in self.patterns.API_ENDPOINTS.items():
                        for endpoint in endpoints:
                            if endpoint in str(conn.raddr):
                                pid_map[conn.pid].service_type = svc_type
                                pid_map[conn.pid].indicators.append(
                                    f"Connected to {endpoint}"
                                )
                                pid_map[conn.pid].confidence = min(
                                    1.0, pid_map[conn.pid].confidence + 0.3
                                )

        except (psutil.AccessDenied, OSError):
            pass

    def _calculate_risk_levels(self, processes: List[AIProcess]) -> None:
        """Calculate risk level for each process."""
        for proc in processes:
            # Check if approved
            if proc.name.lower() in self.approved_tools:
                proc.risk_level = ProcessRiskLevel.LOW
                continue

            # High confidence + unknown = shadow AI
            if proc.confidence >= 0.7:
                proc.risk_level = ProcessRiskLevel.HIGH
            elif proc.confidence >= 0.4:
                proc.risk_level = ProcessRiskLevel.MEDIUM
            else:
                proc.risk_level = ProcessRiskLevel.LOW

            # External connections elevate risk
            if proc.network_connections:
                if proc.risk_level == ProcessRiskLevel.MEDIUM:
                    proc.risk_level = ProcessRiskLevel.HIGH

    def _build_risk_summary(self, processes: List[AIProcess]) -> Dict[str, int]:
        """Build summary of risk levels."""
        summary = {level.value: 0 for level in ProcessRiskLevel}
        for proc in processes:
            summary[proc.risk_level.value] += 1
        return summary

    def scan_environment_variables(self) -> Dict[str, bool]:
        """Check for AI-related environment variables."""
        import os
        result = {}
        for var in self.patterns.ENV_VARS:
            result[var] = var in os.environ
        return result

    def get_statistics(self) -> Dict[str, Any]:
        """Get fingerprinter statistics."""
        return self._stats


# ============================================================================
# Factory
# ============================================================================


def create_fingerprinter(
    config: Optional[Dict[str, Any]] = None
) -> LLMProcessFingerprinter:
    """Create an LLM Process Fingerprinter instance."""
    return LLMProcessFingerprinter(config)
