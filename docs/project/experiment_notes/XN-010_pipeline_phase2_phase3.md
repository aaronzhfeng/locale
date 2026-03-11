---
id: XN-010
title: "Phase 2 (Max-2SAT) + Phase 3 (Reconciliation) pipeline results"
date: 2026-03-10
dag_nodes: [I02, I03, I04]
links:
  evidence_for: [I03, I04]
  derived_from: [XN-009]
---

# XN-010: Phase 2 + Phase 3 Pipeline Results

## Phase 2: Max-2SAT Local Constraint Compilation

For each ego-graph, collider/non-collider constraints from CI testing are compiled as hard clauses. The LLM's K=5 majority votes become soft scores. Exact enumeration finds the feasible assignment maximizing soft score.

### Results

| Network | Phase 1 (ego maj) | Phase 2 | Delta | Hard flips (helped/hurt) |
|---------|-------------------|---------|-------|--------------------------|
| Insurance | 93.1% | 97.2% | +4.2pp | 5/2 |
| Alarm | 88.3% | 89.6% | +1.3pp | 3/2 |
| Child | 87.5% | 93.8% | +6.2pp | 2/0 |
| Sachs | 70.6% | 64.7% | -5.9pp | 0/2 |

Key observations:
- Insurance: constraints fix RuggedAuto, Airbag, DrivHist, OtherCarCost. Near oracle ceiling (97.2% vs 98.6%).
- Child: constraints fix Sick and ChestXray. Matches oracle ceiling (93.8%).
- Alarm: LVEDVOLUME fixed by collider constraint (predicted in LOG-2026-03-10-7). ARTCO2 broken.
- Sachs: PKA's collider constraints force wrong directions on Akt and Raf. The CI structure amplifies LLM errors rather than correcting them.

## Phase 3: Dual-Endpoint Reconciliation

Each edge appears in two ego-graphs. Phase 3 reconciles disagreements using confidence-weighted resolution.

### Results

| Network | N unique edges | Phase 3 | Agreements | Disagreements |
|---------|---------------|---------|------------|---------------|
| Insurance | 37 | 97.3% | 34 | 1 |
| Alarm | 43 | 93.0% | 29 | 5 |
| Child | 23 | 91.3% | 8 | 1 |
| Sachs | 17 | 64.7% | 13 | 4 |

Key finding: **Alarm Phase 3 (93.0%) exceeds the ego-only oracle ceiling (89.6%)**. Dual-endpoint reconciliation adds genuinely new information — edges with only single-endpoint coverage benefit from the second perspective.

Agreement accuracy: 100% Insurance, 96.6% Alarm, 100% Child, 69.2% Sachs. When both endpoints agree, the direction is almost always correct (except Sachs).

## Full Pipeline Summary

| Network | PE baseline | Full pipeline | Delta | Cost |
|---------|-------------|---------------|-------|------|
| Insurance | 94.4% | 97.3% | +2.9pp | 3.3x fewer queries |
| Alarm | 80.5% | 93.0% | +12.5pp | 2.9x fewer queries |
| Child | 87.5% | 91.3% | +3.8pp | 4.0x fewer queries |
| Sachs | 76.5% | 64.7% | -11.8pp | 3.1x fewer queries |

The pipeline provides significant improvement on 3/4 networks at lower query cost. Sachs remains problematic — both endpoints systematically agree on wrong directions for several edges, and CI constraints amplify rather than correct these errors.

## Limitations

- Phase 2 infeasibility on some nodes (Age in Insurance, Disease/LungParench/HypoxiaInO2/HypDistrib in Child). These were handled by fallback to LLM-preferred directions.
- Phase 3 reconciliation uses simple confidence weighting. Dawid-Skene latent error estimation not yet implemented.
- Sachs failure mode: when LLM systematically misidentifies directions AND CI constraints reinforce those errors, the pipeline makes things worse.
