---
id: LN-005
title: "SNOE: Sequential nonlinear edge orientation as methodological parallel to LOCALE"
date: 2026-03-24
dag_nodes: ["I02", "I03", "I05"]
links:
  - target: LN-001
    type: related_to
  - target: XN-022
    type: related_to
tags: ["edge-orientation", "cpdag", "sequential", "non-llm-baseline", "snoe"]
---

# LN-005: SNOE — Sequential Nonlinear Orientation of Edges

## Reference
Huang & Zhou, arXiv:2506.05590 (June 2025). "Nonlinear Causal Discovery through a Sequential Edge Orientation Approach." JMLR.

## Core Idea
SNOE starts from a CPDAG (exactly the same starting point as LOCALE) and sequentially orients undirected edges using a pairwise additive noise model (PANM) criterion. It ranks edges by how well they satisfy the PANM condition, orients the best candidate via a likelihood ratio test, applies Meek rules after each orientation, and repeats.

## Why This Matters for LOCALE

### Structural parallel
SNOE and LOCALE solve the **same abstract problem**: orient undirected edges in a CPDAG to recover the true DAG. The key differences:
- **SNOE**: uses statistical tests on observational data (nonlinear regression residuals)
- **LOCALE**: uses LLM judgments on variable metadata (ego-graph prompts)
Both use sequential/local orientation + Meek propagation. Both exploit the PDAG structure to determine orientation order.

### Potential comparison baseline
SNOE is a strong non-LLM orientation method. If LOCALE targets CLeaR/UAI, reviewers may ask: "why not just use SNOE on the data?" Answer: SNOE requires access to raw observational data and assumes additive noise models (restrictive for categorical/discrete BNLearn networks). LOCALE uses metadata only, complementing data-driven methods.

### Methodological insights
1. **Edge ranking matters**: SNOE's ranking by PANM adherence is analogous to LOCALE's confidence-weighted orientation order. Both recognize that orienting "easy" edges first and propagating constraints is better than random order.
2. **Sequential + Meek**: SNOE proves that sequential orientation + Meek closure is consistent in the large-sample limit under restricted ANMs. LOCALE's Phase 5 (Meek closure) is similar in spirit but found to be a no-op in practice (XN-018), because Max-2SAT already resolves most edges.
3. **Local evaluation**: SNOE evaluates edges using only the sub-DAG on candidate nodes + their identified parents. This is conceptually similar to LOCALE's ego-graph scope.

### Counter-evidence / caution
SNOE achieves structural learning consistency (provable correctness in the population limit). LOCALE has no such theoretical guarantee -- it relies on empirical LLM accuracy. This is a narrative weakness if reviewers compare LOCALE to theoretically-grounded methods.

## For the Paper
- Cite SNOE as a contemporary non-LLM method for the same orientation-from-CPDAG problem
- Use the parallel to argue that "local orientation + global propagation" is a well-motivated algorithmic paradigm across both statistical and knowledge-based approaches
- SNOE's requirement for continuous data and ANM assumptions is the gap LOCALE fills: LOCALE works with metadata only, applicable when data is unavailable or discrete
