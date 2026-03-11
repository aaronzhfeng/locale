# Project Overview

**Project**: LOCALE (Local Oracle for Causal Alignment via Learnable Ego-graphs)
**Paper title**: Ego-Causal: CI-Conditioned Ego-Graph Orientation for LLM-Assisted Skeleton-Based Causal Discovery
**One-line pitch**: A local-to-global orientation layer where the LLM scores all incident edges around a node jointly under CI-derived hard constraints, with dual-endpoint reconciliation and calibrated selective output.

## Research Questions

1. Does ego-graph context (phi x psi) improve edge orientation accuracy over per-edge queries (psi only)?
2. How does reconciliation precision (dual-perspective Dawid-Skene) compare to MosaCD's shuffled-query debiasing?
3. Does the scaling advantage (O(d) context vs O(V^2)) translate to better accuracy on large graphs (100+ nodes)?
4. Can Venn-Abers calibration provide meaningful finite-sample coverage guarantees for causal edge orientations?

## Hypotheses

- **H1 (ego-context)**: At matched total token budget, ego-graph prompting improves accuracy-cost tradeoff over per-edge prompting because one query scores multiple incident edges while exposing mechanism-level neighborhood context.
- **H2 (hard-constraint)**: Adding CI-derived hard local constraints improves local consistency and edge-orientation accuracy relative to unconstrained ego scoring because infeasible collider/non-collider patterns are removed.
- **H3 (reconciliation)**: Statistical reconciliation of endpoint judgments improves seed precision at fixed seed coverage relative to majority vote and shuffled voting, provided the gain persists under dependence-aware sensitivity analysis.
- **H4 (propagation)**: Conservative propagation resolves a substantial fraction of high-confidence edges before fallback; the residual tail is enriched for genuinely hard edges.
- **H5 (selective-output)**: Post-hoc calibration and abstention reduce false-orientation risk among committed edges and improve selective SHD relative to forced top-1 orientation.

## Target Venue

| Venue | Deadline | Page Limit | Track |
|-------|----------|-----------|-------|
| CLeaR 2027 | ~Sep 2026 | TBD | Main conference (primary) |
| UAI 2027 | ~Feb 2027 | TBD | Main conference |
| NeurIPS 2026 | May 2026 | 9+refs | Main conference (stretch) |

## Constraints

- **Compute**: API calls only (~$50-200 for full experiments). No GPU training.
- **Timeline**: MVE in one afternoon; full system 2-3 months.
- **Team**: Solo (first-authored).
- **Causal sufficiency** assumed for v1.

## Key Baselines

1. PC-stable + Meek (data-only, no LLM)
2. CPC + Meek (data-only, no LLM)
3. MosaCD-style per-edge prompting + propagation (matched skeleton, metadata, LLM, token budget)
4. Per-edge same-information baseline (same fields as ego prompt, one edge at a time)
5. Same-context per-edge control (ego neighborhood context, but single edge scored)
6. CI-only local solver (hard constraints with uniform soft weights)
7. CausalFusion, CauScientist (literature-reference comparators)

## The Gap

No existing method uses the LLM for local neighborhood reasoning with algorithmic global propagation. Per-edge methods (MosaCD, chatPC) waste the LLM's context window on single-edge binary classification. Global methods (CausalFusion, CauScientist) stuff the entire DAG into context (O(V^2) tokens). The ego-graph is an underexplored middle ground: rich enough for mechanism-level reasoning, bounded and auditable, naturally matched to PC/CPC-style local structure.

## Claimed Contributions

The contribution is the **composition and evaluation** of modules, not novelty in any single component:

1. **Ego-graph prompting** as an underexplored LLM interface for skeleton-based edge orientation (richer than per-edge, more scalable than whole-graph)
2. **Local hard-constraint compilation** combining CI-derived feasibility with LLM soft scores (joint phi x psi optimization)
3. **Dual-endpoint reconciliation** mapping ego-graph judgments into annotator-aggregation framework (Dawid-Skene + dependence-aware sensitivity)
4. **Conservative propagation** with Meek closure, rollback safeguards, and confidence-aware scheduling
5. **Calibrated selective output** with edge-level Venn-Abers confidence and principled abstention

## Method Pipeline

```
Phase 0: PC-stable skeleton + separating sets + CI stats
Phase 1: Ego-graph construction + LLM prompting (structured JSON output)
Phase 2: Local hard-constraint compilation + exact/near-exact solving (Max-2SAT)
Phase 3: Dual-endpoint reconciliation (Dawid-Skene, EBCC sensitivity)
Phase 4: Conservative propagation + Meek closure + rollback
Phase 5: Budgeted per-edge fallback (hard tail only, ~10-15%)
Phase 6: Multiclass Venn-Abers calibration + selective output
```

## Core Experiments

- **E1**: Context-isolated ego vs per-edge comparison (H1, H2)
- **E2**: Hard-constraint benefit and infeasibility analysis (H2)
- **E3**: Reconciliation and dependence test (H3)
- **E4**: Propagation and fallback analysis (H4)
- **E5**: Calibration and selective output (H5)

## Key Risks (from audits)

1. **Scope creep**: Experiment matrix can explode (432 synthetic cells before seeds). Mitigation: Tier 1 confirmatory suite only in main paper.
2. **Metadata leakage**: Variable descriptions may encode causal direction. Mitigation: Anonymized condition mandatory.
3. **Error propagation**: Mistakes in early rounds cascade. Mitigation: Only propagate reconciled edges; rollback triggers; confidence damping.
4. **Hub-degree handling**: Ego prompts break down for high-degree nodes. Mitigation: Cap at degree 8; sub-ego splitting.
5. **Reconciliation independence**: CBCC correlation correction needs calibration data. Mitigation: Dependence-aware sensitivity analysis mandatory.

## Brainstorm Source

`brainstorm-27-ego-causal/` — contains literature (PDFs + summaries), proposals (v1, v2), audits (C01-C05 novelty/grounding/methodology/evaluation/feasibility), and the raw idea.
