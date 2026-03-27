# Proposal Tracker

Living document. Tracks what the proposal specified vs what has been built, what deviated, and what remains. Updated at every phase transition.

**Baseline**: `baseline.md` (proposal v2: 04_ego-causal_v2.md)

Last updated: 2026-03-11 (multi-seed validation in progress)

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
| E2 | Full pipeline vs MosaCD/chatPC | End-to-end directed F1 | Done (5 networks, 12 seeds) | **Corrected** 12-seed comparison (XN-031, supersedes XN-030 after data seed bug fix D-A02): Sachs +30.7pp (SIG), Insurance +8.8pp (SIG), Alarm +3.9pp (ns), Child +1.1pp (ns), Asia -6.7pp (SIG LOSS). Holm-corrected. Context sensitivity found (XN-029): MosaCD breaks at 2048 tokens. |
| E3 | Reconciliation variants | DS vs majority vs shuffled | Partially done | DS rejected. Confidence-weighted tested. EBCC not tested. |
| E4 | Propagation ablation | With/without Meek + rollback | Done | Meek is no-op. Safety valve prevents damage. |
| E5 | Calibration | Selective SHD, coverage-accuracy | Not done | Phase 6 not built. |

## Additional Experiments (beyond proposal)

| ID | Experiment | Status | Notes |
|----|-----------|--------|-------|
| E-BFS | Iterative BFS decimation | Negative result (XN-025) | Single-pass K=10 beats multi-round K=5×2. More votes > more context. |
| E-DIS | Disguised variable robustness | Done (XN-026) | Names → V01, V02: -0.7pp ego, +4.7pp/0.0pp after NCO. LOCALE doesn't rely on memorized domain knowledge. |
| E-ABL | 9B model ablation | Done (XN-023) | 27B required for ego accuracy. 9B too weak. |
| E-NCO | NCO validation | Done (XN-022) | 97.9% false collider rate across 6 networks. |

## What Remains from Proposal

1. **Skeleton refinement** — proposal doesn't cover this, but F1 decomposition shows skeleton is the bottleneck. VETOED (I10) — 0 true positives across 5/6 networks.
2. **EBCC sensitivity analysis** (Section 4.5) — dependence-aware reconciliation not tested. DS already rejected, EBCC unlikely to help with 2 annotators.
3. **Cross-model validation** — proposal specifies testing with different LLMs. 9B ablation done (XN-023), other model families not tested.
4. **Robustness** (disguised variables) — Done (XN-026). Insurance +4.7pp, Alarm 0.0pp after NCO. Structural constraints are the primary value driver.
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
