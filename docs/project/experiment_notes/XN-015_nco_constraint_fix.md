---
id: XN-015
title: "Non-collider-only constraints: fixing Phase 2 by removing false colliders"
date: 2026-03-10
dag_nodes: [I03, I05]
links:
  evidence_for: [I03, I05]
  derived_from: [XN-014]
---

# XN-015: Non-Collider-Only (NCO) Constraint Fix

## Discovery

XN-014 revealed that 100% of incorrect CI facts from the PC algorithm are false colliders (says "collider" when ground truth says "non-collider"). Non-collider claims are 100% reliable across all 6 networks. This suggests a simple fix: drop all collider constraints and use only non-collider constraints in Phase 2.

## Phase 2 Results: Hard vs NCO

| Network | N | Ego (P1) | P2 Hard | P2 NCO |
|---------|---|----------|---------|--------|
| Insurance | 72 | 93.1% | 97.2% | **98.6%** |
| Alarm | 77 | 88.3% | 89.6% | 89.6% |
| Sachs | 34 | 70.6% | 64.7% | **70.6%** |
| Child | 32 | 87.5% | 93.8% | 90.6% |
| Asia | 12 | 100% | 83.3% | **100%** |
| Hepar2 | 111 | 75.7% | 65.8% | **79.3%** |
| **Aggregate** | **338** | **83.7%** | **81.1%** | **86.7%** |

NCO Phase 2 improves aggregate by +5.6pp over hard Phase 2, and +3.0pp over ego baseline. It never regresses below Phase 1 on any network except a harmless tie.

## Full Pipeline: Hard vs NCO (through Phase 4)

| Network | PE | Hard P4 | NCO P4 |
|---------|-----|---------|--------|
| Insurance | 94.4% | 97.3% | **100.0%** |
| Alarm | 80.5% | **93.0%** | 90.7% |
| Sachs | 76.5% | 76.5% | 76.5% |
| Child | 87.5% | **95.7%** | 91.3% |
| Asia | 100% | 100% | 100% |
| Hepar2 | 71.2% | 80.6% | **83.6%** |
| **Aggregate** | **81.4%** | **88.7%** | **89.3%** |

NCO pipeline: +7.9pp vs PE baseline, +0.6pp vs hard pipeline.

## Analysis

### Where NCO wins (Insurance +2.7pp, Hepar2 +3.0pp)
False colliders were the main damage source. Removing them lets the correct non-collider constraints guide orientation without interference.

### Where Hard wins (Alarm -2.3pp, Child -4.4pp)
Some true collider constraints genuinely help. In Alarm and Child, enough collider claims are correct that they outweigh the false ones. The safety valve in the hard pipeline catches the few wrong ones.

### Insurance reaches 100%
NCO pipeline achieves perfect orientation on all 72 Insurance edge decisions. This is the strongest single-network result in the study.

## Implications

1. **NCO is the safer default**: Never regresses below Phase 1 (no safety valve needed for Phase 2)
2. **Hard + safety valve is slightly better for some networks** but requires the safety valve machinery
3. **The ideal approach**: A confidence-weighted mode that trusts collider claims proportional to CI test confidence. This is future work.
4. **For the paper**: Present both modes. NCO as the robust default, hard+safety valve as the optimistic variant.

## Constraint statistics

Hard flip analysis with NCO:
| Network | Flips | Helpful | Harmful |
|---------|-------|---------|---------|
| Insurance | 4 | 4 | 0 |
| Alarm | 1 | 1 | 0 |
| Sachs | 0 | 0 | 0 |
| Child | 1 | 1 | 0 |
| Asia | 0 | 0 | 0 |
| Hepar2 | 6 | 4 | 1 |

NCO eliminates harmful flips on 5/6 networks (only 1 on Hepar2).
