---
id: LN-002
title: "LLM-causal discovery landscape: two operating points and a gap"
date: 2026-03-11
dag_nodes: [I00, I02]
links:
  evidence_for: [I00]
  related_to: [XN-016, XN-024]
tags: [landscape, positioning, related-work]
---

# LN-002: LLM-Causal Discovery Landscape

## Operating Points

### 1. Small local queries (per-edge/CI)
- **MosaCD** [arXiv:2509.23570]: per-edge orientation with shuffled debiasing + propagation
- **chatPC** [arXiv:2412.18945]: LLM as CI oracle inside PC (answers "is X ⊥ Y | Z?")
- **SCD+LLM/SCP** [arXiv:2307.02390]: pairwise LLM priors injected into score-based discovery

### 2. Graph-level iterative refinement
- **CausalFusion** [NeurIPS 2025 workshop]: LLM proposes, statistical falsification pushes back
- **CauScientist** [arXiv:2601.13614]: multi-agent debate + statistical verification
- **ILS-CSL** [arXiv:2311.11689]: iterative LLM supervision of partially learned DAG
- **MAC** [OpenReview]: multi-agent collaborative causal reasoning

### 3. LOCALE's gap: bounded local neighborhood
LOCALE fills the gap between per-edge and graph-level. The ego-graph is richer than a single edge (exposes joint orientation patterns) yet bounded (O(d) context). No other method in the 2024-2026 literature directly combines:
- Fixed skeleton + local neighborhood orientation
- Hard CI-derived constraints (Max-2SAT)
- Confidence-weighted dual-endpoint reconciliation

## Key Insight
The brainstorm literature review (71 papers) found no method using ego-graph prompting + hard constraint compilation. chatPC is nearest but uses LLM as CI oracle, not orientation oracle. COAT uses local Markov blanket discovery but targets variable discovery, not edge orientation on fixed variables.
