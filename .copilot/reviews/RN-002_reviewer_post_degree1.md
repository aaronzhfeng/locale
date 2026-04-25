---
id: RN-002
source: reviewer
title: "Post-degree-1 review: RN-001 follow-up and independent reassessment"
date: 2026-03-26
dag_nodes: [E01, E03, I02, I03, A02, I11]
trigger: "THINK->DO gate"
recommendation: "Weak Reject"
priority_issues: 6
---

## Per-Dimension Ratings

| Dimension | Score | Justification |
|---|---|---|
| Relevance | 3/4 | Unchanged from RN-001. LLM-assisted causal discovery is an active area; MosaCD at ICLR 2026 confirms venue interest. The bounded-neighborhood operating point fills a real gap. |
| Novelty | 2/4 | NCO finding is the strongest novel element but it is a diagnostic observation about PC's CI tests, not a methodological invention. Ego-graph batching is underexplored but not conceptually novel (BFS prompting, local causal discovery). SNOE solves the same orientation-from-CPDAG problem with theoretical guarantees LOCALE lacks. The method itself is simpler than proposed (3 of 5 hypotheses collapsed). |
| Technical Quality | 2/4 | The corrected comparison (XN-031) is an improvement over XN-030, and credit for self-discovering the seed bug. But 2 of 3 RN-001 must-haves remain unaddressed. MosaCD re-implementation confound is open. Disguised robustness is still single-seed and tainted by the same seed=42 that was the only seed LOCALE ever used. No synthetic experiments. The degree-1 analysis was done informally without an experiment note. |
| Presentation | 3/4 | Internal documentation remains excellent. The hub.md State of Knowledge is honest and well-organized. The tracker is slightly stale (last updated 2026-03-11 at the header, though individual entries were updated 2026-03-26). |
| Reproducibility | 2/4 | Single model family. MosaCD re-implementation without public code or fidelity validation beyond PC-only baseline. Disguised robustness on 1 seed. No synthetic experiments. All benchmarks are small textbook BNLearn networks (8-37 nodes in the multi-seed comparison). |
| Reviewer Confidence | 4/4 | I have read all 31 experiment notes, 8 literature notes, 2 decision memos, the full proposal, the research log through LOG-2026-03-26-39, the raw NCO validation code, and the mve_insurance.py bug fix. My assessment is based on the raw evidence, not the copilot's framing. |

## Overall Recommendation
**Weak Reject** -- progress has been made on one of three RN-001 must-haves (degree-1 analysis, though informally). The other two must-haves (MosaCD confound, disguised robustness re-run) remain unaddressed. The experimental evidence is still insufficient for a venue submission. The core findings (NCO, context efficiency, query savings) are genuine and worth pursuing, but the comparison claim against MosaCD -- which is the paper's competitive positioning -- has unresolved confounds.

## Summary

LOCALE proposes ego-graph batching for LLM-assisted causal edge orientation, combining local CI constraints (NCO filtering) with Max-2SAT solving and confidence-weighted reconciliation. The corrected 12-seed comparison (XN-031) against a same-model MosaCD re-implementation shows 2 significant wins (Sachs +30.7pp, Insurance +8.8pp), 2 non-significant directional wins (Alarm +3.9pp, Child +1.1pp), and 1 significant loss (Asia -6.7pp). The strongest standalone finding is the NCO observation: 97.9% of CI orientation errors are false colliders across 6 networks, 7 sample sizes, and 3 seeds (944 errors). Context efficiency (LOCALE works at 2048 tokens, MosaCD breaks) and query cost savings (2.4-4x) are secondary genuine contributions.

## Previous Review Follow-Up (RN-001)

RN-001 identified 3 must-haves, 2 should-haves, and 2 nice-to-haves.

### Must-Have #1 (W1/P1): MosaCD re-implementation confound
**Status: UNADDRESSED.** The 12.9pp gap on Alarm (80.1% re-implementation vs 93% published) remains unexplained. No cross-model comparison has been run. No sensitivity analysis has been conducted. No fidelity validation beyond the PC-only baseline has been attempted. The proposal's own Gate 3 ("Baseline-fidelity gate") remains unpassed. This was flagged as a showstopper in RN-001 and remains one.

### Must-Have #2 (W4/P2): Disguised robustness re-run
**Status: UNADDRESSED.** XN-026 still uses seed=42 only -- the same seed that was the only data seed LOCALE ever used due to D-A02. The checkpoint acknowledges "NEEDS GPU" but no re-run has been conducted. The anonymization gate (proposal Section 5.7, Gate 5) has not been legitimately passed.

### Must-Have #3 (W5/P2): Degree-1 vulnerability analysis
**Status: PARTIALLY ADDRESSED.** The checkpoint claims this is "DONE" with results: "Asia (25pp gap), Alarm (17pp gap), but Insurance (0pp, perfect) and Child (-5pp, single is better)." However, this analysis exists only as a line item in checkpoint.md -- there is no dedicated experiment note (no XN-032), no documented methodology, no reproducible script, and no formal write-up. The XN-031 note contains some degree-1 discussion for Asia (`tub` has degree 1, 100% consistent error) but not the systematic cross-network analysis claimed in the checkpoint. I cannot verify the numbers "25pp gap" and "17pp gap" because they are not documented anywhere I can find.

### Should-Have #4: Synthetic experiments
**Status: UNADDRESSED.** Proposal Section 5.5 entirely untouched. The checkpoint lists this as "NEEDS GPU."

### Should-Have #5: Hepar2 multi-seed
**Status: UNADDRESSED.** The checkpoint lists this as "NEEDS GPU."

### Nice-to-Haves #6-7 (cross-model, SNOE comparison)
**Status: UNADDRESSED.** No work done.

**Summary: 1 of 3 must-haves partially addressed; 0 of 2 should-haves addressed; 0 of 2 nice-to-haves addressed.** This is insufficient progress to change the RN-001 recommendation.

## Strengths

- **S1: Honest self-assessment and bug discovery (carried from RN-001).** The seed bug (D-A02) was self-discovered, transparently documented, and corrected. The copilot did not sweep it under the rug. The hub.md State of Knowledge remains forthright about all weaknesses. This is still commendable.

- **S2: NCO finding is robust and independently valid (carried from RN-001).** XN-022 validates false-collider dominance across 6 networks, 7 sample sizes, and 3 seeds (944 errors, 97.9% FC rate). The NCO validation script independently found and fixed the same seed bug that affected the main pipeline (XN-022, line 31: "seed not passed through to pgmpy sampler"). I verified in the code (`nco_validation.py` line 36) that the fix is in place: `data = sample_data(model, n=n_samples, seed=seed)`. The NCO finding is the paper's strongest contribution and is not contaminated by the D-A02 bug.

- **S3: Corrected comparison validates the headline.** The XN-030 to XN-031 transition is clean: the results held up despite LOCALE now facing genuine data variance (not just LLM sampling variance). Insurance and Sachs wins are large-effect-size and robust. The "6x more stable" artifact was correctly identified and retracted. This shows methodological integrity.

- **S4: Context efficiency is a genuine, well-documented advantage (carried from RN-001).** XN-029's analysis of MosaCD's context sensitivity is thorough and reproducible. The root cause (chain-based per-edge templates exceeding context for high-degree nodes) is mechanistic, not speculative.

- **S5: Statistical methodology in XN-031 is appropriate.** Paired t-tests with Holm-Bonferroni correction, Cohen's d effect sizes, explicit separation of significant vs directional results. The statistical framework matches the claims.

## Weaknesses

- **W1 (P1): MosaCD re-implementation confound remains the central unresolved threat to validity.** This was RN-001 must-have #1 and it is completely unaddressed. The re-implementation produces Alarm F1=0.801 vs published MosaCD=0.93 (12.9pp gap). XN-024 attributes this to "model difference (GPT-4o-mini has 128K context)" and context overflow, but XN-029 shows only 11/45 Alarm edges at seed 0 are affected by context overflow. Even at 4096 context, the gap is substantial. The comparison is against a potentially degraded re-implementation of MosaCD on a model that may systematically favor ego-graph prompting over per-edge prompting. Until this is addressed, the headline "2 SIG wins + 1 SIG loss" is the comparison between LOCALE and "our understanding of MosaCD, which may be systematically disadvantaged." A CLeaR or UAI reviewer will immediately identify this. Three options exist: (a) run LOCALE with GPT-4o-mini, (b) run MosaCD with a 128K-context open model, (c) transparently report the fidelity gap with a sensitivity analysis showing results are robust to plausible MosaCD improvements. None have been attempted. **Addressable but requires GPU access and either API budget or an open-weight 128K model.**

- **W2 (P1): Disguised robustness test (XN-026) is invalidated by the seed bug context and has not been re-run.** XN-026 used seed=42 -- the only data seed LOCALE ever used before the D-A02 fix. The disguised test therefore ran on the same data configuration that LOCALE was effectively hardcoded to use. While the disguised test does not directly depend on data variance (it tests whether anonymizing variable names degrades accuracy), the fact that it was run on 1 seed that happens to be the buggy default, on only 2 of 6 networks, means the evidence for "LOCALE does not rely on memorized domain knowledge" rests on a single experimental configuration per network. The Phase 2 accuracy improvement from disguised mode (+4.7pp on Insurance) could be a seed-specific artifact. This matters because the memorization/contamination concern is the most common criticism of LLM-based methods on benchmark networks, and the paper's defense against it is thin. **Addressable: re-run disguised mode with multiple seeds on all 5 networks.**

- **W3 (P1): No synthetic experiments, and the benchmark networks are all small textbook BNLearn graphs.** The 5-network comparison uses Asia (8 nodes), Sachs (11), Child (20), Insurance (27), and Alarm (37). These are all classic BNLearn textbook networks that appear extensively in causal discovery literature and, critically, in LLM training corpora. Even though the disguised robustness test (XN-026) suggests LOCALE does not rely on memorized names, it does not rule out that the LLM has learned structural patterns about these specific graph topologies from training data. Synthetic experiments (proposal Section 5.5) would control for this contamination risk by using novel graph structures the LLM cannot have memorized. They would also test scalability beyond 37 nodes -- Hailfinder (56 nodes) already blocked on PC skeleton estimation, and Hepar2 (70 nodes) is absent from the multi-seed comparison. Without synthetic experiments, the paper's evidence base is limited to "toy-sized networks that the LLM may have seen during training." This is not a nit -- it is a fundamental limitation that any informed reviewer will raise. **Addressable but requires substantial compute.**

- **W4 (P2): The degree-1 analysis claimed in checkpoint.md is undocumented and unverifiable.** The checkpoint claims "Degree-1 vulnerability analysis: DONE. Network-dependent: Asia (25pp gap), Alarm (17pp gap), but Insurance (0pp, perfect) and Child (-5pp, single is better)." But there is no XN-032 experiment note, no analysis script, no raw data supporting these numbers. The only documented degree-1 discussion is in XN-031 (Asia's `tub` node). I cannot find any file in the project that documents the 25pp and 17pp figures or explains the methodology behind them. An analysis that exists only as a claim in checkpoint.md without supporting evidence is not "done" -- it is an unverified assertion. **Addressable: write the experiment note with methodology and reproduce the numbers.**

- **W5 (P2): Sachs F1 discrepancy between XN-024 and XN-031 is unexplained and suggests a confound.** XN-024 reports Sachs LOCALE F1=0.765, MosaCD F1=0.588 (delta +17.7pp) at single seed. XN-031 reports Sachs LOCALE F1=0.865, MosaCD F1=0.557 (delta +30.7pp) across 12 seeds. The MosaCD numbers are consistent (0.588 single-seed vs 0.557 multi-seed average -- reasonable). But LOCALE jumped from 0.765 to 0.865 (+10pp), which needs explanation. Is this because XN-024 used seed=42 with the bug (meaning it had data-seed=42 anyway, so both LOCALE runs used the same data), while XN-031 uses correctly varying seeds that happen to produce better-performing skeletons on average? Or did the pipeline change between XN-024 and XN-031? This matters because the Sachs win (+30.7pp) is the largest effect size in the paper and will be scrutinized. **Addressable: document the source of the 10pp LOCALE Sachs improvement between XN-024 and XN-031.**

- **W6 (P2): The "F1 decomposition" and "safety valve" are listed as contributions but are not novel.** The F1 decomposition (F1 = f(skeleton_coverage, orientation_accuracy)) was flagged in RN-001 as "obvious to anyone who thinks about it for 30 seconds." This has not changed. The safety valve (monotonically non-decreasing pipeline via damage detection) is a standard engineering pattern, not a research contribution. Listing 5 contributions when only 2 (NCO, query efficiency) are genuinely novel dilutes the paper's impact. A reviewer counting "contributions that are actually contributions" will arrive at 2, not 5. **Addressable: reframe as context/design choices rather than standalone contributions.**

- **W7 (P3): The tracker header says "Last updated: 2026-03-11" despite substantial work on 2026-03-26.** The tracker body was updated with corrected XN-031 results and the D-A02 bug fix, but the header timestamp was not updated. This is minor but creates a misleading impression of documentation currency.

- **W8 (P3): XN-031 pair counts are inconsistent across networks.** Insurance has 10 paired comparisons, others have 11-12. The broken symlink issue (seed 42 directories from previous Lightning Studio) creates asymmetric sample sizes. While the statistical tests handle unequal n, this is messy data management and a reviewer will question it.

- **W9 (P3): Alpha=0.10 for Asia is a post-hoc tuning that advantages LOCALE.** The alpha change from 0.05 to 0.10 was motivated by XN-028's finding that alpha=0.10 recovers 100% skeleton coverage for Asia. Both methods use alpha=0.10, so the comparison is technically fair. But the decision to change alpha for one network is a post-hoc optimization that risks cherry-picking. If the paper reports "alpha=0.05 for all networks except Asia (alpha=0.10)," a reviewer will ask: "did you try other alpha values for other networks, and if so, why did you pick the one that helped?" XN-028 shows alpha=0.20 marginally helps Alarm (+1.2pp F1 ceiling) -- was that tested with LLM orientation? **Partly addressable: test LOCALE at alpha=0.10 on all networks, not just Asia, to show it is not cherry-picked.**

## Questions for the Copilot

1. **Where is the degree-1 analysis documented?** The checkpoint claims "DONE" with specific numbers (Asia 25pp gap, Alarm 17pp gap) but I cannot find any experiment note, analysis script, or raw data supporting these figures. What methodology produced these numbers? Can you point me to the file?

2. **Why did LOCALE Sachs F1 jump from 0.765 (XN-024) to 0.865 (XN-031)?** Both used the same pipeline (K=10, NCO, Max-2SAT, confidence reconciliation). XN-024 was single-seed (s42), XN-031 is 12-seed average. Is the average being pulled up by seeds where the PC skeleton is more favorable? Or did something else change?

3. **Was alpha=0.10 tested for LOCALE on all networks, or only Asia?** If alpha=0.10 helps Asia's skeleton, does it also change results on Insurance (stuck at 80.8% coverage regardless) or Alarm (coverage goes from 93.5% to 95.7%)? If only Asia uses alpha=0.10, the paper needs strong justification for why this is not selective reporting.

4. **What is the plan for addressing the MosaCD fidelity gap?** This is now the single largest threat to validity and has been flagged in two consecutive reviews. Is there a concrete plan -- (a) run with GPT-4o-mini API, (b) use a 128K open model, (c) write a sensitivity analysis? "NEEDS GPU" is not a plan.

5. **The NCO validation (XN-022) used seeds 42, 0, and 123. Were these the seeds before or after the bug fix?** XN-022 documents its own independent bug fix (line 31). But were the XN-022 results generated before or after the mve_insurance.py fix? If before, the NCO validation used the fixed nco_validation.py but still imported `sample_data` from the buggy mve_insurance.py. I verified in code that nco_validation.py passes `seed=seed` explicitly at line 36, so this should be correct regardless of when it ran -- but I want confirmation that the NCO results in XN-022 were generated from the fixed nco_validation.py, not from an earlier version.

6. **How many edges in each network's PC skeleton are covered by only one endpoint's ego-graph (i.e., one endpoint has degree < 2)?** The degree-1 vulnerability analysis supposedly answers this, but the numbers are undocumented. This directly determines how broadly the Asia-style failure mode applies.

7. **Why was Phase 5 (per-edge fallback) not re-evaluated as a mitigation for the degree-1 vulnerability?** XN-019 found it mixed ("helps Sachs +5.9pp and Child +4.0pp but hurts Alarm -4.7pp"), but those results predate the NCO pipeline and the corrected comparison. A targeted Phase 5 fallback only for degree-1 edges would be a focused intervention with low risk of the "correlated PE-ego errors" problem that caused Alarm to degrade.

## Addressable vs Structural

### Addressable
- **W1**: Run cross-model comparison or sensitivity analysis for MosaCD fidelity gap. This is the single most impactful experiment remaining.
- **W2**: Re-run disguised robustness with correct multi-seed protocol on all 5 networks.
- **W3**: Run reduced synthetic experiments (50-node ER, 2-3 densities, 3 seeds).
- **W4**: Document degree-1 analysis with a proper XN note and reproducible methodology.
- **W5**: Trace the Sachs LOCALE F1 improvement from XN-024 to XN-031.
- **W6**: Reframe F1 decomposition and safety valve as context rather than contributions.
- **W7**: Update tracker header timestamp.
- **W8**: Document or fill in missing seed 42 data.
- **W9**: Test alpha=0.10 across all networks for consistency.

### Structural
- **The method is simpler than proposed (H3, H4, H5 collapsed).** The paper cannot claim a 7-phase pipeline when Phases 3-6 are either no-ops, failed, or descoped. The actual method is: PC skeleton + ego-graph LLM queries + NCO Max-2SAT + confidence-weighted majority vote. This is a 3-step method. The contribution is accordingly thinner than the proposal envisioned.
- **The degree-1 vulnerability is inherent to the ego-graph design.** Any node with degree 1 in the skeleton gets single-endpoint coverage with no reconciliation. This is unfixable without a per-edge fallback mechanism (Phase 5), which was descoped and whose results were mixed (XN-019). Must be disclosed as a known limitation.
- **Single model family.** Ego-graph joint reasoning is demonstrated to be an emergent capability requiring 27B+ scale (XN-023). The paper cannot claim this is "model-agnostic" or "general" when it has been tested on exactly one model family and fails below 27B parameters.
- **All benchmarks are small BNLearn networks that may be contaminated in LLM training data.** Even with disguised variable names, structural patterns from these textbook graphs could be memorized. Without synthetic experiments, this is an irremovable concern.

## Overall Assessment

**The recommendation remains Weak Reject, consistent with RN-001.** The core findings (NCO, context efficiency, query savings) are genuine, robust, and worth publishing. But the comparison claim against MosaCD -- which is how the paper will be evaluated at a competitive venue -- has an unresolved confound that has been flagged for two consecutive reviews. The experimental evidence remains incomplete: no synthetic experiments, thin disguised robustness, Hepar2 absent from multi-seed, no cross-model validation.

**Progress since RN-001 is modest.** Of the three must-haves, one was partially addressed (degree-1 analysis, but undocumented) and two are completely unaddressed (MosaCD confound, disguised re-run). The checkpoint correctly identifies that the remaining items need GPU access. However, the copilot appears to have entered a waiting state ("Awaiting user for next steps") rather than executing the analytical items that do not need GPU (sensitivity analysis for MosaCD fidelity, documenting the degree-1 analysis, tracing the Sachs discrepancy, testing alpha consistency).

**To change my mind, the revision needs:**
1. **(Must-have, carried)** Close the MosaCD re-implementation confound -- cross-model comparison, sensitivity analysis, or fidelity validation.
2. **(Must-have, carried)** Re-run disguised robustness with correct multi-seed protocol.
3. **(Must-have, new)** Document the degree-1 analysis as a proper experiment note with methodology.
4. **(Should-have, carried)** At least a reduced synthetic experiment.
5. **(Should-have, carried)** Hepar2 in multi-seed.
6. **(Should-have, new)** Explain the Sachs F1 discrepancy between XN-024 and XN-031.

Items 1-2 remain showstoppers. Without them, the paper will be rejected at any serious causal discovery venue.

**The direction remains sound.** The NCO finding alone could be a solid workshop paper or short paper at CLeaR/UAI. For a main-track submission, close the evidence gaps. The longest pole is the MosaCD confound, which may require either API budget for GPT-4o-mini or a 128K-context open model.
