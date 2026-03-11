---
id: XN-012
title: "Ablation study: phase contributions, degree analysis, hybrid strategies"
date: 2026-03-10
dag_nodes: [I02, I03, I04, I05]
links:
  evidence_for: [I02, I03, I04, I05]
  derived_from: [XN-009, XN-010, XN-011]
---

# XN-012: Ablation Study

## 1. Phase Contributions (Aggregate over 4 networks, 215 edges)

| Configuration | Accuracy | Delta vs PE |
|---------------|----------|-------------|
| PE baseline | 85.6% | — |
| Ego (Phase 1 swap) | 87.0% | +1.4pp |
| Ego + Phase 2 | 88.8% | +3.3pp |
| Ego + Phase 2 + Phase 3 | 89.7% | +4.1pp |
| Ego + Phase 2 + Phase 3 + Phase 4 | **92.2%** | **+6.6pp** |

Each phase contributes: Ego +1.4pp, Phase 2 +1.9pp, Phase 3 +0.9pp, Phase 4 +2.5pp.

## 2. Per-Degree Analysis (Phase 1 only, ego vs PE)

| Degree | PE acc | Ego acc | Delta | N edges | N nodes |
|--------|--------|---------|-------|---------|---------|
| d=2 | 76.9% | 84.6% | +7.7pp | 52 | 26 |
| d=3 | **88.4%** | **81.2%** | **-7.2pp** | 69 | 23 |
| d=4 | 92.9% | 96.4% | +3.6pp | 28 | 7 |
| d=5 | 88.9% | 91.1% | +2.2pp | 45 | 9 |
| d>=6 | 81.0% | 90.5% | +9.5pp | 21 | 3 |

Key finding: **ego loses at d=3 across all 4 networks**. This "valley of confusion" occurs because d=3 nodes have enough edges to make the joint prompt complex but too few CI constraints (usually 0-1 non-adjacent pairs) to provide structural guidance.

Ego wins most at d=2 and d>=6. At d=2, the ego prompt is simple (2 edges, 1 pair) and provides a useful adjacency signal. At d>=6, the abundance of CI constraints gives the LLM structural scaffolding.

## 3. Hybrid Phase 1 Strategy

| Config | Aggregate | vs PE | vs Ego |
|--------|-----------|-------|--------|
| PE only | 85.6% | — | -1.4pp |
| Ego only | 87.0% | +1.4pp | — |
| **PE for d=3, ego otherwise** | **89.3%** | **+3.7pp** | **+2.3pp** |
| PE for d=2,3 | 87.4% | +1.9pp | +0.5pp |
| PE for d=3,4 | 88.8% | +3.3pp | +1.9pp |

The d=3-only hybrid beats both pure strategies on all 4 networks. However, this is an observation, not a tuned hyperparameter. Needs validation on additional networks before committing as a design choice.

## 4. Bootstrap Confidence Intervals (K=5, 95% CI)

| Network | PE | Ego |
|---------|-----|-----|
| Insurance | 91.7% [87.5, 95.8] | 92.6% [88.9, 95.8] |
| Alarm | 79.8% [76.6, 83.1] | 85.0% [80.5, 89.6] |
| Sachs | 70.3% [61.8, 76.5] | 70.4% [64.7, 76.5] |
| Child | 89.8% [84.4, 96.9] | 86.6% [81.2, 90.6] |

CIs are wide due to K=5. No individual network shows a statistically significant ego advantage. K=15-20 would be needed for narrower CIs.

## 5. Query Cost Analysis

| Network | Centers | Ego queries | PE queries | Savings |
|---------|---------|-------------|------------|---------|
| Insurance | 22 | 110 | 360 | 69% (3.3x) |
| Alarm | 27 | 135 | 385 | 65% (2.9x) |
| Sachs | 11 | 55 | 170 | 68% (3.1x) |
| Child | 8 | 40 | 160 | 75% (4.0x) |

Average savings: 69% (3.3x). This is the most robust advantage — consistent across all networks and degree levels.

## Limitations

- K=5 votes → wide bootstrap CIs, majority vote is unreliable for close margins
- 4 networks, single model (27B) — generalization claims require validation
- d=3 finding needs validation on additional networks before using as a design choice
- No CI violation data tracked in Phase 1 results (field exists but not populated in full-coverage runs)
