---
id: XN-018
title: "Phase 4 conservative propagation: Meek rules are a no-op on fully-oriented graphs"
date: 2026-03-11
dag_nodes: [I04]
links:
  related_to: [XN-010, XN-011, XN-015]
---

## Setup

Implemented proper conservative propagation per proposal v2 Section 4.6:
- Priority queue ordering edges by Phase 3 confidence
- Incremental batch commitment with cycle checking
- Meek R1-R4 applied after each batch
- Conservative Meek acceptance: only accept if agrees with LLM vote or LLM had low confidence (<0.4)

## Results (6 networks, K=10 debiased, n=10k)

| Network   | P3 Acc | P4 Acc | Delta | Committed | Meek | Flips |
|-----------|--------|--------|-------|-----------|------|-------|
| Insurance | 95.3%  | 95.3%  | 0.0pp | 16        | 27   | 0     |
| Alarm     | 93.0%  | 93.0%  | 0.0pp | 25        | 18   | 0     |
| Sachs     | 76.5%  | 76.5%  | 0.0pp | 16        | 1    | 0     |
| Child     | 88.0%  | 88.0%  | 0.0pp | 8         | 17   | 0     |
| Asia      | 100.0% | 100.0% | 0.0pp | 6         | 1    | 0     |
| Hepar2    | 87.5%  | 87.5%  | 0.0pp | 22        | 42   | 0     |

Phase 4 is a strict no-op: no accuracy change, no cycle flips needed.

## Why Meek doesn't help

1. **All edges already oriented**: Max-2SAT (Phase 2) orients every skeleton edge. There are no "unresolved" edges for Meek to newly compel.
2. **Conservative filtering rejects bad Meek**: On Hepar2, Meek proposed 55 orientations but 14 were rejected because they contradicted confident LLM votes. Without conservative filtering, Meek drops Insurance from 95.3% to 72.1% (naive propagation on imperfect skeleton).
3. **Imperfect skeleton breaks Meek**: Meek R1 requires "A not adj C" but if PC missed the A-C edge, Meek wrongly orients B→C. With only 52-83% skeleton coverage, this is frequent.

## Key insight

Conservative Meek filtering is **essential** for correctness but contributes 0pp to accuracy. The value of Phase 4 is **damage prevention**, not improvement. The old safety-valve mechanism (reverting Phase 2 damage) provides more value than Meek propagation.

## Implication for proposal

The proposal's Phase 4 vision assumes a propagation-rich setting where many edges remain unresolved after reconciliation. In our pipeline, Phase 2 (Max-2SAT) resolves everything, making Phase 4 propagation redundant. Phase 4's value would increase if we made Phase 2 output partial (only commit edges above a confidence threshold), but that would likely hurt Phase 3.
