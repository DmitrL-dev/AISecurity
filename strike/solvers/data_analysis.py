"""
DataAnalysisSolver — Strike v4.0

Solves non-LLM data analysis challenges like:
- arrayz (numpy reshape puzzles)
- cluster (ML classification)
- Other data-based CTF challenges

These require different techniques than prompt injection.
"""

import asyncio
import os
from typing import Optional, Tuple, List
import numpy as np
from PIL import Image
import requests


class DataAnalysisSolver:
    """
    Automated solver for data analysis CTF challenges.
    
    Supports:
    - numpy array reshape puzzles (arrayz)
    - Image steganography
    - Binary data analysis
    """
    
    def __init__(self, api_key: str, challenge: str):
        self.api_key = api_key
        self.challenge = challenge
        self.base_url = "https://platform.dreadnode.io"
        self.challenge_url = f"https://{challenge}.platform.dreadnode.io"
        self.artifacts: List[str] = []
        
    def download_artifacts(self) -> List[str]:
        """Download challenge artifacts."""
        # Get challenge info
        info_url = f"{self.base_url}/api/challenges/{self.challenge}"
        headers = {"X-API-Key": self.api_key}
        
        resp = requests.get(info_url, headers=headers)
        if resp.status_code != 200:
            print(f"Failed to get challenge info: {resp.status_code}")
            return []
        
        info = resp.json()
        artifacts = info.get("artifacts", [])
        
        downloaded = []
        for artifact in artifacts:
            name = artifact.get("name", "")
            if not name:
                continue
                
            url = f"{self.base_url}/api/artifacts/{self.challenge}/{name}"
            resp = requests.get(url, headers=headers)
            
            if resp.status_code == 200:
                with open(name, "wb") as f:
                    f.write(resp.content)
                downloaded.append(name)
                print(f"Downloaded: {name}")
        
        self.artifacts = downloaded
        return downloaded
    
    def solve_reshape_puzzle(self, npy_file: str) -> Optional[str]:
        """
        Solve numpy reshape puzzle by finding correct dimensions
        and extracting hidden text from resulting image.
        """
        arr = np.load(npy_file)
        size = arr.size
        dtype = arr.dtype
        
        print(f"Array: size={size}, dtype={dtype}")
        print(f"Unique values: {np.unique(arr)}")
        
        # Find all possible image dimensions
        possible_dims = []
        for h in range(100, min(5000, size)):
            if size % h == 0:
                w = size // h
                if 100 < w < 10000:
                    possible_dims.append((h, w))
        
        print(f"Found {len(possible_dims)} possible dimensions")
        
        # Try each dimension and save as image
        results = []
        for h, w in possible_dims[:20]:  # Try top 20
            try:
                img_data = arr.reshape(h, w)
                
                # Convert to visible image (handle binary 0/1 data)
                if np.max(img_data) <= 1:
                    img_data = np.where(img_data == 0, 255, 0).astype(np.uint8)
                
                filename = f"{self.challenge}_{h}x{w}.png"
                Image.fromarray(img_data).save(filename)
                results.append((h, w, filename))
                
            except Exception as e:
                print(f"Failed {h}x{w}: {e}")
        
        print(f"\nGenerated {len(results)} images. Check them for hidden text:")
        for h, w, f in results[:5]:
            print(f"  - {f}")
        
        return None  # Manual inspection needed
    
    def submit_answer(self, answer: str) -> dict:
        """Submit answer to challenge score endpoint."""
        url = f"{self.challenge_url}/score"
        headers = {"X-API-Key": self.api_key}
        
        # Try with brackets
        if not answer.startswith("{"):
            answer = f"{{{answer}}}"
        
        resp = requests.post(url, headers=headers, json={"data": answer})
        return resp.json()
    
    def submit_flag(self, flag: str) -> bool:
        """Submit captured flag to Crucible."""
        url = f"{self.base_url}/api/challenges/{self.challenge}/submit-flag"
        headers = {"X-API-Key": self.api_key}
        payload = {"challenge": self.challenge, "flag": flag}
        
        resp = requests.post(url, headers=headers, json=payload)
        if resp.status_code == 200:
            result = resp.json()
            if result.get("correct"):
                print("✅ Flag correct!")
                return True
            else:
                print("❌ Flag incorrect")
                return False
        else:
            print(f"Error submitting flag: {resp.text}")
            return False
    
    def auto_solve(self) -> Optional[str]:
        """
        Attempt to automatically solve the challenge.
        
        Returns the flag if successful, None otherwise.
        """
        print(f"=== Solving {self.challenge} ===\n")
        
        # Step 1: Download artifacts
        artifacts = self.download_artifacts()
        if not artifacts:
            print("No artifacts found")
            return None
        
        # Step 2: Analyze each artifact
        for artifact in artifacts:
            ext = artifact.split(".")[-1].lower()
            
            if ext == "npy":
                print(f"\nAnalyzing numpy array: {artifact}")
                self.solve_reshape_puzzle(artifact)
            
            elif ext in ["png", "jpg", "jpeg", "bmp"]:
                print(f"\nAnalyzing image: {artifact}")
                # TODO: Add image steganography analysis
            
            elif ext in ["csv", "json"]:
                print(f"\nAnalyzing data file: {artifact}")
                # TODO: Add data analysis
        
        print("\n⚠️ Manual inspection required. Check generated images for hidden text.")
        return None


# Pre-built solver functions
def solve_arrayz(api_key: str, level: int = 1) -> Optional[str]:
    """Quick solver for arrayz challenges."""
    challenge = f"arrayz{level}"
    solver = DataAnalysisSolver(api_key, challenge)
    return solver.auto_solve()


if __name__ == "__main__":
    import sys
    
    API_KEY = os.environ.get("CRUCIBLE_API_KEY", "_ROezrKpeo4r83nm__IEZVndcFBMSHJS")
    
    if len(sys.argv) > 1:
        challenge = sys.argv[1]
    else:
        challenge = "arrayz1"
    
    solver = DataAnalysisSolver(API_KEY, challenge)
    solver.auto_solve()
