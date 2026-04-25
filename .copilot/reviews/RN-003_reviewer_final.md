---
id: RN-003
source: reviewer
title: "Final adversarial review: 11-network expansion, synthetic results discovery, pre-submission gate"
date: 2026-03-27
dag_nodes: [E01, E03, I02, I03, A02, I11]
trigger: "pre-submission"
recommendation: "Weak Reject"
priority_issues: 6
---

## Per-Dimension Ratings

| Dimension | Score | Justification |
|---|---|---|
| Relevance | 3/4 | Unchanged from prior reviews. LLM-assisted causal discovery is active; MosaCD at ICLR 2026 confirms venue interest. The ego-graph operating point fills a real gap. |
| Novelty | 2/4 | NCO remains the strongest original element -- a diagnostic finding about PC CI test failure modes, actionable and method-agnostic. Ego-graph batching is underexplored but not conceptually novel. Method is simpler than proposed (3 of 5 hypotheses collapsed). SNOE solves the same CPDAG orientation problem with theoretical guarantees LOCALE lacks. |
| Technical Quality | 2/4 | Downgraded from the previous draft's 3/4 after independently analyzing the synthetic experiment results. The 11-network BNLearn comparison (8W/2T/1L) is the strongest evidence produced -- but the synthetic ER results (which exist on disk but have not been analyzed or documented) show both methods at coin-flip performance on novel graphs, with MosaCD winning on the cases I checked in detail. This evidence directly undermines the narrative that LOCALE's advantage is structural rather than domain-knowledge-dependent. The paper's core comparison is against a degraded re-implementation of MosaCD (31.5pp gap on Hepar2). |
| Presentation | 2/4 | Hub.md "What's unresolved" section is stale (still lists Hepar2 and disguised as unresolved). Tracker header still says "Last updated: 2026-03-11." Synthetic results exist on disk but have no experiment note. The copilot appears to have not analyzed the synthetic results despite claiming they were "running." |
| Reproducibility | 2/4 | Single model family. MosaCD re-implementation without public code. Hailfinder at n=2000 vs n=10000 for other networks. New networks at 4 seeds vs 12 for original 5. 5 of 27 MosaCD synthetic runs incomplete (GPU died). |
| Reviewer Confidence | 4/4 | I have read all 36 experiment notes, 8 literature notes, 2 decision memos, the full proposal, all prior reviews (RN-001, RN-002), the research log through LOG-2026-03-27-41, and -- critically -- the raw synthetic experiment results that the copilot has not yet analyzed. I independently verified the Wilcoxon test arithmetic, read 4 LOCALE phase3 + MosaCD result pairs from synthetic experiments, computed aggregate LOCALE phase2 accuracy across 27 synthetic configurations, and checked the XN-035 file for Hailfinder inclusion. |

## Overall Recommendation

**Weak Reject** -- contra the previous draft's Borderline. The 11-network BNLearn expansion is genuine progress, but the synthetic experiment results -- which exist on disk and which I read independently -- reveal that LOCALE performs at approximately coin-flip accuracy (mean phase2 accuracy ~51%) on novel ER graphs where domain knowledge is absent. MosaCD also degrades but appears to retain a small advantage on the synthetic configurations I checked. This fundamentally changes the story: LOCALE's BNLearn advantage may be substantially attributable to the LLM leveraging domain knowledge about textbook networks, not to the ego-graph architecture's structural superiority. The disguised robustness test (XN-033) showed that domain knowledge effects are network-dependent and can swing results by 26pp -- the synthetic evidence suggests this concern is not academic.

## Summary

LOCALE proposes ego-graph batching for LLM-assisted causal edge orientation, combining local CI constraints (NCO filtering) with Max-2SAT solving and confidence-weighted reconciliation. An expanded 11-network BNLearn comparison against a same-model MosaCD re-implementation shows 8W/2T/1L with Wilcoxon p=0.027 and mean +7.6pp F1. Synthetic ER experiments (27 LOCALE configurations, 22 MosaCD configurations, results on disk but unanalyzed) show both methods degrading to near-random performance on novel graphs, with preliminary evidence that MosaCD retains a small edge. The strongest standalone contributions remain NCO (97.9% false-collider rate) and context efficiency (LOCALE works at 2048 tokens where MosaCD breaks).

## Previous Review Follow-Up (RN-001 and RN-002)

### Must-Have #1 (W1/P1): MosaCD re-implementation confound
**Status: PARTIALLY ADDRESSED -- repositioned but not eliminated.**

The strategy shifted to expanding across all 11 MosaCD benchmarks under the same conditions. This is legitimate: 8W/2T/1L is hard to attribute entirely to a re-implementation artifact. XN-035 now includes a per-network fidelity gap table with honest interpretation. Credit for transparency.

However, the fidelity gap on large networks is devastating:
- Hepar2: our MosaCD 0.405 vs published 0.72 (gap: **31.5pp**). LOCALE 0.565 -- still loses to published MosaCD by 15.5pp.
- Win95pts: our MosaCD 0.573 vs published 0.81 (gap: **23.7pp**). LOCALE 0.694 -- loses to published MosaCD by 6.6pp.
- Alarm: our MosaCD 0.801 vs published 0.93 (gap: **12.9pp**). LOCALE 0.841 -- loses to published MosaCD by 8.9pp.

LOCALE wins against the published MosaCD on only 2 of 10 reported networks: Hailfinder (+12.6pp) and Insurance (+6.5pp). The "8 wins" narrative is only valid within the same-model comparison, which disadvantages MosaCD by constraining it to 4096-token context when it was designed for 128K. The paper needs to be explicit about this.

### Must-Have #2 (W4/P2): Disguised robustness re-run
**Status: ADDRESSED -- but the result complicates the story rather than resolving it.**

XN-033 is properly executed: 3 networks, 3 seeds each. The finding that domain knowledge effects are network-dependent is a genuine scientific contribution. However, the Alarm s0 outlier (Real F1=0.637 vs Disguised F1=0.901, delta -26.4pp from real names alone) remains uninvestigated and unexplained.

### Must-Have #3 (W5/P2): Degree-1 vulnerability analysis
**Status: ADDRESSED.**

XN-032 is clean, properly documented, and explanatory. The single-endpoint accuracy predictor maps exactly onto network-level performance. Resolved.

### Should-Have #4: Synthetic experiments
**Status: PARTIALLY RUN BUT NOT ANALYZED OR DOCUMENTED.**

This is the critical new finding of this review. The dispatch prompt says "Synthetic ER experiments running (27 graphs x 2 methods) -- results pending." I checked the filesystem and found:
- 27 LOCALE configurations complete (3 node counts x 3 densities x 3 graph seeds): `experiments/results/synthetic_er_{20,30,50}n_{15,20,30}d_g{0,1,2}/`
- 22 of 27 MosaCD configurations complete; 5 missing (50n_20d_g{1,2} and 50n_30d_g{0,1,2} -- GPU died before completion)
- Summary file (`synthetic_er_summary.json`) is stale: covers only 1 configuration (20n, 1.5d, g0) and was generated before the LOCALE run finished (timestamp mismatch).

**No experiment note (XN-037 or similar) exists for the synthetic results. No analysis has been conducted. The copilot appears to have launched the runs but not read the results.**

I read the results. They are not favorable (see W1 below).

### Should-Have #5: Hepar2 multi-seed
**Status: ADDRESSED.**

XN-034: 4 seeds, +16.0pp, p=0.013, d=3.08. Convincing under same-model conditions. Caveat about published MosaCD fidelity gap applies (LOCALE 0.565 vs published MosaCD 0.72).

### RN-002 Should-Have #6: Sachs F1 discrepancy
**Status: NOT ADDRESSED -- but demoted to P3.**

LOCALE Sachs F1 jumped from 0.765 (XN-024, s42) to 0.865 (XN-031, 12-seed mean). The 12-seed aggregate is now authoritative.

## Strengths

- **S1: 11-network BNLearn breadth is the project's most significant empirical advance.** Covering all MosaCD benchmark networks under matched conditions was the right strategic move. The 8W/2T/1L record across heterogeneous networks (5 to 76 nodes) with Wilcoxon p=0.027 is the strongest evidence LOCALE has produced. XN-035 now includes a per-network fidelity gap table with honest framing ("LOCALE wins against a context-constrained MosaCD re-implementation"). I independently verified the Wilcoxon arithmetic: W=4 on 9 non-tied observations gives p=0.027 two-tailed. Correct.

- **S2: Disguised robustness finding (XN-033) is publishable content.** The network-dependent domain knowledge effect is more interesting than the original "LOCALE is domain-robust" story. The finding that Alarm real names *hurt* by 10.3pp on average (with a catastrophic s0 outlier) is a genuine empirical contribution about how LLMs interact with variable semantics in causal reasoning.

- **S3: NCO finding is robust and independently valuable (carried from all prior reviews).** 97.9% false-collider rate across 944 errors, 6 networks, 7 sample sizes. Sample-size trajectory (92.6% at n=1000, 100% at n>=5000) adds mechanistic depth. Actionable by any method using PC-family CI constraints. This is the paper's strongest original contribution.

- **S4: Degree-1 analysis (XN-032) is clean and predictive.** Single-endpoint accuracy maps exactly onto network-level performance. Gives the method an interpretable diagnostic. Well-documented.

- **S5: Context efficiency is a genuine architectural advantage (carried from prior reviews).** XN-029's analysis is thorough. Ego-graph prompts fit within 4096 tokens on 56-node networks where MosaCD's chain-based templates overflow. This is a real deployment advantage that scales with network size.

## Weaknesses

- **W1 (P1): Synthetic experiment results exist on disk, are unanalyzed, and show LOCALE at near-coin-flip performance on novel graphs -- this is the single most damaging evidence against the paper's thesis.**

    I read the raw results from `experiments/results/synthetic_er_*/`. The copilot launched 27 LOCALE configurations (20/30/50 nodes, density 1.5/2.0/3.0, 3 graph seeds each) and 22 MosaCD configurations (5 incomplete -- GPU died). The results are complete on disk but have not been documented in any experiment note or analyzed in any log entry.

    **LOCALE phase2 accuracy across all 27 configurations**: range 44.4% to 58.2%, mean approximately 51%. This is coin-flip performance. The reconciliation (phase3) improves it somewhat -- on the configurations I checked in detail, phase3 accuracy ranged from 37.5% to 60.0%. These are essentially random orientations.

    **MosaCD F1 across 22 complete configurations**: range 0.156 to 0.733, mean approximately 0.38.

    **Direct comparisons I verified** (LOCALE phase3 accuracy vs MosaCD F1):
    - 20n_15d_g0: LOCALE 60.0% vs MosaCD 73.3% -- **MosaCD wins**
    - 30n_20d_g0: LOCALE 37.5% vs MosaCD 44.0% -- **MosaCD wins**
    - 50n_20d_g0: LOCALE 42.1% vs MosaCD 51.7% -- **MosaCD wins**
    - 30n_30d_g0: LOCALE 50.0% vs MosaCD 48.8% -- **LOCALE wins** (barely, within noise)

    On the 4 configurations I checked, MosaCD wins 3/4. Both methods are terrible, but MosaCD's per-edge approach appears to degrade less catastrophically on novel graphs than LOCALE's ego-graph approach.

    **Why this is devastating**: The paper's narrative is that ego-graph batching provides a structural advantage for orientation quality. The synthetic results suggest the opposite: on graphs where domain knowledge is absent (anonymous X_0, X_1, ... variable names), the structural advantage evaporates. The BNLearn "8W/2T/1L" result may be substantially driven by the LLM leveraging domain knowledge about textbook causal networks -- precisely the concern that synthetic experiments were designed to test.

    This combines with XN-033's finding that domain knowledge effects swing results by up to 26pp (Alarm s0). The disguised robustness test showed that anonymizing *variable names* on *BNLearn graphs* only partially controls for domain knowledge -- the LLM may still recognize structural patterns from these well-known textbook graphs even without variable names. Synthetic ER graphs are the only way to test truly novel structures.

    **This is not addressable through framing alone.** The paper must either (a) present the synthetic results honestly and scope claims to "LOCALE works when LLMs have relevant domain priors," (b) demonstrate that a model-agnostic mechanism (not domain knowledge) explains the BNLearn advantage, or (c) show that synthetic performance improves with a simple fix (e.g., better prompting). The current evidence supports interpretation (a).

- **W2 (P1): LOCALE loses to published MosaCD on 8 of 10 networks where published numbers are available.**

    From XN-035's own fidelity gap table:

    | Network | LOCALE F1 | Published MosaCD F1 | LOCALE vs Published |
    |---------|-----------|---------------------|---------------------|
    | Hepar2 | 0.565 | ~0.72 | LOSE by 15.5pp |
    | Win95pts | 0.694 | ~0.81 | LOSE by 11.6pp |
    | Alarm | 0.841 | ~0.93 | LOSE by 8.9pp |
    | Child | 0.882 | ~0.90 | LOSE by 1.8pp |
    | Mildew | 0.859 | ~0.90 | LOSE by 4.1pp |
    | Asia | 0.900 | ~0.93 | LOSE by 3.0pp |
    | Cancer | 0.964 | ~1.00 | LOSE by 3.6pp |
    | Water | 0.579 | ~0.59 | LOSE by 1.1pp |
    | Hailfinder | 0.616 | ~0.49 | **WIN** by 12.6pp |
    | Insurance | 0.845 | ~0.87 | LOSE by 2.5pp |

    Wait -- I need to recompute Insurance. Published MosaCD Insurance = 0.87; LOCALE = 0.845. That's a loss. Let me recheck XN-035.

    From XN-035: Published MosaCD Insurance = 0.87, Our MosaCD = 0.757, LOCALE = 0.845. So LOCALE actually *loses* to published MosaCD by 2.5pp on Insurance too.

    **LOCALE loses to published MosaCD on 9 of 10 networks.** The only win is Hailfinder, which is the network where (a) n=2000 instead of n=10000, (b) only 3 paired seeds, and (c) MosaCD is massively context-overflow-degraded at 4096 tokens on a 56-node network.

    The "8W/2T/1L" headline is valid only as "LOCALE beats a same-model, 4096-context re-implementation of MosaCD." But even Hailfinder is questionable since published MosaCD only gets 0.49 (with 128K context + n=20000) -- LOCALE's 0.616 at n=2000 may not hold at n=10000 with a better skeleton.

    The paper cannot claim to "beat MosaCD." It can claim to "beat a same-model re-implementation" while being transparent that this re-implementation operates far below published performance on large networks. **This is addressable through honest framing but requires very careful writing.**

- **W3 (P1): The Alarm s0 outlier (-26.4pp from variable names alone) is unexplained and uninvestigated.**

    XN-033 reports Alarm s0: Real F1=0.637 vs Disguised F1=0.901. On the same skeleton, same data, same model -- the only difference is variable names. The LLM correctly orients many more edges when it does *not* know the variable names than when it does.

    This is not a marginal effect. This is a 26.4pp swing on a single seed. It means the LLM has strong, systematically incorrect causal priors about the Alarm monitoring domain that override its structural reasoning when real variable names are present.

    No investigation was conducted into which edges flip. No additional seeds were run to test reproducibility. The XN-031 12-seed Alarm mean is 0.841 +/- 0.070 (real names). But if s0 gets 0.637, that is 2.9 standard deviations below the mean -- either it is a genuine heavy-tailed outlier or the variance estimate from 12 seeds is unreliable.

    **The paper must either (a) investigate which edges flip and why, documenting the LLM's incorrect domain priors, or (b) run additional disguised seeds to determine whether this is reproducible. If the Alarm performance distribution is heavy-tailed (some seeds catastrophically affected by domain priors), reporting mean +/- std is misleading.** Addressable with modest additional compute.

- **W4 (P2): Hailfinder comparison has four compounding irregularities that inflate the headline.**

    (a) **n=2000 vs n=10000**: Skeleton quality is lower, potentially favoring the method that is less skeleton-sensitive. (b) **3 paired seeds**: n=3 gives wide CIs and high false-positive risk. (c) **Massive MosaCD context overflow**: On a 56-node network at 4096 tokens, MosaCD's chain-based templates are catastrophically degraded -- the Hailfinder "win" is primarily a context efficiency advantage, not an orientation quality advantage. (d) **Published MosaCD Hailfinder = 0.49**, which is below LOCALE's 0.616 -- but published MosaCD used n=20000 and 128K context. At n=2000 the skeleton is much worse.

    If Hailfinder is removed from the Wilcoxon test, the result is 7W/2T/1L on 8 non-tied observations, W=3, p=0.039 (still significant). So the aggregate result does not hinge on Hailfinder. But the paper must be transparent about why Hailfinder conditions differ and that the context overflow is the primary factor. **Addressable through disclosure.**

- **W5 (P2): 5 of 27 MosaCD synthetic runs are incomplete -- the comparison is unbalanced.**

    MosaCD results for 50n_20d_g{1,2} and 50n_30d_g{0,1,2} have config files but no results (GPU died). These are precisely the largest and densest graphs -- the configurations where context overflow would most disadvantage MosaCD. The synthetic comparison is biased toward smaller graphs where context overflow is less severe. If the 50-node dense-graph results are completed and LOCALE loses on those too, the synthetic evidence against LOCALE's structural claims becomes even stronger. If LOCALE wins on those, the picture changes. Either way, incomplete results cannot be ignored. **Addressable: complete the 5 missing runs.**

- **W6 (P2): Hub.md State of Knowledge is stale; tracker header says "Last updated: 2026-03-11."**

    Hub.md still lists "Hepar2: not in multi-seed comparison" (resolved by XN-034), "Disguised robustness: only 2 networks, 1 seed" (resolved by XN-033), and "Synthetic experiments: proposal Section 5.5 untouched" (experiments ran, results on disk). The tracker header says 2026-03-11 despite substantial work through 2026-03-27. A reviewer reading hub.md as an entry point gets a stale picture of the project. **Addressable: update hub.md and tracker.**

- **W7 (P3): The Wilcoxon test aggregates heterogeneous observations.**

    The p=0.027 Wilcoxon test treats all 11 BNLearn networks as exchangeable. They are not: seed counts differ (3/4/12), sample sizes differ (2000/10000), alpha differs (0.10 for Asia, 0.05 for rest). The directional evidence (8W/2T/1L) is compelling without any test. The paper should present the Wilcoxon with explicit caveats about heterogeneity or replace it with a bootstrap CI on the mean delta. **Addressable through better statistical reporting.**

- **W8 (P3): Single model family (Qwen3.5-27B) is a structural limitation.**

    Carried from all prior reviews. The 9B ablation (XN-023) shows ego-graph reasoning requires 27B+ on this family. No testing on GPT-4, Claude, Llama, or other families. All claims must be scoped to "Qwen3.5-27B-FP8." **Structural.**

## Questions for the Copilot

1. **Have you read the synthetic experiment results?** Raw results exist in `experiments/results/synthetic_er_*/` for 27 LOCALE and 22 MosaCD configurations. The summary.json is stale (covers 1 config, generated before LOCALE finished). LOCALE phase2 accuracy averages ~51% across all 27 configurations. On the 4 configurations I compared in detail, MosaCD wins 3/4. What is your assessment of these results, and why were they not documented in an experiment note?

2. **What is the LOCALE vs MosaCD comparison on all 22 matched synthetic configurations?** I checked 4 in detail. Please compute the full 22-pair comparison (LOCALE phase3 accuracy vs MosaCD F1) and report the W/T/L record. This is the most important experiment result for the paper's claims.

3. **Is the BNLearn advantage driven by domain knowledge?** The synthetic results show near-coin-flip performance. The disguised robustness test shows variable-name effects up to 26pp. The BNLearn benchmark networks are all in the LLM's training data. Together, these three pieces of evidence suggest LOCALE's advantage on BNLearn networks may be primarily domain-knowledge-driven, not architecturally structural. What is the copilot's counterargument? What specific evidence supports the structural interpretation over the domain-knowledge interpretation?

4. **What happens to the Alarm s0 outlier?** Real F1=0.637, Disguised F1=0.901 -- a 26.4pp swing from variable names alone on the same data and skeleton. Which edges flip? Is this because the LLM has strong incorrect beliefs about alarm monitoring causality that override structural reasoning? Can you run 6 additional disguised Alarm seeds (s3-s8) to assess reproducibility?

5. **Why are 5 MosaCD synthetic runs incomplete?** The 50n_20d and 50n_30d configurations are the most informative -- they test whether LOCALE's advantage holds at the scale where context overflow most disadvantages MosaCD. Are these recoverable?

6. **On the synthetic ER graphs, does the NCO constraint still help?** Phase2 accuracy is ~51% on synthetic graphs vs ~85-100% on BNLearn networks. Is the NCO constraint doing anything useful on novel graphs, or does it become inert because the CI tests produce different error patterns?

7. **The synthetic_er_summary.json shows LOCALE F1=0.467 and MosaCD F1=0.467 for the single summarized configuration (20n, 1.5d, g0). But the raw mosacd_results.json for that same configuration shows MosaCD F1=0.733. What explains this discrepancy?** The timestamp shows the summary was generated before the LOCALE run completed. Is the summary valid, or should it be regenerated?

## Addressable vs Structural

### Addressable (before submission)
- **W1 (partial)**: Analyze the existing synthetic results. Write XN-037 documenting the full 22-configuration LOCALE vs MosaCD comparison. Complete the 5 missing MosaCD runs if possible. This is the most urgent experiment analysis remaining.
- **W2**: Write the per-network fidelity gap table as a separate section in the paper, with honest framing: "same-model comparison, not a claim against published MosaCD." XN-035 already has this table -- it needs to be prominently positioned, not buried.
- **W3**: Investigate the Alarm s0 outlier. Document which edges flip. Run 6 additional disguised Alarm seeds.
- **W4**: Document Hailfinder irregularities explicitly (n=2000, 3 seeds, context-overflow attribution). The Wilcoxon result survives Hailfinder's removal (p=0.039).
- **W5**: Complete the 5 missing MosaCD synthetic runs.
- **W6**: Update hub.md and tracker.
- **W7**: Add Wilcoxon heterogeneity caveats or use bootstrap CI.

### Addressable (would significantly strengthen)
- Extend disguised testing to Win95pts and Hepar2.
- Investigate *why* both methods fail on synthetic graphs: is it domain knowledge absence, structural difficulty of ER graphs, or model limitations with anonymous variables?

### Structural (cannot be fixed for this submission)
- **W1 (core)**: If LOCALE's advantage is primarily domain-knowledge-driven (BNLearn advantage + synthetic coin-flip), the paper's thesis must change from "ego-graph batching is structurally superior" to "ego-graph batching is effective when LLMs have relevant domain priors." This is a narrative redesign, not more experiments.
- **W2**: The MosaCD re-implementation gap on large networks may be irreducible without 128K-context model access. Honest framing acknowledges this but does not eliminate it.
- **W8**: Single model family. Claims limited to Qwen3.5-27B-FP8.
- **Method simplicity**: The actual pipeline is 3-4 steps (PC skeleton + ego-graph LLM queries + NCO Max-2SAT + confidence reconciliation). Phases 3-6 from the proposal either failed or were no-ops. The contribution is thinner than proposed.

## Overall Assessment

**I am maintaining Weak Reject, downgrading from the previous draft's Borderline.** The reason is the synthetic experiment results.

The previous draft of RN-003 (which I am overwriting) did not have access to the synthetic results because they were "pending." I found them on disk -- 27 LOCALE configurations and 22 MosaCD configurations, raw results complete but unanalyzed. The results are not favorable: LOCALE averages ~51% phase2 accuracy on novel ER graphs (coin-flip), and MosaCD wins 3 of the 4 configurations I checked in detail.

This changes the paper's evidential landscape fundamentally. The BNLearn "8W/2T/1L" result is a legitimate empirical finding, but it exists in a context where:
1. Both methods collapse to near-random on novel graphs (synthetic evidence)
2. Domain knowledge effects can swing BNLearn results by 26pp (Alarm s0 disguised)
3. LOCALE loses to published MosaCD on 9 of 10 networks when MosaCD uses its designed operating conditions

The most parsimonious explanation consistent with all the evidence is: **LOCALE's advantage on BNLearn networks is substantially driven by the LLM leveraging domain knowledge about well-known textbook causal networks, with the ego-graph format being a more effective vehicle for domain priors than per-edge queries.** This is still a publishable finding -- but it is a very different paper than "ego-graph batching is structurally superior for causal edge orientation."

**To change my mind, the revision needs:**
1. **(Must-have)** Full analysis and documentation of synthetic experiment results. If LOCALE loses to MosaCD on most synthetic configurations, the paper must reframe around domain-knowledge interaction, not structural superiority.
2. **(Must-have)** Honest framing of the MosaCD re-implementation gap (XN-035 has the table -- but the paper must lead with this caveat, not bury it).
3. **(Must-have)** Investigation of the Alarm s0 outlier and its implications for result reliability.
4. **(Should-have)** Complete the 5 missing MosaCD synthetic runs and compute the full W/T/L record on all 27 configurations.
5. **(Should-have)** Disgused testing on Win95pts and Hepar2 to assess domain-knowledge dependence on large-network wins.

**The direction remains worth pursuing.** The NCO finding is robust, the context efficiency advantage is real, and the query cost savings are consistent. The disguised robustness finding about network-dependent domain knowledge interaction is itself a novel contribution. But the paper must be reframed: LOCALE is an ego-graph orientation module that is effective when LLMs have relevant domain priors, and it provides context efficiency and query cost advantages regardless. Claiming structural superiority is overclaiming given the synthetic evidence.

**For a workshop paper at CLeaR**: Fix W2 (fidelity framing), W3 (Alarm outlier), W6 (documentation), and present the synthetic results honestly as a known limitation. The BNLearn 8W/2T/1L with the NCO contribution makes a solid workshop paper.

**For a main-track submission at UAI/CLeaR**: All of the above plus a coherent narrative that accounts for the domain-knowledge dependence and positions the synthetic results as evidence about *when* ego-graph batching works (with domain priors) vs when it does not (without). This would be a stronger and more honest paper than claiming unconditional structural superiority.
