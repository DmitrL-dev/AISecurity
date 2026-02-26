"""
SENTINEL Strike — Attack Payloads Package

800+ attack payloads for comprehensive penetration testing.
"""

from .attack_payloads import (
    SQLI_PAYLOADS,
    XSS_PAYLOADS,
    LFI_PAYLOADS,
    SSRF_PAYLOADS,
    CMDI_PAYLOADS,
    XXE_PAYLOADS,
    SSTI_PAYLOADS,
    NOSQL_PAYLOADS,
    LDAP_PAYLOADS,
    CRLF_PAYLOADS,
    AUTH_BYPASS_HEADERS,
    COMMON_CREDENTIALS,
    get_all_payloads,
    get_payload_counts,
)

from .extended_payloads import (
    GRAPHQL_PAYLOADS,
    JWT_PAYLOADS,
    JWT_ATTACK_PATTERNS,
    WEBSOCKET_PAYLOADS,
    API_PAYLOADS,
    API_TEST_HEADERS,
    OAUTH_PAYLOADS,
    DESERIALIZATION_PAYLOADS,
    PROTOTYPE_POLLUTION_PAYLOADS,
    CACHE_POISONING_PAYLOADS,
    RACE_CONDITION_PAYLOADS,
    HOST_HEADER_PAYLOADS,
    get_extended_payloads,
    get_extended_payload_counts,
)


def get_total_payload_counts():
    """Get combined payload counts from all libraries."""
    base = get_payload_counts()
    extended = get_extended_payload_counts()

    combined = {}
    for k, v in base.items():
        if k != "total":
            combined[k] = v
    for k, v in extended.items():
        if k != "total":
            combined[k] = v

    combined["GRAND_TOTAL"] = base["total"] + extended["total"]
    return combined


__all__ = [
    # Base payloads
    "SQLI_PAYLOADS",
    "XSS_PAYLOADS",
    "LFI_PAYLOADS",
    "SSRF_PAYLOADS",
    "CMDI_PAYLOADS",
    "XXE_PAYLOADS",
    "SSTI_PAYLOADS",
    "NOSQL_PAYLOADS",
    "LDAP_PAYLOADS",
    "CRLF_PAYLOADS",
    "AUTH_BYPASS_HEADERS",
    "COMMON_CREDENTIALS",
    "get_all_payloads",
    "get_payload_counts",
    # Extended payloads
    "GRAPHQL_PAYLOADS",
    "JWT_PAYLOADS",
    "JWT_ATTACK_PATTERNS",
    "WEBSOCKET_PAYLOADS",
    "API_PAYLOADS",
    "API_TEST_HEADERS",
    "OAUTH_PAYLOADS",
    "DESERIALIZATION_PAYLOADS",
    "PROTOTYPE_POLLUTION_PAYLOADS",
    "CACHE_POISONING_PAYLOADS",
    "RACE_CONDITION_PAYLOADS",
    "HOST_HEADER_PAYLOADS",
    "get_extended_payloads",
    "get_extended_payload_counts",
    "get_total_payload_counts",
]
