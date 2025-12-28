"""
SENTINEL Strike — Universal Target Interface

Generic target abstraction for any AI red teaming target.
One controller, any target.
"""

import aiohttp
import re
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field


@dataclass
class TargetConfig:
    """Universal target configuration."""
    name: str
    url: str
    method: str = "POST"
    content_type: str = "form"  # "form" or "json"
    headers: Dict[str, str] = field(default_factory=dict)
    
    # Request field names
    prompt_field: str = "prompt"
    extra_fields: Dict[str, str] = field(default_factory=dict)
    
    # Response parsing
    response_field: str = "answer"  # JSON path to response text
    
    # Goal extraction patterns
    goal_patterns: List[str] = field(default_factory=lambda: [
        r"(?:password|secret|flag|key) is[:\s]+([A-Z0-9_]+)",
        r"([A-Z]{5,})",
    ])
    
    # Rate limiting
    delay_seconds: float = 0.3


class Target(ABC):
    """
    Abstract base class for red teaming targets.
    
    Implement this for any new target type.
    """
    
    def __init__(self, config: TargetConfig):
        self.config = config
        self._session: Optional[aiohttp.ClientSession] = None
    
    @abstractmethod
    async def send(self, payload: str) -> str:
        """
        Send attack payload to target.
        
        Args:
            payload: Attack prompt/payload string
            
        Returns:
            Response text from target
        """
        pass
    
    def extract_goal(self, response: str) -> Optional[str]:
        """
        Extract goal value (password, flag, etc) from response.
        
        Override for target-specific extraction logic.
        """
        for pattern in self.config.goal_patterns:
            matches = re.findall(pattern, response, re.I)
            for match in matches:
                value = match.upper() if isinstance(match, str) else match[0].upper()
                # Filter false positives
                if value not in ["SORRY", "CANNOT", "ERROR", "POLICY"]:
                    if len(value) >= 4:
                        return value
        return None
    
    async def __aenter__(self):
        self._session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, *args):
        if self._session:
            await self._session.close()


class HTTPTarget(Target):
    """
    Generic HTTP API target.
    
    Works with most REST API-based AI chat interfaces.
    """
    
    async def send(self, payload: str) -> str:
        """Send payload via HTTP."""
        if not self._session:
            self._session = aiohttp.ClientSession()
        
        # Build request data
        data = {self.config.prompt_field: payload}
        data.update(self.config.extra_fields)
        
        try:
            if self.config.content_type == "form":
                form = aiohttp.FormData()
                for k, v in data.items():
                    form.add_field(k, v)
                async with self._session.post(
                    self.config.url,
                    data=form,
                    headers=self.config.headers
                ) as resp:
                    return await self._parse_response(resp)
            else:
                async with self._session.post(
                    self.config.url,
                    json=data,
                    headers={"Content-Type": "application/json", **self.config.headers}
                ) as resp:
                    return await self._parse_response(resp)
                    
        except Exception as e:
            return f"Error: {e}"
    
    async def _parse_response(self, resp: aiohttp.ClientResponse) -> str:
        """Parse response from target."""
        if resp.status != 200:
            return f"Error: HTTP {resp.status}"
        
        try:
            data = await resp.json()
            # Navigate to response field
            result = data
            for key in self.config.response_field.split("."):
                result = result.get(key, "")
            return str(result)
        except:
            return await resp.text()


# ============================================================
# PRE-CONFIGURED TARGETS
# ============================================================

class GandalfTarget(HTTPTarget):
    """Lakera Gandalf CTF target."""
    
    LEVELS = {
        1: "baseline",
        2: "do-not-tell",
        3: "do-not-tell-and-block",
        4: "gpt-is-password-encoded",
        5: "word-blacklist",
        6: "gpt-blacklist",
        7: "gandalf",
        8: "gandalf-the-white",
    }
    
    def __init__(self, level: int = 1):
        defender = self.LEVELS.get(level, "baseline")
        config = TargetConfig(
            name=f"Gandalf Level {level}",
            url="https://gandalf-api.lakera.ai/api/send-message",
            content_type="form",
            prompt_field="prompt",
            extra_fields={"defender": defender},
            response_field="answer",
            goal_patterns=[
                r"password is[:\s]+([A-Z]+)",
                r"([A-Z]{5,})",
            ],
        )
        super().__init__(config)
        self.level = level


class CrucibleTarget(HTTPTarget):
    """
    Dreadnode Crucible CTF target.

    API endpoint: https://{challenge_id}.platform.dreadnode.io/score
    Requires API key from https://platform.dreadnode.io
    """

    def __init__(self, challenge_id: str, api_key: str):
        config = TargetConfig(
            name=f"Crucible {challenge_id}",
            url=f"https://{challenge_id}.platform.dreadnode.io/score",
            content_type="json",
            headers={"X-API-Key": api_key},
            prompt_field="data",
            response_field="output",  # Fixed: API returns 'output' not 'flag'
            goal_patterns=[
                r"gAAAAA[A-Za-z0-9_-]+",  # Crucible flag format
                r"flag\{([^}]+)\}",
                r"FLAG:[:\s]+(\S+)",
            ],
        )
        super().__init__(config)
        self.challenge_id = challenge_id


class OpenAITarget(HTTPTarget):
    """OpenAI-compatible API target."""
    
    def __init__(self, url: str, api_key: str, model: str = "gpt-4"):
        config = TargetConfig(
            name=f"OpenAI {model}",
            url=url,
            content_type="json",
            headers={"Authorization": f"Bearer {api_key}"},
            prompt_field="messages",
            response_field="choices.0.message.content",
        )
        super().__init__(config)
        self.model = model
    
    async def send(self, payload: str) -> str:
        """Override for OpenAI message format."""
        if not self._session:
            self._session = aiohttp.ClientSession()
        
        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": payload}],
        }
        
        try:
            async with self._session.post(
                self.config.url,
                json=data,
                headers=self.config.headers
            ) as resp:
                if resp.status != 200:
                    return f"Error: {resp.status}"
                result = await resp.json()
                return result.get("choices", [{}])[0].get("message", {}).get("content", "")
        except Exception as e:
            return f"Error: {e}"


class CustomTarget(HTTPTarget):
    """
    Fully customizable target.
    
    Example:
        target = CustomTarget(
            name="MyBot",
            url="https://api.mybot.com/chat",
            content_type="json",
            prompt_field="message",
            response_field="reply.text",
        )
    """
    
    def __init__(
        self,
        name: str,
        url: str,
        content_type: str = "json",
        prompt_field: str = "prompt",
        response_field: str = "response",
        extra_fields: Dict[str, str] = None,
        headers: Dict[str, str] = None,
        goal_patterns: List[str] = None,
    ):
        config = TargetConfig(
            name=name,
            url=url,
            content_type=content_type,
            prompt_field=prompt_field,
            response_field=response_field,
            extra_fields=extra_fields or {},
            headers=headers or {},
            goal_patterns=goal_patterns or [r"([A-Z]{5,})"],
        )
        super().__init__(config)


# ============================================================
# TARGET FACTORY
# ============================================================

def create_target(target_type: str, **kwargs) -> Target:
    """
    Factory function to create targets.
    
    Examples:
        create_target("gandalf", level=3)
        create_target("crucible", challenge_id="pwn1", api_key="...")
        create_target("custom", url="...", prompt_field="msg")
    """
    targets = {
        "gandalf": GandalfTarget,
        "crucible": CrucibleTarget,
        "openai": OpenAITarget,
        "custom": CustomTarget,
    }
    
    if target_type not in targets:
        raise ValueError(f"Unknown target: {target_type}. Available: {list(targets.keys())}")
    
    return targets[target_type](**kwargs)
