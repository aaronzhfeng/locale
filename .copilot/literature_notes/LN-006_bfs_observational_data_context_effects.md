---
id: LN-006
title: "BFS prompting with observational data: context structure improves LLM causal reasoning"
date: 2026-03-24
dag_nodes: ["I02", "E01"]
links:
  - target: LN-002
    type: related_to
  - target: XN-029
    type: related_to
tags: ["bfs-prompting", "context-effects", "observational-data", "supporting"]
---

# LN-006: BFS Prompting with Observational Data

## Reference
Susanti & Farber, arXiv:2504.10936 (Workshop on Causal Neuro-symbolic AI, June 2025). "Can LLMs Leverage Observational Data? Towards Data-Driven Causal Discovery with LLMs."

## Key Finding
BFS prompting (which provides neighborhood context: current graph state, already-discovered edges, multi-variable scope) consistently outperforms pairwise prompting for LLM-based causal discovery, with up to 0.32 F1 improvement (0.58 vs 0.90 on Asia). Adding observational data samples to prompts further improves performance (up to +0.11 F1).

## Why This Matters for LOCALE

### Supports ego-graph thesis (I02)
The BFS-pairwise gap is direct evidence that **LLMs reason better about causality with more local context** than in isolation. The authors explicitly note: "leveraging global context awareness -- multi-variable interactions rather than variable pairs in isolation -- enhances causal inference." This is exactly LOCALE's thesis: ego-graph prompts provide richer context than per-edge queries.

### Context efficiency parallel (E01, XN-029)
The authors note BFS prompting "includes the entire query history, which can lead to excessive prompt length and may be infeasible due to the LLM's token limitations." This echoes LOCALE's context sensitivity finding (XN-029): MosaCD's per-edge prompts with chain CI context can overflow at 4096 tokens for high-degree nodes, while LOCALE's ego-graph prompts are inherently bounded by node degree.

### Limitations as contrast point
The paper only evaluates on tiny networks (Asia=8 vars, Cancer=5 vars, Survey=6 vars) with GPT-4. The BFS approach is essentially a global construction method that queries the entire variable set. LOCALE's ego-graph is a middle ground: richer than pairwise (like BFS) but bounded in scope (unlike BFS which grows with query history).

## For the Paper
- Cite as supporting evidence that structured neighborhood context improves LLM causal judgment
- Use to motivate ego-graph as the sweet spot: richer than per-edge but bounded unlike BFS
- Note that BFS's token-length concern validates LOCALE's context-efficient design
