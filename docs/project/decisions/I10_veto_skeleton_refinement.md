---
id: D-I10
title: "Veto LLM-based skeleton refinement"
date: 2026-03-11
dag_nodes: ["I10"]
links:
  evidence_for: [XN-021]
  related_to: [XN-016]
tags: ["veto", "negative-result"]
---

# D-I10: Veto LLM-based skeleton refinement

## Decision

LLM-based skeleton refinement (using pairwise "should there be an edge?" queries to recover edges PC missed) is vetoed after testing on 5/6 benchmark networks with 0 true positives recovered.

## Context

F1 decomposition (XN-016, LOG-2026-03-11-20) established that skeleton coverage is the binding constraint on directed-edge F1, not orientation quality. Skeleton refinement was proposed as a novel contribution to address this bottleneck: query the LLM about candidate missing edges and add them if the LLM agrees.

## What was tested

- 5 networks: Insurance (85 candidates), Alarm (71), Sachs (14), Child (52), Asia (10)
- Prompt: debiased (no anchoring to statistical test results)
- Voting: K=5 passes at temperatures 0.3-1.1, 60% yes-vote threshold
- Model: Qwen3.5-27B non-thinking mode

## Results

| Network   | GT Missing | Reachable (2-hop) | TP Added | FP Added |
|-----------|------------|-------------------|----------|----------|
| Insurance | 10         | 4                 | 0        | 0        |
| Alarm     | 3          | 3                 | 0        | 0        |
| Sachs     | 0          | N/A               | N/A      | N/A      |
| Child     | 0          | N/A               | N/A      | N/A      |
| Asia      | 1          | 1                 | 0        | 0        |

## Root causes

### 1. Reachability bottleneck
Most GT-missing edges are far apart in the skeleton graph. Insurance: 6/10 missing edges are at distance 4-5. Expanding candidate radius beyond 2 hops creates hundreds of candidates with vanishing base rates.

### 2. LLM conservatism on ambiguous edges
The GT-missing edges that ARE reachable are genuinely domain-ambiguous:
- GoodStudent--SocioEcon: 1/5 yes votes
- MakeModel--RiskAversion: 1/5 yes votes
- RiskAversion--VehicleYear: 1/5 yes votes
- CarValue--Theft: 0/5 yes votes

A 27B model lacks the fine-grained domain expertise to confidently assert these edges.

### 3. Proposal scope
The proposal (v2, line 101) explicitly states: "The LLM does not alter the skeleton, sepsets, or CI test results." Skeleton refinement is fundamentally outside the design principles.

### 4. Literature support
"Mitigating Prior Errors in Causal Discovery" (2306.07032) classifies LLM-suggested edge additions as "irrelevant priors" or "indirect priors" — the types that cause cascading damage to downstream structure learning.

## Alternatives considered and rejected

- **Thinking mode**: Would be ~100x slower per query. Root causes are structural, not about reasoning depth.
- **Data-informed prompts**: Showing mutual information scores. Would add complexity without addressing reachability.
- **Higher hop radius**: 3-hop creates hundreds more candidates; 4-5 hop is intractable.
- **Reframe as "validation"**: LLM agreed with PC's removals (0 FP), but this is circular — PC already had statistical justification.

## Impact

The negative result actually strengthens the paper:
1. F1 decomposition becomes more impactful: the bottleneck is not trivially fixable
2. Demonstrates limits of LLM domain knowledge for structural decisions
3. Confirms proposal's design choice to leave skeleton unmodified
