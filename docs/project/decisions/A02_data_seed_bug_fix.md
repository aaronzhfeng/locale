---
id: D-A02
title: "Data seed bug: LOCALE used fixed seed=42 for all multi-seed runs"
date: 2026-03-26
dag_nodes: ["A02", "E03"]
links:
  - target: XN-030
    type: evidence_against
tags: ["bug", "seed", "invalidation", "comparison"]
---

# D-A02: Data Seed Bug Fix

## Bug

In `mve_insurance.py`, the `sample_data()` function has default parameter `seed=SEED_DATA` bound at **definition time** (when the module loads). The module-level `SEED_DATA = 42`. Later, the global is updated to `args.seed` (line 1126), but line 1154 calls `sample_data(model, n=N_SAMPLES)` without passing `seed` explicitly — so it always uses the default value of 42.

MosaCD's `mosacd_baseline.py` correctly calls `sample_data(model, n=n_samples, seed=seed)` with the explicit seed parameter.

## Impact

- All 12 LOCALE "seeds" in XN-030 used identical data (seed=42) and identical skeletons
- LOCALE variance was artificially low: only LLM sampling variance, not data+LLM variance
- The "6x more stable" claim (Insurance std 0.014 vs 0.087) is invalid — we were comparing LLM-only variance against data+LLM variance
- Paired comparisons were unfair: for the same nominal "seed", LOCALE and MosaCD had different data and different skeletons
- Asia results: LOCALE always got the favorable 8-edge skeleton (seed=42), while MosaCD seeds 0,1,4,5,7,9 got 7-edge skeletons

## Fix

Line 1154 changed from:
```python
data = sample_data(model, n=N_SAMPLES)
```
to:
```python
data = sample_data(model, n=N_SAMPLES, seed=SEED_DATA)
```

## Re-run Plan

- Back up all existing LOCALE multi-seed results (`*_seedbug_backup`)
- Re-run all 5 networks × 12 seeds with the fix
- Asia uses alpha=0.10, others use alpha=0.05
- Redo statistical comparison with correctly paired data
- Previous XN-030 results are archived, not deleted

## Expected Impact on Results

- LOCALE variance will increase (now includes data variance)
- Some network-level results may change direction or significance
- Asia will likely become a tie (both methods get same skeleton per seed)
- The stability advantage claim needs re-evaluation
