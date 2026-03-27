---
id: XN-029
title: "Context sensitivity: MosaCD breaks at 2048 tokens, LOCALE is robust"
date: 2026-03-18
dag_nodes: [E03, E01]
links:
  evidence_for: [E03]
  related_to: [XN-024, XN-027]
tags: [context, mosacd, comparison, confound]
---

# XN-029: Context Sensitivity Discovery

## Summary

MosaCD is catastrophically sensitive to context window size. At 2048 max_model_len, nearly all MosaCD queries become "undecided" (38-42 out of 43-45 edges). LOCALE is unaffected. This is both a confound in our comparison AND a genuine finding about prompt architecture.

## Evidence

### Same seed, same data, different context (Insurance s0)

| Metric | 4096 context | 2048 context |
|--------|-------------|-------------|
| MosaCD F1 | 0.723 | 0.538 |
| Valid seeds | 27/42 | **2/41** |
| Undecided edges | 9 | **38** |

### Same seed, same data, different context (Alarm s0)

| Metric | 4096 context | 2048 context |
|--------|-------------|-------------|
| MosaCD F1 | 0.791 | 0.703 |
| Valid seeds | 29/45 | **2/45** |
| Undecided edges | 11 | **42** |

### LOCALE is context-robust

Insurance LOCALE F1 across 12 seeds (mix of 4096 and 2048 context): 0.853 ± 0.017. No degradation. Ego-graph prompts are compact enough to fit in 2048 tokens.

### MosaCD aggregate at each context

| Network | MosaCD 4096 (4 seeds) | MosaCD 2048 (12 seeds) | Degradation |
|---------|---------------------|---------------------|-------------|
| Insurance | 0.806 ± 0.064 | 0.525 ± 0.077 | -28.1pp |
| Alarm | 0.801 ± 0.018 | 0.860 ± 0.076 | +5.9pp* |
| Sachs | 0.523 ± 0.113 | 0.604 ± 0.112 | +8.1pp* |
| Child | 0.876 ± 0.009 | 0.742 ± 0.111 | -13.4pp |
| Asia | 0.933 ± 0.000 | 0.950 ± 0.030 | +1.7pp |

*Alarm and Sachs improved at 2048 — likely because shorter context forces simpler/more decisive outputs on smaller networks where prompts already fit.

## Root Cause

MosaCD's "full" template includes:
- Variable descriptions for u, v, and chain neighbors
- All CI test results mentioning u or v
- Chain constraint descriptions

For high-degree nodes (Insurance: up to d=7, Alarm: up to d=6), the full template produces ~1000-1500+ input tokens. With max_tokens=500 for output, total exceeds 2048 → vLLM truncates or errors.

LOCALE's ego-graph prompt is more compact: one node's neighbors + CI facts, without chain descriptions. Fits comfortably in 2048.

## Implications

1. **The 12-seed comparison at 2048 is NOT a fair head-to-head.** MosaCD is crippled by truncation on Insurance and Child. Cannot use for W/T/L claims.

2. **The 4-seed comparison at 4096 remains the only fair comparison.** But has insufficient power (Insurance ns, Child ns).

3. **Context efficiency IS a genuine contribution.** LOCALE works at 2048; MosaCD requires 4096+. For deployment with small models (limited KV cache, expensive long context), this matters.

4. **To get a powered fair comparison: need 12 seeds at 4096 context.** Requires endpoint redeployment.

## Backups

Original 4096-context MosaCD results backed up at `results/mosacd_{net}_s{0,1,2}_4096ctx_backup/` and `results/mosacd_{net}_4096ctx_backup/`.
