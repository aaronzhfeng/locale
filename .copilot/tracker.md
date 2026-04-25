# Proposal Tracker

Living document. Tracks what the proposal specified vs what has been built, what deviated, and what remains. Updated at every phase transition.

**Baseline**: `baseline.md` (proposal v2: 04_ego-causal_v2.md)

Last updated: 2026-04-10 (all experiments complete, 6-method 11-network comparison)

---

## Hypotheses (Section 3)

| ID | Hypothesis | Status | Evidence |
|----|-----------|--------|----------|
| H1 | Ego-context improves accuracy-cost tradeoff | Supported | Multi-seed (XN-027): LOCALE 4W/0T/1L vs MosaCD with ~50% fewer queries. Disguised test (XN-026) confirms structural reasoning, not memorization. |
| H2 | Hard CI constraints improve local consistency | Supported (refined) | NCO finding: 100% of CI errors are false colliders (XN-022). Non-collider-only constraints improve accuracy; collider constraints hurt. The H2 hypothesis holds but with the important caveat that only non-collider constraints should be enforced. |
| H3 | Reconciliation improves over majority vote | Not supported | Dawid-Skene underperforms majority vote (too sparse: 2 annotators per edge). Confidence-weighted majority vote used instead. |
| H4 | Conservative propagation resolves easy edges | Not tested meaningfully | Meek is no-op when Max-2SAT orients everything. Conservative filtering essential but propagation itself is unnecessary. |
| H5 | Calibration + abstention reduces false-orientation risk | Not tested | Phase 6 not built. Descoped. |

## Pipeline Phases (Section 4)

| Phase | Proposal Spec | Built? | Status | Deviation |
|-------|--------------|--------|--------|-----------|
| 0: Skeleton | PC-stable backend | Yes | Working | Using pgmpy PC. Added debiased K=10 variant. |
| 1: Ego scoring | Ego-graph prompting with K votes | Yes | Working | K=5 initially, K=10 for full runs. Added disguised names. |
| 2: Local constraint compilation | CI-derived hard constraints, Max-2SAT | Yes | Working | NCO variant (non-collider only) is the robust default. Hard constraints hurt due to false colliders. |
| 3: Reconciliation | Multiclass Dawid-Skene | Built, rejected | DS underperforms | Structural mismatch: 2 annotators too sparse for DS. Using confidence-weighted majority vote. |
| 4: Conservative propagation | Meek rules + priority queue + rollback | Built, no-op | Meek has nothing to do | Max-2SAT already orients all edges. Conservative filtering prevents damage on imperfect skeletons. |
| 5: Budgeted per-edge fallback | LLM queries on residual hard edges | Not built | — | Descoped (I06 parked). Residual is empty after Max-2SAT. |
| 6: Calibration + selective output | Venn-Abers on held-out graph instances | Not built | — | Descoped (I07 parked). Needs held-out graph instances. |

## Experiments (Section 5)

| ID | Experiment | Proposal Spec | Status | Notes |
|----|-----------|---------------|--------|-------|
| E1 | Ego vs per-edge on oracle skeleton | Matched-budget comparison | Done | 6 networks, 194 edges. Ego ~ties or wins depending on domain. |
| E2 | Full pipeline vs MosaCD/chatPC | End-to-end directed F1 | Done (11 networks, 6 methods) | **6-method, 11-network comparison** (XN-035/038/039): LOCALE best or tied on 9/11 networks. 5 baselines: PC-orig, PC+Meek, Shapley-PC, ILS-CSL, MosaCD. Synthetic ER validation: 8/10 seeds, p=0.010 (XN-037). |
| E3 | Reconciliation variants | DS vs majority vs shuffled | Partially done | DS rejected. Confidence-weighted tested. EBCC not tested. |
| E4 | Propagation ablation | With/without Meek + rollback | Done | Meek is no-op. Safety valve prevents damage. |
| E5 | Calibration | Selective SHD, coverage-accuracy | Not done | Phase 6 not built. |

## Additional Experiments (beyond proposal)

| ID | Experiment | Status | Notes |
|----|-----------|--------|-------|
| E-BFS | Iterative BFS decimation | Negative result (XN-025) | Single-pass K=10 beats multi-round K=5×2. More votes > more context. |
| E-DIS | Disguised variable robustness | Done (XN-033, supersedes XN-026) | 3 networks × 3 seeds. Domain knowledge effect is network-dependent: Insurance -5pp, Alarm +10.3pp, Sachs -9.7pp. |
| E-ABL | 9B model ablation | Done (XN-023) | 27B required for ego accuracy. 9B too weak. |
| E-NCO | NCO validation | Done (XN-022) | 97.9% false collider rate across 6 networks. |
| E-D1 | Degree-1 vulnerability analysis | Done (XN-032) | Network-dependent: Asia/Alarm vulnerable, Insurance/Child fine. |
| E-HP2 | Hepar2 multi-seed | Done (XN-034) | +16.0pp over MosaCD, p=0.013. |
| E-HF | Hailfinder multi-seed (n=2000) | Done (XN-036) | +16.7pp over MosaCD, p=0.017. PC too slow at n=10k. |
| E-NEW | 5 new MosaCD networks | Done (XN-035) | Cancer, Water, Mildew, Hailfinder, Win95pts added. |
| E-SYN | Synthetic ER graphs | Done (XN-037) | 90 configs, 10 seeds. LOCALE 8/10 seeds, p=0.010. |
| E-BL | Statistical baselines | Done (XN-038) | PC-orig, PC+Meek, Shapley-PC across 10 networks. |
| E-ILS | ILS-CSL baseline | Done (XN-039) | HC variant, 7 networks. LOCALE wins 5/7. |

## What Remains from Proposal

1. **Skeleton refinement** — proposal doesn't cover this, but F1 decomposition shows skeleton is the bottleneck. VETOED (I10) — 0 true positives across 5/6 networks.
2. **EBCC sensitivity analysis** (Section 4.5) — dependence-aware reconciliation not tested. DS already rejected, EBCC unlikely to help with 2 annotators.
3. **Cross-model validation** — proposal specifies testing with different LLMs. 9B ablation done (XN-023), other model families not tested.
4. ~~**Robustness**~~ (disguised variables) — DONE (XN-033, 3 networks × 3 seeds). Domain knowledge effect is network-dependent. NCO constraints work regardless of naming.
5. **Formal evaluation matrix** (Section 5) — proposal specifies exact comparison rules not yet followed.
6. ~~**Multi-seed validation**~~ — DONE (XN-031, corrected). 12 seeds × 5 networks × 2 methods. LOCALE 2 SIG wins + 2 directional + 1 SIG loss. Holm-corrected. Data seed bug (D-A02) found and fixed — results robust.
7. ~~**Asia alpha=0.10**~~ — DONE (XN-031). Asia loss halved (-12.7pp → -6.7pp) but remains significant. Structural limitation: degree-1 nodes get single-endpoint coverage.
8. ~~**Skeleton improvement (I11)**~~ — DONE (XN-028). Alpha tuning exhausted: helps Asia only, Insurance depth-limited. CPC untested but unlikely to help.
9. ~~**Context sensitivity**~~ — FOUND (XN-029). MosaCD breaks at 2048 tokens. LOCALE is robust. Novel finding — no prior work measures this.

## Deviations Logged

| Date | What Changed | Why | Decision Log |
|------|-------------|-----|-------------|
| 2026-03-10 | Phase 3 simplified from DS to confidence-weighted | DS underperforms with 2 annotators | LOG-2026-03-11-24 |
| 2026-03-10 | Phase 4 conservative-only (Meek is no-op) | Max-2SAT already orients everything | LOG-2026-03-11-24 |
| 2026-03-10 | Phase 5 descoped | Residual empty after Max-2SAT | LOG-2026-03-11-22 |
| 2026-03-10 | Phase 6 descoped | Needs held-out instances, premature | LOG-2026-03-11-22 |
| 2026-03-10 | NCO as default over hard constraints | 100% of CI errors are false colliders | LOG-2026-03-10-5 |
| 2026-03-11 | Multi-seed validation required | research-reflect: MosaCD comparison at 2/5 confidence with single seed | LOG-2026-03-11-32 |
| 2026-03-12 | Multi-seed validation complete | 4W/0T/1L. MosaCD comparison confidence now moderate-high | LOG-2026-03-12-33 |
| 2026-03-26 | Data seed bug found (D-A02) | LOCALE used fixed seed=42 for all seeds | LOG-2026-03-26-37 |
| 2026-03-26 | Corrected comparison (XN-031) | Headline unchanged: 2W/2D/1L. LOCALE re-run with correct seeds | LOG-2026-03-26-38 |
| 2026-03-26 | Phase transition DO→THINK (PT-05) | Corrected results validated, research-reflect approved | LOG-2026-03-26-39 |
| 2026-03-27 | Expanded to 11 BNLearn networks | Match all MosaCD benchmarks | LOG-2026-03-27-41 |
| 2026-03-29 | Synthetic ER expanded to 10 seeds | Address pseudoreplication concern | LOG-2026-03-29-44 |
| 2026-04-05 | 5 baselines added (PC-orig, PC+Meek, Shapley-PC, ILS-CSL) | Match MosaCD comparison breadth | LOG-2026-04-05-45, LOG-2026-04-05-46 |
