"""
SENTINEL Shield v2.0 — Structural Detection Engine

Detects structural/format-based attacks:
1. Chat template injection (ChatML, Llama, Mistral delimiters)
2. Markdown/HTML injection (image exfil, XSS)
3. Multi-turn conversation hijacking
4. System prompt boundary violations
5. Tool/function call injection
"""

import re
import logging
from .base import BaseEngine, EngineResult, ThreatMatch

logger = logging.getLogger("shield.engines.structural")


class StructuralEngine(BaseEngine):
    """
    Structural analysis engine.

    Unlike regex (keyword matching), this engine understands
    document/prompt structure and detects format-level attacks.
    """

    def __init__(self, weight: float = 0.9):
        super().__init__(name="structural", weight=weight)

        # Chat template delimiters (attack surface)
        self._template_delimiters = [
            # ChatML (OpenAI, Qwen)
            (r"<\|im_start\|>", "ChatML im_start", 0.90),
            (r"<\|im_end\|>", "ChatML im_end", 0.90),
            (r"<\|system\|>", "ChatML system", 0.92),
            (r"<\|user\|>", "ChatML user", 0.85),
            (r"<\|assistant\|>", "ChatML assistant", 0.88),
            # Llama/Mistral
            (r"<<SYS>>|<</SYS>>", "Llama system delimiter", 0.95),
            (r"\[INST\]|\[/INST\]", "Llama instruction delimiter", 0.90),
            (r"<s>|</s>", "BOS/EOS token", 0.75),
            # Anthropic
            (r"\n\nHuman:\s", "Anthropic Human turn", 0.85),
            (r"\n\nAssistant:\s", "Anthropic Assistant turn", 0.88),
            # Generic
            (
                r"###\s*(System|Human|Assistant|User)\s*:",
                "Markdown role delimiter",
                0.85,
            ),
            (r"<\|endoftext\|>", "GPT end-of-text token", 0.80),
        ]

        # Tool/function call injection patterns
        self._tool_injection = [
            (r"<tool_call>|</tool_call>", "Tool call XML injection", 0.92),
            (r"<function_call>|</function_call>", "Function call XML injection", 0.92),
            (r"<tool_use>|</tool_use>", "Tool use XML injection", 0.90),
            (
                r'"name"\s*:\s*"[^"]+"\s*,\s*"arguments"\s*:',
                "JSON function call injection",
                0.80,
            ),
            (r"<invoke\s+name=", "MCP invoke injection", 0.95),
            (r"<invoke", "Anthropic tool invoke injection", 0.95),
        ]

        # Data exfiltration via markdown
        self._markdown_exfil = [
            (
                r"!\[.*?\]\(https?://[^)]*\?.*?=.*?\)",
                "Markdown image exfil with query params",
                0.85,
            ),
            (
                r"\[.*?\]\(https?://[^)]*\?.*?data=.*?\)",
                "Markdown link exfil with data param",
                0.80,
            ),
            (
                r"!\[.*?\]\(https?://(?!(?:github|imgur|i\.stack))[^)]+\)",
                "Markdown image to unknown host",
                0.60,
            ),
        ]

        # Compile all patterns
        self._compiled_delimiters = [
            (re.compile(pat, re.IGNORECASE), desc, risk)
            for pat, desc, risk in self._template_delimiters
        ]
        self._compiled_tools = [
            (re.compile(pat, re.IGNORECASE), desc, risk)
            for pat, desc, risk in self._tool_injection
        ]
        self._compiled_markdown = [
            (re.compile(pat, re.IGNORECASE), desc, risk)
            for pat, desc, risk in self._markdown_exfil
        ]

    def _check_nested_instructions(self, text: str) -> list[ThreatMatch]:
        """
        Detect nested instruction patterns.
        Example: text contains a "prompt within a prompt."
        """
        threats = []

        # Count instruction-like boundaries
        boundaries = 0
        boundary_patterns = [
            r"\[INST\]",
            r"\[/INST\]",
            r"<<SYS>>",
            r"<</SYS>>",
            r"<\|im_start\|>",
            r"<\|im_end\|>",
            r"### (System|Human|Assistant):",
        ]
        for bp in boundary_patterns:
            boundaries += len(re.findall(bp, text, re.IGNORECASE))

        if boundaries >= 3:
            threats.append(
                ThreatMatch(
                    threat_type="nested_instruction_injection",
                    risk_score=0.90,
                    engine=self.name,
                    description=f"Found {boundaries} instruction boundaries — possible nested injection",
                    category="structural",
                    metadata={"boundary_count": boundaries},
                )
            )

        return threats

    def _check_conversation_hijack(self, text: str) -> list[ThreatMatch]:
        """Detect conversation turn injection."""
        threats = []

        # Multiple role indicators in a single message
        roles_found = set()
        role_patterns = {
            "system": r"(?:system|System)\s*:",
            "user": r"(?:user|User|Human)\s*:",
            "assistant": r"(?:assistant|Assistant|AI)\s*:",
        }
        for role, pattern in role_patterns.items():
            if re.search(pattern, text):
                roles_found.add(role)

        if len(roles_found) >= 2:
            risk = 0.80 if "system" in roles_found else 0.65
            threats.append(
                ThreatMatch(
                    threat_type="conversation_hijack",
                    risk_score=risk,
                    engine=self.name,
                    description=f"Multiple conversation roles detected: {roles_found}",
                    category="structural",
                    metadata={"roles": list(roles_found)},
                )
            )

        return threats

    def analyze(self, text: str) -> EngineResult:
        threats: list[ThreatMatch] = []

        # 1. Template delimiter injection
        for compiled, desc, risk in self._compiled_delimiters:
            if compiled.search(text):
                threats.append(
                    ThreatMatch(
                        threat_type="template_delimiter_injection",
                        risk_score=risk,
                        engine=self.name,
                        description=desc,
                        category="structural",
                        matched_text=compiled.pattern[:50],
                    )
                )

        # 2. Tool/function call injection
        for compiled, desc, risk in self._compiled_tools:
            if compiled.search(text):
                threats.append(
                    ThreatMatch(
                        threat_type="tool_call_injection",
                        risk_score=risk,
                        engine=self.name,
                        description=desc,
                        category="structural",
                    )
                )

        # 3. Markdown exfiltration
        for compiled, desc, risk in self._compiled_markdown:
            m = compiled.search(text)
            if m:
                threats.append(
                    ThreatMatch(
                        threat_type="markdown_exfiltration",
                        risk_score=risk,
                        engine=self.name,
                        description=desc,
                        category="structural",
                        matched_text=m.group(0)[:100],
                    )
                )

        # 4. Nested instructions
        threats.extend(self._check_nested_instructions(text))

        # 5. Conversation hijacking
        threats.extend(self._check_conversation_hijack(text))

        max_risk = max((t.risk_score for t in threats), default=0.0)

        return EngineResult(
            engine_name=self.name,
            risk_score=max_risk,
            threats=threats,
        )
