---
id: XN-021
title: "Skeleton refinement via LLM: definitive negative result"
date: 2026-03-11
dag_nodes: [I02]
tags: [negative-result, skeleton]
links:
  evidence_against: [I02]
  related_to: [XN-016]
---

# XN-021: Skeleton refinement via LLM — definitive negative

## Summary

Tested LLM-based skeleton refinement (recovering edges PC missed) on 6 benchmark networks. **0 true positives recovered across all networks.** The approach is fundamentally limited by (1) reachability — most missing edges are >2 hops apart, (2) LLM conservatism — the model lacks fine-grained domain knowledge to confidently assert ambiguous edges, and (3) proposal scope — the proposal explicitly excludes skeleton modification.

## Method

- Candidate pairs: nodes within 2 hops in PC skeleton but not directly connected
- Prompt: debiased (no anchoring to statistical test results)
- Voting: K=5 passes at varied temperatures (0.3–1.1), 60% threshold
- Model: Qwen3.5-27B non-thinking mode via RunPod

## Results

| Network   | Candidates | GT Missing | Reachable (2-hop) | TP Added | FP Added |
|-----------|-----------|------------|-------------------|----------|----------|
| Insurance | 85        | 10         | 4                 | 0        | 0        |
| Alarm     | 71        | 3          | 3                 | 0        | 0        |
| Sachs     | 14        | 0          | N/A (100% cov)    | N/A      | N/A      |
| Child     | 52        | 0          | N/A (100% cov)    | N/A      | N/A      |
| Asia      | 10        | 1          | 1                 | 0        | 0        |
| Hepar2    | 172       | 58         | TBD               | 0        | 9        |

## Root cause analysis

### 1. Reachability bottleneck
Of 10 GT-missing edges in Insurance, only 4 are within 2 hops. The remaining 6 are at distances 4-5:
- Accident--Antilock: distance 5
- AntiTheft--Theft: distance 5
- Theft--HomeBase: distance 5
- OtherCarCost--RuggedAuto: distance 4
- RuggedAuto--ThisCarDam: distance 4
- Accident--Mileage: distance 4

Expanding to 3+ hops would create hundreds of candidates with even lower base rates.

### 2. LLM conservatism on ambiguous edges
Even for reachable GT-missing edges, the LLM votes "no" or "uncertain":
- GoodStudent--SocioEcon: 1 yes, 3 no, 1 uncertain (GT edge exists)
- MakeModel--RiskAversion: 1 yes, 2 no, 2 uncertain (GT edge exists)
- RiskAversion--VehicleYear: 1 yes, 2 no, 2 uncertain (GT edge exists)
- CarValue--Theft: 0 yes, 2 no, 3 uncertain (GT edge exists)

These are genuinely ambiguous edges. A 27B model lacks the domain specificity to confidently assert them.

### 3. Prompt debiasing was necessary but insufficient
Original prompt ("A statistical independence test found NO direct edge") → all "no" (anchoring).
Debiased prompt → shifted some to "uncertain" but still 0 "yes" on GT-missing edges.

### 4. Literature alignment
"Mitigating Prior Errors" (2306.07032) classifies LLM-suggested edge additions as "irrelevant priors" or "indirect priors" — the types that cause cascading damage. The proposal itself says "The LLM does not alter the skeleton."

## Positive side finding
The LLM correctly rejected 81/85 non-GT candidates on Insurance (0 false positives with debiased prompt). However, this is circular — it's agreeing with PC's edge removals, which already had statistical justification.

## Hepar2 addendum (completed in background)
Hepar2 is the worst case: 172 candidates (largest network, 70 nodes), 58 GT-missing edges (skeleton coverage only 52.8%). The LLM added 9 edges — ALL false positives, 0 true positives. Precision dropped from 97.0% to 85.5% (-11.5%). This is the only network where the LLM actively hurt the skeleton. The aggressive candidate count (172) combined with the LLM's poor edge-existence judgment for medical domain variables makes this a clear worst case.

## Decision
Skeleton refinement vetoed across all 6/6 networks. The negative result strengthens the F1 decomposition contribution: it demonstrates that the skeleton bottleneck cannot be trivially fixed by LLM priors, making the diagnostic finding more impactful. Move to NCO validation, fair comparison, and robustness testing.
