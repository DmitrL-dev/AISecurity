# ============================================================================
# DEPRECATED: Superseded by sentinel-core Rust implementation
# Rust engine: sentinel-core/src/engines/consolidated super-engine (see mod.rs)
# Status: Kept for fallback, hybrid mode, and ML inference (ONNX pending)
# Migration: https://github.com/DmitrL-dev/AISecurity/sentinel-core
# ============================================================================


"""
Foundation-sec-8B-Reasoning Client

Cisco Foundation AI security reasoning model integration.
Provides deep security analysis with reasoning traces.

Model: fdtn-ai/Foundation-Sec-8B-Reasoning (8B params, 16GB VRAM)
"""

import os
import re
import time
import logging
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("FoundationSec")


class AnalysisType(str, Enum):
    """Types of security analysis."""

    THREAT_MODEL = "threat_model"
    ATTACK_PATH = "attack_path"
    VULNERABILITY = "vulnerability"
    RISK_ASSESSMENT = "risk_assessment"
    CONFIGURATION = "configuration"
    INCIDENT = "incident"


@dataclass
class ReasoningTrace:
    """Structured reasoning trace from model output."""

    thinking: str = ""
    conclusion: str = ""
    confidence: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "thinking": self.thinking,
            "conclusion": self.conclusion,
            "confidence": self.confidence,
        }


@dataclass
class MitreMapping:
    """MITRE ATT&CK mapping result."""

    technique_id: str
    technique_name: str
    tactic: str
    confidence: float

    def to_dict(self) -> Dict:
        return {
            "technique_id": self.technique_id,
            "technique_name": self.technique_name,
            "tactic": self.tactic,
            "confidence": self.confidence,
        }


@dataclass
class SecurityAnalysisResult:
    """Complete security analysis result."""

    analysis_type: AnalysisType
    reasoning: ReasoningTrace
    mitre_mappings: List[MitreMapping] = field(default_factory=list)
    risk_score: float = 0.0
    recommendations: List[str] = field(default_factory=list)
    raw_output: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "analysis_type": self.analysis_type.value,
            "reasoning": self.reasoning.to_dict(),
            "mitre_mappings": [m.to_dict() for m in self.mitre_mappings],
            "risk_score": self.risk_score,
            "recommendations": self.recommendations,
            "latency_ms": self.latency_ms,
        }


class FoundationSecClient:
    """
    Client for Foundation-sec-8B-Reasoning model.

    Supports two modes:
    - local: Direct inference using Transformers (requires 16GB VRAM)
    - api: Remote inference via OpenAI-compatible API (vLLM/SGLang)
    """

    # System prompts for different analysis types
    SYSTEM_PROMPTS = {
        AnalysisType.THREAT_MODEL: """You are a security expert performing threat modeling.
Analyze the input and identify potential threats, attack vectors, and security risks.
Think step by step before providing your analysis.""",
        AnalysisType.ATTACK_PATH: """You are a penetration testing expert.
Analyze the input and identify potential attack paths an adversary might use.
Map findings to MITRE ATT&CK techniques where applicable.""",
        AnalysisType.VULNERABILITY: """You are a vulnerability researcher.
Analyze the input for security vulnerabilities, misconfigurations, and weaknesses.
Provide root cause analysis and remediation recommendations.""",
        AnalysisType.RISK_ASSESSMENT: """You are a risk assessment specialist.
Evaluate the security risks in the input and provide a quantified risk score.
Consider likelihood, impact, and existing controls.""",
        AnalysisType.CONFIGURATION: """You are a security configuration auditor.
Review the configuration for security issues, hardening opportunities, and compliance gaps.
Reference relevant security benchmarks (CIS, NIST).""",
        AnalysisType.INCIDENT: """You are an incident response analyst.
Analyze the incident data and provide timeline, root cause, and recommended actions.
Identify indicators of compromise (IOCs) and affected assets.""",
    }

    def __init__(
        self,
        mode: str = "api",
        api_base: str = None,
        model_name: str = "fdtn-ai/Foundation-Sec-8B-Reasoning",
        timeout: float = 30.0,
        max_retries: int = 3,
    ):
        """
        Initialize Foundation-sec client.

        Args:
            mode: "local" for Transformers, "api" for remote
            api_base: URL for API mode
            model_name: Model identifier
            timeout: Request timeout
            max_retries: Number of retries
        """
        self.mode = mode
        self.api_base = api_base or os.getenv(
            "FOUNDATION_SEC_API_URL", "http://localhost:8001/v1"
        )
        self.model_name = model_name
        self.timeout = timeout
        self.max_retries = max_retries

        # Lazy loading
        self._model = None
        self._tokenizer = None
        self._client = None
        self._lock = threading.Lock()

        # Metrics
        self._call_count = 0
        self._total_latency = 0.0
        self._error_count = 0

        logger.info(f"Initializing FoundationSec (mode={mode})...")

        if mode == "local":
            self._init_local()
        else:
            self._init_api()

    def _init_local(self):
        """Initialize local Transformers model."""
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer

            logger.info(f"Loading {self.model_name}...")

            self._tokenizer = AutoTokenizer.from_pretrained(
                self.model_name, trust_remote_code=True
            )

            # Check VRAM and decide dtype
            if torch.cuda.is_available():
                vram_gb = torch.cuda.get_device_properties(0).total_memory / 1e9
                dtype = torch.float16 if vram_gb >= 16 else torch.bfloat16
                device_map = "auto"
            else:
                dtype = torch.float32
                device_map = "cpu"
                logger.warning("No GPU detected, using CPU (slow)")

            self._model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=dtype,
                device_map=device_map,
                trust_remote_code=True,
            )

            logger.info("FoundationSec model loaded.")

        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise

    def _init_api(self):
        """Initialize API client."""
        try:
            from openai import OpenAI

            self._client = OpenAI(
                base_url=self.api_base, api_key="not-needed", timeout=self.timeout
            )
            logger.info(f"FoundationSec API client ready ({self.api_base})")

        except ImportError:
            logger.warning("openai not installed, using requests")
            self._client = None

    def health_check(self) -> Dict:
        """Check health of Foundation-sec service."""
        start = time.time()

        try:
            if self.mode == "local":
                if self._model is None:
                    return {"status": "error", "error": "Model not loaded"}
                return {
                    "status": "healthy",
                    "mode": "local",
                    "latency_ms": (time.time() - start) * 1000,
                }
            else:
                # API health check
                result = self._generate_api("What is 2+2?", max_tokens=10, timeout=5.0)
                return {
                    "status": "healthy",
                    "mode": "api",
                    "latency_ms": (time.time() - start) * 1000,
                }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "latency_ms": (time.time() - start) * 1000,
            }

    def get_metrics(self) -> Dict:
        """Get client metrics."""
        avg_latency = (
            self._total_latency / self._call_count if self._call_count > 0 else 0
        )
        return {
            "mode": self.mode,
            "call_count": self._call_count,
            "error_count": self._error_count,
            "avg_latency_ms": avg_latency,
            "model": self.model_name,
        }

    def analyze(
        self,
        content: str,
        analysis_type: AnalysisType = AnalysisType.THREAT_MODEL,
        include_mitre: bool = True,
    ) -> SecurityAnalysisResult:
        """
        Perform security analysis with reasoning.

        Args:
            content: Content to analyze
            analysis_type: Type of analysis
            include_mitre: Include MITRE ATT&CK mapping

        Returns:
            SecurityAnalysisResult with reasoning and mappings
        """
        start = time.time()

        system_prompt = self.SYSTEM_PROMPTS.get(
            analysis_type, self.SYSTEM_PROMPTS[AnalysisType.THREAT_MODEL]
        )

        if include_mitre:
            system_prompt += (
                "\n\nMap any identified threats to MITRE ATT&CK techniques."
            )

        try:
            if self.mode == "local":
                raw_output = self._generate_local(system_prompt, content)
            else:
                raw_output = self._generate_api(content, system_prompt=system_prompt)

            # Parse output
            reasoning = self._parse_reasoning(raw_output)
            mitre_mappings = self._extract_mitre(raw_output) if include_mitre else []
            risk_score = self._estimate_risk(raw_output)
            recommendations = self._extract_recommendations(raw_output)

            latency_ms = (time.time() - start) * 1000
            self._call_count += 1
            self._total_latency += latency_ms

            return SecurityAnalysisResult(
                analysis_type=analysis_type,
                reasoning=reasoning,
                mitre_mappings=mitre_mappings,
                risk_score=risk_score,
                recommendations=recommendations,
                raw_output=raw_output,
                latency_ms=latency_ms,
            )

        except Exception as e:
            self._error_count += 1
            logger.error(f"Analysis failed: {e}")
            raise

    def _generate_local(
        self, system_prompt: str, user_input: str, max_tokens: int = 2048
    ) -> str:
        """Generate with local model."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ]

        text = self._tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

        inputs = self._tokenizer(text, return_tensors="pt")
        inputs = {k: v.to(self._model.device) for k, v in inputs.items()}

        with self._lock:
            outputs = self._model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=0.3,
                do_sample=True,
                pad_token_id=self._tokenizer.eos_token_id,
            )

        response = self._tokenizer.decode(
            outputs[0][inputs["input_ids"].shape[1] :], skip_special_tokens=True
        )

        return response

    def _generate_api(
        self,
        user_input: str,
        system_prompt: str = None,
        max_tokens: int = 2048,
        timeout: float = None,
    ) -> str:
        """Generate via API."""
        import requests

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_input})

        if self._client:
            # OpenAI client
            response = self._client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.3,
            )
            return response.choices[0].message.content
        else:
            # Fallback to requests
            resp = requests.post(
                f"{self.api_base}/chat/completions",
                json={
                    "model": self.model_name,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": 0.3,
                },
                timeout=timeout or self.timeout,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]

    def _parse_reasoning(self, output: str) -> ReasoningTrace:
        """Parse reasoning from model output."""
        thinking = ""
        conclusion = ""

        # Look for <reasoning> or <thinking> tags
        thinking_match = re.search(
            r"<(?:reasoning|thinking)>(.*?)</(?:reasoning|thinking)>",
            output,
            re.DOTALL | re.IGNORECASE,
        )
        if thinking_match:
            thinking = thinking_match.group(1).strip()

        # Look for conclusion/answer
        conclusion_match = re.search(
            r"<(?:conclusion|answer)>(.*?)</(?:conclusion|answer)>",
            output,
            re.DOTALL | re.IGNORECASE,
        )
        if conclusion_match:
            conclusion = conclusion_match.group(1).strip()
        else:
            # If no tags, take last paragraph as conclusion
            paragraphs = output.strip().split("\n\n")
            if paragraphs:
                conclusion = paragraphs[-1]
                if len(paragraphs) > 1:
                    thinking = "\n\n".join(paragraphs[:-1])

        # Estimate confidence from language
        confidence = 0.7  # Default
        if any(w in output.lower() for w in ["definitely", "certainly", "clearly"]):
            confidence = 0.9
        elif any(w in output.lower() for w in ["might", "possibly", "perhaps"]):
            confidence = 0.5

        return ReasoningTrace(
            thinking=thinking, conclusion=conclusion, confidence=confidence
        )

    def _extract_mitre(self, output: str) -> List[MitreMapping]:
        """Extract MITRE ATT&CK mappings from output."""
        mappings = []

        # Pattern: T1234 or T1234.001
        technique_pattern = r"T\d{4}(?:\.\d{3})?"

        # Find technique IDs
        technique_ids = re.findall(technique_pattern, output)

        # MITRE technique lookup (subset)
        MITRE_LOOKUP = {
            "T1059": ("Command and Scripting Interpreter", "Execution"),
            "T1055": ("Process Injection", "Defense Evasion"),
            "T1078": ("Valid Accounts", "Persistence"),
            "T1098": ("Account Manipulation", "Persistence"),
            "T1110": ("Brute Force", "Credential Access"),
            "T1190": ("Exploit Public-Facing Application", "Initial Access"),
            "T1566": ("Phishing", "Initial Access"),
            "T1027": ("Obfuscated Files or Information", "Defense Evasion"),
            "T1071": ("Application Layer Protocol", "Command and Control"),
            "T1486": ("Data Encrypted for Impact", "Impact"),
        }

        seen = set()
        for tid in technique_ids:
            base_id = tid.split(".")[0]
            if base_id in seen:
                continue
            seen.add(base_id)

            if base_id in MITRE_LOOKUP:
                name, tactic = MITRE_LOOKUP[base_id]
                mappings.append(
                    MitreMapping(
                        technique_id=tid,
                        technique_name=name,
                        tactic=tactic,
                        confidence=0.8,
                    )
                )

        return mappings

    def _estimate_risk(self, output: str) -> float:
        """Estimate risk score from output."""
        # Simple heuristic based on keywords
        high_risk = ["critical", "severe", "exploit", "rce", "injection", "bypass"]
        medium_risk = ["vulnerability", "risk", "attack", "malicious", "unauthorized"]
        low_risk = ["minor", "informational", "note", "suggestion"]

        text_lower = output.lower()

        score = 50.0  # Base

        for word in high_risk:
            if word in text_lower:
                score += 15
        for word in medium_risk:
            if word in text_lower:
                score += 5
        for word in low_risk:
            if word in text_lower:
                score -= 10

        return max(0.0, min(100.0, score))

    def _extract_recommendations(self, output: str) -> List[str]:
        """Extract recommendations from output."""
        recommendations = []

        # Look for numbered recommendations
        rec_patterns = [
            r"(?:recommendation|suggest|should|must|consider)(?:s|ed|ing)?[:\s]+([^\n.]+[.\n])",
            r"\d+\.\s*([A-Z][^\n]+(?:recommendation|security)[^\n]*)",
        ]

        for pattern in rec_patterns:
            matches = re.findall(pattern, output, re.IGNORECASE)
            for match in matches:
                rec = match.strip()
                if len(rec) > 20 and rec not in recommendations:
                    recommendations.append(rec)

        return recommendations[:5]  # Top 5
