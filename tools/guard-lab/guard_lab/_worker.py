"""Private native runner. Only fixed-code/boolean/score protocol leaves it."""
import importlib.metadata
import json
import math
import os
import resource
import sys

from .metrics import PUBLIC_COMMIT


def valid_origin(origin):
    if not isinstance(origin, dict):
        return False
    vcs = origin.get("vcs_info")
    return (origin.get("url") == "https://github.com/DmitrL-dev/AISecurity.git"
            and origin.get("subdirectory") == "sentinel-core" and isinstance(vcs, dict)
            and vcs.get("vcs") == "git" and vcs.get("commit_id") == PUBLIC_COMMIT)


def _registry():
    try:
        dist = importlib.metadata.distribution("sentinel-core")
        origin = json.loads(dist.read_text("direct_url.json") or "null")
    except importlib.metadata.PackageNotFoundError:
        return None, "DEPENDENCY_MISSING"
    except (ValueError, OSError):
        return None, "ENGINE_ORIGIN_MISMATCH"
    if not valid_origin(origin):
        return None, "ENGINE_ORIGIN_MISMATCH"
    try:
        from sentinel_core import EngineRegistry, version
        if version() != "2.0.0":
            return None, "ENGINE_ORIGIN_MISMATCH"
        return EngineRegistry(), None
    except BaseException:
        # Includes PyO3's PanicException; never serialize its message.
        return None, "ENGINE_ERROR"


def main():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_AS, (768 * 1024 * 1024,) * 2)
    resource.setrlimit(resource.RLIMIT_FSIZE, (256 * 1024,) * 2)
    cpu_seconds = min(121, max(1, int(os.environ["GUARD_LAB_CPU_SECONDS"])))
    resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds,) * 2)
    # Keep one protocol descriptor; suppress Python and native stdout.
    with os.fdopen(os.dup(sys.stdout.fileno()), "w") as protocol, open(os.devnull, "w") as sink:
        os.dup2(sink.fileno(), sys.stdout.fileno())
        raw = sys.stdin.buffer.read(8 * 1024 * 1024 + 1)
        if len(raw) > 8 * 1024 * 1024:
            return 1
        texts = json.loads(raw)
        if (not isinstance(texts, list) or len(texts) > 1000
                or any(not isinstance(text, str) or len(text.encode("utf-8")) > 16384 for text in texts)):
            return 1
        registry, error = _registry()
        results = []
        for text in texts:
            if error:
                results.append({"error": error})
                continue
            try:
                result = registry.analyze_patterns(text)
                detected, score = result.detected, result.risk_score
                if (type(detected) is not bool or type(score) not in (float, int)
                        or not math.isfinite(score) or not 0 <= score <= 1):
                    results.append({"error": "INVALID_RESULT"})
                else:
                    results.append({"detected": detected, "risk_score": score})
            except BaseException:
                results.append({"error": "ENGINE_ERROR"})
        json.dump(results, protocol, allow_nan=False, separators=(",", ":"))
        protocol.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
