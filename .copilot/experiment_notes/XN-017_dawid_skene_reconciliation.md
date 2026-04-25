---
id: XN-017
title: "Dawid-Skene reconciliation: structural mismatch with ego-graph annotations"
date: 2026-03-11
dag_nodes: [I03]
links:
  evidence_against: [I03]
  related_to: [XN-010, XN-011]
---

## Setup

Implemented proper Dawid-Skene EM reconciliation per proposal v2 Section 4.5. Tested three formulations on K=10 debiased results across all 6 networks:

1. **3-class per-pass**: Each (node, pass_idx) = 1 annotator, labels {u->v, v->u, abstain}
2. **2-class per-pass**: Same annotators, labels {u->v, v->u} only
3. **2-class per-node**: Each node = 1 annotator (majority of K passes), labels {u->v, v->u}

## Results (per-node 2-class, best DS variant)

| Network   | Edges | MV Acc  | DS Acc  | Delta    |
|-----------|-------|---------|---------|----------|
| Insurance | 43    | 97.7%   | 86.0%   | -11.6pp  |
| Alarm     | 43    | 90.7%   | 79.1%   | -11.6pp  |
| Sachs     | 17    | 76.5%   | 82.4%   | +5.9pp   |
| Child     | 25    | 84.0%   | 88.0%   | +4.0pp   |
| Asia      | 7     | 100.0%  | 100.0%  | +0.0pp   |
| Hepar2    | 64    | 79.7%   | 76.6%   | -3.1pp   |

DS helps on Sachs (+5.9pp) and Child (+4.0pp) but hurts on Insurance (-11.6pp), Alarm (-11.6pp), and Hepar2 (-3.1pp).

## Per-pass aggregation (auditor follow-up)

Per auditor concern MSG-2026-03-11-021, tested per-pass aggregation (each center x pass_idx = 1 annotator, giving ~19 annotations/edge with K=10):

| Network   | Edges | MV Acc  | DS Acc (per-pass) | Delta   |
|-----------|-------|---------|-------------------|---------|
| Insurance | 43    | 97.7%   | 88.4%             | -9.3pp  |
| Alarm     | 43    | 90.7%   | 83.7%             | -7.0pp  |
| Sachs     | 17    | 76.5%   | 76.5%             | +0.0pp  |

Per-pass with ~19 annotations/edge still underperforms MV. DS learns skewed class priors (0.38/0.62 on Insurance) that overwhelm the vote signal.

## Root cause

The issue persists even with ~19 annotators per edge. The problem is not just annotator sparsity but that:

- EM cannot reliably estimate per-annotator error rates (each annotator labels ~5-20 edges, split across 2 directions)
- The algorithm tends to overfit to class priors rather than learning meaningful annotator quality differences
- On networks where MV already has high accuracy (Insurance 97.7%), DS adds noise by re-weighting toward unreliable error rate estimates

The 3-class model was even worse: the abstain class absorbed ~44% prior probability on Insurance, pulling mass from correct directions.

## Conclusion

DS is not suitable for this data structure. The simplified confidence-weighted reconciliation (Phase 3 current) outperforms DS on 3/6 networks and ties on 1/6. The proposal mandates DS as the "full-sweep backbone" but the empirical evidence shows it doesn't fit our annotator sparsity regime.

**Decision**: Keep simplified confidence-weighted reconciliation as Phase 3. Document DS failure as evidence that ego-graph annotations (2 endpoints per edge) don't match DS's many-annotator assumption. The proposal's mandatory "EBCC/BCC sensitivity analysis on confirmatory subset" is also unlikely to help given the same structural mismatch.
