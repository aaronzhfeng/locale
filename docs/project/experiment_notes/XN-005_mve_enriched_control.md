---
id: XN-005
title: "Enriched per-edge control (E1): joint orientation wins on hard domains"
date: 2026-03-10
dag_nodes: [I02, I03]
links:
  evidence_for: [I02]
  evidence_against: []
  related_to: [I00, I09]
  derived_from: [XN-003, XN-004]
---

# XN-005: Enriched Per-Edge Control (E1) — Two Networks

## Setup
- Condition C (enriched per-edge): same neighborhood context + CI facts as ego prompt, but asks about ONE edge at a time. Same query count as vanilla PE.
- Model: Qwen/Qwen3.5-27B-FP8, non-thinking, disguised names, K=5 passes

## Results

### Insurance (familiar domain)
| Condition | Accuracy | Uncertain | CI Violations | Queries |
|-----------|----------|-----------|---------------|---------|
| A: Vanilla PE | 93.7% | 1.1% | 5.5% | 95 |
| B: Ego-graph | 94.7% | 0.0% | 0.0% | 25 |
| C: Enriched PE | 96.8% | 3.2% | — | 95 |

Enriched PE > Ego > Vanilla PE. Context helps; one-at-a-time with context is slightly better than joint.

### Alarm (unfamiliar medical domain)
| Condition | Accuracy | Uncertain | CI Violations | Queries |
|-----------|----------|-----------|---------------|---------|
| A: Vanilla PE | 77.0% | 1.0% | 1.7% | 100 |
| B: Ego-graph | 80.0% | 0.0% | 0.0% | 25 |
| C: Enriched PE | 70.0% | 0.0% | 5.8% | 100 |

**Ego > Vanilla PE > Enriched PE.** Joint orientation decisively wins (+10pp over enriched). Enriched PE actually *hurts* (-7pp vs vanilla).

### Per-node breakdown (Alarm)
| Node | Degree | Vanilla PE | Ego | Enriched PE | Ego-Enriched |
|------|--------|-----------|-----|-------------|-------------|
| VENTLUNG | 5 | 92% | 96% | 84% | +12pp |
| CATECHOL | 2 | 40% | 20% | 50% | -30pp |
| HR | 4 | 80% | 100% | 85% | +15pp |
| LVEDVOLUME | 4 | 85% | 75% | 60% | +15pp |
| VENTALV | 5 | 68% | 76% | 60% | +16pp |

### Majority vote (Alarm)
| Condition | Accuracy |
|-----------|----------|
| Vanilla PE | 75.0% (15/20) |
| Ego-graph | 80.0% (16/20) |
| Enriched PE | 65.0% (13/20) |

## Key Findings

1. **Domain familiarity is the moderator.** On Insurance (familiar), enriched PE slightly wins because the model has strong domain priors and can orient edges individually with context. On Alarm (unfamiliar), the model needs joint structural reasoning — it can't orient edges correctly one at a time even with full context.

2. **Enriched PE can hurt.** On Alarm, enriched PE (70%) is worse than vanilla PE (77%). The extra context confuses the model when it lacks domain knowledge — it sees neighborhood info but can't integrate it properly one edge at a time. Joint orientation (ego) handles this better.

3. **Ego CI adherence is universal.** Ego achieves 0% CI violations on both networks. Enriched PE has 5.8% violations on Alarm (worse than vanilla PE's 1.7%). Joint orientation enforces structural consistency; one-at-a-time doesn't.

4. **CATECHOL (d=2) confirms minimum degree requirement.** Ego fails at d=2 regardless of domain. Design rule: ego only for d>=3.

## Cross-Network Summary

| Metric | Insurance (familiar) | Alarm (unfamiliar) |
|--------|---------------------|-------------------|
| Ego vs Enriched PE | -2.1pp (enriched wins) | +10.0pp (ego wins) |
| Ego vs Vanilla PE | +1.1pp | +3.0pp |
| Ego CI violations | 0% | 0% |
| Enriched PE CI violations | — | 5.8% |
| Ego majority vote | 94.7% | 80.0% |
| Enriched PE majority vote | 94.7% | 65.0% |

## Revised Narrative

The ego advantage is NOT just about cost. On domains where the LLM has weaker priors:
- Joint orientation genuinely helps (+10pp on Alarm)
- One-at-a-time with context can hurt (-7pp enriched vs vanilla on Alarm)
- Structural consistency (0% CI violations) is a real ego advantage

The contribution is: **ego-graph prompting provides joint structural reasoning that is especially valuable when domain priors are weak, while maintaining 4x query efficiency.**

-> DAG: I02, I03
-> Evidence: XN-005
-> Decision: Ego advantage is about joint orientation on hard domains + cost; narrative reframed
