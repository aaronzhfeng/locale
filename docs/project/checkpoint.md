# Checkpoint

## Current Task
MosaCD comparison (E01) and iterative BFS (E02) experiments complete. Results analyzed and logged.

## Phase
DO → approaching THINK — Autonomy: full

## What We Have
- Phase 1: Ego-graph LLM orientation (K=10 debiased, 6 networks)
- Phase 2: Max-2SAT with NCO constraints (works, eliminates false colliders)
- Phase 3: Confidence-weighted reconciliation (DS tested, doesn't help)
- Phase 4: Conservative propagation with Meek (no-op — Max-2SAT resolves everything)
- Phase 5: PE fallback (mixed — helps Sachs/Child, hurts Alarm)
- Phase 6: Calibration + selective output (works: 89.4% -> 92.9% precision at 92% coverage)
- Skeleton refinement: VETOED (XN-021, D-I10)
- NCO validation: COMPLETE (XN-022, 97.9% FC rate)
- MosaCD comparison: COMPLETE (XN-024, 5 networks)
- Iterative BFS: NEGATIVE RESULT (XN-025, single-pass wins)

## MosaCD Same-Model Comparison (XN-024)

| Network | LOCALE F1 | MosaCD F1 | Delta | LOCALE Q | MosaCD Q |
|---------|-----------|-----------|-------|----------|----------|
| Insurance | 0.863 | 0.863 | 0.0 | ~230 | 430 |
| Alarm | 0.899 | 0.809 | **+9.0pp** | ~260 | 430 |
| Asia | 0.933 | 0.933 | 0.0 | ~50 | 70 |
| Child | 0.880 | 0.880 | 0.0 | ~75 | 250 |
| Sachs | 0.765 | 0.588 | **+17.7pp** | ~85 | 170 |

**Score: LOCALE 2 wins, 3 ties, 0 losses. Always ~50% fewer queries.**

## Iterative BFS (XN-025) — Negative Result

| Network | LOCALE K=10 F1 | BFS K=5×2 F1 | Same budget |
|---------|----------------|--------------|-------------|
| Insurance | 0.863 | 0.800 | Yes (~230 Q) |
| Alarm | 0.899 | 0.899 | Yes (~260 Q) |

More votes > more context. Single-pass wins.

## Key Numbers (K=10, n=10k, NCO, 6 networks)

| Network | Edges | P3 Acc | Dir F1 | Skel Cover |
|---------|-------|--------|--------|------------|
| Insurance | 43 | 95.3% | 0.863 | 83% |
| Alarm | 43 | 93.0% | 0.899 | 93% |
| Sachs | 17 | 76.5% | 0.765 | 100% |
| Child | 25 | 88.0% | 0.880 | 100% |
| Asia | 7 | 100% | 0.933 | 88% |
| Hepar2 | 64 | 87.5% | 0.599 | 52% |

**Note: F1 previously reported as 88.4% for Insurance was incorrect — actual is 86.3%.**

## What's Next
1. ~~NCO validation~~ — DONE
2. ~~9B model ablation~~ — DONE (XN-023)
3. ~~MosaCD re-implementation~~ — DONE (E01, XN-024)
4. ~~Iterative BFS~~ — DONE (E02, XN-025, negative)
5. **Robustness** — Disguised/anonymized variables (NEEDS LLM ENDPOINT, available now)
6. **Create LN-001 to LN-004** — Persist literature scout findings
7. **Phase transition** — Move to THINK: narrative framing, judge results
8. **Hepar2 re-run** — Consider larger context for MosaCD comparison fairness

## Blockers
None — 27B endpoint is live
