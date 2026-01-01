"""
Pytest configuration - add src/brain to Python path.
"""
import sys
from pathlib import Path

# Add src/brain to path for engine imports
root = Path(__file__).parent
sys.path.insert(0, str(root / "src" / "brain"))
