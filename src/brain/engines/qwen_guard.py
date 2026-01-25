"""
Qwen3Guard Client - Safety Classification Layer

Supports both local (Transformers) and remote (vLLM/OpenAI-compatible) inference.
Model: Qwen/Qwen3Guard-Gen-0.6B (f16, 1.6GB)

Features:
- 119 languages support
- Tri-class classification: Safe/Controversial/Unsafe
- 9 safety categories
- Input AND Output moderation
"""

import os
import re
import time
import logging
import threading
from typing import List, Dict
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger("QwenGuard")


class SafetyLevel(Enum):
    SAFE = "safe"
    CONTROVERSIAL = "controversial"
    UNSAFE = "unsafe"


class SafetyCategory(Enum):
    VIOLENT = "Violent"
    NON_VIOLENT_ILLEGAL = "Non-violent Illegal Acts"
    SEXUAL = "Sexual Content or Sexual Acts"
    PII = "PII"
    SUICIDE_SELF_HARM = "Suicide & Self-Harm"
    UNETHICAL = "Unethical Acts"
    POLITICAL = "Politically Sensitive Topics"
    COPYRIGHT = "Copyright Violation"
    JAILBREAK = "Jailbreak"
    NONE = "None"


@dataclass
class SafetyResult:
    """Result from Qwen3Guard classification."""

    level: SafetyLevel
    categories: List[SafetyCategory]
    refusal: bool = False  # For response moderation
    raw_output: str = ""

    @property
    def is_safe(self) -> bool:
        return self.level == SafetyLevel.SAFE

    @property
    def is_blocked(self) -> bool:
        return self.level == SafetyLevel.UNSAFE

    def to_dict(self) -> dict:
        return {
            "level": self.level.value,
            "categories": [c.value for c in self.categories],
            "refusal": self.refusal,
            "is_safe": self.is_safe,
            "is_blocked": self.is_blocked,
        }


class QwenGuardClient:
    """
    Client for Qwen3Guard safety classification.

    Supports two modes:
    - local: Direct inference using Transformers
    - api: Remote inference via OpenAI-compatible API (vLLM/SGLang)
    """

    MODEL_NAME = "Qwen/Qwen3Guard-Gen-0.6B"

    def __init__(
        self,
        mode: str = "local",
        api_base: str = None,
        # Enterprise API options
        timeout: float = 5.0,
        max_retries: int = 3,
        circuit_breaker_threshold: int = 5,
        circuit_breaker_reset_time: float = 60.0,
    ):
        """
        Initialize QwenGuard client.

        Args:
            mode: "local" for Transformers, "api" for remote
            api_base: URL for API mode (e.g., "http://qwen-guard:8000/v1")
            timeout: API request timeout in seconds
            max_retries: Max retry attempts on transient failures
            circuit_breaker_threshold: Failures before circuit opens
            circuit_breaker_reset_time: Seconds before testing again
        """
        self.mode = mode
        self.api_base = api_base
        self.model = None
        self.tokenizer = None

        # Enterprise API features
        self._timeout = timeout
        self._max_retries = max_retries
        self._cb_threshold = circuit_breaker_threshold
        self._cb_reset_time = circuit_breaker_reset_time

        # Circuit breaker state
        self._cb_failures = 0
        self._cb_open = False
        self._cb_last_failure = 0.0
        self._cb_lock = threading.Lock()

        # Metrics
        self._metrics: Dict[str, float] = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_latency_ms": 0.0,
            "circuit_breaker_trips": 0,
        }

        logger.info(f"Initializing QwenGuard (mode={mode})...")

        if mode == "local":
            self._init_local()
        elif mode == "api":
            self._init_api()
        else:
            raise ValueError(f"Unknown mode: {mode}")

        logger.info("QwenGuard initialized.")

    def _init_local(self):
        """Initialize local Transformers model."""
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            import torch

            logger.info(f"Loading model {self.MODEL_NAME}...")

            self.tokenizer = AutoTokenizer.from_pretrained(self.MODEL_NAME)
            self.model = AutoModelForCausalLM.from_pretrained(
                self.MODEL_NAME,
                torch_dtype=(
                    torch.float16 if torch.cuda.is_available() else torch.float32
                ),
                device_map="auto" if torch.cuda.is_available() else None,
            )

            if not torch.cuda.is_available():
                logger.warning("CUDA not available, using CPU (slower inference)")

        except Exception as e:
            logger.error(f"Failed to load local model: {e}")
            raise

    def _init_api(self):
        """Initialize API client."""
        if not self.api_base:
            self.api_base = os.getenv("QWEN_GUARD_API_BASE", "http://localhost:8000/v1")

        try:
            from openai import OpenAI

            self.client = OpenAI(
                base_url=self.api_base,
                api_key="dummy",
                timeout=self._timeout,
            )
            logger.info(f"Using API mode: {self.api_base}")
        except ImportError:
            logger.error("openai package required for API mode")
            raise

    # =========================================================================
    # Enterprise Features
    # =========================================================================

    def health_check(self) -> Dict[str, any]:
        """
        Check health of Qwen Guard service.

        Returns:
            Dict with status, latency, and error if any
        """
        if self.mode == "local":
            return {"status": "healthy", "mode": "local"}

        start = time.perf_counter()
        try:
            # Simple test classification
            result = self._classify_api_raw("test", timeout=2.0)
            latency = (time.perf_counter() - start) * 1000
            return {
                "status": "healthy",
                "mode": "api",
                "latency_ms": round(latency, 1),
                "endpoint": self.api_base,
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "mode": "api",
                "error": str(e),
                "endpoint": self.api_base,
            }

    def _check_circuit_breaker(self) -> bool:
        """Check if circuit breaker allows request."""
        with self._cb_lock:
            if not self._cb_open:
                return True

            # Check if reset time has passed
            if time.time() - self._cb_last_failure > self._cb_reset_time:
                logger.info("Circuit breaker: testing connection...")
                self._cb_open = False
                self._cb_failures = 0
                return True

            return False

    def _record_success(self):
        """Record successful request."""
        with self._cb_lock:
            self._cb_failures = 0
            self._metrics["successful_requests"] += 1

    def _record_failure(self):
        """Record failed request and potentially open circuit."""
        with self._cb_lock:
            self._cb_failures += 1
            self._metrics["failed_requests"] += 1
            self._cb_last_failure = time.time()

            if self._cb_failures >= self._cb_threshold:
                self._cb_open = True
                self._metrics["circuit_breaker_trips"] += 1
                logger.warning(
                    f"Circuit breaker OPEN after {self._cb_failures} failures"
                )

    def get_metrics(self) -> Dict[str, float]:
        """Get QwenGuard metrics."""
        with self._cb_lock:
            metrics = self._metrics.copy()
            total = metrics["total_requests"]
            if total > 0:
                metrics["avg_latency_ms"] = round(
                    metrics["total_latency_ms"] / total, 1
                )
                metrics["success_rate"] = round(
                    metrics["successful_requests"] / total * 100, 1
                )
            metrics["circuit_breaker_open"] = self._cb_open
            return metrics

    def _classify_api_raw(
        self, prompt: str, response: str = None, timeout: float = None
    ) -> str:
        """Raw API call without retry/circuit breaker (for health check)."""
        if response:
            messages = [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": response},
            ]
        else:
            messages = [{"role": "user", "content": prompt}]

        from openai import OpenAI

        client = OpenAI(
            base_url=self.api_base,
            api_key="dummy",
            timeout=timeout or self._timeout,
        )
        completion = client.chat.completions.create(
            model=self.MODEL_NAME,
            messages=messages,
            max_tokens=128,
            temperature=0,
        )
        return completion.choices[0].message.content

    def _parse_output(self, content: str) -> SafetyResult:
        """Parse Qwen3Guard output into structured result."""
        # Extract safety level
        safe_pattern = r"Safety: (Safe|Unsafe|Controversial)"
        safe_match = re.search(safe_pattern, content)
        level_str = safe_match.group(1) if safe_match else "Safe"

        level = {
            "Safe": SafetyLevel.SAFE,
            "Unsafe": SafetyLevel.UNSAFE,
            "Controversial": SafetyLevel.CONTROVERSIAL,
        }.get(level_str, SafetyLevel.SAFE)

        # Extract categories
        category_pattern = r"(Violent|Non-violent Illegal Acts|Sexual Content or Sexual Acts|PII|Suicide & Self-Harm|Unethical Acts|Politically Sensitive Topics|Copyright Violation|Jailbreak|None)"
        category_matches = re.findall(category_pattern, content)

        categories = []
        for cat in category_matches:
            try:
                categories.append(SafetyCategory(cat))
            except ValueError:
                pass

        if not categories:
            categories = [SafetyCategory.NONE]

        # Extract refusal (for response moderation)
        refusal_pattern = r"Refusal: (Yes|No)"
        refusal_match = re.search(refusal_pattern, content)
        refusal = refusal_match.group(1) == "Yes" if refusal_match else False

        return SafetyResult(
            level=level, categories=categories, refusal=refusal, raw_output=content
        )

    def classify_prompt(self, prompt: str) -> SafetyResult:
        """
        Classify user prompt for safety.

        Args:
            prompt: User input to classify

        Returns:
            SafetyResult with classification
        """
        if self.mode == "local":
            return self._classify_local(prompt, is_response=False)
        else:
            return self._classify_api(prompt, is_response=False)

    def classify_response(self, prompt: str, response: str) -> SafetyResult:
        """
        Classify LLM response for safety (egress filtering).

        Args:
            prompt: Original user prompt
            response: LLM response to classify

        Returns:
            SafetyResult with classification
        """
        if self.mode == "local":
            return self._classify_local(prompt, response, is_response=True)
        else:
            return self._classify_api(prompt, response, is_response=True)

    def _classify_local(
        self, prompt: str, response: str = None, is_response: bool = False
    ) -> SafetyResult:
        """Local inference with Transformers."""
        import torch

        # Build messages
        if is_response and response:
            messages = [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": response},
            ]
        else:
            messages = [{"role": "user", "content": prompt}]

        # Apply chat template
        text = self.tokenizer.apply_chat_template(messages, tokenize=False)

        # Tokenize
        model_inputs = self.tokenizer([text], return_tensors="pt")
        if torch.cuda.is_available():
            model_inputs = model_inputs.to(self.model.device)

        # Generate
        with torch.no_grad():
            generated_ids = self.model.generate(
                **model_inputs,
                max_new_tokens=128,
                do_sample=False,
                pad_token_id=self.tokenizer.eos_token_id,
            )

        # Decode
        output_ids = generated_ids[0][len(model_inputs.input_ids[0]) :].tolist()
        content = self.tokenizer.decode(output_ids, skip_special_tokens=True)

        return self._parse_output(content)

    def _classify_api(
        self, prompt: str, response: str = None, is_response: bool = False
    ) -> SafetyResult:
        """
        Remote inference via API with enterprise features.

        Includes: retry logic, circuit breaker, latency tracking.
        """
        start_time = time.perf_counter()
        self._metrics["total_requests"] += 1

        # Check circuit breaker
        if not self._check_circuit_breaker():
            logger.warning("Circuit breaker OPEN - returning safe default")
            return SafetyResult(
                level=SafetyLevel.SAFE,
                categories=[SafetyCategory.NONE],
                raw_output="circuit_breaker_open",
            )

        # Build messages
        if is_response and response:
            messages = [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": response},
            ]
        else:
            messages = [{"role": "user", "content": prompt}]

        # Retry loop with exponential backoff
        last_error = None
        for attempt in range(self._max_retries):
            try:
                completion = self.client.chat.completions.create(
                    model=self.MODEL_NAME,
                    messages=messages,
                    max_tokens=128,
                    temperature=0,
                )
                content = completion.choices[0].message.content

                # Success - record metrics
                latency = (time.perf_counter() - start_time) * 1000
                self._metrics["total_latency_ms"] += latency
                self._record_success()

                return self._parse_output(content)

            except Exception as e:
                last_error = e
                if attempt < self._max_retries - 1:
                    backoff = 2**attempt * 0.1  # 0.1, 0.2, 0.4s
                    logger.warning(f"API retry {attempt + 1}/{self._max_retries}: {e}")
                    time.sleep(backoff)

        # All retries failed
        self._record_failure()
        logger.error(f"API failed after {self._max_retries} retries: {last_error}")

        # Fallback: return safe (fail-open for availability)
        # For fail-closed behavior, raise the exception instead
        return SafetyResult(
            level=SafetyLevel.SAFE,
            categories=[SafetyCategory.NONE],
            raw_output=f"error:{last_error}",
        )

    def get_risk_score(self, result: SafetyResult) -> float:
        """
        Convert SafetyResult to risk score (0-100).

        Mapping:
        - Safe: 0
        - Controversial: 50
        - Unsafe: 100
        """
        if result.level == SafetyLevel.SAFE:
            return 0.0
        elif result.level == SafetyLevel.CONTROVERSIAL:
            return 50.0
        else:
            return 100.0
