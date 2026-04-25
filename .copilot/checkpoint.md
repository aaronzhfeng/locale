# Checkpoint

## Current Task
All experiments and baselines complete. Documentation update in progress. Ready for paper finalization.

## Phase
THINK — Autonomy: full

## Final 6-Method, 11-Network Comparison

| Network | Nodes | PC-orig | PC+Meek | Shapley-PC | ILS-CSL | MosaCD | LOCALE | Best |
|---------|-------|---------|---------|------------|---------|--------|--------|------|
| Cancer | 5 | 0.518 | 0.518 | 0.438 | 0.350 | 0.964 | 0.964 | tie(LLM) |
| Asia | 8 | 0.761 | 0.626 | 0.403 | 0.800 | 0.967 | 0.900 | MosaCD |
| Sachs | 11 | 0.278 | 0.278 | 0.044 | — | 0.557 | 0.866 | LOCALE |
| Child | 20 | 0.669 | 0.578 | 0.824 | 0.829 | 0.871 | 0.882 | LOCALE |
| Insurance | 27 | 0.526 | 0.575 | 0.697 | 0.781 | 0.757 | 0.844 | LOCALE |
| Water | 32 | 0.294 | 0.323 | 0.372 | 0.534 | 0.569 | 0.579 | LOCALE |
| Mildew | 35 | 0.656 | 0.643 | 0.830 | 0.517 | 0.859 | 0.859 | tie(LLM) |
| Alarm | 37 | 0.829 | 0.833 | 0.814 | 0.891 | 0.801 | 0.842 | ILS-CSL |
| Hailfinder | 56 | — | — | — | — | 0.449 | 0.616 | LOCALE |
| Hepar2 | 70 | 0.250 | 0.263 | 0.462 | — | 0.405 | 0.565 | LOCALE |
| Win95pts | 76 | 0.633 | 0.648 | 0.690 | — | 0.573 | 0.694 | LOCALE |

**LOCALE best or tied on 9/11 networks.**

## Additional Evidence
- Synthetic ER: 90 LOCALE + 89 MosaCD configs, 10 graph seeds, per-seed Wilcoxon p=0.010
- NCO: 97.9% false collider rate (XN-022)
- Context sensitivity: MosaCD breaks at 2048 tokens (XN-029)
- Degree-1 vulnerability: network-dependent (XN-032)
- Disguised robustness: 3 networks × 3 seeds (XN-033)
- MosaCD fidelity gap disclosed per-network (XN-035)

## Reviewer Status
- RN-005: Weak Accept (CLeaR ready)
- All must-haves addressed
- 5 baselines matching MosaCD's paper

## Paper Status
- CoLM 2026 template compiled (deliverables/locale-colm2026/)
- 3 data figures generated (figures/)
- 2 conceptual figure specs for image generation (figure_specs.md)
- Need to update paper with 6-method table and ILS-CSL/Shapley-PC results

## Experiment Notes Index
XN-031: Corrected 12-seed comparison
XN-032: Degree-1 vulnerability analysis
XN-033: Disguised robustness multi-seed
XN-034: Hepar2 multi-seed
XN-035: 11-network full comparison (updated with fidelity gap)
XN-036: Hailfinder multi-seed
XN-037: Synthetic ER comparison (10 seeds)
XN-038: Statistical baselines (PC-orig, PC+Meek, Shapley-PC)
XN-039: ILS-CSL baseline
