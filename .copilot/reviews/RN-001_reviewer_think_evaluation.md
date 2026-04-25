---
id: RN-001
source: reviewer
title: "THINK-phase gate review: are LOCALE results validated for SAY?"
date: 2026-03-26
dag_nodes: [E01, E03, I02, I03, A02]
trigger: "THINK->SAY gate"
recommendation: "Weak Reject"
priority_issues: 7
---

## Per-Dimension Ratings

| Dimension | Score | Justification |
|---|---|---|
| Relevance | 3/4 | LLM-assisted causal discovery is timely; the ego-graph operating point fills a real gap between per-edge and global methods. MosaCD at ICLR 2026 confirms venue interest. |
| Novelty | 2/4 | NCO finding is genuinely useful but is a diagnostic observation, not a methodological invention. Ego-graph batching is underexplored but not novel in concept (BFS prompting, local causal discovery literature). The proposal framed 5 hypotheses; only H1 and H2 (refined) survive. |
| Technical Quality | 2/4 | Data seed bug (D-A02) was found and corrected -- credit for that. But the comparison still has a fundamental model confound, 2 of 6 proposal hypotheses unsupported, 2 untested, single-model evaluation, no synthetic experiments, and a significant loss on Asia that is structural. |
| Presentation | 3/4 | The internal documentation is thorough and honest. The State of Knowledge in hub.md is well-organized and forthcoming about weaknesses. However, the narrative has drifted substantially from the proposal without formal re-scoping. |
| Reproducibility | 2/4 | Single model family (Qwen3.5-27B). MosaCD re-implementation without public code. Disguised robustness on 1 seed. Several key experiments at single seed. No synthetic experiments for controlled evaluation. |
| Reviewer Confidence | 4/4 | I have read all 31 experiment notes, 8 literature notes, 2 decision memos, the full proposal, and the research log. My assessment is based on the raw evidence. |

## Overall Recommendation
**Weak Reject** -- the project has produced real findings (NCO, context efficiency) but the experimental evidence is not yet sufficient for a venue submission. Multiple P1 and P2 issues must be resolved.

## Summary

LOCALE proposes ego-graph batching as a middle-ground operating point for LLM-assisted causal edge orientation, combining local CI constraints (NCO filtering) with Max-2SAT solving and confidence-weighted reconciliation. The corrected 12-seed comparison against a same-model MosaCD re-implementation shows 2 significant wins (Sachs +30.7pp, Insurance +8.8pp), 2 directional wins (Alarm, Child -- not significant), and 1 significant loss (Asia -6.7pp). The strongest standalone finding is the NCO observation: 97.9% of CI orientation errors are false colliders across 6 networks and 7 sample sizes. Context efficiency (LOCALE works at 2048 tokens, MosaCD breaks) is a secondary but genuine contribution.

## Previous Review Follow-Up
No prior RN-NNN reviews exist. This is the first formal review.

## Strengths

- **S1: Honest self-assessment.** The State of Knowledge in hub.md and the experiment notes are unusually transparent about negative results (Asia loss, Dawid-Skene failure, iterative BFS failure, skeleton refinement veto). This is rare and commendable. The data seed bug (D-A02) was self-discovered and corrected rather than swept under the rug.

- **S2: NCO finding is robust and method-agnostic.** XN-022 validates false-collider dominance across 6 networks, 7 sample sizes, and 3 seeds (944 errors, 97.9% FC rate). The finding has a clean mechanistic explanation (CI test power asymmetry), is independently actionable by any method using PC-family CI facts, and is well-quantified. This is the paper's strongest contribution.

- **S3: Context efficiency is a genuine architectural advantage.** XN-029 demonstrates that MosaCD's chain-based per-edge prompts exceed 2048 tokens on high-degree nodes, causing catastrophic degradation (Insurance F1: 0.723 -> 0.538 at 2048). LOCALE's ego-graph prompts fit comfortably. This is a real deployment advantage, not an artifact.

- **S4: Query cost savings are consistent.** 2.4-4x fewer queries across all 6 networks (XN-013). This is the most robust advantage -- it holds universally regardless of network structure.

- **S5: Statistical methodology on the corrected comparison is sound.** Paired t-tests with Holm-Bonferroni correction, Cohen's d effect sizes, variance analysis. The statistical framework in XN-031 is appropriate for the claims being made.

## Weaknesses

- **W1 (P1): Published MosaCD gap is an unresolved confound that undermines the primary comparison.** The MosaCD re-implementation produces Alarm F1 = 0.801 vs published MosaCD = 0.93 (a 12.9pp gap). XN-024 attributes this to "model difference (GPT-4o-mini has 128K context)" and context overflow. But this means the comparison is not against MosaCD-the-method; it is against a potentially degraded re-implementation of MosaCD on a model (Qwen3.5-27B) that may disadvantage per-edge prompting relative to ego-graph prompting. The proposal's Section 5.7 Gate 3 ("Baseline-fidelity gate") explicitly states: "No direct apples-to-apples claim is made against a system without official code or sufficiently detailed prompts." This gate has not been passed. A reviewer at ICLR/CLeaR will immediately ask: "Your Alarm MosaCD gets 80.1% while the published MosaCD gets 93%. Why should I believe your re-implementation is faithful?" The 12-seed comparison inherits this confound on every network. **This is addressable** but requires either (a) running MosaCD with a model that has 128K+ context (e.g., GPT-4o-mini or a similar open model), or (b) running LOCALE with GPT-4o-mini for a cross-model comparison, or (c) transparently reporting the re-implementation gap with a sensitivity analysis showing the result is robust to plausible model quality differences.

- **W2 (P1): 3 of 5 proposal hypotheses are not supported or not tested -- the paper has no theoretical spine.** The proposal organized itself around H1-H5. Current status: H1 (ego-context) is supported but weakly (ego wins on some networks, loses on d=3 nodes, and the multi-seed comparison shows wins driven as much by NCO+Max-2SAT as by ego prompting itself). H2 (hard constraints) is "supported (refined)" but actually shows the opposite of what was proposed -- hard constraints hurt until NCO filtering removes the false colliders, making the contribution "discovering that the proposed approach was wrong and fixing it." H3 (reconciliation) is explicitly "not supported" -- Dawid-Skene failed. H4 (propagation) is "not tested meaningfully" -- Meek is a no-op. H5 (calibration) is "not tested" -- Phase 6 descoped. When 3 of 5 hypotheses fail or are untested, the paper needs a fundamentally different narrative than the proposal laid out. The current "diagnostic study" reframing is sensible but it was not tested as a hypothesis -- it was retrofitted to match the results. **This is partly addressable** (reframe as diagnostic study, formally descope H3-H5 with justification) and **partly structural** (the method is simpler than proposed, which limits the contribution).

- **W3 (P1): No synthetic experiments (proposal Section 5.5/E5 entirely untouched).** The proposal specifies 100-node ER and scale-free DAGs with controlled conditions as part of the confirmatory suite. These are completely absent. Synthetic experiments are the standard way to evaluate causal discovery methods because they allow controlled variation of graph density, sample size, and noise. Without them, the results are limited to 5 small BNLearn networks (8-37 nodes) which are all textbook examples and potential training data for the LLM. The disguised robustness test (XN-026) addresses memorization but only on 2 networks at 1 seed. Synthetic experiments would also address the scalability question: does ego-graph batching scale to 100+ nodes? Hailfinder (56 nodes) already blocked on PC skeleton estimation (XN-013). **This is addressable** but requires substantial additional work.

- **W4 (P2): Disguised robustness test is thin (2 networks, 1 seed).** XN-026 tests Insurance and Alarm with anonymized variables at seed 42 only. This is the seed that was later found to be the only data seed LOCALE ever used (D-A02). The disguised test has never been re-run with correctly varying seeds. With n=1, the +4.7pp improvement on disguised Insurance could be noise. The proposal's Gate 5 ("Anonymization gate: No headline claim is made unless gains persist, at least partially, under anonymized variables") requires this to hold robustly. It has been tested at the bare minimum. **This is addressable** with multi-seed disguised runs on all 5 networks.

- **W5 (P2): Asia loss is structural and reveals a design limitation that applies to any low-degree node.** The Asia loss (-6.7pp, SIG) is not just about Asia. It reveals that any degree-1 node in any network gets single-endpoint ego-graph coverage with no reconciliation opportunity. The root cause (XN-031): `tub` has degree 1, so only `either`'s ego-graph covers the `either->tub` edge, and the LLM consistently reverses it. This is a structural weakness of the ego-graph approach. In any real-world network with leaf nodes (which is most networks), LOCALE will have this vulnerability. Insurance happens to have no degree-1 nodes in the skeleton, which explains why it works well there. The paper must characterize how many edges in each network are vulnerable to this (degree-1 coverage analysis), and ideally implement the per-edge fallback (Phase 5) that was descoped specifically to handle this case. **This is partly addressable** (degree-1 analysis, Phase 5 fallback) and **partly structural** (ego-graph design inherently has this limitation).

- **W6 (P2): Hepar2 is absent from the multi-seed comparison.** Hub.md notes "Hepar2 not in multi-seed comparison." Hepar2 is the largest network tested (70 nodes) and the only one approaching realistic scale. Single-seed Hepar2 results (XN-024: F1=0.599 for LOCALE vs 0.442 for MosaCD re-implementation) are not sufficient for claims. Moreover, Hepar2 has 52% skeleton coverage, making it the worst case for the "skeleton is the bottleneck" narrative. Including Hepar2 in multi-seed would either strengthen or weaken this narrative -- either way, it needs to be done. **This is addressable.**

- **W7 (P2): Single model family (Qwen3.5-27B) limits generalizability claims.** The proposal specifies cross-model validation (Section 5). Only the 9B ablation (XN-023) has been done, showing 27B is required. No testing with GPT-4 family, Claude, Llama, or other model families. The model confound is particularly acute because: (a) the MosaCD comparison uses the same model that may systematically favor ego-graph prompting over per-edge prompting, (b) the claim of "open-source competitiveness" rests on one model family, (c) the d=3 weakness and Asia loss could be model-specific. **This is addressable** but expensive.

- **W8 (P3): The "F1 decomposition" contribution is descriptive, not methodological.** The observation that F1 = f(skeleton_coverage, orientation_accuracy) is correct but obvious to anyone who thinks about it for 30 seconds. Every causal discovery researcher knows that skeleton quality bounds downstream metrics. Framing this as a "contribution" risks a reviewer dismissal. It would be stronger as a motivation for the NCO finding (which actually improves the F1 decomposition picture) rather than a standalone contribution.

- **W9 (P3): XN-031 uses inconsistent sample counts across networks.** Insurance has 10 paired comparisons (no s42 for MosaCD due to broken symlinks), while other networks have 11-12. Sachs and Alarm have 11 pairs each. The broken symlink issue (seed 42 directories from previous Lightning Studio environment) introduces asymmetry. While the statistical tests account for this, it is messy and a reviewer will question why the flagship experiment has missing data.

- **W10 (P3): No SNOE or CauScientist direct comparison.** LN-005 identifies SNOE as solving the exact same problem (orient undirected edges in a CPDAG). LN-008 identifies CauScientist as the strongest global iterative competitor. Neither has been compared against directly. For a venue submission, reviewers familiar with these methods will ask why they are absent. SNOE is particularly relevant because it has theoretical guarantees that LOCALE lacks. **This is partly addressable** (SNOE comparison on the same networks) but may reveal uncomfortable results.

## Questions for the Copilot

1. **Has the disguised robustness test (XN-026) been re-run with correctly varying data seeds?** The original test used seed 42, which was the only data seed LOCALE ever used due to D-A02. If not, the anonymization gate (proposal Section 5.7, Gate 5) has not been legitimately passed.

2. **What is the degree-1 node count in each network's PC skeleton?** The Asia loss is attributed to `tub` being degree-1. How many edges in Insurance, Alarm, Child, Sachs, and Hepar2 are covered by only one endpoint's ego-graph? This determines how broadly the Asia-style vulnerability applies.

3. **Why was Phase 5 (per-edge fallback) descoped when it directly addresses the Asia loss?** The proposal designed Phase 5 specifically for the "residual hard edges" case. The copilot notes "residual is empty after Max-2SAT" -- but the Asia case shows the residual is not empty, it is just being handled badly by single-endpoint coverage. Phase 5 could serve as a degree-1 safety net.

4. **What is the actual re-implementation fidelity of MosaCD?** XN-024 notes "no public repo exists, but the paper provides complete pseudocode." Has the re-implementation been validated against any MosaCD results beyond the PC-only baseline? The 12.9pp gap on Alarm (80.1% vs 93%) is not explained by context overflow alone -- context overflow affected only 11/45 edges on seed 0.

5. **Can you produce a power analysis for Alarm and Child?** XN-031 reports d=0.51 for Alarm and d=0.18 for Child. How many seeds would be needed for significance? If the answer is 30+ (Alarm) or 250+ (Child), these should be explicitly characterized as "no meaningful difference detectable at feasible sample sizes" rather than "directional wins."

6. **Why does the tracker say "Last updated: 2026-03-11" when the corrected comparison is from 2026-03-26?** This suggests the tracker was not updated at the DO->THINK transition. Is the tracker current?

7. **The NCO validation (XN-022) used 3 seeds. Were these data seeds correctly varying, or did they fall prey to the same seed bug (D-A02) that affected the multi-seed comparison?** If the NCO validation used the same `sample_data()` function, all 3 "seeds" may have used identical data.

## Addressable vs Structural

### Addressable
- **W1**: Run cross-model comparison (either LOCALE on GPT-4o-mini or MosaCD on a 128K-context open model) to close the re-implementation fidelity gap.
- **W3**: Run synthetic experiments (even a reduced set: 50-node ER graphs, 2 densities, 3 seeds) to establish scalability and controlled evaluation.
- **W4**: Re-run disguised robustness with correct multi-seed protocol on all 5 networks.
- **W6**: Add Hepar2 to multi-seed comparison.
- **W7**: Test with at least one additional model family (e.g., Llama 3.x 70B or Qwen3-32B).
- **W9**: Fill in missing seed 42 data or document the gap explicitly.
- **W10**: Run SNOE on the same networks for a non-LLM baseline comparison.

### Structural
- **W2 (partly)**: The proposal's hypothesis structure (H1-H5) has collapsed. The paper must be reframed around what actually works (NCO + ego-batching + context efficiency) rather than the original 5-hypothesis framework. This is a narrative redesign, not just more experiments.
- **W5 (partly)**: The degree-1 vulnerability is inherent to ego-graph orientation. Phase 5 can mitigate it but cannot eliminate the architectural limitation. Must be disclosed as a known weakness.
- **W8**: The F1 decomposition is not a contribution; it is context. This is a framing issue, not an experimental one.

## Overall Assessment

The project has produced two genuinely useful findings: (1) the NCO observation about false-collider dominance in PC-family CI testing, and (2) the context efficiency advantage of ego-graph prompts over per-edge prompts. Both are supported by solid evidence. The query cost savings are also real and consistent.

However, the project is **not ready for SAY** in its current state. The primary comparison is against a re-implementation of MosaCD with a known fidelity gap (W1). The proposal's experimental plan is substantially incomplete: no synthetic experiments (W3), no cross-model validation (W7), thin disguised robustness (W4), Hepar2 absent from multi-seed (W6). The narrative must be rebuilt around the actual findings rather than the original hypothesis structure (W2).

**To change my mind**, the revision needs:
1. **(Must-have)** Close the MosaCD re-implementation confound: either cross-model comparison or explicit sensitivity analysis with documented fidelity check.
2. **(Must-have)** Re-run disguised robustness with correct seeds (the current test is tainted by D-A02).
3. **(Must-have)** Degree-1 vulnerability analysis across all networks.
4. **(Should-have)** At least a reduced synthetic experiment (50-node ER, 3 densities, 3 seeds).
5. **(Should-have)** Hepar2 in multi-seed.
6. **(Nice-to-have)** One additional model family.
7. **(Nice-to-have)** SNOE comparison.

Items 1-3 are showstoppers: without them, a competent reviewer will find the same gaps. Items 4-5 are expected at a top venue and their absence weakens the submission. Items 6-7 would strengthen but are not fatal if the paper is properly scoped to single-model, BNLearn-only claims.

The direction is sound. The NCO finding alone may be publishable at a workshop or as a short paper. For a main-track submission at CLeaR/UAI, the evidence gaps need to be closed.
