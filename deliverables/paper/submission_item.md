# Submission Items

## Title

LOCALE: Ego-Graph Orientation with Non-Collider Constraints for LLM-Assisted Causal Discovery

## Authors

Zhaoxiang Feng

## Keywords

non-collider constraints, ego-graph prompting, causal discovery, large language models, PC algorithm, edge orientation, constraint-based methods, query efficiency

## TL;DR

LOCALE orients causal edges via ego-graph LLM prompting with non-collider-only CI constraints, winning on 7/10 benchmarks vs MosaCD with 2-4x fewer queries; 97.9% of CI orientation errors are false colliders.

## Abstract

Skeleton-based causal discovery recovers an undirected graph from observational data but often leaves many edge orientations unresolved. Recent LLM-assisted methods orient these edges by querying one edge at a time, underusing the context window, or by feeding the entire graph into the prompt, scaling poorly. We propose LOCALE, a local-to-global orientation pipeline that prompts the LLM with node-centered ego graphs, scoring all incident edges jointly in a single query. A key empirical finding motivates our constraint design: across 6 Bayesian networks and 7 sample sizes, 97.9% of CI orientation errors from PC are false colliders (924/944 errors). We therefore discard collider constraints and retain only the more reliable non-collider constraints via weighted Max-2SAT (NCO filtering). In a multi-seed comparison against MosaCD on 10 Bayesian networks using the same open-weight 27B model and skeleton, LOCALE wins on 7 networks, ties on 2, and loses on 1 (Asia, 8 nodes), with a mean F1 improvement of +6.7 percentage points. Three wins are statistically significant after Holm-Bonferroni correction: Sachs (+30.7pp, p<0.0001), Insurance (+8.8pp, p=0.013), and Hepar2 (+16.0pp, p=0.013). Ego-graph prompts use 2-4x fewer queries than per-edge methods and remain robust at 2048-token context windows where MosaCD's per-edge templates fail. The NCO finding is method-agnostic and applicable to any CI-based orientation pipeline.

## Primary Area

Causality / Causal Discovery

## Venue

- **Target:** NeurIPS 2026 (project final report format)
- **Abstract deadline:** 2026-03-26
- **Paper deadline:** 2026-03-26
- **Format:** 6 pages body + appendix, neurips_2026.sty

## Revision Log

| Date | Field | Change | Reason |
|------|-------|--------|--------|
| 2026-03-12 | Title | Initial: "LOCALE: Ego-Graph Orientation with CI Constraints for LLM-Assisted Causal Discovery" | First draft |
| 2026-03-12 | TL;DR | Initial: "...achieving significant F1 gains on 2/5 benchmarks with 6x lower variance..." | Based on XN-030 (4-seed, pre-bug-fix) |
| 2026-03-26 | Title | "CI Constraints" → "Non-Collider Constraints" | NCO is the core contribution per narrative reframe (A01). Title should name it. |
| 2026-03-26 | TL;DR | Rewrote: 2/5 → 7/10 networks, removed "6x lower variance" (network-dependent per XN-031), added NCO finding | Corrected 12-seed comparison (XN-031), 10-network expansion (XN-035), data seed bug fix (D-A02) |
| 2026-03-26 | Abstract | Rewrote from scratch | Updated to XN-031/XN-035 numbers. Added Hepar2 as 3rd SIG win. Expanded from 5→10 networks. Removed "6x lower std" claim (was artifact of fixed data seed). Added context efficiency finding. |
| 2026-03-26 | Keywords | Added "non-collider constraints", "query efficiency"; reordered by specificity | Align with revised contribution ordering |
