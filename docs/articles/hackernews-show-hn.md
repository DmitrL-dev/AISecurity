# Hacker News: Show HN Post

## Title (max 80 chars)

```
Show HN: Micro-Model Swarm – 8K params that beat BERT (F1=0.997) for LLM security
```

## URL

```
https://github.com/DmitrL-dev/AISecurity
```

## Comment (first comment by author, "Show HN" style)

Hi HN,

I built an open-source LLM security platform called SENTINEL. The interesting part is the **Micro-Model Swarm** — instead of fine-tuning BERT (110M params, needs GPU), I use a swarm of tiny domain-specific models (<2K params each) that detect jailbreak attacks.

**Results on 87K real attack samples:**
- F1: 0.997 (vs BERT's 0.96)
- Latency: ~1ms on CPU (vs BERT's ~50ms on GPU)
- Total params: <8K (vs 110M)

The key insight: jailbreak prompts have a distinctive statistical fingerprint — abnormal entropy, unusual char ratios, specific keyword distributions. You don't need to "understand language" to detect attacks, you need to detect anomalies.

**Architecture:** Three layers, all <3ms total:
1. Shield (C, 36K LOC) — DMZ, rate limiting, eBPF
2. Brain (Rust, 49 engines) — pattern matching
3. Micro-Swarm (Python) — ML anomaly detection

The swarm also includes a self-training loop: when the LLM is called as fallback, we compare its verdict with the swarm's prediction. Every LLM call becomes a free training sample. Goal: 95% of requests handled by the swarm, 5% by LLM.

116K LOC, Apache 2.0. Written by one person.

Feedback welcome — especially on the micro-model approach vs traditional transformer fine-tuning.

---

## HN Tips

- Post between **9-11am EST** (peak HN traffic)
- Monday-Thursday = best days
- Don't ask for upvotes
- Respond to every comment in the first 2 hours
- Title formula: `Show HN: [Name] – [One-line value prop]`
- Keep the comment factual, no hype, technical depth = upvotes
