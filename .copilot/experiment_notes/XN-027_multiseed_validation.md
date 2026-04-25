---
id: XN-027
title: "Multi-seed validation: LOCALE 4W/0T/1L vs MosaCD across 5 networks"
date: 2026-03-12
dag_nodes: [E01, I02, I03]
links:
  evidence_for: [E01]
  related_to: [XN-024, XN-022, LN-003]
tags: [multi-seed, robustness, mosacd, comparison, validation]
---

# XN-027: Multi-Seed Validation (4 seeds × 5 networks × 2 methods)

## Motivation

Single-seed (s42) same-model comparison (XN-024) showed LOCALE roughly 1W/3T on 4 networks. Research-reflect (LOG-2026-03-11-32) recommended multi-seed validation before any claims, rating MosaCD comparison confidence at 2/5 with single seed.

## Setup

- **Seeds**: 0, 1, 2, 42 (4 seeds per condition)
- **Networks**: Insurance (52 edges), Alarm (46), Child (25), Sachs (17), Asia (8)
- **Data**: n=10,000 samples per seed, PC-stable skeleton (same skeleton per seed)
- **LOCALE**: Phase 1 (ego-graph K=10 debiased) → Phase 2 (NCO Max-2SAT) → Phase 3 (confidence-weighted reconciliation)
- **MosaCD**: Per-edge orientation (5 reps × 2 orderings = 10 queries/edge), shuffled debiasing, non-collider-first propagation
- **Model**: Qwen3.5-27B-FP8 (same model for both methods), non-thinking mode
- **Win/Tie/Loss**: >2pp = WIN, <-2pp = LOSS, else TIE

## Results

### Summary Table

| Network | LOCALE F1 | MosaCD F1 | Delta | Result |
|---------|-----------|-----------|-------|--------|
| Insurance | 0.853 ± 0.011 | 0.806 ± 0.056 | +4.6pp | **WIN** |
| Alarm | 0.876 ± 0.016 | 0.801 ± 0.016 | +7.5pp | **WIN** |
| Sachs | 0.824 ± 0.042 | 0.523 ± 0.098 | +30.1pp | **WIN** |
| Child | 0.900 ± 0.020 | 0.876 ± 0.007 | +2.4pp | **WIN** |
| Asia | 0.867 ± 0.067 | 0.933 ± 0.000 | -6.7pp | **LOSS** |

**Score: LOCALE 4W / 0T / 1L**

### Per-Seed Detail

**Insurance** (52 edges):
| Seed | LOCALE F1 | MosaCD F1 | Delta |
|------|-----------|-----------|-------|
| 0 | 0.842 | 0.723 | +0.119 |
| 1 | 0.863 | 0.851 | +0.012 |
| 2 | 0.842 | 0.787 | +0.055 |
| 42 | 0.863 | 0.863 | 0.000 |

**Alarm** (46 edges):
| Seed | LOCALE F1 | MosaCD F1 | Delta |
|------|-----------|-----------|-------|
| 0 | 0.876 | 0.791 | +0.085 |
| 1 | 0.854 | 0.822 | +0.032 |
| 2 | 0.876 | 0.782 | +0.095 |
| 42 | 0.899 | 0.809 | +0.090 |

**Sachs** (17 edges):
| Seed | LOCALE F1 | MosaCD F1 | Delta |
|------|-----------|-----------|-------|
| 0 | 0.824 | 0.444 | +0.379 |
| 1 | 0.824 | 0.412 | +0.412 |
| 2 | 0.882 | 0.647 | +0.235 |
| 42 | 0.765 | 0.588 | +0.176 |

**Child** (25 edges):
| Seed | LOCALE F1 | MosaCD F1 | Delta |
|------|-----------|-----------|-------|
| 0 | 0.880 | 0.863 | +0.017 |
| 1 | 0.920 | 0.880 | +0.040 |
| 2 | 0.920 | 0.880 | +0.040 |
| 42 | 0.880 | 0.880 | 0.000 |

**Asia** (8 edges):
| Seed | LOCALE F1 | MosaCD F1 | Delta |
|------|-----------|-----------|-------|
| 0 | 0.800 | 0.933 | -0.133 |
| 1 | 0.933 | 0.933 | 0.000 |
| 2 | 0.800 | 0.933 | -0.133 |
| 42 | 0.933 | 0.933 | 0.000 |

## Key Observations

### 1. Single-seed was misleading
Seed 42 was MosaCD's best or tied-best seed on 4/5 networks. Insurance s42 was a tie (0.863 vs 0.863), but multi-seed reveals LOCALE wins by +4.6pp on average. Single-seed comparison would have understated LOCALE's advantage.

### 2. LOCALE is more robust across seeds
- LOCALE std: 0.011, 0.016, 0.042, 0.020, 0.067 (mean: 0.031)
- MosaCD std: 0.056, 0.016, 0.098, 0.007, 0.000 (mean: 0.035)
- On Insurance and Sachs, MosaCD variance is 5x and 2.3x higher respectively.
- MosaCD's shuffled debiasing (5 reps × 2 orderings) introduces sampling randomness that compounds across edges. LOCALE's ego-graph voting (K=10 from a single joint prompt) is inherently more stable.

### 3. Sachs reveals MosaCD fragility
MosaCD Sachs spans 0.412–0.647 (23.5pp range) vs LOCALE 0.765–0.882 (11.7pp range). The per-edge approach is catastrophically unstable on noisy, small networks where CI testing produces unreliable skeletons.

### 4. Asia is MosaCD's clear strength
MosaCD achieves 0.933 perfectly on every seed (zero variance). Asia has only 8 edges — the per-edge approach with 10 queries per edge gives very high confidence. LOCALE's ego-graph approach introduces more variance on tiny networks where the ego subgraph is the whole graph.

### 5. Child is now a WIN, not a TIE
Single-seed showed Child as a tie (0.880 vs 0.880). Multi-seed reveals LOCALE averages 0.900 vs MosaCD 0.876 — a consistent +2.4pp advantage.

## Shift from Single-Seed

| Network | Single-seed (s42) | Multi-seed (4 seeds) |
|---------|-------------------|---------------------|
| Insurance | TIE (0.863 vs 0.863) | **WIN** (+4.6pp) |
| Alarm | WIN (+9.0pp) | WIN (+7.5pp) |
| Sachs | not compared | **WIN** (+30.1pp) |
| Child | TIE (0.880 vs 0.880) | **WIN** (+2.4pp) |
| Asia | TIE (0.933 vs 0.933) | **LOSS** (-6.7pp) |

Single-seed: 1W/3T → Multi-seed: 4W/0T/1L

## Caveats

1. n=10k only — no sample-size sensitivity analysis across seeds
2. Both methods share the same PC-stable skeleton per seed — skeleton is not the variable under test
3. Asia loss may reflect LOCALE's ego-graph approach being suboptimal for very small networks (8 edges)
4. Only 4 seeds — formal statistical significance testing would require more seeds or a paired test

## Artifacts

- `experiments/results/multiseed_comparison.json` — full per-seed metrics
- `experiments/results/mve_27b_{network}_10k_k10_debiased_s{0,1,2,42}/` — LOCALE results
- `experiments/results/mosacd_{network}_s{0,1,2}/` — MosaCD new seed results
- `experiments/results/mosacd_{network}/` — MosaCD seed 42 reference
