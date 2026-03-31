---
id: RN-005
source: reviewer
title: "Final adversarial review: Weak Accept for CLeaR workshop, not ready for UAI main track"
date: 2026-03-29
dag_nodes: [E01, E03, I02, I03, A02, I11]
trigger: "pre-submission"
recommendation: "Weak Accept"
priority_issues: 4
---

## Per-Dimension Ratings

| Dimension | Score | Justification |
|---|---|---|
| Relevance | 3/4 | LLM-assisted causal discovery is timely. MosaCD at ICLR 2026 confirms venue interest. The ego-graph operating point fills a genuine gap between per-edge and whole-graph approaches. |
| Novelty | 2/4 | NCO (non-collider-only constraints) is a genuine insight. Ego-graph batching for edge orientation is underexplored but conceptually incremental. The composition is useful engineering, not a conceptual breakthrough. Sufficient for workshop, borderline for main track. |
| Technical Quality | 3/4 | Upgraded from RN-004's 3/4. The 10-seed synthetic expansion properly addresses pseudoreplication. 11-network BNLearn comparison is thorough. Statistical analysis is appropriate (Wilcoxon signed-rank at graph-seed level). Remaining concerns are interpretive rather than methodological. |
| Presentation | 2/4 | Hub.md State of Knowledge, tracker, and summary.json are all still partially stale. The experiment notes themselves are well-written and honest. Paper-readiness depends on framing discipline that has not been demonstrated in internal docs. |
| Reproducibility | 2/4 | Single model family (Qwen-27B). MosaCD re-implementation without public code. Single data seed on all synthetic experiments. These are disclosed but limit external reproducibility. |
| Reviewer Confidence | 4/4 | Fifth review of this project. I have independently verified numbers against raw JSON files across all major experiment batches (BNLearn, synthetic g0-g9, disguised). I computed per-seed aggregates, identified the original pseudoreplication confound, and tracked its resolution. |

## Overall Recommendation

**Weak Accept** -- upgraded from Borderline. Ready for CLeaR workshop submission with specific framing requirements. Not ready for UAI main track without additional work.

## Summary

LOCALE proposes ego-graph batching for LLM-assisted causal edge orientation, combining local CI constraints (NCO filtering), Max-2SAT solving, and confidence-weighted reconciliation. Against a same-model MosaCD re-implementation: (1) 11 BNLearn networks show 8W/2T/1L with Wilcoxon p=0.027 and mean +7.6pp F1; (2) 89 synthetic ER configurations across 10 graph seeds show LOCALE winning 8/10 seeds with per-seed Wilcoxon p=0.010 and mean +12.5pp; (3) NCO identifies 97.9% false collider rate in CI-derived constraints; (4) ego-graph prompts are 2-3x more context-efficient than per-edge prompts.

## Previous Review Follow-Up (RN-004)

### RN-004 W1 (P1): Graph-seed pseudoreplication in synthetic results
**Status: ADDRESSED.**

This was my central concern in RN-004. The synthetic experiment was expanded from 3 to 10 graph seeds (g0-g9), producing 89 paired configurations. XN-037 now reports per-seed aggregates and uses Wilcoxon signed-rank at the graph-seed level (the correct unit of analysis). The result: LOCALE wins 8/10 seeds, W=3, p=0.010. The two seeds where MosaCD wins (g0 and g4) show small deltas (-0.9pp and -1.3pp), while the 8 LOCALE-favoring seeds show larger deltas (mean ~+15pp). This is a substantive resolution of my concern. The per-seed analysis is methodologically correct and provides meaningful statistical power.

I verified the new data exists on disk: all 9 configurations are present for each of g3-g9, and the MosaCD counterparts are complete. Spot-checking raw files (e.g., 20n_15d_g4: LOCALE accuracy=0.692, MosaCD F1=1.0; 20n_15d_g7: LOCALE accuracy=0.611, MosaCD F1=0.167) confirms the claimed pattern of high inter-seed variance.

### RN-004 W2 (P1): Near-random absolute performance on synthetic graphs
**Status: ACKNOWLEDGED, not fully resolved.**

LOCALE F1=0.519 on synthetic graphs (updated from 0.528 with the expanded data) remains close to random. The copilot does not report a random baseline. However, MosaCD at 0.393 is clearly below random, which means LOCALE's advantage is partially a "doesn't catastrophically fail" story rather than a "performs well" story. This concern is now a framing requirement (see W2 below), not a fatal gap.

### RN-004 W3 (P2): Alarm s0 outlier
**Status: ADDRESSED** (minimally).

LOG-2026-03-28-43 documents an investigation: Alarm s0 has 13.5% ego-graph accuracy (vs 80-86% for other seeds). The outlier is attributed to a data-dependent LLM failure where the specific data realization triggers systematically wrong orientations. The disguised robustness improvement (real=0.637, disguised=0.901) is explained by the LLM's incorrect domain priors being bypassed by anonymization. This is a plausible explanation. No dedicated experiment note was written (only a log entry), which is sloppy documentation, but the investigation itself is sufficient.

### RN-004 W4 (P2): Single data seed on synthetic experiments
**Status: NOT ADDRESSED.**

All synthetic experiments still use data_seed=0 only. Carried forward as W3.

### RN-004 W5 (P2): Hub.md and tracker stale
**Status: PARTIALLY ADDRESSED.**

Hub.md State of Knowledge was last updated 2026-03-26 and still lists "Hepar2: not in multi-seed comparison," "Disguised robustness: only 2 networks, 1 seed," and "Synthetic experiments: proposal Section 5.5 untouched" as unresolved -- all three are now resolved. Tracker says "Last updated: 2026-03-11" and does not reflect 16 days of subsequent work. The stale synthetic_er_summary.json has been regenerated (2026-03-29 timestamp, no longer shows the contradictory 0.467 value) but only covers g3-g9, not the full g0-g9 range. Carried forward as W4.

### RN-004 W6 (P3): 5 missing MosaCD synthetic runs
**Status: ADDRESSED.**

All 50n MosaCD results are now on disk (30 files for 3 densities x 10 graph seeds). The only missing configuration is 20n_20d_g8 MosaCD (1 of 90), down from 5 of 27 previously.

### RN-004 W7 (P3): Single model family
**Status: STRUCTURAL -- unchanged.**

## Strengths

- **S1: The pseudoreplication concern is properly resolved.** Expanding from 3 to 10 graph seeds was exactly the right response to my RN-004 W1 finding. The per-seed Wilcoxon (W=3, p=0.010) is the correct test: it treats each graph topology as the independent unit, avoids the inflated n=22 from treating configurations as independent, and provides genuine evidence of a systematic advantage. LOCALE wins 8/10 seeds. This is the single most important improvement since my last review.

- **S2: The BNLearn evidence is comprehensive and honest.** 11 networks, 8W/2T/1L, Wilcoxon p=0.027. The fidelity gap table in XN-035 is a model of transparent reporting -- it shows that LOCALE loses to *published* MosaCD on most large networks, clearly attributing this to the model and context window gap. This honesty strengthens the paper's credibility.

- **S3: The degree-1 vulnerability analysis (XN-032) is a genuine contribution to understanding.** Showing that single-endpoint coverage hurts on Asia/Alarm but not Insurance/Child/Sachs, and linking this to the ego-graph architecture, gives reviewers a clear mechanistic story for when the method works and when it doesn't.

- **S4: NCO remains independently valuable.** The 97.9% false collider rate finding (XN-022) across 944 errors, 6 networks, 7 sample sizes is a robust empirical contribution. This finding alone would be useful to the community even if the orientation advantage were smaller.

- **S5: Responsiveness to review.** Over 5 review rounds, every P1 concern I raised has been addressed. The copilot has not ignored or hand-waved any must-have issue. The Alarm s0 investigation was delayed but eventually conducted. The synthetic expansion was done correctly. This is unusually responsive.

## Weaknesses

- **W1 (P2): The synthetic advantage is driven more by MosaCD's catastrophic failure than by LOCALE's structural superiority.**

    This is the same concern as RN-004 W2, now downgraded from P1 to P2 because the per-seed analysis makes the relative advantage statistically valid.

    The absolute numbers remain troubling: LOCALE F1=0.519, MosaCD F1=0.393 on synthetic graphs. No random baseline is reported, but random orientation should yield ~0.50 F1 when skeleton coverage is high (which it is on the 20n and 30n synthetic graphs). This means LOCALE is approximately at random and MosaCD is substantially below random.

    My spot-checks confirm the mechanism: on 20n_15d_g4, MosaCD achieves F1=1.0 (perfect) while LOCALE gets ~0.69. On 20n_15d_g7, MosaCD gets F1=0.167 while LOCALE gets ~0.61. The variance in MosaCD's performance is extreme because its seeding process catastrophically fails on anonymous variables (seed_accuracy ranges from 0% to 31% on synthetic vs 71-100% on BNLearn). When seeding fails, MosaCD's propagation amplifies errors.

    **Implication for the paper**: The synthetic comparison should be framed as "LOCALE is robust to absence of domain knowledge while MosaCD is not," rather than "LOCALE has a structural advantage on novel graphs." The distinction matters: the former is about robustness, the latter about method quality. Both are legitimate contributions, but they have different novelty profiles. Report MosaCD seed_accuracy alongside F1 to make the failure mechanism transparent.

    **Addressable**: Add a random-orientation baseline on synthetic graphs. Report MosaCD seed_accuracy per graph seed.

- **W2 (P2): Single data seed on all synthetic experiments limits variance estimation.**

    All 90 synthetic configurations use data_seed=0. The BNLearn experiments use 12 data seeds and report standard deviations. On synthetic graphs, neither data-sampling variance nor its interaction with graph topology is quantified. With 10 graph seeds, the graph-topology variance is now properly sampled, but data-realization variance could be substantial on small graphs (n_samples=10000 on 20-node graphs is generous, but the LLM's response could be sensitive to specific data patterns).

    **For a workshop paper**: This is a disclosed limitation, not a fatal gap. The graph-seed variance (which is now properly sampled) is likely the dominant source of variance.

    **For a main-track paper**: Running 2-3 data seeds per graph configuration would strengthen the claim substantially. The experiment count would increase 2-3x but the infrastructure is already in place.

    **Addressable**: Run additional data seeds.

- **W3 (P2): The MosaCD re-implementation gap must be the leading caveat in any paper.**

    XN-035's fidelity gap table shows that published MosaCD (GPT-4o-mini, 128K context, n=20000) achieves F1=0.72 on Hepar2 vs LOCALE's 0.565, F1=0.81 on Win95pts vs LOCALE's 0.694, and F1=0.93 on Alarm vs LOCALE's 0.841. LOCALE beats the re-implemented MosaCD (same model, same context) but loses to published MosaCD on most large networks.

    This is transparently documented in XN-035 and the fidelity gap table. The concern is not about the evidence but about how the paper is written. If the paper leads with "LOCALE outperforms MosaCD" without immediately qualifying "under same-model conditions," reviewers will (correctly) flag this as misleading. The paper must position its contribution as: (a) a same-model methodological comparison showing ego-graph orientation advantages, (b) evidence that the advantage holds on novel graphs, and (c) NCO + context efficiency as independent contributions. It should NOT claim to beat MosaCD in absolute terms.

    **Addressable**: Framing only.

- **W4 (P3): Documentation remains partially stale.**

    Hub.md State of Knowledge lists three items as unresolved that have been resolved (Hepar2, disguised robustness, synthetic). Tracker has not been updated since 2026-03-11. The synthetic_er_summary.json covers only g3-g9, not the full g0-g9. These are cosmetic issues for internal project tracking but would be confusing for any external collaborator or auditor reviewing the project state.

    **Addressable**: Update all three files.

- **W5 (P3): Single model family (Qwen-27B) limits generalizability claims.**

    All experiments use Qwen3.5-27B-FP8 with 4096 context. The 9B ablation (XN-023) shows ego-graph reasoning degrades below 27B. No testing on GPT-4, Claude, or Llama families. Claims must be scoped to "on Qwen-27B" until cross-family validation is conducted.

    **Structural.**

## Questions for the Copilot

1. **What is the random orientation baseline F1 on synthetic graphs?** Specifically: take the correct skeletons, randomly orient each edge, compute F1. If LOCALE at 0.519 is within 2pp of random, the synthetic comparison is testing MosaCD's fragility rather than LOCALE's quality. This is a 5-line computation.

2. **What is MosaCD's seed_accuracy per graph seed on synthetic graphs?** The per-seed breakdown would explain why g0 and g4 favor MosaCD (perhaps these graph topologies happen to produce data that MosaCD's seeding prompt can parse despite anonymous variables) while g7 catastrophically fails MosaCD.

3. **Is the synthetic advantage driven by node count?** Does LOCALE's advantage increase or decrease with graph size (20n vs 30n vs 50n)? If the advantage is concentrated in larger graphs where MosaCD's seeding fails more completely, this changes the interpretation.

4. **For the Alarm s0 investigation**: You say ego-graph accuracy is 13.5%. How many edges is that? If it is 5/37, that is a specific set of edges that the LLM gets wrong -- are they related (e.g., a specific subgraph)?

5. **What is the effective sample size for the per-seed Wilcoxon?** With n=10 and a two-sided Wilcoxon signed-rank test, W=3 yields an exact p-value. The minimum achievable p-value at n=10 is 0.002 (W=0). Your W=3, p=0.010 is meaningful but not overwhelming. Is this correctly computed?

## Addressable vs Structural

### Addressable (before submission -- important for framing)
- **W1**: Compute random baseline on synthetic. Report MosaCD seed_accuracy. Reframe as robustness, not structural superiority.
- **W3**: Lead with same-model caveat. Include fidelity gap table in paper.
- **W4**: Update hub.md, tracker, regenerate full summary.json.

### Addressable (would strengthen but not required for workshop)
- **W2**: Run 2-3 data seeds per synthetic configuration.
- Compute per-node-count breakdown of synthetic advantage.
- Add ego-graph majority-vote ablation on synthetic (no NCO, no Max-2SAT) to isolate which pipeline components contribute.

### Structural (cannot be fixed)
- **W5**: Single model family.
- MosaCD re-implementation gap on large networks.
- Absolute synthetic performance near random.
- Two descoped proposal components (Phase 5 per-edge fallback, Phase 6 calibration).

## Overall Assessment

**I am upgrading from Borderline to Weak Accept.** The reason is simple: my central RN-004 concern -- graph-seed pseudoreplication in the synthetic experiments -- has been properly addressed. Expanding from 3 to 10 graph seeds with per-seed Wilcoxon (p=0.010) transforms the synthetic evidence from "suggestive but unreliable" to "statistically meaningful with appropriate caveats." The copilot did exactly what I asked: more seeds, per-seed aggregation, correct statistical test.

**The evidence now supports a specific, well-scoped claim:**

> LOCALE's ego-graph batching approach provides a statistically significant orientation advantage over MosaCD's per-edge approach under same-model conditions (11 BNLearn networks, Wilcoxon p=0.027; 10 synthetic ER topologies, per-seed Wilcoxon p=0.010). The advantage persists on novel graphs without domain knowledge, suggesting it is partially structural rather than purely domain-knowledge-driven. LOCALE also contributes the NCO finding (97.9% false collider rate in CI-derived constraints), 2-3x context efficiency, and a transparent characterization of its degree-1 vulnerability.

That claim is supportable by the evidence. Anything stronger is not.

**For CLeaR workshop submission**: Ready, with the following framing requirements:
1. Lead with same-model comparison caveat and include fidelity gap table.
2. Frame synthetic advantage as robustness to domain-knowledge absence, not structural superiority.
3. Report per-seed synthetic aggregates (the 10-seed table from XN-037), not just the aggregate.
4. Report degree-1 vulnerability analysis from XN-032.
5. Position NCO as an independent contribution, not just a pipeline component.

**For UAI main track**: Not ready without:
1. Multiple data seeds on synthetic experiments.
2. Cross-model validation (at least one additional model family).
3. Random-orientation baseline on synthetic to quantify signal above noise.
4. Ego-graph ablation on synthetic to isolate pipeline component contributions.
5. More complete ablation study (the XN-012 ablation is from early development; a clean ablation on the final pipeline is needed).

**What changed my mind from Borderline**: The pseudoreplication fix. With 3 graph seeds, the evidence was genuinely ambiguous -- g0 favored MosaCD, and the p=0.006 was inflated. With 10 graph seeds, the picture is clear: LOCALE wins 8/10 seeds with a meaningful aggregate effect. The two MosaCD-favoring seeds show small deltas while the LOCALE-favoring seeds show large deltas. This asymmetry supports a real effect, not an artifact.

**What keeps this at Weak Accept rather than Accept**: (1) Near-random absolute performance on synthetic graphs means the comparison's practical significance is unclear; (2) single model family limits generalizability; (3) the MosaCD re-implementation gap means the paper cannot claim to advance the state of the art, only to identify a better methodological approach under controlled conditions; (4) novelty is primarily in the composition and empirical findings, not in the individual components.

**The direction is sound. This is publishable work at the workshop level.**
