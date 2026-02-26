"""
SENTINEL Brain API - Streaming Response

Server-Sent Events (SSE) for real-time progress updates.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Optional

from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)


@dataclass
class StreamEvent:
    """SSE event."""
    event: str
    data: Any
    id: Optional[str] = None
    retry: Optional[int] = None
    
    def format(self) -> str:
        """Format as SSE message."""
        lines = []
        
        if self.id:
            lines.append(f"id: {self.id}")
        if self.event:
            lines.append(f"event: {self.event}")
        if self.retry:
            lines.append(f"retry: {self.retry}")
        
        # Data can be multiline
        data_str = json.dumps(self.data) if not isinstance(self.data, str) else self.data
        for line in data_str.split("\n"):
            lines.append(f"data: {line}")
        
        return "\n".join(lines) + "\n\n"


class StreamingAnalyzer:
    """
    Streaming analyzer with progress updates.
    
    Sends SSE events for:
    - progress: Percentage complete
    - layer: Current analysis layer
    - finding: Detected threat
    - complete: Final result
    - error: Error occurred
    """
    
    def __init__(self, analyzer):
        """
        Initialize streaming analyzer.
        
        Args:
            analyzer: Core SentinelAnalyzer instance
        """
        self.analyzer = analyzer
    
    async def analyze_stream(
        self,
        text: str,
        profile: str = "standard",
    ) -> AsyncGenerator[str, None]:
        """
        Stream analysis with progress updates.
        
        Yields:
            SSE formatted events
        """
        start_time = time.time()
        
        try:
            # Start event
            yield StreamEvent(
                event="start",
                data={"text_length": len(text), "profile": profile},
            ).format()
            
            # Get engine list
            engines = self._get_engines_for_profile(profile)
            total_engines = len(engines)
            
            all_findings = []
            
            for i, engine_name in enumerate(engines, 1):
                # Progress update
                progress = int((i / total_engines) * 100)
                yield StreamEvent(
                    event="progress",
                    data={
                        "percent": progress,
                        "layer": engine_name,
                        "current": i,
                        "total": total_engines,
                    },
                ).format()
                
                # Run engine
                try:
                    result = await self._run_engine(engine_name, text)
                    
                    if result and result.get("threats"):
                        for threat in result["threats"]:
                            finding = {
                                "engine": engine_name,
                                "threat": threat,
                                "risk": result.get("risk_score", 0),
                            }
                            all_findings.append(finding)
                            
                            yield StreamEvent(
                                event="finding",
                                data=finding,
                            ).format()
                    
                except Exception as e:
                    logger.warning(f"Engine {engine_name} error: {e}")
                    yield StreamEvent(
                        event="warning",
                        data={"engine": engine_name, "error": str(e)},
                    ).format()
                
                # Small delay between engines
                await asyncio.sleep(0.01)
            
            # Complete event
            elapsed = time.time() - start_time
            
            yield StreamEvent(
                event="complete",
                data={
                    "findings_count": len(all_findings),
                    "elapsed_ms": elapsed * 1000,
                    "verdict": "block" if all_findings else "allow",
                },
            ).format()
            
        except Exception as e:
            logger.error(f"Streaming analysis error: {e}")
            yield StreamEvent(
                event="error",
                data={"message": str(e)},
            ).format()
    
    def _get_engines_for_profile(self, profile: str) -> list:
        """Get engine list for profile."""
        profiles = {
            "lite": ["regex", "keyword"],
            "standard": ["regex", "semantic", "structural"],
            "enterprise": [
                "regex", "semantic", "structural",
                "behavioral", "context", "yara",
            ],
        }
        return profiles.get(profile, profiles["standard"])
    
    async def _run_engine(self, engine_name: str, text: str) -> Optional[dict]:
        """Run single engine."""
        # Placeholder - would delegate to actual engines
        await asyncio.sleep(0.1)  # Simulate processing
        
        # Return mock result for demo
        if engine_name == "regex":
            return self._check_regex(text)
        
        return {"threats": [], "risk_score": 0}
    
    def _check_regex(self, text: str) -> dict:
        """Quick regex check."""
        import re
        
        threats = []
        patterns = [
            (r"ignore.*previous.*instructions?", "instruction_override"),
            (r"jailbreak|bypass|override", "jailbreak_attempt"),
        ]
        
        for pattern, threat in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                threats.append(threat)
        
        return {
            "threats": threats,
            "risk_score": 0.8 if threats else 0,
        }


def create_streaming_response(
    generator: AsyncGenerator[str, None],
) -> StreamingResponse:
    """
    Create FastAPI StreamingResponse for SSE.
    
    Args:
        generator: Async generator yielding SSE events
        
    Returns:
        StreamingResponse with correct headers
    """
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def heartbeat_generator(
    interval: float = 15.0,
) -> AsyncGenerator[str, None]:
    """
    Generate heartbeat events to keep connection alive.
    
    Args:
        interval: Seconds between heartbeats
        
    Yields:
        SSE heartbeat events
    """
    while True:
        yield StreamEvent(
            event="heartbeat",
            data={"timestamp": time.time()},
        ).format()
        await asyncio.sleep(interval)
