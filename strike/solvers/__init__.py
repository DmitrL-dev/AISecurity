"""
Strike Solvers — Non-LLM Challenge Modules

Specialized solvers for challenges that don't involve LLM prompt injection:
- DataAnalysisSolver: numpy/image puzzles (arrayz challenges)
- MLAttackSolver: adversarial ML (cluster challenges) [TODO]
- CryptoSolver: cryptography challenges [TODO]
"""

from .data_analysis import DataAnalysisSolver, solve_arrayz

__all__ = [
    "DataAnalysisSolver",
    "solve_arrayz",
]
