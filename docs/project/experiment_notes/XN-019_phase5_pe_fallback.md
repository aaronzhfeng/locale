---
id: XN-019
title: "Phase 5 PE fallback: mixed results, tiebreaking helps small networks"
date: 2026-03-11
dag_nodes: [I05]
links:
  related_to: [XN-018, XN-010]
---

## Setup

Implemented budgeted per-edge fallback per proposal v2 Section 4.7. Uses existing PE data from Phase 1 as fallback for hard-tail edges (disagreement + single-endpoint). Budget: 15% of skeleton edges.

Two override strategies tested:
1. Margin-based: PE overrides ego if PE margin > ego margin (too aggressive)
2. 2/3 majority tiebreaker: PE breaks disagreement ties (better but still hurts Alarm)

## Results (2/3 tiebreaker, disagreement-only override)

| Network   | Tail | Changes | Improved | Worsened | P3    | P5    | Delta   |
|-----------|------|---------|----------|----------|-------|-------|---------|
| Insurance | 6    | 0       | 0        | 0        | 95.3% | 95.3% | +0.0pp  |
| Alarm     | 15   | 2       | 0        | 2        | 93.0% | 88.4% | -4.7pp  |
| Sachs     | 4    | 1       | 1        | 0        | 76.5% | 82.4% | +5.9pp  |
| Child     | 8    | 1       | 1        | 0        | 88.0% | 92.0% | +4.0pp  |
| Asia      | 2    | 0       | 0        | 0        | 100%  | 100%  | +0.0pp  |
| Hepar2    | 31   | 0       | 0        | 0        | 87.5% | 87.5% | +0.0pp  |

## Key finding

PE fallback helps on small hard networks (Sachs +5.9pp, Child +4.0pp) but hurts on Alarm (-4.7pp) where PE and ego have correlated errors. The problem is network-specific: there's no universal criterion for when PE override is safe.

## Implication

Phase 5 should be gated by Phase 6 (selective output). Rather than forcing overrides, flag hard-tail edges as uncertain and let Phase 6 abstain on them. This is precisely the proposal's design intent.
