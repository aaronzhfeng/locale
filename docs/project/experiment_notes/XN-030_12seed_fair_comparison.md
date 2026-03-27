---
id: XN-030
title: "12-seed fair comparison: LOCALE 2 significant wins, 1 significant loss (Holm-corrected)"
date: 2026-03-19
dag_nodes: [E03, E01, I02, I03]
links:
  evidence_for: [E03, E01]
  related_to: [XN-027, XN-029, XN-028]
tags: [multi-seed, comparison, mosacd, statistical-test, holm]
---

# XN-030: 12-Seed Fair Comparison (All at 4096 Context)

## Setup

- **Seeds**: 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 42 (12 seeds per condition)
- **Networks**: Insurance, Alarm, Sachs, Child, Asia
- **Both methods**: same Qwen3.5-27B-FP8, same PC-stable skeleton per seed, 4096 max context
- **LOCALE**: Phase 1 (ego K=10 debiased) → Phase 2 (NCO Max-2SAT) → Phase 3 (confidence reconciliation)
- **MosaCD**: Per-edge (5 reps × 2 orderings), shuffled debiasing, propagation
- **Statistical test**: paired t-test with Holm-Bonferroni correction (alpha=0.05)

## Results

| Network | LOCALE F1 | MosaCD F1 | Delta | t | p | d | Result |
|---------|-----------|-----------|-------|---|---|---|--------|
| Insurance | 0.848±0.014 | 0.757±0.087 | +9.1pp | 3.39 | 0.008 | 1.1 | **WIN** |
| Alarm | 0.842±0.066 | 0.801±0.049 | +4.0pp | 1.90 | 0.086 | 0.6 | WIN (ns) |
| Sachs | 0.861±0.040 | 0.557±0.067 | +30.4pp | 10.95 | <0.0001 | 3.3 | **WIN** |
| Child | 0.898±0.021 | 0.871±0.037 | +2.7pp | 2.13 | 0.059 | 0.6 | WIN (ns) |
| Asia | 0.824±0.054 | 0.952±0.031 | -12.7pp | -7.62 | <0.0001 | -2.3 | **LOSS** |

**Holm-corrected**: Sachs SIG, Asia SIG (loss), Insurance SIG, Child ns, Alarm ns

**Score: 2 significant wins + 2 directional wins + 1 significant loss**

## Key Observations

1. **Insurance is now significant** (was ns at 4 seeds). Power analysis predicted ~11 seeds (d=0.86). At 10 paired seeds, t=3.39, p=0.008. Confirmed.

2. **LOCALE has 6x lower variance** on Insurance (std 0.014 vs 0.087). Ego-graph voting is inherently more stable than shuffled per-edge debiasing.

3. **Sachs is the strongest win** (+30.4pp). MosaCD collapses to 0.557 on protein signaling. Per-edge prompts on small non-standard domains are unreliable.

4. **Asia is a clear, significant loss** (-12.7pp). On tiny networks (8 edges), per-edge with 10 queries/edge gives high confidence. Ego-graph adds noise when the ego subgraph IS the whole graph.

5. **Alarm and Child are directional but not Holm-significant.** Alarm p=0.086, Child p=0.059.

6. **Context sensitivity** (XN-029): MosaCD breaks at 2048 context (Insurance F1 drops 0.757→0.525). LOCALE is unaffected. Genuine prompt architecture advantage.

## Comparison with 4-Seed Results (XN-027)

| Network | 4-seed delta | 12-seed delta | Change |
|---------|-------------|---------------|--------|
| Insurance | +4.6pp (ns) | **+9.1pp (sig)** | Stronger, now significant |
| Alarm | +7.5pp (sig) | +4.0pp (ns) | Weaker, lost Holm significance |
| Sachs | +30.1pp (sig) | +30.4pp (sig) | Stable |
| Child | +2.4pp (ns) | +2.7pp (ns) | Stable |
| Asia | -6.7pp (ns) | **-12.7pp (sig)** | Larger loss, now significant |
