---
id: XN-031
title: "Corrected 12-seed comparison: data seed bug fix + Asia alpha=0.10"
date: 2026-03-26
dag_nodes: [E03, A02, I11]
links:
  supersedes: [XN-030]
  evidence_for: [E01, E03]
  related_to: [XN-028, XN-029]
tags: [comparison, seed-fix, holm, multi-seed, alpha-tuning]
---

# XN-031: Corrected 12-Seed Comparison

## Context

XN-030 was invalidated by data seed bug (D-A02): LOCALE used fixed seed=42 data for all "seeds" due to Python default parameter binding. This re-run uses correctly varying data seeds. Asia uses alpha=0.10 (per XN-028).

## Setup

- 5 networks: Insurance (27n), Alarm (37n), Sachs (11n), Child (20n), Asia (8n)
- 12 seeds: 0-10 + 42
- Model: Qwen/Qwen3.5-27B-FP8, max_model_len=4096
- LOCALE: K=10 passes, debiased, all-nodes, NCO Max-2SAT, confidence reconciliation
- MosaCD: 5 reps × 2 orderings, shuffled debiasing, propagation
- Asia: alpha=0.10 (both methods). Others: alpha=0.05
- MosaCD results reused from XN-030 (correctly seeded; Insurance/Alarm/Sachs/Child unchanged)

## Results (Holm-Bonferroni corrected paired t-test)

| Network | Pairs | LOCALE F1 | MosaCD F1 | Delta | p-value | Holm | Cohen's d | Result |
|---------|-------|-----------|-----------|-------|---------|------|-----------|--------|
| Sachs | 11 | 0.865±0.044 | 0.557±0.063 | +30.7pp | <0.0001 | SIG | 5.61 | **WIN** |
| Insurance | 10 | 0.845±0.019 | 0.757±0.083 | +8.8pp | 0.0125 | SIG | 1.04 | **WIN** |
| Alarm | 11 | 0.841±0.070 | 0.801±0.047 | +3.9pp | 0.1394 | ns | 0.51 | win (dir) |
| Child | 11 | 0.882±0.030 | 0.871±0.035 | +1.1pp | 0.5776 | ns | 0.18 | win (dir) |
| Asia | 12 | 0.900±0.100 | 0.967±0.033 | -6.7pp | 0.0069 | SIG | -1.00 | **LOSS** |

**Score: 2 SIG wins + 2 directional wins + 1 SIG loss (Holm-corrected)**

## Variance Analysis

| Network | LOCALE std | MosaCD std | Ratio |
|---------|-----------|-----------|-------|
| Insurance | 0.019 | 0.083 | 0.23x (LOCALE more stable) |
| Sachs | 0.044 | 0.063 | 0.70x (LOCALE more stable) |
| Child | 0.030 | 0.035 | 0.86x (similar) |
| Alarm | 0.070 | 0.047 | 1.48x (MosaCD more stable) |
| Asia | 0.100 | 0.033 | 3.00x (MosaCD more stable) |

LOCALE is more stable on Insurance (4.4x) and Sachs (1.4x). MosaCD is more stable on Alarm (1.5x) and Asia (3x). Child is similar.

## Comparison with XN-030 (buggy results)

| Network | Old Delta | New Delta | Change |
|---------|-----------|-----------|--------|
| Insurance | +9.1pp SIG | +8.8pp SIG | Similar |
| Sachs | +30.4pp SIG | +30.7pp SIG | Similar |
| Alarm | +4.0pp ns | +3.9pp ns | Similar |
| Child | +2.7pp ns | +1.1pp ns | Weakened |
| Asia | -12.7pp SIG | -6.7pp SIG | Improved (alpha=0.10) |

Headline unchanged (2W/2D/1L). Insurance and Sachs wins are robust to the fix. Child weakened from 2.7pp to 1.1pp. Asia loss halved. The "6x more stable" claim from XN-030 was an artifact — actual stability advantage is network-dependent.

## Key Findings

1. **Bug fix validates the comparison.** Insurance and Sachs wins are real and significant despite LOCALE now facing data variance. The ego-graph advantage on these networks is genuine.

2. **Stability is network-dependent, not universal.** LOCALE is more stable on Insurance/Sachs (fewer queries, ego-graph voting smooths noise). MosaCD is more stable on Alarm/Asia (per-edge queries more robust on large/small networks). The old "6x more stable" claim was an artifact of fixed data.

3. **Asia loss is structural.** On 7-edge seeds (s0,1,4,5,7,9), LOCALE gets 6/7 correct (1 systematic error: either->tub reversed). The error is 100% consistent across all 7-edge seeds. Root cause: `tub` has degree 1 in the 7-edge skeleton → only `either`'s ego-graph covers this edge → single-endpoint coverage with no reconciliation opportunity. MosaCD gets 7/7 on these seeds because per-edge prompting doesn't depend on node degree.

4. **Alpha=0.10 helps Asia but doesn't eliminate the loss.** LOCALE improved from 0.824 (old, alpha=0.05, but wrong seed) to 0.900 (corrected, alpha=0.10). MosaCD went from 0.952 to 0.967. The gap narrowed from -12.7pp to -6.7pp.

5. **Child is essentially a tie.** Delta of 1.1pp with p=0.58 — no meaningful difference.

## Broken Symlinks Note

Seed 42 directories for all networks were broken symlinks from a previous Lightning Studio environment. These were discovered and removed during the re-run. Insurance and MosaCD s42 were also affected — Insurance has 10 paired comparisons (s0-s10, no s42 for MosaCD).
