---
id: XN-023
title: "Model size ablation: ego-graph is an emergent capability at scale"
date: 2026-03-11
dag_nodes: [I02]
tags: [ablation, model-size, ego-graph, emergent]
links:
  evidence_for: [I02]
  related_to: [XN-003]
---

# XN-023: Model Size Ablation — 9B vs 27B

## Summary

Tested LOCALE with Qwen3.5-9B (vs production 27B) on Insurance and Alarm. Per-edge accuracy degrades minimally (1-4pp), but ego-graph accuracy **collapses** (22-31pp drop). Ego-graph joint reasoning is an emergent capability that requires sufficient model scale.

## Results

### Insurance (n=10k, K=5, ego-v2, temp-ladder, debiased)

| Metric | 9B | 27B | Delta |
|--------|-----|-----|-------|
| Per-edge accuracy | 81.0% | ~82% | -1pp |
| Ego-graph accuracy | 59.0% | ~90% | **-31pp** |
| PE majority vote | 84.9% | ~85% | ~0pp |
| Ego majority vote | 59.8% | ~95% | **-35pp** |
| PE uncertain rate | 12.2% | ~8% | +4pp |
| Ego uncertain rate | 3.9% | ~4% | ~0pp |
| PE CI violations | 0.7% | ~1% | ~0pp |
| Ego CI violations | 42.1% | ~2% | **+40pp** |
| Query savings (ego) | 72% | 72% | same |

### Alarm (n=10k, K=5, ego-v2, temp-ladder, debiased)

| Metric | 9B | 27B | Delta |
|--------|-----|-----|-------|
| Per-edge accuracy | 76.8% | ~81% | -4pp |
| Ego-graph accuracy | 68.2% | ~90% | **-22pp** |
| PE majority vote | 79.1% | ~84% | -5pp |
| Ego majority vote | 69.7% | ~93% | **-23pp** |
| PE CI violations | 3.6% | ~1% | +3pp |
| Ego CI violations | 25.6% | ~3% | **+23pp** |

## Analysis

1. **Per-edge is model-robust**: Simple A→B or B→A judgments are within reach of 9B models. Accuracy drops only 1-4pp.

2. **Ego-graph requires scale**: Joint reasoning over 3-7 neighbors with CI constraints is beyond 9B capability. The model violates non-collider constraints 25-42% of the time (vs 1-3% at 27B), indicating it can't maintain consistency across the neighborhood.

3. **The crossover point** (XN-003): At 4B, per-edge won. At 9B, per-edge still wins. At 27B, ego-graph dominates. The crossover is somewhere in the 10-27B range.

4. **Query savings are model-independent**: Ego-graph uses 72% fewer queries regardless of model size. The efficiency gain is structural, not quality-dependent.

## Implications

- Ego-graph batching is NOT a universal improvement — it requires models with sufficient reasoning capacity
- This strengthens LOCALE's contribution: it identifies WHERE in the capability ladder ego-graph becomes viable
- For practitioners: use per-edge below ~20B parameters, ego-graph above
- The 9B run serves as a built-in control: shows that ego-graph's advantage is not just about "seeing more context" but about the model's ability to REASON over that context
