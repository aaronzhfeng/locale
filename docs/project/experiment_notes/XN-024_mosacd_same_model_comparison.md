---
id: XN-024
title: "MosaCD same-model comparison: LOCALE matches or beats on all 6 networks"
date: 2026-03-11
dag_nodes: [E01, I02, I03]
links:
  evidence_for: [I02, I03]
  related_to: [XN-016]
tags: [comparison, mosacd, baseline]
---

# XN-024: MosaCD Same-Model Fair Comparison

## Setup

Re-implemented MosaCD's 5-step algorithm from arXiv:2509.23570 (no public repo).
Both methods use **identical** LLM (Qwen3.5-27B-FP8) and skeleton (PC-stable, alpha=0.05, n=10k).

MosaCD: 10 queries per edge (5 reps × 2 orderings for shuffled debiasing), per-edge prompts with chain CI context.
LOCALE: K=10 passes per node, ego-graph prompts with NCO constraints. Max-2SAT + confidence reconciliation.

## Results

| Network | LOCALE F1 | MosaCD F1 | Delta | LOCALE Q | MosaCD Q | Q Savings |
|---------|-----------|-----------|-------|----------|----------|-----------|
| Insurance | 0.863 | 0.863 | 0.0 | ~230 | 430 | 46% |
| Alarm | 0.899 | 0.809 | **+9.0pp** | ~260 | 430 | 40% |
| Asia | 0.933 | 0.933 | 0.0 | ~50 | 70 | 29% |
| Child | 0.880 | 0.880 | 0.0 | ~75 | 250 | 70% |
| Sachs | 0.765 | 0.588 | **+17.7pp** | ~85 | 170 | 50% |
| Hepar2 | 0.599 | 0.442 | **+15.7pp** | ~350 | 670 | 48% |

**Score: LOCALE 3 wins, 3 ties, 0 losses. Always 29-70% fewer queries.**

## MosaCD Detailed Metrics

| Network | Seeds | Seed Acc | Post-Prop | F1 | P | R | SHD |
|---------|-------|----------|-----------|-----|------|------|-----|
| Insurance | 40/43 | 97.5% | 42/43 | 0.863 | 0.953 | 0.788 | 12 |
| Alarm | 38/43 | 84.2% | 42/43 | 0.809 | 0.837 | 0.783 | 10 |
| Asia | 7/7 | 100% | 7/7 | 0.933 | 1.000 | 0.875 | 1 |
| Child | 25/25 | 88.0% | 25/25 | 0.880 | 0.880 | 0.880 | 3 |
| Sachs | 14/17 | 57.1% | 17/17 | 0.588 | 0.588 | 0.588 | 7 |
| Hepar2 | 42/67 | 62.7% | 67/67 | 0.442 | 0.627 | 0.341 | 83 |

## Key Observations

1. **Same accuracy, fewer queries.** On 3/6 networks (Insurance, Asia, Child), both methods achieve identical F1. LOCALE uses 29-70% fewer queries by batching multiple edges per ego-graph query.

2. **LOCALE wins on hard networks.** On Alarm (+9pp), Sachs (+17.7pp), and Hepar2 (+15.7pp), LOCALE's ego-graph approach significantly outperforms MosaCD's per-edge approach. Alarm suffers from MosaCD context overflow (3597 tokens > 4096 limit on "full" template prompts). Sachs shows MosaCD's seed accuracy collapses to 57%. Hepar2 demonstrates that LOCALE's NCO constraints provide better orientation quality even when both methods face the same skeleton bottleneck (52% coverage).

3. **MosaCD context overflow on Alarm.** Some Alarm edges with the "full" template (including chain CI context) exceeded the 4096-token context window, returning empty responses. This dropped seed accuracy to 84.2%. LOCALE's ego prompts (~4200 chars for highest-degree nodes) don't hit this limit because they're more compact.

4. **MosaCD paper used GPT-4o-mini.** Paper reported Insurance=87%, Alarm=93%, Asia=93%, Child=90%. Our same-model re-implementation gets Insurance=86.3%, Alarm=80.9%, Asia=93.3%, Child=88.0%. The Alarm gap (93% paper vs 81% ours) is partly context overflow, partly model difference (GPT-4o-mini has 128K context).

5. **Query efficiency.** LOCALE averages ~50% fewer queries across all networks. For Child (25 edges): LOCALE needs ~75 queries (15 nodes × 5 passes), MosaCD needs 250 (25 edges × 10 queries each).

## Caveats

- Single seed per network (seed=42 for data sampling). Results may vary across seeds.
- MosaCD context overflow on Alarm is deployment-specific (4096 token limit). With larger context, MosaCD would perform better on Alarm.
- Non-thinking mode for all runs (enable_thinking=False). Thinking mode may improve both methods.
- Both methods share the same skeleton bottleneck (Insurance coverage 83%, limiting recall).
