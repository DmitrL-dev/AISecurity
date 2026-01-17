"""
SENTINEL Strike Dashboard - HYDRA Handler

HYDRA multi-head attack controller for LLM/AI targets.
Extracted from strike_console.py (lines 1736-1993).
"""

import asyncio
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

# Import state
try:
    from strike.dashboard.state import state, file_logger
except ImportError:
    from ..state import state, file_logger


@dataclass
class HydraConfig:
    """
    HYDRA attack configuration.
    """
    target: str
    attack_types: List[str] = field(default_factory=lambda: ["jailbreak"])
    mode: str = "phantom"  # phantom, aggressive, stealth
    
    # LLM settings
    llm_endpoint: str = "gemini"
    llm_model: str = "gemini-3-pro-flash"
    gemini_api_key: str = ""
    openai_api_key: str = ""
    
    # Proxy settings
    scraperapi_key: str = ""
    country: str = "us"
    
    @classmethod
    def from_request(cls, data: Dict) -> "HydraConfig":
        """Create config from Flask request data."""
        return cls(
            target=data.get("target", ""),
            attack_types=data.get("attack_types", ["jailbreak"]),
            mode=data.get("mode", "phantom"),
            llm_endpoint=data.get("llm_endpoint", "gemini"),
            llm_model=data.get("model", "gemini-3-pro-flash"),
            gemini_api_key=data.get("gemini_api_key", "") or os.environ.get("GEMINI_API_KEY", "") or os.environ.get("GOOGLE_API_KEY", ""),
            openai_api_key=data.get("openai_api_key", "") or os.environ.get("OPENAI_API_KEY", ""),
            scraperapi_key=data.get("scraperapi_key", ""),
            country=data.get("country", "us"),
        )
    
    def validate(self) -> List[str]:
        """Validate configuration."""
        errors = []
        if not self.target:
            errors.append("Target URL required")
        if not self.attack_types:
            errors.append("At least one attack type required")
        return errors


def log_event(event: Dict) -> None:
    """Log event to state and file logger."""
    # Add timestamp
    event["timestamp"] = datetime.now().isoformat()
    
    # Log to file
    file_logger.log(event)
    
    # Format message for queue
    msg_type = event.get("level", "info")
    message = event.get("message", "")
    formatted = f"[{msg_type.upper()}] {message}"
    
    # Add to queue for SSE
    state.log_event(formatted)


class HydraHandler:
    """
    HYDRA multi-head attack handler.
    
    Manages HYDRA attacks against LLM/AI targets with:
    - AI Detection
    - Multi-head attack execution
    - Proxy support
    - LLM-powered attack planning
    """
    
    def __init__(self):
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._results: List[Dict] = []
    
    @property
    def is_running(self) -> bool:
        """Check if HYDRA attack is running."""
        return self._running
    
    def start(self, config: HydraConfig, on_complete: Optional[Callable] = None) -> Dict:
        """
        Start HYDRA attack.
        
        Args:
            config: HYDRA configuration
            on_complete: Optional callback when complete
            
        Returns:
            Start status dict
        """
        if self._running:
            return {"error": "HYDRA attack already running", "status": "error"}
        
        errors = config.validate()
        if errors:
            return {"error": errors[0], "status": "error"}
        
        self._running = True
        self._results = []
        
        def run_hydra():
            try:
                asyncio.run(self._execute(config))
            except Exception as e:
                log_event({
                    "type": "log",
                    "message": f"❌ HYDRA error: {e}",
                    "level": "error",
                })
            finally:
                log_event({
                    "type": "log",
                    "message": "🐙 HYDRA thread finished",
                    "level": "info",
                })
                if on_complete:
                    on_complete(self._results)
        
        self._thread = threading.Thread(target=run_hydra, daemon=True)
        self._thread.start()
        
        return {
            "status": "started",
            "mode": "hydra",
            "target": config.target,
            "attack_types": config.attack_types,
        }
    
    async def _execute(self, config: HydraConfig) -> Dict:
        """Execute HYDRA attack async."""
        from strike.hydra import HydraAttackController
        
        controller = HydraAttackController()
        await controller.initialize(config.mode)
        
        # Initialize LLM if available
        llm = await self._setup_llm(config)
        
        # Setup proxy if configured
        if config.scraperapi_key:
            proxy_url = f"http://scraperapi:{config.scraperapi_key}@proxy-server.scraperapi.com:8001"
            controller.proxy_url = proxy_url
            log_event({
                "type": "log",
                "message": f"🏠 ScraperAPI Proxy: ENABLED (Country: {config.country.upper()})",
                "level": "attack",
            })
        else:
            log_event({
                "type": "log",
                "message": "⚠️ No proxy configured - using direct connection",
                "level": "warning",
            })
        
        # AI Detection scan
        await self._detect_ai(config.target)
        
        # Log attack start
        log_event({
            "type": "log",
            "message": f"🐙 HYDRA: Starting {config.mode.upper()} mode attack",
            "level": "attack",
        })
        log_event({
            "type": "log",
            "message": f"🎯 Target: {config.target}",
            "level": "info",
        })
        log_event({
            "type": "log",
            "message": f'⚔️ Attack types: {", ".join(config.attack_types)}',
            "level": "info",
        })
        
        # Execute attack
        result = await controller.execute_attack(config.target, config.attack_types, llm)
        
        # Log results
        findings = result.get("findings", [])
        log_event({
            "type": "log",
            "message": f"✅ HYDRA complete: {len(findings)} findings",
            "level": "finding" if findings else "info",
        })
        
        for finding in findings:
            log_event({
                "type": "finding",
                "severity": finding.get("severity", "medium"),
                "message": f"{finding.get('type')}: {finding.get('description', '')[:100]}",
            })
            self._results.append(finding)
            state.add_result(finding)
        
        return result
    
    async def _setup_llm(self, config: HydraConfig) -> Optional[Any]:
        """Setup LLM for attack planning."""
        try:
            from strike.ai import StrikeLLMManager
            from strike.ai.llm_manager import LLMConfig, LLMProvider
        except ImportError:
            return None
        
        try:
            log_event({
                "type": "log",
                "message": f"🔧 LLM Config: endpoint={config.llm_endpoint}, model={config.llm_model}",
                "level": "info",
            })
            
            if config.llm_endpoint == "gemini" and config.gemini_api_key:
                llm_config = LLMConfig(
                    provider=LLMProvider.GEMINI,
                    model=config.llm_model,
                    api_key=config.gemini_api_key,
                )
                llm = StrikeLLMManager(llm_config)
            elif config.llm_endpoint == "openai" and config.openai_api_key:
                llm_config = LLMConfig(
                    provider=LLMProvider.OPENAI,
                    model=config.llm_model,
                    api_key=config.openai_api_key,
                )
                llm = StrikeLLMManager(llm_config)
            else:
                log_event({
                    "type": "log",
                    "message": "⚠️ No API key provided - using auto-detect",
                    "level": "warning",
                })
                llm = StrikeLLMManager()
            
            log_event({
                "type": "log",
                "message": f"🧠 AI Attack Planner: {llm.config.provider.value}/{llm.config.model}",
                "level": "attack",
            })
            return llm
            
        except Exception as e:
            log_event({
                "type": "log",
                "message": f"⚠️ AI not available: {e}",
                "level": "warning",
            })
            return None
    
    async def _detect_ai(self, target: str) -> None:
        """Scan target for hidden AI."""
        log_event({
            "type": "log",
            "message": "🔍 Scanning for hidden AI...",
            "level": "info",
        })
        
        try:
            from strike.recon import AIDetector
            
            detector = AIDetector(timeout=10)
            result = await detector.detect(target)
            
            if result.detected:
                log_event({
                    "type": "log",
                    "message": f"🤖 HIDDEN AI DETECTED! Confidence: {result.confidence:.0%}",
                    "level": "finding",
                })
                log_event({
                    "type": "log",
                    "message": f"📍 AI Type: {result.ai_type}",
                    "level": "info",
                })
                if result.endpoints:
                    log_event({
                        "type": "log",
                        "message": f'🎯 AI Endpoints: {", ".join(result.endpoints[:3])}',
                        "level": "info",
                    })
            else:
                log_event({
                    "type": "log",
                    "message": f"❌ No hidden AI detected (confidence: {result.confidence:.0%})",
                    "level": "info",
                })
                
        except Exception as e:
            log_event({
                "type": "log",
                "message": f"⚠️ AI detection error: {e}",
                "level": "warning",
            })
    
    def get_results(self) -> List[Dict]:
        """Get attack results."""
        return self._results.copy()


# Global instance
hydra_handler = HydraHandler()
