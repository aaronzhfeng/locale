---
id: XN-013
title: "New benchmarks (Asia, Hepar2) and 6-network aggregate results"
date: 2026-03-10
dag_nodes: [I02, I03, I04, I05]
links:
  evidence_for: [I02, I05]
  derived_from: [XN-011, XN-012]
---

# XN-013: New Benchmarks and 6-Network Aggregate

## 1. New Networks

### Asia (8 nodes, 8 edges, pulmonary medicine)
- Phase 1: 100% PE, 100% ego (trivial network — all edges correct)
- Phase 2: 83.3% (constraints hurt: -16.7pp)
- Phase 3: 71.4% (reconciliation made it worse)
- Phase 4: **100%** (safety valve reverted all damage)
- Takeaway: Safety valve essential. Small simple networks don't benefit from CI constraints.

### Hepar2 (70 nodes, ~67 unique edges, liver disease)
- Phase 1: PE 73.9%, ego 76.6% (+2.7pp ego advantage)
- Phase 2: 65.8% (-10.8pp from ego, constraints harmful)
- Phase 3: 65.7% (no improvement)
- Phase 4: **80.6%** (+4.0pp over ego, +6.7pp over PE)
- Safety valve detected -9.9pp Phase 2 delta, reverted 15 harmful constraint flips
- Largest network tested (70 nodes). Pipeline scales.

### Hailfinder (56 nodes, severe weather — BLOCKED)
- PC skeleton estimation stuck at 37+ min. O(n^2 * 2^k) complexity.
- Killed. Need faster skeleton method for 50+ node networks.

## 2. Full 6-Network Pipeline Comparison

| Network | N | PE | Ego | Ego+P2 | P3 | P4 | Method |
|---------|---|-----|-----|--------|-----|-----|--------|
| Insurance | 72 | 94.4% | 93.1% | 97.2% | 97.3% | 97.3% | standard |
| Alarm | 77 | 80.5% | 88.3% | 89.6% | 93.0% | 93.0% | standard |
| Sachs | 34 | 76.5% | 70.6% | 64.7% | 64.7% | 76.5% | standard |
| Child | 32 | 87.5% | 87.5% | 93.8% | 91.3% | 95.7% | adaptive |
| Asia | 12 | 100% | 100% | 83.3% | 71.4% | 100% | standard |
| Hepar2 | 111 | 73.9% | 76.6% | 65.8% | 65.7% | 80.6% | standard |
| **Aggregate** | **338** | **82.2%** | **84.0%** | **81.1%** | **81.2%** | **88.7%** | |

## 3. Critical Finding: Phase 2 Hurts Aggregate

Phase 2 CI constraints actually reduce aggregate accuracy: ego 84.0% → ego+P2 81.1% (-3.0pp). Constraints hurt on 3 of 6 networks:
- Sachs: 70.6% → 64.7% (-5.9pp)
- Asia: 100% → 83.3% (-16.7pp)
- Hepar2: 76.6% → 65.8% (-10.8pp)

This makes Phase 4 (safety valve) the critical component, not a cleanup step. Without it, the pipeline would be *worse* than the ego baseline.

## 4. Updated Per-Degree Analysis (6 networks, 338 edges)

| Degree | PE | Ego | Delta | N |
|--------|-----|-----|-------|---|
| d=2 | 74.5% | 78.3% | +3.8pp | 106 |
| d=3 | 83.9% | 80.6% | **-3.2pp** | 93 |
| d=4 | 86.4% | 86.4% | +0.0pp | 44 |
| d=5 | 88.9% | 91.1% | +2.2pp | 45 |
| d>=6 | 86.0% | 94.0% | +8.0pp | 50 |

d=3 valley persists (-3.2pp) but is weaker than 4-network estimate (-7.2pp). Hepar2 breaks the pattern: ego *wins* at d=3 (+8.3pp). The finding is network-dependent, not universal.

## 5. Updated Hybrid Analysis (6 networks)

| Config | Aggregate | vs PE | vs Ego |
|--------|-----------|-------|--------|
| PE only | 82.2% | — | -1.8pp |
| Ego only | 84.0% | +1.8pp | — |
| PE for d=3 | 84.9% | +2.7pp | +0.9pp |
| PE for d=3,4 | 84.9% | +2.7pp | +0.9pp |
| PE for d=2,3 | 83.7% | +1.5pp | -0.3pp |

Hybrid still helps (+0.9pp vs ego) but the gain is modest and not consistent enough to commit as a design choice.

## 6. Query Cost (6 networks)

| Network | Centers | Ego queries | PE queries | Savings |
|---------|---------|-------------|------------|---------|
| Insurance | 22 | 110 | 360 | 69% (3.3x) |
| Alarm | 27 | 135 | 385 | 65% (2.9x) |
| Sachs | 11 | 55 | 170 | 68% (3.1x) |
| Child | 8 | 40 | 160 | 75% (4.0x) |
| Asia | 5 | 25 | 60 | 58% (2.4x) |
| Hepar2 | 38 | 190 | 555 | 66% (2.9x) |

Average savings: 67% (3.1x). Consistent across all networks.

## Limitations

- Hailfinder blocked by PC skeleton scalability
- K=5 still produces wide bootstrap CIs
- Single model (27B) — no cross-model validation yet
- CI constraint quality depends on PC skeleton quality and sample size
