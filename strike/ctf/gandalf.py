"""
SENTINEL Strike CTF - Gandalf Cracker

Crack all Gandalf levels using the Universal Controller.
Extracted from universal_controller.py (lines 1970-1994).
"""

import asyncio
from typing import Dict, Optional


async def crack_gandalf_all(
    max_attempts: int = 100,
    levels: list = None,
    verbose: bool = True,
) -> Dict[int, str]:
    """
    Crack all Gandalf levels with universal controller.
    
    Args:
        max_attempts: Max attempts per level
        levels: Specific levels to crack (default: 1-8)
        verbose: Print progress
        
    Returns:
        Dict mapping level number to extracted password
    """
    # Import here to avoid circular imports
    from strike.targets import GandalfTarget
    from strike.universal_controller import UniversalController
    
    if verbose:
        print("🧙 SENTINEL Strike — Gandalf Cracker")
        print("=" * 50)
    
    results = {}
    levels = levels or list(range(1, 9))
    
    for level in levels:
        if verbose:
            print(f"\n{'='*50}")
            print(f"🎯 LEVEL {level}")
        
        try:
            async with GandalfTarget(level=level) as target:
                controller = UniversalController(target)
                result = await controller.run(max_attempts=max_attempts)
                
                if result:
                    results[level] = result
                    if verbose:
                        print(f"✅ Level {level}: {result}")
                else:
                    if verbose:
                        print(f"❌ Level {level}: Failed")
        except Exception as e:
            if verbose:
                print(f"❌ Level {level}: Error - {e}")
    
    if verbose:
        print(f"\n{'='*50}")
        print(f"📊 SUMMARY: {len(results)}/{len(levels)} cracked")
        for level, pwd in sorted(results.items()):
            print(f"  Level {level}: {pwd}")
    
    return results


async def crack_gandalf_level(level: int, max_attempts: int = 100) -> Optional[str]:
    """
    Crack a single Gandalf level.
    
    Args:
        level: Level number (1-8)
        max_attempts: Max attempts
        
    Returns:
        Extracted password or None
    """
    from strike.targets import GandalfTarget
    from strike.universal_controller import UniversalController
    
    async with GandalfTarget(level=level) as target:
        controller = UniversalController(target)
        return await controller.run(max_attempts=max_attempts)


def run_gandalf(levels: list = None, max_attempts: int = 100) -> Dict[int, str]:
    """
    Sync wrapper for crack_gandalf_all.
    
    Args:
        levels: Levels to crack
        max_attempts: Max attempts per level
        
    Returns:
        Results dict
    """
    return asyncio.run(crack_gandalf_all(
        max_attempts=max_attempts,
        levels=levels,
    ))
