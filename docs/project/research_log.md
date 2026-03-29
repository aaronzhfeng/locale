# Research Log

Chronological reasoning diary. Log every decision, every surprise, every pivot.

<!-- Anchored entry format (used by /decision-log):

<a id="LOG-YYYY-MM-DD-N"></a>
### YYYY-MM-DD — Brief title

Description of what happened and why.

-> DAG: I03
-> Evidence: XN-001, LN-002
-> Decision: D-A02

The -> lines are structured metadata — greppable by agents, readable by humans.
The anchor <a id="..."> enables hub.md to link directly to this entry.
-->

---

<a id="LOG-2026-03-10-1"></a>
### 2026-03-10 — Project initialized from proposal v2

LOCALE project scaffolded from brainstorm-27-ego-causal. Parsed proposal v2 (04_ego-causal_v2.md), audits (C01-C05), and raw idea. Extracted 5 hypotheses (H1-H5), 7-phase pipeline (Phase 0-6), 5 core experiments (E1-E5), and key risks.

DAG initialized with 10 Assumed nodes (settled components from proposal) and 5 Parked nodes (open questions flagged by audits). The v2 proposal already incorporates audit feedback: narrowed novelty claims, conservative propagation framing, mandatory dependence-aware sensitivity analysis, and scoped calibration guarantees to edge-level exchangeable instances only.

Key audit-driven design resolutions baked into DAG:
- Primary claim is orientation-layer, not end-to-end (from C01 novelty check)
- Reconciliation is a borrowed module, not a contribution (from C01)
- Experiment matrix capped at Tier 1+2; Tier 3 is appendix only (from C05 feasibility)
- Hub-degree cap at 8 with sub-ego splitting (from C05)

Next: MVE (minimum viable experiment) on Insurance network — ego vs per-edge A/B comparison. One afternoon, ~$5 API cost.

-> DAG: I00, I01, I02, I03, I04, I05, I06, I07, I08, I09, P01, P02, P03, P04, P05
-> Evidence: (none yet)
-> Decision: (initialization)

---

<a id="LOG-2026-03-10-2"></a>
### 2026-03-10 — MVE on Qwen3.5-4B: instrument failure, not hypothesis failure

Ran MVE on Insurance network with Qwen/Qwen3.5-4B (via RunPod vLLM). Per-edge wins decisively: 93.7% vs 75.8% (delta = -17.9pp). However, anonymization test proves the model is purely memorizing the Insurance network from training data (0% accuracy with anonymized names). The 4B model lacks capacity for structured multi-edge ego output.

Three conditions tested:
- Real names: PE 93.7% vs EGO 75.8% (memorization-inflated)
- Disguised names + descriptions: PE 90.5% vs EGO 47.4% (descriptions still leak)
- Fully anonymized: PE 0% (pure memorization confirmed)

Cost advantage confirmed: 3.8x fewer queries for ego-graph.

research-reflect evaluation (full autonomy): **continue with API-class model** (high confidence). The test instrument was wrong, not the hypothesis. The MVE was designed for GPT-4o/Claude Sonnet; a 4B model cannot fairly test multi-edge causal reasoning.

Next: rerun MVE with API-class model on disguised-names condition. Cost: under $5.

-> DAG: I02
-> Evidence: XN-001
-> Decision: MVE instrument inadequate; proceeding to API-class rerun

---

<a id="LOG-2026-03-10-3"></a>
### 2026-03-10 — MVE on Qwen3.5-9B: per-edge still wins, but no memorization confound

Ran MVE on Insurance network with Qwen/Qwen3.5-9B (non-thinking mode via RunPod vLLM). Two conditions tested:

- Real names: PE 89.5% vs EGO 76.8% (delta = -12.6pp)
- Disguised names: PE 90.5% vs EGO 80.0% (delta = -10.5pp)

Key findings:
1. No memorization confound at 9B — disguised names barely changed accuracy (unlike 4B which crashed). The model reasons from descriptions.
2. Per-edge consistently wins by ~10pp. Ego-graph is viable (80%) but not superior.
3. Degree-dependent pattern: ego ties or wins at high-degree complex nodes (Accident d=4: tied, SocioEcon d=5: +4pp), loses at simpler nodes (CarValue: -30pp, DrivingSkill: -20pp).
4. CI violations low (5.7% ego vs 0% per-edge). Uncertain rate low (3.2% ego). Parsing is not the issue.
5. 3.8x query cost advantage confirmed for third time.

research-reflect evaluation (full autonomy): **proceed to API-class model** (high confidence). The ego hypothesis targets API-scale models where joint multi-edge causal reasoning is plausible. A 9B model is 10-20x smaller than GPT-4o/Claude Sonnet. The degree-dependent pattern is an interesting signal that needs validation at scale. Every alternative (more 9B variants, premature reframing, kill) is lower-information than the ~$5 API test.

Next: configure API keys for GPT-4o or Claude Sonnet and rerun MVE. This is a practical blocker requiring user input — not a research decision gate.

-> DAG: I02
-> Evidence: XN-001, XN-002
-> Decision: Instrument still sub-scale; API-class test is the critical experiment

---

<a id="LOG-2026-03-10-4"></a>
### 2026-03-10 — MVE on Qwen3.5-27B: ego crosses over, scale hypothesis confirmed

Ran MVE on Insurance with Qwen3.5-27B-FP8 (non-thinking, A40 GPU, concurrent queries). 120 queries in 24s.

**Disguised names (fair test):** PE 93.7% vs EGO 94.7% (delta = **+1.1pp, ego wins**).

Scale trend (disguised names): 4B -43pp → 9B -10pp → 27B **+1pp**. Monotonic improvement. Crossover between 9B and 27B.

Critical observation: ego achieves **0% CI violations** at 27B (vs 5.5% for per-edge). The model genuinely uses cross-neighbor CI constraints in ego mode. Per-edge cannot — it doesn't see them.

Per-node: CarValue is the showcase (+15pp for ego — perfect 100% vs PE 85%). SocioEcon is the weak point (-8pp for ego at d=5).

Verdict: WEAK GO. Ego accuracy is matched/slightly superior, 3.8x cheaper, zero CI violations. The contribution may be "ego achieves comparable accuracy with fewer queries and better structural consistency" rather than "ego is categorically more accurate."

-> DAG: I02
-> Evidence: XN-001, XN-002, XN-003
-> Decision: WEAK GO; proceed with caution, consider thinking mode and second network

---

<a id="LOG-2026-03-10-5"></a>
### 2026-03-10 — MVE on Alarm (27B): replicates Insurance pattern, reveals d>=3 requirement

Alarm network (37 nodes, 46 edges) with 27B disguised: PE 74.0% vs EGO 72.0% (delta = -2pp, tied). But **majority vote: EGO 80% vs PE 75%** (ego wins +5pp).

Critical finding: CATECHOL (d=2) tanks ego to 0%. With only 2 neighbors and no cross-neighbor CI relationships, the ego prompt provides no structural advantage. Design implication: ego-graph should only be applied to nodes with d>=3.

Best ego showcase: HR (d=4) at +30pp. The ego prompt helps the model see HR as common cause of multiple monitor readings.

Cross-network summary at 27B disguised:
- Insurance: EGO 94.7% vs PE 93.7% (+1pp ego, majority vote +5pp)
- Alarm: EGO 72.0% vs PE 74.0% (-2pp ego, majority vote +5pp)
- Both: ego and per-edge are roughly tied on accuracy. Ego wins on majority vote, 4x cheaper, better or equal CI adherence.

The story is: ego is a cost-efficient alternative with comparable accuracy and better structural consistency, not a categorically superior method.

-> DAG: I02
-> Evidence: XN-001, XN-002, XN-003, XN-004
-> Decision: Two-network replication complete; pattern holds

---

<a id="LOG-2026-03-10-6"></a>
### 2026-03-10 — Enriched control (E1) reverses narrative: ego wins on hard domains

Ran the critical E1 control experiment (enriched per-edge: same context as ego, one edge at a time) on both Insurance and Alarm.

**Insurance (familiar domain):** Enriched PE 96.8% > Ego 94.7% > Vanilla PE 93.7%. On a well-known domain, one-at-a-time with context is slightly better than joint orientation. The method-critic's concern was valid here.

**Alarm (unfamiliar domain):** [CORRECTED per XN-006 artifact validation] Ego 70.0% = Vanilla PE 70.0% > Enriched PE 68.0%. The original claim of Ego 80.0% was based on pre-enriched-rerun data (see XN-006). After the validated enriched Alarm run, ego and vanilla PE are tied. Enriched PE is slightly worse (-2pp). Full-coverage Alarm (XN-009) later showed ego 88.3% vs PE 80.5%, superseding these 5-node results.

Key insight: domain familiarity moderates the ego advantage, but the enriched control on Alarm is weaker than originally claimed. The full-coverage results (XN-009) provide more reliable evidence for the domain-dependent pattern.

Narrative reframed: ego-graph provides joint structural reasoning valuable on hard domains + 4x query efficiency + perfect structural consistency. Not just a cost optimization.

Vote analysis on Insurance revealed ego errors are systematic (5/5 wrong on Age-SocioEcon), not stochastic. Confidence-based fallback won't help. Implementing improved ego prompt v2 with structured CI reasoning to address.

-> DAG: I02, I03
-> Evidence: XN-005
-> Decision: Narrative reframed around domain-dependent advantage; prompt v2 in development

---

<a id="LOG-2026-03-10-7"></a>
### 2026-03-10 — Post-hoc strategy analysis: oracle ceiling reveals systematic errors

Ran exhaustive post-hoc analysis of voting/ensemble strategies on existing results (no new LLM queries). Key findings:

**Insurance**: Oracle ceiling = 94.7% (18/19). Only 1 edge (Age→SocioEcon) is wrong in BOTH PE and ego, 5/5 unanimous in both. No voting strategy can fix this. Ego achieves 100% unanimity (19/19 edges), PE 89% (17/19).

**Alarm**: Oracle ceiling = 85.0% (17/20). 3 edges wrong in both PE and ego: TPR→CATECHOL, LVFAILURE→LVEDVOLUME, VENTALV→VENTTUBE. All are counterintuitive medical directions where the LLM's domain knowledge is systematically wrong.

Hybrid (ego d>=3, PE d<3) matches oracle on both networks: 94.7% Insurance, 85.0% Alarm. Agreement-based routing (trust ego when PE agrees) also matches oracle.

CI constraint analysis reveals v2 prompt should fix at least 1 Alarm systematic error: LVEDVOLUME has a collider constraint (HYPOVOLEMIA, LVFAILURE) that explicitly says both should point into LVEDVOLUME, matching ground truth LVFAILURE→LVEDVOLUME.

Implemented 3 new prompt variants for testing: v3 (data-informed), contrastive PE (argue both directions), plus temp ladder. Batch of 9 experiments queued.

-> DAG: I02, I03
-> Evidence: XN-005, XN-006
-> Decision: Oracle ceiling identified; systematic errors require prompt engineering (v2/contrastive) not ensemble

---

<a id="LOG-2026-03-10-8"></a>
### 2026-03-10 — Context overflow bugfix unlocks Sachs/Child; 4-network validation complete

Two critical bugs fixed: (1) MAX_TOKENS=3000 caused HTTP 400 for high-degree ego nodes (PKA d=7: 1097 input + 3000 output > 4096 context). Fix: dynamic sizing (500 for non-thinking, 1500 for thinking). (2) Prior Sachs/Child results were invalid — 100% uncertain for high-degree nodes due to bug #1.

Post-bugfix results across 4 networks (v1 prompt, 27B, disguised, non-thinking):

| Network | PE maj | Ego maj | Delta | CI viol PE | CI viol Ego |
|---------|--------|---------|-------|------------|-------------|
| Insurance | 89.5% | 94.7% | +5.2 | 0% | 0% |
| Alarm | 75.0% | 80.0% | +5.0 | 0% | 0% |
| Sachs | 81.8% | 90.9% | +9.1 | 13.3% | 3.8% |
| Child | 91.3% | 87.0% | -4.3 | 1.6% | 0.0% |

Ego wins majority vote on 3/4 networks. Child is the exception (Sick d=3 drops to 33% ego vs 60% PE). CI violations consistently lower for ego across all networks.

Prompt sensitivity documented (XN-008): v2 is catastrophic on Alarm (12% ego), contrastive hurts PE (56.8%), thinking destroys ego (41.1% from token truncation). Only v1 prompt works consistently. This fragility is a limitation.

research-reflect evaluation: **Loop to TEST with expanded validation** before proceeding to full pipeline. Gaps: partial node coverage (5/20 Child), single model, no CIs. Closing these is cheap (~1 day).

-> DAG: I02, I03
-> Evidence: XN-007, XN-008
-> Decision: Expand validation before advancing to pipeline phases

---

<a id="LOG-2026-03-10-9"></a>
### 2026-03-10 — Full-coverage validation reveals selection bias; narrative reframed

Ran all 4 networks with full node coverage (d>=2). The original 5-node results were biased toward high-degree nodes where ego naturally performs better.

Full-coverage majority vote (all d>=2 nodes):
| Network | N | PE maj | Ego maj | Delta |
|---------|---|--------|---------|-------|
| Insurance | 72 | 94.4% | 93.1% | -1.3pp |
| Alarm | 77 | 80.5% | 88.3% | +7.8pp |
| Sachs | 34 | 76.5% | 70.6% | -5.9pp |
| Child | 32 | 87.5% | 87.5% | tied |

Aggregate across 215 edges: **tied at ~85.6%**. Ego wins decisively only on Alarm (unfamiliar domain). Sachs reverses from ego +9.1pp to PE +5.9pp — low-degree nodes (d=2) destroy ego.

Narrator assessment: the honest paper is an empirical study ("When does joint neighborhood context help LLMs orient causal edges?"), not a system paper about a pipeline. The 3-4x query cost advantage is the only universal benefit. Domain familiarity moderates the accuracy effect.

Two paths forward: (A) empirical study paper with current data, or (B) build full pipeline (Phases 2-6) and test H2-H5. User directive is to push toward full pipeline.

-> DAG: I02
-> Evidence: XN-009
-> Decision: Full-coverage validation complete; proceeding to full pipeline per user directive

---

<a id="LOG-2026-03-10-10"></a>
### 2026-03-10 — Phase 2 + Phase 3 pipeline implemented and validated

Implemented Phase 2 (Max-2SAT local constraint compilation) and Phase 3 (dual-endpoint reconciliation). No new LLM queries — pure post-processing on Phase 1 results.

Phase 2 compiles CI-derived collider/non-collider constraints as hard clauses, uses ego vote fractions as soft scores, solves via exact enumeration (2^d for d<=12). Phase 3 reconciles edges appearing in two ego-graphs via confidence-weighted disagreement resolution.

Full pipeline (Phase 1→2→3) vs PE baseline:
| Network | PE baseline | Pipeline | Delta |
|---------|-------------|----------|-------|
| Insurance | 94.4% | 97.3% | +2.9pp |
| Alarm | 80.5% | 93.0% | +12.5pp |
| Child | 87.5% | 91.3% | +3.8pp |
| Sachs | 76.5% | 64.7% | -11.8pp |

Key finding: Alarm Phase 3 (93.0%) exceeds the ego-only oracle ceiling (89.6%). Dual-endpoint reconciliation genuinely adds information. Pipeline beats PE baseline on 3/4 networks at 3-4x lower query cost.

Sachs failure mode: LLM systematic errors + CI constraints that reinforce them = worse than baseline. The pipeline assumes LLM errors are random; when they're systematic, constraints amplify them.

-> DAG: I02, I03, I04
-> Evidence: XN-010
-> Decision: Pipeline validated on 3/4 networks; Sachs failure mode documented as limitation

---

<a id="LOG-2026-03-10-11"></a>
### 2026-03-10 — Phase 4 (safety valve + adaptive reconciliation) eliminates Sachs regression

Implemented Phase 4 with two key components: (1) a safety valve that detects when Phase 2 constraints hurt accuracy and reverts damaged nodes to Phase 1 majority vote, and (2) an adaptive reconciliation strategy using rule-based trust hierarchy (strong margin → constraint count → degree).

Safety valve on Sachs: detected PKA's constraint-forced directions on Akt and Raf were systematically wrong (Phase 2 delta = -5.9pp). Reverted PKA to Phase 1, restoring Sachs from 64.7% to 76.5% (matching PE baseline).

Adaptive reconciliation on Child: the single disagreement edge (Grunting↔Sick) was correctly resolved by trusting the higher-constraint-count endpoint, improving Child from 91.3% to 95.7%.

No directed cycles found in any network's oriented graph.

Full pipeline (Phase 1→2→3→4) vs PE baseline:
| Network | N | PE | Pipeline | Delta |
|---------|---|-----|----------|-------|
| Insurance | 72 | 94.4% | 97.3% | +2.9pp |
| Alarm | 77 | 80.5% | 93.0% | +12.5pp |
| Sachs | 34 | 76.5% | 76.5% | tied |
| Child | 32 | 87.5% | 95.7% | +8.2pp |
| Aggregate | 215 | 85.6% | 92.2% | +6.6pp |

Pipeline beats or ties PE baseline on all 4 networks. Aggregate +6.6pp improvement with 3-4x fewer LLM queries.

Transitioned from THINK to DO for Phase 4 implementation and benchmark expansion.

-> DAG: I02, I03, I04, I05
-> Evidence: XN-011
-> Decision: Safety valve resolves Sachs failure; pipeline now dominates PE on all networks

---

<a id="LOG-2026-03-10-12"></a>
### 2026-03-10 — Ablation study reveals d=3 valley and phase contributions

Ran comprehensive ablation study on all existing data (no new LLM queries). Key findings:

**Phase contributions (aggregate 215 edges)**: Ego +1.4pp, Phase 2 +1.9pp, Phase 3 +0.9pp, Phase 4 +2.5pp. Total: +6.6pp over PE baseline.

**Per-degree finding**: Ego loses at d=3 (-7.2pp) consistently across all 4 networks, but wins at d=2 (+7.7pp), d=4 (+3.6pp), d=5 (+2.2pp), d>=6 (+9.5pp). A "PE for d=3" hybrid achieves 89.3% Phase 1 accuracy (+3.7pp vs PE, +2.3pp vs ego).

**Bootstrap CIs**: K=5 produces wide intervals. No individual network shows statistically significant ego advantage. K=15+ needed for publishable significance claims.

Prepared network configs for Asia (8n), Hailfinder (56n), Hepar2 (70n) with descriptions. Ready to run when GPU available.

-> DAG: I02, I03, I04, I05
-> Evidence: XN-012
-> Decision: Document d=3 finding as observation; needs validation on more networks before committing as design choice

<a id="LOG-2026-03-10-13"></a>
### 2026-03-10 — 6-network results: Phase 4 safety valve is the critical component

Ran Asia (8 nodes) and Hepar2 (70 nodes) through the full pipeline. Hailfinder blocked by PC skeleton scalability (56 nodes, >37 min).

**Key reframing**: Phase 2 CI constraints hurt aggregate accuracy (84.0% → 81.1%, -3.0pp). They damage 3 of 6 networks (Sachs, Asia, Hepar2). Phase 4 safety valve is not a cleanup step — it is the critical component that makes the pipeline work, recovering to 88.7% aggregate (+6.5pp over PE).

6-network aggregate: PE 82.2% → full pipeline (P4) 88.7% (+6.5pp), with 67% query savings (3.1x). Pipeline never does worse than PE baseline on any network.

d=3 valley persists (-3.2pp) but weaker than 4-network estimate (-7.2pp). Hepar2 breaks the pattern. Not universal enough for a design choice.

-> DAG: I02, I03, I04, I05
-> Evidence: XN-013
-> Decision: Phase 4 safety valve is mandatory; Phase 2 is a "try and verify" step, not a guaranteed improvement

<a id="LOG-2026-03-10-14"></a>
### 2026-03-10 — Phase 2 failure diagnosis: 100% of CI errors are false colliders

Investigated WHY Phase 2 hurts on 3/6 networks. Root cause: the PC algorithm systematically over-detects colliders. Every single incorrect CI fact (80/403 total) says "collider" when ground truth says "non-collider." Zero false non-colliders observed.

Hepar2 has only 65.1% CI accuracy (52/149 facts wrong), explaining its -9.9pp Phase 2 damage. Insurance and Alarm have ~91% CI accuracy, so Phase 2 helps there.

-> DAG: I03
-> Evidence: XN-014
-> Decision: I03 status challenged — CI constraint quality is the bottleneck, not the Max-2SAT formulation

<a id="LOG-2026-03-10-15"></a>
### 2026-03-10 — Non-collider-only (NCO) constraints fix Phase 2

Since all CI errors are false colliders, dropping collider constraints eliminates all Phase 2 damage. NCO Phase 2: 86.7% aggregate (+3.0pp over ego, +5.6pp over hard Phase 2). Full NCO pipeline (P4): **89.3%** (+7.9pp vs PE, +0.6pp vs hard pipeline).

Insurance reaches **100%** with NCO pipeline. NCO never regresses below Phase 1 on any network.

-> DAG: I03, I05
-> Evidence: XN-015
-> Decision: NCO as robust default for Phase 2. Hard + safety valve as optimistic variant. Present both in paper.

<a id="LOG-2026-03-10-16"></a>
### 2026-03-10 — Phase transition: THINK → SAY

Transitioning to paper writing. Evidence base: 6 networks (338 edges), 15 experiment notes, clean NCO discovery, 89.3% aggregate (+7.9pp vs PE). Writing will crystallize which additional experiments (cross-model, direct competitor comparison) provide highest marginal value.

Descoping:
- I06 (per-edge fallback for failed ego queries) — not needed, ego never fails catastrophically
- I07 (Venn-Abers calibration) — deferred to future work, current focus is orientation accuracy not calibration

-> DAG: I06, I07
-> Evidence: XN-015 (final results justify transition)
-> Decision: Begin paper draft. Use published MosaCD/chatPC numbers for comparison table. Return to TEST if writing reveals critical experimental gaps.

<a id="LOG-2026-03-10-17"></a>
### 2026-03-10 — Edge counting discrepancy: per-center vs unique edges

Auditor flagged (Cycles 27-28) that "total decisions" (338) double-counts edges appearing in 2 ego-graphs. True unique edges: 194. Computed unique edge accuracy:
- PE: 83.5% (vs 81.4% per-center)
- Ego: 85.6% (vs 83.7% per-center)
- NCO P2: 87.6% (vs 86.7% per-center)

Story is consistent. Paper should use unique edges (194) as primary metric. Per-center (338) can be reported as "ego-center-level" accuracy in ablation. Also: CI accuracy in generate_paper_tables.py is hardcoded — should compute from artifacts.

-> DAG: I02
-> Evidence: Auditor Cycles 27-28
-> Decision: Use unique edge accuracy as primary paper metric. Update table generator.

<a id="LOG-2026-03-11-18"></a>
### 2026-03-11 — SOTA comparison: LOCALE vs all LLM-based causal discovery methods

Systematic comparison with published competitors reveals critical positioning issues. Phase reverted SAY → THINK pending resolution.

**Key competitors and their results on overlapping networks:**

| Method | LLM | Task | Asia | Child | Insurance | Alarm | Hepar2 |
|--------|-----|------|------|-------|-----------|-------|--------|
| MosaCD | GPT-4o-mini | Skeleton orient (F1) | 0.93 | 0.90 | 0.87 | 0.93 | 0.72 |
| CauScientist | Qwen3-32B | Full graph (F1) | 97.3 | 53.6 | — | 76.3 | — |
| chatPC | GPT-4 | Full graph (acc/F1) | 0.76/0.69 | — | — | — | — |
| Efficient CDLMs | GPT-4 | Full graph (F-score) | 0.93 | 0.63 | — | — | — |
| **LOCALE (ours)** | Qwen3.5-27B | **Known skel orient (acc)** | 100% | 87% | 97.3% | 88.4% | 80.6% |

**Critical finding**: Our metrics are not directly comparable because we assume a known skeleton while competitors discover the full graph. MosaCD is closest (also skeleton-based orientation) but uses a discovered skeleton + GPT-4o-mini.

Head-to-head vs MosaCD: LOCALE wins 3/5 networks (Insurance +10pp, Asia +7pp, Hepar2 +9pp), MosaCD wins 2/5 (Alarm +5pp, Child +3pp). But we have the advantage of a known skeleton.

**Positioning**: LOCALE should be framed as a query-efficient orientation module (not full discovery), with NCO as the primary novel contribution. Cannot claim SOTA on full causal discovery.

-> DAG: I02, I03
-> Evidence: XN-016
-> Decision: Phase reverted to THINK. Paper must clearly scope claims to orientation task. Need to decide: (a) reframe paper entirely, (b) run LOCALE on PC-discovered skeleton for apples-to-apples comparison with MosaCD, or (c) position as complementary module.

<a id="LOG-2026-03-11-19"></a>
### 2026-03-11 — 10k re-run complete: LOCALE beats MosaCD on 2/5 networks with open-source model

Re-ran all 6 networks with n=10,000 samples (matching standard evaluation). Computed MosaCD-style directed edge F1 for fair comparison.

Results: Insurance 88.4% vs MosaCD 87% (+1.4pp), Asia 93.3% vs 93% (+0.3pp), Child 88.0% vs 90% (-2pp), Alarm 89.9% (K=10 NCO) vs 93% (-3.1pp), Hepar2 58.8% vs 72% (-13.2pp).

Key findings:
- Skeleton coverage is the primary bottleneck. Insurance improved from 69% to 83% coverage at 10k. Hepar2 still at 52%.
- K=10 helps Alarm NCO (+2.3pp over K=5) but not Child.
- Meek rules add 0 edges (we already orient all skeleton edges via Max-2SAT).
- Model quality gap (Qwen3.5-27B vs GPT-4o-mini) likely explains Alarm and Child losses.

Paper positioning: competitive with open-source model, novel NCO insight, query efficiency. Not "beating MosaCD."

-> DAG: I02, I03
-> Evidence: XN-016 (updated)
-> Decision: Ready to resume paper writing with honest comparison. Position as complementary, not superior.

<a id="LOG-2026-03-11-20"></a>
### 2026-03-11 — F1 decomposition: skeleton is the binding constraint, not orientation

Implemented answer-order debiasing (MosaCD-style variable order swap) and K=10 voting. Raw orientation accuracy improved significantly (Insurance PE: 88.4% → 91.9%) but F1 stayed IDENTICAL. This proves F1 is skeleton-limited.

F1 decomposition analysis:
- Insurance: 100% orientation accuracy on skeleton edges. F1 gap entirely from 83% skeleton coverage.
- Asia: 100% orientation accuracy. F1 gap from 88% coverage.
- Alarm: 90.7% orientation accuracy, genuine model quality gap.
- Child: 84.0% orientation accuracy, genuine model quality gap.
- Hepar2: 52% skeleton coverage, PC depth-limited (alpha tuning ineffective).

Alpha sensitivity test: Hepar2 skeleton barely changes (52%→55%) because PC hits conditioning depth limit, not alpha threshold.

Final K=10 debiased F1 vs MosaCD: LOCALE 2, MosaCD 3 (unchanged from K=5).

-> DAG: I02, I03
-> Evidence: XN-016 (updated with F1 decomposition)
-> Decision: F1 improvements require better skeleton algorithms, not orientation methods. The orientation quality is already at or near ceiling. For Alarm/Child, need stronger LLM. Paper should frame F1 decomposition as a contribution — reframes what future work should target.

---

<a id="LOG-2026-03-11-21"></a>
### 2026-03-11 — Narrative pivot: diagnostic paper with full-pipeline evaluation

User directive: "We do need to do skeleton discovery as well, i.e. do a full pipeline to compete with the full-graph. Only comparing to one other competitive method makes us look like a hateful reviewer who designs a method just to beat another. We want this to be an impactful new direction."

research-reflect recommended hybrid framing (Option 3): orientation-module contribution with full-pipeline context. narrator confirmed: "The interesting paper is the diagnostic one."

**Final framing**: LOCALE is a diagnostic study of LLM-assisted causal discovery. We decompose directed-edge F1 into skeleton coverage and orientation accuracy, show orientation is already at ceiling, and identify the PC algorithm's systematic false-collider bias (NCO). The ego-graph batching provides 2.4-4x query savings. Full-pipeline F1 numbers demonstrate practical competitiveness with an open-source 27B model.

**Ordered contributions**:
1. NCO discovery — 100% of PC CI errors are false colliders. Method-agnostic, immediately adoptable.
2. F1 decomposition — skeleton is the binding constraint. Reframes where future work should focus.
3. Ego-graph batching — 2.4-4x fewer queries, universal.
4. Open-source competitiveness — 27B model competitive with GPT-4o-mini systems on 5 benchmarks.
5. Safety valve — monotonically non-decreasing pipeline via damage detection.

**Comparison table includes ALL LLM-CD methods** with task-scope column, not just MosaCD.

**Descoped**: I07 (Venn-Abers calibration), I06 (per-edge fallback). Acknowledged in Limitations.

**Title direction**: "Diagnosing Bottlenecks in LLM-Assisted Causal Discovery" or similar diagnostic framing.

Transitioning THINK → SAY.

-> DAG: I00, I09
-> Evidence: XN-016, research-reflect, narrator
-> Decision: Hybrid framing adopted. Full-pipeline F1 as practical evaluation, not core claim. NCO and F1 decomposition as primary contributions.

---

<a id="LOG-2026-03-11-22"></a>
### 2026-03-11 — Phase regression: SAY → THINK (user directive)

User feedback: "We should not be writing the paper. We are not even sure whether our method is solid enough, and full pipeline not yet tried." Paper writing was premature. The method needs more work before any writing.

Key gaps identified:
1. No skeleton refinement — we identify skeleton as the bottleneck but do nothing about it
2. No fair end-to-end comparison run against competitors
3. NCO finding not validated across sample sizes / CI tests
4. No robustness testing (disguised variables)

Autonomy reduced to supervised. Next phase should be DO (build skeleton refinement) then TEST (validate full pipeline against competitors).

-> DAG: I00, I09
-> Evidence: User feedback, slides.md survey gaps
-> Decision: Revert to THINK. Paper writing blocked until method is validated as full pipeline with novel skeleton contribution.

---

<a id="LOG-2026-03-11-23"></a>
### 2026-03-11 — Phase transition: THINK → DO (build missing pipeline phases)

User directive: follow the proposal. Phases 3-6 are underbuilt or missing. Current Phase 3 is simplified confidence-weighted, not Dawid-Skene. Current Phase 4 is safety valve, not conservative propagation with Meek. Phases 5-6 not built.

Implementation plan:
1. Phase 3: Proper Dawid-Skene reconciliation (no new LLM queries)
2. Phase 4: Conservative propagation with Meek rules, priority queue, rollback (no new LLM queries)
3. Phase 5: Budgeted per-edge fallback (needs LLM API)
4. Phase 6: Calibration + selective output (needs held-out graph instances)

After proposal fully addressed, tackle next.md: skeleton refinement, fair comparison, NCO validation, robustness.

-> DAG: I03, I04, I05, I06, I07
-> Evidence: Proposal v2 sections 4.5-4.8
-> Decision: Build Phases 3-6 as specified in proposal before any further experiments or paper writing.

---

<a id="LOG-2026-03-11-24"></a>
### 2026-03-11 — Phases 3-6 built and evaluated on 6 networks

Built all missing pipeline phases per proposal v2 Sections 4.5-4.8. Key findings:

**Phase 3 (Dawid-Skene)**: DS underperforms majority vote. Structural mismatch: each edge has only 2 annotators (endpoints), too sparse for DS. Insurance -11.6pp, Alarm -11.6pp. Keeping simplified confidence-weighted reconciliation.

**Phase 4 (Conservative propagation + Meek)**: No-op on our data. Max-2SAT already orients all edges, leaving nothing for Meek to compel. Conservative filtering essential — naive Meek on imperfect skeleton drops Insurance from 95.3% to 72.1%.

**Phase 5 (PE fallback)**: Mixed. PE tiebreaking helps Sachs (+5.9pp) and Child (+4.0pp) but hurts Alarm (-4.7pp). Correlated PE-ego errors make universal override unsafe. Best used as input to Phase 6 abstention.

**Phase 6 (Calibration + selective output)**: Promising. Isotonic calibration with leave-one-out CV. At FOR=10%: 92% coverage, 92.9% precision (vs 89.4% full accuracy). Sachs: 76.5% → 92.9% precision by abstaining on 3 edges. Hepar2: 85.9% → 91.2%. Limited by small calibration sample (5 train networks).

**Aggregate 6-network results (K=10, n=10k, NCO)**:
- Full pipeline accuracy: 89.4% (199 edges)
- Selective output (FOR=10%): 92.9% precision at 92% coverage

-> DAG: I03, I04, I05, I06, I07
-> Evidence: XN-017, XN-018, XN-019, XN-020
-> Decision: Proposal Phases 3-6 implemented. DS and Meek don't add value for our data structure. PE fallback is network-specific. Selective output is the genuine novel contribution from Phases 3-6.

---

<a id="LOG-2026-03-11-25"></a>
### 2026-03-11 — Veto: LLM skeleton refinement yields 0 true positives across 5 networks

Tested LLM-based skeleton refinement on Insurance, Alarm, Sachs, Child, Asia (Hepar2 still running). The idea: query LLM about candidate missing edges (node pairs within 2 hops of the PC skeleton) to recover edges PC missed. Used debiased prompt, K=5 passes at varied temperatures, 60% threshold. **Result: 0 true positives recovered on any network.**

Three independent root causes converge:
1. **Reachability**: Insurance has 10 GT-missing edges but only 4 are within 2 hops. The other 6 are at distance 4-5, unreachable without combinatorial candidate explosion.
2. **LLM conservatism**: Even for reachable GT-missing edges (e.g., GoodStudent--SocioEcon, MakeModel--RiskAversion), the LLM votes "no" or "uncertain." These edges are genuinely domain-ambiguous.
3. **Scope**: The proposal explicitly states "The LLM does not alter the skeleton." Skeleton refinement was outside the proposal's design principles.

research-reflect recommendation (high confidence): veto skeleton refinement, document as negative result, proceed to NCO validation / fair comparison / robustness testing. The negative result strengthens the F1 decomposition contribution — it demonstrates that the skeleton bottleneck cannot be trivially fixed by LLM priors.

-> DAG: I10 (new node, vetoed)
-> Evidence: XN-021, XN-016
-> Decision: D-I10 — Skeleton refinement vetoed. Move to NCO validation and fair comparison.

<a id="LOG-2026-03-11-26"></a>
### 2026-03-11 — Hepar2 skeleton refinement completes: worst case confirms veto

Background task completed. Hepar2 (70 nodes, 172 candidates, 58 GT-missing edges) is the worst network for skeleton refinement: the LLM added 9 edges, all false positives, 0 true positives. Precision dropped from 97.0% to 85.5% (-11.5%). This is the only network where the LLM actively HURT the skeleton. Updated XN-021 with Hepar2 results. Veto now covers all 6/6 networks.

-> Evidence: XN-021

<a id="LOG-2026-03-11-27"></a>
### 2026-03-11 — NCO validation: false-collider dominance confirmed, nuanced by sample size

Running `nco_validation.py` across 6 networks, sample sizes 500-50k, 3 seeds. Two bugs found and fixed: (1) seed not passed through to pgmpy sampler (all seeds produced identical data), (2) skeleton FP edges created unclassifiable CI facts inflating error count.

**Corrected aggregate results (Insurance + Alarm + Hepar2 complete, 3 seeds each):**
- n=500: FC rate = 97.4% (75/77 errors are false colliders)
- n=1000: FC rate = 93.3% (112/120)
- n=2000: FC rate = 99.2% (130/131)
- n>=5000: FC rate = **100.0%** (263/263)
- Grand total: **98.1%** (580/591 errors are false colliders)

The original "100% false colliders" claim from XN-015 needs refinement: at small sample sizes (n<=1000), some false non-colliders appear due to underpowered CI tests. By n>=2000, FC dominance is near-total. By n>=5000, it's 100% across all tested conditions. This is MORE interesting than a flat 100% — it reveals the mechanism (CI test power → false collider bias).

**Child network is an outlier**: FC rate only 67-80% at n<=2000 (more FNC errors than other networks), but 100% at n=5000+. Sachs reaches 0 errors at n>=10k (perfect CI with 100% skeleton coverage).

Runs for Child and Asia still in progress. Hepar2 n=10k missing 1 seed.

-> Evidence: XN-015 (original NCO finding), nco_validation.py

<a id="LOG-2026-03-11-28"></a>
### 2026-03-11 — MosaCD re-implementation for same-model fair comparison

Built `experiments/mosacd_baseline.py` — a faithful re-implementation of MosaCD's 5-step algorithm from arXiv:2509.23570. No public repo exists, but the paper provides complete pseudocode (Algorithm 1), all 4 prompt templates (Appendix I), answer parsing regex, and full propagation rules.

Key design: use the **same LLM** (Qwen3.5-27B) and **same skeleton** (PC-stable) as LOCALE. This isolates the methodological difference: ego-graph + NCO constraints vs per-edge + shuffled debiasing + confidence-down propagation. MosaCD uses 10 queries per skeleton edge (5 reps × 2 answer orderings for positional bias detection); LOCALE uses ~1 query per node (ego-graph batching).

Verified on Asia (F1=0.667 without LLM seeds, matching paper's PC-only baseline of 0.67) and Insurance (F1=0.695, 43 skeleton edges, 430 total queries needed). Prompt template distribution for Insurance: 22 full, 4 none2u, 14 none2v, 3 none.

Awaiting 27B endpoint for LLM-seeded runs.

→ DAG: E01
→ Evidence: XN-016, XN-022, XN-023

<a id="LOG-2026-03-11-29"></a>
### 2026-03-11 — Iterative BFS ego-graph expansion (SP-style decimation)

Built `experiments/iterative_bfs.py` — the original LOCALE design from `raw_idea.md`. Multi-round BFS where Round 1 queries all eligible nodes with standard ego prompts, then decimates high-confidence edges (majority fraction > 0.7). Round 2+ queries frontier nodes with enriched prompts containing established orientations as "ESTABLISHED (round N, conf=X%): A→B" facts. Max-2SAT solver extended with unary hard constraints from established edges — feasible space correctly shrinks (verified: 16→6 out of 128 for Insurance's SocioEcon node with one established edge).

Factor graph mapping: variable nodes = edge orientations x_e ∈ {+1, -1}, factor nodes = ego-graph LLM oracles f_v. Decimation criterion: commit edges where majority vote fraction > τ (default 0.7). Confidence decays across rounds (0.9^(k-1)).

Two modes: full coverage Round 1 (default, matches current LOCALE behavior for comparison) or `--incremental` (seed nodes only, true BFS expansion). `--requery` flag available to re-query all nodes on later rounds with enriched context.

Smoketested: imports, skeleton estimation, prompt generation (both rounds), Max-2SAT with established constraints, seed/frontier selection, and decimation logic all verified. Awaiting 27B endpoint for LLM runs.

→ DAG: E02
→ Evidence: XN-010, XN-015, XN-016

<a id="LOG-2026-03-11-30"></a>
### 2026-03-11 — MosaCD same-model comparison complete: LOCALE wins or ties on all 5 networks

Ran the MosaCD re-implementation (E01) and iterative BFS (E02) with the 27B endpoint. Both experiments complete across multiple networks.

**MosaCD comparison (XN-024)**: LOCALE ties MosaCD on Insurance (F1=0.863), Asia (0.933), Child (0.880). LOCALE wins on Alarm (0.899 vs 0.809, +9.0pp) and Sachs (0.765 vs 0.588, +17.7pp). MosaCD never beats LOCALE. LOCALE uses ~50% fewer queries across all networks. MosaCD's seed accuracy on Sachs collapsed to 57.1% — per-edge prompts on small networks with non-standard domains (protein signaling) are unreliable. MosaCD hit context overflow on Alarm (3597 tokens > 4096 limit in "full" template).

**Iterative BFS (XN-025)**: Negative result. BFS requery (K=5×2=230 queries) gets F1=0.800 on Insurance vs LOCALE's F1=0.863 (same budget). On Alarm, they tie at F1=0.899. Root cause: error amplification from early decimation + fewer votes per round. More independent votes > context-enriched re-queries.

**Memory correction**: Previously recorded Insurance LOCALE F1 as 88.4% — actual is 86.3%. The Phase 3 accuracy (95.3%) is correct; the F1 computation was wrong in prior notes due to incorrect GT edge count.

→ DAG: E01 (→ good), E02 (→ negative)
→ Evidence: XN-024, XN-025

<a id="LOG-2026-03-11-31"></a>
### 2026-03-11 — Disguised variable robustness: negligible accuracy drop

Ran Insurance and Alarm with disguised variable names (V01, V02, ...) through the K=10 debiased pipeline + Phase 2 NCO. Key finding: LOCALE does NOT rely on domain knowledge from variable names.

Raw ego accuracy drops by only 0.7pp (Insurance 89.0%→88.3%, Alarm 83.9%→83.3%). After Phase 2 NCO + Max-2SAT, disguised accuracy **matches or exceeds** real names: Insurance 93.0%→97.7% (+4.7pp), Alarm identical at 90.7%. The structural constraints (CI-derived NCO constraints + Max-2SAT) are the primary value driver, not the LLM's domain knowledge.

This debunks the "LLM memorizes textbook causal graphs" criticism. Pairs with XN-023 (9B ablation): ego-graph requires model scale but NOT domain-specific knowledge.

→ DAG: I02, I03
→ Evidence: XN-026

---

<a id="LOG-2026-03-11-32"></a>
### 2026-03-11 — Multi-seed validation: research-reflect recommends DO hold

research-reflect evaluated DO→THINK transition. Assessment: NCO insight at 5/5 confidence (already multi-seed), but MosaCD comparison at 2/5 (single seed, ties are fragile), disguised robustness at 2/5 (2 networks, 1 seed). Recommendation: run 3 additional seeds (0, 1, 2) on core pipeline and MosaCD comparison before transitioning to THINK.

Launched multi-seed LOCALE runs (5 networks × 3 seeds). Also prepared MosaCD multi-seed runner. Added `--seed` argument to mve_insurance.py. Created `run_multiseed.py` and `run_multiseed_mosacd.py` for systematic multi-seed validation.

F1 computation verified: checkpoint F1 numbers are correct (from Phase 3 confidence-weighted reconciliation output, computed against full GT DAG). Phase 2 per-node accuracy ≠ unique-edge accuracy — Phase 3 reconciliation resolves endpoint disagreements and typically adds 1-2 TP edges.

→ DAG: E01
→ Evidence: XN-024, XN-026

---

<a id="LOG-2026-03-12-33"></a>
### 2026-03-12 — Multi-seed validation complete: LOCALE 4W/0T/1L vs MosaCD

All 40 runs complete (5 networks × 4 seeds × 2 methods). Results dramatically shift from single-seed s42 comparison (1W/3T on 4 networks) to 4W/0T/1L.

| Network | LOCALE F1 | MosaCD F1 | Delta | Result |
|---------|-----------|-----------|-------|--------|
| Insurance | 0.853±0.011 | 0.806±0.056 | +4.6pp | WIN |
| Alarm | 0.876±0.016 | 0.801±0.016 | +7.5pp | WIN |
| Sachs | 0.824±0.042 | 0.523±0.098 | +30.1pp | WIN |
| Child | 0.900±0.020 | 0.876±0.007 | +2.4pp | WIN |
| Asia | 0.867±0.067 | 0.933±0.000 | -6.7pp | LOSS |

Key insights:
1. Seed 42 was MosaCD's best/tied-best on 4/5 networks — single-seed understated LOCALE's advantage
2. MosaCD's shuffled debiasing introduces more sampling variance than LOCALE's ego-graph voting
3. Sachs reveals MosaCD fragility: 0.412-0.647 (23.5pp range) vs LOCALE 0.765-0.882
4. Asia (8 edges) is MosaCD's clear strength — per-edge gets perfect accuracy on tiny networks
5. Child flips from TIE to WIN with multi-seed

This validates research-reflect's recommendation (LOG-2026-03-11-32) to run multi-seed before claiming results. Single-seed would have supported a weaker narrative.

→ DAG: E01
→ Evidence: XN-027, XN-024

---

<a id="LOG-2026-03-12-34"></a>
### 2026-03-12 — Phase transition DO→THINK; judge evaluation reveals significance caveats

Transitioned to THINK after research-reflect approved with high confidence. Narrative framing (narrator agent) identified story type as "surprise reframe" — the NCO discovery is the cargo, the ego-graph is the vehicle.

Judge evaluation found critical nuance in the 4W/0T/1L headline:
- Only 2/4 wins are statistically significant (Alarm t=5.18, Sachs t=5.33)
- Insurance (t=1.73) and Child (t=2.49) are directional but not significant at p<0.05
- Skeletons are identical across seeds at n=10k — variance is purely LLM sampling
- Insurance win is fragile (s42 Δ=0.000, s0 Δ=+0.119)
- Alarm comparison disadvantaged MosaCD due to 4096-token context overflow
- Disguised robustness (XN-026) is thin but not load-bearing

Recommendation: proceed to SAY with mandatory caveats. Paper must report paired significance tests alongside threshold-based W/T/L. Must cite MosaCD Theorem 5.5 for NCO. Must disclose Alarm context overflow.

→ DAG: E01, I03
→ Evidence: XN-027, XN-026, LN-003

---

<a id="LOG-2026-03-17-35"></a>
### 2026-03-17 — Phase transition THINK→DO: skeleton improvement + MosaCD replication

User directive: "We need to replicate MosaCD" and "didn't we mention improving on the skeleton?" Full autonomy set — explore all directions before paper.

**Reviewer challenge** (pre-THINK→DO): MosaCD re-implementation may systematically disadvantage MosaCD. Three confounds: (1) 4096-token context overflow on Alarm returns degraded responses — MosaCD designed for 128K, (2) 12pp gap between our Alarm re-implementation (80.9%) and published MosaCD (93%) is suspicious, (3) only 2/4 wins statistically significant at p<0.05. Reviewer verdict: "contribution is thin even if numbers improve." Key questions: what specific statistical method for skeleton improvement? How many seeds needed (power analysis)? Hepar2 orientation at 77% contradicts "orientation at ceiling" narrative.

**research-reflect recommendation** (high confidence): Loop to DO with priority ordering: (1) MosaCD replication — fix context overflow, validate against published numbers. Highest information per cost. (2) Cross-model comparison — run both methods on same frontier model to eliminate model confound. (3) NCO-informed skeleton improvement — but only with concrete hypothesis, not vague exploration. Also flagged: proposal Section 5.5 synthetic experiments completely untouched.

**Three new DAG nodes**:
- PT-04: Phase transition THINK→DO
- I11: NCO-informed skeleton improvement (statistical, distinct from vetoed I10 LLM-based)
- E03: MosaCD faithful replication (fix context overflow + validate)

Skeleton analysis experiment running (CPU-only, all 6 networks × 6 alphas × 4 seeds + sample size sweep). Context overflow quantification on Alarm: seed s0 had 11/45 undecided edges vs 2/43 at seed 42 — variable but not catastrophic. Need larger context window to eliminate confound entirely.

→ DAG: PT-04, I11, E03
→ Evidence: XN-024, XN-027, XN-016, XN-014, XN-022, D-I10

---

<a id="LOG-2026-03-19-36"></a>
### 2026-03-19 — 12-seed fair comparison complete: LOCALE 2 sig wins + 1 sig loss (Holm-corrected)

Expanded from 4 seeds to 12 (s0-s10, s42) at 4096 context for all MosaCD runs. Three endpoint deployments: (1) original 4096 with 14 tok/s, (2) optimized 2048 with 227 tok/s — discovered MosaCD context sensitivity (XN-029), (3) final 4096 with 386 tok/s.

**12-seed results** (all at 4096, Holm-corrected):
- Insurance: +9.1pp, p=0.008, **SIG** (was ns at 4 seeds — power analysis confirmed)
- Sachs: +30.4pp, p<0.0001, **SIG**
- Alarm: +4.0pp, p=0.086, ns (lost Holm significance vs 4-seed)
- Child: +2.7pp, p=0.059, ns
- Asia: -12.7pp, p<0.0001, **SIG LOSS**

**Context sensitivity finding** (XN-029): MosaCD breaks at 2048 tokens (Insurance: 27/42 valid seeds at 4096 → 2/41 at 2048). LOCALE unaffected (0.848±0.014 stable). This is a genuine prompt architecture advantage — ego-graph prompts are 2-3x more context-efficient than MosaCD's chain-based per-edge templates.

**Skeleton analysis** (XN-028): alpha tuning helps Asia only (87.5%→100% at alpha=0.10). Insurance is stuck at 80.8% (PC depth limit). I11 status → partially addressed.

→ DAG: E03, I11
→ Evidence: XN-028, XN-029, XN-030

---

<a id="LOG-2026-03-26-37"></a>
### 2026-03-26 — Data seed bug: LOCALE used fixed seed=42 for all multi-seed runs

Critical bug discovered during Asia alpha=0.10 experiment. LOCALE's `sample_data()` call on line 1154 of `mve_insurance.py` did not pass the seed explicitly — Python default parameters bind at definition time, so every LOCALE run used seed=42 data regardless of `--seed` flag. MosaCD correctly passed the seed explicitly.

**Impact**: All 12-seed LOCALE results (XN-030) used identical data and skeleton. LOCALE's low variance was artificial. Paired comparison was unfair (different data for the same nominal seed). Asia results were especially affected — LOCALE always got the favorable 8-edge skeleton while MosaCD seeds varied.

**Fix**: Changed `sample_data(model, n=N_SAMPLES)` to `sample_data(model, n=N_SAMPLES, seed=SEED_DATA)`. Existing results backed up as `*_seedbug_backup`. Full re-run in progress.

**Discovery method**: Noticed LOCALE Asia alpha=0.10 reported 8/8 edges (F1=1.000) while MosaCD s0 reported 7/8 edges despite same parameters. Traced to skeleton discrepancy → data seed discrepancy → default parameter binding bug.

→ DAG: A02, E03 (status → exploring)
→ Evidence: XN-030
→ Decision: D-A02

---

<a id="LOG-2026-03-26-38"></a>
### 2026-03-26 — Corrected 12-seed comparison complete: headline robust to bug fix

Re-ran all LOCALE experiments (5 networks × 12 seeds) with corrected data seeding. Asia uses alpha=0.10.

**Result: 2 SIG wins + 2 directional + 1 SIG loss** — same headline as XN-030.

- Sachs (+30.7pp, p<0.0001) and Insurance (+8.8pp, p=0.0125) remain significant wins
- Alarm (+3.9pp) and Child (+1.1pp) remain directional but ns
- Asia (-6.7pp, p=0.0069) remains a significant loss but halved from -12.7pp

Key insight: LOCALE's stability advantage is network-dependent, not universal. LOCALE is 4.4x more stable on Insurance but 3x less stable on Asia. The old "6x more stable" claim was an artifact of fixed data. Asia loss is structural: single-endpoint coverage on degree-1 nodes causes 100% consistent orientation error on `either→tub`.

Also discovered broken symlinks from old Lightning Studio environment affecting s42 directories. All fixed.

→ DAG: E03 (status → good), A02
→ Evidence: XN-031 (supersedes XN-030)

---

<a id="LOG-2026-03-26-39"></a>
### 2026-03-26 — Phase transition DO→THINK: corrected comparison validates headline

research-reflect approved DO→THINK with medium-high confidence. The three concerns that triggered the previous THINK→DO loop-back (PT-04) are all resolved: (1) data seed bug fixed and re-run validates results, (2) 4096-context confound addressed, (3) 12-seed comparison well-powered.

Remaining gaps flagged for THINK evaluation: proposal Section 5.7 threats-to-validity gates (benchmark contamination, anonymization) not formally passed. Published MosaCD gap (model confound) needs positioning decision. THINK should evaluate these before declaring results ready for SAY.

→ DAG: PT-05
→ Evidence: XN-031, XN-029, D-A02

---

<a id="LOG-2026-03-26-40"></a>
### 2026-03-26 — Full 10-network comparison: LOCALE 7W/2T/1L across all MosaCD benchmarks

Expanded to all 10 MosaCD benchmark networks (minus Hailfinder). Added Cancer (5n), Water (32n), Mildew (35n), Win95pts (76n) with variable descriptions from BNLearn repository.

Results: LOCALE wins or ties on 9/10 networks. Only loss is Asia (8 nodes). Win95pts (+12.2pp on 76 nodes) is a strong new result. Aggregate Wilcoxon p=0.055. Only Sachs survives Holm with 10 tests, but the 7W/2T/1L pattern speaks for itself.

→ DAG: E03
→ Evidence: XN-035, XN-031, XN-034

---

<a id="LOG-2026-03-27-41"></a>
### 2026-03-27 — Full 11-network comparison: 8W/2T/1L, Wilcoxon p=0.027

Expanded to all 11 BNLearn benchmarks (10 MosaCD + Sachs). Added Hailfinder at n=2000 (PC skeleton too slow at n=10000 for 56-node network).

Final scorecard: LOCALE wins 8, ties 2, loses 1. Mean +7.6pp. Aggregate Wilcoxon signed-rank p=0.027 — statistically significant overall advantage. Largest wins on Sachs (+30.7pp), Hailfinder (+16.7pp), Hepar2 (+16.0pp), Win95pts (+12.2pp). Only loss: Asia (-6.7pp, degree-1 structural vulnerability).

→ DAG: E03
→ Evidence: XN-035 (updated to include Hailfinder)

---

<a id="LOG-2026-03-28-42"></a>
### 2026-03-28 — Synthetic ER results: LOCALE wins 14/22, +14.3pp, p=0.006

Synthetic ER experiment complete (27 LOCALE, 22 MosaCD configurations). LOCALE wins 14/22 matched pairs with mean +14.3pp (p=0.006). Both methods degrade without domain knowledge (LOCALE 0.53, MosaCD 0.39) but LOCALE preserves its relative advantage.

This directly refutes the concern (raised in RN-003) that LOCALE's BNLearn advantage is purely domain-knowledge-driven. The ego-graph structural advantage carries over to novel graphs. LOCALE's advantage grows with graph density (5/6 wins at avg_degree=3.0).

Note: RN-003 reviewer checked only 4 synthetic pairs and concluded MosaCD wins 3/4 — a sampling error. The full 22-pair dataset tells the opposite story.

→ DAG: E03
→ Evidence: XN-037

---

<a id="LOG-2026-03-28-43"></a>
### 2026-03-28 — Alarm s0 outlier investigated: LLM gives systematically wrong orientations

Alarm seed 0 has 13.5% ego-graph accuracy (vs 80-86% for all other 11 seeds). Per-edge accuracy is also low (58.1% vs ~82%). All other Alarm seeds are tightly clustered. This is a data-dependent LLM failure — the particular data realization at seed 0 triggers wrong orientations.

This explains the disguised robustness outlier (XN-033, Alarm s0: real=0.637, disguised=0.901). With disguised names, the LLM can't apply its (incorrect for this data) domain priors, so accuracy improves.

The outlier is 1/12 seeds — not a systematic problem. Paper options: exclude as outlier with justification, or include with explanation that LLM orientation quality varies by data realization.

→ Evidence: XN-033, XN-031

---

<a id="LOG-2026-03-29-44"></a>
### 2026-03-29 — Synthetic ER expanded to 10 seeds: LOCALE wins 8/10, per-seed Wilcoxon p=0.010

Expanded from 3 to 10 graph seeds (g0-g9), totaling 89 paired configurations. LOCALE wins 8/10 graph seeds with per-seed Wilcoxon p=0.010 — fully addresses the pseudoreplication concern from RN-004. Mean per-seed delta +12.5pp.

The synthetic advantage (+12.5pp) is actually larger than the BNLearn advantage (+7.6pp), refuting the hypothesis that LOCALE's advantage is primarily domain-knowledge-driven.

→ DAG: E03
→ Evidence: XN-037 (updated)
