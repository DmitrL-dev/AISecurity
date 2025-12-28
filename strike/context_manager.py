#!/usr/bin/env python3
"""
SENTINEL Strike v3.0 — Context Manager

200K token context management with auto-summarization.
Based on ARTEMIS pattern: preserve recent context, summarize old.
"""

import logging
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class Message:
    """Conversation message."""
    role: str
    content: str
    timestamp: datetime = None
    tokens: int = 0

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.tokens == 0:
            # Rough estimate: 1 token ≈ 4 chars
            self.tokens = len(self.content) // 4


class ContextManager:
    """
    Manages conversation context with 200K token limit.

    Features:
    - Auto-summarization when approaching limit
    - Preserves recent N messages
    - Token counting (approximate)
    """

    def __init__(
        self,
        max_tokens: int = 200_000,
        buffer_tokens: int = 15_000,
        summary_model: str = "gpt-4o-mini"
    ):
        self.max_tokens = max_tokens
        self.buffer_tokens = buffer_tokens
        self.summary_model = summary_model

        self._total_tokens = 0
        self._summaries: List[str] = []

    def count_tokens(self, messages: List[Message]) -> int:
        """Count total tokens in messages."""
        return sum(m.tokens for m in messages)

    def should_summarize(self, messages: List[Message]) -> bool:
        """Check if summarization is needed."""
        total = self.count_tokens(messages)
        threshold = self.max_tokens - self.buffer_tokens

        if total > threshold:
            logger.info(
                f"📊 Context: {total:,} tokens (threshold: {threshold:,})")
            return True
        return False

    async def summarize(
        self,
        messages: List[Message],
        preserve_recent: int = 20
    ) -> List[Message]:
        """
        Summarize old messages, preserve recent ones.

        Args:
            messages: Full conversation history
            preserve_recent: Number of recent messages to keep intact

        Returns:
            New message list with summary + recent messages
        """
        if len(messages) <= preserve_recent:
            return messages

        # Split messages
        old_messages = messages[:-preserve_recent]
        recent_messages = messages[-preserve_recent:]

        # Generate summary of old messages
        summary = await self._generate_summary(old_messages)

        # Create summary message
        summary_msg = Message(
            role="system",
            content=f"[CONTEXT SUMMARY]\n{summary}\n[END SUMMARY]",
        )

        self._summaries.append(summary)

        logger.info(
            f"📝 Summarized {len(old_messages)} messages → "
            f"{summary_msg.tokens} tokens"
        )

        # Return: summary + recent
        return [summary_msg] + recent_messages

    async def _generate_summary(self, messages: List[Message]) -> str:
        """Generate summary of messages using LLM."""

        # Format messages for summarization
        context = "\n".join([
            f"[{m.role}]: {m.content[:200]}..."
            for m in messages[-50:]  # Last 50 of old messages
        ])

        prompt = f"""Summarize the following conversation context concisely.
Focus on:
- Key decisions made
- Successful attack vectors
- Failed approaches (to avoid repeating)
- Important findings

Context:
{context}

Summary (max 500 words):"""

        # Try to use LLM, fallback to simple summary
        try:
            # Use Google Generative AI for summarization
            import os

            api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get(
                "GEMINI_API_KEY"
            )

            if api_key:
                try:
                    import google.generativeai as genai

                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel("gemini-2.0-flash-exp")
                    response = model.generate_content(prompt)
                    return response.text
                except ImportError:
                    logger.debug("google-generativeai not installed, using fallback")
                except Exception as e:
                    logger.warning(f"Gemini API error: {e}")

            # Fallback: extractive summary
            summary_parts = []

            # Extract key events
            for m in messages:
                if "SUCCESS" in m.content:
                    summary_parts.append(f"✅ {m.content[:100]}")
                elif "FAILED" in m.content and len(summary_parts) < 10:
                    summary_parts.append(f"❌ {m.content[:50]}")

            if summary_parts:
                return "\n".join(summary_parts[:20])
            else:
                return f"Processed {len(messages)} messages. No significant findings."

        except Exception as e:
            logger.warning(f"Summary generation failed: {e}")
            return f"Processed {len(messages)} messages."

    def add_message(self, messages: List[Message], message: Message) -> List[Message]:
        """Add message and return updated list."""
        messages.append(message)
        return messages

    def get_stats(self) -> dict:
        """Get context statistics."""
        return {
            "max_tokens": self.max_tokens,
            "buffer_tokens": self.buffer_tokens,
            "summaries_created": len(self._summaries),
        }
