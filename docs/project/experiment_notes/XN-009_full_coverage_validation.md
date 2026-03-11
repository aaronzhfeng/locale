---
id: XN-009
title: "Full-coverage validation reveals selection bias in original 5-node results"
date: 2026-03-10
dag_nodes: [I02]
links:
  evidence_for: [I02]
  evidence_against: [I02]
  supersedes: [XN-007]
  related_to: [XN-008]
---

# XN-009: Full-Coverage Validation

## Context

The original MVE tested 5 hand-selected nodes per network — all high-degree, biased toward ego-favorable territory. research-reflect flagged this bias. Full-coverage runs test all nodes with d>=2.

## Results (Qwen3.5-27B, disguised, non-thinking, v1 prompt, K=5)

### Full Coverage vs Original 5-Node (majority vote)

| Network | N_orig | PE_orig | Ego_orig | N_full | PE_full | Ego_full | Bias |
|---------|--------|---------|----------|--------|---------|----------|------|
| Insurance | 19 | 89.5% | 94.7% | 72 | 94.4% | 93.1% | Ego advantage disappears |
| Alarm | 20 | 75.0% | 80.0% | 77 | 80.5% | 88.3% | Ego advantage grows |
| Sachs | 14 | 81.8% | 90.9% | 34 | 76.5% | 70.6% | Ego advantage reverses |
| Child | 18 | 91.3% | 87.0% | 32 | 87.5% | 87.5% | Stays tied |

### Key Findings

1. **Alarm is the genuine ego win.** +7.8pp on 77 edges with full coverage. HRBP: PE 0% → ego 80% (+80pp). HREKG: PE 40% → ego 90% (+50pp). The unfamiliar medical domain genuinely benefits from joint structural reasoning.

2. **Insurance is tied.** PE 94.4% vs ego 93.1% on 72 edges. The original +5.2pp advantage was from favorable node selection.

3. **Sachs reverses.** PE 76.5% vs ego 70.6% on 34 edges. Low-degree nodes (Akt d=2: ego 10%, PIP2 d=2: ego 30%) destroy ego performance. The original +9.1pp was entirely from high-degree nodes.

4. **Child is tied.** 87.5% = 87.5% on 32 edges.

5. **Query cost advantage is universal.** 2.9-4.0x fewer queries across all networks.

### Low-Degree Nodes Hurt Ego

Nodes with d=2 consistently show ego underperformance:
- Sachs: Akt 10%, PIP2 30%, PIP3 40%, P38 80%, Jnk 100% (avg ~52%)
- Alarm: CATECHOL (d=2) 10% ego, 10% PE (both terrible)
- With d=2 ego responses, there's only 1 neighbor — no cross-neighbor CI reasoning is possible, so the ego prompt provides no structural advantage over PE.

### Design Implication

Ego-graph prompting should only be applied to nodes with d>=3. For d<3, use per-edge.

## Aggregate (215 edges across 4 networks, full coverage)

| Metric | PE | Ego |
|--------|-----|------|
| Majority vote | 85.6% | 85.6% |
| Raw accuracy | 83.3% | 83.3% |

**Aggregate is tied.** The ego advantage on Alarm is offset by the ego disadvantage on Sachs.

## Implication for Paper

The honest story is: ego-graph prompting is a cost-efficient alternative (3-4x fewer queries) with domain-dependent accuracy effects. It is not categorically better. The contribution is an empirical characterization of when joint context helps, not a system that always wins.
