---
id: XN-034
title: "Hepar2 multi-seed: LOCALE +16pp over MosaCD (4 seeds, p=0.013)"
date: 2026-03-26
dag_nodes: [E03, I02]
links:
  evidence_for: [E03, I02]
  related_to: [XN-031]
tags: [hepar2, multi-seed, comparison]
---

# XN-034: Hepar2 Multi-Seed Comparison

## Setup

- Network: Hepar2 (70 nodes, 123 directed edges)
- 4 seeds: 0, 1, 2, 42
- Same model/context as XN-031: Qwen3.5-27B-FP8, 4096 context
- LOCALE: K=10 passes, debiased, all-nodes, NCO, alpha=0.05
- MosaCD: 5 reps × 2 orderings

## Results

| Seed | LOCALE F1 | MosaCD F1 | Delta |
|------|-----------|-----------|-------|
| 0 | 0.562 | 0.426 | +13.7pp |
| 1 | 0.532 | 0.440 | +9.2pp |
| 2 | 0.559 | 0.381 | +17.8pp |
| 42 | 0.605 | 0.372 | +23.3pp |
| **Mean** | **0.565±0.026** | **0.405±0.029** | **+16.0pp** |

Paired t-test: t=5.328, p=0.0129, d=3.08

## Key Findings

1. **LOCALE wins convincingly on the largest network.** +16.0pp F1 with p=0.013 and d=3.08 (very large effect). All 4 seeds show consistent advantage.

2. **Both methods are skeleton-bottlenecked.** Hepar2 PC skeleton at n=10k has ~52% recall (depth-limited, same issue as Insurance). LOCALE recall=42.7%, MosaCD recall=31.1% — both far below the skeleton ceiling.

3. **LOCALE's precision advantage is dramatic.** 83.4% vs 57.9% — LOCALE gets many fewer false orientations. This is the NCO + ego-graph advantage at work.

4. **This is the 6th network and 3rd significant win.** Updated scorecard: 3 SIG wins (Sachs, Insurance, Hepar2) + 2 directional (Alarm, Child) + 1 SIG loss (Asia).
