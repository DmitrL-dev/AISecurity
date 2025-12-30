"""
FastAPI Integration — SENTINEL middleware for FastAPI.

Automatically scans requests for security threats.
"""

from typing import Callable, List, Optional
import logging

logger = logging.getLogger(__name__)


class SentinelMiddleware:
    """
    FastAPI/Starlette middleware for SENTINEL.
    
    Automatically scans incoming requests for threats.
    
    Usage:
        >>> from fastapi import FastAPI
        >>> from sentinel.integrations.fastapi import SentinelMiddleware
        >>> 
        >>> app = FastAPI()
        >>> app.add_middleware(SentinelMiddleware)
    """
    
    def __init__(
        self,
        app,
        engines: List[str] = None,
        on_threat: str = "block",  # block, log, raise
        exclude_paths: List[str] = None,
        threshold: float = 0.5,
    ):
        self.app = app
        self.engines = engines
        self.on_threat = on_threat
        self.exclude_paths = exclude_paths or ["/health", "/metrics"]
        self.threshold = threshold
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Check excluded paths
        path = scope.get("path", "")
        if any(path.startswith(p) for p in self.exclude_paths):
            await self.app(scope, receive, send)
            return
        
        # Get request body
        body = b""
        
        async def receive_wrapper():
            nonlocal body
            message = await receive()
            if message["type"] == "http.request":
                body = message.get("body", b"")
            return message
        
        # Scan the request body
        try:
            if body:
                from sentinel import scan
                
                prompt = body.decode("utf-8", errors="ignore")
                result = scan(prompt, engines=self.engines)
                
                if result.risk_score >= self.threshold:
                    logger.warning(
                        f"Threat detected: risk={result.risk_score}, "
                        f"path={path}"
                    )
                    
                    if self.on_threat == "block":
                        # Return 403 Forbidden
                        await send({
                            "type": "http.response.start",
                            "status": 403,
                            "headers": [[b"content-type", b"application/json"]],
                        })
                        await send({
                            "type": "http.response.body",
                            "body": b'{"error": "Request blocked by SENTINEL"}',
                        })
                        return
                    
                    elif self.on_threat == "raise":
                        raise SecurityThreatError(result)
        
        except ImportError:
            logger.debug("SENTINEL scan not available")
        except Exception as e:
            logger.error(f"SENTINEL middleware error: {e}")
        
        await self.app(scope, receive_wrapper, send)


class SecurityThreatError(Exception):
    """Raised when a security threat is detected."""
    
    def __init__(self, result):
        self.result = result
        super().__init__(f"Security threat detected: risk={result.risk_score}")
