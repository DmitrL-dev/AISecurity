"""
Strike Evasion Layer — Advanced filter bypass techniques.

Modules:
- token_splitter: Word splitting, leet speak, zero-width injection
- homoglyph: Unicode lookalike character injection
"""

from .token_splitter import TokenSplitter, get_evasion_variants, EVASION_PAYLOADS
from .homoglyph import HomoglyphInjector, evade_with_homoglyphs, HOMOGLYPH_PAYLOADS

__all__ = [
    "TokenSplitter",
    "HomoglyphInjector",
    "get_evasion_variants",
    "evade_with_homoglyphs",
    "EVASION_PAYLOADS",
    "HOMOGLYPH_PAYLOADS",
]
