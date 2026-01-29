"""
SENTINEL Brain Analyzer - Re-export for backward compatibility.

The actual implementation is in core.analyzer.
This file provides the old import path: from src.brain.analyzer import SentinelAnalyzer
"""

from src.brain.core.analyzer import SentinelAnalyzer

__all__ = ["SentinelAnalyzer"]
