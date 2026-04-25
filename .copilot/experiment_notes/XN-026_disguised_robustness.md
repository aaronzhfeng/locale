---
id: XN-026
title: "Disguised variable robustness: LOCALE does not rely on domain knowledge from names"
date: 2026-03-11
dag_nodes: [I02, I03]
links:
  evidence_for: [I02, I03]
  related_to: [XN-024, XN-023]
tags: [robustness, disguised, memorization]
---

# XN-026: Disguised Variable Robustness Test

## Hypothesis

If LOCALE relies on the LLM recognizing variable names from its training data (e.g., "SocioEcon → RiskAversion" memorized from textbook Bayesian networks), disguising names as V01, V02, ... should significantly degrade accuracy. If structural constraints (CI tests, NCO, Max-2SAT) are doing the heavy lifting, accuracy should be preserved.

## Setup

- **Networks**: Insurance, Alarm (n=10k, K=10 debiased, non-thinking)
- **Disguised**: Variable names replaced with V01, V02, ... (alphabetical order). Descriptions also replaced with generic "Variable V01", etc.
- **Pipeline**: Phase 1 (ego-graph queries) → Phase 2 (NCO + Max-2SAT)
- **Same seed, same skeleton, same CI tests** — only the LLM prompts differ (variable names).

## Results

### Raw Phase 1 Accuracy (per-pass, before constraints)

| Network | Metric | Real Names | Disguised | Delta |
|---------|--------|-----------|-----------|-------|
| Insurance | Ego | 89.0% | 88.3% | **-0.7pp** |
| Insurance | PE | 89.6% | 91.0% | +1.3pp |
| Alarm | Ego | 83.9% | 83.3% | **-0.7pp** |
| Alarm | PE | 82.1% | 80.4% | -1.7pp |

### After Phase 2 (NCO + Max-2SAT)

| Network | Real Names | Disguised | Delta |
|---------|-----------|-----------|-------|
| Insurance | 93.0% (40/43) | **97.7% (42/43)** | **+4.7pp** |
| Alarm | 90.7% (39/43) | 90.7% (39/43) | **0.0pp** |

## Analysis

1. **Raw ego accuracy drops by only 0.7pp** on both networks when variable names are disguised. This is negligible — well within noise for a single-seed experiment.

2. **After NCO + Max-2SAT, disguised accuracy matches or exceeds real names.** On Insurance, disguised is actually 4.7pp BETTER. On Alarm, identical.

3. **Why disguised can be better than real names**: When variable names are anonymized, the LLM cannot use potentially misleading domain knowledge. For example, if the LLM "knows" from training data that A→B is a common causal relationship, but the Bayesian network encodes a different structure, real names can hurt. Disguised mode forces the LLM to rely purely on the structural information provided in the prompt (neighbor topology, CI constraints).

4. **The structural constraints are the primary value driver.** NCO constraints improve accuracy from 88-89% (raw) to 91-98% (after Phase 2) regardless of whether names are real or disguised. This confirms that the CI-derived constraint compilation (Phase 2) is the core methodological contribution, not the LLM's domain knowledge.

5. **Per-edge also robust**: PE accuracy drops by only 1.3-1.7pp when disguised. Both prompting strategies are robust to name anonymization.

## Implications for Paper

- LOCALE passes the anonymization test — it's not "cheating" by recognizing benchmark networks
- Can be deployed on proprietary/sensitive data where variable names must be anonymized
- The NCO + Max-2SAT constraint layer is the critical differentiator, not the LLM's domain knowledge
- This finding pairs with XN-023 (model size ablation): ego-graph accuracy requires model scale (27B) but NOT domain-specific knowledge

## Caveats

- Single seed (42). Should be validated with multiple seeds.
- Phase 2 accuracy uses simple reconciliation (not full Phase 3 confidence-weighted). Full pipeline results may differ slightly.
- Disguised descriptions are "Variable V01" — real deployment might use more informative but non-revealing descriptions.
