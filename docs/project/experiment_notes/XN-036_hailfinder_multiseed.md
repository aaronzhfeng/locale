---
id: XN-036
title: "Hailfinder multi-seed (n=2000): LOCALE +16.7pp over MosaCD"
date: 2026-03-27
dag_nodes: [E03, I02]
links:
  evidence_for: [E03, I02]
  related_to: [XN-035]
tags: [hailfinder, multi-seed, comparison, reduced-samples]
---

# XN-036: Hailfinder Multi-Seed Comparison

## Setup

- Network: Hailfinder (56 nodes, 66 directed edges)
- **n_samples=2000** (reduced from 10000 — PC skeleton at n=10000 takes ~10 hrs per seed on M5 Pro due to combinatorial CI test explosion at 56 nodes)
- 3 paired seeds: 0, 1, 2 (MosaCD s42 failed due to endpoint going down)
- Same model/context: Qwen3.5-27B-FP8, 4096 context
- LOCALE: K=10 passes, debiased, all-nodes, NCO, alpha=0.05
- MosaCD: 5 reps × 2 orderings

## Results

| Seed | LOCALE F1 | MosaCD F1 | Delta |
|------|-----------|-----------|-------|
| 0 | 0.615 | 0.446 | +16.9pp |
| 1 | 0.592 | 0.464 | +12.8pp |
| 2 | 0.641 | 0.438 | +20.3pp |
| **Mean** | **0.616±0.020** | **0.449±0.011** | **+16.7pp** |

Paired t-test (3 pairs): t=7.678, p=0.017

## Caveats

1. **Reduced sample size.** n=2000 vs n=10000 for other networks. Skeleton coverage is lower (~55% at n=1000 benchmark), which affects both methods equally. Comparison is fair (same skeleton), but absolute F1 values are not directly comparable to other networks.

2. **3 seeds instead of 4.** MosaCD s42 failed due to endpoint going down mid-run. LOCALE s42 completed (F1=0.554, phase3 accuracy=59.3%).

3. **PC skeleton bottleneck.** At 56 nodes, PC-stable hits maximum conditioning depth (level 5) with a combinatorial number of tests. This is an intrinsic limitation of the PC algorithm on dense networks, not specific to our setup.

## MosaCD Fidelity Gap

MosaCD paper reports Hailfinder F1=0.49 (with GPT-4o-mini, 128K context, n=20000). Our re-implementation gets 0.449 (with Qwen-27B, 4096 context, n=2000). The gap is explained by: (1) different model, (2) different context window, (3) different sample size. Both methods face the same conditions in our comparison.
