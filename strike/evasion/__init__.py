"""
SENTINEL Strike — Evasion Module

Block detection, automatic evasion, and WAF bypass for real-world pentesting.
"""

from .block_detector import (
    BlockType,
    BlockInfo,
    BlockDetector,
    EvasionEngine,
    WAF_SIGNATURES,
)

from .waf_bypass import (
    WAFBypass,
    HTTPBypass,
    BypassTechnique,
    BypassResult,
)

from .enterprise_bypass import (
    EnterpriseBypass,
    EnterpriseBypassConfig,
    AggressionLevel,
    BypassPayload,
    create_enterprise_bypass,
    AGGRESSION_LEVELS,
)

from .advanced_evasion import (
    TLSFingerprintSpoofer,
    BrowserImpersonation,
    HTTP2Bypass,
    RawSocketSmuggler,
    EliteBypass,
    AdvancedEvasionEngine,
    AdvancedEvasionConfig,
    create_advanced_evasion,
    BROWSER_PROFILES,
)

from .residential_proxy import (
    ResidentialProxyManager,
    ProxyProvider,
    ProxyConfig,
    create_scraperapi_proxy,
    create_goproxy,
    create_brightdata_proxy,
    create_custom_proxy,
    PROXY_PROVIDERS,
)

from .payload_mutator import (
    UltimatePayloadMutator,
    create_mutator,
    mutate_payload,
    get_waf_bypasses,
    MUTATION_TECHNIQUES,
)

# New advanced bypass modules
from .waf_fingerprinter import (
    WAFFingerprinter,
    WAFType,
    WAFRule,
    WAFProfile,
    fingerprinter,
)

from .adaptive_engine import (
    AdaptivePayloadEngine,
    TechniqueStats,
    BypassAttempt,
    adaptive_engine,
)

from .advanced_smuggling import (
    AdvancedSmuggling,
    SmuggleResult,
    smuggling,
)

from .ml_selector import (
    MLBypassSelector,
    PayloadFeatures,
    PredictionResult,
    ml_selector,
)

__all__ = [
    # Block Detection
    "BlockType",
    "BlockInfo",
    "BlockDetector",
    "EvasionEngine",
    "WAF_SIGNATURES",
    # WAF Bypass
    "WAFBypass",
    "HTTPBypass",
    "BypassTechnique",
    "BypassResult",
    # Enterprise Bypass
    "EnterpriseBypass",
    "EnterpriseBypassConfig",
    "AggressionLevel",
    "BypassPayload",
    "create_enterprise_bypass",
    "AGGRESSION_LEVELS",
    # Advanced Evasion
    "TLSFingerprintSpoofer",
    "BrowserImpersonation",
    "HTTP2Bypass",
    "RawSocketSmuggler",
    "EliteBypass",
    "AdvancedEvasionEngine",
    "AdvancedEvasionConfig",
    "create_advanced_evasion",
    "BROWSER_PROFILES",
    # Residential Proxy
    "ResidentialProxyManager",
    "ProxyProvider",
    "ProxyConfig",
    "create_scraperapi_proxy",
    "create_goproxy",
    "create_brightdata_proxy",
    "create_custom_proxy",
    "PROXY_PROVIDERS",
    # Payload Mutator
    "UltimatePayloadMutator",
    "create_mutator",
    "mutate_payload",
    "get_waf_bypasses",
    "MUTATION_TECHNIQUES",
    # WAF Fingerprinter
    "WAFFingerprinter",
    "WAFType",
    "WAFRule",
    "WAFProfile",
    "fingerprinter",
    # Adaptive Engine
    "AdaptivePayloadEngine",
    "TechniqueStats",
    "BypassAttempt",
    "adaptive_engine",
    # Advanced Smuggling
    "AdvancedSmuggling",
    "SmuggleResult",
    "smuggling",
    # ML Selector
    "MLBypassSelector",
    "PayloadFeatures",
    "PredictionResult",
    "ml_selector",
]
