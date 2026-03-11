---
id: XN-007
title: "Sachs & Child network MVE results (27B, post-bugfix)"
date: 2026-03-10
dag_nodes: [I02]
links:
  evidence_for: [I02]
  derived_from: [XN-003, XN-004]
  related_to: [XN-008]
---

# XN-007: Sachs & Child Network MVE Results

## Context

Extended MVE to Sachs (cell signaling, 11 nodes, 17 edges) and Child (neonatal diagnosis, 20 nodes, 25 edges). Initial runs had two bugs: (1) parser name mismatch for Sachs/Child where model sometimes outputs real names instead of V-codes, (2) context overflow for high-degree nodes (MAX_TOKENS=3000 + input tokens > 4096 context window). Both fixed.

## Bug: Context Overflow for High-Degree Nodes

**Root cause**: MAX_TOKENS was set to 3000 (for thinking mode headroom) for all queries. PKA (d=7) ego prompt = 1097 tokens. 1097 + 3000 = 4097 > 4096 context limit. All PKA ego queries returned HTTP 400 errors, parsed as "uncertain."

**Fix**: Dynamic MAX_TOKENS: 1500 for thinking mode, 500 for non-thinking (ego responses are ~7 lines, ~100 tokens max). This also likely affected the original batch runs of Sachs/Child.

## Results (post-bugfix, Qwen3.5-27B, disguised, non-thinking, v1 prompt)

### Sachs (5 test nodes covering 14/17 edges)
| Metric | PE | Ego | Delta |
|--------|-----|------|-------|
| Raw accuracy | 76.4% | 88.2% | +11.8pp |
| Majority vote | 81.8% | 90.9% | +9.1pp |
| CI violations | 13.3% | 3.8% | -9.5pp |
| Uncertain | 4.5% | 0.0% | -4.5pp |

**Strongest ego win across all networks.** PKA (d=7): ego 85.7% vs PE 60.0% (+25.7pp). PKC (d=5): ego 96.0% vs PE 72.0% (+24.0pp).

### Child (5 test nodes covering 18/25 edges)
| Metric | PE | Ego | Delta |
|--------|-----|------|-------|
| Raw accuracy | 87.8% | 85.2% | -2.6pp |
| Majority vote | 91.3% | 87.0% | -4.3pp |
| CI violations | 1.6% | 0.0% | -1.6pp |
| Uncertain | 0.0% | 0.0% | 0.0pp |

**PE slightly wins.** Disease (d=8): ego 85.0% vs PE 87.5% (-2.5pp). Sick (d=3): ego 33.3% vs PE 60.0% (-26.7pp, largest single-node ego loss).

## Cross-Network Summary (4 networks, 84 total edges)

| Network | PE maj | Ego maj | Ego wins? | CI viol PE | CI viol Ego |
|---------|--------|---------|-----------|------------|-------------|
| Insurance | 89.5% | 94.7% | Yes (+5.2) | 0% | 0% |
| Alarm | 75.0% | 80.0% | Yes (+5.0) | 0% | 0% |
| Sachs | 81.8% | 90.9% | Yes (+9.1) | 13.3% | 3.8% |
| Child | 91.3% | 87.0% | No (-4.3) | 1.6% | 0.0% |

Ego wins majority vote on 3/4 networks. CI violations always lower for ego.

## Limitations

- Only 5 test nodes per network (not full coverage). Child especially: 5/20 nodes = 25%.
- Single model (Qwen3.5-27B). No cross-model validation.
- K=5 passes — majority vote on 5 samples has high variance.
- Test nodes selected for high degree, biasing toward ego-favorable territory.
