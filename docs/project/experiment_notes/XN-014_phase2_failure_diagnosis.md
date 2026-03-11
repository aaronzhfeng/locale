---
id: XN-014
title: "Phase 2 failure diagnosis: systematic false-collider bias in CI facts"
date: 2026-03-10
dag_nodes: [I03]
links:
  evidence_against: [I03]
  derived_from: [XN-013]
---

# XN-014: Phase 2 Failure Diagnosis

## Root Cause: False Collider Bias

100% of incorrect CI facts (across all 6 networks) follow the same pattern: **PC says "collider" when ground truth says "non-collider."** Not a single false non-collider was observed.

| Network | CI Facts | CI Accuracy | False Colliders | Phase 2 Delta |
|---------|----------|-------------|-----------------|---------------|
| Insurance | 92 | 92.4% | 7 | +4.2pp |
| Alarm | 73 | 90.4% | 7 | +1.3pp |
| Sachs | 22 | 95.5% | 1 | -5.9pp |
| Child | 57 | 78.9% | 12 | +6.2pp |
| Asia | 10 | 90.0% | 1 | -16.7pp |
| Hepar2 | 149 | **65.1%** | **52** | **-9.9pp** |

## Why False Colliders?

The PC algorithm tests conditional independence (CI). When two neighbors n1, n2 of node v are NOT conditionally independent given conditioning sets, PC infers n1→v←n2 (collider). False positive CI tests (detecting dependence when variables are actually independent given the right conditioning set) produce false collider claims.

This happens because:
1. **Limited sample size** (1000 samples) → noisy CI test statistics
2. **Incomplete conditioning** → confounding paths create spurious dependence
3. **Large networks** → more confounding paths → more false positives

Hepar2 (70 nodes) has by far the worst CI accuracy (65.1%) because its large size creates many confounding paths that fool CI tests with only 1000 samples.

## Hard Flip Analysis

| Network | Flips | Helpful | Harmful | Net |
|---------|-------|---------|---------|-----|
| Insurance | 7 | 5 | 2 | +3 |
| Alarm | 5 | 3 | 2 | +1 |
| Sachs | 2 | 0 | 2 | -2 |
| Child | 2 | 2 | 0 | +2 |
| Asia | 2 | 0 | 2 | -2 |
| Hepar2 | 19 | 3 | 15 | -12 |

Hepar2's 15 harmful flips come from false collider constraints forcing wrong directions.

## Failure Patterns

### Pattern 1: Hub Node Cascade (Sachs, Asia)
A single incorrect CI fact at a hub node cascades to flip multiple edges.
- Sachs: PKA (d=7, 14 constraints, 1/128 feasible) — one false collider forces 2 wrong edges
- Asia: smoke (d=2, 1 constraint, 1/4 feasible) — one false collider forces 2 wrong edges from a previously perfect node

### Pattern 2: Systematic Accuracy Erosion (Hepar2)
Many incorrect CI facts across many nodes create widespread damage.
- 9 damaged nodes, 15 harmful flips, scattered across degree 2-4 nodes
- Low feasibility: 28/33 constrained nodes have <50% feasible assignments

### Pattern 3: Correct CI Facts Help (Insurance, Child)
When CI facts are largely correct, constraints genuinely improve accuracy.
- Insurance: 92.4% CI accuracy → +4.2pp improvement
- Child: even with only 78.9% CI accuracy, the 2 flips that happen to occur are both correct → +6.2pp

## Implications

1. **Phase 2 is not inherently harmful** — it helps when CI facts are correct
2. **CI fact quality is the bottleneck**, not the Max-2SAT formulation
3. **The safety valve (Phase 4) is essential** because CI fact quality is unpredictable
4. **Potential fix**: treat collider claims as soft constraints (since 100% of errors are false colliders), or add CI test confidence thresholds

## Suggested Improvements (not yet tested)

1. **Soft collider constraints**: Weight collider constraints by CI test p-value instead of treating as hard constraints
2. **Asymmetric treatment**: Non-collider claims are reliable (0% false positive rate); collider claims are unreliable
3. **Sample size scaling**: Use more samples for larger networks (Hepar2 needs >1000)
4. **Feasibility gating**: If feasibility ratio < 10%, skip constraints for that node (use Phase 1 majority vote)
