---
id: XN-004
title: "MVE on Alarm with Qwen3.5-27B: ego and per-edge tied, majority-vote ego wins"
date: 2026-03-10
dag_nodes: [I02, I09]
links:
  evidence_for: []
  evidence_against: []
  related_to: [I00, I03]
  derived_from: [XN-003]
---

# XN-004: MVE on Alarm with Qwen3.5-27B-FP8 (non-thinking, disguised)

## Setup
- Alarm network (37 nodes, 46 GT edges, 43 skeleton edges)
- PC-stable skeleton
- 5 test nodes: VENTLUNG (d=5), CATECHOL (d=2), HR (d=4), LVEDVOLUME (d=4), VENTALV (d=5)
- 19 unique test edges (1 more than Insurance's 17), K=5 stochastic passes
- Model: Qwen/Qwen3.5-27B-FP8, non-thinking, disguised names, 32 concurrent workers

## Results

### Raw accuracy (disguised)
| Condition | Accuracy | Uncertain | CI violations | Queries |
|-----------|----------|-----------|---------------|---------|
| Per-edge  | 74.0%    | 0.0%      | 4.2%          | 100     |
| Ego-graph | 72.0%    | 0.0%      | 4.2%          | 25      |

Delta: -2.0pp. Essentially tied.

### Majority vote
| Condition | Accuracy |
|-----------|----------|
| Per-edge  | 75.0% (15/20) |
| Ego-graph | 80.0% (16/20) |

**Ego wins on majority vote by 5pp.**

### Per-node breakdown
| Node       | Degree | Per-edge | Ego-graph | Delta    |
|-----------|--------|----------|-----------|----------|
| VENTLUNG   | 5      | 100.0%   | 80.0%     | -20.0pp  |
| CATECHOL   | 2      | 40.0%    | 0.0%      | -40.0pp  |
| HR         | 4      | 65.0%    | 95.0%     | +30.0pp  |
| LVEDVOLUME | 4      | 75.0%    | 70.0%     | -5.0pp   |
| VENTALV    | 5      | 68.0%    | 76.0%     | +8.0pp   |

## Key Findings

1. **CATECHOL (d=2) tanks ego to 0%**: With only 2 neighbors and no cross-neighbor relationships, the ego prompt provides no structural advantage. The model consistently misorirants both edges in ego mode. This is a design insight: ego-graph should not be used for d<=2 nodes.

2. **HR (d=4) showcases ego at +30pp**: HR has 4 children (HRBP, HREKG, HRSAT, CO). The ego prompt helps the model see that HR is the common cause of multiple monitor readings. Per-edge cannot infer this.

3. **Alarm is harder than Insurance**: Overall accuracy dropped from ~94% (Insurance) to ~73% (Alarm). This is expected — Alarm has more confusing medical variables and the model has less domain knowledge about ICU monitoring than about car insurance.

4. **Majority vote favors ego**: Despite per-edge winning on raw accuracy (-2pp), ego wins on majority vote (+5pp). This suggests ego's errors are more stochastic (different per pass) while per-edge errors are more systematic (same edge wrong every time).

## Degree-Dependent Pattern (Cross-Network)

Combining Insurance (XN-003) and Alarm (XN-004) per-node results at 27B disguised:

| Node (Network) | Degree | PE Acc | EGO Acc | Delta |
|----------------|--------|--------|---------|-------|
| CATECHOL (Alarm) | 2 | 40% | 0% | -40pp |
| DrivingSkill (Ins) | 3 | 100% | 100% | 0 |
| DrivQuality (Ins) | 3 | 93% | 80% | -13pp |
| Accident (Ins) | 4 | 100% | 100% | 0 |
| CarValue (Ins) | 4 | 85% | 100% | +15pp |
| HR (Alarm) | 4 | 65% | 95% | +30pp |
| LVEDVOLUME (Alarm) | 4 | 75% | 70% | -5pp |
| VENTALV (Alarm) | 5 | 68% | 76% | +8pp |
| SocioEcon (Ins) | 5 | 88% | 80% | -8pp |
| VENTLUNG (Alarm) | 5 | 100% | 80% | -20pp |

No clear monotonic degree→delta relationship, but d=2 is clearly bad for ego, and the best ego showcases (CarValue +15pp, HR +30pp) are at d=4.

## Conclusion

Alarm replicates the Insurance pattern in aggregate: ego and per-edge are roughly tied on accuracy, ego wins on majority vote, 4x cheaper. The CATECHOL failure reveals a minimum-degree requirement for ego-graph prompting.
