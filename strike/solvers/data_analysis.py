"""
DataAnalysisSolver — Strike v4.0

Solves non-LLM data analysis challenges like:
- arrayz (numpy reshape puzzles)
- cluster (ML classification)
- Other data-based CTF challenges

These require different techniques than prompt injection.
"""

import os
from typing import Optional, List
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

    def histogram_forensic_analysis(
        self, npy_file: str, auto_visualize: bool = True
    ) -> Optional[str]:
        """
        Histogram forensic analysis for float64 arrays.

        Key technique for arrayz2-style challenges where float64 noise
        hides a discrete signal. Uses low-frequency bin filtering.

        Algorithm (from Black Hat 2024):
        1. Create histogram with optimal bin count (135)
        2. Identify low-frequency bins (count < threshold)
        3. Mark values in low-frequency bins as signal (1)
        4. Reshape to known dimensions and visualize

        Returns: flag string if automatically detected, else None
        """
        arr = np.load(npy_file)
        size = arr.size
        dtype = arr.dtype

        print(f"[HISTOGRAM FORENSIC] Array: size={size}, dtype={dtype}")
        print(f"  Value range: [{arr.min():.6f}, {arr.max():.6f}]")

        # Step 1: Create histogram with optimal bin count
        num_bins = 135  # Optimal for arrayz2-style challenges
        counts, edges = np.histogram(arr, bins=num_bins)

        print(f"  Histogram: {num_bins} bins")
        print(f"  Bin counts: min={counts.min()}, max={counts.max()}")

        # Step 2: Low-frequency bin filtering
        threshold = 4000
        result = np.zeros_like(arr)
        low_freq_bins = 0

        for i, count in enumerate(counts):
            if count < threshold:
                mask = (arr >= edges[i]) & (arr <= edges[i + 1])
                result[mask] = 1
                low_freq_bins += 1

        signal_pixels = int(result.sum())
        print(f"  Low-frequency bins (<{threshold}): {low_freq_bins}")
        print(f"  Signal pixels: {signal_pixels}")

        # Step 3: Known dimensions (arrayz2 confirmed)
        known_dims = [
            (4186, 349),  # arrayz2 primary
            (349, 4186),  # transposed
        ]

        # Find all possible dimensions
        possible_dims = []
        for h in range(100, min(5000, size)):
            if size % h == 0:
                w = size // h
                if 100 < w < 10000:
                    possible_dims.append((h, w))

        # Prioritize known dims
        all_dims = known_dims + [d for d in possible_dims if d not in known_dims]

        # Step 4: Generate images
        results = []
        for h, w in all_dims[:15]:
            try:
                if h * w != size:
                    continue
                img_data = (result.reshape(h, w) * 255).astype(np.uint8)
                filename = f"{self.challenge}_forensic_{h}x{w}.png"
                Image.fromarray(img_data).save(filename)
                results.append((h, w, filename))
            except Exception as e:
                print(f"  Failed {h}x{w}: {e}")

        if auto_visualize and results:
            print(f"\n🖼️ Generated {len(results)} forensic images:")
            for h, w, f in results[:10]:
                print(f"    {f}")

        return None

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
                # Load to check dtype for appropriate solver
                arr = np.load(artifact)

                if arr.dtype == np.float64 or arr.dtype == np.float32:
                    print(
                        f"  🔬 Float data detected — applying histogram forensic analysis"
                    )
                    self.histogram_forensic_analysis(artifact)
                else:
                    # Standard reshape for integer arrays
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
