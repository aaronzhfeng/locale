---
id: XN-035
title: "11-network comparison: LOCALE 8W/2T/1L across all MosaCD benchmarks + Sachs"
date: 2026-03-27
dag_nodes: [E03, I02, I03]
links:
  evidence_for: [E03, I02]
  related_to: [XN-031, XN-034, XN-036]
tags: [comparison, 11-network, holm, wilcoxon, mosacd-benchmarks]
---

# XN-035: Full 11-Network Comparison

## Objective

Match all 10 MosaCD benchmark networks plus Sachs for a comprehensive same-model comparison. All 11 BNLearn benchmarks tested.

## Setup

- 11 networks: Cancer (5n), Asia (8n), Sachs (11n), Child (20n), Insurance (27n), Water (32n), Mildew (35n), Alarm (37n), Hailfinder (56n), Hepar2 (70n), Win95pts (76n)
- Seeds: 12 (s0-s10, s42) for original 6 networks; 4 (s0-s2, s42) for new networks; 3 for Hailfinder (s42 MosaCD failed)
- Both methods: same model (Qwen3.5-27B-FP8), same context (4096), same skeleton (PC-stable)
- n_samples=10000 for all except Hailfinder (n=2000, PC too slow at 56 nodes — see XN-036)
- Asia: alpha=0.10 (both methods)

## Results (sorted by delta)

| Network | Nodes | Pairs | LOCALE F1 | MosaCD F1 | Delta | p (uncorr) |
|---------|-------|-------|-----------|-----------|-------|------------|
| Sachs | 11 | 11 | 0.865±0.044 | 0.557±0.063 | +30.7pp | <0.0001 |
| Hailfinder | 56 | 3 | 0.616±0.020 | 0.449±0.011 | +16.7pp | 0.017 |
| Hepar2 | 70 | 4 | 0.565±0.026 | 0.405±0.029 | +16.0pp | 0.013 |
| Win95pts | 76 | 4 | 0.694±0.091 | 0.573±0.057 | +12.2pp | 0.061 |
| Insurance | 27 | 10 | 0.845±0.019 | 0.757±0.083 | +8.8pp | 0.013 |
| Alarm | 37 | 11 | 0.841±0.070 | 0.801±0.047 | +3.9pp | 0.139 |
| Child | 20 | 11 | 0.882±0.030 | 0.871±0.035 | +1.1pp | 0.578 |
| Water | 32 | 4 | 0.579±0.068 | 0.569±0.049 | +1.1pp | 0.824 |
| Cancer | 5 | 4 | 0.964±0.062 | 0.964±0.062 | 0.0pp | tie |
| Mildew | 35 | 4 | 0.859±0.036 | 0.859±0.032 | 0.0pp | 0.989 |
| Asia | 8 | 12 | 0.900±0.100 | 0.967±0.033 | -6.7pp | 0.007 |

## Aggregate Tests (11 networks)

- **Direction**: 8 wins / 2 ties / 1 loss
- **Mean delta**: +7.6pp across 11 networks
- **Wilcoxon signed-rank** (9 non-tie networks): W=4.0, p=0.027
- **Sign test**: 8+ / 1- (p=0.020)

## Key Findings

1. **LOCALE wins or ties on 10/11 networks.** The only loss is Asia (8 nodes), the smallest network — where ego-graph's degree-1 vulnerability matters most.

2. **Largest wins on networks with complex structure.** Sachs (+30.7pp), Hailfinder (+16.7pp), Hepar2 (+16.0pp), Win95pts (+12.2pp), Insurance (+8.8pp).

3. **Ties on Cancer and Mildew.** Cancer is trivial (5 nodes). Mildew has temporal structure where both methods perform identically.

4. **Aggregate significance.** Wilcoxon p=0.027 — LOCALE is statistically significantly better overall across 11 networks.

## MosaCD Fidelity Gap (Critical Caveat)

Our same-model comparison uses Qwen-27B (4096 context) and n=10000. MosaCD paper uses GPT-4o-mini (128K context) and n=20000. The fidelity gap scales with network size because MosaCD's chain-based prompts need more context on larger networks:

| Network | Published MosaCD | Our MosaCD | Gap | LOCALE |
|---------|-----------------|-----------|-----|--------|
| Hepar2 | 0.72 | 0.405 | +31.5pp | 0.565 |
| Win95pts | 0.81 | 0.573 | +23.7pp | 0.694 |
| Insurance | 0.87 | 0.757 | +17.7pp | 0.845 |
| Alarm | 0.93 | 0.801 | +13.9pp | 0.841 |
| Hailfinder | 0.49 | 0.449 | +4.1pp | 0.616 |
| Mildew | 0.90 | 0.859 | +4.1pp | 0.859 |
| Child | 0.90 | 0.871 | +5.2pp | 0.882 |
| Asia | 0.93 | 0.967 | -3.7pp | 0.900 |
| Cancer | 1.00 | 0.964 | +3.6pp | 0.964 |
| Water | 0.59 | 0.569 | +2.1pp | 0.579 |

**Honest interpretation**: LOCALE wins against a context-constrained MosaCD re-implementation. On large networks (Hepar2, Win95pts, Alarm), LOCALE's absolute F1 is lower than MosaCD's published numbers. The same-model comparison isolates the methodological difference (ego-graph vs per-edge); the published-number gap reflects model + context differences. Both comparisons should be reported.
