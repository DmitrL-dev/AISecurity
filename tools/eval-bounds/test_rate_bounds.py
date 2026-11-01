"""Exact one-sided binomial bounds: golden values, a brute-force cross-check, and the verdict rule.

The golden values are a published red-team sample-size table (2026-10-23), recomputed independently
before they were pinned here, so a mistake would have to be made twice the same way.
"""

from __future__ import annotations

import math
import subprocess
import sys
import unittest
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "rate_bounds.py"
sys.path.insert(0, str(HERE))

import rate_bounds  # noqa: E402


def exact_cdf(k: int, n: int, p: float) -> float:
    q = Fraction(p)
    return float(sum(math.comb(n, i) * q**i * (1 - q) ** (n - i) for i in range(k + 1)))


def log_space_cdf(k: int, n: int, p: float) -> float:
    terms = [
        math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1)
        + i * math.log(p) + (n - i) * math.log1p(-p)
        for i in range(k + 1)
    ]
    top = max(terms)
    return math.exp(top) * sum(math.exp(term - top) for term in terms)


class GoldenValues(unittest.TestCase):
    def test_upper_bounds_match_the_published_table(self) -> None:
        cases = {
            (0, 10): 0.258866,
            (0, 20): 0.139108,
            (0, 100): 0.029513,
            (0, 300): 0.009936,
            (0, 1000): 0.002991,
            (1, 1000): 0.004735,
            (2, 100): 0.0616,
            (20, 1000): 0.0289,
            (200, 10000): 0.0225,
            (10, 100): 0.1637,
            (100, 1000): 0.1170,
        }
        for (events, trials), expected in cases.items():
            with self.subTest(events=events, trials=trials):
                places = len(str(expected).split(".")[1])
                self.assertAlmostEqual(rate_bounds.upper_bound(events, trials), expected, places=places)

    def test_trials_needed_match_the_published_table(self) -> None:
        for tau, expected in ((0.05, 59), (0.01, 299), (0.005, 598), (0.003, 998), (0.001, 2995)):
            with self.subTest(tau=tau):
                needed = rate_bounds.trials_needed(tau)
                self.assertEqual(needed, expected)
                self.assertLess(rate_bounds.upper_bound(0, needed), tau)
                self.assertGreaterEqual(rate_bounds.upper_bound(0, needed - 1), tau)


class AgainstBruteForce(unittest.TestCase):
    def test_bounds_put_exactly_alpha_in_the_tail_for_every_small_count(self) -> None:
        for trials in range(1, 41):
            for events in range(1, trials):
                with self.subTest(events=events, trials=trials):
                    upper = rate_bounds.upper_bound(events, trials)
                    lower = rate_bounds.lower_bound(events, trials)
                    self.assertAlmostEqual(exact_cdf(events, trials, upper), 0.05, places=9)
                    self.assertAlmostEqual(1.0 - exact_cdf(events - 1, trials, lower), 0.05, places=9)
                    self.assertLess(lower, events / trials)
                    self.assertGreater(upper, events / trials)

    def test_the_edges_are_closed_forms(self) -> None:
        for trials in (1, 7, 115, 79000):
            with self.subTest(trials=trials):
                self.assertEqual(rate_bounds.upper_bound(0, trials), 1.0 - 0.05 ** (1.0 / trials))
                self.assertEqual(rate_bounds.lower_bound(0, trials), 0.0)
                self.assertEqual(rate_bounds.upper_bound(trials, trials), 1.0)
                self.assertEqual(rate_bounds.lower_bound(trials, trials), 0.05 ** (1.0 / trials))

    def test_large_counts_stay_exact(self) -> None:
        upper = rate_bounds.upper_bound(100, 100_000)
        self.assertAlmostEqual(log_space_cdf(100, 100_000, upper), 0.05, places=9)


class Verdict(unittest.TestCase):
    def test_the_three_outcomes(self) -> None:
        self.assertEqual(rate_bounds.claim(0, 299, 0.01)["verdict"], "VERIFIED")
        # «Nothing happened» on too few samples is a lack of data, not safety.
        self.assertEqual(rate_bounds.claim(0, 298, 0.01)["verdict"], "INCONCLUSIVE")
        self.assertEqual(rate_bounds.claim(2, 36, 0.01)["verdict"], "INCONCLUSIVE")
        self.assertEqual(rate_bounds.claim(30, 100, 0.1)["verdict"], "NOT VERIFIED")

    def test_the_document_names_its_inputs(self) -> None:
        result = rate_bounds.claim(1, 1000, 0.003)
        self.assertEqual(result["trials_needed_with_no_event"], 998)
        self.assertEqual(result["confidence"], 0.95)
        self.assertEqual((result["events"], result["trials"], result["tau"]), (1, 1000, 0.003))

    def test_bad_inputs_are_refused(self) -> None:
        for events, trials in ((3, 2), (-1, 5), (0, 0), (True, 5), (1.0, 5)):
            with self.subTest(events=events, trials=trials):
                with self.assertRaises(ValueError):
                    rate_bounds.upper_bound(events, trials)  # type: ignore[arg-type]
        for tau in (0.0, 1.0, -0.1, 2.0):
            with self.subTest(tau=tau):
                with self.assertRaises(ValueError):
                    rate_bounds.claim(0, 10, tau)


class McNemar(unittest.TestCase):
    def test_exact_paired_p_values(self) -> None:
        self.assertEqual(rate_bounds.mcnemar_exact(0, 0), 1.0)
        self.assertAlmostEqual(rate_bounds.mcnemar_exact(0, 6), 0.03125, places=12)
        self.assertAlmostEqual(rate_bounds.mcnemar_exact(6, 0), 0.03125, places=12)
        self.assertEqual(rate_bounds.mcnemar_exact(3, 3), 1.0)
        self.assertAlmostEqual(rate_bounds.mcnemar_exact(2, 9), 2 * exact_cdf(2, 11, 0.5), places=12)

    def test_tiny_tails_keep_their_precision(self) -> None:
        # «132 → 1» on the same rows: 131 flips one way, none the other. A tail computed as 1 - I rounds
        # to zero here, and p = 0 claims a certainty no finite sample gives.
        self.assertAlmostEqual(rate_bounds.mcnemar_exact(131, 0) / (2 * 0.5**131), 1.0, places=9)
        self.assertAlmostEqual(rate_bounds.binomial_cdf(0, 2000, 0.05) / 0.95**2000, 1.0, places=9)


class CommandLine(unittest.TestCase):
    def run_cli(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-I", str(SCRIPT), *arguments],
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )

    def test_exit_status_carries_the_verdict(self) -> None:
        for arguments, status in (
            (("claim", "0", "299", "--tau", "0.01"), 0),
            (("claim", "30", "100", "--tau", "0.1"), 1),
            (("claim", "0", "298", "--tau", "0.01"), 2),
            (("claim", "5", "3", "--tau", "0.1"), 64),
        ):
            with self.subTest(arguments=arguments):
                self.assertEqual(self.run_cli(*arguments).returncode, status)

    def test_plan_and_mcnemar(self) -> None:
        self.assertEqual(self.run_cli("plan", "--tau", "0.003").stdout.strip(), "998")
        self.assertEqual(self.run_cli("mcnemar", "0", "6").stdout.strip(), "0.03125")


if __name__ == "__main__":
    unittest.main()
