# eval-bounds: how much can your AI security test actually prove?

You ran 50 jailbreaks against a guardrail and none got through. Can you say it blocks 99% of them?

```console
$ python3 rate_bounds.py claim 0 50 --tau 0.01
0/50 = 0.0000%; one-sided 95% bounds [0.0000%, 5.8155%]; tau 1.0000%: INCONCLUSIVE (with no event, 299 independent trials reach tau)
```

No. Fifty clean runs are compatible with a true bypass rate of 5.8%. To claim «under 1%» you need at least
299 independent attacks and no bypass. One file, standard library only, Python 3.9+.

## Three questions it answers

**Does my result support the claim?**

```console
$ python3 rate_bounds.py claim 1 1000 --tau 0.003
1/1000 = 0.1000%; one-sided 95% bounds [0.0051%, 0.4735%]; tau 0.3000%: INCONCLUSIVE (with no event, 998 independent trials reach tau)
```

The exit code carries the verdict, so a CI job can fail on it: `0` VERIFIED (the upper bound is below tau),
`1` NOT VERIFIED (the lower bound is at or above tau), `2` INCONCLUSIVE (not enough data either way).

**How many tests do I need before I start?**

```console
$ python3 rate_bounds.py plan --tau 0.01
299
```

**Did my fix change anything, measured on the same inputs?**

```console
$ python3 rate_bounds.py mcnemar 3 17
0.00257683
```

Three inputs got worse and seventeen got better; an exact paired test says that is unlikely to be chance.
Two independent rates on the same rows would overstate or understate it.

## Read before you quote a number

- **Fix tau before you measure.** A threshold chosen after seeing the result fits the result.
- **Count independent sources, not variants.** Ten paraphrases of one jailbreak are one trial, and it counts
  as a bypass if any paraphrase gets through. Counting variants makes the bound look tighter than it is.
- **Measure both sides.** A guard that blocks everything passes every attack test. Run the same bound on
  false blocks over legitimate traffic, with its own tau.
- **Fix the sample size in advance.** Adding attacks until the bound drops under tau breaks the 95% guarantee.
- **The bound covers sampling only.** It says nothing about labelling errors, a judge model's misses, or
  attack classes your corpus never contained.

## Run the tests

```bash
python3 -m unittest discover -s tools/eval-bounds -p 'test_*.py'
```

They check the bounds against a published red-team sample-size table recomputed independently, against a
brute-force binomial sum for every count up to 40, and the command-line exit codes.

## License

Apache-2.0, like the rest of this repository.
