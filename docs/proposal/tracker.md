# Proposal Tracker

Living document. Tracks what the proposal specified vs what has been built, what deviated, and what remains. Updated at every phase transition.

**Baseline**: `baseline.md` (proposal v2: 04_ego-causal_v2.md)

Last updated: 2026-03-11

---

## Hypotheses (Section 3)

| ID | Hypothesis | Status | Evidence |
|----|-----------|--------|----------|
| H1 | Ego-context improves accuracy-cost tradeoff | Partially supported | Ego wins on unfamiliar domains (Alarm +10pp), ties on familiar. 2.4-4x query savings universal. |
| H2 | Hard CI constraints improve local consistency | Partially supported | NCO finding: 100% of CI errors are false colliders. Hard constraints hurt when colliders are wrong. |
| H3 | Reconciliation improves over majority vote | Not supported | Dawid-Skene underperforms majority vote (too sparse: 2 annotators per edge) |
| H4 | Conservative propagation resolves easy edges | Not tested meaningfully | Meek is no-op when Max-2SAT orients everything. Conservative filtering essential. |
| H5 | Calibration + abstention reduces false-orientation risk | Not tested | Phase 6 not validated |

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
| E2 | Full pipeline vs MosaCD/chatPC | End-to-end directed F1 | Partially done | F1 computed but using PC skeleton, not oracle. LOCALE 2 wins, MosaCD 3 wins. |
| E3 | Reconciliation variants | DS vs majority vs shuffled | Partially done | DS rejected. Confidence-weighted tested. EBCC not tested. |
| E4 | Propagation ablation | With/without Meek + rollback | Done | Meek is no-op. Safety valve prevents damage. |
| E5 | Calibration | Selective SHD, coverage-accuracy | Not done | Phase 6 not built. |

## What Remains from Proposal

1. **Skeleton refinement** — proposal doesn't cover this, but F1 decomposition shows skeleton is the bottleneck. This is beyond-proposal work.
2. **EBCC sensitivity analysis** (Section 4.5) — dependence-aware reconciliation not tested.
3. **Cross-model validation** — proposal specifies testing with different LLMs.
4. **Robustness** (disguised variables at scale) — done at MVE level, not at full scale.
5. **Formal evaluation matrix** (Section 5) — proposal specifies exact comparison rules not yet followed.

## Deviations Logged

| Date | What Changed | Why | Decision Log |
|------|-------------|-----|-------------|
| 2026-03-10 | Phase 3 simplified from DS to confidence-weighted | DS underperforms with 2 annotators | LOG-2026-03-11-24 |
| 2026-03-10 | Phase 4 conservative-only (Meek is no-op) | Max-2SAT already orients everything | LOG-2026-03-11-24 |
| 2026-03-10 | Phase 5 descoped | Residual empty after Max-2SAT | LOG-2026-03-11-22 |
| 2026-03-10 | Phase 6 descoped | Needs held-out instances, premature | LOG-2026-03-11-22 |
| 2026-03-10 | NCO as default over hard constraints | 100% of CI errors are false colliders | LOG-2026-03-10-5 |
