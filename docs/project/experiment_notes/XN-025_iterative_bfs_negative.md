---
id: XN-025
title: "Iterative BFS decimation: negative result, single-pass beats multi-round"
date: 2026-03-11
dag_nodes: [E02, I02, I03, I05]
links:
  evidence_against: [E02]
  evidence_for: [I02]
  related_to: [XN-024]
tags: [negative-result, iterative, decimation]
---

# XN-025: Iterative BFS Ego-Graph Expansion — Negative Result

## Hypothesis

Multi-round ego-graph querying with SP-style decimation should improve orientation accuracy. Established orientations from earlier rounds provide additional context to the LLM, and hard constraints in Max-2SAT reduce the solution space.

## Setup

- **File**: `experiments/iterative_bfs.py`
- **Design**: Round 1 queries all eligible nodes (K=5), decimates high-confidence edges (majority > 0.7). Round 2 re-queries all nodes with enriched prompts containing established orientations as fixed facts. Max-2SAT extended with unary hard constraints.
- **Networks**: Insurance, Alarm (n=10k, non-thinking mode)
- **Comparison**: LOCALE single-pass (K=10), same total query budget (~230-260 queries)

## Results

| Network | Method | Queries | Accuracy | F1 | P | R |
|---------|--------|---------|----------|-----|------|------|
| Insurance | LOCALE K=10 | ~230 | 95.3% | 0.863 | 0.953 | 0.788 |
| Insurance | BFS R1 (K=5) | 115 | 92.3% (39/43) | 0.791 | 0.923 | 0.692 |
| Insurance | BFS requery (K=5×2) | 230 | 88.4% (43/43) | 0.800 | 0.884 | 0.731 |
| Alarm | LOCALE K=10 | ~260 | 93.0% | 0.899 | 0.930 | 0.870 |
| Alarm | BFS requery (K=5×2) | 260 | 93.0% (43/43) | 0.899 | 0.930 | 0.870 |

## Analysis

1. **Insurance: Single-pass wins decisively.** LOCALE K=10 (F1=0.863) > BFS K=5×2 (F1=0.800) with same query budget. The 6.3pp gap is significant.

2. **Alarm: Tie.** Both methods achieve identical F1=0.899 with ~260 queries. The iterative context didn't help but also didn't hurt.

3. **BFS R1 selective output is interesting.** Round 1 only commits 39/43 edges at 92.3% precision — 4 uncertain edges are withheld. This is conceptually similar to Phase 6 calibration but at the decimation level.

4. **Decimation threshold matters.** With threshold=0.7, Round 1 commits ~90-98% of edges. The remaining 2-10% get resolved in Round 2 but don't improve accuracy.

## Root Cause Analysis

Why doesn't iterative context help on Insurance?

1. **K=5 is too few votes per round.** With only 5 passes, soft scores are noisier, leading to more R1 decimation errors. These errors become hard constraints in R2, compounding.

2. **Error amplification.** If R1 commits an incorrect edge, R2 treats it as ground truth. The LLM sees "ESTABLISHED: A→B" and may rationalize the wrong direction rather than independently evaluating it.

3. **Diminishing returns of context.** The LLM already has the full ego-graph structure. Adding "this edge was oriented A→B in a previous round" doesn't provide genuinely new information — it just reinforces the prior round's (potentially incorrect) judgment.

4. **More votes > more context.** 10 independent votes per node (LOCALE) provide more robust soft scores than 5 votes + context from potentially-wrong established edges (BFS).

## Conclusion

The iterative BFS design from the original proposal is a negative result. Single-pass LOCALE with K=10 passes is both simpler and more accurate than multi-round BFS with K=5 passes per round. The value of additional LLM queries is better spent on independent re-evaluations than on context-enriched re-queries.

This validates the current LOCALE design and should be reported as an ablation in the paper (single-pass vs iterative).
