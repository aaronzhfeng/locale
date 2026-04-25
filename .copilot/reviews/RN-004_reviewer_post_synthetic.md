---
id: RN-004
source: reviewer
title: "Fourth adversarial review: synthetic ER results analyzed, graph-seed confound discovered"
date: 2026-03-28
dag_nodes: [E01, E03, I02, I03, A02, I11]
trigger: "pre-submission"
recommendation: "Borderline"
priority_issues: 5
---

## Per-Dimension Ratings

| Dimension | Score | Justification |
|---|---|---|
| Relevance | 3/4 | Unchanged. LLM-assisted causal discovery is an active area; MosaCD at ICLR 2026 confirms venue interest. |
| Novelty | 2/4 | Unchanged. NCO remains the strongest original element. Ego-graph batching is underexplored but not conceptually novel. The synthetic evidence adds a "when does it work" dimension but does not increase the novelty of the method itself. |
| Technical Quality | 3/4 | Upgraded from 2/4. The synthetic analysis (XN-037) is a genuine correction of my RN-003 finding. The 22-pair comparison with paired t-test is methodologically sound. However, I identify a critical graph-seed confound (see W1) that the analysis does not address. The BNLearn 11-network comparison remains the strongest evidence. |
| Presentation | 2/4 | Hub.md State of Knowledge is still stale (lists Hepar2, disguised, and synthetic as unresolved when all are now addressed). Tracker header still says "2026-03-11." The synthetic_er_summary.json contradicts the raw results (shows LOCALE=0.467 for 20n_15d_g0 when the actual phase3_results.json gives 0.600). These inconsistencies would confuse any external reader. |
| Reproducibility | 2/4 | Single model family. MosaCD re-implementation without public code. 5 of 27 MosaCD synthetic runs incomplete. Synthetic experiments use single data seed (data_seed=0) per graph configuration -- no data seed variance. |
| Reviewer Confidence | 4/4 | I independently verified XN-037's numbers against raw phase3_results.json and mosacd_results.json for 4 configurations (20n_15d_g0, 30n_15d_g0, 20n_20d_g2, 50n_15d_g0). All match. I computed per-graph-seed aggregates that XN-037 does not report, discovering the graph-seed confound. I confirmed the summary.json is stale and contradicts the raw results. |

## Overall Recommendation

**Borderline** -- upgraded from Weak Reject.

## Summary

LOCALE proposes ego-graph batching for LLM-assisted causal edge orientation, combining local CI constraints (NCO filtering) with Max-2SAT solving and confidence-weighted reconciliation. An expanded 11-network BNLearn comparison against a same-model MosaCD re-implementation shows 8W/2T/1L with Wilcoxon p=0.027 and mean +7.6pp F1. A new synthetic ER experiment (22 paired configurations, XN-037) shows LOCALE winning 14/22 with mean +14.3pp and paired t-test p=0.006, providing evidence that the advantage is not purely domain-knowledge-driven. The project also contributes the NCO finding (97.9% false collider rate) and context efficiency advantages.

## Previous Review Follow-Up (RN-003)

### RN-003 W1 (P1): Synthetic experiment results unanalyzed
**Status: ADDRESSED.**

This was the central finding of RN-003 and the reason for the Weak Reject. I found raw results on disk that the copilot had not analyzed and checked 4 configurations myself, finding MosaCD won 3/4. The copilot has now produced XN-037 documenting the full 22-pair comparison.

**My RN-003 finding was based on an unrepresentative 4-configuration sample.** I acknowledge this. The 4 configurations I checked (20n_15d_g0, 30n_20d_g0, 50n_20d_g0, 30n_30d_g0) are all graph seed g0, which I now demonstrate systematically favors MosaCD (see W1 below). Had I checked g1 or g2 configurations, I would have seen the opposite pattern. This is a lesson in the danger of small-n spot checks on high-variance data -- the same lesson the project learned with its original 4-seed comparison.

The copilot's correction is legitimate. LOCALE does win 14/22 on the full dataset. The p=0.006 paired t-test is valid. However, the graph-seed confound I discover in this review is a new concern that XN-037 does not address.

### RN-003 W2 (P1): LOCALE loses to published MosaCD on 9/10 networks
**Status: ACKNOWLEDGED but not resolved.**

This is a structural limitation. The fidelity gap table in XN-035 is transparently documented. LOCALE does lose to published MosaCD on most networks when MosaCD operates at its designed conditions (GPT-4o-mini, 128K context, n=20000). The paper must be framed as a same-model comparison, not a claim of beating MosaCD absolutely. This is a framing requirement, not additional experiments.

### RN-003 W3 (P1): Alarm s0 outlier uninvestigated
**Status: NOT ADDRESSED.**

Real F1=0.637, Disguised F1=0.901, delta=-26.4pp. No additional seeds, no edge-level analysis, no investigation conducted. Carried forward as W3.

### RN-003 W4 (P2): Hailfinder comparison irregularities
**Status: ACKNOWLEDGED but unchanged.**

Still n=2000, 3 seeds, massive context overflow. The Wilcoxon survives Hailfinder removal (p=0.039), which mitigates the concern. Carried as a disclosure requirement.

### RN-003 W5 (P2): 5 missing MosaCD synthetic runs
**Status: NOT ADDRESSED.**

Still missing. Carried forward.

### RN-003 W6 (P2): Hub.md and tracker stale
**Status: NOT ADDRESSED.**

Hub.md still lists synthetic experiments and disguised robustness as unresolved. Tracker still says 2026-03-11. Carried forward as W5.

### RN-003 W7 (P3): Wilcoxon heterogeneity caveats
**Status: NOT ADDRESSED.**

No change. Minor.

### RN-003 W8 (P3): Single model family
**Status: STRUCTURAL -- carried forward.**

## Strengths

- **S1: Synthetic ER experiment directly tests the key hypothesis and the analysis is methodologically sound.** 22 paired configurations, three node counts, three density levels, three graph seeds, both methods on identical graphs. Paired t-test (p=0.006) is appropriate. LOCALE mean 0.528 vs MosaCD 0.385 (+14.3pp). I verified the numbers against raw data files -- they are accurate. This is the single most important experiment the project has run, and it was motivated by RN-003's concerns. Credit for responsiveness.

- **S2: The 11-network BNLearn comparison remains the strongest empirical evidence.** 8W/2T/1L with Wilcoxon p=0.027 across heterogeneous networks. The per-network fidelity gap table (XN-035) is honest and transparent. This breadth is competitive for a workshop paper.

- **S3: The copilot acknowledged my RN-003 correction was based on a biased sample.** The 4 configs I checked were all g0, which systematically favors MosaCD. This is an important methodological lesson documented transparently.

- **S4: NCO, context efficiency, and degree-1 analysis remain robust (carried from prior reviews).** These are genuinely useful contributions that would survive any framing revision.

## Weaknesses

- **W1 (P1): The synthetic results exhibit extreme graph-seed dependence that the paired t-test does not account for, and that XN-037 does not report.**

    I computed per-graph-seed aggregates from XN-037's own table:

    | Graph seed | LOCALE wins | MosaCD wins | Mean delta | Interpretation |
    |------------|-------------|-------------|------------|----------------|
    | g0 (8 pairs) | 2 | 6 | -1.2pp | MosaCD slightly better |
    | g1 (7 pairs) | 6 | 1 | +15.0pp | LOCALE dominates |
    | g2 (7 pairs) | 6 | 1 | +31.4pp | LOCALE dominates |

    The "14/22 LOCALE wins" headline is driven almost entirely by g1 and g2 graph realizations. On g0 graphs, MosaCD wins 6/8 with a mean delta of approximately -1pp. The aggregate +14.3pp is the average of three very different regimes: {-1.2, +15.0, +31.4}.

    **Why this matters**: With only 3 graph seeds, the aggregate is dominated by which *graph topologies* the random seed happens to generate, not by systematic properties of the methods. The paired t-test across 22 observations treats each configuration as independent, but they are nested within 3 graph seeds. The correct statistical model is a mixed-effects analysis or a graph-seed-stratified test. If you average by graph seed first (the independent unit), the 3 data points are {-1.2, +15.0, +31.4} -- far too few for any meaningful test.

    **What might explain the pattern**: Graph seed g0 may generate topologies with more degree-1 nodes (favoring MosaCD's per-edge approach) or sparser local neighborhoods (less ego-graph context). Graph seeds g1 and g2 may generate denser local structures. Without characterizing the structural properties of each graph realization, we cannot know whether the LOCALE advantage is general or topology-dependent.

    **This is not necessarily fatal.** The direction of the effect (+14.3pp mean, 14/22 wins) is suggestive that LOCALE has an advantage on average. But the variance structure means the p=0.006 is likely inflated because the 22 observations are not independent -- they cluster within 3 graph seeds. The honest statement is: "On 2 of 3 graph topologies tested, LOCALE substantially outperforms MosaCD. On 1 of 3, MosaCD is slightly better." That is still positive evidence, but it is much weaker than "p=0.006 across 22 configurations."

    **Addressable**: Run more graph seeds (g3-g9 at minimum) to increase the number of independent graph topology samples. Report per-graph-seed aggregates. Use a mixed-effects model or bootstrap at the graph-seed level.

- **W2 (P1): Both methods are at near-random absolute performance on synthetic graphs, which limits the interpretive value of the comparison.**

    LOCALE mean F1=0.528, MosaCD mean F1=0.385. Neither method is doing well. For context:
    - A random orientation baseline would achieve ~50% accuracy on each edge, which translates to F1 around 0.50 when skeleton coverage is high.
    - LOCALE at 0.528 is barely above this random baseline.
    - MosaCD at 0.385 is *below* it, which means MosaCD is actively making things worse through its propagation procedure.

    The "LOCALE wins" narrative could equally be framed as "MosaCD's seeding+propagation pipeline catastrophically fails on anonymous variables, while LOCALE's local voting at least doesn't make things worse." I verified this: MosaCD's seed_accuracy on synthetic graphs ranges from 0.0 (zero valid seeds on 20n_15d_g2!) to 0.31, compared to 0.71-1.00 on BNLearn networks. MosaCD's propagation from bad seeds cascades errors.

    This means the comparison may be testing MosaCD's fragility to anonymous variables more than LOCALE's structural advantage. A fairer test would compare LOCALE against a simple majority-vote ego-graph baseline (no NCO, no Max-2SAT) on the same synthetic graphs to demonstrate that the pipeline components add value, not just that MosaCD fails.

    **Addressable**: Add a majority-vote ego-graph ablation on synthetic graphs. Report MosaCD seed_accuracy to explain *why* MosaCD fails. Reframe the comparison as "robustness to domain-knowledge absence" rather than "structural superiority."

- **W3 (P2): The Alarm s0 outlier (-26.4pp from variable names) remains uninvestigated after being flagged as P1 in RN-003.**

    XN-033: Alarm s0 Real F1=0.637, Disguised F1=0.901. This 26.4pp swing from variable names alone is the largest single-seed effect in the entire project. No edge-level analysis was conducted. No additional disguised seeds were run to assess reproducibility. The copilot's response to RN-003 addressed the synthetic experiments but ignored this issue entirely.

    If the Alarm s0 result is reproducible, it means that on some seeds the LLM's domain knowledge about alarm monitoring is actively harmful by 26pp. This has implications for how the paper should frame the role of domain knowledge. If it is a one-off outlier, that should be documented with evidence.

    **Addressable**: Run 6+ additional disguised Alarm seeds. Document which edges flip on s0.

- **W4 (P2): The synthetic experiments use a single data seed (data_seed=0) per graph configuration, providing no estimate of data-sampling variance.**

    Each of the 27 LOCALE configurations uses one data sample (n=10000, data_seed=0) from one random BN. There is no variance estimate from data resampling. The results could be sensitive to the specific data realization. Compare to the BNLearn experiments, which use 12 data seeds and report standard deviations.

    Combined with the graph-seed confound (W1), this means the synthetic results have two sources of unquantified variance: graph topology (partially addressed by 3 seeds, but with extreme dependence) and data realization (not addressed at all).

    **Addressable**: Run 3+ data seeds per graph configuration. Would increase the experiment count substantially but is standard practice.

- **W5 (P2): Hub.md State of Knowledge and tracker remain stale despite being flagged in RN-003 W6.**

    Hub.md "What's unresolved" still says:
    - "Hepar2: not in multi-seed comparison" -- addressed by XN-034
    - "Disguised robustness: only 2 networks, 1 seed" -- addressed by XN-033
    - "Synthetic experiments: proposal Section 5.5 untouched" -- addressed by XN-037

    Tracker says "Last updated: 2026-03-11" despite 17 days of subsequent work including the entire 11-network expansion, synthetic experiments, and disguised multi-seed.

    The synthetic_er_summary.json reports LOCALE F1=0.467 and MosaCD F1=0.467 for 20n_15d_g0, but the actual raw phase3_results.json shows correct=9/15 (F1=0.600) and mosacd_results.json shows F1=0.733. The summary was generated from a different (earlier) run and is misleading. It should either be regenerated from current data or deleted.

    **Addressable**: Update all three files.

- **W6 (P3): 5 of 27 MosaCD synthetic runs remain incomplete (carried from RN-003 W5).**

    The missing configurations (50n_20d_g1, 50n_20d_g2, 50n_30d_g0-g2) include both g0 (which favors MosaCD) and g1/g2 (which favor LOCALE). Their absence biases the 50n results. All 27 LOCALE configurations are complete but only 4/9 of the 50n MosaCD configurations are present, meaning the 50n comparison is particularly unreliable.

    **Addressable**: Complete the 5 runs.

- **W7 (P3): Single model family remains a structural limitation (carried from all prior reviews).**

    All results are Qwen3.5-27B-FP8. No testing on GPT-4, Claude, Llama. The 9B ablation (XN-023) shows ego-graph reasoning requires 27B+ within this family. Claims must be scoped accordingly.

    **Structural.**

## Questions for the Copilot

1. **Are you aware of the graph-seed dependence in the synthetic results?** On g0 graphs, MosaCD wins 6/8 (mean delta -1.2pp). On g1/g2, LOCALE wins 12/14 (mean deltas +15pp and +31pp). What structural properties of g0 graphs favor MosaCD? Have you computed node degree distributions, number of degree-1 nodes, or average local clustering for each graph seed?

2. **What does a random orientation baseline achieve on these synthetic graphs?** If LOCALE's F1=0.528 on synthetic graphs and a random baseline would get ~0.50, the signal above random is approximately 3pp. Is this within the noise floor?

3. **Why does MosaCD's seeding process catastrophically fail on anonymous variables?** Seed accuracy drops from 71-100% (BNLearn) to 0-31% (synthetic). Is this because MosaCD's seeding prompt relies on variable semantics? If so, the synthetic comparison is testing MosaCD's sensitivity to variable names, not the methods' structural properties.

4. **Why was the Alarm s0 outlier not investigated?** It was explicitly flagged as P1 in RN-003 W3. The copilot addressed the synthetic experiment concern but ignored this one. What is the prioritization logic?

5. **The synthetic_er_summary.json contradicts the raw data.** It shows LOCALE F1=0.467 for 20n_15d_g0, but phase3_results.json shows accuracy=0.600 (which corresponds to F1=0.600 at 100% skeleton coverage). These appear to be from different runs. Which is authoritative? Was LOCALE re-run on this configuration?

6. **How many of the 22 paired configurations have skeleton coverage below 100%?** If LOCALE's skeleton has missing edges on some synthetic graphs, the F1 computation includes those as FN, penalizing LOCALE. Does MosaCD use the same skeleton? If not, the comparison is confounded.

7. **Have you computed the paired t-test excluding g0 and then including only g0?** The per-seed results I computed suggest p>>0.05 for g0 alone and p<<0.01 for g1/g2. If true, the aggregate p=0.006 is driven by 14 of the 22 observations, not by a consistent effect across all configurations.

## Addressable vs Structural

### Addressable (before submission -- high priority)
- **W1**: Run more graph seeds (g3-g9) to increase the number of independent topology samples. Report per-graph-seed aggregates and use a mixed-effects model or bootstrap. This is the most important remaining experiment.
- **W2**: Add a majority-vote ego-graph ablation on synthetic graphs. Report MosaCD seed_accuracy to explain the mechanism of MosaCD's failure. Reframe around robustness rather than structural superiority.
- **W3**: Run 6+ disguised Alarm seeds. Investigate which edges flip on s0.
- **W5**: Update hub.md, tracker, and delete/regenerate the stale summary.json.
- **W6**: Complete the 5 missing MosaCD runs.

### Addressable (would strengthen but not required for workshop)
- **W4**: Multiple data seeds per graph configuration.
- Per-network Hailfinder disclosure (already in XN-035, needs to transfer to paper).

### Structural (cannot be fixed)
- **W7**: Single model family.
- The MosaCD re-implementation gap on large networks.
- Absolute performance on synthetic graphs is near-random -- the relative comparison is valid but the absolute numbers are weak.

## Overall Assessment

**I am upgrading from Weak Reject to Borderline.** The synthetic experiment analysis (XN-037) is a substantive correction of my RN-003 finding. I was wrong about the direction of the synthetic results: LOCALE does win 14/22 with a meaningful aggregate advantage. The copilot's criticism that my 4-config spot check was unrepresentative is factually correct.

However, I have identified a new concern that was not visible in RN-003: the extreme graph-seed dependence. The "p=0.006" headline treats 22 configurations as independent observations, but they cluster into 3 graph topologies with dramatically different outcomes. This is a classic pseudoreplication problem. The real sample size for the synthetic experiment is 3 (graph seeds), not 22 (configurations). With n=3, no statistical test is meaningful.

**The overall evidence is now genuinely mixed, in an interesting way:**

1. **BNLearn (strong)**: 8W/2T/1L, Wilcoxon p=0.027, mean +7.6pp across 11 heterogeneous networks. Legitimate same-model advantage. But LOCALE loses to published MosaCD on 9/10 networks.

2. **Synthetic (suggestive but unreliable)**: 14/22 wins, mean +14.3pp, but with extreme graph-seed dependence (g0 favors MosaCD, g1/g2 favor LOCALE). Near-random absolute performance for both methods. MosaCD's seeding process catastrophically fails on anonymous variables, confounding the comparison.

3. **Domain knowledge (nuanced)**: Network-dependent. Domain knowledge helps on Insurance and Sachs, hurts on Alarm, with a 26pp unexplained outlier on Alarm s0. Not investigated despite being flagged.

4. **NCO + context efficiency (robust)**: These findings are solid regardless of the synthetic results.

**To reach Weak Accept, the revision needs:**

1. **(Must-have)** More graph seeds for synthetic experiments (g3-g9 minimum). Report per-graph-seed aggregates. If the graph-seed dependence is confirmed with more data (i.e., some topologies favor MosaCD), the paper must characterize *which* topologies and *why*. This is actually more interesting than a uniform advantage.

2. **(Must-have)** MosaCD seed_accuracy reported for synthetic graphs, explaining the mechanism of MosaCD's collapse on anonymous variables. The paper should argue whether this is a feature of the comparison or a confound.

3. **(Must-have)** Honest framing of the MosaCD re-implementation gap. The paper cannot claim to "beat MosaCD" without prominent caveat.

4. **(Should-have)** Alarm s0 investigation. Either explain the 26pp swing or run enough seeds to determine whether it is reproducible.

5. **(Should-have)** Update all stale documentation.

**For a CLeaR workshop paper**: The BNLearn evidence (8W/2T/1L) plus NCO is sufficient with honest framing. The synthetic results, even with the graph-seed caveat, are at worst neutral -- they show LOCALE does not collapse on novel graphs and maintains a directional advantage. Present them with the graph-seed analysis as a limitation.

**For a UAI main-track paper**: The graph-seed confound must be resolved with more data. The near-random absolute performance on synthetic graphs is a concern that should be investigated (is this a model limitation? a fundamental difficulty of ER graphs? an insufficient prompt design?). The Alarm s0 outlier must be explained. The MosaCD re-implementation gap should be positioned clearly as a limitation, not hidden.

**The direction is sound.** The ego-graph approach has genuine advantages (context efficiency, query savings, robustness to context overflow). The NCO finding is independently valuable. The question is whether the orientation quality advantage is real or an artifact of the comparison conditions. More graph seeds will settle this definitively.
