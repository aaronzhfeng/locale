---
id: LN-008
title: "LLM-causal discovery landscape update: 2026 methods and venue context"
date: 2026-03-24
dag_nodes: ["I00", "E01"]
links:
  - target: LN-002
    type: supersedes
  - target: LN-001
    type: related_to
tags: ["landscape", "positioning", "venue-context", "competing-methods"]
---

# LN-008: LLM-Causal Discovery Landscape Update (March 2026)

## Purpose
Updates LN-002's landscape map with newer methods and venue context discovered during March 2026 literature scouting.

## New Methods Since LN-002

### CauScientist (arXiv:2601.13614, Jan 2026)
- **Global iterative** paradigm: LLM proposes graph edits, BIC-based verifier accepts/rejects
- Claims up to 53.8% F1 improvement and 44.0% SHD reduction on 37-node graphs
- Has error-memory component (records past failures to improve proposals)
- **Relevance**: strongest "global iterative" competitor. Different paradigm from LOCALE (local orientation). Reviewers may ask for comparison. However, CauScientist uses LLM for full graph refinement (O(n^2) scope per iteration), while LOCALE constrains LLM queries to local ego-graphs.

### ASoT (Meier et al., Information Processing & Management, 2025)
- Orchestrates smaller open models using dual-stream processing of opposing hypotheses
- Uses consensus mechanisms (Delphi protocol, ensemble synthesis)
- **Relevance**: dual-stream hypothesis processing parallels LOCALE's dual-endpoint reconciliation. Could cite for methodological precedent.

### MatMcd (Shen et al., ACL 2025 Findings, arXiv:2412.13667)
- Multi-agent system with Data Augmentation and Causal Constraint agents
- Integrates external data (web search, logs) as additional modality
- **Relevance**: different setting (multimodal, AIOps). Not a direct competitor for BNLearn benchmarks.

### LLM-Driven Causal Discovery via Harmonized Prior (Ban et al., IEEE TKDE, 2025)
- Decomposes pairwise causal judgment into separate aspects, then harmonizes
- **Relevance**: "decomposed prompting reduces noise" aligns with LOCALE's ego-graph thesis (structured context > monolithic query). Useful related work citation.

## MosaCD Venue Context
The brainstorm literature.md confirms MosaCD (arXiv:2509.23570) is an ICLR 2026 submission. If accepted, this significantly raises its profile as the primary baseline. LOCALE's paper should be positioned as a methodological advance beyond MosaCD, not just a comparison.

## Updated Operating Points (extends LN-002)

| Operating Point | Methods | LOCALE relation |
|----------------|---------|-----------------|
| Per-edge/CI local | MosaCD, chatPC, SCP | LOCALE is richer (ego-graph > single edge) |
| Bounded neighborhood | **LOCALE** (new) | Fills the gap |
| Global iterative | CausalFusion, CauScientist, ILS-CSL, MAC, MatMcd | LOCALE avoids O(n^2) global scope |
| Orchestration/consensus | ASoT, WISE | Design parallels to LOCALE's reconciliation |

## Counter-Evidence to Surface

1. **CauScientist's 37-node results** may outperform LOCALE on comparable networks if their error-memory mechanism is effective. We have not compared directly. This is a gap.
2. **No cross-model comparison**: LOCALE uses Qwen3.5-27B exclusively. CauScientist uses frontier models. The model gap remains an unresolved confound (noted in hub.md).
3. **Synthetic experiments missing**: CauScientist and MosaCD both evaluate on synthetic (ER, scale-free) graphs. LOCALE's proposal Section 5.5 on synthetic experiments is still untouched.

## For the Paper
- Updated related work section should include CauScientist and ASoT
- Positioning: LOCALE fills the "bounded neighborhood" operating point between per-edge and global
- MosaCD's potential ICLR acceptance raises the bar for comparison rigor
