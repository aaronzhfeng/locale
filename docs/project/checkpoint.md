# Checkpoint

## Current Task
Iterative BFS (E02) — code complete, smoketested. MosaCD (E01) also ready. Both awaiting 27B LLM endpoint.

## Phase
DO — Autonomy: full

## What We Have
- Phase 1: Ego-graph LLM orientation (K=10 debiased, 6 networks)
- Phase 2: Max-2SAT with NCO constraints (works, eliminates false colliders)
- Phase 3: Confidence-weighted reconciliation (DS tested, doesn't help)
- Phase 4: Conservative propagation with Meek (no-op — Max-2SAT resolves everything)
- Phase 5: PE fallback (mixed — helps Sachs/Child, hurts Alarm)
- Phase 6: Calibration + selective output (works: 89.4% -> 92.9% precision at 92% coverage)
- Skeleton refinement: VETOED (XN-021, D-I10, 0 TP across ALL 6 networks including Hepar2)
- NCO validation: PARTIALLY COMPLETE (see below)

## Key Numbers (K=10, n=10k, NCO, 6 networks)

| Network   | Edges | P3 Acc | P6 Prec | P6 Cover |
|-----------|-------|--------|---------|----------|
| Insurance | 43    | 95.3%  | 95.3%   | 100%     |
| Alarm     | 43    | 93.0%  | 92.5%   | 93%      |
| Sachs     | 17    | 76.5%  | 92.9%   | 82%      |
| Child     | 25    | 88.0%  | 90.9%   | 88%      |
| Asia      | 7     | 100%   | 100%    | 100%     |
| Hepar2    | 64    | 87.5%  | 91.2%   | 89%      |
| **Agg**   | 199   | 89.4%  | 92.9%   | 92%      |

## NCO Validation Results (In Progress)

**Key finding: 98.1% of CI orientation errors are false colliders (FC). FC rate approaches 100% at n>=5000.**

### FINAL aggregate by sample size (ALL 6 networks, 3 seeds each):
| n | Total FC | Total FNC | Total Errors | FC Rate | Networks |
|---|----------|-----------|-------------|---------|----------|
| 500 | 101 | 5 | 106 | 95.3% | 6 |
| 1000 | 138 | 11 | 149 | 92.6% | 6 |
| 2000 | 151 | 3 | 154 | 98.1% | 6 |
| 5000 | 200 | 0 | 200 | 100.0% | 6 |
| 10000 | 234 | 0 | 234 | 100.0% | 6 |
| 20000 | 54 | 0 | 54 | 100.0% | 5 |
| 50000 | 46 | 1 | 47 | 97.9% | 4 |
| **Total** | **924** | **20** | **944** | **97.9%** | |

### Per-network summary:
| Network | FC | FNC | Errors | FC Rate | Sample sizes |
|---------|-----|-----|--------|---------|-------------|
| Insurance | 262 | 6 | 268 | 97.8% | 500-50k |
| Alarm | 52 | 2 | 54 | 96.3% | 500-20k |
| Sachs | 45 | 2 | 47 | 95.7% | 500-50k |
| Child | 77 | 6 | 83 | 92.8% | 500-50k |
| Asia | 9 | 0 | 9 | 100.0% | 500-50k |
| Hepar2 | 479 | 4 | 483 | 99.2% | 500-10k |

### Key patterns:
- FC rate = 100% at n>=5000 (200/200 errors across 6 networks)
- FC rate > 92% at ALL sample sizes
- Child is hardest (92.8% overall) — more FNC at small n, likely due to network structure
- Sachs and Asia reach 0 errors at n>=10k (perfect CI with full skeleton)
- Hepar2 has most errors (483) but 99.2% are FC — NCO robust even with 53% skeleton coverage

### Bug found and fixed this session
`nco_validation.py` had two bugs:
1. **Seed bug**: `sample_data()` was called without passing the seed param — pgmpy's `forward_sample(seed=)` defaulted to 42 for all seeds. Fixed: now passes `seed=seed`.
2. **Counting bug**: Skeleton false-positive edges created CI facts where ground truth was unavailable. These were counted as "incorrect" but not classified as FC or FNC. Fixed: added `unclassifiable` category, excluded from error rate calculation.

**The old (buggy-seed) Alarm run saved to `results/nco_validation/nco_sample_size_results.json` — this file has WRONG data (identical across seeds). Must be overwritten by the corrected run when it completes.**

## Skeleton Refinement Final Results (All 6 Networks)

Hepar2 skeleton refinement completed (background task). Results:
| Network | Candidates | GT-Missing | TP | FP |
|---------|-----------|-----------|-----|-----|
| Insurance | 85 | 10 | 0 | 0 |
| Alarm | 71 | 3 | 0 | 0 |
| Sachs | 14 | 0 | 0 | 0 |
| Child | 52 | 0 | 0 | 0 |
| Asia | 10 | 1 | 0 | 0 |
| Hepar2 | 172 | 58 | 0 | 9 |

Hepar2 worst: 9 FP added, 0 TP, precision dropped 11.5%. Confirms veto across all 6 networks.

## Literature Scout Findings (Completed)
Scout ran on 4 research questions. Key findings (NOT persisted as LN-*.md files yet — agent output only):
- RQ1 (skeleton refinement): No prior work on LLM-only skeleton recovery. Gap confirmed.
- RQ2 (ego vs per-edge): LOCALE is first systematic comparison. No counter-evidence.
- RQ3 (NCO): Novel empirical discovery. No prior false-collider bias analysis in literature.
- RQ4 (calibration): Strong methodological precedent (Venn-Abers, conformal). DAG application novel.
Action needed: Create LN-001 through LN-004 from scout output.

## 9B Model Size Ablation (NEW — XN-023)
Ran Insurance + Alarm with Qwen3.5-9B (endpoint had 9B loaded). Key finding: ego-graph accuracy COLLAPSES at 9B (-22 to -31pp vs 27B) while per-edge barely changes (-1 to -4pp). CI constraint violations jump from ~2% to 25-42%. Ego-graph is an emergent capability requiring model scale.

## MosaCD Re-Implementation (E01)
- File: `experiments/mosacd_baseline.py`
- Faithfully implements all 5 steps from arXiv:2509.23570
- Uses same skeleton (PC-stable) and same LLM (Qwen3.5-27B) as LOCALE
- 10 queries per edge (5 reps × 2 orderings for positional bias detection)
- Verified: Asia PC-only F1=0.667 (matches paper's 0.67), Insurance PC-only F1=0.695
- Template distribution (Insurance): 22 full, 4 none2u, 14 none2v, 3 none
- Query budget: ~430 per network (43 skel edges × 10), ~18x more than LOCALE ego-graph

## Iterative BFS Expansion (E02)
- File: `experiments/iterative_bfs.py`
- Original proposal design: multi-round ego-graph with SP-style decimation
- Round 1 queries all eligible nodes, decimates high-confidence edges (majority > 0.7)
- Round 2+ queries frontier nodes with enriched prompts containing established orientations
- Max-2SAT extended with unary hard constraints from established edges
- Two modes: full-coverage R1 (default) or `--incremental` (seed nodes only)
- Smoketested: all non-LLM components verified

## What's Next
1. ~~Finish NCO validation~~ — DONE (all 6 networks complete, XN-022 written)
2. ~~Write XN-022~~ — DONE
3. ~~9B model ablation~~ — DONE (XN-023, Insurance + Alarm)
4. ~~MosaCD re-implementation~~ — DONE (mosacd_baseline.py, E01)
5. ~~Iterative BFS~~ — DONE (iterative_bfs.py, E02)
6. **Run iterative BFS** — Insurance + Alarm with 27B endpoint, compare R1 vs R2+ (NEEDS LLM ENDPOINT)
7. **Run MosaCD baseline** — Insurance + Alarm + Asia with 27B endpoint (NEEDS LLM ENDPOINT)
8. **Robustness** — Disguised/anonymized variables (NEEDS LLM ENDPOINT)
9. **Create LN-001 to LN-004** — Persist literature scout findings as notes

## Migration Notes
- Server can be CPU-only for NCO validation (items 1-2)
- Items 3-4 need LLM inference (RunPod or local vLLM with GPU)
- All experiment code is in `projects/locale/experiments/`
- Key files: `nco_validation.py`, `mve_insurance.py`, `skeleton_refinement.py`
- Dependencies: pgmpy, numpy, networkx, openai (for LLM experiments only)
- pgmpy 1.0.0 bug workaround in `mve_insurance.py:estimate_skeleton()` — don't upgrade pgmpy

## Blockers
None
