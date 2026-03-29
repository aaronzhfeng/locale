# Checkpoint

## Current Task
All experiments complete including synthetic ER. GPU released. Ready for paper writing.

## Phase
THINK — Autonomy: full

## Final Results Summary

### BNLearn (11 networks): 8W/2T/1L, Wilcoxon p=0.027

| Network | Nodes | LOCALE F1 | MosaCD F1 | Delta |
|---------|-------|-----------|-----------|-------|
| Sachs | 11 | 0.865 | 0.557 | +30.7pp |
| Hailfinder | 56 | 0.616 | 0.449 | +16.7pp |
| Hepar2 | 70 | 0.565 | 0.405 | +16.0pp |
| Win95pts | 76 | 0.694 | 0.573 | +12.2pp |
| Insurance | 27 | 0.845 | 0.757 | +8.8pp |
| Alarm | 37 | 0.841 | 0.801 | +3.9pp |
| Child | 20 | 0.882 | 0.871 | +1.1pp |
| Water | 32 | 0.579 | 0.569 | +1.1pp |
| Cancer | 5 | 0.964 | 0.964 | 0.0pp |
| Mildew | 35 | 0.859 | 0.859 | 0.0pp |
| Asia | 8 | 0.900 | 0.967 | -6.7pp |

### Synthetic ER (22 paired graphs): LOCALE 14W/8L, p=0.006
- LOCALE: 0.528±0.120, MosaCD: 0.385±0.141, delta +14.3pp
- Refutes "domain knowledge only" hypothesis

### Other key results
- NCO: 97.9% false collider rate (XN-022)
- Context sensitivity: MosaCD breaks at 2048, LOCALE unaffected (XN-029)
- Degree-1 vulnerability: network-dependent (XN-032)
- Disguised robustness: domain knowledge effect is network-dependent (XN-033)

## Reviewer Status
- RN-001: Weak Reject → addressed all must-haves
- RN-002: Weak Reject → addressed documentation gaps
- RN-003 (Opus): Weak Reject based on 4-sample synthetic analysis — refuted by full 22-pair data (LOCALE wins 14/22, p=0.006)
- RN-003 (Sonnet): Borderline

## Next Steps
1. Call reviewer again with synthetic results for final verdict
2. Narrative reframe with synthetic evidence
3. Paper writing
