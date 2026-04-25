---
id: LN-001
title: "MosaCD: per-edge orientation with shuffled debiasing and propagation"
date: 2026-03-11
dag_nodes: [E01, I02, I03]
links:
  related_to: [XN-024, XN-016]
tags: [mosacd, baseline, comparison]
---

# LN-001: MosaCD — Primary Baseline

## Reference
arXiv:2509.23570. "Improving constraint-based discovery with robust propagation and reliable LLM priors."

## Key Claims
1. Per-edge LLM orientation with shuffled debiasing (5 reps x 2 orderings = 10 queries/edge)
2. 3-phase propagation: Meek R2 + CI-supervised + collider detection
3. Least-conflict orientation for remaining edges
4. Final vote-based orientation
5. Results: Insurance=87%, Alarm=93%, Hepar2=72% (with GPT-4o-mini, 128K context)

## Relevance to LOCALE
- **Primary methodological comparison**: LOCALE's ego-graph batching (K=10 per node) vs MosaCD's per-edge querying (10 per edge).
- **Same-model re-implementation** (XN-024): Our re-implementation using Qwen3.5-27B gives similar Insurance (86.3%) but lower Alarm (80.9%) — partly due to 4096-token context overflow on "full" template.
- **Query efficiency**: LOCALE needs ~O(nodes × K) queries, MosaCD needs ~O(edges × 10). For Insurance: 230 vs 430 (46% savings).
- **Context overflow vulnerability**: MosaCD's "full" template with chain CI context exceeds 4096 tokens for high-degree Alarm nodes. LOCALE's ego prompts are more compact.

## Key Differences from LOCALE
1. Per-edge vs ego-graph: MosaCD queries one edge at a time; LOCALE queries all edges around a node jointly.
2. No hard constraints: MosaCD uses soft voting + propagation; LOCALE uses hard NCO constraints + Max-2SAT.
3. Propagation-heavy: MosaCD relies on iterative propagation (3 phases); LOCALE's Max-2SAT resolves everything locally.
4. No public code: paper provides algorithm + prompt templates in appendix, enabling faithful re-implementation.
