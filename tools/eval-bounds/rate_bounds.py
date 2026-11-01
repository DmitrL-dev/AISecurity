#!/usr/bin/env python3
"""How sure can you be about an AI guardrail's rate: exact one-sided binomial bounds.

«0 attacks got through out of 10» is compatible with a true bypass rate of 25.9% at 95% confidence, and
«2 of 36 missed» with 16.5%. This tool states the bound beside every rate and judges a claim «the rate is
below tau» three ways:

* VERIFIED when the one-sided 95% Clopper-Pearson upper bound is below tau;
* NOT VERIFIED when the one-sided 95% lower bound is at or above tau;
* INCONCLUSIVE in between, which is what «0 of N» means whenever N is too small for tau.

Choose tau before the measurement, from the risk, never from the result.

A trial is an independent source sample. Paraphrases, translations, mutations and repeated runs of one
sample are one trial, which counts as an event if any of its variants does; counting variants as trials
makes the bound narrower than the evidence. Before/after comparisons on the same rows are paired and take
`mcnemar`, not two independent bounds.

    python3 rate_bounds.py claim EVENTS TRIALS --tau 0.01   # exit 0 VERIFIED, 1 NOT VERIFIED, 2 INCONCLUSIVE
    python3 rate_bounds.py plan --tau 0.003                 # trials needed if no event occurs
    python3 rate_bounds.py mcnemar ONLY_BEFORE ONLY_AFTER   # exact two-sided p for paired change

Standard library only. Python 3.10+.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from typing import Any

ALPHA = 0.05
_BETA_ITERATIONS = 100_000
_BETA_EPSILON = 1e-15
_TINY = 1e-300
_BISECTIONS = 200


def _require_counts(events: int, trials: int) -> None:
    for name, value in (("events", events), ("trials", trials)):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{name} must be an integer count")
    if trials <= 0:
        raise ValueError("trials must be positive")
    if not 0 <= events <= trials:
        raise ValueError("events must be between 0 and trials")


def _require_probability(name: str, value: float) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0.0 < value < 1.0:
        raise ValueError(f"{name} must be strictly between 0 and 1")


def _beta_continued_fraction(a: float, b: float, x: float) -> float:
    """Modified Lentz evaluation of the incomplete beta continued fraction."""
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) >= _TINY else _TINY)
    h = d
    for m in range(1, _BETA_ITERATIONS + 1):
        m2 = 2 * m
        for numerator in (
            m * (b - m) * x / ((qam + m2) * (a + m2)),
            -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2)),
        ):
            d = 1.0 + numerator * d
            d = 1.0 / (d if abs(d) >= _TINY else _TINY)
            c = 1.0 + numerator / c
            c = c if abs(c) >= _TINY else _TINY
            step = d * c
            h *= step
        if abs(step - 1.0) < _BETA_EPSILON:
            return h
    # A bound computed from a fraction that did not converge would be a number with no meaning.
    raise ArithmeticError("incomplete beta did not converge")


def _regularized_beta(a: float, b: float, x: float) -> float:
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    log_front = (
        math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log1p(-x)
    )
    if x < (a + 1.0) / (a + b + 2.0):
        return math.exp(log_front) * _beta_continued_fraction(a, b, x) / a
    return 1.0 - math.exp(log_front) * _beta_continued_fraction(b, a, 1.0 - x) / b


def binomial_cdf(k: int, n: int, p: float) -> float:
    """P(X <= k) for X ~ Binomial(n, p)."""
    if k < 0:
        return 0.0
    if k >= n:
        return 1.0
    # I_{1-p}(n-k, k+1) rather than 1 - I_p(k+1, n-k): the subtraction rounds a tail of 1e-40 to zero,
    # which a paired test of 131 flips against none returned as p = 0.
    return _regularized_beta(float(n - k), k + 1.0, 1.0 - p)


def _solve(function: Any, target: float, low: float, high: float, increasing: bool) -> float:
    for _ in range(_BISECTIONS):
        middle = (low + high) / 2.0
        if (function(middle) < target) == increasing:
            low = middle
        else:
            high = middle
    return high if not increasing else low


def upper_bound(events: int, trials: int, alpha: float = ALPHA) -> float:
    """One-sided (1 - alpha) Clopper–Pearson upper bound of the event rate."""
    _require_counts(events, trials)
    _require_probability("alpha", alpha)
    if events == trials:
        return 1.0
    if events == 0:
        return 1.0 - alpha ** (1.0 / trials)
    # P(X <= events) falls as p grows; the bound is where it reaches alpha.
    return _solve(
        lambda p: binomial_cdf(events, trials, p), alpha, events / trials, 1.0, increasing=False
    )


def lower_bound(events: int, trials: int, alpha: float = ALPHA) -> float:
    """One-sided (1 - alpha) Clopper–Pearson lower bound of the event rate."""
    _require_counts(events, trials)
    _require_probability("alpha", alpha)
    if events == 0:
        return 0.0
    if events == trials:
        return alpha ** (1.0 / trials)
    # P(X >= events) grows with p; the bound is where it reaches alpha.
    return _solve(
        lambda p: 1.0 - binomial_cdf(events - 1, trials, p), alpha, 0.0, events / trials, increasing=True
    )


def trials_needed(tau: float, alpha: float = ALPHA) -> int:
    """Fewest independent trials whose upper bound falls below tau when no event occurs."""
    _require_probability("tau", tau)
    _require_probability("alpha", alpha)
    trials = max(1, math.floor(math.log(alpha) / math.log1p(-tau)))
    while upper_bound(0, trials, alpha) >= tau:
        trials += 1
    while trials > 1 and upper_bound(0, trials - 1, alpha) < tau:
        trials -= 1
    return trials


def claim(events: int, trials: int, tau: float, alpha: float = ALPHA) -> dict[str, Any]:
    """Judge «the rate is below tau» from `events` of `trials` independent samples."""
    _require_probability("tau", tau)
    upper = upper_bound(events, trials, alpha)
    lower = lower_bound(events, trials, alpha)
    if upper < tau:
        verdict = "VERIFIED"
    elif lower >= tau:
        verdict = "NOT VERIFIED"
    else:
        verdict = "INCONCLUSIVE"
    return {
        "events": events,
        "trials": trials,
        "rate": events / trials,
        "confidence": 1.0 - alpha,
        "upper_bound": upper,
        "lower_bound": lower,
        "tau": tau,
        "verdict": verdict,
        "trials_needed_with_no_event": trials_needed(tau, alpha),
    }


def mcnemar_exact(only_before: int, only_after: int) -> float:
    """Exact two-sided p-value for a paired change: rows that flipped one way against the other."""
    for name, value in (("only_before", only_before), ("only_after", only_after)):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"{name} must be a non-negative integer count")
    discordant = only_before + only_after
    if discordant == 0:
        return 1.0
    return min(1.0, 2.0 * binomial_cdf(min(only_before, only_after), discordant, 0.5))


def describe(result: dict[str, Any]) -> str:
    return (
        f"{result['events']}/{result['trials']} = {result['rate']:.4%}; "
        f"one-sided {result['confidence']:.0%} bounds [{result['lower_bound']:.4%}, "
        f"{result['upper_bound']:.4%}]; tau {result['tau']:.4%}: {result['verdict']} "
        f"(with no event, {result['trials_needed_with_no_event']} independent trials reach tau)"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--alpha", type=float, default=ALPHA)
    parser.add_argument("--json", action="store_true", help="print one JSON document")
    commands = parser.add_subparsers(dest="command", required=True)
    claim_parser = commands.add_parser("claim")
    claim_parser.add_argument("events", type=int)
    claim_parser.add_argument("trials", type=int)
    claim_parser.add_argument("--tau", type=float, required=True)
    plan_parser = commands.add_parser("plan")
    plan_parser.add_argument("--tau", type=float, required=True)
    mcnemar_parser = commands.add_parser("mcnemar")
    mcnemar_parser.add_argument("only_before", type=int)
    mcnemar_parser.add_argument("only_after", type=int)
    args = parser.parse_args(argv)

    try:
        if args.command == "claim":
            result = claim(args.events, args.trials, args.tau, args.alpha)
            print(json.dumps(result, sort_keys=True) if args.json else describe(result))
            return {"VERIFIED": 0, "NOT VERIFIED": 1, "INCONCLUSIVE": 2}[result["verdict"]]
        if args.command == "plan":
            needed = trials_needed(args.tau, args.alpha)
            print(json.dumps({"tau": args.tau, "trials_needed_with_no_event": needed}) if args.json else needed)
            return 0
        p_value = mcnemar_exact(args.only_before, args.only_after)
        print(json.dumps({"p_value_two_sided": p_value}) if args.json else f"{p_value:.6g}")
        return 0
    except ValueError as error:
        print(f"rate_bounds: {error}", file=sys.stderr)
        return 64


if __name__ == "__main__":
    raise SystemExit(main())
