---
id: LN-007
title: "Prior error taxonomy and quasi-circles: framing NCO as error mitigation"
date: 2026-03-24
dag_nodes: ["I03"]
links:
  - target: LN-003
    type: related_to
  - target: XN-022
    type: evidence_for
tags: ["prior-errors", "nco", "quasi-circles", "error-mitigation", "framing"]
---

# LN-007: Prior Error Taxonomy — Connecting NCO to Error Mitigation Literature

## Reference
Chen, Ban, Wang, Lyu & Chen, arXiv:2306.07032 (IEEE Trans., 2023). "Mitigating Prior Errors in Causal Structure Learning: Towards LLM driven Prior Knowledge."

## Core Contribution
Classifies LLM-derived prior errors into three types:
1. **Order-consistent**: edge exists in ground truth, direction matches (correct prior)
2. **Order-reversed**: edge exists but direction is wrong (most damaging)
3. **Irrelevant**: edge does not exist in ground truth (adds at most 1 SHD)

Key finding: **only order-reversed errors** create "quasi-circles" (acyclic closed structures) and cause cascading SHD increases. The paper proposes a post-hoc quasi-circle detection strategy that removes ~60% of prior errors while retaining 90% of correct priors.

## Connection to LOCALE's NCO

### LOCALE's NCO as error-type-specific mitigation
LOCALE's false collider problem (97.9% of CI errors are false colliders, XN-022) maps onto this taxonomy:
- **False colliders from CI tests** are analogous to "order-reversed" errors applied to v-structures -- the CI test claims a collider exists where it doesn't, which is a structural error that propagates
- **NCO (Non-Collider Only)** is a radical error mitigation strategy: instead of trying to detect and remove bad collider constraints, LOCALE drops ALL collider constraints and keeps only non-collider constraints

### Theoretical grounding
Chen et al.'s framework provides additional theoretical support for NCO:
- Their proof that order-reversed errors propagate more damage than irrelevant errors aligns with MosaCD's Theorem 5.5 (false colliders are combinatorially more common)
- NCO's strategy of dropping all collider constraints is more aggressive than Chen et al.'s post-hoc correction, but justified by the extreme false-collider rate (97.9%)

### Difference in scope
Chen et al. address LLM prior errors (edge-level). LOCALE's NCO addresses CI test errors (constraint-level). The error taxonomy is applicable to both settings. A reviewer might ask: "could LOCALE use Chen et al.'s quasi-circle detection instead of NCO?" Answer: NCO operates upstream (before orientation) while quasi-circles are detected post-hoc. NCO prevents damage; quasi-circles repair it.

## For the Paper
- Cite in related work as prior art on LLM prior error taxonomy
- Use to frame NCO: "Chen et al. show order-reversed errors are most damaging; we show CI-derived collider constraints are the causal-discovery analogue, and NCO eliminates them preemptively"
- Note the 60% error removal / 90% correct retention as a comparison point for NCO's effectiveness
