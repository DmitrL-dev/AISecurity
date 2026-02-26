#!/usr/bin/env python3
"""
SENTINEL Strike — AI-Powered LLM Manager

Multi-provider support:
- OpenRouter (Claude, GPT-4, Llama, Mistral)
- Ollama (local models)
- Google Gemini
- Anthropic direct
- OpenAI direct

Based on NeuroSploit llm_manager.py patterns with enhancements.
"""

import os
import json
import socket
import logging
from typing import Dict, List, Optional
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class LLMProvider(Enum):
    """Supported LLM providers."""
    OPENROUTER = "openrouter"
    OLLAMA = "ollama"
    GEMINI = "gemini"
    ANTHROPIC = "anthropic"
    OPENAI = "openai"


@dataclass
class LLMConfig:
    """Configuration for LLM provider."""
    provider: LLMProvider
    model: str
    api_key: str = ""
    base_url: str = ""
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: int = 120


class StrikeLLMManager:
    """
    Unified LLM interface for Strike operations.

    Features:
    - Multi-provider support with auto-detection
    - Async generation
    - JSON mode for structured output
    - Specialized attack planning methods
    - Hallucination mitigation (optional)
    """

    PROVIDER_URLS = {
        LLMProvider.OPENROUTER: "https://openrouter.ai/api/v1/chat/completions",
        LLMProvider.OLLAMA: "http://localhost:11434/api/generate",
        LLMProvider.GEMINI: "https://generativelanguage.googleapis.com/v1beta/models",
        LLMProvider.ANTHROPIC: "https://api.anthropic.com/v1/messages",
        LLMProvider.OPENAI: "https://api.openai.com/v1/chat/completions"
    }

    DEFAULT_MODELS = {
        LLMProvider.OPENROUTER: "anthropic/claude-sonnet-4.5",
        LLMProvider.OLLAMA: "llama3:8b",
        LLMProvider.GEMINI: "gemini-3-flash-preview",
        LLMProvider.ANTHROPIC: "claude-sonnet-4.5",
        LLMProvider.OPENAI: "gpt-4o"
    }

    def __init__(self, config: Optional[LLMConfig] = None):
        """
        Initialize LLM Manager.

        Args:
            config: Optional LLMConfig. If None, auto-detects available provider.
        """
        self.config = config or self._auto_detect_config()
        self._session = None
        self._hallucination_mitigation = False

        logger.info(
            "StrikeLLMManager initialized: %s/%s",
            self.config.provider.value, self.config.model
        )

    def _auto_detect_config(self) -> LLMConfig:
        """
        Auto-detect available LLM provider.

        Priority: OpenRouter > Gemini > Anthropic > OpenAI > Ollama
        """
        # Check OpenRouter
        if os.getenv('OPENROUTER_API_KEY'):
            return LLMConfig(
                provider=LLMProvider.OPENROUTER,
                model=self.DEFAULT_MODELS[LLMProvider.OPENROUTER],
                api_key=os.getenv('OPENROUTER_API_KEY')
            )

        # Check Gemini
        if os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY'):
            return LLMConfig(
                provider=LLMProvider.GEMINI,
                model=self.DEFAULT_MODELS[LLMProvider.GEMINI],
                api_key=os.getenv('GEMINI_API_KEY') or os.getenv(
                    'GOOGLE_API_KEY')
            )

        # Check Anthropic
        if os.getenv('ANTHROPIC_API_KEY'):
            return LLMConfig(
                provider=LLMProvider.ANTHROPIC,
                model=self.DEFAULT_MODELS[LLMProvider.ANTHROPIC],
                api_key=os.getenv('ANTHROPIC_API_KEY')
            )

        # Check OpenAI
        if os.getenv('OPENAI_API_KEY'):
            return LLMConfig(
                provider=LLMProvider.OPENAI,
                model=self.DEFAULT_MODELS[LLMProvider.OPENAI],
                api_key=os.getenv('OPENAI_API_KEY')
            )

        # Check Ollama (local)
        if self._check_ollama():
            return LLMConfig(
                provider=LLMProvider.OLLAMA,
                model=self.DEFAULT_MODELS[LLMProvider.OLLAMA]
            )

        raise ValueError(
            "No LLM provider available. Set one of: "
            "OPENROUTER_API_KEY, GEMINI_API_KEY, ANTHROPIC_API_KEY, "
            "OPENAI_API_KEY, or run Ollama locally."
        )

    def _check_ollama(self) -> bool:
        """Check if Ollama is running locally."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', 11434))
            sock.close()
            return result == 0
        except Exception:
            return False

    async def _get_session(self):
        """Get or create aiohttp session."""
        if self._session is None:
            import aiohttp
            self._session = aiohttp.ClientSession()
        return self._session

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_mode: bool = False,
        temperature: Optional[float] = None
    ) -> str:
        """
        Generate response from LLM.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            json_mode: If True, request JSON output
            temperature: Override default temperature

        Returns:
            Generated text response
        """
        temp = temperature or self.config.temperature

        try:
            if self.config.provider == LLMProvider.OPENROUTER:
                return await self._generate_openrouter(prompt, system_prompt, json_mode, temp)
            elif self.config.provider == LLMProvider.OLLAMA:
                return await self._generate_ollama(prompt, system_prompt, json_mode, temp)
            elif self.config.provider == LLMProvider.GEMINI:
                return await self._generate_gemini(prompt, system_prompt, temp)
            elif self.config.provider == LLMProvider.ANTHROPIC:
                return await self._generate_anthropic(prompt, system_prompt, temp)
            elif self.config.provider == LLMProvider.OPENAI:
                return await self._generate_openai(prompt, system_prompt, json_mode, temp)
            else:
                raise ValueError(
                    f"Unsupported provider: {self.config.provider}")
        except Exception as e:
            logger.error("LLM generation error: %s", e)
            return f"Error: {str(e)}"

    async def _generate_openrouter(
        self, prompt: str, system: Optional[str], json_mode: bool, temp: float
    ) -> str:
        """Generate via OpenRouter API."""
        session = await self._get_session()

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://sentinel-strike.local",
            "X-Title": "SENTINEL Strike"
        }

        data = {
            "model": self.config.model,
            "messages": messages,
            "temperature": temp,
            "max_tokens": self.config.max_tokens
        }

        if json_mode:
            data["response_format"] = {"type": "json_object"}

        async with session.post(
            self.PROVIDER_URLS[LLMProvider.OPENROUTER],
            headers=headers,
            json=data,
            timeout=self.config.timeout
        ) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                raise Exception(
                    f"OpenRouter API error {resp.status}: {error_text}")
            result = await resp.json()
            return result['choices'][0]['message']['content']

    async def _generate_ollama(
        self, prompt: str, system: Optional[str], json_mode: bool, temp: float
    ) -> str:
        """Generate via local Ollama."""
        session = await self._get_session()

        data = {
            "model": self.config.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temp,
                "num_predict": self.config.max_tokens
            }
        }

        if system:
            data["system"] = system

        if json_mode:
            data["format"] = "json"

        async with session.post(
            self.PROVIDER_URLS[LLMProvider.OLLAMA],
            json=data,
            timeout=self.config.timeout
        ) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                raise Exception(f"Ollama error {resp.status}: {error_text}")
            result = await resp.json()
            return result.get('response', '')

    async def _generate_gemini(
        self, prompt: str, system: Optional[str], temp: float
    ) -> str:
        """Generate via Google Gemini API."""
        session = await self._get_session()

        url = (
            f"{self.PROVIDER_URLS[LLMProvider.GEMINI]}"
            f"/{self.config.model}:generateContent"
            f"?key={self.config.api_key}"
        )

        full_prompt = prompt
        if system:
            full_prompt = f"{system}\n\n{prompt}"

        data = {
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {
                "temperature": temp,
                "maxOutputTokens": self.config.max_tokens
            }
        }

        async with session.post(url, json=data, timeout=self.config.timeout) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                raise Exception(
                    f"Gemini API error {resp.status}: {error_text}")
            result = await resp.json()
            return result['candidates'][0]['content']['parts'][0]['text']

    async def _generate_anthropic(
        self, prompt: str, system: Optional[str], temp: float
    ) -> str:
        """Generate via Anthropic API."""
        session = await self._get_session()

        headers = {
            "x-api-key": self.config.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        data = {
            "model": self.config.model,
            "max_tokens": self.config.max_tokens,
            "temperature": temp,
            "messages": [{"role": "user", "content": prompt}]
        }

        if system:
            data["system"] = system

        async with session.post(
            self.PROVIDER_URLS[LLMProvider.ANTHROPIC],
            headers=headers,
            json=data,
            timeout=self.config.timeout
        ) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                raise Exception(
                    f"Anthropic API error {resp.status}: {error_text}")
            result = await resp.json()
            return result['content'][0]['text']

    async def _generate_openai(
        self, prompt: str, system: Optional[str], json_mode: bool, temp: float
    ) -> str:
        """Generate via OpenAI API."""
        session = await self._get_session()

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": self.config.model,
            "messages": messages,
            "temperature": temp,
            "max_tokens": self.config.max_tokens
        }

        if json_mode:
            data["response_format"] = {"type": "json_object"}

        async with session.post(
            self.PROVIDER_URLS[LLMProvider.OPENAI],
            headers=headers,
            json=data,
            timeout=self.config.timeout
        ) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                raise Exception(
                    f"OpenAI API error {resp.status}: {error_text}")
            result = await resp.json()
            return result['choices'][0]['message']['content']

    # ========================================================================
    # SPECIALIZED ATTACK PLANNING METHODS
    # ========================================================================

    async def plan_exploitation(
        self,
        findings: List[Dict],
        target_info: Dict
    ) -> Dict:
        """
        AI-powered exploit planning.

        Args:
            findings: List of vulnerability findings
            target_info: Target information (url, waf, etc.)

        Returns:
            Exploitation plan with prioritized steps
        """
        from .prompts import EXPLOIT_EXPERT

        prompt = f"""Analyze these security findings and create an exploitation plan:

TARGET: {target_info.get('url', 'unknown')}
WAF DETECTED: {target_info.get('waf', 'unknown')}

FINDINGS:
{json.dumps(findings, indent=2)}

Provide a JSON response with:
{{
    "priority_order": ["list of finding IDs by priority"],
    "exploitation_steps": [
        {{
            "finding_id": "...",
            "technique": "...",
            "payload": "...",
            "bypass_method": "...",
            "success_probability": 0.0-1.0
        }}
    ],
    "evasion_recommendations": ["..."],
    "estimated_total_success": 0.0-1.0
}}"""

        response = await self.generate(prompt, EXPLOIT_EXPERT, json_mode=True)

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {"raw_response": response, "error": "Failed to parse JSON"}

    async def analyze_block(
        self,
        request_info: Dict,
        response_info: Dict,
        waf_type: str = "unknown"
    ) -> Dict:
        """
        Analyze WAF block and suggest bypasses.

        Args:
            request_info: Request details (url, method, payload)
            response_info: Response details (status, headers, body)
            waf_type: Detected WAF type

        Returns:
            Bypass suggestions with confidence scores
        """
        from .prompts import WAF_BYPASS_EXPERT

        prompt = f"""WAF blocked this request. Analyze and suggest bypass techniques:

WAF TYPE: {waf_type}

REQUEST:
- URL: {request_info.get('url', 'unknown')}
- Method: {request_info.get('method', 'GET')}
- Payload: {request_info.get('payload', 'none')}

BLOCK RESPONSE:
- Status: {response_info.get('status_code', 'unknown')}
- Headers: {json.dumps(response_info.get('headers', {}), indent=2)}
- Body snippet: {str(response_info.get('body', ''))[:500]}

Provide JSON with bypass suggestions:
{{
    "block_reason": "detected pattern/rule",
    "bypass_techniques": [
        {{
            "technique": "technique name",
            "modified_payload": "ready-to-use payload",
            "explanation": "why this works",
            "confidence": 0.0-1.0
        }}
    ],
    "alternative_vectors": ["other attack approaches"],
    "overall_confidence": 0.0-1.0
}}"""

        response = await self.generate(prompt, WAF_BYPASS_EXPERT, json_mode=True)

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {"raw_response": response, "error": "Failed to parse JSON"}

    async def generate_custom_payload(
        self,
        vuln_type: str,
        context: Dict
    ) -> str:
        """
        Generate custom exploit payload using AI.

        Args:
            vuln_type: Vulnerability type (sqli, xss, ssrf, etc.)
            context: Context information (url, param, waf, etc.)

        Returns:
            Generated payload string
        """
        from .prompts import PAYLOAD_MUTATOR

        prompt = f"""Generate a custom {vuln_type.upper()} payload for this context:

TARGET: {context.get('url', 'unknown')}
PARAMETER: {context.get('param', 'unknown')}
INJECTION CONTEXT: {context.get('context', 'unknown')}
WAF: {context.get('waf', 'none detected')}
BACKEND: {context.get('backend', 'unknown')}

Requirements:
1. Must bypass {context.get('waf', 'WAF')} detection
2. Use advanced obfuscation
3. Minimal footprint
4. Maintain payload functionality

Return ONLY the payload, no explanation or markdown."""

        return await self.generate(prompt, PAYLOAD_MUTATOR, temperature=0.8)

    async def analyze_response(
        self,
        payload: str,
        response: str,
        vuln_type: str
    ) -> Dict:
        """
        Analyze response to determine if exploit was successful.

        Args:
            payload: Payload that was sent
            response: Response received
            vuln_type: Type of vulnerability being tested

        Returns:
            Analysis with success determination and evidence
        """
        from .prompts import EXPLOIT_EXPERT

        prompt = f"""Analyze this response to determine if the {vuln_type} exploit was successful:

PAYLOAD SENT:
{payload}

RESPONSE RECEIVED (first 2000 chars):
{response[:2000]}

Provide JSON analysis:
{{
    "success": true/false,
    "confidence": 0.0-1.0,
    "evidence": "what indicates success/failure",
    "data_extracted": "any sensitive data found",
    "next_steps": ["recommended follow-up actions"]
}}"""

        response_text = await self.generate(prompt, EXPLOIT_EXPERT, json_mode=True)

        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            return {"raw_response": response_text, "success": False}

    async def close(self):
        """Close HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None


# Synchronous wrapper for non-async contexts
def create_llm_manager(config: Optional[LLMConfig] = None) -> StrikeLLMManager:
    """Create LLM manager instance."""
    return StrikeLLMManager(config)
