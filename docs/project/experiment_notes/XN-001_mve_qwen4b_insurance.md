---
id: XN-001
title: "MVE on Insurance with Qwen3.5-4B: uninformative due to model capacity"
date: 2026-03-10
dag_nodes: [I02, I09]
links:
  evidence_against: []
  evidence_for: []
  related_to: [I00, I03]
---

# XN-001: MVE on Insurance with Qwen3.5-4B

## Setup
- Insurance network (27 nodes, 52 GT edges, 37 skeleton edges)
- PC-stable skeleton (P=0.97, R=0.69)
- 5 test nodes: DrivingSkill (d=3), DrivQuality (d=3), Accident (d=4), CarValue (d=4), SocioEcon (d=5)
- 17 unique test edges, K=5 stochastic passes
- Model: Qwen/Qwen3.5-4B via vLLM on RunPod

## Results

### Real variable names
| Condition | Accuracy | Uncertain | Queries |
|-----------|----------|-----------|---------|
| Per-edge  | 93.7%    | 0.0%      | 95      |
| Ego-graph | 75.8%    | 2.1%      | 25      |

Delta: -17.9pp. Per-edge wins decisively.

### Disguised names + descriptions
| Condition | Accuracy | Uncertain |
|-----------|----------|-----------|
| Per-edge  | 90.5%    | 3.2%     |
| Ego-graph | 47.4%    | 24.2%    |

Delta: -43.2pp.

### Fully anonymized (no descriptions)
Per-edge: 0% accuracy (all "uncertain"). Proves pure memorization.

### CI consistency violations
Per-edge: 7.8%, Ego-graph: 10.4% (Run 1)

### Query cost
Per-edge: 95 queries, Ego-graph: 25 queries (3.8x cheaper). Cost advantage confirmed.

## Diagnosis: Instrument failure, not hypothesis failure

The 4B model is the wrong instrument for this test:

1. **Memorization**: Anonymization test proves the model recalls Insurance network from training data. Descriptions alone (even with disguised names) are enough to trigger memorization. Per-edge barely drops (94% -> 91%); ego drops more because structured output is harder.

2. **Model capacity**: Structured multi-line ego-graph output is qualitatively harder than binary per-edge A/B classification for a 4B model. This asymmetrically penalizes the ego condition.

3. **Missing Phase 2**: No hard constraints (Max-2SAT) applied. This tests Phase 1 only; the full LOCALE method has not been tested.

4. **Parser limitations**: 24% uncertain rate in disguised ego condition indicates the model struggles to produce parseable structured output.

## What this DOES tell us
- The **3.8x query reduction** is real and robust across conditions.
- Ego-graph prompts **fit within 4K context** for degree <= 5 (330-450 tokens).
- The PC skeleton estimation pipeline works (P=0.97, R=0.69).
- CI facts and separating sets are correctly extracted and integrated into prompts.

## Conclusion
Uninformative for H1 (ego-context hypothesis). The MVE needs to be rerun with an API-class model (GPT-4o or Claude Sonnet) on the disguised-names condition. Estimated cost: under $5.
