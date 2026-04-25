---
id: XN-039
title: "ILS-CSL baseline: LLM-guided score-based learning across 7 networks"
date: 2026-04-05
dag_nodes: [E03]
links:
  evidence_for: [E03]
  related_to: [XN-038, XN-035]
tags: [baseline, ilscsl, llm, score-based]
---

# XN-039: ILS-CSL Baseline

## Setup

- ILS-CSL (Ban et al., 2023): iterative LLM-supervised causal structure learning
- Uses HC (Hill Climbing) variant — MINOBSx (their main algorithm) is a Linux binary, not available on macOS
- Same LLM as LOCALE/MosaCD: Qwen3.5-27B-FP8 via vLLM
- 7 networks (limited by ILS-CSL's variable description availability): Asia, Cancer, Child, Insurance, Alarm, Water, Mildew
- 4 seeds each (0, 1, 2, 42)
- n_samples matched to ILS-CSL defaults per network (250-8000 depending on network)

## Results

| Network | ILS-CSL F1 | LOCALE F1 | MosaCD F1 |
|---------|-----------|-----------|-----------|
| Asia | 0.800±0.231 | 0.900 | 0.967 |
| Cancer | 0.350±0.237 | 0.964 | 0.964 |
| Child | 0.829±0.075 | 0.882 | 0.871 |
| Insurance | 0.781±0.019 | 0.845 | 0.757 |
| Water | 0.534±0.025 | 0.579 | 0.569 |
| Mildew | 0.517±0.015 | 0.859 | 0.859 |
| Alarm | 0.891±0.043 | 0.841 | 0.801 |

## Key Findings

1. **LOCALE beats ILS-CSL on 5/7 networks.** ILS-CSL wins only on Alarm (0.891 vs 0.841) where its score-based approach with iterative refinement works well.

2. **ILS-CSL has high variance.** Asia std=0.231, Cancer std=0.237 — much less stable than LOCALE or MosaCD.

3. **ILS-CSL uses fewer LLM queries** (pairwise, one per edge per iteration) but the iterative HC re-runs are expensive.

4. **HC variant caveat.** ILS-CSL paper primarily reports MINOBSx results, which use exact/approximate optimal search. HC is a weaker variant. Our ILS-CSL numbers may underestimate their method's full capability.

5. **Different sample sizes.** ILS-CSL uses their default n per network (250-8000), not our standard n=10000. This matches their paper's protocol but means the comparison isn't perfectly controlled for data quantity.
