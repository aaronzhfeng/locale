---
id: XN-008
title: "Prompt variant sensitivity analysis"
date: 2026-03-10
dag_nodes: [I02, I03]
links:
  evidence_against: [I03]
  related_to: [XN-005, XN-007]
---

# XN-008: Prompt Variant Sensitivity Analysis

## Context

Tested multiple prompt engineering approaches to improve orientation accuracy beyond v1 baseline. All on Qwen3.5-27B, disguised names, non-thinking.

## Variants Tested

### v2 Prompt (Structured CI Constraints)
Added explicit "MUST orient as" / "MUST NOT orient as" instructions for CI-derived constraints.

| Network | PE raw | Ego raw | PE maj | Ego maj |
|---------|--------|---------|--------|---------|
| Insurance | 94.7% | 90.5% | 100% | 89.5% |
| Alarm | 28.0% | 12.0% | 50.0% | 25.0% |

**Catastrophic on Alarm**: 85% ego uncertain rate. The rigid constraint language confused the model on the unfamiliar medical domain. Slightly hurt Insurance ego too.

**Verdict**: Do not use. Rigid constraint language is counterproductive.

### Contrastive PE Prompt
Forces model to argue both directions (Hypothesis A vs B) before deciding. Different parser needed (Final answer: A/B/C format).

| Network | PE raw | Ego raw | PE maj | Ego maj |
|---------|--------|---------|--------|---------|
| Insurance | 56.8% | 90.5% | 78.9% | 94.7% |
| Alarm | 56.0% | 75.0% | 70.0% | 75.0% |

**Hurts PE dramatically** (27% uncertain on Insurance). Helps ego on Alarm (+19pp delta in ego's favor). The ego advantage with contrastive is artificially inflated by PE degradation.

**Verdict**: Contrastive format harms PE more than it helps ego. Not useful.

### Temperature Ladder (T=[0.3, 0.5, 0.7, 0.9, 1.1])
Uses diverse temperatures across K=5 passes instead of fixed T=0.7.

| Network | PE raw | Ego raw | PE maj | Ego maj |
|---------|--------|---------|--------|---------|
| Insurance | 94.7% | 95.8% | 100% | 94.7% |

**PE majority vote reaches 100% on Insurance.** Slight ego improvement (+1.1pp raw). Temperature diversity helps PE more because each query is independent; ego queries already have internal diversity from multi-edge reasoning.

**Verdict**: Useful for PE. Does not change the ego narrative.

### Thinking Mode (Extended Reasoning)
Enables Qwen3.5's thinking chain before answering. MAX_TOKENS=1500 (insufficient for ego).

| Network | PE raw | Ego raw | PE maj | Ego maj |
|---------|--------|---------|--------|---------|
| Insurance | 90.5% | 41.1% | 100% | 63.2% |

**Thinking destroys ego (45% uncertain from token truncation).** Thinking tokens consume the output budget, leaving no room for multi-edge answers. PE benefits from thinking (100% majority). This is a fundamental asymmetry: ego needs more output tokens.

**Verdict**: Thinking mode is PE-only. Ego would need much larger max_tokens (and longer context) to benefit.

## Key Finding: Prompt Fragility

The method is highly sensitive to prompt engineering:
- v1 → ego wins on 3/4 networks
- v2 → ego collapses on Alarm (12% accuracy)
- Contrastive → PE collapses (56% accuracy)
- Thinking → ego collapses (41% accuracy)

Small prompt changes cause 30-50pp swings. This weakens the claim that ego-graph prompting is "fundamentally better" and suggests the contribution is more about "a specific prompting strategy that works" than a general principle.

## Implication for Paper

The v1 results are the method. The other variants belong in an ablation study showing sensitivity, not as method improvements. The paper should acknowledge prompt sensitivity as a limitation.
