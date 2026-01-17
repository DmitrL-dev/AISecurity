"""
SENTINEL Strike CTF - Crucible Cracker

Crack Crucible CTF challenges using the Universal Controller.
Extracted from universal_controller.py (lines 1997-2328).
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional


# All Crucible challenges organized by difficulty
CRUCIBLE_CHALLENGES = [
    # Easy tier
    "pieceofcake",
    "bear1", "bear2", "bear3", "bear4",
    "whatistheflag", "whatistheflag2", "whatistheflag3",
    "whatistheflag4", "whatistheflag5", "whatistheflag6",
    # Prompt injection
    "puppeteer1", "puppeteer2", "puppeteer3", "puppeteer4",
    "brig1", "brig2",
    "squeeze1", "squeeze2", "squeeze3",
    # Extraction
    "extractor", "extractor2",
    "probe", "probe2",
    # Stealth/encoding
    "blindspot", "hush", "mumble",
    "passphrase", "secretsloth",
    # Adversarial images
    "granny", "granny2",
    "hotdog", "fiftycats", "pixelated",
    # Data analysis
    "voyager", "voyager2",
    "forensics", "audit",
    # Advanced
    "autopilot1", "autopilot2", "autopilot3",
    "cluster1", "cluster2", "cluster3",
    # Hard
    "museum", "sillygoose", "pirate", "donottell",
    "librarian", "miner",
    # Expert
    "blobshop", "wizardcoder",
]


async def crack_crucible(
    api_key: str,
    challenges: List[str] = None,
    max_attempts: int = 50,
    verbose: bool = True,
) -> Dict:
    """
    Crack Crucible CTF challenges with timing.
    
    Args:
        api_key: Dreadnode API key
        challenges: List of challenge slugs (default: all)
        max_attempts: Max attempts per challenge
        verbose: Print progress
        
    Returns:
        Dict with results, timing, and statistics
    """
    from strike.targets import create_target
    from strike.universal_controller import UniversalController
    
    challenges = challenges or CRUCIBLE_CHALLENGES
    
    if verbose:
        print("🔥 SENTINEL Strike — Crucible Cracker")
        print("=" * 50)
        print(f"Challenges: {len(challenges)}")
        print(f"Max attempts: {max_attempts}")
    
    results = {}
    stats = {
        "total": len(challenges),
        "cracked": 0,
        "failed": 0,
        "errors": 0,
        "start_time": datetime.now().isoformat(),
    }
    
    for i, slug in enumerate(challenges, 1):
        if verbose:
            print(f"\n[{i}/{len(challenges)}] 🎯 {slug}")
        
        start = datetime.now()
        
        try:
            async with create_target("crucible", api_key=api_key, name=slug) as target:
                controller = UniversalController(target)
                result = await controller.run(max_attempts=max_attempts)
                
                duration = (datetime.now() - start).total_seconds()
                
                if result:
                    results[slug] = {
                        "flag": result,
                        "duration": duration,
                        "attempts": controller.attempt_count,
                    }
                    stats["cracked"] += 1
                    if verbose:
                        print(f"✅ {slug}: {result} ({duration:.1f}s)")
                else:
                    stats["failed"] += 1
                    if verbose:
                        print(f"❌ {slug}: Failed ({duration:.1f}s)")
                        
        except Exception as e:
            stats["errors"] += 1
            if verbose:
                print(f"❌ {slug}: Error - {e}")
    
    stats["end_time"] = datetime.now().isoformat()
    
    if verbose:
        print(f"\n{'='*50}")
        print(f"📊 SUMMARY")
        print(f"  Cracked: {stats['cracked']}/{stats['total']}")
        print(f"  Failed:  {stats['failed']}")
        print(f"  Errors:  {stats['errors']}")
    
    return {
        "results": results,
        "stats": stats,
    }


async def crack_crucible_hydra(
    api_key: str,
    challenges: List[str] = None,
    max_attempts: int = 50,
    concurrency: int = 5,
    verbose: bool = True,
) -> Dict:
    """
    Crack Crucible CTF using HYDRA multi-head architecture.
    
    Features:
    - Parallel challenge execution (configurable concurrency)
    - Multiple attack heads per challenge
    - Attack success tracking and caching
    
    Args:
        api_key: Dreadnode API key
        challenges: List of challenge slugs (default: all)
        max_attempts: Max attempts per challenge
        concurrency: Number of parallel attacks
        verbose: Print progress
        
    Returns:
        Dict with results, timing, and statistics
    """
    from strike.targets import create_target
    from strike.universal_controller import UniversalController
    
    challenges = challenges or CRUCIBLE_CHALLENGES
    semaphore = asyncio.Semaphore(concurrency)
    
    if verbose:
        print("🐙 SENTINEL Strike — Crucible HYDRA")
        print("=" * 50)
        print(f"Challenges: {len(challenges)}")
        print(f"Concurrency: {concurrency}")
    
    results = {}
    stats = {
        "total": len(challenges),
        "cracked": 0,
        "failed": 0,
        "errors": 0,
        "start_time": datetime.now().isoformat(),
    }
    
    async def attack_challenge(slug: str, idx: int):
        """Attack single challenge with semaphore."""
        async with semaphore:
            if verbose:
                print(f"[{idx}/{len(challenges)}] 🎯 {slug}")
            
            start = datetime.now()
            
            try:
                async with create_target("crucible", api_key=api_key, name=slug) as target:
                    controller = UniversalController(target)
                    result = await controller.run(max_attempts=max_attempts)
                    
                    duration = (datetime.now() - start).total_seconds()
                    
                    if result:
                        results[slug] = {
                            "flag": result,
                            "duration": duration,
                            "attempts": controller.attempt_count,
                        }
                        stats["cracked"] += 1
                        if verbose:
                            print(f"✅ {slug}: {result}")
                    else:
                        stats["failed"] += 1
                        if verbose:
                            print(f"❌ {slug}: Failed")
                            
            except Exception as e:
                stats["errors"] += 1
                if verbose:
                    print(f"❌ {slug}: {e}")
    
    # Run all challenges concurrently
    tasks = [
        attack_challenge(slug, i)
        for i, slug in enumerate(challenges, 1)
    ]
    await asyncio.gather(*tasks)
    
    stats["end_time"] = datetime.now().isoformat()
    
    if verbose:
        print(f"\n{'='*50}")
        print(f"📊 HYDRA SUMMARY")
        print(f"  Cracked: {stats['cracked']}/{stats['total']}")
    
    return {
        "results": results,
        "stats": stats,
    }


def run_crucible(api_key: str, challenges: List[str] = None) -> Dict:
    """Sync wrapper for crack_crucible."""
    return asyncio.run(crack_crucible(api_key, challenges))


def run_crucible_hydra(api_key: str, challenges: List[str] = None) -> Dict:
    """Sync wrapper for crack_crucible_hydra."""
    return asyncio.run(crack_crucible_hydra(api_key, challenges))
