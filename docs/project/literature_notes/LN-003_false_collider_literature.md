---
id: LN-003
title: "False collider dominance in CI testing: theoretically known (MosaCD Thm 5.5), operationally novel (NCO)"
date: 2026-03-11
dag_nodes: [I03]
links:
  evidence_for: [I03]
  related_to: [XN-022, XN-014, XN-015]
tags: [nco, false-collider, ci-testing, novelty]
---

# LN-003: False Collider Literature — Is NCO Known?

## Our Finding
XN-022 shows 97.9% of CI errors in PC-stable skeletons are false colliders (v-structures that CI claims exist but don't). At n>=5000, this is 100%. Removing collider constraints and keeping only non-collider constraints (NCO) dramatically improves orientation accuracy.

## What the Literature Says

### Known: CI tests have finite-sample errors
- **Colombo & Maathuis 2014** (PC-stable): order-independent variant reduces but doesn't eliminate CI errors.
- **Consistent separating sets** [Ramsey 2006, ICD]: address coherence of CI decisions across conditioning set sizes.
- **RFCI/lFCI**: acknowledge that finite-sample CI unreliability increases with conditioning set size.

### Known: collider detection is fragile
- **MosaCD paper**: explicitly notes that their seeding accuracy is much better than PC's (false-seed rates 4.8% vs 26.7%), implying PC's collider detection is known to be problematic.
- **Mitigating Prior Errors** [arXiv:2602.02279]: notes not all prior mistakes are equally damaging — implies error asymmetry is a concern in the community.

### KNOWN theoretically: false-collider dominance (MosaCD Theorem 5.5)
**UPDATE (literature-scout 2026-03-11)**: MosaCD (Lyu et al., arXiv:2509.23570) § 5.2 formally proves that under noisy CI testing, collider error rate always exceeds non-collider error rate by a combinatorial margin: R_ℓ^PC = (M/(M-ℓ))^2 > 1 for sparse graphs. Intuition: "There are more candidate subsets that do NOT contain Z than subsets that DO contain Z, so collider-first strategies have more opportunities to make a mistake." MosaCD's solution: non-collider-first strategy (probabilistic confidence-down propagation).

### What LOCALE adds beyond MosaCD's theory
- MosaCD uses **asymptotic analysis**; we provide **empirical validation across sample sizes** (n=500→50k), revealing the mechanism: 93-99% false-collider rate at n≤1k, 100% at n≥5k (CI test power dependence).
- MosaCD uses **probabilistic non-collider-first** strategy; we use **deterministic binary NCO** (drop ALL collider constraints from Max-2SAT). Simpler, more robust for dual-endpoint reconciliation.
- Our quantitative result: 944 errors across 6 networks × 7 sample sizes × 3 seeds, 97.9% false collider rate overall.

## Implications (revised)
1. **NCO is a novel operational implementation** — the error asymmetry is theoretically predicted (MosaCD), but our binary NCO constraint approach and sample-size curves are new.
2. **Method-agnostic**: NCO applies to any constraint-based method using CI-derived collider constraints, not just LOCALE.
3. **Practical recipe**: "drop collider constraints, keep non-collider constraints" is a simple, deployable insight for any PC-family pipeline.
4. **Caveat**: validated on 6 BNLearn networks only. Needs validation on larger/different graph families to claim full generality.

## Answered Question
The false-collider dominance is a consequence of PC's architecture (how it detects colliders from separating sets). MosaCD Theorem 5.5 proves this formally: there are combinatorially more candidate conditioning sets that exclude Z than include Z, so the "Z not in sepset(X,Y)" collider test has more chances to fire falsely. This is not a bug — it's a structural property of the PC algorithm family.
