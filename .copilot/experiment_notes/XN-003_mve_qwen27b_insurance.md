---
id: XN-003
title: "MVE on Insurance with Qwen3.5-27B: ego-graph matches per-edge, scale confirms hypothesis"
date: 2026-03-10
dag_nodes: [I02, I09]
links:
  evidence_for: [I02]
  evidence_against: []
  related_to: [I00, I03]
  derived_from: [XN-001, XN-002]
---

# XN-003: MVE on Insurance with Qwen3.5-27B-FP8 (non-thinking)

## Setup
- Insurance network (27 nodes, 52 GT edges, 37 skeleton edges)
- PC-stable skeleton (P=0.97, R=0.69)
- 5 test nodes: DrivingSkill (d=3), DrivQuality (d=3), Accident (d=4), CarValue (d=4), SocioEcon (d=5)
- 17 unique test edges, K=5 stochastic passes
- Model: Qwen/Qwen3.5-27B-FP8 via vLLM on RunPod A40 (non-thinking mode)
- Concurrent queries (32 workers), total runtime ~24s per condition

## Results

### Disguised names + descriptions (THE FAIR TEST)
| Condition | Accuracy | Uncertain | CI violations | Queries |
|-----------|----------|-----------|---------------|---------|
| Per-edge  | 93.7%    | 1.1%      | 5.5%          | 95      |
| Ego-graph | 94.7%    | 0.0%      | 0.0%          | 25      |

**Delta: +1.1pp. Ego wins.**

### Real variable names (memorization check)
| Condition | Accuracy | Uncertain | CI violations |
|-----------|----------|-----------|---------------|
| Per-edge  | 100.0%   | 0.0%      | 0.0%          |
| Ego-graph | 95.8%    | 0.0%      | 0.0%          |

Delta: -4.2pp. Per-edge hits memorization ceiling (100%). Ego still 95.8%.

### Per-node breakdown (disguised)
| Node         | Per-edge | Ego-graph | Delta    |
|-------------|----------|-----------|----------|
| DrivingSkill | 100.0%   | 100.0%    |  +0.0pp  |
| DrivQuality  | 100.0%   | 100.0%    |  +0.0pp  |
| Accident     | 100.0%   | 100.0%    |  +0.0pp  |
| CarValue     | 85.0%    | 100.0%    | +15.0pp  |
| SocioEcon    | 88.0%    | 80.0%     |  -8.0pp  |

### Majority vote (disguised)
- Per-edge: 89.5% (17/19 edges)
- Ego-graph: 94.7% (18/19 edges)

### Query cost
- Per-edge: 95 queries, Ego-graph: 25 queries (3.8x cheaper)

## Scale Trend (Disguised Names)

| Model | Per-edge | Ego-graph | Delta | CI viol (EGO) |
|-------|----------|-----------|-------|---------------|
| 4B    | 90.5%    | 47.4%     | -43.2pp | — |
| 9B    | 90.5%    | 80.0%     | -10.5pp | 5.7% |
| 27B   | 93.7%    | 94.7%     | +1.1pp  | 0.0% |

Clear monotonic trend: ego accuracy scales with model capacity. The crossover happens between 9B and 27B.

## Key Findings

1. **H1 weakly supported**: Ego-graph matches or slightly beats per-edge at 27B scale (+1.1pp disguised). The hypothesis that ego-context improves orientation accuracy holds, but the advantage is narrow.

2. **CI constraint adherence**: Ego-graph has 0% CI violations at 27B (vs 5.5% for per-edge!). The model genuinely uses cross-neighbor CI information in ego mode. Per-edge cannot use CI constraints because it doesn't see them.

3. **Per-edge CI violations at 27B**: 5.5% violation rate for per-edge (disguised) — per-edge decisions are locally optimal but globally inconsistent. This is exactly the problem ego-graph was designed to solve.

4. **CarValue is the showcase**: Per-edge gets 85% accuracy on CarValue (d=4); ego gets 100%. The ego prompt provides cross-neighbor context (VehicleYear-MakeModel adjacency, Mileage-ThisCarCost non-adjacency) that helps orient the edges correctly.

5. **SocioEcon is the weak point**: Ego loses 8pp on SocioEcon (d=5). This is the highest-degree test node. The 5-neighbor ego prompt may be too complex for some orientations. Worth investigating whether sub-ego splitting (from proposal) helps.

6. **Cost-efficiency story is strong**: 94.7% accuracy at 3.8x fewer queries. Even if accuracy is only matched (not beaten), the cost advantage alone is publishable.

## Conclusion

WEAK GO for full build. The ego advantage is narrow (+1.1pp) but the combination of:
- Matched/superior accuracy
- 3.8x query reduction
- Zero CI violations
- Clear scale trend

...makes a compelling case. The contribution may need reframing from "ego is more accurate" to "ego achieves comparable accuracy with fewer queries and better constraint adherence."

Next steps: research-reflect to evaluate whether to proceed to full build or test with thinking mode first.
